"""Event bus for inter-component communication."""

import asyncio
from typing import Callable, Dict, List, Any
from collections import defaultdict
import logging

from app.core.schemas import TranscriptEvent, TranslationResult, SummaryUpdate, QuestionPair, ProviderChangeEvent


logger = logging.getLogger(__name__)


class EventBus:
    """Thread-safe event bus for publishing and subscribing to events."""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    def subscribe(self, event_type: str, callback: Callable):
        """
        Subscribe to events of a specific type.
        
        Args:
            event_type: Event type (e.g., "transcript", "translation", "summary")
            callback: Async or sync callback function
        """
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to {event_type}: {callback.__name__}")
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """Unsubscribe from events."""
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)
            logger.debug(f"Unsubscribed from {event_type}: {callback.__name__}")
    
    async def publish(self, event_type: str, data: Any):
        """
        Publish an event to all subscribers.
        
        Args:
            event_type: Event type
            data: Event data (should match expected schema)
        """
        async with self._lock:
            callbacks = self._subscribers[event_type].copy()
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Error in event callback {callback.__name__}: {e}", exc_info=True)
    
    def publish_sync(self, event_type: str, data: Any):
        """Synchronous version of publish (for use in non-async contexts)."""
        callbacks = self._subscribers[event_type].copy()
        
        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in event callback {callback.__name__}: {e}", exc_info=True)


# Global event bus instance
event_bus = EventBus()

