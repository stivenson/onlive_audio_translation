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
            # Detect language if not provided
            source_language = event.language
            if not source_language or self.settings.auto_detect_language:
                source_language = await self.translate_router.detect_language(event.text)
            
            # Translate if source is English (or if different from target)
            target_language = "es"
            if source_language == target_language:
                # Already in Spanish, just pass through
                translation = TranslationResult(
                    original_text=event.text,
                    translated_text=event.text,
                    source_language=source_language,
                    target_language=target_language
                )
            else:
                # Translate
                translation = await self.translate_router.translate(
                    text=event.text,
                    source_language=source_language,
                    target_language=target_language
                )
            
            # Publish translation event
            await event_bus.publish("translation", translation)
        
        except Exception as e:
            logger.error(f"Translation error: {e}")
    
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

