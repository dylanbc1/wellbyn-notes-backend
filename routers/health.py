"""
Health check endpoints
"""

from fastapi import APIRouter
from config import settings
import time

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/")
def root():
    """Root endpoint"""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "endpoints": {
            "health": "GET /api/health",
            "transcribe": "POST /api/transcriptions/transcribe",
            "transcriptions": "GET /api/transcriptions",
            "docs": "GET /docs"
        }
    }


@router.get("/health")
def health_check():
    """
    Health check endpoint
    """
    # HF_TOKEN is optional since we use local models
    hf_configured = bool(settings.HF_TOKEN and settings.HF_TOKEN.strip())
    
    # Check database connection
    db_status = "unknown"
    try:
        from database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)[:50]}"
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "huggingface_configured": hf_configured,
        "model_type": "local",  # Using local Whisper model
        "database": db_status
    }

