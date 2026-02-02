"""
Transcription endpoints
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import time
import json
import asyncio

from database import get_db
from config import settings
from services.transcription_service import TranscriptionService
from services.ai_medical_service import AIMedicalService

import logging
logger = logging.getLogger(__name__)

# Import HuggingFaceService with error handling (Whisper)
try:
    from services.huggingface_service import HuggingFaceService
    HUGGINGFACE_SERVICE_AVAILABLE = True
except ImportError as e:
    HUGGINGFACE_SERVICE_AVAILABLE = False
    HuggingFaceService = None
    logger.warning(f"HuggingFaceService (Whisper) not available: {e}")

# Import DeepgramService with error handling
try:
    from services.deepgram_service import DeepgramService
    DEEPGRAM_SERVICE_AVAILABLE = True
except ImportError as e:
    DEEPGRAM_SERVICE_AVAILABLE = False
    DeepgramService = None
    logger.warning(f"DeepgramService not available: {e}")

# Import DeepgramStreamingService for real-time transcription
try:
    from services.deepgram_streaming_service import DeepgramStreamingService
    DEEPGRAM_STREAMING_AVAILABLE = True
except ImportError as e:
    DEEPGRAM_STREAMING_AVAILABLE = False
    DeepgramStreamingService = None
    logger.warning(f"DeepgramStreamingService not available: {e}")
from schemas.transcription import (
    TranscriptionCreate, 
    TranscriptionResponse, 
    TranscriptionResponseDoctor,
    TranscriptionListResponse, 
    WorkflowStepResponse
)
from routers.auth import get_current_user
from models.user import User, UserRole
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union

router = APIRouter(prefix="/api/transcriptions", tags=["Transcriptions"])


def get_transcription_service():
    """
    Get the appropriate transcription service based on configuration.
    Returns tuple: (service_instance, provider_name, model_id)
    """
    provider = settings.TRANSCRIPTION_PROVIDER.lower()
    
    # If auto mode, try Deepgram first if API key is available
    if provider == "auto":
        if DEEPGRAM_SERVICE_AVAILABLE and settings.DEEPGRAM_API_KEY:
            logger.info("Using Deepgram (auto mode)")
            return DeepgramService(), "deepgram", f"deepgram/{settings.DEEPGRAM_MODEL}"
        elif HUGGINGFACE_SERVICE_AVAILABLE:
            logger.info("Using HuggingFace (auto mode, Deepgram not configured or unavailable)")
            return HuggingFaceService(), "huggingface", settings.AVAILABLE_MODELS[settings.DEFAULT_MODEL]["id"]
        else:
            raise HTTPException(
                status_code=503,
                detail="No transcription service available. Please configure Deepgram API key or install Whisper."
            )
    
    # Explicit provider selection
    elif provider == "deepgram":
        if not DEEPGRAM_SERVICE_AVAILABLE:
            if HUGGINGFACE_SERVICE_AVAILABLE:
                logger.warning("Deepgram requested but service not available. Falling back to HuggingFace.")
                return HuggingFaceService(), "huggingface", settings.AVAILABLE_MODELS[settings.DEFAULT_MODEL]["id"]
            else:
                raise HTTPException(
                    status_code=503,
                    detail="Deepgram service not available and HuggingFace (Whisper) is not installed."
                )
        if not settings.DEEPGRAM_API_KEY:
            if HUGGINGFACE_SERVICE_AVAILABLE:
                logger.warning("Deepgram requested but API key not configured. Falling back to HuggingFace.")
                return HuggingFaceService(), "huggingface", settings.AVAILABLE_MODELS[settings.DEFAULT_MODEL]["id"]
            else:
                raise HTTPException(
                    status_code=503,
                    detail="Deepgram API key not configured and HuggingFace (Whisper) is not installed."
                )
        logger.info("Using Deepgram (explicit)")
        return DeepgramService(), "deepgram", f"deepgram/{settings.DEEPGRAM_MODEL}"
    
    elif provider == "huggingface":
        if not HUGGINGFACE_SERVICE_AVAILABLE:
            if DEEPGRAM_SERVICE_AVAILABLE and settings.DEEPGRAM_API_KEY:
                logger.warning("HuggingFace requested but not available. Falling back to Deepgram.")
                return DeepgramService(), "deepgram", f"deepgram/{settings.DEEPGRAM_MODEL}"
            else:
                raise HTTPException(
                    status_code=503,
                    detail="HuggingFace (Whisper) service not available. Please install openai-whisper or configure Deepgram."
                )
        logger.info("Using HuggingFace (explicit)")
        return HuggingFaceService(), "huggingface", settings.AVAILABLE_MODELS[settings.DEFAULT_MODEL]["id"]
    
    else:
        # Fallback logic
        if DEEPGRAM_SERVICE_AVAILABLE and settings.DEEPGRAM_API_KEY:
            logger.warning(f"Unknown provider '{provider}'. Using Deepgram as fallback.")
            return DeepgramService(), "deepgram", f"deepgram/{settings.DEEPGRAM_MODEL}"
        elif HUGGINGFACE_SERVICE_AVAILABLE:
            logger.warning(f"Unknown provider '{provider}'. Using HuggingFace as fallback.")
            return HuggingFaceService(), "huggingface", settings.AVAILABLE_MODELS[settings.DEFAULT_MODEL]["id"]
        else:
            raise HTTPException(
                status_code=503,
                detail="No transcription service available. Please configure Deepgram API key or install Whisper."
            )


def filter_transcription_for_role(transcription, user: User):
    """Filtra la transcripción según el rol del usuario"""
    from models.transcription import Transcription
    
    if user.role == UserRole.DOCTOR:
        # Para doctores, crear una copia sin códigos ni formularios
        return TranscriptionResponseDoctor(
            id=transcription.id,
            filename=transcription.filename,
            file_size_mb=transcription.file_size_mb,
            content_type=transcription.content_type,
            text=transcription.text,
            processing_time_seconds=transcription.processing_time_seconds,
            model=transcription.model,
            provider=transcription.provider,
            medical_note=transcription.medical_note,
            workflow_status=transcription.workflow_status,
            created_at=transcription.created_at,
            updated_at=transcription.updated_at
        )
    else:
        # Para administradores, devolver todo
        return TranscriptionResponse.from_orm(transcription)


@router.post("/transcribe-chunk", response_model=Dict[str, Any])
async def transcribe_audio_chunk(
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Transcribe un chunk de audio para transcripción en tiempo real
    Retorna solo el texto transcrito del chunk
    """
    logger.info(f"Received chunk: {audio.filename}")
    
    # Leer chunk
    audio_bytes = await audio.read()
    
    if len(audio_bytes) == 0:
        return {"text": "", "status": "empty"}
    
    # Get transcription service (Deepgram or HuggingFace)
    transcription_service, provider, model_id = get_transcription_service()
    
    content_type = audio.content_type or "audio/webm"
    result = transcription_service.transcribe_audio(audio_bytes, content_type)
    
    if result["status"] == "error":
        return {"text": "", "status": "error", "message": result.get("message", "Error transcribing")}
    
    if result["status"] == "loading":
        return {"text": "", "status": "loading"}
    
    return {
        "text": result["text"],
        "status": "success"
    }


@router.post("/transcribe", response_model=Union[TranscriptionResponse, TranscriptionResponseDoctor])
async def transcribe_audio(
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Transcribe audio file to text
    
    - **audio**: Audio file (MP3, WAV, M4A, etc.)
    
    Returns:
        Transcription with metadata
    """
    
    logger.info(f"Received file: {audio.filename}")
    logger.info(f"Content-Type: {audio.content_type}")
    
    # Validar formato y detectar por extensión si es necesario
    content_type = audio.content_type
    
    # Si es octet-stream, detectar por extensión
    if content_type == "application/octet-stream":
        ext_to_mime = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".m4a": "audio/m4a",
            ".ogg": "audio/ogg",
            ".flac": "audio/flac",
            ".webm": "audio/webm"
        }
        
        filename_lower = audio.filename.lower() if audio.filename else ""
        for ext, mime in ext_to_mime.items():
            if filename_lower.endswith(ext):
                content_type = mime
                logger.info(f"Content-Type detected: {content_type}")
                break
    
    # Extract base content type (before semicolon for formats like "audio/webm;codecs=opus")
    base_content_type = content_type.split(';')[0].strip() if content_type else ""
    
    if base_content_type not in settings.ALLOWED_AUDIO_FORMATS and base_content_type != "application/octet-stream":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {content_type}"
        )
    
    # Leer archivo
    audio_bytes = await audio.read()
    file_size = len(audio_bytes)
    file_size_mb = file_size / (1024 * 1024)
    
    # Validate file size
    if file_size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {file_size_mb:.2f} MB. Maximum: {settings.MAX_FILE_SIZE_MB} MB"
        )
    
    # Get transcription service (Deepgram or HuggingFace)
    transcription_service, provider, model_id = get_transcription_service()
    
    start_time = time.time()
    result = transcription_service.transcribe_audio(audio_bytes, content_type)
    elapsed_time = time.time() - start_time
    
    # Validate result
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    
    if result["status"] == "loading":
        raise HTTPException(status_code=503, detail="Model is loading. Please retry in 30 seconds")
    
    # Save to database
    transcription_data = TranscriptionCreate(
        filename=audio.filename,
        file_size_mb=round(file_size_mb, 2),
        content_type=content_type,
        text=result["text"],
        processing_time_seconds=round(elapsed_time, 2),
        model=model_id,
        provider=provider
    )
    
    db_transcription = TranscriptionService.create_transcription(db, transcription_data)
    
    # Filtrar según rol
    return filter_transcription_for_role(db_transcription, current_user)


@router.get("/", response_model=TranscriptionListResponse)
def get_transcriptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of transcriptions
    
    - **skip**: Offset for pagination
    - **limit**: Number of results (max 100)
    
    Nota: Los doctores solo verán notas médicas, sin códigos ni formularios
    """
    
    transcriptions = TranscriptionService.get_transcriptions(db, skip=skip, limit=limit)
    total = TranscriptionService.count_transcriptions(db)
    
    # Filtrar según rol
    filtered_items = [filter_transcription_for_role(t, current_user) for t in transcriptions]
    
    return {
        "total": total,
        "items": filtered_items,
        "page": (skip // limit) + 1,
        "page_size": limit
    }


@router.get("/{transcription_id}", response_model=Union[TranscriptionResponse, TranscriptionResponseDoctor])
def get_transcription(
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get specific transcription by ID
    
    Nota: Los doctores solo verán notas médicas, sin códigos ni formularios
    """
    
    transcription = TranscriptionService.get_transcription(db, transcription_id)
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    # Filtrar según rol
    return filter_transcription_for_role(transcription, current_user)


@router.delete("/{transcription_id}")
def delete_transcription(
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a transcription
    """
    
    success = TranscriptionService.delete_transcription(db, transcription_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    return {"message": "Transcription deleted successfully"}


# ==================== Medical Workflow Endpoints ====================

class PatientInfo(BaseModel):
    """Optional patient information for CMS-1500 form"""
    name: Optional[str] = None
    dob: Optional[str] = None
    sex: Optional[str] = None
    address: Optional[str] = None
    city_state_zip: Optional[str] = None
    phone: Optional[str] = None
    id: Optional[str] = None
    insured_name: Optional[str] = None
    insured_id: Optional[str] = None
    insurance_group: Optional[str] = None


@router.post("/{transcription_id}/workflow/generate-note", response_model=WorkflowStepResponse)
def generate_medical_note(
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Step 2: Generate medical note from transcription
    """
    transcription = TranscriptionService.get_transcription(db, transcription_id)
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    ai_service = AIMedicalService()
    medical_note = ai_service.generate_medical_note(transcription.text)
    
    updated = TranscriptionService.update_medical_note(db, transcription_id, medical_note)
    
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update medical note")
    
    # Filtrar según rol
    filtered_transcription = filter_transcription_for_role(updated, current_user)
    
    return {
        "success": True,
        "message": "Medical note generated successfully",
        "transcription": filtered_transcription
    }


@router.post("/{transcription_id}/workflow/suggest-icd10", response_model=WorkflowStepResponse)
def suggest_icd10_codes(
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Step 3: Suggest ICD-10 codes based on medical note
    """
    transcription = TranscriptionService.get_transcription(db, transcription_id)
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    if not transcription.medical_note:
        raise HTTPException(status_code=400, detail="Medical note must be generated first")
    
    ai_service = AIMedicalService()
    icd10_codes = ai_service.suggest_icd10_codes(transcription.medical_note, transcription.text)
    
    updated = TranscriptionService.update_icd10_codes(db, transcription_id, icd10_codes)
    
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update ICD-10 codes")
    
    # Filtrar según rol
    filtered_transcription = filter_transcription_for_role(updated, current_user)
    
    return {
        "success": True,
        "message": "ICD-10 codes suggested successfully",
        "transcription": filtered_transcription
    }


@router.post("/{transcription_id}/workflow/suggest-cpt", response_model=WorkflowStepResponse)
def suggest_cpt_codes(
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Step 4: Suggest CPT codes with modifiers
    """
    transcription = TranscriptionService.get_transcription(db, transcription_id)
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    if not transcription.medical_note:
        raise HTTPException(status_code=400, detail="Medical note must be generated first")
    
    ai_service = AIMedicalService()
    cpt_codes = ai_service.suggest_cpt_codes(transcription.medical_note, transcription.text)
    
    updated = TranscriptionService.update_cpt_codes(db, transcription_id, cpt_codes)
    
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update CPT codes")
    
    # Filtrar según rol
    filtered_transcription = filter_transcription_for_role(updated, current_user)
    
    return {
        "success": True,
        "message": "CPT codes suggested successfully",
        "transcription": filtered_transcription
    }


@router.post("/{transcription_id}/workflow/generate-cms1500", response_model=WorkflowStepResponse)
def generate_cms1500_form(
    transcription_id: int,
    patient_info: Optional[PatientInfo] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Step 5: Generate CMS-1500 form data
    """
    transcription = TranscriptionService.get_transcription(db, transcription_id)
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    if not transcription.medical_note:
        raise HTTPException(status_code=400, detail="Medical note must be generated first")
    
    if not transcription.icd10_codes or not transcription.cpt_codes:
        raise HTTPException(status_code=400, detail="ICD-10 and CPT codes must be suggested first")
    
    ai_service = AIMedicalService()
    patient_dict = patient_info.dict() if patient_info else None
    cms1500_form = ai_service.generate_cms1500_form_data(
        transcription.medical_note,
        transcription.icd10_codes,
        transcription.cpt_codes,
        patient_dict
    )
    
    updated = TranscriptionService.update_cms1500_form(db, transcription_id, cms1500_form)
    
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update CMS-1500 form")
    
    # Filtrar según rol
    filtered_transcription = filter_transcription_for_role(updated, current_user)
    
    return {
        "success": True,
        "message": "CMS-1500 form generated successfully",
        "transcription": filtered_transcription
    }


@router.post("/{transcription_id}/workflow/run-full", response_model=WorkflowStepResponse)
def run_full_workflow(
    transcription_id: int,
    patient_info: Optional[PatientInfo] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Run complete workflow: Generate note -> Suggest ICD-10 -> Suggest CPT -> Generate CMS-1500
    """
    transcription = TranscriptionService.get_transcription(db, transcription_id)
    
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    ai_service = AIMedicalService()
    patient_dict = patient_info.dict() if patient_info else None
    
    workflow_result = ai_service.run_full_workflow(transcription.text, patient_dict)
    
    updated = TranscriptionService.update_full_workflow(
        db,
        transcription_id,
        workflow_result["medical_note"],
        workflow_result["icd10_codes"],
        workflow_result["cpt_codes"],
        workflow_result["cms1500_form_data"]
    )
    
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update workflow")
    
    # Filtrar según rol antes de devolver
    filtered_transcription = filter_transcription_for_role(updated, current_user)
    
    return {
        "success": True,
        "message": "Full workflow completed successfully",
        "transcription": filtered_transcription
    }


# ==================== Real-Time Streaming WebSocket ====================

@router.websocket("/stream")
async def websocket_transcription_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time audio transcription with Deepgram.
    
    Client sends:
    - Binary audio data (audio chunks)
    - JSON messages: {"type": "start"}, {"type": "stop"}
    
    Server sends:
    - JSON: {"type": "transcript", "text": "...", "is_final": true/false}
    - JSON: {"type": "error", "message": "..."}
    - JSON: {"type": "connected"}
    """
    await websocket.accept()
    logger.info("WebSocket connection accepted for streaming transcription")
    
    if not DEEPGRAM_STREAMING_AVAILABLE:
        await websocket.send_json({
            "type": "error",
            "message": "Deepgram streaming service not available"
        })
        await websocket.close()
        return
    
    if not settings.DEEPGRAM_API_KEY:
        await websocket.send_json({
            "type": "error", 
            "message": "DEEPGRAM_API_KEY not configured"
        })
        await websocket.close()
        return
    
    deepgram_service: Optional[DeepgramStreamingService] = None
    
    async def on_transcript(text: str, is_final: bool):
        """Callback when transcript is received from Deepgram"""
        try:
            await websocket.send_json({
                "type": "transcript",
                "text": text,
                "is_final": is_final
            })
        except Exception as e:
            logger.error(f"Error sending transcript to client: {e}")
    
    async def on_error(error_msg: str):
        """Callback when error occurs"""
        try:
            await websocket.send_json({
                "type": "error",
                "message": error_msg
            })
        except Exception as e:
            logger.error(f"Error sending error to client: {e}")
    
    try:
        # Create streaming service
        deepgram_service = DeepgramStreamingService(
            on_transcript=on_transcript,
            on_error=on_error
        )
        
        # Connect to Deepgram
        connected = await deepgram_service.connect(language="es")
        
        if not connected:
            await websocket.send_json({
                "type": "error",
                "message": "Failed to connect to Deepgram"
            })
            await websocket.close()
            return
        
        # Notify client that we're connected
        await websocket.send_json({"type": "connected"})
        
        # Main loop: receive audio from client and forward to Deepgram
        while True:
            try:
                # Receive data from client
                data = await websocket.receive()
                
                if "bytes" in data:
                    # Binary audio data - forward to Deepgram
                    audio_bytes = data["bytes"]
                    logger.debug(f"Received {len(audio_bytes)} bytes from client")
                    await deepgram_service.send_audio(audio_bytes)
                    
                elif "text" in data:
                    # JSON control message
                    try:
                        message = json.loads(data["text"])
                        msg_type = message.get("type")
                        
                        if msg_type == "stop":
                            logger.info("Client requested stop")
                            break
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON message: {data['text']}")
                        
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected by client")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket loop: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        # Cleanup
        if deepgram_service:
            await deepgram_service.close()
        try:
            await websocket.close()
        except:
            pass
        logger.info("WebSocket connection closed")

