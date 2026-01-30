"""
Schemas package
"""

from schemas.transcription import (
    TranscriptionCreate,
    TranscriptionResponse,
    TranscriptionListResponse
)
from schemas.ehr import (
    EHRConnectionCreate,
    EHRConnectionUpdate,
    EHRConnectionResponse,
    EHRTokenResponse,
    EHRAuthorizationRequest,
    EHRAuthorizationCallback,
    EHRSyncRequest,
    EHRSyncResponse,
    EHRPatientSearch,
    EHRPatientResponse,
    EHRListResponse
)

__all__ = [
    "TranscriptionCreate",
    "TranscriptionResponse",
    "TranscriptionListResponse",
    "EHRConnectionCreate",
    "EHRConnectionUpdate",
    "EHRConnectionResponse",
    "EHRTokenResponse",
    "EHRAuthorizationRequest",
    "EHRAuthorizationCallback",
    "EHRSyncRequest",
    "EHRSyncResponse",
    "EHRPatientSearch",
    "EHRPatientResponse",
    "EHRListResponse"
]

