"""LLM provider router with failover."""

from typing import List, Optional
import logging

from app.llm.base import LLMProvider
from app.llm.openai_provider import OpenAIProvider
from app.core.provider_router import ProviderRouter
from app.config.settings import Settings

logger = logging.getLogger(__name__)


class LLMRouter:
    """Router for LLM providers with automatic failover."""
    
    def __init__(self, settings: Settings, model_override: Optional[str] = None):
        """
        Initialize LLM router.
        
        Args:
            settings: Application settings
            model_override: Optional model name to override default model for this router instance
        """
        self.settings = settings
        self.model_override = model_override
        self.providers: List[LLMProvider] = []
        self.provider_names: List[str] = []
        
        # Create providers based on chain
        for provider_name in settings.llm_provider_chain:
            try:
                provider = self._create_provider(provider_name, settings, model_override)
                if provider:
                    self.providers.append(provider)
                    self.provider_names.append(provider_name)
                    logger.info(f"Initialized LLM provider: {provider_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM provider {provider_name}: {e}")
        
        if not self.providers:
            raise RuntimeError("No LLM providers available")
        
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
    
    def _create_provider(self, provider_name: str, settings: Settings, model_override: Optional[str] = None) -> Optional[LLMProvider]:
        """Create an LLM provider instance."""
        # Determine which model to use
        model_to_use = model_override or settings.openai_model
        
        if provider_name == "openai":
            if not settings.openai_api_key:
                logger.warning("OpenAI API key not configured")
                return None
            return OpenAIProvider(
                api_key=settings.openai_api_key,
                model=model_to_use
            )
        
        else:
            logger.warning(f"Unknown LLM provider: {provider_name}. Only 'openai' is supported.")
            return None
    
    async def generate_json(
        self,
        prompt: str,
        schema: type,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ):
        """Generate structured JSON with failover."""
        async def generate_operation(provider: LLMProvider):
            return await provider.generate_json(prompt, schema, temperature, max_tokens)
        
        return await self.router.execute_with_failover(
            generate_operation,
            operation_name="generate_json"
        )
    
    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate text with failover."""
        async def generate_operation(provider: LLMProvider):
            return await provider.generate_text(prompt, temperature, max_tokens)
        
        return await self.router.execute_with_failover(
            generate_operation,
            operation_name="generate_text"
        )
    
    def get_current_provider_name(self) -> str:
        """Get current active provider name."""
        return self.router.get_current_provider_name()
    
    def get_health_status(self):
        """Get health status of all providers."""
        return self.router.get_health_status()

