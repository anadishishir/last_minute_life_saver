import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from ..config import settings
from ..models.user import UserProfile
from ..models.deadline import Deadline

logger = logging.getLogger("firestore_service")
logging.basicConfig(level=logging.INFO)

# Make firebase-admin optional
FIREBASE_AVAILABLE = False
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ firebase-admin package is not installed. Firestore database connection is disabled.")

class InMemoryMockDB:
    """Fallback DB used when Firestore credentials are not supplied."""
    def __init__(self):
        self.users: Dict[str, Dict[str, Any]] = {
            "default_user": {
                "uid": "default_user",
                "name": "Ninjaneer",
                "working_hours_start": "09:00",
                "working_hours_end": "18:00",
                "energy_profile": "morning_person",
                "stress_handling": "break_into_tiny_steps"
            }
        }
        self.deadlines: Dict[str, Dict[str, Any]] = {}
        logger.warning("⚠️ Using in-memory Mock Firestore. Data will NOT persist between server restarts.")

class FirestoreService:
    def __init__(self):
        self.db = None
        self.mock_db = None
        
        # Check if we should initialize Firebase
        cred_path = settings.FIREBASE_CREDENTIALS_PATH
        project_id = settings.FIRESTORE_PROJECT_ID
        
        if settings.USE_MOCK_DB or not FIREBASE_AVAILABLE:
            self.mock_db = InMemoryMockDB()
            if not FIREBASE_AVAILABLE and not settings.USE_MOCK_DB:
                logger.info("ℹ️ firebase-admin is not installed. Initializing in-memory mock database.")
            return

        if cred_path and os.path.exists(cred_path):
            try:
                # Initialize Firebase App if not already initialized
                try:
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                except ValueError:
                    # App already initialized
                    pass
                self.db = firestore.client()
                logger.info("🔥 Firestore client initialized using credentials file.")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Firestore with service account: {e}")
                self.mock_db = InMemoryMockDB()
        elif project_id:
            try:
                try:
                    firebase_admin.initialize_app(options={'projectId': project_id})
                except ValueError:
                    pass
                self.db = firestore.client()
                logger.info(f"🔥 Firestore client initialized using Project ID: {project_id}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Firestore with Project ID: {e}")
                self.mock_db = InMemoryMockDB()
        else:
            logger.info("ℹ️ No Firestore credentials found in environment. Initializing in-memory mock database.")
            self.mock_db = InMemoryMockDB()

    def get_user_profile(self, uid: str) -> UserProfile:
        if self.mock_db:
            user_data = self.mock_db.users.get(uid)
            if not user_data:
                # Create a default user profile dynamically
                user_data = {
                    "uid": uid,
                    "name": "Ninjaneer",
                    "working_hours_start": "09:00",
                    "working_hours_end": "18:00",
                    "energy_profile": "morning_person",
                    "stress_handling": "break_into_tiny_steps"
                }
                self.mock_db.users[uid] = user_data
            return UserProfile(**user_data)
        
        # Real firestore implementation
        doc_ref = self.db.collection("users").document(uid)
        doc = doc_ref.get()
        if doc.exists:
            return UserProfile(**doc.to_dict())
        else:
            # Create a default
            default_profile = UserProfile(
                uid=uid,
                name="Ninjaneer",
                working_hours_start="09:00",
                working_hours_end="18:00",
                energy_profile="morning_person",
                stress_handling="break_into_tiny_steps"
            )
            self.update_user_profile(uid, default_profile)
            return default_profile

    def update_user_profile(self, uid: str, profile: UserProfile) -> None:
        profile_dict = profile.model_dump()
        if self.mock_db:
            self.mock_db.users[uid] = profile_dict
            return
        
        doc_ref = self.db.collection("users").document(uid)
        doc_ref.set(profile_dict)

    def get_deadline(self, deadline_id: str) -> Optional[Deadline]:
        if self.mock_db:
            data = self.mock_db.deadlines.get(deadline_id)
            return Deadline(**data) if data else None
        
        doc_ref = self.db.collection("deadlines").document(deadline_id)
        doc = doc_ref.get()
        if doc.exists:
            return Deadline(**doc.to_dict())
        return None

    def get_user_deadlines(self, user_id: str) -> List[Deadline]:
        if self.mock_db:
            return [Deadline(**d) for d in self.mock_db.deadlines.values() if d.get("user_id") == user_id]
        
        docs = self.db.collection("deadlines").where("user_id", "==", user_id).stream()
        return [Deadline(**doc.to_dict()) for doc in docs]

    def create_deadline(self, deadline: Deadline) -> None:
        data = deadline.model_dump()
        if self.mock_db:
            self.mock_db.deadlines[deadline.id] = data
            return
        
        doc_ref = self.db.collection("deadlines").document(deadline.id)
        doc_ref.set(data)

    def update_deadline(self, deadline: Deadline) -> None:
        data = deadline.model_dump()
        if self.mock_db:
            self.mock_db.deadlines[deadline.id] = data
            return
        
        doc_ref = self.db.collection("deadlines").document(deadline.id)
        doc_ref.set(data)

    def delete_deadline(self, deadline_id: str) -> None:
        if self.mock_db:
            self.mock_db.deadlines.pop(deadline_id, None)
            return
        
        doc_ref = self.db.collection("deadlines").document(deadline_id)
        doc_ref.delete()

# Singleton instance
firestore_service = FirestoreService()
