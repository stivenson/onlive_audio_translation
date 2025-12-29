"""STT provider router with failover."""

import sys
from typing import List, Optional, AsyncIterator
from datetime import datetime, timedelta
import asyncio
import logging

from app.stt.base import STTProvider
from app.stt.deepgram_provider import DeepgramProvider
from app.core.provider_router import ProviderRouter
from app.core.schemas import TranscriptEvent
from app.config.settings import Settings

logger = logging.getLogger(__name__)


class STTRouter:
    """Router for STT providers with automatic failover."""
    
    def __init__(self, settings: Settings):
        """
        Initialize STT router with providers from settings.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.providers: List[STTProvider] = []
        self.provider_names: List[str] = []
        
        # Track initialization failures for better error messages
        initialization_errors = []
        
        # Create providers based on chain
        for provider_name in settings.stt_provider_chain:
            try:
                provider = self._create_provider(provider_name, settings)
                if provider:
                    self.providers.append(provider)
                    self.provider_names.append(provider_name)
                    logger.info(f"Initialized STT provider: {provider_name}")
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Failed to initialize STT provider {provider_name}: {error_msg}")
                initialization_errors.append((provider_name, error_msg))
        
        if not self.providers:
            # Build detailed error message with diagnostics
            error_details = []
            error_details.append("No STT providers available. Failed to initialize:")
            
            for provider_name, error_msg in initialization_errors:
                error_details.append(f"  - {provider_name}: {error_msg}")
            
            # Add diagnostic suggestions
            suggestions = []
            
            # Check if it's an import error (likely wrong Python environment)
            if any("not installed" in err.lower() or "import" in err.lower() 
                   for _, err in initialization_errors):
                python_path = sys.executable
                in_venv = hasattr(sys, 'real_prefix') or (
                    hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
                )
                
                if not in_venv:
                    suggestions.append(
                        "  * You may not be using the virtual environment. "
                        "Activate it with: .venv\\Scripts\\activate (Windows) or "
                        "source .venv/bin/activate (Linux/Mac)"
                    )
                    suggestions.append(
                        f"  * Current Python: {python_path}"
                    )
                else:
                    suggestions.append(
                        "  * Package may not be installed. Install with: "
                        "pip install deepgram-sdk"
                    )
            
            # Check for missing API keys
            if any("api key" in err.lower() or "api_key" in err.lower() 
                   for _, err in initialization_errors):
                suggestions.append(
                    "  * Check your .env file and ensure DEEPGRAM_API_KEY is set"
                )
            
            if suggestions:
                error_details.append("\nSuggestions:")
                error_details.extend(suggestions)
            
            error_message = "\n".join(error_details)
            raise RuntimeError(error_message)
        
        # Create router
        self.router = ProviderRouter(
            providers=self.providers,
            provider_names=self.provider_names,
            failover_cooldown_seconds=settings.provider_failover_cooldown_seconds,
            max_retries=settings.provider_max_retries,
            timeout_seconds=settings.provider_timeout_seconds,
            circuit_breaker_failures=settings.provider_circuit_breaker_failures,
            circuit_breaker_timeout=settings.provider_circuit_breaker_timeout_seconds
        )
    
    def _create_provider(self, provider_name: str, settings: Settings) -> Optional[STTProvider]:
        """Create a provider instance based on name."""
        if provider_name == "deepgram":
            if not settings.deepgram_api_key:
                logger.warning("Deepgram API key not configured")
                return None
            return DeepgramProvider(api_key=settings.deepgram_api_key)
        
        else:
            logger.warning(f"Unknown STT provider: {provider_name}. Only 'deepgram' is supported.")
            return None
    
    async def stream(
        self,
        audio_stream: AsyncIterator[bytes],
        sample_rate: int = 16000,
        language: Optional[str] = None,
        diarize: bool = True,
        punctuate: bool = True
    ) -> AsyncIterator[TranscriptEvent]:
        """
        Stream audio through STT router with failover.
        
        Yields:
            TranscriptEvent objects
        """
        max_failover_attempts = len(self.providers)
        attempt = 0
        
        while attempt < max_failover_attempts:
            provider = self.router.get_current_provider()
            provider_name = self.router.get_current_provider_name()
            
            try:
                logger.info(f"Streaming with STT provider: {provider_name}")
                
                # Track last event time for timeout detection
                last_event_time = datetime.now()
                event_count = 0
                
                async for event in provider.stream(
                    audio_stream=audio_stream,
                    sample_rate=sample_rate,
                    language=language,
                    diarize=diarize,
                    punctuate=punctuate
                ):
                    # Update health on successful event
                    self.router._update_health(
                        self.router.current_index,
                        success=True
                    )
                    
                    # Track events
                    event_count += 1
                    last_event_time = datetime.now()
                    
                    yield event
                    
                    # Periodically check for timeout (only after some events received)
                    if event_count > 0 and event_count % 10 == 0:
                        time_since_last_event = (datetime.now() - last_event_time).total_seconds()
                        if time_since_last_event > 120:  # 2 minutes without events
                            logger.warning(
                                f"No events from {provider_name} for {time_since_last_event:.1f}s - "
                                "stream may be stalled"
                            )
                
                # Stream completed successfully
                break
                
            except Exception as e:
                logger.warning(f"STT provider {provider_name} failed: {e}")
                
                # Update health
                self.router._update_health(
                    self.router.current_index,
                    success=False
                )
                
                # Try failover
                self.router._failover_to_next(self.router.current_index)
                attempt += 1
                
                if attempt >= max_failover_attempts:
                    logger.error("All STT providers failed")
                    raise RuntimeError("All STT providers failed") from e
    
    def get_current_provider_name(self) -> str:
        """Get current active provider name."""
        return self.router.get_current_provider_name()
    
    def get_health_status(self):
        """Get health status of all providers."""
        return self.router.get_health_status()
    
    async def health_check_all(self):
        """Perform health check on all providers."""
        await self.router.health_check_all()

