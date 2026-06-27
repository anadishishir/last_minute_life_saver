from pydantic import BaseModel, Field
from typing import List, Optional
from .deadline import SubTask

class PanicRequest(BaseModel):
    current_time: str = Field(..., description="Current ISO timestamp at point of panic")
    lost_hours: float = Field(default=0.0, description="Hours lost or amount of delay to account for")
    custom_panic_reason: Optional[str] = Field(default=None, description="Why the user got behind (e.g., got stuck, distracted)")

class RecoveryPlan(BaseModel):
    generated_at: str = Field(..., description="ISO timestamp when recovery plan was calculated")
    triage_strategy: str = Field(..., description="AI description of the shortcut/triage strategies applied")
    rearranged_subtasks: List[SubTask] = Field(..., description="Updated subtask list with adjusted timelines and truncated deliverables")
    motivation_tip: str = Field(..., description="Gemini-styled motivational focus boost")
