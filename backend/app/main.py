from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routes import deadlines, schedule, recovery

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Intelligent planning, scheduling, and panic-mode triage for deadlines.",
    version="1.0.0"
)

# CORS Configuration for Frontend Connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, narrow this down to your frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Router Modules
app.include_router(deadlines.router)
app.include_router(schedule.router)
app.include_router(recovery.router)

@app.get("/")
def read_root():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "message": "AI-powered productivity life saver backend is running."
    }
