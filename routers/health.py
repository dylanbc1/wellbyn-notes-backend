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
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "huggingface_configured": hf_configured,
        "model_type": "local",  # Using local Whisper model
        "database": "connected"
    }

