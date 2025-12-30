"""Main entry point for the Desktop Live Audio Translator application."""

import sys
import asyncio
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QTimer, qInstallMessageHandler
import qasync

from app.config.settings import load_settings
from app.ui.main_window import MainWindow
from app.ui.controller import AppController
from app.core.diagnostics import run_full_diagnostic
from app.ui.diagnostic_dialog import DiagnosticDialog


_previous_qt_message_handler = None


def qt_message_handler(msg_type, context, message):
    """Filter out Qt timer warnings from other threads."""
    # Suppress "QObject::startTimer: Timers cannot be started from another thread" warnings
    # These are harmless warnings from Deepgram's internal threads
    if "startTimer" in message and "another thread" in message:
        return  # Suppress this specific warning
    # Forward everything else to the previous handler (default behavior)
    global _previous_qt_message_handler
    if _previous_qt_message_handler and _previous_qt_message_handler is not qt_message_handler:
        _previous_qt_message_handler(msg_type, context, message)
        return

    # Fallback: print to stderr
    try:
        sys.stderr.write(message + "\n")
    except Exception:
        pass


from app.utils.paths import get_base_path


def setup_logging():
    """Configure logging for the application."""
    base_path = get_base_path()
    log_dir = base_path / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Configure file handler with rotation
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        str(log_dir / "app.log"),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=3
    )
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            file_handler,
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Install Qt message handler to suppress timer warnings from Deepgram threads
    global _previous_qt_message_handler
    _previous_qt_message_handler = qInstallMessageHandler(qt_message_handler)


async def main_async():
    """Async main function."""
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        settings = load_settings()
        logger.info("Configuration loaded successfully")
        
        # Create controller
        controller = AppController(settings)
        
        # Start services
        await controller.start()
        logger.info("Services started successfully")
        
        return controller
        
    except Exception as e:
        logger.error(f"Failed to start services: {e}", exc_info=True)
        raise


def main():
    """Main application entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Create Qt application
        app = QApplication(sys.argv)
        app.setApplicationName("Live Audio Translator")
        app.setOrganizationName("Personal")
        
        # Setup async event loop
        loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(loop)
        
        # Load settings
        settings = load_settings()
        logger.info("Configuration loaded successfully")
        
        # Run diagnostic check
        diagnostic_report = run_full_diagnostic(settings)
        
        # Show diagnostic dialog if there are issues
        if diagnostic_report.has_errors() or diagnostic_report.has_warnings():
            dialog = DiagnosticDialog(diagnostic_report)
            dialog.exec()
        
        # Create controller
        controller = AppController(settings)
        
        # Create and show main window
        window = MainWindow(settings, controller)
        window.show()
        
        # Note: Services will start when user clicks "Start" button
        # Removed auto-start to allow user control
        
        logger.info("Application started successfully")
        
        # Run event loop
        with loop:
            sys.exit(loop.run_forever())
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

