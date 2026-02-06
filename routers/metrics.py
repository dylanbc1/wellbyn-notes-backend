"""
Endpoints para métricas y reportes administrativos
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from database import get_db
from routers.auth import get_current_user
from models.user import User, UserRole
from services.metrics_service import MetricsService
from services.ai_medical_service import AIMedicalService
from services.transcription_service import TranscriptionService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


def require_admin(current_user: User = Depends(get_current_user)):
    """Verificar que el usuario es administrador"""
    if current_user.role != UserRole.ADMINISTRATOR:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ==================== Doctor Metrics ====================

@router.get("/doctor/{doctor_id}")
def get_doctor_metrics(
    doctor_id: int,
    period_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene métricas de eficiencia del doctor (privadas al doctor)
    """
    # Solo el doctor puede ver sus propias métricas, o un admin
    if current_user.role != UserRole.ADMINISTRATOR and current_user.id != doctor_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Calcular métricas si no existen
    metrics = MetricsService.calculate_doctor_metrics(db, doctor_id, period_days)
    
    if not metrics:
        return {
            "doctor_id": doctor_id,
            "period_days": period_days,
            "message": "No data available for this period"
        }
    
    return {
        "doctor_id": metrics.doctor_id,
        "average_visit_time_minutes": metrics.average_visit_time_minutes,
        "same_day_note_completion_rate": metrics.same_day_note_completion_rate,
        "charting_time_saved_minutes": metrics.charting_time_saved_minutes,
        "period_start": metrics.period_start,
        "period_end": metrics.period_end
    }


# ==================== Operational Metrics ====================

@router.get("/operational")
def get_operational_metrics(
    period_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Obtiene métricas operativas a nivel clínica (solo admin)
    """
    # Calcular métricas si no existen
    metrics = MetricsService.calculate_operational_metrics(db, period_days)
    
    if not metrics:
        return {
            "period_days": period_days,
            "message": "No data available for this period"
        }
    
    return {
        "average_visit_duration_minutes": metrics.average_visit_duration_minutes,
        "same_day_note_completion_percentage": metrics.same_day_note_completion_percentage,
        "after_hours_charting_reduction_percentage": metrics.after_hours_charting_reduction_percentage,
        "period_start": metrics.period_start,
        "period_end": metrics.period_end
    }


# ==================== Documentation Completeness Dashboard ====================

@router.get("/documentation-completeness")
def get_documentation_completeness_dashboard(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Dashboard de completitud de documentación (solo admin)
    """
    reports = MetricsService.get_documentation_completeness_dashboard(db, skip, limit)
    
    return {
        "total": len(reports),
        "reports": [
            {
                "id": r.id,
                "transcription_id": r.transcription_id,
                "doctor_id": r.doctor_id,
                "missing_elements": r.missing_elements,
                "completeness_score": r.completeness_score,
                "high_risk_patterns": r.high_risk_patterns,
                "created_at": r.created_at
            }
            for r in reports
        ]
    }


@router.post("/documentation-completeness/{transcription_id}")
def create_documentation_completeness_report(
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Crea reporte de completitud de documentación para una transcripción
    """
    report = MetricsService.create_documentation_completeness_report(
        db, transcription_id, current_user.id
    )
    
    return {
        "success": True,
        "report": {
            "id": report.id,
            "transcription_id": report.transcription_id,
            "missing_elements": report.missing_elements,
            "completeness_score": report.completeness_score,
            "high_risk_patterns": report.high_risk_patterns
        }
    }


# ==================== Coding & Charge Capture Report ====================

@router.get("/coding-reports")
def get_coding_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Obtiene reportes de códigos sugeridos vs finales (solo admin)
    """
    from models.metrics import CodingReport
    
    reports = db.query(CodingReport).order_by(
        CodingReport.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return {
        "total": len(reports),
        "reports": [
            {
                "id": r.id,
                "transcription_id": r.transcription_id,
                "doctor_id": r.doctor_id,
                "suggested_icd10_codes": r.suggested_icd10_codes,
                "suggested_cpt_codes": r.suggested_cpt_codes,
                "final_icd10_codes": r.final_icd10_codes,
                "final_cpt_codes": r.final_cpt_codes,
                "downgrade_frequency": r.downgrade_frequency,
                "missed_documentation_impact": r.missed_documentation_impact,
                "created_at": r.created_at
            }
            for r in reports
        ]
    }


@router.post("/coding-reports/{transcription_id}")
def create_coding_report(
    transcription_id: int,
    final_icd10_codes: List[Dict[str, Any]],
    final_cpt_codes: List[Dict[str, Any]],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Crea reporte de códigos sugeridos vs finales
    """
    report = MetricsService.create_coding_report(
        db, transcription_id, final_icd10_codes, final_cpt_codes, current_user.id
    )
    
    return {
        "success": True,
        "report": {
            "id": report.id,
            "transcription_id": report.transcription_id,
            "downgrade_frequency": report.downgrade_frequency,
            "missed_documentation_impact": report.missed_documentation_impact
        }
    }


# ==================== Denial Risk Indicators ====================

@router.get("/denial-risk")
def get_denial_risk_indicators(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    risk_level: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Obtiene indicadores de riesgo de denegación (solo admin)
    """
    from models.metrics import DenialRiskIndicator
    
    query = db.query(DenialRiskIndicator)
    
    if risk_level:
        query = query.filter(DenialRiskIndicator.risk_level == risk_level)
    
    indicators = query.order_by(
        DenialRiskIndicator.risk_score.desc()
    ).offset(skip).limit(limit).all()
    
    return {
        "total": len(indicators),
        "indicators": [
            {
                "id": i.id,
                "transcription_id": i.transcription_id,
                "doctor_id": i.doctor_id,
                "risk_level": i.risk_level,
                "risk_score": i.risk_score,
                "root_causes": i.root_causes,
                "created_at": i.created_at
            }
            for i in indicators
        ]
    }


@router.post("/denial-risk/{transcription_id}")
def create_denial_risk_indicator(
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Crea indicador de riesgo de denegación para una transcripción
    """
    indicator = MetricsService.create_denial_risk_indicator(
        db, transcription_id, current_user.id
    )
    
    return {
        "success": True,
        "indicator": {
            "id": indicator.id,
            "transcription_id": indicator.transcription_id,
            "risk_level": indicator.risk_level,
            "risk_score": indicator.risk_score,
            "root_causes": indicator.root_causes
        }
    }


# ==================== EHR Write-Back Audit Log ====================

@router.get("/ehr-audit-logs")
def get_ehr_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Obtiene logs de auditoría de escrituras al EHR (solo admin)
    """
    logs = MetricsService.get_ehr_audit_logs(db, skip, limit)
    
    return {
        "total": len(logs),
        "logs": [
            {
                "id": log.id,
                "transcription_id": log.transcription_id,
                "connection_id": log.connection_id,
                "doctor_id": log.doctor_id,
                "data_written": log.data_written,
                "fhir_resource_type": log.fhir_resource_type,
                "fhir_resource_id": log.fhir_resource_id,
                "doctor_approval": log.doctor_approval,
                "ai_assisted_flag": log.ai_assisted_flag,
                "written_at": log.written_at
            }
            for log in logs
        ]
    }


@router.post("/ehr-audit-logs")
def create_ehr_audit_log(
    transcription_id: int,
    connection_id: int,
    data_written: Dict[str, Any],
    fhir_resource_type: Optional[str] = None,
    fhir_resource_id: Optional[str] = None,
    doctor_approval: bool = False,
    ai_assisted_flag: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea log de auditoría de escritura al EHR
    """
    log = MetricsService.create_ehr_audit_log(
        db,
        transcription_id,
        connection_id,
        current_user.id,
        data_written,
        fhir_resource_type,
        fhir_resource_id,
        doctor_approval,
        ai_assisted_flag
    )
    
    return {
        "success": True,
        "log": {
            "id": log.id,
            "transcription_id": log.transcription_id,
            "written_at": log.written_at
        }
    }
