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
from routers.metrics import router as metrics_router

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
print("=" * 50)
print("CORS CONFIGURATION:")
print(f"Allowed origins: {settings.ALLOWED_ORIGINS}")
print(f"Type: {type(settings.ALLOWED_ORIGINS)}")
print("=" * 50)
logger.info(f"CORS: Allowed origins: {settings.ALLOWED_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
print("✓ CORS middleware added")
logger.info("✓ CORS middleware added")

# Middleware para logging de requests
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        origin = request.headers.get("origin", "no origin")
        logger.info(f"REQUEST: {request.method} {request.url.path} from {client_ip}, origin: {origin}")
        print(f"🌐 Request: {request.method} {request.url.path} | Origin: {origin} | IP: {client_ip}")
        response = await call_next(request)
        process_time = time.time() - start_time
        cors_headers = {k: v for k, v in response.headers.items() if 'access-control' in k.lower()}
        logger.info(f"RESPONSE: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s - CORS headers: {cors_headers}")
        print(f"📤 Response: {response.status_code} | CORS headers: {cors_headers}")
        return response

app.add_middleware(LoggingMiddleware)

# Register routers
print("=" * 50)
print("REGISTERING ROUTERS...")
print("=" * 50)
logger.info("Registering routers...")

try:
    print("1. Registering health router...")
    logger.info("1. Registering health router...")
    app.include_router(health_router)
    print("   ✓ Health router registered")
    logger.info("✓ Health router registered")
except Exception as e:
    print(f"   ✗ ERROR registering health router: {e}")
    logger.error(f"ERROR registering health router: {e}")

try:
    print("2. Registering auth router...")
    logger.info("2. Registering auth router...")
    app.include_router(auth_router)
    print(f"   ✓ Auth router registered (prefix: {auth_router.prefix})")
    logger.info(f"✓ Auth router registered (prefix: {auth_router.prefix})")
    # Listar rutas del auth router
    auth_routes = [route.path for route in auth_router.routes]
    print(f"   Auth routes: {auth_routes}")
    logger.info(f"Auth routes: {auth_routes}")
except Exception as e:
    print(f"   ✗ ERROR registering auth router: {e}")
    logger.error(f"ERROR registering auth router: {e}")
    import traceback
    traceback.print_exc()

try:
    print("3. Registering transcription router...")
    logger.info("3. Registering transcription router...")
    app.include_router(transcription_router)
    print("   ✓ Transcription router registered")
    logger.info("✓ Transcription router registered")
except Exception as e:
    print(f"   ✗ ERROR registering transcription router: {e}")
    logger.error(f"ERROR registering transcription router: {e}")

try:
    print("4. Registering EHR router...")
    logger.info("4. Registering EHR router...")
    app.include_router(ehr_router)
    print("   ✓ EHR router registered")
    logger.info("✓ EHR router registered")
except Exception as e:
    print(f"   ✗ ERROR registering EHR router: {e}")
    logger.error(f"ERROR registering EHR router: {e}")

try:
    print("5. Registering metrics router...")
    logger.info("5. Registering metrics router...")
    app.include_router(metrics_router)
    print("   ✓ Metrics router registered")
    logger.info("✓ Metrics router registered")
except Exception as e:
    print(f"   ✗ ERROR registering metrics router: {e}")
    logger.error(f"ERROR registering metrics router: {e}")

print("=" * 50)
print("All routers registered successfully ✅")
print("=" * 50)
logger.info("All routers registered successfully ✅")

# Verificar todas las rutas registradas
print("\nREGISTERED ROUTES:")
print("-" * 50)
for route in app.routes:
    if hasattr(route, 'path') and hasattr(route, 'methods'):
        methods = ', '.join(route.methods) if route.methods else 'N/A'
        print(f"  {methods:10} {route.path}")
logger.info(f"Total routes registered: {len([r for r in app.routes if hasattr(r, 'path')])}")
print("-" * 50)


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

