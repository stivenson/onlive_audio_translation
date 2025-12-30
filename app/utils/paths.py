"""Utility functions for portable path handling."""

import sys
from pathlib import Path


def get_base_path() -> Path:
    """
    Get the base path for the application.
    
    When running as a PyInstaller executable, returns the directory containing the executable.
    When running as a Python script, returns the current working directory or project root.
    
    Returns:
        Path object pointing to the base directory
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable (PyInstaller)
        # sys.executable is the path to the .exe file
        return Path(sys.executable).parent
    else:
        # Running as Python script
        # Use current working directory, but try to find project root
        cwd = Path.cwd()
        # If we're in the project root, use it
        if (cwd / "app").exists() or (cwd / ".env.example").exists():
            return cwd
        # Otherwise, try to find project root by going up
        current = cwd
        for _ in range(5):  # Max 5 levels up
            if (current / "app").exists() or (current / ".env.example").exists():
                return current
            parent = current.parent
            if parent == current:  # Reached filesystem root
                break
            current = parent
        # Fallback to current directory
        return cwd

