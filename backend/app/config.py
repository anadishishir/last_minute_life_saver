import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Last-Minute Life Saver"
    GEMINI_API_KEY: Optional[str] = None
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    FIRESTORE_PROJECT_ID: Optional[str] = None
    USE_MOCK_DB: bool = False
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Ensure we read environment variables directly if dotenv file is missing
if not settings.GEMINI_API_KEY:
    settings.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not settings.FIREBASE_CREDENTIALS_PATH:
    settings.FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")

if not settings.FIRESTORE_PROJECT_ID:
    settings.FIRESTORE_PROJECT_ID = os.getenv("FIRESTORE_PROJECT_ID")
