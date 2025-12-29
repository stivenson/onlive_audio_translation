"""Session management for tracking and exporting conversation data."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import logging

from app.core.schemas import (
    TranscriptEvent, TranslationResult, SummaryUpdate,
    QuestionPair, ProviderChangeEvent
)
from app.storage.session_exporter import SessionExporter
from app.core.event_bus import event_bus

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages session data collection and export."""
    
    def __init__(self, export_dir: str = "exports"):
        """
        Initialize session manager.
        
        Args:
            export_dir: Directory for exports
        """
        self.session_id = str(uuid.uuid4())
        self.start_time = datetime.now()
        
        self.transcripts: List[TranscriptEvent] = []
        self.translations: List[TranslationResult] = []
        self.summaries: List[SummaryUpdate] = []
        self.questions: List[QuestionPair] = []
        self.provider_changes: List[ProviderChangeEvent] = []
        
        self.exporter = SessionExporter(export_dir)
        self.is_tracking = False
    
    def start_tracking(self):
        """Start tracking session events."""
        if self.is_tracking:
            return
        
        self.is_tracking = True
        
        # Subscribe to events
        event_bus.subscribe("transcript", self._on_transcript)
        event_bus.subscribe("translation", self._on_translation)
        event_bus.subscribe("summary", self._on_summary)
        event_bus.subscribe("questions", self._on_questions)
        event_bus.subscribe("provider_change", self._on_provider_change)
        
        logger.info(f"Started tracking session: {self.session_id}")
    
    def stop_tracking(self):
        """Stop tracking session events."""
        if not self.is_tracking:
            return
        
        self.is_tracking = False
        
        # Unsubscribe from events
        event_bus.unsubscribe("transcript", self._on_transcript)
        event_bus.unsubscribe("translation", self._on_translation)
        event_bus.unsubscribe("summary", self._on_summary)
        event_bus.unsubscribe("questions", self._on_questions)
        event_bus.unsubscribe("provider_change", self._on_provider_change)
        
        logger.info(f"Stopped tracking session: {self.session_id}")
    
    def _on_transcript(self, event: TranscriptEvent):
        """Handle transcript event."""
        if event.transcript_type.value == "final":
            self.transcripts.append(event)
    
    def _on_translation(self, event: TranslationResult):
        """Handle translation event."""
        self.translations.append(event)
    
    def _on_summary(self, event: SummaryUpdate):
        """Handle summary event."""
        self.summaries.append(event)
    
    def _on_questions(self, event: List[QuestionPair]):
        """Handle questions event."""
        self.questions.extend(event)
    
    def _on_provider_change(self, event: ProviderChangeEvent):
        """Handle provider change event."""
        self.provider_changes.append(event)
    
    def export(self, format: str = "json") -> Path:
        """
        Export current session.
        
        Args:
            format: Export format ("json", "csv", "jsonl")
            
        Returns:
            Path to exported file
        """
        return self.exporter.export_session(
            session_id=self.session_id,
            transcripts=self.transcripts,
            translations=self.translations,
            summaries=self.summaries,
            questions=self.questions,
            provider_changes=self.provider_changes,
            format=format
        )
    
    def clear(self):
        """Clear all session data."""
        self.transcripts.clear()
        self.translations.clear()
        self.summaries.clear()
        self.questions.clear()
        self.provider_changes.clear()
        self.session_id = str(uuid.uuid4())
        self.start_time = datetime.now()
        logger.info(f"Session cleared, new session ID: {self.session_id}")
    
    def get_stats(self) -> dict:
        """Get session statistics."""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "transcripts_count": len(self.transcripts),
            "translations_count": len(self.translations),
            "summaries_count": len(self.summaries),
            "questions_count": len(self.questions),
            "provider_changes_count": len(self.provider_changes)
        }

