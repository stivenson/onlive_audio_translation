"""Main application window."""

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from app.config.settings import Settings
from app.ui.controller import AppController


class MainWindow(QMainWindow):
    """Main application window with 4 vertical panels."""
    
    def __init__(self, settings: Settings, controller: AppController):
        super().__init__()
        self.settings = settings
        self.controller = controller
        self.init_ui()
        self.setup_controller_callbacks()
    
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Live Audio Translator")
        self.setGeometry(100, 100, 1600, 900)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main horizontal layout with 4 panels
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        
        # Panel 1: Original Transcription
        from app.ui.panels.transcription_panel import TranscriptionPanel
        self.panel1 = TranscriptionPanel("Original Transcription", self.settings)
        splitter.addWidget(self.panel1)
        
        # Panel 2: Spanish Translation
        from app.ui.panels.translation_panel import TranslationPanel
        self.panel2 = TranslationPanel("Spanish Translation", self.settings)
        splitter.addWidget(self.panel2)
        
        # Panel 3: Summary/Idea General
        from app.ui.panels.summary_panel import SummaryPanel
        self.panel3 = SummaryPanel("Idea General / Summary", self.settings)
        splitter.addWidget(self.panel3)
        
        # Panel 4: Questions/Replicas
        from app.ui.panels.questions_panel import QuestionsPanel
        self.panel4 = QuestionsPanel("Questions / Preguntas", self.settings)
        splitter.addWidget(self.panel4)
        
        # Set equal sizes for panels
        splitter.setSizes([400, 400, 400, 400])
        
        main_layout.addWidget(splitter)
        
        # Status bar with provider info
        self.statusBar().showMessage("Ready")
        self.status_label = QLabel("")
        self.statusBar().addPermanentWidget(self.status_label)
        
        # Update status periodically
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(2000)  # Update every 2 seconds
    
    def setup_controller_callbacks(self):
        """Setup callbacks to connect controller events to UI."""
        callbacks = {
            "on_transcript": self.on_transcript,
            "on_translation": self.on_translation,
            "on_summary": self.on_summary,
            "on_questions": self.on_questions
        }
        self.controller.setup_ui_callbacks(callbacks)
    
    def on_transcript(self, event):
        """Handle transcript event."""
        speaker = event.speaker_id or "Unknown"
        self.panel1.append_text(event.text, speaker=speaker)
    
    def on_translation(self, event):
        """Handle translation event."""
        self.panel2.append_text(event.translated_text)
    
    def on_summary(self, event):
        """Handle summary event."""
        self.panel3.update_summary(event.summary)
    
    def on_questions(self, questions):
        """Handle questions event."""
        self.panel4.clear_questions()
        for q in questions:
            self.panel4.add_question(q.question_en, q.question_es)
    
    def update_status(self):
        """Update status bar with provider information."""
        if not self.controller.is_running:
            self.status_label.setText("Services not running")
            return
        
        status = self.controller.get_provider_status()
        parts = []
        
        if "stt" in status:
            parts.append(f"STT: {status['stt']['current']}")
        if "translation" in status:
            parts.append(f"Translate: {status['translation']['current']}")
        if "translation_llm" in status:
            parts.append(f"Trans-Model: {status['translation_llm']['model']}")
        if "summary_llm" in status:
            parts.append(f"Summary-Model: {status['summary_llm']['model']}")
        if "questions_llm" in status:
            parts.append(f"Questions-Model: {status['questions_llm']['model']}")
        
        self.status_label.setText(" | ".join(parts) if parts else "Running")
    
    def closeEvent(self, event):
        """Handle window close event."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.controller.stop())
        except Exception as e:
            print(f"Error stopping controller: {e}")
        event.accept()

