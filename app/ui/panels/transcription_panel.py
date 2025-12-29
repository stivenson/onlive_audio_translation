"""Panel for displaying original transcription."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton
from PySide6.QtCore import Qt

from app.config.settings import Settings


class TranscriptionPanel(QWidget):
    """Panel displaying original transcription with speaker roles."""
    
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
        
        # Text display
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        layout.addWidget(self.text_display)
        
        # Control buttons
        button_layout = QVBoxLayout()
        
        self.auto_scroll_btn = QPushButton("Auto-scroll: ON")
        self.auto_scroll_btn.setCheckable(True)
        self.auto_scroll_btn.setChecked(True)
        self.auto_scroll_btn.clicked.connect(self.toggle_auto_scroll)
        button_layout.addWidget(self.auto_scroll_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_text)
        button_layout.addWidget(clear_btn)
        
        layout.addLayout(button_layout)
        
        self.auto_scroll_enabled = True
    
    def toggle_auto_scroll(self):
        """Toggle auto-scroll functionality."""
        self.auto_scroll_enabled = self.auto_scroll_btn.isChecked()
        self.auto_scroll_btn.setText(
            f"Auto-scroll: {'ON' if self.auto_scroll_enabled else 'OFF'}"
        )
    
    def clear_text(self):
        """Clear the text display."""
        self.text_display.clear()
    
    def append_text(self, text: str, speaker: str = None):
        """Append text to the display with optional speaker role."""
        # Format text
        if speaker:
            formatted_text = f"[{speaker}]: {text}\n"
        else:
            formatted_text = f"{text}\n"
        
        # Use plain text for now (HTML formatting can be added later if needed)
        self.text_display.append(formatted_text)
        
        if self.auto_scroll_enabled:
            scrollbar = self.text_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

