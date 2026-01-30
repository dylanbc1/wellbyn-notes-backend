"""
Script de migración para agregar columnas del workflow médico
Ejecuta este script una vez para actualizar la base de datos
"""

from sqlalchemy import text
from database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_database():
    """
    Agrega las columnas del workflow médico a la tabla transcriptions
    """
    try:
        with engine.connect() as conn:
            # Verificar si las columnas ya existen
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'transcriptions' 
                AND column_name IN ('medical_note', 'icd10_codes', 'cpt_codes', 'cms1500_form_data', 'workflow_status')
            """)
            
            existing_columns = [row[0] for row in conn.execute(check_query)]
            logger.info(f"Columnas existentes: {existing_columns}")
            
            # Agregar medical_note si no existe
            if 'medical_note' not in existing_columns:
                logger.info("Agregando columna medical_note...")
                conn.execute(text("""
                    ALTER TABLE transcriptions 
                    ADD COLUMN medical_note TEXT
                """))
                conn.commit()
                logger.info("✓ Columna medical_note agregada")
            else:
                logger.info("✓ Columna medical_note ya existe")
            
            # Agregar icd10_codes si no existe
            if 'icd10_codes' not in existing_columns:
                logger.info("Agregando columna icd10_codes...")
                conn.execute(text("""
                    ALTER TABLE transcriptions 
                    ADD COLUMN icd10_codes JSONB
                """))
                conn.commit()
                logger.info("✓ Columna icd10_codes agregada")
            else:
                logger.info("✓ Columna icd10_codes ya existe")
            
            # Agregar cpt_codes si no existe
            if 'cpt_codes' not in existing_columns:
                logger.info("Agregando columna cpt_codes...")
                conn.execute(text("""
                    ALTER TABLE transcriptions 
                    ADD COLUMN cpt_codes JSONB
                """))
                conn.commit()
                logger.info("✓ Columna cpt_codes agregada")
            else:
                logger.info("✓ Columna cpt_codes ya existe")
            
            # Agregar cms1500_form_data si no existe
            if 'cms1500_form_data' not in existing_columns:
                logger.info("Agregando columna cms1500_form_data...")
                conn.execute(text("""
                    ALTER TABLE transcriptions 
                    ADD COLUMN cms1500_form_data JSONB
                """))
                conn.commit()
                logger.info("✓ Columna cms1500_form_data agregada")
            else:
                logger.info("✓ Columna cms1500_form_data ya existe")
            
            # Agregar workflow_status si no existe
            if 'workflow_status' not in existing_columns:
                logger.info("Agregando columna workflow_status...")
                conn.execute(text("""
                    ALTER TABLE transcriptions 
                    ADD COLUMN workflow_status VARCHAR(50) DEFAULT 'transcribed'
                """))
                # Actualizar registros existentes
                conn.execute(text("""
                    UPDATE transcriptions 
                    SET workflow_status = 'transcribed' 
                    WHERE workflow_status IS NULL
                """))
                conn.commit()
                logger.info("✓ Columna workflow_status agregada")
            else:
                logger.info("✓ Columna workflow_status ya existe")
            
            logger.info("\n✅ Migración completada exitosamente!")
            
    except Exception as e:
        logger.error(f"❌ Error durante la migración: {e}")
        raise


if __name__ == "__main__":
    logger.info("Iniciando migración de base de datos...")
    logger.info("Agregando columnas del workflow médico...\n")
    migrate_database()

