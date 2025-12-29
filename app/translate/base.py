"""Base classes and interfaces for translation providers."""

from abc import ABC, abstractmethod
from typing import Optional

from app.core.schemas import TranslationResult


class TranslateProvider(ABC):
    """Abstract base class for translation providers."""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.config = kwargs
    
    @abstractmethod
    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str = "es"
    ) -> TranslationResult:
        """
        Translate text from source to target language.
        
        Args:
            text: Text to translate
            source_language: Source language code (e.g., "en")
            target_language: Target language code (default: "es")
            
        Returns:
            TranslationResult with translated text
        """
        pass
    
    @abstractmethod
    async def detect_language(self, text: str) -> str:
        """
        Detect the language of the given text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Language code (e.g., "en", "es")
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

