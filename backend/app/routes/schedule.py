from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime

from ..models.user import UserProfile, UserProfileUpdate
from ..models.deadline import Deadline
from ..services.firestore_service import firestore_service
from ..services.gemini_service import gemini_service

router = APIRouter(prefix="/api/schedule", tags=["Schedule & Profile"])

def get_current_user_id() -> str:
    return "default_user"

@router.get("/profile", response_model=UserProfile)
def get_profile(user_id: str = Depends(get_current_user_id)):
    return firestore_service.get_user_profile(user_id)

@router.put("/profile", response_model=UserProfile)
def update_profile(payload: UserProfileUpdate, user_id: str = Depends(get_current_user_id)):
    profile = firestore_service.get_user_profile(user_id)
    
    # Update fields if provided
    if payload.name is not None:
        profile.name = payload.name
    if payload.working_hours_start is not None:
        profile.working_hours_start = payload.working_hours_start
    if payload.working_hours_end is not None:
        profile.working_hours_end = payload.working_hours_end
    if payload.energy_profile is not None:
        profile.energy_profile = payload.energy_profile
    if payload.stress_handling is not None:
        profile.stress_handling = payload.stress_handling
        
    firestore_service.update_user_profile(user_id, profile)
    
    # Dynamically reschedule all active deadlines to match the new profile
    active_deadlines = firestore_service.get_user_deadlines(user_id)
    for deadline in active_deadlines:
        if deadline.status == "active" and deadline.subtasks:
            # Reschedule remaining subtasks starting from now
            incomplete_subtasks = [t for t in deadline.subtasks if t.status != "done"]
            if incomplete_subtasks:
                try:
                    schedule_res = gemini_service.schedule_subtasks(
                        subtasks=incomplete_subtasks,
                        due_date_str=deadline.due_date,
                        user_profile=profile,
                        start_time_str=datetime.utcnow().isoformat()
                    )
                    
                    # Update active subtasks with new scheduled starts and ends
                    scheduled_map = {item.title: item for item in schedule_res.scheduled_tasks}
                    for sub in deadline.subtasks:
                        if sub.status != "done":
                            match = scheduled_map.get(sub.title)
                            if match:
                                sub.scheduled_start = match.scheduled_start
                                sub.scheduled_end = match.scheduled_end
                                
                    firestore_service.update_deadline(deadline)
                except Exception as e:
                    # Log error but don't fail the whole user profile save
                    print(f"Failed to reschedule deadline {deadline.id}: {e}")
                    
    return profile

@router.post("/reschedule/{deadline_id}", response_model=Deadline)
def reschedule_deadline(deadline_id: str, user_id: str = Depends(get_current_user_id)):
    deadline = firestore_service.get_deadline(deadline_id)
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
        
    user_profile = firestore_service.get_user_profile(user_id)
    incomplete_subtasks = [t for t in deadline.subtasks if t.status != "done"]
    
    if not incomplete_subtasks:
        raise HTTPException(status_code=400, detail="No incomplete tasks to reschedule")
        
    # Re-trigger scheduler starting from now
    schedule_res = gemini_service.schedule_subtasks(
        subtasks=incomplete_subtasks,
        due_date_str=deadline.due_date,
        user_profile=user_profile,
        start_time_str=datetime.utcnow().isoformat()
    )
    
    scheduled_map = {item.title: item for item in schedule_res.scheduled_tasks}
    for sub in deadline.subtasks:
        if sub.status != "done":
            match = scheduled_map.get(sub.title)
            if match:
                sub.scheduled_start = match.scheduled_start
                sub.scheduled_end = match.scheduled_end
                
    firestore_service.update_deadline(deadline)
    return deadline
