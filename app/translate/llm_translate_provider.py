"""LLM-based translation provider."""

from typing import Optional
import logging

from app.translate.base import TranslateProvider
from app.core.schemas import TranslationResult
from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class LLMTranslateProvider(TranslateProvider):
    """Translation provider using LLM."""
    
    def __init__(self, llm_provider: LLMProvider, **kwargs):
        """
        Initialize LLM translation provider.
        
        Args:
            llm_provider: LLM provider instance
        """
        super().__init__(api_key=None, **kwargs)
        self.llm_provider = llm_provider
    
    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str = "es"
    ) -> TranslationResult:
        """Translate text using LLM."""
        if source_language == target_language:
            # No translation needed
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_language=source_language,
                target_language=target_language
            )
        
        # Create translation prompt
        lang_names = {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese"
        }
        
        source_name = lang_names.get(source_language, source_language)
        target_name = lang_names.get(target_language, target_language)
        
        prompt = f"""Translate the following text from {source_name} to {target_name}. 
Only provide the translation, no explanations or additional text.

Text to translate:
{text}

Translation:"""
        
        try:
            translated_text = await self.llm_provider.generate_text(
                prompt=prompt,
                temperature=0.3,
                max_tokens=500
            )
            
            # Clean up response (remove quotes, extra whitespace)
            translated_text = translated_text.strip().strip('"').strip("'")
            
            return TranslationResult(
                original_text=text,
                translated_text=translated_text,
                source_language=source_language,
                target_language=target_language
            )
        except Exception as e:
            logger.error(f"LLM translation failed: {e}")
            raise
    
    async def detect_language(self, text: str) -> str:
        """Detect language using LLM."""
        prompt = f"""Detect the language of the following text. Respond with only the ISO 639-1 language code (e.g., "en", "es", "fr").

Text:
{text}

Language code:"""
        
        try:
            result = await self.llm_provider.generate_text(
                prompt=prompt,
                temperature=0.1,
                max_tokens=10
            )
            
            # Extract language code
            lang_code = result.strip().lower()[:2]
            return lang_code
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return "en"  # Default to English
    
    async def health_check(self) -> bool:
        """Check if LLM provider is healthy."""
        return await self.llm_provider.health_check()
    
    def get_provider_name(self) -> str:
        return "llm"

