"""
Deepgram streaming transcription service for real-time audio
"""

import asyncio
import logging
import json
from typing import Callable, Optional
import websockets

from config import settings

logger = logging.getLogger(__name__)

# Deepgram WebSocket URL
DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen"


class DeepgramStreamingService:
    """
    Service for real-time streaming transcription using Deepgram WebSocket API
    """
    
    def __init__(self, on_transcript: Callable[[str, bool], None], on_error: Optional[Callable[[str], None]] = None):
        """
        Initialize the streaming service
        
        Args:
            on_transcript: Callback function called with (text, is_final)
            on_error: Optional callback for errors
        """
        self.on_transcript = on_transcript
        self.on_error = on_error
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self._receive_task: Optional[asyncio.Task] = None
        
    async def connect(self, language: str = "es") -> bool:
        """
        Connect to Deepgram WebSocket API
        
        Args:
            language: Language code (default: "es" for Spanish)
            
        Returns:
            True if connection successful
        """
        api_key = settings.DEEPGRAM_API_KEY
        
        if not api_key:
            logger.error("DEEPGRAM_API_KEY not configured")
            if self.on_error:
                self.on_error("DEEPGRAM_API_KEY not configured")
            return False
        
        try:
            # Build WebSocket URL with parameters
            model = settings.DEEPGRAM_MODEL
            params = {
                "model": model,
                "language": language,
                "punctuate": "true",
                "smart_format": "true",
                "interim_results": "true",  # Enable word-by-word updates
                "endpointing": "300",  # End speech detection after 300ms of silence
                "vad_events": "true",  # Voice activity detection
                "encoding": "linear16",  # Raw PCM 16-bit
                "sample_rate": "16000",  # 16kHz sample rate
                "channels": "1",
            }
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{DEEPGRAM_WS_URL}?{query_string}"
            
            logger.info(f"Connecting to Deepgram WebSocket: {url[:80]}...")
            
            # Connect with authentication header
            headers = {
                "Authorization": f"Token {api_key}"
            }
            
            self.websocket = await websockets.connect(
                url,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=10,
            )
            
            self.is_connected = True
            logger.info("Connected to Deepgram WebSocket successfully")
            
            # Start receiving messages in background
            self._receive_task = asyncio.create_task(self._receive_messages())
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Deepgram: {str(e)}")
            if self.on_error:
                self.on_error(f"Connection failed: {str(e)}")
            return False
    
    async def _receive_messages(self):
        """Background task to receive and process Deepgram responses"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    
                    # Check for transcription results
                    if data.get("type") == "Results":
                        channel = data.get("channel", {})
                        alternatives = channel.get("alternatives", [])
                        
                        if alternatives:
                            transcript = alternatives[0].get("transcript", "")
                            is_final = data.get("is_final", False)
                            
                            if transcript:
                                logger.debug(f"Transcript ({'final' if is_final else 'interim'}): {transcript[:50]}...")
                                self.on_transcript(transcript, is_final)
                    
                    elif data.get("type") == "Metadata":
                        logger.info(f"Deepgram metadata: request_id={data.get('request_id')}")
                    
                    elif data.get("type") == "SpeechStarted":
                        logger.debug("Speech started detected")
                    
                    elif data.get("type") == "UtteranceEnd":
                        logger.debug("Utterance end detected")
                    
                    elif data.get("type") == "Error":
                        error_msg = data.get("message", "Unknown error")
                        logger.error(f"Deepgram error: {error_msg}")
                        if self.on_error:
                            self.on_error(error_msg)
                            
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse Deepgram message: {e}")
                    
        except websockets.ConnectionClosed as e:
            logger.info(f"Deepgram WebSocket closed: {e}")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error receiving Deepgram messages: {e}")
            self.is_connected = False
            if self.on_error:
                self.on_error(str(e))
    
    async def send_audio(self, audio_data: bytes):
        """
        Send audio data to Deepgram
        
        Args:
            audio_data: Raw audio bytes
        """
        if not self.is_connected or not self.websocket:
            logger.warning("Cannot send audio: not connected")
            return
        
        try:
            await self.websocket.send(audio_data)
            logger.debug(f"Sent {len(audio_data)} bytes to Deepgram")
        except Exception as e:
            logger.error(f"Failed to send audio: {e}")
            if self.on_error:
                self.on_error(f"Send failed: {str(e)}")
    
    async def close(self):
        """Close the WebSocket connection"""
        self.is_connected = False
        
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            try:
                # Send close message to Deepgram
                await self.websocket.send(json.dumps({"type": "CloseStream"}))
                await self.websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
        
        logger.info("Deepgram streaming connection closed")
