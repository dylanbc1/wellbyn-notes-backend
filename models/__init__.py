"""
Models package - Versión Demo
"""

from models.transcription import Transcription
from models.ehr_connection import EHRConnection, EHRSync
from models.user import User, Session, UserRole
from models.metrics import (
    DoctorMetrics, OperationalMetrics, DocumentationCompletenessReport,
    CodingReport, DenialRiskIndicator, EHRAuditLog
)

__all__ = [
    "Transcription", "EHRConnection", "EHRSync", "User", "Session", "UserRole",
    "DoctorMetrics", "OperationalMetrics", "DocumentationCompletenessReport",
    "CodingReport", "DenialRiskIndicator", "EHRAuditLog"
]

