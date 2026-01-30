"""
Script de migración para agregar tablas de usuarios y sesiones
"""

from database import init_db, engine
from models.user import User, Session
from models.transcription import Transcription
from models.ehr_connection import EHRConnection, EHRSync
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """Crea las tablas de usuarios y sesiones"""
    logger.info("Iniciando migración...")
    
    try:
        # Importar todos los modelos para que SQLAlchemy los reconozca
        from models import User, Session, Transcription, EHRConnection, EHRSync
        
        # Crear todas las tablas
        logger.info("Creando tablas...")
        init_db()
        
        logger.info("✅ Migración completada exitosamente")
        logger.info("Tablas creadas:")
        logger.info("  - users")
        logger.info("  - sessions")
        logger.info("  - transcriptions (si no existía)")
        logger.info("  - ehr_connections (si no existía)")
        logger.info("  - ehr_syncs (si no existía)")
        
    except Exception as e:
        logger.error(f"❌ Error en la migración: {e}")
        raise


if __name__ == "__main__":
    migrate()
