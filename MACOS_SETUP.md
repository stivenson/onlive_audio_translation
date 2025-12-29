# macOS Audio Setup Guide

This guide explains how to set up audio loopback on macOS for the Live Audio Translator application.

## Why is this needed?

macOS doesn't natively support capturing system audio (what you hear) like Windows does. We need a virtual audio device to route system audio so the application can capture it.

## Step 1: Install BlackHole

BlackHole is a virtual audio driver for macOS that allows routing audio between applications.

### Option A: Using Homebrew (Recommended)

```bash
brew install blackhole-2ch
```

### Option B: Manual Installation

1. Download from: https://github.com/ExistentialAudio/BlackHole/releases
2. Download the version for your macOS version
3. Open the `.pkg` file and follow the installation instructions
4. Restart your Mac if prompted

## Step 2: Create Multi-Output Device

To hear audio while also capturing it, create a Multi-Output Device:

1. Open **Audio MIDI Setup** (Applications → Utilities → Audio MIDI Setup)
2. Click the **"+"** button at the bottom left
3. Select **"Create Multi-Output Device"**
4. In the right panel, check:
   - Your speakers/headphones (e.g., "Built-in Output")
   - **BlackHole 2ch**
5. Right-click the Multi-Output Device → **"Use This Device For Sound Output"**

## Step 3: Configure Application

1. Launch the Live Audio Translator application
2. The application should automatically detect BlackHole
3. If not, go to Settings and select "BlackHole 2ch" as the input device

## Step 4: Test

1. Play some audio (YouTube, music, etc.)
2. You should see transcription appearing in the application
3. If not, check:
   - Audio MIDI Setup shows BlackHole is receiving audio
   - Application settings show correct input device
   - System audio is playing through the Multi-Output Device

## Troubleshooting

### No audio detected

- Verify BlackHole is installed: `ls /Library/Audio/Plug-Ins/HAL/BlackHole.driver`
- Restart your Mac after installing BlackHole
- Check Audio MIDI Setup that Multi-Output Device includes BlackHole

### Can't hear audio

- Ensure your speakers/headphones are also checked in the Multi-Output Device
- Try adjusting volume in Audio MIDI Setup for each device

### Application crashes

- Check console logs: `Console.app` → Search for "LiveAudioTranslator"
- Verify all dependencies are installed
- Try reinstalling BlackHole

## Alternative: Soundflower

If BlackHole doesn't work, you can try Soundflower (older, less maintained):

```bash
brew install soundflower
```

However, BlackHole is recommended as it's actively maintained and more reliable.

## Uninstalling

To remove BlackHole:

```bash
sudo rm -rf /Library/Audio/Plug-Ins/HAL/BlackHole.driver
```

Then restart your Mac.

