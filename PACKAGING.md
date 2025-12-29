# Packaging Guide

This guide explains how to package the Desktop Live Audio Translator application for Windows and macOS.

## Prerequisites

- Python 3.10 or higher
- PyInstaller (for packaging)
- All dependencies installed

## Installation

```bash
pip install pyinstaller
```

## Windows Packaging

### Create Executable

```bash
pyinstaller --name="LiveAudioTranslator" \
    --windowed \
    --onefile \
    --icon=icon.ico \
    --add-data=".env.example;." \
    app/main.py
```

### Create Installer (Optional)

Use Inno Setup or NSIS to create an installer from the executable.

## macOS Packaging

### Prerequisites for macOS

1. Install BlackHole (required for audio loopback):
   ```bash
   brew install blackhole-2ch
   ```

2. Or download from: https://github.com/ExistentialAudio/BlackHole

### Create Application Bundle

```bash
pyinstaller --name="LiveAudioTranslator" \
    --windowed \
    --onedir \
    --icon=icon.icns \
    --add-data=".env.example:." \
    app/main.py
```

### Create DMG (Optional)

Use `create-dmg` or similar tools to create a DMG file:

```bash
npm install -g create-dmg
create-dmg LiveAudioTranslator.app LiveAudioTranslator.dmg
```

## Audio Setup Instructions

### Windows

1. Enable "Stereo Mix" in Windows Sound settings:
   - Right-click sound icon → Sounds
   - Recording tab → Right-click → Show Disabled Devices
   - Enable "Stereo Mix"
   - Set as default recording device

### macOS

1. Install BlackHole:
   ```bash
   brew install blackhole-2ch
   ```

2. Create Multi-Output Device:
   - Open Audio MIDI Setup
   - Click "+" → Create Multi-Output Device
   - Check both your speakers/headphones AND BlackHole
   - Set as default output

3. In the application, select BlackHole as the input device

## Distribution

Include the following files in your distribution:

- Executable/Application bundle
- `.env.example` file
- `README.md`
- `PACKAGING.md` (this file)
- Audio setup instructions

## Troubleshooting

### Audio Not Capturing

- **Windows**: Ensure Stereo Mix is enabled and set as default recording device
- **macOS**: Verify BlackHole is installed and selected in the app

### Missing Dependencies

If the packaged app fails to run, you may need to:

1. Include all required DLLs/dylibs
2. Use `--collect-all` flag in PyInstaller for specific packages
3. Test on a clean system without Python installed

### Code Signing (macOS)

For distribution outside the App Store, you may need to code sign:

```bash
codesign --deep --force --verify --verbose --sign "Developer ID Application: Your Name" LiveAudioTranslator.app
```

