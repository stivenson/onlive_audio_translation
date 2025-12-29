"""Diagnostic dialog for displaying issues and solutions."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QScrollArea, QWidget, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette

from app.core.diagnostics import DiagnosticReport, DiagnosticIssue


class DiagnosticDialog(QDialog):
    """Dialog for displaying diagnostic issues and solutions."""
    
    def __init__(self, report: DiagnosticReport, parent=None):
        """
        Initialize diagnostic dialog.
        
        Args:
            report: Diagnostic report to display
            parent: Parent widget
        """
        super().__init__(parent)
        self.report = report
        self.init_ui()
    
    def init_ui(self):
        """Initialize the dialog UI."""
        self.setWindowTitle("Diagnostic Report")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("System Diagnostic Report")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Python environment info
        env_info = QLabel(f"Python: {self.report.python_path}")
        if self.report.is_venv:
            env_info.setText(f"Python: {self.report.python_path} (Virtual Environment: {self.report.venv_path})")
            env_info.setStyleSheet("color: green;")
        else:
            env_info.setStyleSheet("color: orange;")
        layout.addWidget(env_info)
        
        # Issues area
        if self.report.issues:
            issues_label = QLabel("Issues Found:")
            issues_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            layout.addWidget(issues_label)
            
            # Scrollable area for issues
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setMinimumHeight(300)
            
            issues_widget = QWidget()
            issues_layout = QVBoxLayout(issues_widget)
            issues_layout.setContentsMargins(5, 5, 5, 5)
            
            for issue in self.report.issues:
                issue_widget = self._create_issue_widget(issue)
                issues_layout.addWidget(issue_widget)
            
            issues_layout.addStretch()
            scroll.setWidget(issues_widget)
            layout.addWidget(scroll)
        else:
            no_issues = QLabel("✓ No issues found. System is ready!")
            no_issues.setStyleSheet("color: green; font-size: 14px; padding: 20px;")
            no_issues.setAlignment(Qt.AlignCenter)
            layout.addWidget(no_issues)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Copy command button (only if there are commands to copy)
        commands = [issue.command for issue in self.report.issues if issue.command]
        if commands:
            copy_btn = QPushButton("Copy Commands")
            copy_btn.clicked.connect(lambda: self._copy_commands(commands))
            button_layout.addWidget(copy_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_issue_widget(self, issue: DiagnosticIssue) -> QWidget:
        """Create a widget for displaying an issue."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Severity color
        if issue.severity == "error":
            bg_color = "#3d1a1a"
            border_color = "#ff4444"
            severity_text = "ERROR"
        elif issue.severity == "warning":
            bg_color = "#3d3d1a"
            border_color = "#ffaa44"
            severity_text = "WARNING"
        else:
            bg_color = "#1a1a3d"
            border_color = "#4444ff"
            severity_text = "INFO"
        
        widget.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 5px;
                padding: 5px;
            }}
        """)
        
        # Severity and category
        header = QLabel(f"[{severity_text}] {issue.category.upper()}")
        header.setStyleSheet("font-weight: bold; color: white;")
        layout.addWidget(header)
        
        # Message
        message = QLabel(issue.message)
        message.setStyleSheet("color: #cccccc; margin-top: 5px;")
        message.setWordWrap(True)
        layout.addWidget(message)
        
        # Solution
        solution = QLabel(f"Solution: {issue.solution}")
        solution.setStyleSheet("color: #aaccff; margin-top: 5px;")
        solution.setWordWrap(True)
        layout.addWidget(solution)
        
        # Command (if available)
        if issue.command:
            command_text = QTextEdit()
            command_text.setPlainText(issue.command)
            command_text.setReadOnly(True)
            command_text.setMaximumHeight(50)
            command_text.setStyleSheet("background-color: #2a2a2a; color: #00ff00; font-family: monospace;")
            layout.addWidget(command_text)
        
        return widget
    
    def _copy_commands(self, commands: list):
        """Copy commands to clipboard."""
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        text = "\n".join(commands)
        clipboard.setText(text)
        
        QMessageBox.information(
            self,
            "Commands Copied",
            f"Copied {len(commands)} command(s) to clipboard.\n\n"
            "Paste them in your terminal to fix the issues."
        )

