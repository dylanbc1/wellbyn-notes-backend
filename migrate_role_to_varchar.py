"""
Script de migración para cambiar columna role de ENUM a VARCHAR
"""

from database import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """Cambia la columna role de ENUM a VARCHAR"""
    logger.info("Iniciando migración para cambiar columna 'role' a VARCHAR...")
    
    try:
        with engine.connect() as conn:
            # Verificar si la columna existe y su tipo actual
            result = conn.execute(text("""
                SELECT data_type, udt_name
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='role'
            """))
            
            row = result.fetchone()
            if not row:
                logger.error("❌ La columna 'role' no existe")
                return
            
            logger.info(f"Tipo actual de 'role': {row[0]} ({row[1]})")
            
            # Si ya es VARCHAR, no hacer nada
            if row[0] == 'character varying' or row[0] == 'varchar':
                logger.info("✅ La columna 'role' ya es VARCHAR")
                return
            
            # Cambiar de ENUM a VARCHAR
            logger.info("Cambiando columna 'role' de ENUM a VARCHAR...")
            
            # Primero, cambiar el tipo a VARCHAR temporalmente
            conn.execute(text("""
                ALTER TABLE users 
                ALTER COLUMN role TYPE VARCHAR(20) USING role::text;
            """))
            conn.commit()
            
            logger.info("✅ Migración completada exitosamente")
            logger.info("   Columna 'role' ahora es VARCHAR(20)")
            
    except Exception as e:
        logger.error(f"❌ Error en la migración: {e}")
        raise


if __name__ == "__main__":
    migrate()
