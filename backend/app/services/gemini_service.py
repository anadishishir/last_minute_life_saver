import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel, Field

# Try importing the new Google GenAI SDK
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from ..config import settings
from ..models.user import UserProfile
from ..models.deadline import SubTask, Deadline
from ..models.recovery import RecoveryPlan

logger = logging.getLogger("gemini_service")
logging.basicConfig(level=logging.INFO)

# Define schemas for Gemini structured outputs
class GeminiSubTask(BaseModel):
    title: str = Field(..., description="Actionable title for the subtask")
    duration_hours: float = Field(..., description="Estimated hours to complete (minimum 0.5)")
    importance: int = Field(..., description="Priority weighting: 1 (low) to 3 (critical)")

class GeminiDecomposeResponse(BaseModel):
    suggested_total_hours: float = Field(..., description="Refined estimate of total hours required")
    subtasks: List[GeminiSubTask] = Field(..., description="Decomposed list of subtasks in logical order")

class GeminiScheduledSubTask(BaseModel):
    title: str
    duration_hours: float
    importance: int
    scheduled_start: str = Field(..., description="ISO 8601 start timestamp in user's timezone")
    scheduled_end: str = Field(..., description="ISO 8601 end timestamp in user's timezone")

class GeminiScheduleResponse(BaseModel):
    scheduled_tasks: List[GeminiScheduledSubTask] = Field(..., description="List of tasks with assigned time slots")

class GeminiRecoveryResponse(BaseModel):
    triage_strategy: str = Field(..., description="Description of changes (e.g. what is cut down, automated, or postponed)")
    motivation_tip: str = Field(..., description="A short, high-energy motivational punchy focus boost")
    rearranged_tasks: List[GeminiScheduledSubTask] = Field(..., description="Updated schedule with trimmed task durations and slots")


class GeminiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.client = None
        
        if GENAI_AVAILABLE and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
                logger.info("✨ Gemini Client successfully initialized.")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Gemini client: {e}")
        else:
            if not GENAI_AVAILABLE:
                logger.warning("⚠️ google-genai library is not installed. Using mock Gemini service.")
            if not self.api_key:
                logger.warning("⚠️ GEMINI_API_KEY is not set. Using mock Gemini service.")

    def decompose_deadline(self, title: str, description: str, due_date: str, estimated_hours: Optional[float], user_profile: UserProfile) -> GeminiDecomposeResponse:
        """Decomposes a deadline description into structured, sequential subtasks."""
        if not self.client:
            return self._mock_decompose(title, description, estimated_hours)

        prompt = f"""
        Objective: Decompose the following project goal into a logical, sequential checklist of subtasks.
        
        Goal: "{title}"
        Description: "{description}"
        Target Deadline: {due_date}
        User Preference: {user_profile.stress_handling} (e.g., break into tiny steps vs. deep blocks)
        Original User Hours Estimate: {estimated_hours or "Not provided"}

        Guidelines:
        1. Break this task into 4-8 distinct subtasks.
        2. Assign a duration (in hours) to each subtask. If the original estimate is provided, try to align the sum of subtasks close to it, but adjust if it's unrealistic.
        3. Weight each subtask by importance (1 = low, 2 = medium, 3 = critical/non-negotiable).
        4. Sort them in chronological order of implementation.
        """
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiDecomposeResponse,
                    temperature=0.2
                ),
            )
            data = json.loads(response.text)
            return GeminiDecomposeResponse(**data)
        except Exception as e:
            logger.error(f"Error calling Gemini decompose: {e}. Falling back to mock.")
            return self._mock_decompose(title, description, estimated_hours)

    def schedule_subtasks(self, subtasks: List[SubTask], due_date_str: str, user_profile: UserProfile, start_time_str: Optional[str] = None) -> GeminiScheduleResponse:
        """Schedules subtasks chronologically fitting inside the user's preferred working hours, avoiding sleep time."""
        if not self.client:
            return self._mock_schedule(subtasks, due_date_str, user_profile, start_time_str)

        start_time = start_time_str or datetime.utcnow().isoformat()
        
        subtasks_data = [{"title": t.title, "duration_hours": t.duration_hours, "importance": t.importance} for t in subtasks]
        
        prompt = f"""
        Objective: Schedule the following tasks chronologically, placing them in valid working windows leading up to the deadline.
        
        Current Time (Start of Scheduling): {start_time}
        Final Deadline: {due_date_str}
        
        User Working Profile:
        - Daily Working Hours: {user_profile.working_hours_start} to {user_profile.working_hours_end}
        - Peak Energy Profile: {user_profile.energy_profile} (e.g. morning_person, night_owl, consistent)
        
        Tasks to Schedule:
        {json.dumps(subtasks_data, indent=2)}
        
        Rules:
        1. Only schedule work during the user's working hours ({user_profile.working_hours_start} to {user_profile.working_hours_end}).
        2. Do not schedule work during sleep or off-hours unless the deadline is extremely urgent.
        3. Prioritize higher importance tasks (importance=3) earlier or during peak energy periods (morning if morning_person, evening if night_owl).
        4. Tasks must not overlap. The end of one task should precede or align with the start of the next.
        5. Return the tasks with precise ISO 8601 start and end timestamps.
        """
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiScheduleResponse,
                    temperature=0.2
                ),
            )
            data = json.loads(response.text)
            return GeminiScheduleResponse(**data)
        except Exception as e:
            logger.error(f"Error calling Gemini schedule: {e}. Falling back to mock.")
            return self._mock_schedule(subtasks, due_date_str, user_profile, start_time_str)

    def generate_recovery_plan(self, deadline: Deadline, current_time_str: str, lost_hours: float, custom_panic_reason: Optional[str], user_profile: UserProfile) -> GeminiRecoveryResponse:
        """Generates a compressed triage plan and reschedules remaining tasks when the user panics or gets off track."""
        if not self.client:
            return self._mock_recovery(deadline, current_time_str, lost_hours, custom_panic_reason, user_profile)

        # Filter remaining incomplete subtasks
        remaining_tasks = [t for t in deadline.subtasks if t.status != "done"]
        completed_tasks = [t for t in deadline.subtasks if t.status == "done"]
        
        remaining_data = [{"title": t.title, "duration_hours": t.duration_hours, "importance": t.importance} for t in remaining_tasks]
        
        prompt = f"""
        PANIC MODE TRIGGERED! The user is falling behind on their deadline.
        
        Goal: "{deadline.title}"
        Final Deadline: {deadline.due_date}
        Current Time: {current_time_str}
        Lost / Wasted Hours: {lost_hours} hours
        Reason for Delay: {custom_panic_reason or "Unknown / general delay"}
        
        User Working Profile:
        - Daily Working Hours: {user_profile.working_hours_start} to {user_profile.working_hours_end}
        - Stress Coping Preference: {user_profile.stress_handling}
        
        Remaining Incomplete Tasks:
        {json.dumps(remaining_data, indent=2)}
        
        Goal: 
        1. Formulate a Triage Strategy. Identify shortcuts, what deliverables to simplify/trim, or what tasks to split or postpone.
        2. Adjust Task Durations. Trim durations for the remaining tasks (especially lower importance ones) to fit them into the remaining time before the deadline.
        3. Reschedule the remaining tasks starting immediately from {current_time_str} up to the deadline, respecting the user's working hours. If time is extremely tight, you may extend working hours into the evening, but explain this in the triage strategy.
        4. Provide an ultra-short, highly motivating focus tip to calm stress.
        """
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiRecoveryResponse,
                    temperature=0.3
                ),
            )
            data = json.loads(response.text)
            return GeminiRecoveryResponse(**data)
        except Exception as e:
            logger.error(f"Error calling Gemini recovery: {e}. Falling back to mock.")
            return self._mock_recovery(deadline, current_time_str, lost_hours, custom_panic_reason, user_profile)

    # --- OFFLINE / MOCK GENERATORS FOR EXCELLENT DX ---

    def _mock_decompose(self, title: str, description: str, estimated_hours: Optional[float]) -> GeminiDecomposeResponse:
        logger.info("Generating mock subtask decomposition.")
        hours = estimated_hours or 6.0
        
        subtask_titles = [
            f"Research and planning for {title}",
            "Drafting outline and core structure",
            "Core implementation / content creation",
            "Refinement and review",
            "Final submission details and wrap-up"
        ]
        
        subtasks = []
        each_hour = round(hours / len(subtask_titles), 1)
        if each_hour < 0.5:
            each_hour = 0.5
            
        for i, t in enumerate(subtask_titles):
            importance = 3 if i in (0, 2) else (2 if i == 1 else 1)
            subtasks.append(GeminiSubTask(
                title=t,
                duration_hours=each_hour,
                importance=importance
            ))
            
        return GeminiDecomposeResponse(
            suggested_total_hours=sum(s.duration_hours for s in subtasks),
            subtasks=subtasks
        )

    def _mock_schedule(self, subtasks: List[SubTask], due_date_str: str, user_profile: UserProfile, start_time_str: Optional[str] = None) -> GeminiScheduleResponse:
        logger.info("Generating mock schedule.")
        start_dt = datetime.fromisoformat(start_time_str) if start_time_str else datetime.utcnow()
        due_dt = datetime.fromisoformat(due_date_str)
        
        scheduled = []
        current_cursor = start_dt + timedelta(minutes=15) # Start in 15 mins
        
        # Parse user working hours
        try:
            start_hour, start_min = map(int, user_profile.working_hours_start.split(":"))
            end_hour, end_min = map(int, user_profile.working_hours_end.split(":"))
        except Exception:
            start_hour, start_min = 9, 0
            end_hour, end_min = 18, 0
            
        for task in subtasks:
            # Check if current cursor is within working hours
            if current_cursor.hour >= end_hour or current_cursor.hour < start_hour:
                # Move to next day start
                if current_cursor.hour >= end_hour:
                    current_cursor = current_cursor + timedelta(days=1)
                current_cursor = current_cursor.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
                
            task_duration = timedelta(hours=task.duration_hours)
            end_dt = current_cursor + task_duration
            
            # If it overflows the work day, split or push
            if end_dt.hour > end_hour or (end_dt.hour == end_hour and end_dt.minute > end_min):
                # For mock, just extend or schedule it anyway but limit it
                pass
                
            # If it overflows the final deadline, cap it
            if end_dt > due_dt:
                end_dt = due_dt
                if current_cursor > due_dt:
                    current_cursor = due_dt - timedelta(minutes=30)
            
            scheduled.append(GeminiScheduledSubTask(
                title=task.title,
                duration_hours=task.duration_hours,
                importance=task.importance,
                scheduled_start=current_cursor.isoformat(),
                scheduled_end=end_dt.isoformat()
            ))
            
            current_cursor = end_dt + timedelta(minutes=10) # 10 min break
            
        return GeminiScheduleResponse(scheduled_tasks=scheduled)

    def _mock_recovery(self, deadline: Deadline, current_time_str: str, lost_hours: float, custom_panic_reason: Optional[str], user_profile: UserProfile) -> GeminiRecoveryResponse:
        logger.info("Generating mock recovery plan.")
        remaining = [t for t in deadline.subtasks if t.status != "done"]
        
        # Trim durations by 30% for mock recovery
        rearranged = []
        cursor = datetime.fromisoformat(current_time_str)
        due_dt = datetime.fromisoformat(deadline.due_date)
        
        for task in remaining:
            trimmed_duration = max(0.5, round(task.duration_hours * 0.7, 1))
            end_dt = cursor + timedelta(hours=trimmed_duration)
            if end_dt > due_dt:
                end_dt = due_dt
                
            rearranged.append(GeminiScheduledSubTask(
                title=f"⚡ CAPPED: {task.title}",
                duration_hours=trimmed_duration,
                importance=task.importance,
                scheduled_start=cursor.isoformat(),
                scheduled_end=end_dt.isoformat()
            ))
            cursor = end_dt + timedelta(minutes=5)
            
        triage_strategy = (
            f"Panic triggered due to: '{custom_panic_reason or 'Time crunch'}'. "
            f"We have applied a 30% duration reduction to all remaining subtasks. "
            f"Focus on minimum viable deliverables. Skip heavy aesthetics/extra features."
        )
        motivation_tip = "Breathe in. Exhale. Focus only on the active task. You've got this, one small block at a time!"
        
        return GeminiRecoveryResponse(
            triage_strategy=triage_strategy,
            motivation_tip=motivation_tip,
            rearranged_tasks=rearranged
        )

# Singleton instance
gemini_service = GeminiService()
