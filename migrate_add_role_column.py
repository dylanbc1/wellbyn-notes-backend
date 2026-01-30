"""
Script de migración para agregar columna role a la tabla users
"""

from database import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """Agrega la columna role a la tabla users"""
    logger.info("Iniciando migración para agregar columna 'role'...")
    
    try:
        with engine.connect() as conn:
            # Verificar si la columna ya existe
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='role'
            """))
            
            if result.fetchone():
                logger.info("✅ La columna 'role' ya existe")
                return
            
            # Eliminar tipo ENUM si existe (para recrearlo)
            logger.info("Verificando/creando tipo ENUM userrole...")
            conn.execute(text("""
                DROP TYPE IF EXISTS userrole CASCADE;
            """))
            conn.commit()
            
            # Crear tipo ENUM con los valores correctos
            conn.execute(text("""
                CREATE TYPE userrole AS ENUM ('doctor', 'administrator');
            """))
            conn.commit()
            
            # Agregar columna role con valor por defecto
            logger.info("Agregando columna 'role'...")
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN role userrole NOT NULL DEFAULT 'doctor';
            """))
            conn.commit()
            
            logger.info("✅ Migración completada exitosamente")
            logger.info("   Columna 'role' agregada a la tabla 'users'")
            
    except Exception as e:
        logger.error(f"❌ Error en la migración: {e}")
        raise


if __name__ == "__main__":
    migrate()
