"""
Migration script para agregar tablas de EHR
Ejecutar: python migrate_add_ehr_tables.py
"""

from database import engine, Base
from models import Transcription, EHRConnection, EHRSync
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """
    Crea las tablas de EHR si no existen
    """
    logger.info("Creating EHR tables...")
    
    try:
        # Crear solo las tablas de EHR (las otras ya existen)
        EHRConnection.__table__.create(bind=engine, checkfirst=True)
        EHRSync.__table__.create(bind=engine, checkfirst=True)
        
        logger.info("✓ EHR tables created successfully")
    except Exception as e:
        logger.error(f"Error creating EHR tables: {e}")
        raise


if __name__ == "__main__":
    migrate()
