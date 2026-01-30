"""
Servicio de lógica de negocio para transcripciones
"""

from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from models.transcription import Transcription
from schemas.transcription import TranscriptionCreate


class TranscriptionService:
    """
    Servicio para manejar transcripciones
    """
    
    @staticmethod
    def create_transcription(db: Session, transcription_data: TranscriptionCreate) -> Transcription:
        """
        Crear una nueva transcripción en la BD
        """
        db_transcription = Transcription(
            filename=transcription_data.filename,
            file_size_mb=transcription_data.file_size_mb,
            content_type=transcription_data.content_type,
            text=transcription_data.text,
            processing_time_seconds=transcription_data.processing_time_seconds,
            model=transcription_data.model,
            provider=transcription_data.provider
        )
        
        db.add(db_transcription)
        db.commit()
        db.refresh(db_transcription)
        
        return db_transcription
    
    @staticmethod
    def get_transcription(db: Session, transcription_id: int) -> Optional[Transcription]:
        """
        Obtener una transcripción por ID
        """
        return db.query(Transcription).filter(Transcription.id == transcription_id).first()
    
    @staticmethod
    def get_transcriptions(
        db: Session,
        skip: int = 0,
        limit: int = 100
    ) -> List[Transcription]:
        """
        Obtener lista de transcripciones
        """
        return db.query(Transcription).order_by(Transcription.created_at.desc()).offset(skip).limit(limit).all()
    
    @staticmethod
    def count_transcriptions(db: Session) -> int:
        """
        Contar transcripciones
        """
        return db.query(Transcription).count()
    
    @staticmethod
    def delete_transcription(db: Session, transcription_id: int) -> bool:
        """
        Eliminar una transcripción
        """
        transcription = db.query(Transcription).filter(Transcription.id == transcription_id).first()
        
        if transcription:
            db.delete(transcription)
            db.commit()
            return True
        
        return False
    
    @staticmethod
    def update_medical_note(db: Session, transcription_id: int, medical_note: str) -> Optional[Transcription]:
        """
        Update medical note for a transcription
        """
        transcription = db.query(Transcription).filter(Transcription.id == transcription_id).first()
        
        if transcription:
            transcription.medical_note = medical_note
            transcription.workflow_status = "note_generated"
            db.commit()
            db.refresh(transcription)
            return transcription
        
        return None
    
    @staticmethod
    def update_icd10_codes(db: Session, transcription_id: int, icd10_codes: List[Dict[str, Any]]) -> Optional[Transcription]:
        """
        Update ICD-10 codes for a transcription
        """
        transcription = db.query(Transcription).filter(Transcription.id == transcription_id).first()
        
        if transcription:
            transcription.icd10_codes = icd10_codes
            transcription.workflow_status = "codes_suggested"
            db.commit()
            db.refresh(transcription)
            return transcription
        
        return None
    
    @staticmethod
    def update_cpt_codes(db: Session, transcription_id: int, cpt_codes: List[Dict[str, Any]]) -> Optional[Transcription]:
        """
        Update CPT codes for a transcription
        """
        transcription = db.query(Transcription).filter(Transcription.id == transcription_id).first()
        
        if transcription:
            transcription.cpt_codes = cpt_codes
            transcription.workflow_status = "codes_suggested"
            db.commit()
            db.refresh(transcription)
            return transcription
        
        return None
    
    @staticmethod
    def update_cms1500_form(db: Session, transcription_id: int, cms1500_form_data: Dict[str, Any]) -> Optional[Transcription]:
        """
        Update CMS-1500 form data for a transcription
        """
        transcription = db.query(Transcription).filter(Transcription.id == transcription_id).first()
        
        if transcription:
            transcription.cms1500_form_data = cms1500_form_data
            transcription.workflow_status = "form_created"
            db.commit()
            db.refresh(transcription)
            return transcription
        
        return None
    
    @staticmethod
    def update_full_workflow(
        db: Session,
        transcription_id: int,
        medical_note: str,
        icd10_codes: List[Dict[str, Any]],
        cpt_codes: List[Dict[str, Any]],
        cms1500_form_data: Dict[str, Any]
    ) -> Optional[Transcription]:
        """
        Update all workflow fields at once
        """
        transcription = db.query(Transcription).filter(Transcription.id == transcription_id).first()
        
        if transcription:
            transcription.medical_note = medical_note
            transcription.icd10_codes = icd10_codes
            transcription.cpt_codes = cpt_codes
            transcription.cms1500_form_data = cms1500_form_data
            transcription.workflow_status = "form_created"
            db.commit()
            db.refresh(transcription)
            return transcription
        
        return None

