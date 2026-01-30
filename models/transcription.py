"""
Modelo de Transcripción - Versión simplificada
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.sql import func
from database import Base


class Transcription(Base):
    """
    Modelo para guardar transcripciones de audio y workflow médico
    """
    __tablename__ = "transcriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Información del archivo
    filename = Column(String(255), nullable=False)
    file_size_mb = Column(Float, nullable=False)
    content_type = Column(String(100), nullable=False)
    
    # Transcripción
    text = Column(Text, nullable=False)
    
    # Metadata del procesamiento
    processing_time_seconds = Column(Float, nullable=False)
    model = Column(String(100), default="openai/whisper-base")
    provider = Column(String(50), default="huggingface")
    
    # Medical Workflow Fields
    # Step 1: Transcription (already exists as 'text')
    # Step 2: AI-generated medical note
    medical_note = Column(Text, nullable=True)
    
    # Step 3: ICD-10 codes (array of objects: {code, description, confidence})
    icd10_codes = Column(JSON, nullable=True)
    
    # Step 4: CPT codes + modifiers (array of objects: {code, description, modifier, confidence})
    cpt_codes = Column(JSON, nullable=True)
    
    # Step 5: CMS-1500 form data (JSON object with all form fields)
    cms1500_form_data = Column(JSON, nullable=True)
    
    # Workflow status tracking
    workflow_status = Column(String(50), default="transcribed")  # transcribed, note_generated, codes_suggested, form_created
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Transcription {self.id}: {self.filename}>"

