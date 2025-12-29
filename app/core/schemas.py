"""Core data models and schemas for the application."""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class TranscriptType(str, Enum):
    """Type of transcript event."""
    INTERIM = "interim"
    FINAL = "final"


class TranscriptEvent(BaseModel):
    """Normalized transcript event from STT provider."""
    text: str
    transcript_type: TranscriptType
    speaker_id: Optional[str] = None
    start_time: float = Field(description="Start time in seconds")
    end_time: float = Field(description="End time in seconds")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    language: Optional[str] = None
    words: Optional[List[Dict[str, Any]]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class TranslationResult(BaseModel):
    """Normalized translation result."""
    original_text: str
    translated_text: str
    source_language: str
    target_language: str = "es"
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.now)


class QuestionPair(BaseModel):
    """Question pair in English and Spanish."""
    question_en: str
    question_es: str
    priority: int = Field(default=0, ge=0, le=10)
    reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class SummaryUpdate(BaseModel):
    """Live summary update."""
    summary: str
    context_minutes: float
    last_updated: datetime = Field(default_factory=datetime.now)
    version: int = Field(default=1, ge=1)


class ProviderStatus(str, Enum):
    """Provider health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    CIRCUIT_OPEN = "circuit_open"


class ProviderHealth(BaseModel):
    """Provider health information."""
    provider_name: str
    status: ProviderStatus
    latency_p95: Optional[float] = None
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    failure_count: int = Field(default=0, ge=0)
    circuit_breaker_state: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.now)


class ProviderChangeEvent(BaseModel):
    """Event when provider changes due to failover."""
    domain: str  # "stt", "translate", "llm"
    old_provider: Optional[str]
    new_provider: str
    reason: str
    timestamp: datetime = Field(default_factory=datetime.now)

