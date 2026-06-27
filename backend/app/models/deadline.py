from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class SubTask(BaseModel):
    id: str = Field(..., description="Unique subtask identifier")
    title: str = Field(..., description="Actionable title for the subtask")
    duration_hours: float = Field(..., description="Estimated hours to complete")
    importance: int = Field(default=2, ge=1, le=3, description="Priority weight (1 = Low, 2 = Medium, 3 = High)")
    status: str = Field(default="todo", description="Status: todo | in_progress | done")
    scheduled_start: Optional[str] = Field(default=None, description="ISO datetime string for scheduled start")
    scheduled_end: Optional[str] = Field(default=None, description="ISO datetime string for scheduled end")

class Deadline(BaseModel):
    id: str = Field(..., description="Unique deadline identifier")
    user_id: str = Field(..., description="Associated user ID")
    title: str = Field(..., description="Title of the goal/deadline")
    description: str = Field(..., description="Detailed description")
    due_date: str = Field(..., description="Target ISO datetime string")
    estimated_hours: float = Field(..., description="Total estimated hours")
    category: str = Field(default="study", description="Category: work | study | personal")
    status: str = Field(default="active", description="Status: active | completed | panicked")
    subtasks: List[SubTask] = Field(default=[], description="Decomposed AI-generated subtasks")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="ISO timestamp of creation")

class DeadlineCreate(BaseModel):
    title: str = Field(..., example="Complete Machine Learning Project")
    description: str = Field(..., example="Write training pipeline, evaluate model and prepare final report.")
    due_date: str = Field(..., example="2026-06-30T18:00:00")
    estimated_hours: Optional[float] = Field(default=None, description="User estimate, Gemini will refine if omitted")
    category: str = Field(default="study", example="study")

class SubTaskUpdate(BaseModel):
    status: str = Field(..., example="in_progress")
