"""
Servicio para métricas y reportes
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from models.metrics import (
    DoctorMetrics, OperationalMetrics, DocumentationCompletenessReport,
    CodingReport, DenialRiskIndicator, EHRAuditLog
)
from models.transcription import Transcription
from models.user import User
import logging

logger = logging.getLogger(__name__)


class MetricsService:
    """
    Servicio para calcular y gestionar métricas
    """
    
    @staticmethod
    def calculate_doctor_metrics(
        db: Session,
        doctor_id: int,
        period_days: int = 30
    ) -> Optional[DoctorMetrics]:
        """
        Calcula métricas de eficiencia del doctor
        """
        period_end = datetime.now()
        period_start = period_end - timedelta(days=period_days)
        
        # Obtener transcripciones del doctor en el período
        transcriptions = db.query(Transcription).filter(
            Transcription.doctor_id == doctor_id,
            Transcription.created_at >= period_start,
            Transcription.created_at <= period_end
        ).all()
        
        if not transcriptions:
            return None
        
        # Calcular métricas
        total_visits = len(transcriptions)
        total_visit_time = sum(t.visit_duration_minutes or 0 for t in transcriptions)
        average_visit_time = total_visit_time / total_visits if total_visits > 0 else 0
        
        # Same-day completion (notas aprobadas el mismo día)
        same_day_completed = sum(
            1 for t in transcriptions
            if t.doctor_approved and t.doctor_approved_at
            and t.doctor_approved_at.date() == t.created_at.date()
        )
        same_day_completion_rate = same_day_completed / total_visits if total_visits > 0 else 0
        
        # Charting time saved (estimado basado en tiempo promedio de documentación manual)
        # Asumimos que sin AI tomaría 15 minutos por nota, con AI toma 5 minutos
        estimated_manual_time = total_visits * 15
        estimated_ai_time = total_visits * 5
        charting_time_saved = estimated_manual_time - estimated_ai_time
        
        # Crear o actualizar métricas
        metrics = db.query(DoctorMetrics).filter(
            DoctorMetrics.doctor_id == doctor_id,
            DoctorMetrics.period_start == period_start,
            DoctorMetrics.period_end == period_end
        ).first()
        
        if not metrics:
            metrics = DoctorMetrics(
                doctor_id=doctor_id,
                average_visit_time_minutes=average_visit_time,
                same_day_note_completion_rate=same_day_completion_rate,
                charting_time_saved_minutes=charting_time_saved,
                period_start=period_start,
                period_end=period_end
            )
            db.add(metrics)
        else:
            metrics.average_visit_time_minutes = average_visit_time
            metrics.same_day_note_completion_rate = same_day_completion_rate
            metrics.charting_time_saved_minutes = charting_time_saved
        
        db.commit()
        db.refresh(metrics)
        
        return metrics
    
    @staticmethod
    def calculate_operational_metrics(
        db: Session,
        period_days: int = 30
    ) -> Optional[OperationalMetrics]:
        """
        Calcula métricas operativas a nivel clínica
        """
        period_end = datetime.now()
        period_start = period_end - timedelta(days=period_days)
        
        # Obtener todas las transcripciones en el período
        transcriptions = db.query(Transcription).filter(
            Transcription.created_at >= period_start,
            Transcription.created_at <= period_end
        ).all()
        
        if not transcriptions:
            return None
        
        # Calcular métricas agregadas
        total_visits = len(transcriptions)
        total_visit_time = sum(t.visit_duration_minutes or 0 for t in transcriptions)
        average_visit_duration = total_visit_time / total_visits if total_visits > 0 else 0
        
        # Same-day completion percentage
        same_day_completed = sum(
            1 for t in transcriptions
            if t.doctor_approved and t.doctor_approved_at
            and t.doctor_approved_at.date() == t.created_at.date()
        )
        same_day_completion_percentage = (same_day_completed / total_visits * 100) if total_visits > 0 else 0
        
        # After-hours charting reduction (estimado)
        # Asumimos que sin AI, 40% de notas se completan después de horas
        # Con AI, solo 10% se completan después de horas
        estimated_before_after_hours = total_visits * 0.4
        estimated_after_after_hours = total_visits * 0.1
        reduction = ((estimated_before_after_hours - estimated_after_after_hours) / estimated_before_after_hours * 100) if estimated_before_after_hours > 0 else 0
        
        # Crear o actualizar métricas
        metrics = db.query(OperationalMetrics).filter(
            OperationalMetrics.period_start == period_start,
            OperationalMetrics.period_end == period_end
        ).first()
        
        if not metrics:
            metrics = OperationalMetrics(
                average_visit_duration_minutes=average_visit_duration,
                same_day_note_completion_percentage=same_day_completion_percentage,
                after_hours_charting_reduction_percentage=reduction,
                period_start=period_start,
                period_end=period_end
            )
            db.add(metrics)
        else:
            metrics.average_visit_duration_minutes = average_visit_duration
            metrics.same_day_note_completion_percentage = same_day_completion_percentage
            metrics.after_hours_charting_reduction_percentage = reduction
        
        db.commit()
        db.refresh(metrics)
        
        return metrics
    
    @staticmethod
    def create_documentation_completeness_report(
        db: Session,
        transcription_id: int,
        doctor_id: Optional[int] = None
    ) -> DocumentationCompletenessReport:
        """
        Crea reporte de completitud de documentación
        """
        transcription = db.query(Transcription).filter(Transcription.id == transcription_id).first()
        
        if not transcription:
            raise ValueError(f"Transcription {transcription_id} not found")
        
        completeness = transcription.documentation_completeness or {}
        
        # Calcular elementos faltantes
        missing_elements = [
            key for key, value in completeness.items()
            if value == "missing"
        ]
        
        # Calcular score de completitud
        total_elements = len(completeness)
        complete_elements = sum(1 for v in completeness.values() if v == "complete")
        partial_elements = sum(1 for v in completeness.values() if v == "partial")
        completeness_score = (complete_elements + partial_elements * 0.5) / total_elements if total_elements > 0 else 0
        
        # Identificar patrones de riesgo
        high_risk_patterns = []
        if completeness.get("assessment") == "missing":
            high_risk_patterns.append("missing_assessment")
        if completeness.get("plan") == "missing":
            high_risk_patterns.append("missing_plan")
        if completeness.get("chief_complaint") == "missing":
            high_risk_patterns.append("missing_chief_complaint")
        
        report = DocumentationCompletenessReport(
            transcription_id=transcription_id,
            doctor_id=doctor_id or transcription.doctor_id,
            missing_elements=missing_elements,
            completeness_score=completeness_score,
            high_risk_patterns=high_risk_patterns
        )
        
        db.add(report)
        db.commit()
        db.refresh(report)
        
        return report
    
    @staticmethod
    def create_coding_report(
        db: Session,
        transcription_id: int,
        final_icd10_codes: List[Dict[str, Any]],
        final_cpt_codes: List[Dict[str, Any]],
        doctor_id: Optional[int] = None
    ) -> CodingReport:
        """
        Crea reporte de códigos sugeridos vs finales
        """
        transcription = db.query(Transcription).filter(Transcription.id == transcription_id).first()
        
        if not transcription:
            raise ValueError(f"Transcription {transcription_id} not found")
        
        suggested_icd10 = transcription.icd10_codes or []
        suggested_cpt = transcription.cpt_codes or []
        
        # Calcular frecuencia de downgrades
        downgrade_count = 0
        total_suggested = len(suggested_icd10) + len(suggested_cpt)
        total_final = len(final_icd10_codes) + len(final_cpt_codes)
        
        if total_suggested > total_final:
            downgrade_count = total_suggested - total_final
        
        downgrade_frequency = downgrade_count / total_suggested if total_suggested > 0 else 0
        
        # Analizar impacto de documentación faltante
        missing_doc_impact = []
        if transcription.documentation_completeness:
            for key, value in transcription.documentation_completeness.items():
                if value == "missing":
                    missing_doc_impact.append({
                        "element": key,
                        "impact": "May affect code accuracy"
                    })
        
        report = CodingReport(
            transcription_id=transcription_id,
            doctor_id=doctor_id or transcription.doctor_id,
            suggested_icd10_codes=suggested_icd10,
            suggested_cpt_codes=suggested_cpt,
            final_icd10_codes=final_icd10_codes,
            final_cpt_codes=final_cpt_codes,
            downgrade_frequency=downgrade_frequency,
            missed_documentation_impact=missing_doc_impact
        )
        
        db.add(report)
        db.commit()
        db.refresh(report)
        
        return report
    
    @staticmethod
    def create_denial_risk_indicator(
        db: Session,
        transcription_id: int,
        doctor_id: Optional[int] = None
    ) -> DenialRiskIndicator:
        """
        Crea indicador de riesgo de denegación
        """
        transcription = db.query(Transcription).filter(Transcription.id == transcription_id).first()
        
        if not transcription:
            raise ValueError(f"Transcription {transcription_id} not found")
        
        completeness = transcription.documentation_completeness or {}
        
        # Calcular score de riesgo
        missing_count = sum(1 for v in completeness.values() if v == "missing")
        partial_count = sum(1 for v in completeness.values() if v == "partial")
        total_elements = len(completeness)
        
        risk_score = (missing_count * 1.0 + partial_count * 0.5) / total_elements if total_elements > 0 else 0
        
        # Determinar nivel de riesgo
        if risk_score >= 0.7:
            risk_level = "high"
        elif risk_score >= 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Identificar causas raíz
        root_causes = []
        for key, value in completeness.items():
            if value == "missing":
                root_causes.append({
                    "type": "missing_elements",
                    "element": key,
                    "details": f"{key} not documented"
                })
            elif value == "partial":
                root_causes.append({
                    "type": "insufficient_specificity",
                    "element": key,
                    "details": f"{key} partially documented"
                })
        
        indicator = DenialRiskIndicator(
            transcription_id=transcription_id,
            doctor_id=doctor_id or transcription.doctor_id,
            risk_level=risk_level,
            risk_score=risk_score,
            root_causes=root_causes
        )
        
        db.add(indicator)
        db.commit()
        db.refresh(indicator)
        
        return indicator
    
    @staticmethod
    def create_ehr_audit_log(
        db: Session,
        transcription_id: int,
        connection_id: int,
        doctor_id: int,
        data_written: Dict[str, Any],
        fhir_resource_type: Optional[str] = None,
        fhir_resource_id: Optional[str] = None,
        doctor_approval: bool = False,
        ai_assisted_flag: bool = True
    ) -> EHRAuditLog:
        """
        Crea log de auditoría de escritura al EHR
        """
        log = EHRAuditLog(
            transcription_id=transcription_id,
            connection_id=connection_id,
            doctor_id=doctor_id,
            data_written=data_written,
            fhir_resource_type=fhir_resource_type,
            fhir_resource_id=fhir_resource_id,
            doctor_approval=doctor_approval,
            ai_assisted_flag=ai_assisted_flag
        )
        
        db.add(log)
        db.commit()
        db.refresh(log)
        
        return log
    
    @staticmethod
    def get_doctor_metrics(
        db: Session,
        doctor_id: int,
        period_days: int = 30
    ) -> Optional[DoctorMetrics]:
        """
        Obtiene métricas del doctor
        """
        period_end = datetime.now()
        period_start = period_end - timedelta(days=period_days)
        
        return db.query(DoctorMetrics).filter(
            DoctorMetrics.doctor_id == doctor_id,
            DoctorMetrics.period_start >= period_start,
            DoctorMetrics.period_end <= period_end
        ).order_by(desc(DoctorMetrics.created_at)).first()
    
    @staticmethod
    def get_operational_metrics(
        db: Session,
        period_days: int = 30
    ) -> Optional[OperationalMetrics]:
        """
        Obtiene métricas operativas
        """
        period_end = datetime.now()
        period_start = period_end - timedelta(days=period_days)
        
        return db.query(OperationalMetrics).filter(
            OperationalMetrics.period_start >= period_start,
            OperationalMetrics.period_end <= period_end
        ).order_by(desc(OperationalMetrics.created_at)).first()
    
    @staticmethod
    def get_documentation_completeness_dashboard(
        db: Session,
        skip: int = 0,
        limit: int = 100
    ) -> List[DocumentationCompletenessReport]:
        """
        Obtiene dashboard de completitud de documentación
        """
        return db.query(DocumentationCompletenessReport).order_by(
            desc(DocumentationCompletenessReport.created_at)
        ).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_ehr_audit_logs(
        db: Session,
        skip: int = 0,
        limit: int = 100
    ) -> List[EHRAuditLog]:
        """
        Obtiene logs de auditoría de EHR
        """
        return db.query(EHRAuditLog).order_by(
            desc(EHRAuditLog.written_at)
        ).offset(skip).limit(limit).all()
