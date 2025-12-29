# Desktop Live Audio Translator

Python desktop application for real-time system audio translation and analysis, with support for Windows 11 and macOS.

## Features

- **System audio capture**: Captures audio passing through your sound card (loopback)
- **Real-time transcription**: With automatic language detection and diarization (multiple speakers)
- **Automatic translation**: Translates from English to Spanish (or keeps Spanish if already in Spanish)
- **Automatic role assignment**: Detects multiple speakers and assigns User_1, User_2, etc.
- **Contextual summary**: Generates a live summary of the conversation with accumulated context
- **Question suggestions**: Generates relevant questions/replies in English and Spanish
- **High availability**: Redundant system with automatic failover between multiple providers

## Requirements

- Python 3.10 or higher
- Windows 11 or macOS
- **For Windows**: You need to enable "Stereo Mix" or a loopback device to capture system audio (see instructions below)
- **For macOS**: You need to install [BlackHole](https://github.com/ExistentialAudio/BlackHole) for system audio capture

### Audio Setup on Windows

To capture system audio on Windows, you need to enable "Stereo Mix". You have two options:

#### Option 1: Automated Script (Recommended)

The project includes a PowerShell script that automatically enables Stereo Mix:

```powershell
.\enable-stereo-mix.ps1
```

This script will:
- Automatically request administrator permissions if needed
- Search for disabled audio devices
- Enable "Stereo Mix" if found
- Guide you through the process if manual intervention is needed

**Note**: The script requires administrator privileges. It will automatically prompt for elevation if needed.

#### Option 2: Manual Setup

If you prefer to enable it manually:

1. **Right-click the volume icon** in the taskbar
2. Select **"Sounds"** or **"Sound settings"**
3. Go to the **"Recording"** tab
4. **Right-click in empty space** and check **"Show disabled devices"**
5. Find **"Stereo Mix"** or **"Mezcla estéreo"**
6. **Right-click** on "Stereo Mix" and select **"Enable"**
7. **Right-click** again and select **"Set as default device"**

**Note**: If you don't see "Stereo Mix", your sound card may not support it. In that case, you can use software like [VB-Audio Virtual Cable](https://vb-audio.com/Cable/) to create a virtual loopback device.

The application will automatically detect and use Stereo Mix when available.

## Installation

1. Clone the repository:
```bash
git clone <repo-url>
cd traducción_on_live_audio
```

2. Create a virtual environment:
```bash
python -m venv .venv
```

3. Activate the virtual environment and install dependencies:

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS/Linux:**
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

## Configuration

Edit the `.env` file with your API credentials:

- **STT Providers**: Deepgram
- **LLM Providers**: OpenAI
- **Translation Providers**: CTranslate2 (local, recommended), DeepL, Hugging Face, OpenAI LLM (fallback)

The application uses CTranslate2 as the primary translation provider (local, fast, free) with DeepL, Hugging Face, and OpenAI as fallbacks. If one provider fails, it automatically switches to the next.

### Fast Local Translation Setup

For the best performance, set up CTranslate2 for ultra-fast local translation:

1. See [TRANSLATION_SETUP.md](TRANSLATION_SETUP.md) for detailed instructions
2. Quick setup:
   ```bash
   pip install ctranslate2 sentencepiece deepl
   python scripts/convert_model_to_ct2.py
   ```
3. Configure in `.env`:
   ```env
   TRANSLATE_PROVIDER_CHAIN=ctranslate2,deepl,huggingface,llm
   CTRANSLATE2_MODEL_PATH=models/opus-mt-en-es-ct2
   DEEPL_API_KEY=  # Optional, free tier available
   ```

### Hugging Face Translation Configuration

To use Hugging Face as a translation provider (fallback option):

1. Get your Hugging Face API token: https://huggingface.co/settings/tokens
2. Configure in `.env`:
   ```env
   HF_API_TOKEN=your_token_here
   HF_TRANSLATION_MODEL=Helsinki-NLP/opus-mt-en-es
   TRANSLATE_PROVIDER_CHAIN=ctranslate2,deepl,huggingface,llm
   ```

The default model `Helsinki-NLP/opus-mt-en-es` is optimized for English→Spanish translation. You can change the model according to your needs.

### Models by Service

Each service can use a different AI model:

- **`TRANSLATION_MODEL_FALLBACK`**: Model used for translating transcripts when LLM is used as fallback (default: `gpt-4o`)
- **`SUMMARY_MODEL`**: Model used for generating conversation summaries (default: `gpt-4o`)
- **`QUESTIONS_MODEL`**: Model used for generating relevant questions/replies (default: `gpt-4o`)

Example configuration:
```env
TRANSLATION_MODEL_FALLBACK=gpt-4o
SUMMARY_MODEL=gpt-4o-mini
QUESTIONS_MODEL=gpt-4o
```

This allows you to optimize costs by using cheaper models for simple tasks (like translation) and more powerful models for complex analysis (like summaries and questions).

## Usage

### Windows (PowerShell)

**Recommended - Use the run script:**
```powershell
.\run.ps1
```

This script automatically:
- Activates the virtual environment (`.venv`)
- Verifies you're using the correct Python
- Runs the application

**Alternative - Manual execution:**
```powershell
# 1. Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Run the application
python -m app.main
```

**Note about PowerShell permissions:**
If you encounter an execution policy error, run:
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### macOS/Linux

**Recommended - Use the run script:**
```bash
# Give execution permissions (first time only)
chmod +x run.sh

# Run the application
./run.sh
```

**Alternative - Manual execution:**
```bash
# 1. Activate the virtual environment
source .venv/bin/activate

# 2. Run the application
python -m app.main
```

**IMPORTANT**: 
- You must always activate the virtual environment before running the application, otherwise providers won't initialize correctly.
- The `run.ps1` script (Windows) or `run.sh` script (macOS/Linux) does this automatically for you.

### Installing Additional Packages

If you need to install an additional package and update `requirements.txt`:

**Windows:**
```powershell
.\install-package.ps1 <package-name>
```

**Example:**
```powershell
.\install-package.ps1 requests
```

This script automatically:
- Activates the virtual environment
- Installs the package
- Updates `requirements.txt` with the exact installed version

## Project Structure

```
app/
├── main.py              # Entry point
├── ui/                  # Graphical interface (PySide6)
├── audio/               # Audio capture
├── stt/                 # STT providers and router
├── translate/           # Translation providers and router
├── llm/                 # LLM providers and router
├── core/                # Event bus, memory, schemas, circuit breaker
├── config/              # Configuration and .env loading
└── storage/             # Persistence and export
```

## License

MIT
