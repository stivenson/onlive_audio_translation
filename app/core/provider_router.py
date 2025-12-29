"""Provider router with failover, health checks, and circuit breakers."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, TypeVar, Generic, Dict, Any, Callable
import logging

from app.core.circuit_breaker import CircuitBreaker, CircuitState
from app.core.retry_policy import RetryPolicy
from app.core.schemas import ProviderStatus, ProviderHealth, ProviderChangeEvent
from app.core.event_bus import event_bus

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ProviderRouter(Generic[T]):
    """Router for providers with failover, health checks, and circuit breakers."""
    
    def __init__(
        self,
        providers: List[T],
        provider_names: List[str],
        failover_cooldown_seconds: int = 120,
        max_retries: int = 2,
        timeout_seconds: int = 15,
        circuit_breaker_failures: int = 5,
        circuit_breaker_timeout: int = 60
    ):
        """
        Initialize provider router.
        
        Args:
            providers: List of provider instances
            provider_names: List of provider names (same order as providers)
            failover_cooldown_seconds: Cooldown before switching back to previous provider
            max_retries: Maximum retries per operation
            timeout_seconds: Operation timeout
            circuit_breaker_failures: Failures before opening circuit
            circuit_breaker_timeout: Seconds before trying half-open
        """
        if len(providers) != len(provider_names):
            raise ValueError("providers and provider_names must have same length")
        
        self.providers = providers
        self.provider_names = provider_names
        self.failover_cooldown_seconds = failover_cooldown_seconds
        
        # Current active provider index
        self.current_index = 0
        
        # Circuit breakers per provider
        self.circuit_breakers: Dict[int, CircuitBreaker] = {
            i: CircuitBreaker(
                failure_threshold=circuit_breaker_failures,
                timeout_seconds=circuit_breaker_timeout
            )
            for i in range(len(providers))
        }
        
        # Retry policies per provider
        self.retry_policies: Dict[int, RetryPolicy] = {
            i: RetryPolicy(max_retries=max_retries)
            for i in range(len(providers))
        }
        
        # Health tracking
        self.health_status: Dict[int, ProviderHealth] = {
            i: ProviderHealth(
                provider_name=name,
                status=ProviderStatus.HEALTHY,
                failure_count=0
            )
            for i, name in enumerate(provider_names)
        }
        
        # Failover tracking
        self.last_failover_time: Optional[datetime] = None
        self.last_failed_provider: Optional[int] = None
        
        # Latency tracking
        self.latency_history: Dict[int, List[float]] = {
            i: [] for i in range(len(providers))
        }
    
    def get_current_provider(self) -> T:
        """Get the current active provider."""
        return self.providers[self.current_index]
    
    def get_current_provider_name(self) -> str:
        """Get the current active provider name."""
        return self.provider_names[self.current_index]
    
    def _calculate_p95_latency(self, provider_index: int) -> Optional[float]:
        """Calculate p95 latency for a provider."""
        history = self.latency_history[provider_index]
        if not history:
            return None
        
        sorted_latencies = sorted(history)
        p95_index = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[p95_index] if p95_index < len(sorted_latencies) else sorted_latencies[-1]
    
    def _update_health(self, provider_index: int, success: bool, latency: Optional[float] = None):
        """Update health status for a provider."""
        health = self.health_status[provider_index]
        breaker = self.circuit_breakers[provider_index]
        
        if success:
            breaker.record_success()
            health.status = ProviderStatus.HEALTHY
            health.last_success = datetime.now()
            health.failure_count = breaker.failure_count
            
            if latency is not None:
                self.latency_history[provider_index].append(latency)
                # Keep only last 100 measurements
                if len(self.latency_history[provider_index]) > 100:
                    self.latency_history[provider_index].pop(0)
                health.latency_p95 = self._calculate_p95_latency(provider_index)
        else:
            breaker.record_failure()
            health.last_failure = datetime.now()
            health.failure_count = breaker.failure_count
            
            if breaker.get_state() == CircuitState.OPEN:
                health.status = ProviderStatus.CIRCUIT_OPEN
            else:
                health.status = ProviderStatus.DEGRADED
        
        health.circuit_breaker_state = breaker.get_state().value
        health.last_updated = datetime.now()
    
    def _should_failover(self, provider_index: int) -> bool:
        """Determine if we should failover to next provider."""
        breaker = self.circuit_breakers[provider_index]
        
        # Check circuit breaker
        if not breaker.can_attempt():
            return True
        
        # Check cooldown (don't failover too quickly)
        if self.last_failover_time:
            elapsed = (datetime.now() - self.last_failover_time).total_seconds()
            if elapsed < self.failover_cooldown_seconds:
                return False
        
        return False
    
    def _failover_to_next(self, failed_index: int):
        """Failover to the next available provider."""
        old_provider = self.provider_names[self.current_index]
        
        # Find next healthy provider
        for i in range(len(self.providers)):
            next_index = (failed_index + 1 + i) % len(self.providers)
            
            if next_index == failed_index:
                # Wrapped around, no healthy provider found
                logger.error("All providers are down!")
                return
            
            breaker = self.circuit_breakers[next_index]
            if breaker.can_attempt():
                self.current_index = next_index
                self.last_failover_time = datetime.now()
                self.last_failed_provider = failed_index
                
                new_provider = self.provider_names[self.current_index]
                logger.warning(f"Failover: {old_provider} -> {new_provider}")
                
                # Publish failover event
                event = ProviderChangeEvent(
                    domain="unknown",  # Will be set by specific routers
                    old_provider=old_provider,
                    new_provider=new_provider,
                    reason=f"Circuit breaker open or provider unhealthy"
                )
                event_bus.publish_sync("provider_change", event)
                
                return
        
        logger.error("No healthy providers available for failover")
    
    async def execute_with_failover(
        self,
        operation: Callable[[T], Any],
        operation_name: str = "operation"
    ) -> Any:
        """
        Execute operation with automatic failover.
        
        Args:
            operation: Async function that takes provider as argument
            operation_name: Name for logging
            
        Returns:
            Operation result
            
        Raises:
            Exception: If all providers fail
        """
        last_exception = None
        attempts = 0
        max_attempts = len(self.providers)
        
        while attempts < max_attempts:
            provider = self.get_current_provider()
            provider_name = self.get_current_provider_name()
            provider_index = self.current_index
            
            breaker = self.circuit_breakers[provider_index]
            
            # Check circuit breaker
            if not breaker.can_attempt():
                logger.warning(f"{provider_name} circuit is open, failing over")
                self._failover_to_next(provider_index)
                attempts += 1
                continue
            
            # Execute with retry policy
            retry_policy = self.retry_policies[provider_index]
            start_time = datetime.now()
            
            try:
                result = await retry_policy.execute(operation, provider)
                
                # Success
                latency = (datetime.now() - start_time).total_seconds()
                self._update_health(provider_index, success=True, latency=latency)
                return result
                
            except Exception as e:
                latency = (datetime.now() - start_time).total_seconds()
                self._update_health(provider_index, success=False, latency=latency)
                last_exception = e
                
                logger.warning(f"{provider_name} failed: {e}")
                
                # Try next provider
                self._failover_to_next(provider_index)
                attempts += 1
        
        # All providers failed
        logger.error(f"All providers failed for {operation_name}")
        raise last_exception or Exception("All providers failed")
    
    def get_health_status(self) -> Dict[str, ProviderHealth]:
        """Get health status for all providers."""
        return {
            name: self.health_status[i]
            for i, name in enumerate(self.provider_names)
        }
    
    async def health_check_all(self):
        """Perform health check on all providers."""
        for i, provider in enumerate(self.providers):
            try:
                if hasattr(provider, 'health_check'):
                    is_healthy = await provider.health_check()
                    self._update_health(i, success=is_healthy)
                else:
                    logger.warning(f"Provider {self.provider_names[i]} has no health_check method")
            except Exception as e:
                logger.error(f"Health check failed for {self.provider_names[i]}: {e}")
                self._update_health(i, success=False)

