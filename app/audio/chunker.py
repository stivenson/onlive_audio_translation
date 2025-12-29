"""Audio chunking and buffering for streaming."""

import asyncio
from collections import deque
from typing import Optional, Callable
import logging

from app.audio.vad import SimpleVAD

logger = logging.getLogger(__name__)


class AudioChunker:
    """Chunks and buffers audio for streaming to STT providers."""
    
    def __init__(
        self,
        sample_rate: int = 16000,
        buffer_seconds: int = 3,
        chunk_size: int = 3200,
        vad: Optional[SimpleVAD] = None
    ):
        """
        Initialize audio chunker.
        
        Args:
            sample_rate: Audio sample rate
            buffer_seconds: Buffer duration in seconds
            chunk_size: Size of chunks to emit
            vad: Optional VAD instance for filtering silence
        """
        self.sample_rate = sample_rate
        self.buffer_seconds = buffer_seconds
        self.chunk_size = chunk_size
        # If vad is None, do not filter silence (required for some streaming STT providers
        # that will disconnect if they don't receive audio for a while).
        self.vad = vad
        
        # Circular buffer
        buffer_size = int(sample_rate * buffer_seconds * 2)  # 16-bit = 2 bytes per sample
        self.buffer = deque(maxlen=buffer_size)
        
        self.callback: Optional[Callable[[bytes], None]] = None
        self.is_running = False
    
    def add_audio(self, audio_data: bytes):
        """
        Add audio data to buffer.
        
        Args:
            audio_data: Raw audio bytes
        """
        if not self.is_running:
            return
        
        # Log first few chunks to verify audio is being received
        if not hasattr(self, '_audio_chunk_count'):
            self._audio_chunk_count = 0
        self._audio_chunk_count += 1
        
        if self._audio_chunk_count <= 3:
            logger.info(f"Audio chunker received chunk {self._audio_chunk_count}: {len(audio_data)} bytes")
        elif self._audio_chunk_count % 100 == 0:
            logger.debug(f"Audio chunker received chunk {self._audio_chunk_count}: {len(audio_data)} bytes")
        
        # Optionally filter silence
        if self.vad is not None and not self.vad.is_speech(audio_data):
            return
        
        # Add to buffer
        self.buffer.extend(audio_data)
        
        # Emit chunks if buffer is large enough
        chunks_emitted = 0
        while len(self.buffer) >= self.chunk_size:
            chunk = bytes([self.buffer.popleft() for _ in range(self.chunk_size)])
            if self.callback:
                try:
                    self.callback(chunk)
                    chunks_emitted += 1
                except Exception as e:
                    logger.error(f"Error in chunker callback: {e}")
        
        if chunks_emitted > 0 and self._audio_chunk_count <= 5:
            logger.info(f"Emitted {chunks_emitted} chunk(s) to STT (buffer size: {len(self.buffer)})")
        elif chunks_emitted > 0:
            logger.debug(f"Emitted {chunks_emitted} chunk(s) to STT")
    
    def set_callback(self, callback: Callable[[bytes], None]):
        """Set callback for audio chunks."""
        self.callback = callback
    
    def start(self):
        """Start chunking."""
        self.is_running = True
        logger.debug("Audio chunker started")
    
    def stop(self):
        """Stop chunking."""
        self.is_running = False
        self.buffer.clear()
        logger.debug("Audio chunker stopped")
    
    def get_buffer_size(self) -> int:
        """Get current buffer size in bytes."""
        return len(self.buffer)

