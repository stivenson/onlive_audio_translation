"""Base classes and interfaces for LLM providers."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pydantic import BaseModel

from app.core.schemas import QuestionPair, SummaryUpdate


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.model = model
        self.config = kwargs
    
    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        schema: BaseModel,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> BaseModel:
        """
        Generate structured JSON output following a Pydantic schema.
        
        Args:
            prompt: The prompt to send to the LLM
            schema: Pydantic model class to validate output
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Instance of the schema class with validated data
        """
        pass
    
    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate plain text output.
        
        Args:
            prompt: The prompt to send to the LLM
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text string
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy and accessible."""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of this provider."""
        pass

