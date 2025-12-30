"""Service for generating conversation participation suggestions."""

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
    """Service that generates conversation participation suggestions (statements, comments, or questions)."""
    
    def __init__(self, settings: Settings, llm_router: LLMRouter, memory: ConversationMemory):
        """
        Initialize questions service.
        
        Args:
            settings: Application settings
            llm_router: LLM router for generating suggestions
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
        logger.info("Conversation suggestions service started")
    
    async def _questions_loop(self):
        """Main loop for generating conversation suggestions."""
        while self.is_running:
            try:
                await asyncio.sleep(self.settings.questions_update_seconds)
                
                if not self.is_running:
                    break
                
                # Check if we have enough content
                recent_transcripts = self.memory.get_recent_transcripts()
                
                if len(recent_transcripts) < 3:  # Need at least a few exchanges
                    logger.debug(f"Not enough transcripts for suggestions: {len(recent_transcripts)}/3. Waiting...")
                    continue
                
                logger.info(f"Generating conversation suggestions from {len(recent_transcripts)} transcripts...")
                # Generate suggestions
                await self._generate_questions()
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Conversation suggestions loop error: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _generate_questions(self):
        """Generate conversation participation suggestions (statements, comments, or questions)."""
        try:
            # Get conversation context
            context_text = self.memory.get_full_context_text(include_translations=True)
            
            if not context_text:
                return
            
            # Build prompt - generate relevant statements, comments, or questions in both languages
            prompt = f"""Based on the following conversation, generate {self.settings.questions_max_count} relevant suggestions in both English and Spanish that someone could use to participate in the conversation.

These suggestions can be:

1. **AFFIRMATIVE STATEMENTS/COMMENTS** - when there's something to agree with or highlight:
   - "That's a great point" / "Ese es un gran punto"
   - "I agree with that approach" / "Estoy de acuerdo con ese enfoque"
   - "This makes a lot of sense" / "Esto tiene mucho sentido"
   - "That's exactly right" / "Eso es exactamente correcto"

2. **QUESTIONS/CLARIFICATIONS** - when something needs more information or clarification:
   - "Could you elaborate on that?" / "¿Podrías elaborar sobre eso?"
   - "What do you mean by...?" / "¿Qué quieres decir con...?"
   - "How would that work in practice?" / "¿Cómo funcionaría eso en la práctica?"
   - "Can you give an example?" / "¿Puedes dar un ejemplo?"

Choose the most appropriate type based on the conversation context. If something is clear and good, suggest statements of agreement. If something is unclear or needs more detail, suggest questions for clarification.

For each suggestion, provide:
1. The phrase in English (question_en)
2. The phrase in Spanish (question_es)
3. A brief reason why this suggestion is relevant
4. A priority score (0-10) indicating how relevant/useful it is

Conversation:
{context_text}

Generate the suggestions in JSON format with this structure:
{{
  "questions": [
    {{
      "question_en": "Phrase in English",
      "question_es": "Frase en español",
      "reason": "Why this suggestion is relevant",
      "priority": 7
    }}
  ]
}}

IMPORTANT: Mix statements and questions as appropriate. Provide both English and Spanish versions.
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
            
            # Update current questions (now statements/comments)
            self.current_questions = response.questions[:self.settings.questions_max_count]
            
            logger.info(f"Generated {len(self.current_questions)} conversation suggestions")
            
            # Publish questions event
            await event_bus.publish("questions", self.current_questions)
            
            logger.info(f"Published {len(self.current_questions)} conversation suggestions to UI")
        
        except Exception as e:
            logger.error(f"Conversation suggestions generation error: {e}")
    
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
        
        logger.info("Conversation suggestions service stopped")
    
    def get_current_questions(self) -> List[QuestionPair]:
        """Get current conversation suggestions."""
        return self.current_questions
    
    async def force_update(self):
        """Force immediate suggestions update."""
        await self._generate_questions()

