"""STT service that orchestrates audio capture, STT, and event publishing."""

import asyncio
from typing import Optional
import logging

from app.stt.router import STTRouter
from app.stt.speaker_mapper import SpeakerMapper
from app.audio.capture import AudioCapture
from app.audio.chunker import AudioChunker
from app.core.event_bus import event_bus
from app.core.schemas import TranscriptEvent
from app.config.settings import Settings

logger = logging.getLogger(__name__)


class STTService:
    """Service that handles audio capture and STT processing."""
    
    def __init__(self, settings: Settings):
        """
        Initialize STT service.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.stt_router = STTRouter(settings)
        self.speaker_mapper = SpeakerMapper()
        
        self.audio_capture: Optional[AudioCapture] = None
        self.audio_chunker: Optional[AudioChunker] = None
        self.is_running = False
        self._audio_queue: Optional[asyncio.Queue] = None
        self._stt_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start STT service."""
        if self.is_running:
            logger.warning("STT service already running")
            return
        
        self.is_running = True
        self._audio_queue = asyncio.Queue()
        
        # Initialize audio capture
        self.audio_capture = AudioCapture(
            sample_rate=self.settings.audio_sample_rate,
            channels=self.settings.audio_channels,
            chunk_size=self.settings.audio_chunk_size
        )
        
        # Initialize chunker
        self.audio_chunker = AudioChunker(
            sample_rate=self.settings.audio_sample_rate,
            buffer_seconds=self.settings.audio_buffer_seconds,
            chunk_size=self.settings.audio_chunk_size
        )
        
        # Set chunker callback
        def audio_callback(audio_data: bytes):
            """Callback for audio chunks."""
            if self._audio_queue:
                try:
                    self._audio_queue.put_nowait(audio_data)
                except asyncio.QueueFull:
                    logger.warning("Audio queue full, dropping chunk")
        
        self.audio_chunker.set_callback(audio_callback)
        self.audio_chunker.start()
        
        # Start audio capture
        self.audio_capture.start_capture(
            lambda data: self.audio_chunker.add_audio(data)
        )
        
        # Start STT processing task
        self._stt_task = asyncio.create_task(self._process_stt())
        
        logger.info("STT service started")
    
    async def _process_stt(self):
        """Process audio through STT."""
        async def audio_stream():
            """Async iterator for audio chunks."""
            while self.is_running:
                try:
                    chunk = await asyncio.wait_for(
                        self._audio_queue.get(),
                        timeout=1.0
                    )
                    yield chunk
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error getting audio chunk: {e}")
                    break
        
        try:
            async for transcript_event in self.stt_router.stream(
                audio_stream=audio_stream(),
                sample_rate=self.settings.audio_sample_rate,
                language=self.settings.default_language_hint if not self.settings.auto_detect_language else None,
                diarize=True,
                punctuate=True
            ):
                # Map speaker ID to User role
                if transcript_event.speaker_id:
                    user_role = self.speaker_mapper.get_user_role(transcript_event.speaker_id)
                    transcript_event.speaker_id = user_role
                
                # Publish transcript event
                await event_bus.publish("transcript", transcript_event)
        
        except Exception as e:
            logger.error(f"STT processing error: {e}")
            if self.is_running:
                # Try to restart
                logger.info("Attempting to restart STT processing...")
                await asyncio.sleep(2)
                if self.is_running:
                    self._stt_task = asyncio.create_task(self._process_stt())
    
    async def stop(self):
        """Stop STT service."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Stop audio capture
        if self.audio_capture:
            self.audio_capture.stop_capture()
        
        # Stop chunker
        if self.audio_chunker:
            self.audio_chunker.stop()
        
        # Cancel STT task
        if self._stt_task:
            self._stt_task.cancel()
            try:
                await self._stt_task
            except asyncio.CancelledError:
                pass
        
        # Close STT connections
        for provider in self.stt_router.providers:
            try:
                await provider.close()
            except Exception as e:
                logger.error(f"Error closing provider: {e}")
        
        logger.info("STT service stopped")
    
    def get_current_provider_name(self) -> str:
        """Get current STT provider name."""
        return self.stt_router.get_current_provider_name()
    
    def get_health_status(self):
        """Get health status of STT providers."""
        return self.stt_router.get_health_status()

