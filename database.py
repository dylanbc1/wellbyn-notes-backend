"""
Configuración de base de datos con SQLAlchemy
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

# Engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()


def get_db():
    """
    Dependency para obtener sesión de BD
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Inicializar base de datos (crear tablas)
    """
    try:
        from sqlalchemy import text
        # Test connection first
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        # Import models to register them
        import models
        
        # Create tables
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Database initialization error: {e}")
        # Re-raise to let caller handle it
        raise

