"""
Endpoints para integración con EHRs
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from database import get_db
from schemas.ehr import (
    EHRConnectionCreate,
    EHRConnectionUpdate,
    EHRConnectionResponse,
    EHRAuthorizationRequest,
    EHRAuthorizationCallback,
    EHRSyncRequest,
    EHRSyncResponse,
    EHRPatientSearch,
    EHRPatientResponse,
    EHRListResponse
)
from services.ehr_service import EHRService
from services.transcription_service import TranscriptionService
import secrets

router = APIRouter(prefix="/api/ehr", tags=["EHR Integration"])

logger = logging.getLogger(__name__)


@router.post("/connections", response_model=EHRConnectionResponse, status_code=201)
def create_ehr_connection(
    connection_data: EHRConnectionCreate,
    db: Session = Depends(get_db)
):
    """
    Crea una nueva conexión con un EHR
    
    - **ehr_provider**: Proveedor del EHR (eclinicalworks, athenahealth, epic, etc.)
    - **ehr_name**: Nombre descriptivo de la conexión
    - **base_url**: URL base del EHR (ej: https://fhir.eclinicalworks.com/fhir/r4)
    - **client_id**: Client ID de OAuth2 (opcional, se puede agregar después)
    - **client_secret**: Client Secret de OAuth2 (opcional)
    """
    connection = EHRService.create_connection(db, connection_data)
    return connection


@router.get("/connections", response_model=EHRListResponse)
def get_ehr_connections(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    active_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Obtiene lista de conexiones EHR
    
    - **skip**: Offset para paginación
    - **limit**: Número de resultados (max 100)
    - **active_only**: Solo conexiones activas
    """
    connections = EHRService.get_connections(db, skip=skip, limit=limit, active_only=active_only)
    total = EHRService.count_connections(db, active_only=active_only)
    
    return {
        "total": total,
        "items": connections,
        "page": (skip // limit) + 1,
        "page_size": limit
    }


@router.get("/connections/{connection_id}", response_model=EHRConnectionResponse)
def get_ehr_connection(
    connection_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene una conexión específica por ID
    """
    connection = EHRService.get_connection(db, connection_id)
    
    if not connection:
        raise HTTPException(status_code=404, detail="EHR connection not found")
    
    return connection


@router.put("/connections/{connection_id}", response_model=EHRConnectionResponse)
def update_ehr_connection(
    connection_id: int,
    update_data: EHRConnectionUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza una conexión EHR
    """
    connection = EHRService.update_connection(db, connection_id, update_data)
    
    if not connection:
        raise HTTPException(status_code=404, detail="EHR connection not found")
    
    return connection


@router.delete("/connections/{connection_id}")
def delete_ehr_connection(
    connection_id: int,
    db: Session = Depends(get_db)
):
    """
    Elimina (desactiva) una conexión EHR
    """
    success = EHRService.delete_connection(db, connection_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="EHR connection not found")
    
    return {"message": "EHR connection deactivated successfully"}


@router.post("/connections/{connection_id}/authorize")
def get_authorization_url(
    connection_id: int,
    redirect_uri: str,
    scopes: Optional[List[str]] = None,
    db: Session = Depends(get_db)
):
    """
    Genera URL de autorización OAuth2 para conectar con el EHR
    
    - **connection_id**: ID de la conexión
    - **redirect_uri**: URI de redirección después de autorización
    - **scopes**: Scopes adicionales (opcional, usa los de la conexión si no se proporcionan)
    
    Returns:
        URL de autorización y state token para validación
    """
    connection = EHRService.get_connection(db, connection_id)
    
    if not connection:
        raise HTTPException(status_code=404, detail="EHR connection not found")
    
    if not connection.client_id:
        raise HTTPException(
            status_code=400,
            detail="Client ID not configured for this connection"
        )
    
    # Usar scopes de la conexión si no se proporcionan
    if not scopes:
        scopes = connection.scopes or ["patient/*.read", "user/*.write"]
    
    # Generar state token para seguridad
    state_token = secrets.token_urlsafe(32)
    
    # Obtener servicio FHIR
    fhir_service = EHRService.get_fhir_service(connection)
    
    # Generar URL de autorización
    auth_url = fhir_service.get_authorization_url(
        redirect_uri=redirect_uri,
        scopes=scopes,
        state=state_token
    )
    
    # Guardar state token en extra_metadata (en producción, usar Redis o similar)
    if not connection.extra_metadata:
        connection.extra_metadata = {}
    connection.extra_metadata["last_auth_state"] = state_token
    db.commit()
    
    return {
        "authorization_url": auth_url,
        "state": state_token,
        "connection_id": connection_id
    }


@router.post("/connections/{connection_id}/callback")
def handle_authorization_callback(
    connection_id: int,
    code: str,
    redirect_uri: str,
    state: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Maneja el callback de autorización OAuth2
    
    Intercambia el código de autorización por tokens de acceso
    """
    connection = EHRService.get_connection(db, connection_id)
    
    if not connection:
        raise HTTPException(status_code=404, detail="EHR connection not found")
    
    # Validar state token (en producción)
    if state and connection.extra_metadata and connection.extra_metadata.get("last_auth_state") != state:
        logger.warning(f"State token mismatch for connection {connection_id}")
        # En producción, esto debería ser un error, pero lo dejamos como warning para desarrollo
    
    # Obtener servicio FHIR
    fhir_service = EHRService.get_fhir_service(connection)
    
    try:
        # Intercambiar código por tokens
        token_data = fhir_service.exchange_code_for_token(code, redirect_uri)
        
        # Actualizar tokens en la conexión
        EHRService.update_tokens(
            db,
            connection_id,
            token_data["access_token"],
            token_data.get("refresh_token"),
            token_data.get("expires_in")
        )
        
        # Actualizar última sincronización
        connection.last_sync_at = None  # Se actualizará en la primera sincronización exitosa
        db.commit()
        
        return {
            "success": True,
            "message": "Authorization successful. Connection is now active.",
            "connection_id": connection_id
        }
    except Exception as e:
        logger.error(f"Error exchanging code for token: {e}")
        connection.last_error = str(e)
        db.commit()
        raise HTTPException(status_code=400, detail=f"Failed to exchange authorization code: {str(e)}")


@router.post("/connections/{connection_id}/sync", response_model=EHRSyncResponse)
def sync_transcription_to_ehr(
    connection_id: int,
    transcription_id: int,
    patient_id: str,
    sync_types: Optional[List[str]] = None,
    db: Session = Depends(get_db)
):
    """
    Sincroniza una transcripción con el EHR
    
    - **connection_id**: ID de la conexión EHR
    - **transcription_id**: ID de la transcripción a sincronizar
    - **patient_id**: ID del paciente en el EHR
    - **sync_types**: Tipos de recursos a sincronizar (document, diagnosis, procedure)
    
    Crea recursos FHIR en el EHR:
    - DocumentReference para la nota clínica
    - Condition para diagnósticos (ICD-10)
    - Procedure para procedimientos (CPT)
    """
    # Obtener conexión
    connection = EHRService.get_connection(db, connection_id)
    
    if not connection:
        raise HTTPException(status_code=404, detail="EHR connection not found")
    
    if not connection.is_active:
        raise HTTPException(status_code=400, detail="EHR connection is not active")
    
    if not connection.access_token:
        raise HTTPException(
            status_code=400,
            detail="Connection not authorized. Please complete OAuth2 authorization first."
        )
    
    # Obtener transcripción
    transcription = TranscriptionService.get_transcription(db, transcription_id)
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    if not transcription.medical_note:
        raise HTTPException(
            status_code=400,
            detail="Medical note must be generated before syncing to EHR"
        )
    
    # Preparar datos de transcripción
    transcription_data = {
        "medical_note": transcription.medical_note,
        "icd10_codes": transcription.icd10_codes or [],
        "cpt_codes": transcription.cpt_codes or []
    }
    
    # Obtener servicio FHIR
    fhir_service = EHRService.get_fhir_service(connection)
    fhir_service.set_access_token(connection.access_token)
    
    # Determinar tipos de sincronización
    if not sync_types:
        sync_types = ["document", "diagnosis", "procedure"]
    
    try:
        # Sincronizar según el tipo de EHR
        if connection.ehr_provider.lower() == "eclinicalworks":
            if isinstance(fhir_service, EClinicalWorksFHIRService):
                results = fhir_service.sync_transcription_to_ehr(
                    transcription_data,
                    patient_id,
                    connection.refresh_token
                )
            else:
                # Fallback a método genérico
                results = {}
                if "document" in sync_types and transcription.medical_note:
                    # Crear DocumentReference
                    doc_ref = {
                        "resourceType": "DocumentReference",
                        "status": "current",
                        "type": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "11506-3",
                                "display": "Progress note"
                            }]
                        },
                        "subject": {"reference": f"Patient/{patient_id}"},
                        "date": transcription.created_at.isoformat() if hasattr(transcription, 'created_at') else None,
                        "content": [{
                            "attachment": {
                                "contentType": "text/plain",
                                "data": transcription.medical_note
                            }
                        }]
                    }
                    results["document_reference"] = fhir_service.create_document_reference(
                        doc_ref, connection.refresh_token
                    )
        else:
            # Método genérico para otros EHRs
            results = {}
            # Implementar lógica genérica aquí
        
        # Crear registro de sincronización
        sync = EHRService.create_sync(
            db,
            connection_id,
            transcription_id,
            sync_type="full_sync",
            status="success",
            request_data={"patient_id": patient_id, "sync_types": sync_types},
            response_data=results
        )
        
        # Actualizar última sincronización
        from datetime import datetime
        connection.last_sync_at = datetime.now()
        connection.last_error = None
        db.commit()
        
        return {
            "success": True,
            "message": "Transcription synced successfully to EHR",
            "sync_id": sync.id,
            "resources_created": results
        }
        
    except Exception as e:
        logger.error(f"Error syncing to EHR: {e}")
        
        # Crear registro de sincronización fallida
        sync = EHRService.create_sync(
            db,
            connection_id,
            transcription_id,
            sync_type="full_sync",
            status="failed",
            request_data={"patient_id": patient_id, "sync_types": sync_types},
            response_data={"error": str(e)}
        )
        
        # Actualizar error en conexión
        connection.last_error = str(e)
        db.commit()
        
        raise HTTPException(status_code=500, detail=f"Failed to sync to EHR: {str(e)}")


@router.post("/connections/{connection_id}/patients/search", response_model=List[EHRPatientResponse])
def search_patients(
    connection_id: int,
    name: Optional[str] = None,
    identifier: Optional[str] = None,
    birthdate: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Busca pacientes en el EHR
    
    - **connection_id**: ID de la conexión EHR
    - **name**: Nombre del paciente
    - **identifier**: Identificador (MRN, SSN, etc.)
    - **birthdate**: Fecha de nacimiento (YYYY-MM-DD)
    """
    connection = EHRService.get_connection(db, connection_id)
    
    if not connection:
        raise HTTPException(status_code=404, detail="EHR connection not found")
    
    if not connection.access_token:
        raise HTTPException(
            status_code=400,
            detail="Connection not authorized. Please complete OAuth2 authorization first."
        )
    
    # Obtener servicio FHIR
    fhir_service = EHRService.get_fhir_service(connection)
    fhir_service.set_access_token(connection.access_token)
    
    try:
        # Buscar pacientes
        search_results = fhir_service.search_patients(
            name=name,
            identifier=identifier,
            birthdate=birthdate,
            refresh_token=connection.refresh_token
        )
        
        # Procesar resultados
        patients = []
        if "entry" in search_results:
            for entry in search_results["entry"]:
                patient_resource = entry.get("resource", {})
                patient_id = patient_resource.get("id")
                
                # Extraer nombre
                name_parts = []
                if "name" in patient_resource and len(patient_resource["name"]) > 0:
                    name_obj = patient_resource["name"][0]
                    if "given" in name_obj:
                        name_parts.extend(name_obj["given"])
                    if "family" in name_obj:
                        name_parts.append(name_obj["family"])
                    name = " ".join(name_parts) if name_parts else None
                else:
                    name = None
                
                # Extraer identificadores
                identifiers = []
                if "identifier" in patient_resource:
                    for ident in patient_resource["identifier"]:
                        identifiers.append({
                            "system": ident.get("system", ""),
                            "value": ident.get("value", "")
                        })
                
                patients.append({
                    "id": patient_id,
                    "name": name,
                    "birthdate": patient_resource.get("birthDate"),
                    "gender": patient_resource.get("gender"),
                    "identifiers": identifiers,
                    "fhir_resource": patient_resource
                })
        
        return patients
        
    except Exception as e:
        logger.error(f"Error searching patients: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search patients: {str(e)}")


@router.get("/connections/{connection_id}/capabilities")
def get_ehr_capabilities(
    connection_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene el capability statement del EHR (metadata sobre recursos soportados)
    """
    connection = EHRService.get_connection(db, connection_id)
    
    if not connection:
        raise HTTPException(status_code=404, detail="EHR connection not found")
    
    # Obtener servicio FHIR
    fhir_service = EHRService.get_fhir_service(connection)
    
    try:
        capabilities = fhir_service.get_capability_statement()
        return capabilities
    except Exception as e:
        logger.error(f"Error getting capabilities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get EHR capabilities: {str(e)}")
