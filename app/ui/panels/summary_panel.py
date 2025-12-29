"""Panel for displaying live summary/idea general."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton

from app.config.settings import Settings


class SummaryPanel(QWidget):
    """Panel displaying live summary with accumulated context."""
    
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
        
        refresh_btn = QPushButton("Refresh Summary")
        refresh_btn.clicked.connect(self.refresh_summary)
        button_layout.addWidget(refresh_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_text)
        button_layout.addWidget(clear_btn)
        
        layout.addLayout(button_layout)
    
    def refresh_summary(self):
        """Trigger summary refresh."""
        # This will be connected to the summary generator
        # For now, emit a signal or call a callback
        pass
    
    def set_refresh_callback(self, callback):
        """Set callback for refresh button."""
        # Find refresh button by checking all buttons
        for widget in self.findChildren(QPushButton):
            if widget.text() == "Refresh Summary":
                widget.clicked.disconnect()
                widget.clicked.connect(callback)
                break
    
    def clear_text(self):
        """Clear the text display."""
        self.text_display.clear()
    
    def update_summary(self, summary: str):
        """Update the summary text."""
        self.text_display.setPlainText(summary)

