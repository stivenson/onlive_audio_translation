"""Translation service that processes transcript events and translates them."""

import asyncio
import re
from typing import Optional, Dict
from datetime import datetime, timedelta
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
        
        # Sentence buffering for end-of-sentence detection
        self._sentence_buffers: Dict[str, str] = {}  # speaker_id -> buffered text
        self._buffer_timestamps: Dict[str, datetime] = {}  # speaker_id -> last update time
        self._last_speaker_id: Optional[str] = None
        self._buffer_timeout_seconds: int = 5  # Timeout to flush buffer if no punctuation
        self._buffer_check_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start translation service."""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Subscribe to transcript events
        event_bus.subscribe("transcript", self._handle_transcript)
        
        # Start buffer timeout check task
        self._buffer_check_task = asyncio.create_task(self._check_buffer_timeouts())
        
        logger.info("Translation service started")
    
    def _ends_with_sentence_punctuation(self, text: str) -> bool:
        """
        Check if text ends with sentence-ending punctuation.
        
        Handles common abbreviations to avoid false positives.
        """
        text = text.strip()
        if not text:
            return False
        
        # Common abbreviations that shouldn't trigger sentence end
        abbreviations = [
            r'Dr\.$', r'Mr\.$', r'Mrs\.$', r'Ms\.$', r'Prof\.$',
            r'Sr\.$', r'Jr\.$', r'Ph\.D\.$', r'M\.D\.$',
            r'etc\.$', r'vs\.$', r'i\.e\.$', r'e\.g\.$'
        ]
        
        # Check if text ends with an abbreviation
        for abbr_pattern in abbreviations:
            if re.search(abbr_pattern, text, re.IGNORECASE):
                return False
        
        # Check if ends with sentence punctuation (., !, ?)
        # Allow optional quotation marks or parentheses after punctuation
        return bool(re.search(r'[.!?]["\')]*\s*$', text))
    
    async def _check_buffer_timeouts(self):
        """Periodically check for buffers that have timed out and need flushing."""
        while self.is_running:
            try:
                await asyncio.sleep(1)  # Check every second
                
                current_time = datetime.now()
                speakers_to_flush = []
                
                # Find buffers that have exceeded timeout
                for speaker_id, timestamp in self._buffer_timestamps.items():
                    if speaker_id in self._sentence_buffers:
                        age = (current_time - timestamp).total_seconds()
                        if age >= self._buffer_timeout_seconds:
                            speakers_to_flush.append(speaker_id)
                
                # Flush timed-out buffers
                for speaker_id in speakers_to_flush:
                    if speaker_id in self._sentence_buffers:
                        buffered_text = self._sentence_buffers[speaker_id]
                        logger.info(f"Buffer timeout for {speaker_id}, flushing: '{buffered_text[:50]}...'")
                        await self._process_buffered_text(speaker_id, buffered_text)
                        del self._sentence_buffers[speaker_id]
                        del self._buffer_timestamps[speaker_id]
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in buffer timeout check: {e}")
    
    async def _process_buffered_text(self, speaker_id: str, text: str):
        """
        Process and translate buffered text.
        
        Args:
            speaker_id: Speaker identifier
            text: Accumulated text to translate
        """
        if not text or not text.strip():
            return
        
        try:
            text = text.strip()
            target_language = "es"
            
            # Detect language
            source_language = await self.translate_router.detect_language(text)
            logger.info(f"[{speaker_id}] Detected language: '{source_language}' for buffered text: '{text[:50]}...'")
            
            # Validate detection with English word heuristic
            contains_english = self._detect_english_words(text)
            if contains_english and source_language == "es":
                logger.warning(
                    f"[{speaker_id}] Detection said Spanish but text contains English words. "
                    f"Overriding to English: '{text[:50]}...'"
                )
                source_language = "en"

            # Additional validation: if we're still unsure, use verification layer
            if not contains_english and source_language == "en":
                # Detection said English but no English words found - double check
                logger.warning(
                    f"[{speaker_id}] Detection inconsistency - running additional verification"
                )
                try:
                    from app.translate.verification_layer import RedundantVerificationTranslator
                    verifier = RedundantVerificationTranslator()
                    is_english, confidence = verifier.detect_is_english(text)

                    if not is_english and confidence > 0.7:
                        logger.info(
                            f"[{speaker_id}] Verification override: changing from 'en' to 'es' "
                            f"(confidence={confidence:.2f})"
                        )
                        source_language = "es"
                except Exception as e:
                    logger.debug(f"Additional verification skipped: {e}")

            # Check for discrepancy with checkbox
            if self.settings.audio_is_spanish and source_language != "es":
                logger.warning(
                    f"[{speaker_id}] Discrepancy: 'Audio en Español' checkbox is marked, "
                    f"but detected language is '{source_language}'. Will translate anyway."
                )
            
            # Translate or pass through
            if source_language == target_language and not contains_english:
                # Confirmed Spanish, pass through
                logger.debug(f"[{speaker_id}] Text is Spanish, passing through: '{text[:50]}...'")
                translation = TranslationResult(
                    original_text=text,
                    translated_text=text,
                    source_language=source_language,
                    target_language=target_language
                )
            else:
                # Not Spanish OR uncertain - always translate
                logger.info(f"[{speaker_id}] Translating from '{source_language}' to '{target_language}': '{text[:50]}...'")
                
                translation = await self.translate_router.translate(
                    text=text,
                    source_language=source_language if source_language != "es" else "en",
                    target_language=target_language
                )
                
                # Validate translation result
                if translation.translated_text == text:
                    logger.warning(
                        f"[{speaker_id}] Translation returned same text as input! "
                        f"Original: '{text[:50]}...', Translated: '{translation.translated_text[:50]}...'"
                    )
                    
                    # If translation didn't change and input was English, try verification layer
                    if contains_english or source_language == "en":
                        logger.error(
                            f"[{speaker_id}] Translation FAILED - attempting emergency translation with verification layer"
                        )

                        # Import and use verification translator as emergency backup
                        try:
                            from app.translate.verification_layer import RedundantVerificationTranslator
                            emergency_translator = RedundantVerificationTranslator()
                            verified_text = emergency_translator.verify_and_ensure_spanish(text)

                            if verified_text != text:
                                # Emergency translation succeeded
                                logger.info(
                                    f"[{speaker_id}] ✓ Emergency translation succeeded: '{verified_text[:50]}...'"
                                )
                                translation = TranslationResult(
                                    original_text=text,
                                    translated_text=verified_text,
                                    source_language=source_language,
                                    target_language="es"
                                )
                            else:
                                # Even emergency translation failed - don't publish
                                logger.error(
                                    f"[{speaker_id}] ⚠️  ALL translation methods failed, not publishing"
                                )
                                return
                        except Exception as e:
                            logger.error(f"[{speaker_id}] Emergency translation failed: {e}")
                            return
                
                logger.info(f"[{speaker_id}] Translation successful: '{translation.translated_text[:50]}...'")
            
            # Publish translation event
            await event_bus.publish("translation", translation)
        
        except Exception as e:
            logger.error(f"[{speaker_id}] Translation error for buffered text '{text[:50]}...': {e}", exc_info=True)
    
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
            speaker_id = event.speaker_id or "default"
            
            # Handle speaker change: flush previous speaker's buffer
            if self._last_speaker_id and self._last_speaker_id != speaker_id:
                if self._last_speaker_id in self._sentence_buffers:
                    buffered_text = self._sentence_buffers[self._last_speaker_id]
                    logger.info(f"Speaker changed from {self._last_speaker_id} to {speaker_id}, flushing buffer: '{buffered_text[:50]}...'")
                    await self._process_buffered_text(self._last_speaker_id, buffered_text)
                    del self._sentence_buffers[self._last_speaker_id]
                    if self._last_speaker_id in self._buffer_timestamps:
                        del self._buffer_timestamps[self._last_speaker_id]
            
            self._last_speaker_id = speaker_id
            
            # Add text to buffer for this speaker
            if speaker_id in self._sentence_buffers:
                # Append with a space
                self._sentence_buffers[speaker_id] += " " + text
            else:
                self._sentence_buffers[speaker_id] = text
            
            # Update timestamp
            self._buffer_timestamps[speaker_id] = datetime.now()
            
            buffered_text = self._sentence_buffers[speaker_id]
            
            # Check if buffer ends with sentence punctuation
            if self._ends_with_sentence_punctuation(buffered_text):
                logger.info(f"[{speaker_id}] Sentence complete, processing: '{buffered_text[:50]}...'")
                await self._process_buffered_text(speaker_id, buffered_text)
                # Clear buffer after processing
                del self._sentence_buffers[speaker_id]
                del self._buffer_timestamps[speaker_id]
            else:
                logger.debug(f"[{speaker_id}] Buffering text (no sentence end): '{buffered_text[:50]}...'")
        
        except Exception as e:
            logger.error(f"Error handling transcript for text '{event.text[:50]}...': {e}", exc_info=True)
    
    async def stop(self):
        """Stop translation service."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Stop buffer check task
        if self._buffer_check_task:
            self._buffer_check_task.cancel()
            try:
                await self._buffer_check_task
            except asyncio.CancelledError:
                pass
        
        # Flush any remaining buffers
        for speaker_id in list(self._sentence_buffers.keys()):
            buffered_text = self._sentence_buffers[speaker_id]
            if buffered_text.strip():
                logger.info(f"Flushing remaining buffer for {speaker_id} on shutdown: '{buffered_text[:50]}...'")
                await self._process_buffered_text(speaker_id, buffered_text)
        
        # Clear buffers
        self._sentence_buffers.clear()
        self._buffer_timestamps.clear()
        
        event_bus.unsubscribe("transcript", self._handle_transcript)
        logger.info("Translation service stopped")
    
    def get_current_provider_name(self) -> str:
        """Get current translation provider name."""
        return self.translate_router.get_current_provider_name()
    
    def get_health_status(self):
        """Get health status of translation providers."""
        return self.translate_router.get_health_status()

