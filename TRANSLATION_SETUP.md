# Fast Local Translation Setup Guide

This guide will help you set up the new fast translation providers (CTranslate2 and DeepL) for your application.

## Overview

The new translation system offers:
- **CTranslate2**: Ultra-fast local translation (50-200ms latency, 100% offline, free)
- **DeepL**: High-quality cloud translation (100-200ms latency, 500K chars/month free)
- **Hugging Face + LLM**: Existing fallback providers

## Quick Start

### Step 1: Install New Dependencies

```bash
# Activate your virtual environment
.venv\Scripts\activate

# Install new packages
pip install ctranslate2 sentencepiece deepl
```

### Step 2: Convert Translation Model to CTranslate2

Run the conversion script to create the local fast model:

```bash
# Convert the OPUS-MT English-Spanish model
python scripts/convert_model_to_ct2.py

# This will create: models/opus-mt-en-es-ct2/
# Model size: ~150MB (int8 quantized)
# First run will download the model from Hugging Face
```

**Alternative models** (for better quality):

```bash
# NLLB-600M (better quality, larger size ~600MB)
python scripts/convert_model_to_ct2.py \
    --model facebook/nllb-200-distilled-600M \
    --output models/nllb-600M-ct2

# NLLB-1.3B (best quality, ~1.3GB)
python scripts/convert_model_to_ct2.py \
    --model facebook/nllb-200-1.3B \
    --output models/nllb-1.3B-ct2
```

### Step 3: Configure .env

Update your `.env` file:

```ini
# Translation Provider Chain
# CTranslate2 (local) is tried first, then DeepL (if configured), then fallbacks
TRANSLATE_PROVIDER_CHAIN=ctranslate2,deepl,huggingface,llm

# CTranslate2 Model Path
CTRANSLATE2_MODEL_PATH=models/opus-mt-en-es-ct2

# DeepL API Key (optional - get free at https://www.deepl.com/pro-api)
# 500,000 characters/month free tier available
# Leave empty to skip DeepL
DEEPL_API_KEY=

# Existing providers (fallbacks)
HF_API_TOKEN=your_hf_token
OPENAI_API_KEY=your_openai_key
```

### Step 4: Test It!

Run your application:

```bash
.\run.ps1
```

The application will now:
1. **Try CTranslate2 first** (local, super fast)
2. **Fall back to DeepL** if CTranslate2 fails (if API key configured)
3. **Fall back to Hugging Face** if DeepL fails
4. **Fall back to OpenAI GPT-4o** as last resort

## Performance Comparison

| Provider | Latency | Quality | Cost | Offline |
|----------|---------|---------|------|---------|
| **CTranslate2** | 50-200ms | ⭐⭐⭐⭐ | $0 | ✅ |
| **DeepL** | 100-200ms | ⭐⭐⭐⭐⭐ | Free tier | ❌ |
| **Hugging Face** | 500-1000ms | ⭐⭐⭐⭐ | Free | ❌ |
| **OpenAI GPT-4o** | 1000-2000ms | ⭐⭐⭐⭐⭐ | $0.15/1M tokens | ❌ |

## Expected Speed Improvement

**Before** (Hugging Face API):
- Average latency: ~800ms per translation
- Depends on internet connection

**After** (CTranslate2 local):
- Average latency: ~100ms per translation
- **~8x faster!**
- No internet dependency
- Consistent performance

## DeepL Free API Setup (Optional)

1. Go to https://www.deepl.com/pro-api
2. Sign up for a free account
3. Get your API key (500,000 characters/month free)
4. Add to `.env`: `DEEPL_API_KEY=your_key_here`

## Troubleshooting

### CTranslate2 model not found

```
Error: CTranslate2 model not found at models/opus-mt-en-es-ct2
```

**Solution**: Run the conversion script:
```bash
python scripts/convert_model_to_ct2.py
```

### Import error: ctranslate2 not installed

```
Error: ctranslate2 and sentencepiece not installed
```

**Solution**: Install dependencies:
```bash
pip install ctranslate2 sentencepiece
```

### Model conversion failed

If the conversion fails, ensure you have:
- Internet connection (to download the model)
- Enough disk space (~500MB)
- Updated transformers: `pip install --upgrade transformers`

### DeepL authentication failed

```
Error: DeepL API authentication failed
```

**Solution**: Check your API key in `.env` is correct and active.

## Using GPU (Optional, for even faster translation)

If you have an NVIDIA GPU with CUDA:

1. Install CUDA-enabled CTranslate2:
```bash
pip install ctranslate2-cuda
```

2. The provider will automatically use GPU if available

3. Expected speed: ~20-50ms per translation (2-4x faster than CPU)

## Monitoring Translation Performance

Check the logs to see which provider is being used:

```
INFO: Initialized translation provider: ctranslate2
INFO: CTranslate2 provider initialized successfully
INFO: Translation completed in 87ms using ctranslate2
```

## Next Steps

1. ✅ Install dependencies: `pip install ctranslate2 sentencepiece deepl`
2. ✅ Convert model: `python scripts/convert_model_to_ct2.py`
3. ✅ Update `.env` with new `TRANSLATE_PROVIDER_CHAIN`
4. ✅ (Optional) Get DeepL API key and add to `.env`
5. ✅ Test the application: `.\run.ps1`

Enjoy ultra-fast local translation! 🚀

