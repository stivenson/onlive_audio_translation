"""Translation service that processes transcript events and translates them."""

import asyncio
from typing import Optional
import logging

from app.translate.router import TranslateRouter
from app.core.event_bus import event_bus
from app.core.schemas import TranscriptEvent, TranslationResult
from app.config.settings import Settings
from app.llm.router import LLMRouter

logger = logging.getLogger(__name__)


class TranslationService:
    """Service that handles translation of transcripts."""
    
    def __init__(self, settings: Settings, llm_router: Optional[LLMRouter] = None):
        """
        Initialize translation service.
        
        Args:
            settings: Application settings
            llm_router: Optional LLM router for LLM-based translation
        """
        self.settings = settings
        self.translate_router = TranslateRouter(settings, llm_router)
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start translation service."""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Subscribe to transcript events
        event_bus.subscribe("transcript", self._handle_transcript)
        
        logger.info("Translation service started")
    
    def _detect_english_words(self, text: str) -> bool:
        """
        Detect if text contains common English words.
        
        This is a simple heuristic to catch obvious English text.
        """
        english_words = {
            'the', 'and', 'is', 'are', 'was', 'were', 'to', 'of', 'in', 'for',
            'on', 'with', 'at', 'by', 'from', 'that', 'this', 'you', 'it', 'have',
            'what', 'when', 'where', 'why', 'how', 'but', 'want', 'need', 'can',
            'will', 'would', 'should', 'could', 'into', 'because', 'they', 'them'
        }
        
        words = text.lower().split()
        english_count = sum(1 for word in words if word.strip('.,!?;:') in english_words)
        
        # If more than 30% of words are common English words, consider it English
        if len(words) > 0 and (english_count / len(words)) > 0.3:
            return True
        return False
    
    async def _handle_transcript(self, event: TranscriptEvent):
        """Handle transcript event and translate if needed."""
        if not self.is_running:
            return
        
        # Only translate final transcripts
        if event.transcript_type.value != "final":
            return
        
        # Skip if text is empty
        if not event.text or not event.text.strip():
            return
        
        try:
            text = event.text.strip()
            target_language = "es"
            
            # Step 1: Detect language with multiple checks
            source_language = event.language
            if not source_language or self.settings.auto_detect_language:
                source_language = await self.translate_router.detect_language(text)
                logger.info(f"Detected language: '{source_language}' for text: '{text[:50]}...'")
            
            # Step 2: Validate detection with English word heuristic
            contains_english = self._detect_english_words(text)
            if contains_english and source_language == "es":
                logger.warning(
                    f"Detection said Spanish but text contains English words. "
                    f"Overriding to English: '{text[:50]}...'"
                )
                source_language = "en"
            
            # Step 3: Check for discrepancy with checkbox
            if self.settings.audio_is_spanish and source_language != "es":
                logger.warning(
                    f"Discrepancy: 'Audio en Español' checkbox is marked, "
                    f"but detected language is '{source_language}'. Will translate anyway."
                )
            
            # Step 4: Translate aggressively - when in doubt, translate!
            # Only skip translation if we're VERY sure it's already Spanish
            if source_language == target_language and not contains_english:
                # Confirmed Spanish, pass through
                logger.debug(f"Text is Spanish, passing through: '{text[:50]}...'")
                translation = TranslationResult(
                    original_text=text,
                    translated_text=text,
                    source_language=source_language,
                    target_language=target_language
                )
            else:
                # Not Spanish OR uncertain - always translate
                logger.info(f"Translating from '{source_language}' to '{target_language}': '{text[:50]}...'")
                
                translation = await self.translate_router.translate(
                    text=text,
                    source_language=source_language if source_language != "es" else "en",
                    target_language=target_language
                )
                
                # Step 5: Validate translation result
                if translation.translated_text == text:
                    logger.warning(
                        f"Translation returned same text as input! "
                        f"Original: '{text[:50]}...', Translated: '{translation.translated_text[:50]}...'"
                    )
                    
                    # If translation didn't change and input was English, something went wrong
                    if contains_english or source_language == "en":
                        logger.error(
                            f"Translation FAILED - English text not translated: '{text[:50]}...'"
                        )
                        # Don't publish this - it would show English in Spanish column
                        return
                
                logger.info(f"Translation successful: '{translation.translated_text[:50]}...'")
            
            # Publish translation event
            await event_bus.publish("translation", translation)
        
        except Exception as e:
            logger.error(f"Translation error for text '{event.text[:50]}...': {e}", exc_info=True)
            # Don't publish anything if translation fails - better to have nothing
            # than English text in Spanish column
    
    async def stop(self):
        """Stop translation service."""
        if not self.is_running:
            return
        
        self.is_running = False
        event_bus.unsubscribe("transcript", self._handle_transcript)
        logger.info("Translation service stopped")
    
    def get_current_provider_name(self) -> str:
        """Get current translation provider name."""
        return self.translate_router.get_current_provider_name()
    
    def get_health_status(self):
        """Get health status of translation providers."""
        return self.translate_router.get_health_status()

