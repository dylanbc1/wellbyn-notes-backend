"""
Deepgram transcription service
"""

import io
import logging
from typing import Dict

try:
    from deepgram import DeepgramClient
    DEEPGRAM_AVAILABLE = True
except ImportError as e:
    DEEPGRAM_AVAILABLE = False
    logging.warning(f"Deepgram SDK not available: {e}")

from config import settings

logger = logging.getLogger(__name__)


class DeepgramService:
    """
    Deepgram transcription service for audio transcription
    """
    
    def __init__(self):
        """Initialize Deepgram client"""
        if not DEEPGRAM_AVAILABLE:
            logger.warning("Deepgram SDK not installed. Install with: pip install deepgram-sdk")
            self.client = None
            return
        
        # Debug: Check API key from settings
        api_key = settings.DEEPGRAM_API_KEY
        logger.info(f"Deepgram API Key check: {'Present' if api_key else 'Missing'} (length: {len(api_key) if api_key else 0})")
        
        # Also check directly from environment as fallback
        import os
        env_api_key = os.getenv("DEEPGRAM_API_KEY", "")
        if not api_key and env_api_key:
            logger.warning("DEEPGRAM_API_KEY found in environment but not in settings. Using environment value.")
            api_key = env_api_key
            
        if not api_key:
            logger.warning("DEEPGRAM_API_KEY not configured. Deepgram service will not work.")
            self.client = None
        else:
            try:
                # DeepgramClient requires api_key as a keyword argument
                self.client = DeepgramClient(api_key=api_key)
                logger.info("Deepgram client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Deepgram client: {str(e)}")
                self.client = None
    
    def transcribe_audio(self, audio_bytes: bytes, content_type: str, language: str = "es") -> Dict:
        """
        Transcribe audio using Deepgram API
        
        Args:
            audio_bytes: Audio file bytes
            content_type: MIME type of the file
            language: Language code (default: "es" for Spanish)
            
        Returns:
            Dict with transcription result
        """
        
        if not self.client:
            return {
                "status": "error",
                "message": "Deepgram client not initialized. Check DEEPGRAM_API_KEY configuration."
            }
        
        try:
            logger.info(f"Transcribing audio with Deepgram: {len(audio_bytes)} bytes, content_type: {content_type}")
            
            # Create buffer from bytes
            audio_buffer = io.BytesIO(audio_bytes)
            # Source is just the buffer (mimetype is detected automatically or can be specified via encoding param)
            source = audio_buffer
            
            # Configure transcription options as keyword arguments
            # Using configured model (default: nova-2, good balance of speed and accuracy)
            model = settings.DEEPGRAM_MODEL
            
            # Transcribe using Deepgram - SDK 5.3+ uses client.listen.v1.media.transcribe_file()
            response = self.client.listen.v1.media.transcribe_file(
                request=source,
                model=model,  # Use configured model (nova-2 or nova-3)
                language=language,  # Spanish
                smart_format=True,  # Automatically format punctuation and capitalization
                punctuate=True,  # Add punctuation
                paragraphs=False,  # Don't split into paragraphs for now
                diarize=False,  # Speaker diarization (set to True if needed)
                multichannel=False,  # Single channel audio
            )
            
            # Extract transcription text
            # Deepgram response structure: response.results.channels[0].alternatives[0].transcript
            if response and hasattr(response, 'results'):
                if hasattr(response.results, 'channels') and len(response.results.channels) > 0:
                    channel = response.results.channels[0]
                    if hasattr(channel, 'alternatives') and len(channel.alternatives) > 0:
                        transcript = channel.alternatives[0].transcript
                        
                        logger.info(f"Deepgram transcription successful: {len(transcript)} characters")
                        
                        return {
                            "text": transcript.strip(),
                            "status": "success"
                        }
            
            # If we get here, the response structure was unexpected
            logger.error(f"Unexpected Deepgram response structure: {response}")
            return {
                "status": "error",
                "message": "Unexpected response format from Deepgram API"
            }
        
        except Exception as e:
            logger.error(f"Deepgram transcription error: {str(e)}")
            return {
                "status": "error",
                "message": f"Deepgram transcription failed: {str(e)}"
            }
