"""
Routers package - Versión Demo
"""

from routers.transcription import router as transcription_router
from routers.health import router as health_router
from routers.ehr import router as ehr_router
from routers.auth import router as auth_router

__all__ = ["transcription_router", "health_router", "ehr_router", "auth_router"]

