"""Application settings and configuration management."""

import os
import logging
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


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
    audio_device_index: Optional[int] = None
    
    # Language Detection
    default_language_hint: str = "en"
    auto_detect_language: bool = True
    audio_is_spanish: bool = False  # When True, audio is in Spanish, no translation needed
    
    # Summary Configuration
    summary_update_seconds: int = 60
    summary_max_context_minutes: int = 20
    
    # Questions Configuration
    questions_update_seconds: int = 300  # 5 minutes
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
        elif key_lower in ["auto_detect_language", "audio_is_spanish"]:
            settings_dict[key_lower] = value.lower() in ("true", "1", "yes")
        # Parse integer values
        elif key_lower in [
            "provider_failover_cooldown_seconds", "provider_max_retries",
            "provider_timeout_seconds", "provider_circuit_breaker_failures",
            "provider_circuit_breaker_timeout_seconds", "audio_sample_rate",
            "audio_channels", "audio_chunk_size", "audio_buffer_seconds",
            "audio_device_index", "summary_update_seconds", "summary_max_context_minutes",
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
    
    settings = Settings(**settings_dict)
    
    # Auto-select Realtek device if available (always, even if another device is configured)
    try:
        from app.audio.capture import AudioCapture
        capture = AudioCapture()
        realtek_index = capture.find_realtek_device()
        
        if realtek_index is not None:
            previous_device = settings.audio_device_index
            settings.audio_device_index = realtek_index
            if previous_device is not None:
                logger.info(f"Auto-selected Realtek device (index {realtek_index}) - replaced previous device index {previous_device}")
            else:
                logger.info(f"Auto-selected audio device: Realtek (index {realtek_index})")
        else:
            # Fallback: try Stereo Mix if Realtek not found
            stereo_mix_index = capture.find_loopback_device()
            if stereo_mix_index is not None:
                previous_device = settings.audio_device_index
                settings.audio_device_index = stereo_mix_index
                if previous_device is not None:
                    logger.info(f"Auto-selected Stereo Mix (index {stereo_mix_index}) - replaced previous device index {previous_device}")
                else:
                    logger.info(f"Auto-selected audio device: Stereo Mix (index {stereo_mix_index})")
            else:
                logger.info("No Realtek or Stereo Mix device found. Using configured or default audio device.")
    except Exception as e:
        logger.warning(f"Could not auto-select audio device: {e}")
    
    return settings

