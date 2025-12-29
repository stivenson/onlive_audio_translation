"""Retry policy with exponential backoff."""

import asyncio
import random
from typing import Callable, TypeVar, Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError
)
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryPolicy:
    """Retry policy with exponential backoff and jitter."""
    
    def __init__(
        self,
        max_retries: int = 2,
        initial_wait: float = 1.0,
        max_wait: float = 10.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        """
        Initialize retry policy.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_wait: Initial wait time in seconds
            max_wait: Maximum wait time in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter
        """
        self.max_retries = max_retries
        self.initial_wait = initial_wait
        self.max_wait = max_wait
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def _should_retry(self, exception: Exception) -> bool:
        """Determine if exception is retryable."""
        # Retry on network errors, timeouts, rate limits, server errors
        retryable_exceptions = (
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
        )
        
        if isinstance(exception, retryable_exceptions):
            return True
        
        # Check for HTTP status codes (if exception has status_code attribute)
        if hasattr(exception, 'status_code'):
            status = exception.status_code
            if status in (429, 500, 502, 503, 504):
                return True
        
        # Check for error messages
        error_str = str(exception).lower()
        if any(keyword in error_str for keyword in ['timeout', 'connection', 'rate limit', '503', '502', '500']):
            return True
        
        return False
    
    async def execute(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """
        Execute function with retry policy.
        
        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if not self._should_retry(e):
                    logger.debug(f"Non-retryable exception: {e}")
                    raise
                
                if attempt < self.max_retries:
                    wait_time = min(
                        self.initial_wait * (self.exponential_base ** attempt),
                        self.max_wait
                    )
                    
                    if self.jitter:
                        wait_time = wait_time * (0.5 + random.random())
                    
                    logger.debug(f"Retry attempt {attempt + 1}/{self.max_retries} after {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                else:
                    logger.warning(f"All {self.max_retries + 1} attempts failed")
        
        raise last_exception

