"""
Notes API - Main Application
FastAPI backend for audio transcription
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import time

from config import settings
from database import init_db
from routers import transcription_router, health_router, ehr_router, auth_router

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle events
    """
    import os
    import sys
    
    # Startup
    logger.info("=" * 50)
    logger.info("LIFESPAN: Starting Notes API...")
    logger.info("=" * 50)
    logger.info(f"Version: {settings.APP_VERSION}")
    logger.info(f"Model: {settings.DEFAULT_MODEL}")
    logger.info(f"Host: {settings.HOST}")
    logger.info(f"Port: {settings.PORT}")
    logger.info(f"Database URL: {settings.DATABASE_URL[:50]}...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"PORT env var: {os.getenv('PORT', 'NOT_SET')}")
    logger.info(f"CORS Allowed Origins: {settings.ALLOWED_ORIGINS}")
    logger.info(f"ALLOWED_ORIGINS env var: {os.getenv('ALLOWED_ORIGINS', 'NOT_SET')}")
    
    # Initialize database (non-blocking)
    logger.info("LIFESPAN: Initializing database...")
    try:
        init_db()
        logger.info("LIFESPAN: Database ready ✅")
    except Exception as e:
        logger.error(f"LIFESPAN: Error initializing database: {e}")
        logger.warning("LIFESPAN: Application will continue, but database operations may fail")
        # Don't raise - allow app to start even if DB init fails
        # This allows health check to work and logs to be visible
    
    logger.info("LIFESPAN: Application startup complete ✅")
    logger.info("LIFESPAN: Entering runtime phase...")
    logger.info("=" * 50)
    
    yield
    
    # Shutdown
    logger.info("=" * 50)
    logger.info("LIFESPAN: Shutting down Notes API...")
    logger.info("=" * 50)


# Create application
app = FastAPI(
    title=settings.APP_NAME,
    description="Audio transcription API with AI",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
logger.info(f"CORS: Allowed origins: {settings.ALLOWED_ORIGINS}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Middleware para logging de requests
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        logger.info(f"REQUEST: {request.method} {request.url.path} from {client_ip}")
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"RESPONSE: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s")
        return response

app.add_middleware(LoggingMiddleware)

# Register routers
logger.info("Registering routers...")
app.include_router(health_router)
logger.info("✓ Health router registered")
app.include_router(auth_router)
logger.info("✓ Auth router registered")
app.include_router(transcription_router)
logger.info("✓ Transcription router registered")
app.include_router(ehr_router)
logger.info("✓ EHR router registered")
logger.info("All routers registered successfully ✅")


# Root endpoint (simple check)
@app.get("/")
def root():
    """Simple root endpoint"""
    return {
        "status": "ok",
        "message": "Wellbyn Notes API is running",
        "version": settings.APP_VERSION
    }


if __name__ == "__main__":
    import uvicorn
    
    print(f"\nServer: http://{settings.HOST}:{settings.PORT}")
    print(f"Docs: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"ReDoc: http://{settings.HOST}:{settings.PORT}/redoc\n")
    
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level="info"
    )

