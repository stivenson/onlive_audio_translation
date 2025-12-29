"""Service for generating question suggestions."""

import asyncio
from typing import List, Optional
from datetime import datetime
import logging

from app.llm.router import LLMRouter
from app.core.memory import ConversationMemory
from app.core.schemas import QuestionPair
from app.core.event_bus import event_bus
from app.config.settings import Settings

logger = logging.getLogger(__name__)


class QuestionsService:
    """Service that generates question suggestions based on conversation."""
    
    def __init__(self, settings: Settings, llm_router: LLMRouter, memory: ConversationMemory):
        """
        Initialize questions service.
        
        Args:
            settings: Application settings
            llm_router: LLM router for generating questions
            memory: Conversation memory
        """
        self.settings = settings
        self.llm_router = llm_router
        self.memory = memory
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.current_questions: List[QuestionPair] = []
    
    async def start(self):
        """Start questions service."""
        if self.is_running:
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._questions_loop())
        logger.info("Questions service started")
    
    async def _questions_loop(self):
        """Main loop for generating questions."""
        while self.is_running:
            try:
                await asyncio.sleep(self.settings.questions_update_seconds)
                
                if not self.is_running:
                    break
                
                # Check if we have enough content
                recent_transcripts = self.memory.get_recent_transcripts()
                
                if len(recent_transcripts) < 3:  # Need at least a few exchanges
                    continue
                
                # Generate questions
                await self._generate_questions()
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Questions loop error: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _generate_questions(self):
        """Generate question suggestions."""
        try:
            # Get conversation context
            context_text = self.memory.get_full_context_text(include_translations=True)
            
            if not context_text:
                return
            
            # Build prompt
            prompt = f"""Based on the following conversation, generate {self.settings.questions_max_count} relevant questions or follow-up statements that would help clarify, deepen understanding, or fill gaps in the discussion.

For each question, provide:
1. The question in English
2. The same question translated to Spanish
3. A brief reason why this question is relevant
4. A priority score (0-10) indicating how important/urgent the question is

Conversation:
{context_text}

Generate questions in JSON format with this structure:
{{
  "questions": [
    {{
      "question_en": "Question in English",
      "question_es": "Pregunta en español",
      "reason": "Why this question is relevant",
      "priority": 7
    }}
  ]
}}

Only provide the JSON, no additional text."""
            
            # Generate questions using structured output
            from pydantic import BaseModel
            
            class QuestionsResponse(BaseModel):
                questions: List[QuestionPair]
            
            response = await self.llm_router.generate_json(
                prompt=prompt,
                schema=QuestionsResponse,
                temperature=0.7,
                max_tokens=1000
            )
            
            # Update current questions
            self.current_questions = response.questions[:self.settings.questions_max_count]
            
            # Publish questions event
            await event_bus.publish("questions", self.current_questions)
            
            logger.debug(f"Generated {len(self.current_questions)} questions")
        
        except Exception as e:
            logger.error(f"Questions generation error: {e}")
    
    async def stop(self):
        """Stop questions service."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Questions service stopped")
    
    def get_current_questions(self) -> List[QuestionPair]:
        """Get current questions."""
        return self.current_questions
    
    async def force_update(self):
        """Force immediate questions update."""
        await self._generate_questions()

