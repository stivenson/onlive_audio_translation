"""Application settings and configuration management."""

import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv


class Settings(BaseModel):
    """Application settings loaded from environment variables."""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # STT Provider Chain
    stt_provider_chain: List[str] = ["deepgram"]
    
    # Deepgram
    deepgram_api_key: Optional[str] = None
    
    # LLM Provider Chain
    llm_provider_chain: List[str] = ["openai"]
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    
    # Model Configuration by Service
    translation_model_fallback: str = "gpt-4o"
    summary_model: str = "gpt-4o"
    questions_model: str = "gpt-4o"
    
    # Translation Provider Chain
    translate_provider_chain: List[str] = ["huggingface", "llm"]
    
    # Hugging Face
    hf_api_token: Optional[str] = None
    hf_translation_model: str = "Helsinki-NLP/opus-mt-en-es"
    
    # Provider Resilience
    provider_failover_cooldown_seconds: int = 120
    provider_max_retries: int = 2
    provider_timeout_seconds: int = 15
    provider_circuit_breaker_failures: int = 5
    provider_circuit_breaker_timeout_seconds: int = 60
    
    # Audio Configuration
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    audio_chunk_size: int = 3200
    audio_buffer_seconds: int = 3
    
    # Language Detection
    default_language_hint: str = "en"
    auto_detect_language: bool = True
    
    # Summary Configuration
    summary_update_seconds: int = 15
    summary_max_context_minutes: int = 20
    
    # Questions Configuration
    questions_update_seconds: int = 30
    questions_max_count: int = 10
    
    # UI Configuration
    ui_theme: str = "dark"
    ui_font_size: int = 12
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    log_rotation_max_bytes: int = 10485760
    log_rotation_backup_count: int = 5


def load_settings() -> Settings:
    """Load settings from .env file."""
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path)
    
    # Parse provider chains from environment
    env_vars = os.environ
    
    settings_dict = {}
    
    # Parse all environment variables
    for key, value in env_vars.items():
        key_lower = key.lower()
        
        # Parse provider chains as lists
        if key_lower.endswith("_chain"):
            settings_dict[key_lower] = [p.strip() for p in value.split(",")]
        # Parse boolean values
        elif key_lower == "auto_detect_language":
            settings_dict[key_lower] = value.lower() in ("true", "1", "yes")
        # Parse integer values
        elif key_lower in [
            "provider_failover_cooldown_seconds", "provider_max_retries",
            "provider_timeout_seconds", "provider_circuit_breaker_failures",
            "provider_circuit_breaker_timeout_seconds", "audio_sample_rate",
            "audio_channels", "audio_chunk_size", "audio_buffer_seconds",
            "summary_update_seconds", "summary_max_context_minutes",
            "questions_update_seconds", "questions_max_count", "ui_font_size",
            "log_rotation_max_bytes", "log_rotation_backup_count"
        ]:
            try:
                settings_dict[key_lower] = int(value)
            except ValueError:
                pass  # Use default value
        # All other string values
        else:
            # Map common environment variable names to settings fields
            if key_lower in [
                "deepgram_api_key", "openai_api_key", "openai_model",
                "translation_model_fallback", "summary_model", "questions_model",
                "hf_api_token", "hf_translation_model", "default_language_hint",
                "ui_theme", "log_level", "log_file"
            ]:
                settings_dict[key_lower] = value
    
    return Settings(**settings_dict)

