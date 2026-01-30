"""
Servicio para gestión de conexiones EHR
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from models.ehr_connection import EHRConnection, EHRSync
from schemas.ehr import EHRConnectionCreate, EHRConnectionUpdate
from services.fhir_service import FHIRService, EClinicalWorksFHIRService

logger = logging.getLogger(__name__)


class EHRService:
    """
    Servicio para gestionar conexiones con EHRs
    """
    
    @staticmethod
    def create_connection(db: Session, connection_data: EHRConnectionCreate) -> EHRConnection:
        """
        Crea una nueva conexión EHR
        """
        db_connection = EHRConnection(
            ehr_provider=connection_data.ehr_provider,
            ehr_name=connection_data.ehr_name,
            base_url=connection_data.base_url,
            client_id=connection_data.client_id,
            client_secret=connection_data.client_secret,
            practice_id=connection_data.practice_id,
            practice_name=connection_data.practice_name,
            fhir_version=connection_data.fhir_version,
            scopes=connection_data.scopes,
            extra_metadata=connection_data.metadata
        )
        
        db.add(db_connection)
        db.commit()
        db.refresh(db_connection)
        
        logger.info(f"Created EHR connection: {db_connection.id} - {db_connection.ehr_provider}")
        return db_connection
    
    @staticmethod
    def get_connection(db: Session, connection_id: int) -> Optional[EHRConnection]:
        """
        Obtiene una conexión por ID
        """
        return db.query(EHRConnection).filter(EHRConnection.id == connection_id).first()
    
    @staticmethod
    def get_connections(db: Session, skip: int = 0, limit: int = 10, 
                       active_only: bool = False) -> List[EHRConnection]:
        """
        Obtiene lista de conexiones
        """
        query = db.query(EHRConnection)
        
        if active_only:
            query = query.filter(EHRConnection.is_active == True)
        
        return query.order_by(desc(EHRConnection.created_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def count_connections(db: Session, active_only: bool = False) -> int:
        """
        Cuenta el total de conexiones
        """
        query = db.query(EHRConnection)
        
        if active_only:
            query = query.filter(EHRConnection.is_active == True)
        
        return query.count()
    
    @staticmethod
    def update_connection(db: Session, connection_id: int, 
                         update_data: EHRConnectionUpdate) -> Optional[EHRConnection]:
        """
        Actualiza una conexión
        """
        connection = EHRService.get_connection(db, connection_id)
        
        if not connection:
            return None
        
        update_dict = update_data.dict(exclude_unset=True)
        
        for key, value in update_dict.items():
            setattr(connection, key, value)
        
        db.commit()
        db.refresh(connection)
        
        logger.info(f"Updated EHR connection: {connection_id}")
        return connection
    
    @staticmethod
    def delete_connection(db: Session, connection_id: int) -> bool:
        """
        Elimina una conexión (soft delete marcando como inactiva)
        """
        connection = EHRService.get_connection(db, connection_id)
        
        if not connection:
            return False
        
        connection.is_active = False
        db.commit()
        
        logger.info(f"Deactivated EHR connection: {connection_id}")
        return True
    
    @staticmethod
    def update_tokens(db: Session, connection_id: int, access_token: str,
                     refresh_token: Optional[str] = None, expires_in: Optional[int] = None):
        """
        Actualiza los tokens de una conexión
        """
        connection = EHRService.get_connection(db, connection_id)
        
        if not connection:
            raise ValueError(f"Connection {connection_id} not found")
        
        connection.access_token = access_token
        
        if refresh_token:
            connection.refresh_token = refresh_token
        
        if expires_in:
            from datetime import timedelta
            connection.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        connection.last_error = None
        db.commit()
        db.refresh(connection)
        
        logger.info(f"Updated tokens for connection: {connection_id}")
    
    @staticmethod
    def get_fhir_service(connection: EHRConnection) -> FHIRService:
        """
        Obtiene una instancia del servicio FHIR apropiado según el proveedor
        """
        if connection.ehr_provider.lower() == "eclinicalworks":
            return EClinicalWorksFHIRService(
                base_url=connection.base_url,
                client_id=connection.client_id,
                client_secret=connection.client_secret
            )
        else:
            # Servicio genérico FHIR
            return FHIRService(
                base_url=connection.base_url,
                client_id=connection.client_id,
                client_secret=connection.client_secret,
                fhir_version=connection.fhir_version
            )
    
    @staticmethod
    def create_sync(db: Session, connection_id: int, transcription_id: Optional[int],
                   sync_type: str, fhir_resource_type: Optional[str] = None,
                   fhir_resource_id: Optional[str] = None, status: str = "pending",
                   request_data: Optional[Dict] = None, response_data: Optional[Dict] = None) -> EHRSync:
        """
        Crea un registro de sincronización
        """
        sync = EHRSync(
            connection_id=connection_id,
            transcription_id=transcription_id,
            sync_type=sync_type,
            fhir_resource_type=fhir_resource_type,
            fhir_resource_id=fhir_resource_id,
            status=status,
            request_data=request_data,
            response_data=response_data
        )
        
        db.add(sync)
        db.commit()
        db.refresh(sync)
        
        return sync
    
    @staticmethod
    def update_sync_status(db: Session, sync_id: int, status: str,
                          fhir_resource_id: Optional[str] = None,
                          response_data: Optional[Dict] = None,
                          error_message: Optional[str] = None):
        """
        Actualiza el estado de una sincronización
        """
        sync = db.query(EHRSync).filter(EHRSync.id == sync_id).first()
        
        if not sync:
            raise ValueError(f"Sync {sync_id} not found")
        
        sync.status = status
        
        if fhir_resource_id:
            sync.fhir_resource_id = fhir_resource_id
        
        if response_data:
            sync.response_data = response_data
        
        if error_message:
            sync.error_message = error_message
        
        if status == "success":
            sync.synced_at = datetime.now()
        
        db.commit()
        db.refresh(sync)
        
        return sync
