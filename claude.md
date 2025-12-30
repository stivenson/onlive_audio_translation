# Desktop Live Audio Translator - Claude Context

## Project Overview
Real-time system audio translation app for Windows/macOS. Captures loopback audio, transcribes with speaker detection, translates EN↔ES, generates summaries and conversation suggestions.

## Tech Stack
- **Language**: Python 3.10+
- **UI**: PySide6 (Qt)
- **Audio**: PyAudio, qasync for async event handling
- **Providers**:
  - STT: Deepgram (WebSocket streaming)
  - Translation: CTranslate2 (local, primary), DeepL, Hugging Face, OpenAI LLM (fallbacks)
  - LLM: OpenAI (summaries, questions)
- **Config**: pydantic-settings, python-dotenv

## Project Structure
```
app/
├── main.py              # Entry point
├── ui/                  # PySide6 GUI (main_window.py, panels/)
│   └── panels/          # transcription_panel, translation_panel, questions_panel
├── audio/               # Audio capture (vad.py for voice activity detection)
├── stt/                 # STT providers (base.py, deepgram_provider.py, speaker_mapper.py)
├── translate/           # Translation providers (base.py, service.py, llm_translate_provider.py)
├── llm/                 # LLM providers (base.py, openai_provider.py, questions_service.py, router.py)
├── core/                # event_bus.py, schemas.py, circuit_breaker.py, provider_router.py, retry_policy.py
├── config/              # settings.py - Pydantic BaseSettings for .env
└── storage/             # Persistence and export
```

## Key Commands
```powershell
# Run application (Windows)
.\run.ps1

# Run application (macOS/Linux)
./run.sh

# Install new package and update requirements.txt
.\install-package.ps1 <package-name>

# Build portable executable (Windows only)
.\build-executable.ps1

# Convert translation model to CTranslate2 format
python scripts/convert_model_to_ct2.py
```

## Code Conventions

### Architecture Patterns
- **Event-driven**: All components communicate via `EventBus` (publish/subscribe)
- **Provider pattern**: STT, Translation, LLM use base classes with router/circuit breaker
- **High availability**: Automatic failover between providers using circuit breaker pattern
- **Async/await**: Async operations for all I/O (audio, network, LLM calls)

### Naming Conventions
- Classes: PascalCase (e.g., `DeepgramProvider`, `EventBus`)
- Functions/methods: snake_case (e.g., `emit_event`, `process_audio`)
- Constants: UPPER_SNAKE_CASE (e.g., `DEFAULT_SAMPLE_RATE`)
- Private methods: prefix with `_` (e.g., `_handle_connection`)

### Code Style
- Follow PEP 8
- Type hints required for all function signatures
- Pydantic models for all data schemas (see `app/core/schemas.py`)
- Docstrings for complex functions only (avoid obvious documentation)

### Error Handling
- Use circuit breaker for provider failures (see `app/core/circuit_breaker.py`)
- Retry policy with exponential backoff for transient failures
- Always log errors with context using standard logging module

## Configuration
- All settings in `.env` file (see `env.example`)
- Loaded via `app/config/settings.py` (Pydantic BaseSettings)
- Environment variables override defaults
- Models configurable per service: `TRANSLATION_MODEL_FALLBACK`, `SUMMARY_MODEL`, `QUESTIONS_MODEL`

## Do Not Touch
- `.venv/` - Virtual environment files
- `dist/` - Build artifacts (if exists)
- `models/opus-mt-en-es-ct2/` - Pre-converted CTranslate2 model (if exists)
- Audio device detection logic in `app/audio/` - fragile, platform-specific

## Important Notes
- Always activate virtual environment before running (run scripts do this automatically)
- Windows: Requires Stereo Mix enabled for loopback audio capture
- macOS: Requires BlackHole for loopback audio
- Translation provider chain: CTranslate2 → DeepL → Hugging Face → LLM fallback
- UI updates must use Qt signals/slots, never direct modification from worker threads
- Event bus is thread-safe but subscribers must handle async context properly

## Testing
- No formal test suite currently
- Manual testing via UI
- Provider failover can be tested by disabling API keys in `.env`

## Git Workflow
- Main branch: `main`
- Commit messages: Imperative mood, concise (e.g., "Add dark mode", "Fix audio buffer overflow")
- Include GitHub co-author footer when applicable
