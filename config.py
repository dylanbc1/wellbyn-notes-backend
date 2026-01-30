"""
Application configuration
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file first
load_dotenv()


class Settings(BaseSettings):
    """Configuración de la aplicación"""
    
    # App
    APP_NAME: str = "Notes API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # CORS
    _allowed_origins = os.getenv("ALLOWED_ORIGINS", "")
    ALLOWED_ORIGINS: list = (
        _allowed_origins.split(",") if _allowed_origins 
        else ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"]
    )
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/notes"
    )
    
    # Google Gemini
    GEMINI_KEY: str = os.getenv("GEMINI_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")  # Free model for medical note generation
    
    # Hugging Face (optional, not required for local models)
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")
    
    # Deepgram API - Read directly from environment after load_dotenv()
    DEEPGRAM_API_KEY: str = os.getenv("DEEPGRAM_API_KEY", "").strip() if os.getenv("DEEPGRAM_API_KEY") else ""
    DEEPGRAM_MODEL: str = os.getenv("DEEPGRAM_MODEL", "nova-2").strip() if os.getenv("DEEPGRAM_MODEL") else "nova-2"
    
    # Transcription provider selection
    # Options: "huggingface" (local Whisper), "deepgram" (cloud), "auto" (try Deepgram first, fallback to local)
    TRANSCRIPTION_PROVIDER: str = os.getenv("TRANSCRIPTION_PROVIDER", "auto")
    
    # Transcription model (local)
    AVAILABLE_MODELS: dict = {
        "whisper-base": {
            "name": "Whisper Base (Local)",
            "id": "openai/whisper-base",
            "url": "local",
            "description": "Local Whisper Base model - Fast and efficient for multilingual transcription (74 MB)",
            "language": "multilingual",
            "speed": "fast",
            "quality": "good",
            "provider": "huggingface"
        },
        "deepgram-nova-2": {
            "name": "Deepgram Nova-2 (Cloud)",
            "id": "deepgram/nova-2",
            "url": "cloud",
            "description": "Deepgram Nova-2 model - High accuracy cloud transcription",
            "language": "multilingual",
            "speed": "very_fast",
            "quality": "excellent",
            "provider": "deepgram"
        },
        "deepgram-nova-3": {
            "name": "Deepgram Nova-3 (Cloud)",
            "id": "deepgram/nova-3",
            "url": "cloud",
            "description": "Deepgram Nova-3 model - Latest high accuracy cloud transcription",
            "language": "multilingual",
            "speed": "very_fast",
            "quality": "excellent",
            "provider": "deepgram"
        }
    }
    
    # Default model
    DEFAULT_MODEL: str = "whisper-base"
    
    # File Upload
    MAX_FILE_SIZE_MB: int = 25
    ALLOWED_AUDIO_FORMATS: list = [
        "audio/mpeg",
        "audio/wav", 
        "audio/x-wav",
        "audio/m4a",
        "audio/x-m4a",
        "audio/ogg",
        "audio/flac",
        "audio/webm",
        "application/octet-stream"
    ]
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    
    # EHR Integration
    SUPPORTED_EHRS: dict = {
        "eclinicalworks": {
            "name": "eClinicalWorks",
            "base_url": "https://fhir.eclinicalworks.com/fhir/r4",
            "fhir_version": "R4",
            "auth_url": "https://fhir.eclinicalworks.com/fhir/r4/authorize",
            "token_url": "https://fhir.eclinicalworks.com/fhir/r4/token",
            "scopes": ["patient/*.read", "user/*.write", "system/*.read"],
            "documentation": "https://fhir.eclinicalworks.com",
            "connect_url": "https://connect4.healow.com"
        },
        "athenahealth": {
            "name": "athenahealth",
            "base_url": "https://api.athenahealth.com/fhir/r4",
            "fhir_version": "R4",
            "auth_url": "https://api.athenahealth.com/oauth2/v1/authorize",
            "token_url": "https://api.athenahealth.com/oauth2/v1/token",
            "scopes": ["system/Patient.read", "system/Observation.write"],
            "documentation": "https://docs.athenahealth.com/api"
        },
        "epic": {
            "name": "Epic",
            "base_url": "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4",
            "fhir_version": "R4",
            "auth_url": "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize",
            "token_url": "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token",
            "scopes": ["patient/*.read", "user/*.write"],
            "documentation": "https://fhir.epic.com"
        },
        "cerner": {
            "name": "Cerner (Oracle Health)",
            "base_url": "https://fhir-ehr-code.cerner.com/r4",
            "fhir_version": "R4",
            "auth_url": "https://authorization.cerner.com/tenants/{tenant}/protocols/oauth2/profiles/smart-v1/personas/provider/authorize",
            "token_url": "https://authorization.cerner.com/tenants/{tenant}/protocols/oauth2/profiles/smart-v1/token",
            "scopes": ["patient/*.read", "user/*.write"],
            "documentation": "https://fhir.cerner.com"
        },
        "drchrono": {
            "name": "DrChrono",
            "base_url": "https://drchrono.com/fhir/r4",
            "fhir_version": "R4",
            "auth_url": "https://drchrono.com/o/authorize/",
            "token_url": "https://drchrono.com/o/token/",
            "scopes": ["patient:read", "user:write"],
            "documentation": "https://drchrono.com/api-docs"
        },
        "practicefusion": {
            "name": "Practice Fusion",
            "base_url": "{{BaseURL}}",  # Variable - depende de la práctica
            "fhir_version": "R4",
            "auth_url": "{{BaseURL}}/authorize",
            "token_url": "{{BaseURL}}/token",
            "well_known_url": "{{BaseURL}}/.well-known/smart-configuration",
            "scopes": [
                "openid",
                "fhirUser",
                "offline_access",
                "launch",
                "patient/*.read",
                "user/*.write"
            ],
            "documentation": "https://www.practicefusion.com/ehr-support/fhir-api-specifications",
            "sales_contact": "(415) 993-4977",
            "features": [
                "Standalone Launch",
                "EHR Launch",
                "System Apps (Client Credentials)",
                "Bulk Data Export"
            ],
            "notes": "Base URL es variable por práctica. Usar well-known endpoint para descubrir endpoints."
        }
    }
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env that aren't in the model


@lru_cache()
def get_settings() -> Settings:
    """
    Returns cached singleton settings instance
    """
    # Ensure we have the latest env vars
    load_dotenv(override=True)
    
    settings_instance = Settings()
    
    # Debug: Log Deepgram API key status and ensure it's set
    import logging
    logger = logging.getLogger(__name__)
    
    # Always check environment directly as source of truth
    env_key = os.getenv("DEEPGRAM_API_KEY", "").strip()
    if env_key:
        if not settings_instance.DEEPGRAM_API_KEY or settings_instance.DEEPGRAM_API_KEY != env_key:
            # Update the settings instance
            object.__setattr__(settings_instance, "DEEPGRAM_API_KEY", env_key)
            logger.info(f"Deepgram API Key loaded from environment (length: {len(env_key)})")
        else:
            logger.info(f"Deepgram API Key already set in settings (length: {len(env_key)})")
    else:
        logger.warning("DEEPGRAM_API_KEY not found in environment")
    
    return settings_instance


# Export settings instance
settings = get_settings()

