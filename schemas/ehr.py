"""
Schemas para integración con EHRs
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class EHRConnectionCreate(BaseModel):
    """Schema para crear una conexión EHR"""
    ehr_provider: str = Field(..., description="Proveedor del EHR (eclinicalworks, athenahealth, etc.)")
    ehr_name: str = Field(..., description="Nombre descriptivo de la conexión")
    base_url: str = Field(..., description="URL base del EHR")
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    practice_id: Optional[str] = None
    practice_name: Optional[str] = None
    fhir_version: str = Field(default="R4", description="Versión FHIR")
    scopes: Optional[List[str]] = Field(default=None, description="Scopes OAuth2 solicitados")
    metadata: Optional[Dict[str, Any]] = None


class EHRConnectionUpdate(BaseModel):
    """Schema para actualizar una conexión EHR"""
    ehr_name: Optional[str] = None
    base_url: Optional[str] = None
    practice_id: Optional[str] = None
    practice_name: Optional[str] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class EHRConnectionResponse(BaseModel):
    """Schema de respuesta para conexión EHR"""
    id: int
    ehr_provider: str
    ehr_name: str
    practice_id: Optional[str]
    practice_name: Optional[str]
    base_url: str
    fhir_version: str
    scopes: Optional[List[str]]
    is_active: bool
    last_sync_at: Optional[datetime]
    last_error: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class EHRTokenResponse(BaseModel):
    """Schema para respuesta de tokens OAuth2"""
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    token_type: str = "Bearer"
    scope: Optional[str] = None


class EHRAuthorizationRequest(BaseModel):
    """Schema para solicitar autorización OAuth2"""
    connection_id: int
    redirect_uri: str = Field(..., description="URI de redirección después de autorización")
    scopes: Optional[List[str]] = Field(default=None, description="Scopes adicionales si no están en la conexión")
    state: Optional[str] = Field(default=None, description="Estado para prevenir CSRF")


class EHRAuthorizationCallback(BaseModel):
    """Schema para callback de autorización OAuth2"""
    connection_id: int
    code: str = Field(..., description="Código de autorización")
    state: Optional[str] = None


class EHRSyncRequest(BaseModel):
    """Schema para sincronizar transcripción con EHR"""
    connection_id: int
    transcription_id: int
    patient_id: str = Field(..., description="ID del paciente en el EHR")
    sync_types: Optional[List[str]] = Field(
        default=["document", "diagnosis", "procedure"],
        description="Tipos de recursos a sincronizar"
    )


class EHRSyncResponse(BaseModel):
    """Schema de respuesta para sincronización"""
    success: bool
    message: str
    sync_id: int
    resources_created: Dict[str, Any] = Field(
        default_factory=dict,
        description="Recursos FHIR creados en el EHR"
    )


class EHRPatientSearch(BaseModel):
    """Schema para búsqueda de pacientes"""
    connection_id: int
    name: Optional[str] = None
    identifier: Optional[str] = None
    birthdate: Optional[str] = None


class EHRPatientResponse(BaseModel):
    """Schema de respuesta para paciente"""
    id: str
    name: Optional[str] = None
    birthdate: Optional[str] = None
    gender: Optional[str] = None
    identifiers: List[Dict[str, str]] = Field(default_factory=list)
    fhir_resource: Optional[Dict[str, Any]] = None


class EHRListResponse(BaseModel):
    """Schema para lista de conexiones EHR"""
    total: int
    items: List[EHRConnectionResponse]
    page: int
    page_size: int
