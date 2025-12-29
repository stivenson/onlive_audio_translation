"""Session export functionality."""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import logging

from app.core.schemas import (
    TranscriptEvent, TranslationResult, SummaryUpdate, 
    QuestionPair, ProviderChangeEvent
)

logger = logging.getLogger(__name__)


class SessionExporter:
    """Exports session data to various formats."""
    
    def __init__(self, export_dir: str = "exports"):
        """
        Initialize session exporter.
        
        Args:
            export_dir: Directory to save exports
        """
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(exist_ok=True)
    
    def export_session(
        self,
        session_id: str,
        transcripts: List[TranscriptEvent],
        translations: List[TranslationResult],
        summaries: List[SummaryUpdate],
        questions: List[QuestionPair],
        provider_changes: List[ProviderChangeEvent],
        format: str = "json"
    ) -> Path:
        """
        Export session data.
        
        Args:
            session_id: Unique session identifier
            transcripts: List of transcript events
            translations: List of translation results
            summaries: List of summary updates
            questions: List of question pairs
            provider_changes: List of provider change events
            format: Export format ("json", "csv", "jsonl")
            
        Returns:
            Path to exported file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "json":
            return self._export_json(
                session_id, timestamp, transcripts, translations,
                summaries, questions, provider_changes
            )
        elif format == "csv":
            return self._export_csv(
                session_id, timestamp, transcripts, translations,
                summaries, questions, provider_changes
            )
        elif format == "jsonl":
            return self._export_jsonl(
                session_id, timestamp, transcripts, translations,
                summaries, questions, provider_changes
            )
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _export_json(
        self,
        session_id: str,
        timestamp: str,
        transcripts: List[TranscriptEvent],
        translations: List[TranslationResult],
        summaries: List[SummaryUpdate],
        questions: List[QuestionPair],
        provider_changes: List[ProviderChangeEvent]
    ) -> Path:
        """Export to JSON format."""
        data = {
            "session_id": session_id,
            "export_timestamp": timestamp,
            "transcripts": [t.model_dump() for t in transcripts],
            "translations": [t.model_dump() for t in translations],
            "summaries": [s.model_dump() for s in summaries],
            "questions": [q.model_dump() for q in questions],
            "provider_changes": [p.model_dump() for p in provider_changes]
        }
        
        filename = f"session_{session_id}_{timestamp}.json"
        filepath = self.export_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Exported session to {filepath}")
        return filepath
    
    def _export_csv(
        self,
        session_id: str,
        timestamp: str,
        transcripts: List[TranscriptEvent],
        translations: List[TranslationResult],
        summaries: List[SummaryUpdate],
        questions: List[QuestionPair],
        provider_changes: List[ProviderChangeEvent]
    ) -> Path:
        """Export to CSV format."""
        filename = f"session_{session_id}_{timestamp}.csv"
        filepath = self.export_dir / filename
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write transcripts
            writer.writerow(["Type", "Timestamp", "Speaker", "Text", "Language", "Confidence"])
            for t in transcripts:
                writer.writerow([
                    "transcript",
                    t.timestamp.isoformat(),
                    t.speaker_id or "",
                    t.text,
                    t.language or "",
                    t.confidence or ""
                ])
            
            # Write translations
            writer.writerow([])  # Empty row
            writer.writerow(["Type", "Timestamp", "Original", "Translated", "Source Lang", "Target Lang"])
            for t in translations:
                writer.writerow([
                    "translation",
                    t.timestamp.isoformat(),
                    t.original_text,
                    t.translated_text,
                    t.source_language,
                    t.target_language
                ])
            
            # Write summaries
            writer.writerow([])  # Empty row
            writer.writerow(["Type", "Timestamp", "Version", "Summary"])
            for s in summaries:
                writer.writerow([
                    "summary",
                    s.last_updated.isoformat(),
                    s.version,
                    s.summary
                ])
            
            # Write questions
            writer.writerow([])  # Empty row
            writer.writerow(["Type", "Timestamp", "Question EN", "Question ES", "Priority", "Reason"])
            for q in questions:
                writer.writerow([
                    "question",
                    q.timestamp.isoformat(),
                    q.question_en,
                    q.question_es,
                    q.priority,
                    q.reason or ""
                ])
            
            # Write provider changes
            writer.writerow([])  # Empty row
            writer.writerow(["Type", "Timestamp", "Domain", "Old Provider", "New Provider", "Reason"])
            for p in provider_changes:
                writer.writerow([
                    "provider_change",
                    p.timestamp.isoformat(),
                    p.domain,
                    p.old_provider or "",
                    p.new_provider,
                    p.reason
                ])
        
        logger.info(f"Exported session to {filepath}")
        return filepath
    
    def _export_jsonl(
        self,
        session_id: str,
        timestamp: str,
        transcripts: List[TranscriptEvent],
        translations: List[TranslationResult],
        summaries: List[SummaryUpdate],
        questions: List[QuestionPair],
        provider_changes: List[ProviderChangeEvent]
    ) -> Path:
        """Export to JSONL format (one JSON object per line)."""
        filename = f"session_{session_id}_{timestamp}.jsonl"
        filepath = self.export_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # Write transcripts
            for t in transcripts:
                obj = {"type": "transcript", **t.model_dump()}
                f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
            
            # Write translations
            for t in translations:
                obj = {"type": "translation", **t.model_dump()}
                f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
            
            # Write summaries
            for s in summaries:
                obj = {"type": "summary", **s.model_dump()}
                f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
            
            # Write questions
            for q in questions:
                obj = {"type": "question", **q.model_dump()}
                f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
            
            # Write provider changes
            for p in provider_changes:
                obj = {"type": "provider_change", **p.model_dump()}
                f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
        
        logger.info(f"Exported session to {filepath}")
        return filepath
    
    def export_to_folder(
        self,
        meeting_name: str,
        transcripts: List[TranscriptEvent],
        translations: List[TranslationResult],
        summaries: List[SummaryUpdate],
        questions: List[QuestionPair]
    ) -> Path:
        """
        Export session data to a folder with individual TXT files.
        
        Args:
            meeting_name: Name of the meeting (will be sanitized)
            transcripts: List of transcript events
            translations: List of translation results
            summaries: List of summary updates
            questions: List of question pairs
            
        Returns:
            Path to the created folder
        """
        # Sanitize meeting name (remove invalid chars for folder name)
        import re
        safe_name = re.sub(r'[<>:"/\\|?*]', '', meeting_name)
        safe_name = safe_name.strip()
        
        # Create folder name with timestamp
        timestamp = datetime.now().strftime("%d%m%Y_%H%M")
        folder_name = f"{safe_name}_{timestamp}"
        folder_path = self.export_dir / folder_name
        folder_path.mkdir(exist_ok=True)
        
        # Export transcription.txt
        transcription_path = folder_path / "transcription.txt"
        with open(transcription_path, 'w', encoding='utf-8') as f:
            for transcript in transcripts:
                speaker = transcript.speaker_id or "Unknown"
                f.write(f"[{speaker}]: {transcript.text}\n")
        
        # Export translation.txt
        translation_path = folder_path / "translation.txt"
        with open(translation_path, 'w', encoding='utf-8') as f:
            for translation in translations:
                f.write(f"{translation.translated_text}\n")
        
        # Export summary.txt (use latest summary)
        summary_path = folder_path / "summary.txt"
        with open(summary_path, 'w', encoding='utf-8') as f:
            if summaries:
                # Get the latest summary
                latest_summary = max(summaries, key=lambda s: s.last_updated)
                f.write(latest_summary.summary)
            else:
                f.write("No summary available.\n")
        
        # Export questions.txt
        questions_path = folder_path / "questions.txt"
        with open(questions_path, 'w', encoding='utf-8') as f:
            for question in questions:
                f.write(f"EN: {question.question_en}\n")
                f.write(f"ES: {question.question_es}\n")
                f.write("\n")
        
        logger.info(f"Exported session to folder: {folder_path}")
        return folder_path

