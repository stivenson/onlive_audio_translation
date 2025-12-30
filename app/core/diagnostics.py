"""Diagnostic utilities for checking environment and dependencies."""

import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class DiagnosticIssue:
    """Represents a diagnostic issue."""
    
    def __init__(self, severity: str, category: str, message: str, solution: str, command: Optional[str] = None):
        """
        Initialize diagnostic issue.
        
        Args:
            severity: "error", "warning", or "info"
            category: Category of issue (e.g., "environment", "dependency", "api_key")
            message: Description of the issue
            solution: Suggested solution
            command: Optional command to fix the issue
        """
        self.severity = severity
        self.category = category
        self.message = message
        self.solution = solution
        self.command = command


class DiagnosticReport:
    """Report containing all diagnostic results."""
    
    def __init__(self):
        """Initialize diagnostic report."""
        self.issues: List[DiagnosticIssue] = []
        self.python_path = sys.executable
        self.is_venv = False
        self.venv_path: Optional[str] = None
        
    def has_errors(self) -> bool:
        """Check if report has any errors."""
        return any(issue.severity == "error" for issue in self.issues)
    
    def has_warnings(self) -> bool:
        """Check if report has any warnings."""
        return any(issue.severity == "warning" for issue in self.issues)
    
    def get_errors(self) -> List[DiagnosticIssue]:
        """Get all error issues."""
        return [issue for issue in self.issues if issue.severity == "error"]
    
    def get_warnings(self) -> List[DiagnosticIssue]:
        """Get all warning issues."""
        return [issue for issue in self.issues if issue.severity == "warning"]


def check_python_environment(report: DiagnosticReport) -> None:
    """
    Check Python environment and virtual environment status.
    
    Args:
        report: Diagnostic report to update
    """
    # Skip environment checks if running as PyInstaller executable
    if getattr(sys, 'frozen', False):
        # Running as compiled executable - no need to check environment
        report.python_path = sys.executable
        report.is_venv = False  # Not applicable for executables
        logger.info("Running as compiled executable - skipping environment checks")
        return
    
    python_path = sys.executable
    report.python_path = python_path
    
    # Check if running in virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    report.is_venv = in_venv
    
    if in_venv:
        report.venv_path = sys.prefix
        logger.info(f"Running in virtual environment: {sys.prefix}")
    else:
        # Check if .venv exists in project
        project_root = Path.cwd()
        venv_path = project_root / ".venv"
        
        if venv_path.exists():
            venv_python = venv_path / "Scripts" / "python.exe" if os.name == "nt" else venv_path / "bin" / "python"
            
            if venv_python.exists():
                report.issues.append(DiagnosticIssue(
                    severity="error",
                    category="environment",
                    message=f"Not using virtual environment. Current Python: {python_path}",
                    solution="Activate the virtual environment before running the application.",
                    command=f".venv\\Scripts\\activate" if os.name == "nt" else "source .venv/bin/activate"
                ))
            else:
                report.issues.append(DiagnosticIssue(
                    severity="warning",
                    category="environment",
                    message="Virtual environment directory exists but Python executable not found.",
                    solution="Recreate the virtual environment: python -m venv .venv",
                    command="python -m venv .venv"
                ))
        else:
            report.issues.append(DiagnosticIssue(
                severity="warning",
                category="environment",
                message="No virtual environment found in project directory.",
                solution="Create a virtual environment: python -m venv .venv",
                command="python -m venv .venv"
            ))


def check_dependencies(report: DiagnosticReport) -> None:
    """
    Check if required dependencies are installed.
    
    Args:
        report: Diagnostic report to update
    """
    # Skip dependency checks if running as PyInstaller executable
    # All dependencies are bundled in the executable
    if getattr(sys, 'frozen', False):
        logger.info("Running as compiled executable - skipping dependency checks (all bundled)")
        return
    
    required_packages = {
        "deepgram": "deepgram-sdk",
        "openai": "openai",
        "huggingface": "huggingface-hub",
        "pyaudio": "pyaudio",
        "PySide6": "PySide6",
        "qasync": "qasync"
    }
    
    missing_packages = []
    
    for module_name, package_name in required_packages.items():
        try:
            if module_name == "deepgram":
                import deepgram
            elif module_name == "openai":
                import openai
            elif module_name == "huggingface":
                import huggingface_hub
            elif module_name == "pyaudio":
                import pyaudio
            elif module_name == "PySide6":
                import PySide6
            elif module_name == "qasync":
                import qasync
        except ImportError:
            missing_packages.append(package_name)
            report.issues.append(DiagnosticIssue(
                severity="error",
                category="dependency",
                message=f"Package '{package_name}' is not installed or not accessible.",
                solution=f"Install the package: pip install {package_name}",
                command=f"pip install {package_name}"
            ))
    
    if missing_packages:
        # Add a combined install command
        install_all = "pip install " + " ".join(missing_packages)
        report.issues.append(DiagnosticIssue(
            severity="info",
            category="dependency",
            message=f"Install all missing packages at once",
            solution="Run the following command to install all missing packages:",
            command=install_all
        ))


def check_api_keys(settings) -> DiagnosticReport:
    """
    Check if required API keys are configured.
    
    Args:
        settings: Application settings object
        
    Returns:
        Diagnostic report with API key issues
    """
    report = DiagnosticReport()
    
    # Check STT provider keys
    if "deepgram" in settings.stt_provider_chain:
        if not settings.deepgram_api_key or settings.deepgram_api_key == "your_deepgram_api_key_here":
            report.issues.append(DiagnosticIssue(
                severity="error",
                category="api_key",
                message="Deepgram API key is not configured.",
                solution="Set DEEPGRAM_API_KEY in your .env file.",
                command=None
            ))
    
    # Check LLM provider keys
    if "openai" in settings.llm_provider_chain:
        if not settings.openai_api_key or settings.openai_api_key == "your_openai_api_key_here":
            report.issues.append(DiagnosticIssue(
                severity="error",
                category="api_key",
                message="OpenAI API key is not configured.",
                solution="Set OPENAI_API_KEY in your .env file.",
                command=None
            ))
    
    # Check translation provider keys
    if "huggingface" in settings.translate_provider_chain:
        if not settings.hf_api_token or settings.hf_api_token == "your_huggingface_api_token_here":
            report.issues.append(DiagnosticIssue(
                severity="warning",
                category="api_key",
                message="Hugging Face API token is not configured (optional but recommended).",
                solution="Set HF_API_TOKEN in your .env file for better performance.",
                command=None
            ))
    
    return report


def run_full_diagnostic(settings) -> DiagnosticReport:
    """
    Run complete diagnostic check.
    
    Args:
        settings: Application settings object
        
    Returns:
        Complete diagnostic report
    """
    report = DiagnosticReport()
    
    # Check Python environment
    check_python_environment(report)
    
    # Check dependencies
    check_dependencies(report)
    
    # Check API keys
    api_key_report = check_api_keys(settings)
    report.issues.extend(api_key_report.issues)
    
    return report

