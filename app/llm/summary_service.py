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
        self.last_summarized_timestamp: Optional[datetime] = None
    
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
            # Get new content since last summary
            if self.last_summarized_timestamp:
                # Get only new transcripts/translations since last summary
                new_transcripts = self.memory.get_transcripts_after(self.last_summarized_timestamp)
                new_translations = self.memory.get_translations_after(self.last_summarized_timestamp)
                
                if not new_transcripts and not new_translations:
                    logger.debug("No new content to summarize")
                    return
                
                # Build context text from new content only
                lines = []
                for trans in new_translations:
                    lines.append(f"[{trans.timestamp.strftime('%H:%M:%S')}] {trans.translated_text}")
                
                context_text = "\n".join(lines)
            else:
                # First summary - get all recent context
                context_text = self.memory.get_full_context_text(include_translations=True)
            
            if not context_text:
                return
            
            # Summary is always in Spanish as per requirements ("la idea general es en español")
            # Generate a new paragraph for the new content
            if self.last_summarized_timestamp:
                # Generate a new paragraph for incremental update
                prompt = f"""Eres un asistente que genera resúmenes incrementales de una conversación en español.

Aquí está el nuevo contenido de la conversación que ha ocurrido desde la última actualización:

{context_text}

Genera un nuevo párrafo en español que resuma ÚNICAMENTE esta nueva información. 
Enfócate en puntos clave, decisiones e información importante.
Manténlo conciso (2-4 oraciones).
Responde SOLO con el nuevo párrafo en español, sin texto adicional ni referencias al resumen anterior.

Nuevo párrafo:"""
            else:
                # Create first summary paragraph
                prompt = f"""Crea un párrafo de resumen conciso en español de la siguiente conversación. 
Enfócate en puntos clave, decisiones e información importante.
Manténlo conciso (2-4 oraciones).
Responde SOLO con el párrafo en español, sin texto adicional.

Conversación:
{context_text}

Párrafo de resumen:"""
            
            # Generate summary paragraph
            summary_text = await self.llm_router.generate_text(
                prompt=prompt,
                temperature=0.5,
                max_tokens=300
            )
            
            # Update tracking
            version = (self.current_summary.version + 1) if self.current_summary else 1
            self.current_summary = SummaryUpdate(
                summary=summary_text.strip(),
                context_minutes=self.settings.summary_max_context_minutes,
                version=version
            )
            self.last_update_time = datetime.now()
            
            # Update last summarized timestamp to the latest content timestamp
            translations = self.memory.get_recent_translations()
            if translations:
                self.last_summarized_timestamp = max(t.timestamp for t in translations)
            
            # Publish summary event (this will be appended in the UI)
            await event_bus.publish("summary", self.current_summary)
            
            logger.debug(f"Summary paragraph generated (version {version})")
        
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

