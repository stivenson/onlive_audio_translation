"""Main entry point for the Desktop Live Audio Translator application."""

import sys
import asyncio
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer
import qasync

from app.config.settings import load_settings
from app.ui.main_window import MainWindow
from app.ui.controller import AppController


def setup_logging():
    """Configure logging for the application."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "app.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )


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
        
        # Create controller
        controller = AppController(settings)
        
        # Create and show main window
        window = MainWindow(settings, controller)
        window.show()
        
        # Start services in background
        async def start_services():
            try:
                await controller.start()
                logger.info("Services started successfully")
            except Exception as e:
                logger.error(f"Failed to start services: {e}", exc_info=True)
                window.statusBar().showMessage(f"Error: {e}")
        
        asyncio.ensure_future(start_services())
        
        logger.info("Application started successfully")
        
        # Run event loop
        with loop:
            sys.exit(loop.run_forever())
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

