# Script para ejecutar la aplicacion con el entorno virtual activado
# Uso: .\run.ps1

# Verificar y configurar Stereo Mix si es necesario
if (-not (Test-Path ".stereo-mix-checked")) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  CONFIGURACION DE AUDIO DEL SISTEMA" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Para capturar audio del sistema (reuniones, videos, etc.)," -ForegroundColor White
    Write-Host "necesitas habilitar Stereo Mix / Mezcla estéreo." -ForegroundColor White
    Write-Host ""
    Write-Host "INSTRUCCIONES:" -ForegroundColor Green
    Write-Host "1. Ve a la pestaña 'Grabación'" -ForegroundColor White
    Write-Host "2. Clic derecho en espacio vacío → 'Mostrar dispositivos deshabilitados'" -ForegroundColor White
    Write-Host "3. Clic derecho en 'Mezcla estéreo' → 'Habilitar'" -ForegroundColor White
    Write-Host "4. Clic derecho en 'Mezcla estéreo' → 'Establecer como predeterminado'" -ForegroundColor White
    Write-Host ""
    
    $response = Read-Host "¿Quieres abrir la configuración de sonido ahora? (S/N)"
    
    if ($response -eq 'S' -or $response -eq 's') {
        Write-Host "Abriendo configuración de sonido..." -ForegroundColor Green
        Start-Process "mmsys.cpl"
        Write-Host ""
        Write-Host "Sigue las instrucciones mostradas arriba." -ForegroundColor Cyan
        Write-Host ""
    }
    
    Write-Host "Presiona Enter para continuar con la aplicación..." -ForegroundColor Gray
    pause
    
    # Marcar como verificado
    New-Item -ItemType File -Path ".stereo-mix-checked" -Force | Out-Null
}

# Activar el entorno virtual
& "$PSScriptRoot\.venv\Scripts\Activate.ps1"

# Verificar que el entorno está activo
$pythonPath = (Get-Command python).Source
Write-Host "Usando Python de: $pythonPath" -ForegroundColor Green

# Ejecutar la aplicación
python -m app.main
