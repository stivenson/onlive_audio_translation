"""Dialog for selecting audio input device."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox
)
from PySide6.QtCore import Qt
from typing import Optional, List, Dict

from app.audio.capture import AudioCapture


class AudioDeviceDialog(QDialog):
    """Dialog for selecting audio input device."""
    
    def __init__(self, current_device_index: Optional[int] = None, parent=None):
        """
        Initialize audio device dialog.
        
        Args:
            current_device_index: Currently selected device index
            parent: Parent widget
        """
        super().__init__(parent)
        self.current_device_index = current_device_index
        self.selected_device_index: Optional[int] = None
        self.devices: List[Dict] = []
        self.init_ui()
        self.load_devices()
    
    def init_ui(self):
        """Initialize the dialog UI."""
        self.setWindowTitle("Seleccionar Dispositivo de Audio")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("Selecciona el dispositivo de entrada de audio:")
        title.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(title)
        
        # Info label
        info = QLabel("Para capturar audio del sistema, selecciona 'Stereo Mix' o 'Mezcla estéreo'")
        info.setStyleSheet("color: #888888; font-size: 11px; margin-bottom: 10px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Devices list
        self.devices_list = QListWidget()
        self.devices_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #2a2a2a;
            }
            QListWidget::item:hover {
                background-color: #2a2a2a;
            }
            QListWidget::item:selected {
                background-color: #3a5a3a;
            }
        """)
        self.devices_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.devices_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: white;
                padding: 6px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
        """)
        refresh_btn.clicked.connect(self.load_devices)
        button_layout.addWidget(refresh_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a2a2a;
                color: white;
                padding: 6px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #5a3a3a;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("Aceptar")
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d5a2d;
                color: white;
                padding: 6px 15px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d7a3d;
            }
        """)
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
    
    def load_devices(self):
        """Load available audio devices."""
        self.devices_list.clear()
        self.devices = []
        
        try:
            capture = AudioCapture()
            devices = capture.list_devices()
            
            if not devices:
                item = QListWidgetItem("No se encontraron dispositivos de audio")
                item.setFlags(Qt.NoItemFlags)
                self.devices_list.addItem(item)
                return
            
            self.devices = devices
            
            selected_item = None
            for device in devices:
                device_name = device['name']
                device_index = device['index']
                channels = device.get('channels', 1)
                sample_rate = device.get('sample_rate', 0)
                
                # Format display text
                display_text = f"{device_name}"
                if channels > 1:
                    display_text += f" ({channels} canales)"
                if sample_rate > 0:
                    display_text += f" - {sample_rate}Hz"
                
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, device_index)
                
                # Highlight loopback devices
                name_lower = device_name.lower()
                if 'stereo mix' in name_lower or 'mezcla estéreo' in name_lower or 'loopback' in name_lower:
                    item.setForeground(Qt.green)
                    item.setText(f"🎤 {display_text} (Recomendado para audio del sistema)")
                
                # Mark current selection
                if device_index == self.current_device_index:
                    item.setSelected(True)
                    selected_item = item
                
                self.devices_list.addItem(item)
            
            # Ensure selected item is visible and focused
            if selected_item:
                self.devices_list.setCurrentItem(selected_item)
                self.devices_list.scrollToItem(selected_item)
        
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"No se pudieron cargar los dispositivos de audio:\n{str(e)}"
            )
    
    def accept(self):
        """Handle accept button click."""
        current_item = self.devices_list.currentItem()
        
        if not current_item:
            QMessageBox.warning(
                self,
                "Selección requerida",
                "Por favor, selecciona un dispositivo de audio."
            )
            return
        
        self.selected_device_index = current_item.data(Qt.UserRole)
        super().accept()
    
    def get_selected_device_index(self) -> Optional[int]:
        """Get selected device index."""
        return self.selected_device_index

