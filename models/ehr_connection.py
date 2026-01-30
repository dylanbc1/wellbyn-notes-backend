"""
Modelo para conexiones con EHRs
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class EHRConnection(Base):
    """
    Modelo para almacenar conexiones con sistemas EHR
    """
    __tablename__ = "ehr_connections"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Información del EHR
    ehr_provider = Column(String(100), nullable=False, index=True)  # eclinicalworks, athenahealth, epic, etc.
    ehr_name = Column(String(255), nullable=False)  # Nombre descriptivo
    
    # Información de autenticación
    client_id = Column(String(255), nullable=True)  # OAuth2 Client ID
    client_secret = Column(String(500), nullable=True)  # OAuth2 Client Secret (encrypted)
    access_token = Column(Text, nullable=True)  # Access token actual
    refresh_token = Column(Text, nullable=True)  # Refresh token
    token_expires_at = Column(DateTime(timezone=True), nullable=True)  # Expiración del token
    
    # Información de la práctica/clínica
    practice_id = Column(String(255), nullable=True)  # ID de la práctica en el EHR
    practice_name = Column(String(255), nullable=True)
    base_url = Column(String(500), nullable=False)  # URL base del EHR (ej: https://fhir.eclinicalworks.com)
    
    # Configuración SMART on FHIR
    fhir_version = Column(String(20), default="R4")  # R4, STU3, etc.
    scopes = Column(JSON, nullable=True)  # Scopes solicitados: ["patient/*.read", "user/*.write"]
    
    # Estado de la conexión
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    
    # Metadata adicional (usando extra_metadata porque 'metadata' es reservado en SQLAlchemy)
    extra_metadata = Column(JSON, nullable=True)  # Información adicional específica del EHR
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    syncs = relationship("EHRSync", back_populates="connection", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<EHRConnection {self.id}: {self.ehr_provider} - {self.practice_name}>"


class EHRSync(Base):
    """
    Modelo para rastrear sincronizaciones con EHRs
    """
    __tablename__ = "ehr_syncs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Relación con conexión
    connection_id = Column(Integer, ForeignKey("ehr_connections.id"), nullable=False)
    connection = relationship("EHRConnection", back_populates="syncs")
    
    # Relación con transcripción
    transcription_id = Column(Integer, ForeignKey("transcriptions.id"), nullable=True)
    
    # Tipo de sincronización
    sync_type = Column(String(50), nullable=False)  # patient_data, clinical_note, diagnosis, procedure, etc.
    
    # Datos sincronizados
    fhir_resource_type = Column(String(100), nullable=True)  # Patient, Observation, Condition, Procedure, etc.
    fhir_resource_id = Column(String(255), nullable=True)  # ID del recurso en el EHR
    
    # Estado
    status = Column(String(50), default="pending")  # pending, success, failed
    error_message = Column(Text, nullable=True)
    
    # Datos enviados/recibidos
    request_data = Column(JSON, nullable=True)
    response_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    synced_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<EHRSync {self.id}: {self.sync_type} - {self.status}>"
