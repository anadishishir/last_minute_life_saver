from pydantic import BaseModel, Field
from typing import Optional

class UserProfile(BaseModel):
    uid: str = Field(..., description="Unique identifier for the user")
    name: str = Field(..., description="User's display name")
    working_hours_start: str = Field(default="09:00", description="Preferred work day start time (24h format HH:MM)")
    working_hours_end: str = Field(default="18:00", description="Preferred work day end time (24h format HH:MM)")
    energy_profile: str = Field(default="consistent", description="Energy pattern: morning_person | night_owl | consistent")
    stress_handling: str = Field(default="break_into_tiny_steps", description="Style: break_into_tiny_steps | deep_focus_blocks")

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    working_hours_start: Optional[str] = None
    working_hours_end: Optional[str] = None
    energy_profile: Optional[str] = None
    stress_handling: Optional[str] = None
