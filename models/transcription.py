"""
Modelo de Transcripción - Versión simplificada
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean, ForeignKey
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
    
    # NEW FEATURES - Live Clinical Transcription (Structured)
    # SOAP sections with real-time mapping
    soap_sections = Column(JSON, nullable=True)  # {subjective: {text: "", locked: false}, objective: {...}, assessment: {...}, plan: {...}}
    raw_transcript = Column(Text, nullable=True)  # Raw transcript for live transcription
    
    # NEW FEATURES - Clinical Coverage Indicator
    documentation_completeness = Column(JSON, nullable=True)  # {chief_complaint: "complete|partial|missing", duration: "...", severity: "...", location: "...", assessment: "...", plan: "..."}
    
    # NEW FEATURES - Final Clinical Note (Doctor-Approved)
    final_note = Column(Text, nullable=True)  # Final approved note
    note_format = Column(String(50), nullable=True)  # "soap" or "narrative" or "problem-oriented"
    doctor_approved = Column(Boolean, default=False)
    doctor_approved_at = Column(DateTime(timezone=True), nullable=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Doctor who approved
    
    # NEW FEATURES - Coding Preview
    coding_preview = Column(JSON, nullable=True)  # Enhanced coding with warnings
    
    # NEW FEATURES - Patient Context (EHR-Pulled)
    patient_context = Column(JSON, nullable=True)  # {medications: [], allergies: [], problems: [], recent_visits: []}
    patient_id = Column(String(255), nullable=True)  # Patient identifier from EHR
    
    # NEW FEATURES - Visit Information
    visit_date = Column(DateTime(timezone=True), nullable=True)
    visit_duration_minutes = Column(Integer, nullable=True)
    
    # NEW FEATURES - Patient Summary
    patient_summary = Column(Text, nullable=True)  # Plain-language summary
    next_steps = Column(JSON, nullable=True)  # [{type: "medication", description: "...", ...}, ...]
    
    # NEW FEATURES - Shareable Summary
    share_token = Column(String(255), nullable=True, unique=True, index=True)
    share_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Transcription {self.id}: {self.filename}>"

