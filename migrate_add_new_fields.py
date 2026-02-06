"""
Script de migración para agregar los nuevos campos a la tabla transcriptions
Ejecutar: python migrate_add_new_fields.py
"""

import sys
from sqlalchemy import text
from database import engine, SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """Agrega las nuevas columnas a la tabla transcriptions"""
    
    # Columnas nuevas a agregar
    new_columns = [
        ("soap_sections", "JSON", "NULL"),
        ("raw_transcript", "TEXT", "NULL"),
        ("documentation_completeness", "JSON", "NULL"),
        ("final_note", "TEXT", "NULL"),
        ("note_format", "VARCHAR(50)", "NULL"),
        ("doctor_approved", "BOOLEAN", "DEFAULT FALSE"),
        ("doctor_approved_at", "TIMESTAMP WITH TIME ZONE", "NULL"),
        ("doctor_id", "INTEGER", "NULL"),
        ("coding_preview", "JSON", "NULL"),
        ("patient_context", "JSON", "NULL"),
        ("patient_id", "VARCHAR(255)", "NULL"),
        ("visit_date", "TIMESTAMP WITH TIME ZONE", "NULL"),
        ("visit_duration_minutes", "INTEGER", "NULL"),
        ("patient_summary", "TEXT", "NULL"),
        ("next_steps", "JSON", "NULL"),
        ("share_token", "VARCHAR(255)", "NULL"),
        ("share_expires_at", "TIMESTAMP WITH TIME ZONE", "NULL"),
    ]
    
    # Foreign key constraint para doctor_id
    foreign_keys = [
        ("doctor_id", "users", "id")
    ]
    
    db = SessionLocal()
    
    try:
        logger.info("Iniciando migración de base de datos...")
        
        # Verificar qué columnas ya existen
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'transcriptions'
            """))
            existing_columns = {row[0] for row in result}
            logger.info(f"Columnas existentes: {sorted(existing_columns)}")
        
        # Agregar columnas que no existen
        for column_name, column_type, default in new_columns:
            if column_name in existing_columns:
                logger.info(f"✓ Columna '{column_name}' ya existe, omitiendo...")
                continue
            
            try:
                sql = f"ALTER TABLE transcriptions ADD COLUMN {column_name} {column_type}"
                if default and not default.startswith("NULL"):
                    sql += f" {default}"
                
                logger.info(f"Agregando columna '{column_name}'...")
                with engine.connect() as conn:
                    conn.execute(text(sql))
                    conn.commit()
                logger.info(f"✓ Columna '{column_name}' agregada exitosamente")
            except Exception as e:
                logger.error(f"✗ Error agregando columna '{column_name}': {e}")
                # Continuar con las demás columnas
        
        # Agregar foreign key constraint para doctor_id si la columna existe
        if "doctor_id" in existing_columns or "doctor_id" in [col[0] for col in new_columns if col[0] not in existing_columns]:
            try:
                logger.info("Verificando foreign key constraint para doctor_id...")
                with engine.connect() as conn:
                    # Verificar si el constraint ya existe
                    result = conn.execute(text("""
                        SELECT constraint_name 
                        FROM information_schema.table_constraints 
                        WHERE table_name = 'transcriptions' 
                        AND constraint_type = 'FOREIGN KEY'
                        AND constraint_name LIKE '%doctor_id%'
                    """))
                    if result.fetchone() is None:
                        logger.info("Agregando foreign key constraint para doctor_id...")
                        conn.execute(text("""
                            ALTER TABLE transcriptions 
                            ADD CONSTRAINT fk_transcriptions_doctor_id 
                            FOREIGN KEY (doctor_id) REFERENCES users(id)
                        """))
                        conn.commit()
                        logger.info("✓ Foreign key constraint agregado")
                    else:
                        logger.info("✓ Foreign key constraint ya existe")
            except Exception as e:
                logger.warning(f"⚠ No se pudo agregar foreign key constraint (puede que ya exista): {e}")
        
        # Crear índice único para share_token si no existe
        try:
            logger.info("Verificando índice único para share_token...")
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE tablename = 'transcriptions' 
                    AND indexname LIKE '%share_token%'
                """))
                if result.fetchone() is None:
                    logger.info("Creando índice único para share_token...")
                    conn.execute(text("""
                        CREATE UNIQUE INDEX IF NOT EXISTS idx_transcriptions_share_token 
                        ON transcriptions(share_token) 
                        WHERE share_token IS NOT NULL
                    """))
                    conn.commit()
                    logger.info("✓ Índice único creado para share_token")
                else:
                    logger.info("✓ Índice único ya existe para share_token")
        except Exception as e:
            logger.warning(f"⚠ No se pudo crear índice único: {e}")
        
        logger.info("=" * 50)
        logger.info("✅ Migración completada exitosamente!")
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"❌ Error durante la migración: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    try:
        migrate()
        print("\n✅ Migración completada. Puedes reiniciar el servidor ahora.")
    except Exception as e:
        print(f"\n❌ Error en la migración: {e}")
        sys.exit(1)
