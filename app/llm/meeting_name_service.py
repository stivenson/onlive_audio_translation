"""Service for inferring meeting names using LLM."""

import logging
from typing import Optional

from app.llm.router import LLMRouter
from app.config.settings import Settings
from app.core.memory import ConversationMemory

logger = logging.getLogger(__name__)


class MeetingNameService:
    """Service to infer meeting names from conversation context."""
    
    def __init__(self, llm_router: LLMRouter):
        """
        Initialize meeting name service.
        
        Args:
            llm_router: LLM router for generating names
        """
        self.llm_router = llm_router
    
    async def infer_meeting_name(
        self,
        memory: ConversationMemory,
        current_summary: Optional[str] = None
    ) -> str:
        """
        Infer a meeting name from conversation context.
        
        Args:
            memory: Conversation memory with transcripts and translations
            current_summary: Current summary if available
            
        Returns:
            Inferred meeting name (3-5 words, hyphenated, no special chars)
        """
        # Build context for LLM
        context_parts = []
        
        # Add summary if available
        if current_summary:
            context_parts.append(f"Summary: {current_summary}")
        
        # Add recent transcripts (last 10-15)
        recent_transcripts = memory.get_recent_transcripts(minutes=30)
        if recent_transcripts:
            transcript_text = memory.get_full_context_text(include_translations=False)
            # Limit to reasonable length
            if len(transcript_text) > 2000:
                transcript_text = transcript_text[-2000:]  # Last 2000 chars
            context_parts.append(f"Recent conversation:\n{transcript_text}")
        
        # If no context available, use default
        if not context_parts:
            from datetime import datetime
            return f"Meeting-{datetime.now().strftime('%Y%m%d')}"
        
        context = "\n\n".join(context_parts)
        
        # Create prompt
        prompt = f"""Based on this conversation, generate a short and descriptive meeting name.

Requirements:
- 3 to 5 words maximum
- Use hyphens instead of spaces (e.g., "Weekly-Standup-Review")
- No special characters, only letters, numbers, and hyphens
- Descriptive of the main topic or purpose
- In English

Conversation context:
{context}

Generate only the meeting name, nothing else:"""

        try:
            name = await self.llm_router.generate_text(
                prompt=prompt,
                temperature=0.7,
                max_tokens=50
            )
            
            # Clean up the response
            name = name.strip()
            
            # Remove quotes if present
            if name.startswith('"') and name.endswith('"'):
                name = name[1:-1]
            if name.startswith("'") and name.endswith("'"):
                name = name[1:-1]
            
            # Replace spaces with hyphens
            name = name.replace(" ", "-")
            
            # Remove any special characters except hyphens and alphanumeric
            import re
            name = re.sub(r'[^a-zA-Z0-9\-]', '', name)
            
            # Ensure it's not empty
            if not name:
                from datetime import datetime
                name = f"Meeting-{datetime.now().strftime('%Y%m%d')}"
            
            # Limit length
            if len(name) > 60:
                name = name[:60]
            
            logger.info(f"Inferred meeting name: {name}")
            return name
            
        except Exception as e:
            logger.error(f"Failed to infer meeting name: {e}")
            # Fallback to timestamp-based name
            from datetime import datetime
            return f"Meeting-{datetime.now().strftime('%Y%m%d')}"

