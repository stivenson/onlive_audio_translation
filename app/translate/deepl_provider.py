"""DeepL translation provider for high-quality translations."""

from typing import Optional
import logging

try:
    import deepl
    DEEPL_AVAILABLE = True
except ImportError:
    DEEPL_AVAILABLE = False

from app.translate.base import TranslateProvider
from app.core.schemas import TranslationResult

logger = logging.getLogger(__name__)


class DeepLProvider(TranslateProvider):
    """Translation provider using DeepL API."""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize DeepL translation provider.
        
        Args:
            api_key: DeepL API key (required)
        """
        super().__init__(api_key=api_key, **kwargs)
        
        if not DEEPL_AVAILABLE:
            raise ImportError(
                "deepl not installed. Install with: pip install deepl"
            )
        
        if not api_key:
            raise ValueError("DeepL API key required")
        
        # Initialize DeepL translator
        self.translator = deepl.Translator(api_key)
        
        logger.info("DeepL provider initialized successfully")
    
    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str = "es"
    ) -> TranslationResult:
        """Translate text using DeepL API."""
        if source_language == target_language:
            # No translation needed
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_language=source_language,
                target_language=target_language
            )
        
        try:
            # Validate input
            if not text or not text.strip():
                logger.warning("Empty text provided for translation")
                return TranslationResult(
                    original_text=text,
                    translated_text=text,
                    source_language=source_language,
                    target_language=target_language
                )
            
            # DeepL expects uppercase language codes
            source_lang_code = source_language.upper()
            target_lang_code = target_language.upper()
            
            # DeepL uses specific codes for some languages
            # For Spanish: ES
            # For English: EN-US or EN-GB (we'll use EN-US)
            if target_lang_code == "ES":
                target_lang_code = "ES"  # Spanish (all variants)
            elif source_lang_code == "EN":
                source_lang_code = "EN"  # English (any variant)
            
            # Translate using DeepL
            result = self.translator.translate_text(
                text,
                source_lang=source_lang_code if source_lang_code != "EN" else None,
                target_lang=target_lang_code
            )
            
            # Extract translated text
            translated_text = result.text.strip()
            
            if not translated_text:
                logger.error(f"Empty translation result for text: {text[:50]}...")
                raise Exception("DeepL returned empty translation")
            
            # Get detected source language if it was auto-detected
            detected_lang = result.detected_source_lang.lower() if hasattr(result, 'detected_source_lang') else source_language
            
            return TranslationResult(
                original_text=text,
                translated_text=translated_text,
                source_language=detected_lang,
                target_language=target_language
            )
        
        except deepl.DeepLException as e:
            logger.error(f"DeepL API error: {e}")
            raise
        except Exception as e:
            logger.error(f"DeepL translation failed: {e}")
            raise
    
    async def detect_language(self, text: str) -> str:
        """Detect language using DeepL."""
        try:
            # DeepL doesn't have a dedicated detect endpoint,
            # but translate_text with target_lang will return detected_source_lang
            # We'll translate to a neutral target to detect the source
            result = self.translator.translate_text(
                text[:100],  # Use first 100 chars for detection
                target_lang="ES"
            )
            
            if hasattr(result, 'detected_source_lang'):
                detected = result.detected_source_lang.lower()
                logger.debug(f"Detected language: {detected}")
                return detected
            
            # Fallback
            return "en"
        
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return "en"  # Default to English
    
    async def health_check(self) -> bool:
        """Check if DeepL API is accessible."""
        try:
            # Check usage to verify API key and connectivity
            usage = self.translator.get_usage()
            
            # Check if we have any quota left
            if usage.character.limit_exceeded:
                logger.warning("DeepL character limit exceeded")
                return False
            
            logger.debug(
                f"DeepL usage: {usage.character.count}/{usage.character.limit} characters"
            )
            return True
        
        except deepl.AuthorizationException:
            logger.error("DeepL API authentication failed - invalid API key")
            return False
        except deepl.DeepLException as e:
            logger.error(f"DeepL API error during health check: {e}")
            return False
        except Exception as e:
            logger.error(f"DeepL health check failed: {e}")
            return False
    
    def get_provider_name(self) -> str:
        return "deepl"

