"""
Schemas para Transcripciones - Versión Demo
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any


class TranscriptionBase(BaseModel):
    """Base schema"""
    filename: str
    text: str


class TranscriptionCreate(TranscriptionBase):
    """Schema para crear transcripción"""
    file_size_mb: float
    content_type: str
    processing_time_seconds: float
    model: str = "openai/whisper-base"
    provider: str = "huggingface"


class ICD10Code(BaseModel):
    """ICD-10 code suggestion"""
    code: str
    description: str
    confidence: float


class CPTCode(BaseModel):
    """CPT code with modifier"""
    code: str
    description: str
    modifier: Optional[str] = None
    confidence: float


class TranscriptionResponse(BaseModel):
    """Schema de respuesta completo (para administradores)"""
    id: int
    filename: str
    file_size_mb: float
    content_type: str
    text: str
    processing_time_seconds: float
    model: str
    provider: str
    medical_note: Optional[str] = None
    icd10_codes: Optional[List[Dict[str, Any]]] = None
    cpt_codes: Optional[List[Dict[str, Any]]] = None
    cms1500_form_data: Optional[Dict[str, Any]] = None
    workflow_status: str = "transcribed"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TranscriptionResponseDoctor(BaseModel):
    """Schema de respuesta para doctores (sin códigos ni formularios)"""
    id: int
    filename: str
    file_size_mb: float
    content_type: str
    text: str
    processing_time_seconds: float
    model: str
    provider: str
    medical_note: Optional[str] = None
    # icd10_codes y cpt_codes NO se incluyen para doctores
    # cms1500_form_data NO se incluye para doctores
    workflow_status: str = "transcribed"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TranscriptionListResponse(BaseModel):
    """Schema para lista de transcripciones"""
    total: int
    items: list[TranscriptionResponse]
    page: int = 1
    page_size: int = 10


class WorkflowStepResponse(BaseModel):
    """Response for workflow step execution"""
    success: bool
    message: str
    transcription: TranscriptionResponse

