import uuid
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime

from ..models.deadline import Deadline, DeadlineCreate, SubTask, SubTaskUpdate
from ..services.firestore_service import firestore_service
from ..services.gemini_service import gemini_service

router = APIRouter(prefix="/api/deadlines", tags=["Deadlines"])

# Helper to get user profile (mock user_id since we don't have auth implemented yet)
def get_current_user_id() -> str:
    return "default_user"

@router.post("", response_model=Deadline)
def create_deadline(payload: DeadlineCreate, user_id: str = Depends(get_current_user_id)):
    user_profile = firestore_service.get_user_profile(user_id)
    
    # 1. Ask Gemini to decompose the goal into subtasks
    decomposition = gemini_service.decompose_deadline(
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        estimated_hours=payload.estimated_hours,
        user_profile=user_profile
    )
    
    # Create the base subtasks list with unique IDs
    subtasks = []
    for g_sub in decomposition.subtasks:
        subtasks.append(SubTask(
            id=str(uuid.uuid4())[:8],
            title=g_sub.title,
            duration_hours=g_sub.duration_hours,
            importance=g_sub.importance,
            status="todo"
        ))
        
    # 2. Schedule these subtasks within working hours
    schedule_res = gemini_service.schedule_subtasks(
        subtasks=subtasks,
        due_date_str=payload.due_date,
        user_profile=user_profile
    )
    
    # Map the scheduled times back to our subtasks
    scheduled_tasks_map = {item.title: item for item in schedule_res.scheduled_tasks}
    for sub in subtasks:
        match = scheduled_tasks_map.get(sub.title)
        if match:
            sub.scheduled_start = match.scheduled_start
            sub.scheduled_end = match.scheduled_end
            
    # Create the complete deadline object
    total_hours = decomposition.suggested_total_hours
    deadline = Deadline(
        id=str(uuid.uuid4())[:8],
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        estimated_hours=total_hours,
        category=payload.category,
        status="active",
        subtasks=subtasks,
        created_at=datetime.utcnow().isoformat()
    )
    
    # Save to Firestore
    firestore_service.create_deadline(deadline)
    return deadline

@router.get("", response_model=List[Deadline])
def list_deadlines(user_id: str = Depends(get_current_user_id)):
    return firestore_service.get_user_deadlines(user_id)

@router.get("/{id}", response_model=Deadline)
def get_deadline(id: str):
    deadline = firestore_service.get_deadline(id)
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
    return deadline

@router.delete("/{id}")
def delete_deadline(id: str):
    deadline = firestore_service.get_deadline(id)
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
    firestore_service.delete_deadline(id)
    return {"message": "Deadline successfully deleted"}

@router.patch("/{id}/subtasks/{subtask_id}", response_model=Deadline)
def update_subtask_status(id: str, subtask_id: str, payload: SubTaskUpdate):
    deadline = firestore_service.get_deadline(id)
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
        
    subtask_found = False
    for sub in deadline.subtasks:
        if sub.id == subtask_id:
            sub.status = payload.status
            subtask_found = True
            break
            
    if not subtask_found:
        raise HTTPException(status_code=404, detail="Subtask not found")
        
    # Check if all subtasks are done
    all_done = all(sub.status == "done" for sub in deadline.subtasks)
    if all_done:
        deadline.status = "completed"
    else:
        # If it was completed/panicked and a subtask is reopened, revert to active
        if deadline.status == "completed":
            deadline.status = "active"
            
    firestore_service.update_deadline(deadline)
    return deadline
