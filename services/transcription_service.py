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
    
    @staticmethod
    def update_soap_sections(db: Session, transcription_id: int, soap_sections: Dict[str, Any]) -> Optional[Transcription]:
        """
        Update SOAP sections for a transcription
        """
        transcription = db.query(Transcription).filter(Transcription.id == transcription_id).first()
        
        if transcription:
            transcription.soap_sections = soap_sections
            db.commit()
            db.refresh(transcription)
            return transcription
        
        return None
    
    @staticmethod
    def update_documentation_completeness(db: Session, transcription_id: int, completeness: Dict[str, str]) -> Optional[Transcription]:
        """
        Update documentation completeness status
        """
        transcription = db.query(Transcription).filter(Transcription.id == transcription_id).first()
        
        if transcription:
            transcription.documentation_completeness = completeness
            db.commit()
            db.refresh(transcription)
            return transcription
        
        return None
    
    @staticmethod
    def update_final_note(db: Session, transcription_id: int, final_note: str, note_format: str, doctor_id: int) -> Optional[Transcription]:
        """
        Update final approved note
        """
        from datetime import datetime
        
        transcription = db.query(Transcription).filter(Transcription.id == transcription_id).first()
        
        if transcription:
            transcription.final_note = final_note
            transcription.note_format = note_format
            transcription.doctor_approved = True
            transcription.doctor_approved_at = datetime.now()
            transcription.doctor_id = doctor_id
            db.commit()
            db.refresh(transcription)
            return transcription
        
        return None
    
    @staticmethod
    def update_patient_context(db: Session, transcription_id: int, patient_context: Dict[str, Any], patient_id: Optional[str] = None) -> Optional[Transcription]:
        """
        Update patient context from EHR
        """
        transcription = db.query(Transcription).filter(Transcription.id == transcription_id).first()
        
        if transcription:
            transcription.patient_context = patient_context
            if patient_id:
                transcription.patient_id = patient_id
            db.commit()
            db.refresh(transcription)
            return transcription
        
        return None
    
    @staticmethod
    def update_patient_summary(db: Session, transcription_id: int, patient_summary: str, next_steps: List[Dict[str, Any]]) -> Optional[Transcription]:
        """
        Update patient summary and next steps
        """
        transcription = db.query(Transcription).filter(Transcription.id == transcription_id).first()
        
        if transcription:
            transcription.patient_summary = patient_summary
            transcription.next_steps = next_steps
            db.commit()
            db.refresh(transcription)
            return transcription
        
        return None
    
    @staticmethod
    def generate_share_token(db: Session, transcription_id: int, expires_days: int = 30) -> Optional[str]:
        """
        Generate shareable token for visit summary
        """
        import secrets
        from datetime import datetime, timedelta
        
        transcription = db.query(Transcription).filter(Transcription.id == transcription_id).first()
        
        if transcription:
            token = secrets.token_urlsafe(32)
            transcription.share_token = token
            transcription.share_expires_at = datetime.now() + timedelta(days=expires_days)
            db.commit()
            return token
        
        return None
    
    @staticmethod
    def get_by_share_token(db: Session, share_token: str) -> Optional[Transcription]:
        """
        Get transcription by share token (for patient access)
        """
        from datetime import datetime
        
        transcription = db.query(Transcription).filter(
            Transcription.share_token == share_token,
            Transcription.share_expires_at > datetime.now()
        ).first()
        
        return transcription

