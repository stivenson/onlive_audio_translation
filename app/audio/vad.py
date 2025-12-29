"""Voice Activity Detection (VAD) for audio chunks."""

import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SimpleVAD:
    """Simple Voice Activity Detection using energy threshold."""
    
    def __init__(
        self,
        energy_threshold: float = 0.01,
        frame_duration_ms: int = 20,
        sample_rate: int = 16000
    ):
        """
        Initialize VAD.
        
        Args:
            energy_threshold: Energy threshold for voice detection
            frame_duration_ms: Frame duration in milliseconds
            sample_rate: Audio sample rate
        """
        self.energy_threshold = energy_threshold
        self.frame_duration_ms = frame_duration_ms
        self.sample_rate = sample_rate
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
    
    def is_speech(self, audio_chunk: bytes) -> bool:
        """
        Determine if audio chunk contains speech.
        
        Args:
            audio_chunk: Raw audio bytes (16-bit PCM)
            
        Returns:
            True if speech detected, False otherwise
        """
        if len(audio_chunk) == 0:
            return False
        
        # Convert bytes to numpy array
        audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
        
        # Calculate RMS energy
        energy = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
        
        # Normalize (assuming 16-bit audio, max value is 32768)
        normalized_energy = energy / 32768.0
        
        return normalized_energy > self.energy_threshold
    
    def filter_silence(self, audio_chunks: list) -> list:
        """
        Filter out silent chunks from a list of audio chunks.
        
        Args:
            audio_chunks: List of audio chunks (bytes)
            
        Returns:
            List of non-silent chunks
        """
        return [chunk for chunk in audio_chunks if self.is_speech(chunk)]

