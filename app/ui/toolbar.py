"""Control toolbar for session management."""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QCheckBox
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor


class ControlToolbar(QWidget):
    """Toolbar with session control buttons."""
    
    # Signals
    start_requested = Signal()
    pause_requested = Signal()
    resume_requested = Signal()
    finalize_requested = Signal()
    clear_requested = Signal()
    audio_device_requested = Signal()
    audio_is_spanish_changed = Signal(bool)  # Emitted when checkbox state changes
    
    def __init__(self, parent=None):
        """Initialize control toolbar."""
        super().__init__(parent)
        self.is_running = False
        self.is_paused = False
        self.init_ui()
        self.update_button_states()
    
    def init_ui(self):
        """Initialize toolbar UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        # Start button (green)
        self.start_btn = QPushButton("▶ Iniciar")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d5a2d;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #3d7a3d;
            }
            QPushButton:disabled {
                background-color: #1a3a1a;
                color: #888888;
            }
        """)
        self.start_btn.clicked.connect(self._on_start_clicked)
        layout.addWidget(self.start_btn)
        
        # Pause/Resume button (yellow/orange)
        self.pause_btn = QPushButton("⏸ Pausar")
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #5a4d2d;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7a6d3d;
            }
            QPushButton:disabled {
                background-color: #3a2d1a;
                color: #888888;
            }
        """)
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        layout.addWidget(self.pause_btn)
        
        # Finalize button (red)
        self.finalize_btn = QPushButton("⏹ Finalizar")
        self.finalize_btn.setStyleSheet("""
            QPushButton {
                background-color: #5a2d2d;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #7a3d3d;
            }
            QPushButton:disabled {
                background-color: #3a1a1a;
                color: #888888;
            }
        """)
        self.finalize_btn.clicked.connect(self._on_finalize_clicked)
        layout.addWidget(self.finalize_btn)
        
        layout.addStretch()
        
        # Audio is Spanish checkbox
        self.audio_is_spanish_checkbox = QCheckBox("Audio en Español")
        self.audio_is_spanish_checkbox.setToolTip(
            "Marcar si el audio es en español.\n"
            "Nota: El sistema detecta automáticamente el idioma y traducirá\n"
            "si detecta inglés, incluso si este checkbox está marcado.\n"
            "Esto previene que aparezca texto en inglés en la columna de traducción."
        )
        self.audio_is_spanish_checkbox.setStyleSheet("""
            QCheckBox {
                color: white;
                font-weight: bold;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #4a4a4a;
                border-radius: 3px;
                background-color: #2a2a2a;
            }
            QCheckBox::indicator:checked {
                background-color: #2d5a2d;
                border-color: #3d7a3d;
            }
            QCheckBox::indicator:hover {
                border-color: #5a5a5a;
            }
        """)
        self.audio_is_spanish_checkbox.setChecked(False)
        self.audio_is_spanish_checkbox.stateChanged.connect(
            lambda state: self.audio_is_spanish_changed.emit(state == Qt.Checked)
        )
        layout.addWidget(self.audio_is_spanish_checkbox)
        
        # Audio device button (blue)
        self.audio_device_btn = QPushButton("🎤 Audio")
        self.audio_device_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d3a5a;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #3d4a7a;
            }
        """)
        self.audio_device_btn.clicked.connect(self._on_audio_device_clicked)
        layout.addWidget(self.audio_device_btn)
        
        # Clear button (gray)
        self.clear_btn = QPushButton("🗑 Limpiar")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #888888;
            }
        """)
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        layout.addWidget(self.clear_btn)
    
    def _on_start_clicked(self):
        """Handle start button click."""
        self.start_requested.emit()
    
    def _on_pause_clicked(self):
        """Handle pause/resume button click."""
        if self.is_paused:
            self.resume_requested.emit()
        else:
            self.pause_requested.emit()
    
    def _on_finalize_clicked(self):
        """Handle finalize button click."""
        self.finalize_requested.emit()
    
    def _on_clear_clicked(self):
        """Handle clear button click."""
        self.clear_requested.emit()
    
    def _on_audio_device_clicked(self):
        """Handle audio device button click."""
        self.audio_device_requested.emit()
    
    def set_running(self, running: bool):
        """Set running state."""
        self.is_running = running
        self.update_button_states()
    
    def set_paused(self, paused: bool):
        """Set paused state."""
        self.is_paused = paused
        if paused:
            self.pause_btn.setText("▶ Retomar")
        else:
            self.pause_btn.setText("⏸ Pausar")
        self.update_button_states()
    
    def update_button_states(self):
        """Update button enabled/disabled states based on current state."""
        # Start button: enabled when not running
        self.start_btn.setEnabled(not self.is_running)
        
        # Pause/Resume button: enabled when running
        self.pause_btn.setEnabled(self.is_running)
        
        # Finalize button: enabled when running
        self.finalize_btn.setEnabled(self.is_running)
        
        # Clear button: always enabled (but will show confirmation dialog)

