"""Controller that orchestrates services and connects them to UI."""

import asyncio
from typing import Optional, List, Dict
import logging

from app.config.settings import Settings
from app.stt.service import STTService
from app.translate.service import TranslationService
from app.llm.router import LLMRouter
from app.llm.summary_service import SummaryService
from app.llm.questions_service import QuestionsService
from app.core.memory import ConversationMemory
from app.core.event_bus import event_bus
from app.core.schemas import TranscriptEvent, TranslationResult, SummaryUpdate, QuestionPair
from app.storage.session_manager import SessionManager

logger = logging.getLogger(__name__)


class AppController:
    """Main application controller."""
    
    def __init__(self, settings: Settings):
        """
        Initialize application controller.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.memory = ConversationMemory(
            max_context_minutes=settings.summary_max_context_minutes
        )
        
        # Initialize routers and services
        # Create separate LLM routers for each service with their specific models
        self.translation_llm_router = LLMRouter(settings, model_override=settings.translation_model_fallback)
        self.summary_llm_router = LLMRouter(settings, model_override=settings.summary_model)
        self.questions_llm_router = LLMRouter(settings, model_override=settings.questions_model)
        
        self.stt_service: Optional[STTService] = None
        self.translation_service: Optional[TranslationService] = None
        self.summary_service: Optional[SummaryService] = None
        self.questions_service: Optional[QuestionsService] = None
        self.session_manager = SessionManager()
        
        self.is_running = False
    
    async def initialize_services(self):
        """Initialize all services."""
        try:
            # Initialize STT service
            self.stt_service = STTService(self.settings)
            
            # Initialize translation service
            self.translation_service = TranslationService(
                self.settings,
                llm_router=self.translation_llm_router
            )
            
            # Initialize summary service
            self.summary_service = SummaryService(
                self.settings,
                llm_router=self.summary_llm_router,
                memory=self.memory
            )
            
            # Initialize questions service
            self.questions_service = QuestionsService(
                self.settings,
                llm_router=self.questions_llm_router,
                memory=self.memory
            )
            
            logger.info("All services initialized")
        
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise
    
    async def start(self):
        """Start all services."""
        if self.is_running:
            return
        
        try:
            await self.initialize_services()
            
            # Start session tracking
            self.session_manager.start_tracking()
            
            # Start services
            await self.stt_service.start()
            await self.translation_service.start()
            await self.summary_service.start()
            await self.questions_service.start()
            
            self.is_running = True
            logger.info("All services started")
        
        except Exception as e:
            logger.error(f"Failed to start services: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop all services."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Stop services in reverse order
        if self.questions_service:
            await self.questions_service.stop()
        
        if self.summary_service:
            await self.summary_service.stop()
        
        if self.translation_service:
            await self.translation_service.stop()
        
        if self.stt_service:
            await self.stt_service.stop()
        
        # Stop session tracking
        self.session_manager.stop_tracking()
        
        logger.info("All services stopped")
    
    def export_session(self, format: str = "json"):
        """Export current session."""
        return self.session_manager.export(format=format)
    
    def setup_ui_callbacks(self, ui_callbacks: dict):
        """
        Setup UI callbacks for events.
        
        Args:
            ui_callbacks: Dictionary with callback functions:
                - on_transcript: Callback for transcript events
                - on_translation: Callback for translation events
                - on_summary: Callback for summary events
                - on_questions: Callback for questions events
        """
        async def handle_transcript(event: TranscriptEvent):
            # Add to memory
            self.memory.add_transcript(event)
            # Call UI callback
            if "on_transcript" in ui_callbacks:
                ui_callbacks["on_transcript"](event)
        
        async def handle_translation(event: TranslationResult):
            # Add to memory
            self.memory.add_translation(event)
            # Call UI callback
            if "on_translation" in ui_callbacks:
                ui_callbacks["on_translation"](event)
        
        async def handle_summary(event: SummaryUpdate):
            # Call UI callback
            if "on_summary" in ui_callbacks:
                ui_callbacks["on_summary"](event)
        
        async def handle_questions(event: List[QuestionPair]):
            # Call UI callback
            if "on_questions" in ui_callbacks:
                ui_callbacks["on_questions"](event)
        
        # Subscribe to events
        event_bus.subscribe("transcript", handle_transcript)
        event_bus.subscribe("translation", handle_translation)
        event_bus.subscribe("summary", handle_summary)
        event_bus.subscribe("questions", handle_questions)
    
    def get_provider_status(self) -> dict:
        """Get status of all providers."""
        status = {}
        
        if self.stt_service:
            status["stt"] = {
                "current": self.stt_service.get_current_provider_name(),
                "health": self.stt_service.get_health_status()
            }
        
        if self.translation_service:
            status["translation"] = {
                "current": self.translation_service.get_current_provider_name(),
                "health": self.translation_service.get_health_status()
            }
        
        if self.translation_llm_router:
            status["translation_llm"] = {
                "current": self.translation_llm_router.get_current_provider_name(),
                "health": self.translation_llm_router.get_health_status(),
                "model": self.settings.translation_model_fallback
            }
        
        if self.summary_llm_router:
            status["summary_llm"] = {
                "current": self.summary_llm_router.get_current_provider_name(),
                "health": self.summary_llm_router.get_health_status(),
                "model": self.settings.summary_model
            }
        
        if self.questions_llm_router:
            status["questions_llm"] = {
                "current": self.questions_llm_router.get_current_provider_name(),
                "health": self.questions_llm_router.get_health_status(),
                "model": self.settings.questions_model
            }
        
        return status

