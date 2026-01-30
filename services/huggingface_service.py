"""
Local Whisper transcription service
"""

import whisper
import tempfile
import os
from typing import Dict
from config import settings
import logging

logger = logging.getLogger(__name__)


class HuggingFaceService:
    """
    Local Whisper transcription service
    """
    
    def __init__(self):
        self.model = None
        self.model_name = "base"  # Using whisper-base
    
    def _load_model(self):
        """Load Whisper model (lazy loading)"""
        if self.model is None:
            logger.info(f"Loading Whisper model: {self.model_name}")
            self.model = whisper.load_model(self.model_name)
            logger.info("Whisper model loaded successfully")
        return self.model
    
    def transcribe_audio(self, audio_bytes: bytes, content_type: str) -> Dict:
        """
        Transcribe audio using local Whisper model
        
        Args:
            audio_bytes: Audio file bytes
            content_type: MIME type of the file
            
        Returns:
            Dict with transcription result
        """
        
        try:
            # Load model
            model = self._load_model()
            
            # Determinar extensión basada en content_type
            suffix_map = {
                "audio/webm": ".webm",
                "audio/ogg": ".ogg",
                "audio/mp4": ".mp4",
                "audio/mpeg": ".mp3",
                "audio/wav": ".wav",
                "audio/x-wav": ".wav",
                "audio/m4a": ".m4a",
                "audio/x-m4a": ".m4a",
                "audio/flac": ".flac"
            }
            suffix = suffix_map.get(content_type.split(';')[0], ".webm")
            
            # Save audio bytes to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(audio_bytes)
                temp_path = temp_file.name
            
            logger.info(f"Transcribing audio file: {temp_path}")
            logger.info(f"Audio size: {len(audio_bytes)} bytes, content_type: {content_type}")
            
            # Optimizar parámetros para chunks pequeños (tiempo real)
            # Para chunks pequeños, usar parámetros más rápidos
            is_small_chunk = len(audio_bytes) < 50000  # Menos de ~50KB
            
            transcribe_options = {
                "language": "es",
                "task": "transcribe",
                "fp16": False,  # Usar float32 para mejor compatibilidad
            }
            
            # Para chunks pequeños, usar beam_size más pequeño para velocidad
            if is_small_chunk:
                transcribe_options["beam_size"] = 1  # Más rápido para chunks pequeños
                transcribe_options["best_of"] = 1
                logger.info("Using fast mode for small chunk")
            else:
                transcribe_options["beam_size"] = 5  # Mejor calidad para chunks grandes
                transcribe_options["best_of"] = 5
            
            # Transcribe using Whisper
            result = model.transcribe(temp_path, **transcribe_options)
            
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except Exception as cleanup_error:
                logger.warning(f"Could not delete temp file: {cleanup_error}")
            
            text = result["text"].strip()
            logger.info(f"Transcription successful: {len(text)} characters")
            
            return {
                "text": text,
                "status": "success"
            }
        
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }

