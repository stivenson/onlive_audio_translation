"""STT service that orchestrates audio capture, STT, and event publishing."""

import asyncio
from typing import Optional
from datetime import datetime, timedelta
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
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Health monitoring
        self.last_valid_transcript_time: Optional[datetime] = None
        self.reconnect_attempts = 0
        self.connection_healthy = True
    
    async def start(self):
        """Start STT service."""
        if self.is_running:
            logger.warning("STT service already running")
            return
        
        self.is_running = True
        self._loop = asyncio.get_running_loop()
        self._audio_queue = asyncio.Queue()
        
        # Initialize audio capture
        self.audio_capture = AudioCapture(
            sample_rate=self.settings.audio_sample_rate,
            channels=self.settings.audio_channels,
            chunk_size=self.settings.audio_chunk_size,
            device_index=self.settings.audio_device_index
        )
        
        # Initialize chunker
        self.audio_chunker = AudioChunker(
            sample_rate=self.settings.audio_sample_rate,
            buffer_seconds=self.settings.audio_buffer_seconds,
            chunk_size=self.settings.audio_chunk_size,
            vad=None  # Do not drop silence; Deepgram will disconnect if it receives no audio.
        )
        
        # Set chunker callback
        def audio_callback(audio_data: bytes):
            """Callback for audio chunks."""
            # NOTE: This callback is invoked from PyAudio's thread, not the asyncio loop thread.
            # asyncio.Queue is not thread-safe: we must enqueue via loop.call_soon_threadsafe.
            if not self._audio_queue or not self._loop:
                return

            def _enqueue():
                try:
                    self._audio_queue.put_nowait(audio_data)
                    if not hasattr(self, "_callback_count"):
                        self._callback_count = 0
                    self._callback_count += 1
                    if self._callback_count <= 5:
                        logger.info(f"Audio callback {self._callback_count}: queued {len(audio_data)} bytes")
                    elif self._callback_count % 100 == 0:
                        logger.debug(f"Audio callback {self._callback_count}: queued {len(audio_data)} bytes")
                except asyncio.QueueFull:
                    logger.warning("Audio queue full, dropping chunk")

            if self._loop.is_running():
                self._loop.call_soon_threadsafe(_enqueue)
            else:
                _enqueue()
        
        self.audio_chunker.set_callback(audio_callback)
        self.audio_chunker.start()
        
        # Start audio capture
        self.audio_capture.start_capture(
            lambda data: self.audio_chunker.add_audio(data)
        )
        
        # Start STT processing task
        self._stt_task = asyncio.create_task(self._process_stt_with_reconnect())
        
        # Start health monitoring task
        self._health_monitor_task = asyncio.create_task(self._monitor_health())
        
        logger.info("STT service started")
    
    async def _monitor_health(self):
        """Monitor health of STT connection and detect dead connections."""
        logger.info("STT health monitor started")
        
        while self.is_running:
            try:
                await asyncio.sleep(self.settings.stt_health_check_interval_seconds)
                
                if not self.is_running:
                    break
                
                # Check if we've received any valid transcripts recently
                if self.last_valid_transcript_time is not None:
                    time_since_last_transcript = (datetime.now() - self.last_valid_transcript_time).total_seconds()
                    
                    if time_since_last_transcript > self.settings.stt_no_transcript_timeout_seconds:
                        if self.connection_healthy:
                            logger.warning(
                                f"No valid transcripts received for {time_since_last_transcript:.1f}s "
                                f"(threshold: {self.settings.stt_no_transcript_timeout_seconds}s). "
                                "Connection may be dead."
                            )
                            self.connection_healthy = False
                    else:
                        if not self.connection_healthy:
                            logger.info("Connection recovered - receiving valid transcripts again")
                            self.connection_healthy = True
                            self.reconnect_attempts = 0  # Reset reconnect counter on recovery
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(5)
        
        logger.info("STT health monitor stopped")
    
    async def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        delay = min(
            self.settings.stt_reconnect_backoff_base ** attempt,
            self.settings.stt_reconnect_max_wait_seconds
        )
        return delay
    
    async def _process_stt_with_reconnect(self):
        """Process audio through STT with automatic reconnection."""
        while self.is_running:
            try:
                # Check if we've exceeded max reconnection attempts
                if self.reconnect_attempts >= self.settings.stt_max_reconnect_attempts:
                    logger.error(
                        f"Maximum reconnection attempts ({self.settings.stt_max_reconnect_attempts}) reached. "
                        "STT processing paused. Please check your connection or restart manually."
                    )
                    # Wait longer before trying again
                    await asyncio.sleep(60)
                    self.reconnect_attempts = 0  # Reset after long wait
                    continue
                
                # If this is a reconnection attempt (not first attempt)
                if self.reconnect_attempts > 0:
                    delay = await self._calculate_backoff_delay(self.reconnect_attempts - 1)
                    logger.info(
                        f"Reconnection attempt {self.reconnect_attempts}/{self.settings.stt_max_reconnect_attempts} "
                        f"- waiting {delay:.1f}s before retry..."
                    )
                    await asyncio.sleep(delay)
                
                # Try to process STT
                logger.info(f"Starting STT processing (attempt {self.reconnect_attempts + 1})")
                await self._process_stt()
                
                # If we get here, the stream ended normally (unlikely in streaming scenario)
                logger.info("STT stream ended normally")
                break
                
            except asyncio.CancelledError:
                logger.info("STT processing cancelled")
                raise
            except Exception as e:
                self.reconnect_attempts += 1
                logger.error(
                    f"STT processing error (attempt {self.reconnect_attempts}): {e}",
                    exc_info=True if self.reconnect_attempts == 1 else False
                )
                
                if not self.is_running:
                    break
                
                # Mark connection as unhealthy
                self.connection_healthy = False
                
                # Continue loop to attempt reconnection
                continue
    
    async def _process_stt(self):
        """Process audio through STT."""
        # Reset transcript timer at start of new connection
        self.last_valid_transcript_time = datetime.now()
        
        async def audio_stream():
            """Async iterator for audio chunks - batches audio into N-second chunks."""
            batch_seconds = self.settings.audio_batch_seconds
            bytes_per_second = self.settings.audio_sample_rate * 2  # 16-bit = 2 bytes per sample
            batch_size_bytes = bytes_per_second * batch_seconds
            
            batch_buffer = bytearray()
            batch_start_time = datetime.now()
            chunks_yielded = 0
            batches_sent = 0
            
            logger.info(f"Audio batching enabled: accumulating {batch_seconds}s ({batch_size_bytes} bytes) before sending")
            
            while self.is_running:
                try:
                    # Get chunk from queue
                    chunk = await asyncio.wait_for(
                        self._audio_queue.get(),
                        timeout=1.0
                    )
                    
                    # Add to batch buffer
                    batch_buffer.extend(chunk)
                    
                    # Check if we've accumulated enough for a batch
                    elapsed = (datetime.now() - batch_start_time).total_seconds()
                    if len(batch_buffer) >= batch_size_bytes or elapsed >= batch_seconds:
                        # Send the batch
                        if len(batch_buffer) > 0:
                            batch_data = bytes(batch_buffer)
                            batches_sent += 1
                            
                            if batches_sent <= 3:
                                logger.info(
                                    f"Sending audio batch {batches_sent}: {len(batch_data)} bytes "
                                    f"({len(batch_data) / bytes_per_second:.2f}s of audio)"
                                )
                            elif batches_sent % 10 == 0:
                                logger.debug(f"Sent {batches_sent} audio batches")
                            
                            yield batch_data
                            
                            # Reset batch
                            batch_buffer.clear()
                            batch_start_time = datetime.now()
                    
                except asyncio.TimeoutError:
                    # If we have accumulated audio but timeout, send it anyway
                    if len(batch_buffer) > 0:
                        elapsed = (datetime.now() - batch_start_time).total_seconds()
                        if elapsed >= batch_seconds * 0.5:  # Send if we have at least half a batch
                            batch_data = bytes(batch_buffer)
                            batches_sent += 1
                            logger.info(f"Sending partial batch {batches_sent}: {len(batch_data)} bytes (timeout)")
                            yield batch_data
                            batch_buffer.clear()
                            batch_start_time = datetime.now()
                    continue
                except Exception as e:
                    logger.error(f"Error getting audio chunk: {e}")
                    # Send any remaining buffer before breaking
                    if len(batch_buffer) > 0:
                        batch_data = bytes(batch_buffer)
                        logger.info(f"Sending final batch: {len(batch_data)} bytes")
                        yield batch_data
                    break
            
            # Send any remaining buffer when stopping
            if len(batch_buffer) > 0:
                batch_data = bytes(batch_buffer)
                logger.info(f"Sending final batch on stop: {len(batch_data)} bytes")
                yield batch_data
        
        # Determine language for STT
        if self.settings.audio_is_spanish:
            stt_language = "es"
        elif not self.settings.auto_detect_language:
            stt_language = self.settings.default_language_hint
        else:
            stt_language = None
        
        async for transcript_event in self.stt_router.stream(
            audio_stream=audio_stream(),
            sample_rate=self.settings.audio_sample_rate,
            language=stt_language,
            diarize=True,
            punctuate=True
        ):
            # Update health: we received a valid transcript
            if transcript_event.text and transcript_event.text.strip():
                self.last_valid_transcript_time = datetime.now()
                self.connection_healthy = True
                # Reset reconnect attempts on successful transcript
                if self.reconnect_attempts > 0:
                    logger.info("Connection successful - received valid transcript, resetting reconnect counter")
                    self.reconnect_attempts = 0
            
            # Map speaker ID to User role
            if transcript_event.speaker_id:
                user_role = self.speaker_mapper.get_user_role(transcript_event.speaker_id)
                transcript_event.speaker_id = user_role
            
            # Publish transcript event
            await event_bus.publish("transcript", transcript_event)
    
    async def stop(self):
        """Stop STT service."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel health monitor task
        if self._health_monitor_task:
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass
        
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

