"""Translation provider router with failover."""

from typing import List, Optional
import logging

from app.translate.base import TranslateProvider
from app.translate.llm_translate_provider import LLMTranslateProvider
from app.translate.huggingface_provider import HuggingFaceProvider
from app.translate.ctranslate2_provider import CTranslate2Provider
from app.translate.deepl_provider import DeepLProvider
from app.core.provider_router import ProviderRouter
from app.core.schemas import TranslationResult
from app.config.settings import Settings
from app.llm.router import LLMRouter

logger = logging.getLogger(__name__)


class TranslateRouter:
    """Router for translation providers with automatic failover."""
    
    def __init__(self, settings: Settings, llm_router: Optional[LLMRouter] = None):
        """
        Initialize translation router.
        
        Args:
            settings: Application settings
            llm_router: Optional LLM router for LLM-based translation
        """
        self.settings = settings
        self.llm_router = llm_router
        self.providers: List[TranslateProvider] = []
        self.provider_names: List[str] = []
        
        # Create providers based on chain
        for provider_name in settings.translate_provider_chain:
            try:
                provider = self._create_provider(provider_name, settings)
                if provider:
                    self.providers.append(provider)
                    self.provider_names.append(provider_name)
                    logger.info(f"Initialized translation provider: {provider_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize translation provider {provider_name}: {e}")
        
        if not self.providers:
            raise RuntimeError("No translation providers available")
        
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
    
    def _create_provider(self, provider_name: str, settings: Settings) -> Optional[TranslateProvider]:
        """Create a translation provider instance."""
        if provider_name == "ctranslate2":
            try:
                return CTranslate2Provider(
                    model_path=settings.ctranslate2_model_path
                )
            except Exception as e:
                logger.warning(f"CTranslate2 provider not available: {e}")
                return None
        
        elif provider_name == "deepl":
            if not settings.deepl_api_key:
                logger.warning("DeepL API key not configured")
                return None
            try:
                return DeepLProvider(api_key=settings.deepl_api_key)
            except Exception as e:
                logger.warning(f"DeepL provider not available: {e}")
                return None
        
        elif provider_name == "huggingface":
            if not settings.hf_api_token:
                logger.warning("Hugging Face API token not configured")
                return None
            return HuggingFaceProvider(
                api_token=settings.hf_api_token,
                model=settings.hf_translation_model
            )
        
        elif provider_name == "llm":
            if not self.llm_router:
                logger.warning("LLM router not available for LLM translation")
                return None
            # Get current LLM provider
            llm_provider = self.llm_router.router.get_current_provider()
            return LLMTranslateProvider(llm_provider=llm_provider)
        
        else:
            logger.warning(
                f"Unknown translation provider: {provider_name}. "
                f"Supported providers: ctranslate2, deepl, huggingface, llm"
            )
            return None
    
    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str = "es"
    ) -> TranslationResult:
        """
        Translate text with automatic failover.
        
        Args:
            text: Text to translate
            source_language: Source language code
            target_language: Target language code
            
        Returns:
            TranslationResult
        """
        async def translate_operation(provider: TranslateProvider):
            return await provider.translate(text, source_language, target_language)
        
        return await self.router.execute_with_failover(
            translate_operation,
            operation_name="translate"
        )
    
    async def detect_language(self, text: str) -> str:
        """
        Detect language of text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Language code
        """
        # Use first available provider for detection
        if self.providers:
            try:
                return await self.providers[0].detect_language(text)
            except Exception as e:
                logger.warning(f"Language detection failed: {e}")
        
        # Fallback to default
        return self.settings.default_language_hint
    
    def get_current_provider_name(self) -> str:
        """Get current active provider name."""
        return self.router.get_current_provider_name()
    
    def get_health_status(self):
        """Get health status of all providers."""
        return self.router.get_health_status()

