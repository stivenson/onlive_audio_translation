"""Base classes and interfaces for STT providers."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional
import numpy as np

from app.core.schemas import TranscriptEvent


class STTProvider(ABC):
    """Abstract base class for STT providers."""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.config = kwargs
    
    @abstractmethod
    async def stream(
        self, 
        audio_stream: AsyncIterator[bytes],
        sample_rate: int = 16000,
        language: Optional[str] = None,
        diarize: bool = True,
        punctuate: bool = True
    ) -> AsyncIterator[TranscriptEvent]:
        """
        Stream audio and yield transcript events.
        
        Args:
            audio_stream: Async iterator of audio frames (bytes)
            sample_rate: Audio sample rate
            language: Language hint (e.g., "en", "es")
            diarize: Enable speaker diarization
            punctuate: Enable punctuation
            
        Yields:
            TranscriptEvent objects (interim and final)
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy and accessible."""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of this provider."""
        pass
    
    async def close(self):
        """Clean up resources."""
        pass

