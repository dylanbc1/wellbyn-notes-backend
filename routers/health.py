"""
Health check endpoints
"""

from fastapi import APIRouter, Request
from config import settings
import time
import logging

router = APIRouter(prefix="/api", tags=["Health"])
logger = logging.getLogger(__name__)


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
def health_check(request: Request):
    """
    Health check endpoint
    """
    import os
    
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"HEALTH CHECK: Request from {client_ip} at {time.time()}")
    logger.info(f"HEALTH CHECK: PORT env var = {os.getenv('PORT', 'NOT_SET')}")
    logger.info(f"HEALTH CHECK: Settings.PORT = {settings.PORT}")
    
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
        logger.info("HEALTH CHECK: Database connection OK ✅")
    except Exception as e:
        db_status = f"error: {str(e)[:50]}"
        logger.warning(f"HEALTH CHECK: Database connection failed: {e}")
    
    response = {
        "status": "healthy",
        "timestamp": time.time(),
        "huggingface_configured": hf_configured,
        "model_type": "local",  # Using local Whisper model
        "database": db_status,
        "port": settings.PORT,
        "port_env": os.getenv("PORT", "NOT_SET")
    }
    
    logger.info(f"HEALTH CHECK: Returning response: {response}")
    return response

