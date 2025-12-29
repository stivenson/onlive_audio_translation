"""Conversation memory for maintaining context."""

from datetime import datetime, timedelta
from typing import List, Optional
from collections import deque
import logging

from app.core.schemas import TranscriptEvent, TranslationResult

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Manages conversation history and context."""
    
    def __init__(self, max_context_minutes: int = 20):
        """
        Initialize conversation memory.
        
        Args:
            max_context_minutes: Maximum minutes of context to keep
        """
        self.max_context_minutes = max_context_minutes
        self.transcripts: deque = deque()
        self.translations: deque = deque()
        self.start_time: Optional[datetime] = None
    
    def add_transcript(self, event: TranscriptEvent):
        """Add a transcript event to memory."""
        if self.start_time is None:
            self.start_time = datetime.now()
        
        self.transcripts.append(event)
        self._prune_old_transcripts()
    
    def add_translation(self, translation: TranslationResult):
        """Add a translation to memory."""
        self.translations.append(translation)
        self._prune_old_translations()
    
    def _prune_old_transcripts(self):
        """Remove transcripts older than max_context_minutes."""
        if not self.transcripts:
            return
        
        cutoff_time = datetime.now() - timedelta(minutes=self.max_context_minutes)
        
        while self.transcripts and self.transcripts[0].timestamp < cutoff_time:
            self.transcripts.popleft()
    
    def _prune_old_translations(self):
        """Remove translations older than max_context_minutes."""
        if not self.translations:
            return
        
        cutoff_time = datetime.now() - timedelta(minutes=self.max_context_minutes)
        
        while self.translations and self.translations[0].timestamp < cutoff_time:
            self.translations.popleft()
    
    def get_recent_transcripts(self, minutes: Optional[int] = None) -> List[TranscriptEvent]:
        """
        Get recent transcripts.
        
        Args:
            minutes: Number of minutes to look back (default: all in memory)
            
        Returns:
            List of transcript events
        """
        if minutes is None:
            return list(self.transcripts)
        
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [t for t in self.transcripts if t.timestamp >= cutoff_time]
    
    def get_recent_translations(self, minutes: Optional[int] = None) -> List[TranslationResult]:
        """
        Get recent translations.
        
        Args:
            minutes: Number of minutes to look back (default: all in memory)
            
        Returns:
            List of translation results
        """
        if minutes is None:
            return list(self.translations)
        
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [t for t in self.translations if t.timestamp >= cutoff_time]
    
    def get_transcripts_after(self, timestamp: datetime) -> List[TranscriptEvent]:
        """
        Get transcripts that occurred after a specific timestamp.
        
        Args:
            timestamp: Get transcripts after this timestamp
            
        Returns:
            List of transcript events after the timestamp
        """
        return [t for t in self.transcripts if t.timestamp > timestamp]
    
    def get_translations_after(self, timestamp: datetime) -> List[TranslationResult]:
        """
        Get translations that occurred after a specific timestamp.
        
        Args:
            timestamp: Get translations after this timestamp
            
        Returns:
            List of translations after the timestamp
        """
        return [t for t in self.translations if t.timestamp > timestamp]
    
    def get_full_context_text(self, include_translations: bool = False) -> str:
        """
        Get full context as text for LLM prompts.
        
        Args:
            include_translations: Whether to include translations or just transcripts
            
        Returns:
            Formatted text with all context
        """
        lines = []
        
        if include_translations:
            for trans in self.translations:
                lines.append(f"[{trans.timestamp.strftime('%H:%M:%S')}] {trans.translated_text}")
        else:
            for transcript in self.transcripts:
                speaker = transcript.speaker_id or "Unknown"
                lines.append(
                    f"[{transcript.timestamp.strftime('%H:%M:%S')}] [{speaker}]: {transcript.text}"
                )
        
        return "\n".join(lines)
    
    def clear(self):
        """Clear all memory."""
        self.transcripts.clear()
        self.translations.clear()
        self.start_time = None
        logger.info("Conversation memory cleared")

