"""Service for generating live summaries."""

import asyncio
from typing import Optional
from datetime import datetime, timedelta
import logging

from app.llm.router import LLMRouter
from app.core.memory import ConversationMemory
from app.core.schemas import SummaryUpdate
from app.core.event_bus import event_bus
from app.config.settings import Settings

logger = logging.getLogger(__name__)


class SummaryService:
    """Service that generates live summaries of conversations."""
    
    def __init__(self, settings: Settings, llm_router: LLMRouter, memory: ConversationMemory):
        """
        Initialize summary service.
        
        Args:
            settings: Application settings
            llm_router: LLM router for generating summaries
            memory: Conversation memory
        """
        self.settings = settings
        self.llm_router = llm_router
        self.memory = memory
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.current_summary: Optional[SummaryUpdate] = None
        self.last_update_time: Optional[datetime] = None
    
    async def start(self):
        """Start summary service."""
        if self.is_running:
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._summary_loop())
        logger.info("Summary service started")
    
    async def _summary_loop(self):
        """Main loop for generating summaries."""
        while self.is_running:
            try:
                await asyncio.sleep(self.settings.summary_update_seconds)
                
                if not self.is_running:
                    break
                
                # Check if we have enough content
                recent_transcripts = self.memory.get_recent_transcripts(
                    minutes=self.settings.summary_max_context_minutes
                )
                
                if not recent_transcripts:
                    continue
                
                # Generate or update summary
                await self._generate_summary()
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Summary loop error: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _generate_summary(self):
        """Generate or update summary."""
        try:
            # Get recent context
            context_text = self.memory.get_full_context_text(include_translations=True)
            
            if not context_text:
                return
            
            # Build prompt
            if self.current_summary:
                # Update existing summary
                prompt = f"""You are maintaining a live summary of a conversation. 
Here is the current summary:

{self.current_summary.summary}

Here is new conversation content that has occurred since the last update:

{context_text}

Update the summary to include the new information while maintaining important facts and decisions from the previous summary. 
Keep it concise but comprehensive. Focus on key points, decisions, and important information.

Updated summary:"""
            else:
                # Create new summary
                prompt = f"""Create a concise summary of the following conversation. 
Focus on key points, decisions, and important information.

Conversation:
{context_text}

Summary:"""
            
            # Generate summary
            summary_text = await self.llm_router.generate_text(
                prompt=prompt,
                temperature=0.5,
                max_tokens=500
            )
            
            # Create summary update
            version = (self.current_summary.version + 1) if self.current_summary else 1
            self.current_summary = SummaryUpdate(
                summary=summary_text.strip(),
                context_minutes=self.settings.summary_max_context_minutes,
                version=version
            )
            self.last_update_time = datetime.now()
            
            # Publish summary event
            await event_bus.publish("summary", self.current_summary)
            
            logger.debug(f"Summary updated (version {version})")
        
        except Exception as e:
            logger.error(f"Summary generation error: {e}")
    
    async def stop(self):
        """Stop summary service."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                    pass
        
        logger.info("Summary service stopped")
    
    def get_current_summary(self) -> Optional[SummaryUpdate]:
        """Get current summary."""
        return self.current_summary
    
    async def force_update(self):
        """Force immediate summary update."""
        await self._generate_summary()

