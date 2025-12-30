"""OpenAI LLM provider implementation."""

from typing import Optional
import logging

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from app.llm.base import LLMProvider
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, **kwargs):
        super().__init__(api_key, model, **kwargs)
        
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not installed")
        
        if not api_key:
            raise ValueError("OpenAI API key required")
        
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model or "gpt-4o"
    
    async def generate_json(
        self,
        prompt: str,
        schema: BaseModel,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> BaseModel:
        """Generate structured JSON output."""
        try:
            # Get JSON schema from Pydantic model
            json_schema = schema.model_json_schema()

            # OpenAI requires a 'name' field in the json_schema
            schema_name = schema.__name__ if hasattr(schema, '__name__') else "Response"

            response = await self.client.beta.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name,
                        "schema": json_schema
                    }
                },
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content
            if content:
                # Parse JSON and validate against schema
                import json
                data = json.loads(content)
                return schema.model_validate(data)
            
            raise ValueError("Empty response from OpenAI")
        
        except Exception as e:
            logger.error(f"OpenAI JSON generation failed: {e}")
            raise
    
    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate plain text output."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content
            return content or ""
        
        except Exception as e:
            logger.error(f"OpenAI text generation failed: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Check OpenAI API health."""
        try:
            # Simple health check
            await self.client.models.list()
            return True
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False
    
    def get_provider_name(self) -> str:
        return "openai"

