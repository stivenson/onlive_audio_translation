"""Hugging Face translation provider using Inference API."""

from typing import Optional
import logging

try:
    from huggingface_hub import InferenceClient
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

from app.translate.base import TranslateProvider
from app.core.schemas import TranslationResult

logger = logging.getLogger(__name__)


class HuggingFaceProvider(TranslateProvider):
    """Translation provider using Hugging Face Inference API."""
    
    def __init__(self, api_token: Optional[str] = None, model: str = "Helsinki-NLP/opus-mt-en-es", **kwargs):
        """
        Initialize Hugging Face translation provider.
        
        Args:
            api_token: Hugging Face API token
            model: Model name from Hugging Face (default: Helsinki-NLP/opus-mt-en-es)
        """
        super().__init__(api_key=api_token, **kwargs)
        
        if not HF_AVAILABLE:
            raise ImportError("huggingface-hub not installed")
        
        if not api_token:
            raise ValueError("Hugging Face API token required")
        
        self.model = model
        # Initialize client with provider and API token
        # Using "hf-inference" provider as shown in Hugging Face documentation
        self.client = InferenceClient(
            provider="hf-inference",
            api_key=api_token
        )
    
    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str = "es"
    ) -> TranslationResult:
        """Translate text using Hugging Face model."""
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
            
            # Use the translation method directly as shown in Hugging Face documentation
            # client.translation() returns the translated text directly
            # Reference: https://huggingface.co/docs/huggingface_hub/en/package_reference/inference_client
            result = self.client.translation(
                text,
                model=self.model
            )
            
            # Parse response - translation() method returns translated text directly
            # Handle different possible response formats for robustness
            if isinstance(result, str):
                translated_text = result
            elif isinstance(result, dict):
                # Some models might return a dict with translation_text key
                translated_text = result.get("translation_text", result.get("text", str(result)))
            elif isinstance(result, list) and len(result) > 0:
                # Some models might return a list
                if isinstance(result[0], dict):
                    translated_text = result[0].get("translation_text", result[0].get("text", str(result[0])))
                else:
                    translated_text = str(result[0])
            else:
                translated_text = str(result)
            
            # Clean up and validate
            translated_text = translated_text.strip()
            
            # If translation failed or returned empty, log warning
            if not translated_text:
                logger.warning(f"Empty translation result for text: {text[:50]}...")
                translated_text = text  # Fallback to original text
            
            return TranslationResult(
                original_text=text,
                translated_text=translated_text,
                source_language=source_language,
                target_language=target_language
            )
        
        except Exception as e:
            logger.error(f"Hugging Face translation failed: {e}")
            raise
    
    async def detect_language(self, text: str) -> str:
        """Detect language using Hugging Face language detection model."""
        try:
            # Use a language detection model
            # Note: This requires a separate model for language detection
            # For now, we'll use a simple heuristic or return default
            # You could use a model like "papluca/xlm-roberta-base-language-detection"
            
            # Simple heuristic: check for common Spanish words/patterns
            spanish_indicators = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le']
            text_lower = text.lower()
            spanish_count = sum(1 for word in spanish_indicators if word in text_lower)
            
            if spanish_count > 2:
                return "es"
            
            # Default to English
            return "en"
        
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return "en"  # Default to English
    
    async def health_check(self) -> bool:
        """Check if Hugging Face API is accessible."""
        try:
            # Simple health check - try to access the model with a minimal translation
            # Use a very short text to minimize API usage
            test_result = self.client.translation(
                "hello",
                model=self.model
            )
            
            # Validate that we got a meaningful response
            if test_result is None:
                return False
            
            result_str = str(test_result).strip()
            return len(result_str) > 0 and result_str.lower() != "hello"
        
        except Exception as e:
            logger.error(f"Hugging Face health check failed: {e}")
            return False
    
    def get_provider_name(self) -> str:
        return "huggingface"

