"""CTranslate2 local translation provider for fast inference."""

from typing import Optional
import logging
import os
from pathlib import Path

try:
    import ctranslate2
    import sentencepiece as spm
    CT2_AVAILABLE = True
except ImportError:
    CT2_AVAILABLE = False

from app.translate.base import TranslateProvider
from app.core.schemas import TranslationResult

logger = logging.getLogger(__name__)


class CTranslate2Provider(TranslateProvider):
    """Fast local translation provider using CTranslate2."""
    
    def __init__(self, model_path: str = "models/opus-mt-en-es-ct2", **kwargs):
        """
        Initialize CTranslate2 translation provider.
        
        Args:
            model_path: Path to the CTranslate2 model directory
        """
        super().__init__(**kwargs)
        
        if not CT2_AVAILABLE:
            raise ImportError(
                "ctranslate2 and sentencepiece not installed. "
                "Install with: pip install ctranslate2 sentencepiece"
            )
        
        self.model_path = Path(model_path)
        
        if not self.model_path.exists():
            raise ValueError(
                f"CTranslate2 model not found at {model_path}. "
                f"Please run the model conversion script first."
            )
        
        # Initialize translator
        logger.info(f"Loading CTranslate2 model from {model_path}")
        self.translator = ctranslate2.Translator(
            str(self.model_path),
            device="cpu",  # Can be changed to "cuda" if GPU available
            compute_type="int8"  # Quantized for speed
        )
        
        # Load SentencePiece tokenizer
        sp_model_path = self.model_path / "source.spm"
        if not sp_model_path.exists():
            # Try alternative path
            sp_model_path = self.model_path / "sentencepiece.model"
        
        if not sp_model_path.exists():
            raise ValueError(
                f"SentencePiece model not found in {model_path}. "
                f"Expected 'source.spm' or 'sentencepiece.model'"
            )
        
        self.sp_source = spm.SentencePieceProcessor()
        self.sp_source.load(str(sp_model_path))
        
        # Target tokenizer (usually same as source for OPUS-MT)
        sp_target_path = self.model_path / "target.spm"
        if sp_target_path.exists():
            self.sp_target = spm.SentencePieceProcessor()
            self.sp_target.load(str(sp_target_path))
        else:
            self.sp_target = self.sp_source
        
        logger.info("CTranslate2 provider initialized successfully")
    
    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str = "es"
    ) -> TranslationResult:
        """Translate text using CTranslate2."""
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
            
            # Tokenize input text
            source_tokens = self.sp_source.encode(text, out_type=str)
            
            # Translate
            results = self.translator.translate_batch(
                [source_tokens],
                beam_size=1,  # Faster with beam_size=1
                max_decoding_length=512
            )
            
            # Get the best hypothesis
            target_tokens = results[0].hypotheses[0]
            
            # Detokenize
            translated_text = self.sp_target.decode(target_tokens)
            
            # Clean up
            translated_text = translated_text.strip()
            
            if not translated_text:
                logger.error(f"Empty translation result for text: {text[:50]}...")
                raise Exception("CTranslate2 returned empty translation")
            
            return TranslationResult(
                original_text=text,
                translated_text=translated_text,
                source_language=source_language,
                target_language=target_language
            )
        
        except Exception as e:
            logger.error(f"CTranslate2 translation failed: {e}")
            raise
    
    async def detect_language(self, text: str) -> str:
        """
        Detect language using improved heuristics.
        
        Note: CTranslate2 doesn't include language detection.
        This uses improved heuristics for Spanish/English detection.
        """
        try:
            # Expanded Spanish indicators
            spanish_indicators = {
                'el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 
                'no', 'te', 'lo', 'le', 'los', 'las', 'del', 'al', 'por',
                'para', 'con', 'su', 'mi', 'tu', 'esta', 'este', 'están',
                'son', 'como', 'si', 'más', 'pero', 'sobre', 'también', 'muy'
            }
            
            # Common English words
            english_indicators = {
                'the', 'and', 'is', 'are', 'was', 'were', 'to', 'of', 'in', 'for',
                'on', 'with', 'at', 'by', 'from', 'that', 'this', 'you', 'it', 'have',
                'what', 'when', 'where', 'why', 'how', 'but', 'want', 'into', 'because'
            }
            
            text_lower = text.lower()
            words = [word.strip('.,!?;:') for word in text_lower.split()]
            
            if len(words) == 0:
                return "en"  # Default to English for empty text
            
            spanish_count = sum(1 for word in words if word in spanish_indicators)
            english_count = sum(1 for word in words if word in english_indicators)
            
            spanish_ratio = spanish_count / len(words)
            english_ratio = english_count / len(words)
            
            logger.debug(f"Language detection - Spanish: {spanish_ratio:.2%}, English: {english_ratio:.2%}")
            
            # If English ratio is significant, it's likely English
            if english_ratio > 0.25:
                return "en"
            
            # If Spanish ratio is significant, it's likely Spanish
            if spanish_ratio > 0.20:
                return "es"
            
            # When in doubt, default to English (safer to translate than not)
            return "en"
        
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return "en"  # Default to English
    
    async def health_check(self) -> bool:
        """Check if CTranslate2 model is loaded and working."""
        try:
            # Simple health check - try a minimal translation
            test_tokens = self.sp_source.encode("hello", out_type=str)
            results = self.translator.translate_batch(
                [test_tokens],
                beam_size=1,
                max_decoding_length=10
            )
            
            # Check that we got a result
            if not results or not results[0].hypotheses:
                return False
            
            return True
        
        except Exception as e:
            logger.error(f"CTranslate2 health check failed: {e}")
            return False
    
    def get_provider_name(self) -> str:
        return "ctranslate2"

