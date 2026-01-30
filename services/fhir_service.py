"""
Servicio para integración con EHRs usando FHIR/SMART on FHIR
"""

import requests
import logging
import base64
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlencode
import json

logger = logging.getLogger(__name__)


class FHIRService:
    """
    Servicio base para integración FHIR/SMART on FHIR
    """
    
    def __init__(self, base_url: str, client_id: Optional[str] = None, 
                 client_secret: Optional[str] = None, fhir_version: str = "R4"):
        self.base_url = base_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.fhir_version = fhir_version
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        
    def get_authorization_url(self, redirect_uri: str, scopes: List[str], 
                             state: Optional[str] = None) -> str:
        """
        Genera URL de autorización OAuth2 para SMART on FHIR
        
        Args:
            redirect_uri: URI de redirección después de autorización
            scopes: Lista de scopes solicitados (ej: ["patient/*.read", "user/*.write"])
            state: Estado opcional para prevenir CSRF
            
        Returns:
            URL de autorización
        """
        auth_endpoint = f"{self.base_url}/authorize"
        
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "aud": self.base_url
        }
        
        if state:
            params["state"] = state
            
        return f"{auth_endpoint}?{urlencode(params)}"
    
    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Intercambia código de autorización por tokens de acceso
        
        Args:
            code: Código de autorización recibido
            redirect_uri: URI de redirección usado en autorización
            
        Returns:
            Diccionario con access_token, refresh_token, expires_in, etc.
        """
        token_endpoint = f"{self.base_url}/token"
        
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
        }
        
        if self.client_secret:
            data["client_secret"] = self.client_secret
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        try:
            response = requests.post(token_endpoint, data=data, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error exchanging code for token: {e}")
            raise
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresca el token de acceso usando refresh token
        
        Args:
            refresh_token: Refresh token actual
            
        Returns:
            Nuevo diccionario con tokens
        """
        token_endpoint = f"{self.base_url}/token"
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
        }
        
        if self.client_secret:
            data["client_secret"] = self.client_secret
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        try:
            response = requests.post(token_endpoint, data=data, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error refreshing token: {e}")
            raise
    
    def set_access_token(self, access_token: str, expires_in: Optional[int] = None):
        """
        Establece el token de acceso
        
        Args:
            access_token: Token de acceso
            expires_in: Segundos hasta expiración
        """
        self.access_token = access_token
        if expires_in:
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
        else:
            self.token_expires_at = None
    
    def _ensure_valid_token(self, refresh_token: Optional[str] = None):
        """
        Asegura que el token sea válido, refrescándolo si es necesario
        """
        if not self.access_token:
            raise ValueError("No access token available")
        
        if self.token_expires_at and datetime.now() >= self.token_expires_at - timedelta(minutes=5):
            if refresh_token:
                logger.info("Refreshing access token...")
                token_data = self.refresh_access_token(refresh_token)
                self.set_access_token(
                    token_data["access_token"],
                    token_data.get("expires_in")
                )
                return token_data.get("refresh_token", refresh_token)
            else:
                raise ValueError("Token expired and no refresh token available")
        
        return refresh_token
    
    def _make_fhir_request(self, method: str, resource_path: str, 
                          data: Optional[Dict] = None, params: Optional[Dict] = None,
                          refresh_token: Optional[str] = None) -> requests.Response:
        """
        Realiza una petición FHIR autenticada
        
        Args:
            method: Método HTTP (GET, POST, PUT, PATCH)
            resource_path: Ruta del recurso FHIR (ej: "Patient/123")
            data: Datos para POST/PUT/PATCH
            params: Parámetros de query
            refresh_token: Refresh token para renovar si es necesario
        """
        self._ensure_valid_token(refresh_token)
        
        url = urljoin(self.base_url + "/", resource_path)
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/fhir+json",
            "Accept": "application/fhir+json"
        }
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, params=params)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data, params=params)
            elif method.upper() == "PATCH":
                response = requests.patch(url, headers=headers, json=data, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"FHIR request failed: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise
    
    # Métodos FHIR comunes
    
    def get_patient(self, patient_id: str, refresh_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene información de un paciente
        
        Args:
            patient_id: ID del paciente en el EHR
            
        Returns:
            Recurso FHIR Patient
        """
        response = self._make_fhir_request("GET", f"Patient/{patient_id}", refresh_token=refresh_token)
        return response.json()
    
    def search_patients(self, name: Optional[str] = None, identifier: Optional[str] = None,
                       birthdate: Optional[str] = None, refresh_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Busca pacientes
        
        Args:
            name: Nombre del paciente
            identifier: Identificador (MRN, SSN, etc.)
            birthdate: Fecha de nacimiento (YYYY-MM-DD)
            
        Returns:
            Bundle con resultados de búsqueda
        """
        params = {}
        if name:
            params["name"] = name
        if identifier:
            params["identifier"] = identifier
        if birthdate:
            params["birthdate"] = birthdate
        
        response = self._make_fhir_request("GET", "Patient", params=params, refresh_token=refresh_token)
        return response.json()
    
    def create_observation(self, observation_data: Dict[str, Any], 
                          refresh_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Crea una observación (resultado de laboratorio, signo vital, etc.)
        
        Args:
            observation_data: Recurso FHIR Observation
            
        Returns:
            Recurso Observation creado
        """
        response = self._make_fhir_request("POST", "Observation", data=observation_data, refresh_token=refresh_token)
        return response.json()
    
    def create_condition(self, condition_data: Dict[str, Any],
                        refresh_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Crea un diagnóstico/condición
        
        Args:
            condition_data: Recurso FHIR Condition
            
        Returns:
            Recurso Condition creado
        """
        response = self._make_fhir_request("POST", "Condition", data=condition_data, refresh_token=refresh_token)
        return response.json()
    
    def create_procedure(self, procedure_data: Dict[str, Any],
                        refresh_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Crea un procedimiento
        
        Args:
            procedure_data: Recurso FHIR Procedure
            
        Returns:
            Recurso Procedure creado
        """
        response = self._make_fhir_request("POST", "Procedure", data=procedure_data, refresh_token=refresh_token)
        return response.json()
    
    def create_document_reference(self, document_data: Dict[str, Any],
                                 refresh_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Crea una referencia a documento (nota clínica, transcripción, etc.)
        
        Args:
            document_data: Recurso FHIR DocumentReference
            
        Returns:
            Recurso DocumentReference creado
        """
        response = self._make_fhir_request("POST", "DocumentReference", data=document_data, refresh_token=refresh_token)
        return response.json()
    
    def get_capability_statement(self) -> Dict[str, Any]:
        """
        Obtiene el capability statement del servidor FHIR (metadata)
        
        Returns:
            CapabilityStatement
        """
        response = requests.get(f"{self.base_url}/metadata")
        response.raise_for_status()
        return response.json()


class EClinicalWorksFHIRService(FHIRService):
    """
    Implementación específica para eClinicalWorks
    """
    
    def __init__(self, base_url: str = "https://fhir.eclinicalworks.com/fhir/r4",
                 client_id: Optional[str] = None, client_secret: Optional[str] = None):
        super().__init__(base_url, client_id, client_secret, fhir_version="R4")
    
    def sync_transcription_to_ehr(self, transcription_data: Dict[str, Any], 
                                  patient_id: str, refresh_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Sincroniza una transcripción con el EHR de eClinicalWorks
        
        Convierte la transcripción en recursos FHIR apropiados:
        - DocumentReference para la nota clínica
        - Condition para diagnósticos (ICD-10)
        - Procedure para procedimientos (CPT)
        
        Args:
            transcription_data: Datos de la transcripción (medical_note, icd10_codes, cpt_codes)
            patient_id: ID del paciente en el EHR
            refresh_token: Refresh token para renovar si es necesario
            
        Returns:
            Diccionario con los recursos creados
        """
        results = {}
        
        # 1. Crear DocumentReference para la nota clínica
        if transcription_data.get("medical_note"):
            document_ref = {
                "resourceType": "DocumentReference",
                "status": "current",
                "type": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "11506-3",
                        "display": "Progress note"
                    }]
                },
                "subject": {
                    "reference": f"Patient/{patient_id}"
                },
                "date": datetime.now().isoformat(),
                "content": [{
                    "attachment": {
                        "contentType": "text/plain",
                        "data": base64.b64encode(transcription_data["medical_note"].encode('utf-8')).decode('utf-8')
                    }
                }]
            }
            results["document_reference"] = self.create_document_reference(document_ref, refresh_token)
        
        # 2. Crear Conditions para diagnósticos ICD-10
        if transcription_data.get("icd10_codes"):
            conditions = []
            for icd10 in transcription_data["icd10_codes"]:
                condition = {
                    "resourceType": "Condition",
                    "clinicalStatus": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "active"
                        }]
                    },
                    "verificationStatus": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                            "code": "confirmed"
                        }]
                    },
                    "category": [{
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "439401001",
                            "display": "Diagnosis"
                        }]
                    }],
                    "code": {
                        "coding": [{
                            "system": "http://hl7.org/fhir/sid/icd-10-cm",
                            "code": icd10["code"],
                            "display": icd10["description"]
                        }]
                    },
                    "subject": {
                        "reference": f"Patient/{patient_id}"
                    },
                    "recordedDate": datetime.now().isoformat()
                }
                conditions.append(self.create_condition(condition, refresh_token))
            results["conditions"] = conditions
        
        # 3. Crear Procedures para procedimientos CPT
        if transcription_data.get("cpt_codes"):
            procedures = []
            for cpt in transcription_data["cpt_codes"]:
                procedure = {
                    "resourceType": "Procedure",
                    "status": "completed",
                    "code": {
                        "coding": [{
                            "system": "http://www.ama-assn.org/go/cpt",
                            "code": cpt["code"],
                            "display": cpt["description"]
                        }]
                    },
                    "subject": {
                        "reference": f"Patient/{patient_id}"
                    },
                    "performedDateTime": datetime.now().isoformat()
                }
                if cpt.get("modifier"):
                    procedure["modifierExtension"] = [{
                        "url": "http://hl7.org/fhir/StructureDefinition/procedure-modifier",
                        "valueCode": cpt["modifier"]
                    }]
                procedures.append(self.create_procedure(procedure, refresh_token))
            results["procedures"] = procedures
        
        return results
