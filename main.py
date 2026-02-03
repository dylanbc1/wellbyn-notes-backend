"""
Notes API - Main Application
FastAPI backend for audio transcription
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

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
    # Startup
    logger.info("Starting Notes API...")
    logger.info(f"Version: {settings.APP_VERSION}")
    logger.info(f"Model: {settings.DEFAULT_MODEL}")
    logger.info(f"Database URL: {settings.DATABASE_URL}")
    
    # Initialize database (non-blocking)
    logger.info("Initializing database...")
    try:
        init_db()
        logger.info("Database ready")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        logger.warning("Application will continue, but database operations may fail")
        # Don't raise - allow app to start even if DB init fails
        # This allows health check to work and logs to be visible
    
    yield
    
    # Shutdown
    logger.info("Shutting down Notes API...")


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(transcription_router)
app.include_router(ehr_router)


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

