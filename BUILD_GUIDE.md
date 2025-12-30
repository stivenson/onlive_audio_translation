# Guía de Build / Build Guide

Esta guía explica cómo crear un ejecutable portable de Live Audio Translator para Windows.

This guide explains how to create a portable executable of Live Audio Translator for Windows.

## Requisitos Previos / Prerequisites

- Python 3.10 o superior / Python 3.10 or higher
- Entorno virtual activado con todas las dependencias / Virtual environment activated with all dependencies
- PyInstaller (se instala automáticamente si no está) / PyInstaller (installed automatically if missing)

## Método Rápido / Quick Method

### Windows (PowerShell)

```powershell
# Opción 1: Ejecutable único (recomendado para distribución)
# Option 1: Single executable (recommended for distribution)
.\build-executable.ps1

# Opción 2: Directorio con archivos (más rápido de compilar)
# Option 2: Directory with files (faster to compile)
.\build-executable.ps1 -OneFile:$false

# Opción 3: Limpiar y reconstruir
# Option 3: Clean and rebuild
.\build-executable.ps1 -Clean
```

## Estructura del Ejecutable / Executable Structure

### Modo OneFile (Un solo archivo)

El script crea un único archivo `LiveAudioTranslator.exe` en `dist/` que contiene todo.

The script creates a single `LiveAudioTranslator.exe` file in `dist/` containing everything.

**Ventajas / Advantages:**
- ✅ Un solo archivo fácil de distribuir / Single file easy to distribute
- ✅ No necesita instalación / No installation needed
- ✅ Portable completo / Fully portable

**Desventajas / Disadvantages:**
- ⚠️ Tarda más en compilar / Takes longer to compile
- ⚠️ Tarda más en iniciar (extrae archivos temporalmente) / Takes longer to start (extracts files temporarily)
- ⚠️ Archivo más grande (~200-300 MB) / Larger file size (~200-300 MB)

### Modo Onedir (Directorio)

El script crea una carpeta `LiveAudioTranslator/` en `dist/` con todos los archivos necesarios.

The script creates a `LiveAudioTranslator/` folder in `dist/` with all necessary files.

**Ventajas / Advantages:**
- ✅ Compila más rápido / Compiles faster
- ✅ Inicia más rápido / Starts faster
- ✅ Más fácil de depurar / Easier to debug

**Desventajas / Disadvantages:**
- ⚠️ Necesitas distribuir toda la carpeta / Need to distribute entire folder
- ⚠️ Muchos archivos / Many files

## Distribución / Distribution

### Para OneFile (Ejecutable único)

1. **Copia el ejecutable / Copy the executable:**
   ```
   dist/LiveAudioTranslator.exe
   ```

2. **Copia el archivo de configuración de ejemplo / Copy example config file:**
   ```
   .env.example
   ```

3. **Opcional: Si usas modelos CTranslate2 locales / Optional: If using local CTranslate2 models:**
   ```
   models/opus-mt-en-es-ct2/
   ```

4. **Estructura recomendada / Recommended structure:**
   ```
   LiveAudioTranslator/
   ├── LiveAudioTranslator.exe
   ├── .env.example
   └── models/                    (opcional / optional)
       └── opus-mt-en-es-ct2/
   ```

### Para Onedir (Directorio)

1. **Copia toda la carpeta / Copy entire folder:**
   ```
   dist/LiveAudioTranslator/
   ```

2. **Agrega archivos adicionales / Add additional files:**
   - `.env.example` (junto al ejecutable / next to executable)
   - `models/` si usas CTranslate2 / if using CTranslate2

## Configuración del Usuario Final / End User Configuration

El usuario final necesita:

The end user needs to:

1. **Copiar `.env.example` a `.env` / Copy `.env.example` to `.env`:**
   ```powershell
   copy .env.example .env
   ```

2. **Editar `.env` con sus API keys / Edit `.env` with their API keys:**
   - `DEEPGRAM_API_KEY` (requerido / required)
   - `OPENAI_API_KEY` (requerido / required)
   - `DEEPL_API_KEY` (opcional / optional)
   - `HF_API_TOKEN` (opcional / optional)

3. **Configurar audio / Configure audio:**
   - Windows: Habilitar "Stereo Mix" / Enable "Stereo Mix"
   - macOS: Instalar BlackHole / Install BlackHole

## Incluir Modelos CTranslate2 / Including CTranslate2 Models

Si quieres incluir modelos de traducción locales en el ejecutable:

If you want to include local translation models in the executable:

1. **Genera el modelo / Generate the model:**
   ```bash
   python scripts/convert_model_to_ct2.py
   ```

2. **El modelo se crea en / Model is created in:**
   ```
   models/opus-mt-en-es-ct2/
   ```

3. **El script de build lo incluye automáticamente / Build script includes it automatically**

4. **Para distribución / For distribution:**
   - OneFile: Copia la carpeta `models/` junto al ejecutable / Copy `models/` folder next to executable
   - Onedir: Ya está incluida / Already included

## Solución de Problemas / Troubleshooting

### El ejecutable no inicia / Executable won't start

1. **Ejecuta desde la línea de comandos / Run from command line:**
   ```powershell
   .\LiveAudioTranslator.exe
   ```
   Esto mostrará errores / This will show errors

2. **Verifica dependencias / Check dependencies:**
   - Asegúrate de que todas las DLLs estén incluidas / Make sure all DLLs are included
   - Prueba en una máquina limpia / Test on a clean machine

3. **Revisa los logs / Check logs:**
   ```
   logs/app.log
   ```

### Falta algún módulo / Missing module

Agrega el módulo faltante al script `build-executable.ps1`:

Add the missing module to `build-executable.ps1`:

```powershell
$pyinstallerArgs += "--hidden-import=nombre_modulo"
```

### El ejecutable es muy grande / Executable is too large

1. **Usa modo onedir en lugar de onefile / Use onedir mode instead of onefile**
2. **Excluye modelos grandes si no son necesarios / Exclude large models if not needed**
3. **Usa compresión UPX (opcional) / Use UPX compression (optional):**
   ```powershell
   $pyinstallerArgs += "--upx-dir=C:\upx"
   ```

### Errores de audio / Audio errors

El ejecutable necesita acceso a los dispositivos de audio del sistema.

The executable needs access to system audio devices.

- **Windows:** Asegúrate de que "Stereo Mix" esté habilitado / Make sure "Stereo Mix" is enabled
- **macOS:** BlackHole debe estar instalado / BlackHole must be installed

## Crear Instalador (Opcional) / Create Installer (Optional)

### Inno Setup (Windows)

1. Descarga Inno Setup: https://jrsoftware.org/isinfo.php
2. Crea un script `.iss` que incluya:
   - El ejecutable
   - `.env.example`
   - Modelos si aplica
   - Scripts de configuración de audio

### NSIS (Windows)

Similar a Inno Setup, pero con sintaxis diferente.

Similar to Inno Setup, but with different syntax.

## Notas Importantes / Important Notes

1. **Primera ejecución lenta / Slow first run:**
   - El modo onefile extrae archivos temporalmente / Onefile mode extracts files temporarily
   - La primera vez puede tardar más / First time may take longer

2. **Antivirus / Antivirus:**
   - Algunos antivirus pueden marcar el ejecutable como sospechoso / Some antivirus may flag the executable
   - Esto es normal con PyInstaller / This is normal with PyInstaller
   - Considera firmar el ejecutable digitalmente / Consider digitally signing the executable

3. **Actualizaciones / Updates:**
   - El usuario necesita reemplazar el ejecutable completo / User needs to replace entire executable
   - Considera un sistema de actualización automática / Consider automatic update system

4. **Privacidad / Privacy:**
   - El ejecutable contiene todo el código / Executable contains all code
   - Las API keys deben estar en `.env` (no hardcodeadas) / API keys must be in `.env` (not hardcoded)

## Comandos Útiles / Useful Commands

```powershell
# Ver tamaño del ejecutable / Check executable size
Get-Item dist\LiveAudioTranslator.exe | Select-Object Length

# Probar ejecutable / Test executable
.\dist\LiveAudioTranslator.exe

# Limpiar todo / Clean everything
Remove-Item -Recurse -Force build, dist, *.spec
```

