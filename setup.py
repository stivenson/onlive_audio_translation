"""Setup script for Desktop Live Audio Translator."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="live-audio-translator",
    version="0.1.0",
    description="Desktop application for real-time audio translation and analysis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/traduccion_on_live_audio",
    packages=find_packages(),
    install_requires=[
        "PySide6>=6.6.0",
        "qasync>=0.27.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
        "pyaudio>=0.2.14",
        "numpy>=1.24.0",
        "deepgram-sdk>=3.2.0",
        "openai>=1.12.0",
        "websockets>=12.0",
        "aiohttp>=3.9.0",
        "tenacity>=8.2.0",
    ],
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "live-audio-translator=app.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)

