"""Panel for displaying questions/replicas in English and Spanish."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QPushButton,
    QListWidgetItem, QHBoxLayout
)

from app.config.settings import Settings


class QuestionsPanel(QWidget):
    """Panel displaying suggested questions/replicas in EN and ES."""
    
    def __init__(self, title: str, settings: Settings):
        super().__init__()
        self.settings = settings
        self.init_ui(title)
    
    def init_ui(self, title: str):
        """Initialize panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)
        
        # Questions list
        self.questions_list = QListWidget()
        self.questions_list.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        layout.addWidget(self.questions_list)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh Questions")
        refresh_btn.clicked.connect(self.refresh_questions)
        button_layout.addWidget(refresh_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_questions)
        button_layout.addWidget(clear_btn)
        
        layout.addLayout(button_layout)
    
    def refresh_questions(self):
        """Trigger questions refresh."""
        # This will be connected to the questions generator
        pass
    
    def clear_questions(self):
        """Clear the questions list."""
        self.questions_list.clear()
    
    def add_questions(self, questions: list):
        """Add multiple questions to the list."""
        for q in questions:
            if hasattr(q, 'question_en') and hasattr(q, 'question_es'):
                self.add_question(q.question_en, q.question_es)
    
    def add_question(self, question_en: str, question_es: str):
        """Add a question pair to the list."""
        # Since questions are now only in Spanish, just show the Spanish version
        # Use question_es if available, otherwise fallback to question_en (which should also be Spanish)
        question_text = question_es if question_es else question_en
        item = QListWidgetItem(question_text)
        self.questions_list.addItem(item)

