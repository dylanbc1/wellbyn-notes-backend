"""
Modelos para métricas y reportes
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey, Boolean
from sqlalchemy.sql import func
from database import Base


class DoctorMetrics(Base):
    """
    Métricas de eficiencia del doctor
    """
    __tablename__ = "doctor_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Métricas
    average_visit_time_minutes = Column(Float, nullable=True)
    same_day_note_completion_rate = Column(Float, nullable=True)  # 0.0-1.0
    charting_time_saved_minutes = Column(Float, nullable=True)
    
    # Período de cálculo
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<DoctorMetrics {self.id}: Doctor {self.doctor_id}>"


class OperationalMetrics(Base):
    """
    Métricas operativas a nivel clínica
    """
    __tablename__ = "operational_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Métricas agregadas
    average_visit_duration_minutes = Column(Float, nullable=True)
    same_day_note_completion_percentage = Column(Float, nullable=True)
    after_hours_charting_reduction_percentage = Column(Float, nullable=True)
    
    # Período de cálculo
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<OperationalMetrics {self.id}>"


class DocumentationCompletenessReport(Base):
    """
    Reporte de completitud de documentación por visita
    """
    __tablename__ = "documentation_completeness_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    transcription_id = Column(Integer, ForeignKey("transcriptions.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Elementos faltantes
    missing_elements = Column(JSON, nullable=True)  # Lista de elementos faltantes
    completeness_score = Column(Float, nullable=True)  # 0.0-1.0
    
    # Patrones de riesgo
    high_risk_patterns = Column(JSON, nullable=True)  # Lista de patrones de riesgo
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<DocumentationCompletenessReport {self.id}: Transcription {self.transcription_id}>"


class CodingReport(Base):
    """
    Reporte de códigos sugeridos vs finales
    """
    __tablename__ = "coding_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    transcription_id = Column(Integer, ForeignKey("transcriptions.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Códigos sugeridos
    suggested_icd10_codes = Column(JSON, nullable=True)
    suggested_cpt_codes = Column(JSON, nullable=True)
    
    # Códigos finales (aprobados por billing)
    final_icd10_codes = Column(JSON, nullable=True)
    final_cpt_codes = Column(JSON, nullable=True)
    
    # Análisis
    downgrade_frequency = Column(Float, nullable=True)  # Frecuencia de downgrades
    missed_documentation_impact = Column(JSON, nullable=True)  # Impacto de documentación faltante
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<CodingReport {self.id}: Transcription {self.transcription_id}>"


class DenialRiskIndicator(Base):
    """
    Indicador de riesgo de denegación de reclamaciones
    """
    __tablename__ = "denial_risk_indicators"
    
    id = Column(Integer, primary_key=True, index=True)
    transcription_id = Column(Integer, ForeignKey("transcriptions.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Riesgo
    risk_level = Column(String(20), nullable=False)  # "high", "medium", "low"
    risk_score = Column(Float, nullable=False)  # 0.0-1.0
    
    # Causas raíz
    root_causes = Column(JSON, nullable=True)  # [{type: "missing_elements|insufficient_specificity", details: "..."}]
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<DenialRiskIndicator {self.id}: Transcription {self.transcription_id}>"


class EHRAuditLog(Base):
    """
    Log de auditoría de escrituras al EHR
    """
    __tablename__ = "ehr_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    transcription_id = Column(Integer, ForeignKey("transcriptions.id"), nullable=False, index=True)
    connection_id = Column(Integer, ForeignKey("ehr_connections.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Datos escritos
    data_written = Column(JSON, nullable=False)  # Qué datos se escribieron
    fhir_resource_type = Column(String(100), nullable=True)
    fhir_resource_id = Column(String(255), nullable=True)
    
    # Aprobación
    doctor_approval = Column(Boolean, default=False)
    ai_assisted_flag = Column(Boolean, default=False)
    
    # Timestamps
    written_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<EHRAuditLog {self.id}: Transcription {self.transcription_id}>"
