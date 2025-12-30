"""Main application window."""

import asyncio
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
    QLabel, QMessageBox, QDialog
)
from app.ui.audio_device_dialog import AudioDeviceDialog
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
import qasync

from app.config.settings import Settings
from app.ui.controller import AppController
from app.ui.toolbar import ControlToolbar


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
        # Tamaño optimizado para iPad (1024x600) - menos alta
        self.setGeometry(100, 100, 1024, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main vertical layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Control toolbar
        self.toolbar = ControlToolbar()
        self.toolbar.start_requested.connect(self._on_start)
        self.toolbar.pause_requested.connect(self._on_pause)
        self.toolbar.resume_requested.connect(self._on_resume)
        self.toolbar.finalize_requested.connect(self._on_finalize)
        self.toolbar.clear_requested.connect(self._on_clear)
        self.toolbar.audio_device_requested.connect(self._on_audio_device)
        self.toolbar.audio_is_spanish_changed.connect(self._on_audio_is_spanish_changed)
        # Initialize checkbox state from settings
        self.toolbar.audio_is_spanish_checkbox.setChecked(self.settings.audio_is_spanish)
        main_layout.addWidget(self.toolbar)
        
        # Panels layout
        panels_layout = QHBoxLayout()
        panels_layout.setContentsMargins(0, 0, 0, 0)
        panels_layout.setSpacing(5)
        
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
        
        # Panel 4: Conversation Suggestions / Sugerencias
        from app.ui.panels.questions_panel import QuestionsPanel
        self.panel4 = QuestionsPanel("Participation Suggestions / Sugerencias", self.settings)
        splitter.addWidget(self.panel4)

        # Initialize verification translator (Capa 2 - final verification layer)
        from app.translate.verification_layer import RedundantVerificationTranslator
        self.verification_translator = RedundantVerificationTranslator()

        # Set equal sizes for panels
        splitter.setSizes([400, 400, 400, 400])
        
        panels_layout.addWidget(splitter)
        main_layout.addLayout(panels_layout)
        
        # Status bar with provider info
        self.statusBar().showMessage("Listo / Ready")
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
        # Capa 2: Verificación final - garantizar que solo texto en español llegue al panel
        verified_text = self.verification_translator.verify_and_ensure_spanish(
            event.translated_text
        )
        self.panel2.append_text(verified_text)
    
    def on_summary(self, event):
        """Handle summary event."""
        self.panel3.update_summary(event.summary)
    
    def on_questions(self, questions):
        """Handle questions event."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"MainWindow received {len(questions)} questions")
        
        self.panel4.clear_questions()
        if not questions:
            logger.warning("Received empty questions list")
            return
        
        for q in questions:
            logger.debug(f"Adding question: {q.question_es if hasattr(q, 'question_es') else q.question_en}")
            self.panel4.add_question(q.question_en, q.question_es)
        
        logger.info(f"Added {len(questions)} questions to panel")
    
    def update_status(self):
        """Update status bar with provider information."""
        if not self.controller.is_running:
            self.status_label.setText("Servicios no iniciados / Services not running")
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
        
        status_text = " | ".join(parts) if parts else "Ejecutando / Running"
        if self.controller.is_paused:
            status_text += " (PAUSADO / PAUSED)"
        self.status_label.setText(status_text)
    
    def _on_start(self):
        """Handle start button click."""
        async def start_async():
            try:
                await self.controller.start()
                self.toolbar.set_running(True)
                self.statusBar().showMessage("Servicios iniciados / Services started", 3000)
            except Exception as e:
                self.statusBar().showMessage(f"Error: {e}", 5000)
                QMessageBox.critical(
                    self,
                    "Error al Iniciar / Start Error",
                    f"No se pudieron iniciar los servicios:\nFailed to start services:\n\n{str(e)}"
                )
        
        asyncio.ensure_future(start_async())
    
    def _on_pause(self):
        """Handle pause button click."""
        async def pause_async():
            try:
                await self.controller.pause()
                self.toolbar.set_paused(True)
                self.statusBar().showMessage("Servicios pausados / Services paused", 3000)
            except Exception as e:
                self.statusBar().showMessage(f"Error: {e}", 5000)
        
        asyncio.ensure_future(pause_async())
    
    def _on_resume(self):
        """Handle resume button click."""
        async def resume_async():
            try:
                await self.controller.resume()
                self.toolbar.set_paused(False)
                self.statusBar().showMessage("Servicios reanudados / Services resumed", 3000)
            except Exception as e:
                self.statusBar().showMessage(f"Error: {e}", 5000)
        
        asyncio.ensure_future(resume_async())
    
    def _on_finalize(self):
        """Handle finalize button click."""
        reply = QMessageBox.question(
            self,
            "Finalizar Sesión / Finalize Session",
            "Esto detendrá todos los servicios y exportará la sesión.\nThis will stop all services and export the session.\n\n¿Continuar? / Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        async def finalize_async():
            try:
                folder_path = await self.controller.finalize_session()
                self.toolbar.set_running(False)
                self.toolbar.set_paused(False)
                
                QMessageBox.information(
                    self,
                    "Sesión Finalizada / Session Finalized",
                    f"Sesión exportada exitosamente a:\nSession exported successfully to:\n\n{folder_path}"
                )
                self.statusBar().showMessage("Sesión finalizada / Session finalized", 5000)
            except Exception as e:
                self.statusBar().showMessage(f"Error: {e}", 5000)
                QMessageBox.critical(
                    self,
                    "Error al Finalizar / Finalize Error",
                    f"No se pudo finalizar la sesión:\nFailed to finalize session:\n\n{str(e)}"
                )
        
        asyncio.ensure_future(finalize_async())
    
    def _on_clear(self):
        """Handle clear button click."""
        reply = QMessageBox.question(
            self,
            "Limpiar Sesión / Clear Session",
            "Esto limpiará todos los paneles y los datos de la sesión.\nThis will clear all panels and session data.\n\n¿Estás seguro? / Are you sure?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            self.controller.clear_session()
            self.clear_all_panels()
            self.statusBar().showMessage("Sesión limpiada / Session cleared", 3000)
        except Exception as e:
            self.statusBar().showMessage(f"Error: {e}", 5000)
            QMessageBox.critical(
                self,
                "Error al Limpiar / Clear Error",
                f"No se pudo limpiar la sesión:\nFailed to clear session:\n\n{str(e)}"
            )
    
    def clear_all_panels(self):
        """Clear all panels."""
        self.panel1.clear_text()
        self.panel2.clear_text()
        self.panel3.clear_text()
        self.panel4.clear_questions()
    
    def _on_audio_device(self):
        """Handle audio device selection button click."""
        dialog = AudioDeviceDialog(
            current_device_index=self.settings.audio_device_index,
            parent=self
        )
        
        if dialog.exec() == QDialog.Accepted:
            selected_index = dialog.get_selected_device_index()
            if selected_index is not None:
                # Update settings
                self.settings.audio_device_index = selected_index
                
                # Save to .env file
                self._save_audio_device_to_env(selected_index)
                
                # Show confirmation
                device_name = "Desconocido"
                for device in dialog.devices:
                    if device['index'] == selected_index:
                        device_name = device['name']
                        break
                
                self.statusBar().showMessage(
                    f"Dispositivo de audio seleccionado / Audio device selected: {device_name}",
                    5000
                )
                
                QMessageBox.information(
                    self,
                    "Dispositivo Seleccionado / Device Selected",
                    f"Dispositivo de audio configurado:\nAudio device configured:\n\n{device_name}\n\n"
                    "La configuración se aplicará la próxima vez que inicies la captura.\n"
                    "The configuration will be applied the next time you start capture."
                )
    
    def _on_audio_is_spanish_changed(self, is_spanish: bool):
        """Handle audio is Spanish checkbox change."""
        self.settings.audio_is_spanish = is_spanish
        
        # Save to .env file
        self._save_audio_is_spanish_to_env(is_spanish)
        
        # Show status message
        if is_spanish:
            self.statusBar().showMessage(
                "Modo español activado / Spanish mode activated: El audio será transcrito en español sin traducción / Audio will be transcribed in Spanish without translation",
                3000
            )
        else:
            self.statusBar().showMessage(
                "Modo inglés activado / English mode activated: El audio será transcrito en inglés y traducido al español / Audio will be transcribed in English and translated to Spanish",
                3000
            )
    
    def _save_audio_device_to_env(self, device_index: int):
        """Save audio device index to .env file."""
        from pathlib import Path
        from app.utils.paths import get_base_path
        base_path = get_base_path()
        env_path = base_path / ".env"
        
        # Read existing .env if it exists
        env_lines = []
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                env_lines = f.readlines()
        
        # Update or add AUDIO_DEVICE_INDEX
        found = False
        for i, line in enumerate(env_lines):
            if line.strip().startswith('AUDIO_DEVICE_INDEX='):
                env_lines[i] = f'AUDIO_DEVICE_INDEX={device_index}\n'
                found = True
                break
        
        if not found:
            env_lines.append(f'AUDIO_DEVICE_INDEX={device_index}\n')
        
        # Write back to .env
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(env_lines)
    
    def _save_audio_is_spanish_to_env(self, is_spanish: bool):
        """Save audio_is_spanish setting to .env file."""
        from pathlib import Path
        from app.utils.paths import get_base_path
        base_path = get_base_path()
        env_path = base_path / ".env"
        
        # Read existing .env if it exists
        env_lines = []
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                env_lines = f.readlines()
        
        # Update or add AUDIO_IS_SPANISH
        found = False
        for i, line in enumerate(env_lines):
            if line.strip().startswith('AUDIO_IS_SPANISH='):
                env_lines[i] = f'AUDIO_IS_SPANISH={"true" if is_spanish else "false"}\n'
                found = True
                break
        
        if not found:
            env_lines.append(f'AUDIO_IS_SPANISH={"true" if is_spanish else "false"}\n')
        
        # Write back to .env
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(env_lines)
    
    def closeEvent(self, event):
        """Handle window close event with confirmation."""
        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "Cerrar Aplicación / Close Application",
            "¿Estás seguro de que deseas cerrar la aplicación?\nAre you sure you want to close the application?\n\n"
            "Si hay una sesión activa, se detendrá.\nIf there is an active session, it will be stopped.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            event.ignore()
            return
        
        # Stop services if running
        import asyncio
        try:
            if self.controller.is_running:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.controller.stop())
        except Exception as e:
            print(f"Error stopping controller: {e}")
        
        event.accept()

