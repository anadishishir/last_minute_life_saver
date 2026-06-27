from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime

from ..models.recovery import PanicRequest, RecoveryPlan
from ..models.deadline import Deadline, SubTask
from ..services.firestore_service import firestore_service
from ..services.gemini_service import gemini_service

router = APIRouter(prefix="/api/recovery", tags=["Panic & Recovery"])

def get_current_user_id() -> str:
    return "default_user"

@router.post("/panic/{deadline_id}", response_model=RecoveryPlan)
def trigger_panic(deadline_id: str, payload: PanicRequest, user_id: str = Depends(get_current_user_id)):
    deadline = firestore_service.get_deadline(deadline_id)
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
        
    user_profile = firestore_service.get_user_profile(user_id)
    
    # 1. Generate recovery plan via Gemini
    recovery_res = gemini_service.generate_recovery_plan(
        deadline=deadline,
        current_time_str=payload.current_time,
        lost_hours=payload.lost_hours,
        custom_panic_reason=payload.custom_panic_reason,
        user_profile=user_profile
    )
    
    # 2. Update the deadline subtasks list
    # Map the new durations and schedule back
    rearranged_map = {item.title.replace("⚡ CAPPED: ", ""): item for item in recovery_res.rearranged_tasks}
    
    updated_subtasks = []
    # Retain completed subtasks as they were
    for sub in deadline.subtasks:
        if sub.status == "done":
            updated_subtasks.append(sub)
        else:
            # Check if this task is in the rearranged list
            # We match by looking for subtask title matches
            match = rearranged_map.get(sub.title)
            
            # Or match general starts if title is modified
            if not match:
                # Direct match fallback
                for title_key, item in rearranged_map.items():
                    if title_key in sub.title or sub.title in title_key:
                        match = item
                        break
                        
            if match:
                sub.title = match.title
                sub.duration_hours = match.duration_hours
                sub.scheduled_start = match.scheduled_start
                sub.scheduled_end = match.scheduled_end
                # Keep status as 'todo' or 'in_progress'
                updated_subtasks.append(sub)
            else:
                # If Gemini omitted a task, it was triaged/skipped!
                # We mark it as skipped or let's say "skipped" status
                sub.status = "skipped"
                updated_subtasks.append(sub)
                
    # 3. Update Deadline metadata
    deadline.subtasks = updated_subtasks
    deadline.status = "panicked"
    
    # Save the updated deadline
    firestore_service.update_deadline(deadline)
    
    # Return recovery plan details to client
    return RecoveryPlan(
        generated_at=datetime.utcnow().isoformat(),
        triage_strategy=recovery_res.triage_strategy,
        rearranged_subtasks=[s for s in updated_subtasks if s.status != "done" and s.status != "skipped"],
        motivation_tip=recovery_res.motivation_tip
    )
