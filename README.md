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
git clone git@github.com:stivenson/onlive_audio_translation.git
cd onlive_audio_translation
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

## Creating a Portable Executable (Windows 11) - Optional

This section explains how to create a standalone executable that doesn't require Python installation. **This is only for Windows 11.**

### Prerequisites

- Windows 11
- Python 3.10 or higher installed (only needed for building, not for running the executable)
- All dependencies installed in your virtual environment

### Creating the Executable

1. **Ensure your virtual environment is activated and all dependencies are installed:**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. **Run the build script:**
   ```powershell
   .\build-executable.ps1
   ```

   This will create a single executable file `LiveAudioTranslator.exe` in the `dist/` folder.

3. **Wait for the build to complete** (this may take several minutes)

4. **The executable will be located at:**
   ```
   dist\LiveAudioTranslator.exe
   ```

### Using the Portable Executable

1. **Copy the executable to your desired location:**
   - Copy `dist\LiveAudioTranslator.exe` to wherever you want to use it
   - Copy `.env.example` to the same location

2. **Configure the application:**
   ```powershell
   # Copy the example config file
   copy .env.example .env
   
   # Edit .env with your API keys (use Notepad or any text editor)
   notepad .env
   ```

3. **Run the executable:**
   ```powershell
   .\LiveAudioTranslator.exe
   ```

   The executable is fully portable and doesn't require Python or any dependencies to be installed.

### Optional: Including Local Translation Models

If you want to include CTranslate2 models for offline translation:

1. **Before building, generate the model:**
   ```powershell
   python scripts/convert_model_to_ct2.py
   ```

2. **The build script will automatically include the models**

3. **After building, copy the models folder alongside the executable:**
   ```
   YourFolder/
   ├── LiveAudioTranslator.exe
   ├── .env
   └── models/
       └── opus-mt-en-es-ct2/
   ```

### Distribution

To distribute the application:

1. **Create a folder with:**
   - `LiveAudioTranslator.exe`
   - `.env.example` (users will copy this to `.env` and configure it)
   - `README.md` (optional, for instructions)
   - `models/` folder (optional, if using local translation)

2. **Users only need to:**
   - Copy `.env.example` to `.env`
   - Edit `.env` with their API keys
   - Run `LiveAudioTranslator.exe`

**Note:** The executable is large (~200-300 MB) because it includes all dependencies. This is normal for PyInstaller executables.

For more detailed information, see [BUILD_GUIDE.md](BUILD_GUIDE.md).

## License

MIT
