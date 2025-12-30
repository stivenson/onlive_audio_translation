# Script para crear ejecutable portable de Live Audio Translator
# Build script for creating portable executable

param(
    [switch]$Clean = $false,
    [switch]$OneFile = $true,
    [string]$Icon = ""
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  BUILD EXECUTABLE - LIVE AUDIO TRANSLATOR" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar que estamos en el directorio correcto
if (-not (Test-Path "app\main.py")) {
    Write-Host "Error: No se encontró app\main.py" -ForegroundColor Red
    Write-Host "Error: app\main.py not found" -ForegroundColor Red
    Write-Host "Ejecuta este script desde la raíz del proyecto / Run this script from project root" -ForegroundColor Yellow
    exit 1
}

# Activar entorno virtual si existe
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "Activando entorno virtual / Activating virtual environment..." -ForegroundColor Green
    & ".venv\Scripts\Activate.ps1"
}

# Verificar PyInstaller
Write-Host "Verificando PyInstaller / Checking PyInstaller..." -ForegroundColor Green
try {
    $pyinstallerVersion = pyinstaller --version
    Write-Host "PyInstaller encontrado / PyInstaller found: $pyinstallerVersion" -ForegroundColor Green
} catch {
    Write-Host "PyInstaller no encontrado. Instalando / PyInstaller not found. Installing..." -ForegroundColor Yellow
    pip install pyinstaller
}

# Limpiar builds anteriores si se solicita
if ($Clean -or (Test-Path "build") -or (Test-Path "dist")) {
    Write-Host "Limpiando builds anteriores / Cleaning previous builds..." -ForegroundColor Yellow
    if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
    if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
    if (Test-Path "*.spec") { Remove-Item -Force "*.spec" }
    Write-Host "Limpieza completada / Cleanup completed" -ForegroundColor Green
}

# Preparar argumentos de PyInstaller
$pyinstallerArgs = @(
    "--name=LiveAudioTranslator",
    "--windowed",
    "--noconfirm",
    "--clean"
)

# Opción onefile o onedir
if ($OneFile) {
    $pyinstallerArgs += "--onefile"
    Write-Host "Modo: Un solo archivo ejecutable / Mode: Single executable file" -ForegroundColor Cyan
} else {
    $pyinstallerArgs += "--onedir"
    Write-Host "Modo: Directorio con archivos / Mode: Directory with files" -ForegroundColor Cyan
}

# Agregar icono si existe
if ($Icon -and (Test-Path $Icon)) {
    $pyinstallerArgs += "--icon=$Icon"
    Write-Host "Icono personalizado / Custom icon: $Icon" -ForegroundColor Cyan
} elseif (Test-Path "icon.ico") {
    $pyinstallerArgs += "--icon=icon.ico"
    Write-Host "Usando icon.ico / Using icon.ico" -ForegroundColor Cyan
}

# Agregar archivos de datos
Write-Host "Agregando archivos de datos / Adding data files..." -ForegroundColor Green

# .env.example
if (Test-Path ".env.example") {
    $pyinstallerArgs += "--add-data=.env.example;."
    Write-Host "  - .env.example" -ForegroundColor Gray
}

# Modelos de CTranslate2 si existen
if (Test-Path "models") {
    $pyinstallerArgs += "--add-data=models;models"
    Write-Host "  - models/ (CTranslate2 models)" -ForegroundColor Gray
}

# Scripts útiles
if (Test-Path "scripts") {
    $pyinstallerArgs += "--add-data=scripts;scripts"
    Write-Host "  - scripts/" -ForegroundColor Gray
}

# Archivos ocultos necesarios
$pyinstallerArgs += "--hidden-import=PySide6.QtCore"
$pyinstallerArgs += "--hidden-import=PySide6.QtGui"
$pyinstallerArgs += "--hidden-import=PySide6.QtWidgets"
$pyinstallerArgs += "--hidden-import=qasync"
$pyinstallerArgs += "--hidden-import=ctranslate2"
$pyinstallerArgs += "--hidden-import=sentencepiece"
$pyinstallerArgs += "--hidden-import=deepl"
$pyinstallerArgs += "--hidden-import=deepgram"
$pyinstallerArgs += "--hidden-import=openai"
$pyinstallerArgs += "--hidden-import=pyaudio"
$pyinstallerArgs += "--hidden-import=numpy"
$pyinstallerArgs += "--hidden-import=dotenv"

# Recopilar todos los módulos de la app
$pyinstallerArgs += "--collect-all=app"
$pyinstallerArgs += "--collect-all=PySide6"

# Punto de entrada
$pyinstallerArgs += "app/main.py"

Write-Host ""
Write-Host "Ejecutando PyInstaller / Running PyInstaller..." -ForegroundColor Yellow
Write-Host "Esto puede tardar varios minutos / This may take several minutes..." -ForegroundColor Yellow
Write-Host ""

# Ejecutar PyInstaller
& pyinstaller @pyinstallerArgs

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  BUILD COMPLETADO / BUILD COMPLETED" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    
    if ($OneFile) {
        $exePath = "dist\LiveAudioTranslator.exe"
        if (Test-Path $exePath) {
            $fileSize = (Get-Item $exePath).Length / 1MB
            Write-Host "Ejecutable creado / Executable created:" -ForegroundColor Green
            Write-Host "  $exePath" -ForegroundColor Cyan
            Write-Host "  Tamaño / Size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "Para distribuir / To distribute:" -ForegroundColor Yellow
            Write-Host "  1. Copia LiveAudioTranslator.exe a donde quieras" -ForegroundColor White
            Write-Host "     Copy LiveAudioTranslator.exe to where you want" -ForegroundColor White
            Write-Host "  2. Copia .env.example junto al ejecutable" -ForegroundColor White
            Write-Host "     Copy .env.example next to the executable" -ForegroundColor White
            Write-Host "  3. Si usas modelos CTranslate2, copia la carpeta models/" -ForegroundColor White
            Write-Host "     If using CTranslate2 models, copy the models/ folder" -ForegroundColor White
        }
    } else {
        $dirPath = "dist\LiveAudioTranslator"
        if (Test-Path $dirPath) {
            Write-Host "Aplicación creada / Application created:" -ForegroundColor Green
            Write-Host "  $dirPath" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "Para distribuir / To distribute:" -ForegroundColor Yellow
            Write-Host "  Copia toda la carpeta LiveAudioTranslator" -ForegroundColor White
            Write-Host "  Copy the entire LiveAudioTranslator folder" -ForegroundColor White
        }
    }
    
    Write-Host ""
    Write-Host "NOTA / NOTE:" -ForegroundColor Yellow
    Write-Host "  El ejecutable necesita las DLLs de PySide6 y otras dependencias." -ForegroundColor White
    Write-Host "  The executable needs PySide6 DLLs and other dependencies." -ForegroundColor White
    Write-Host "  Prueba en una máquina limpia antes de distribuir." -ForegroundColor White
    Write-Host "  Test on a clean machine before distributing." -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  ERROR EN EL BUILD / BUILD ERROR" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Revisa los mensajes de error arriba / Check error messages above" -ForegroundColor Yellow
    exit 1
}

