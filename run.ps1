# Script para ejecutar la aplicacion con el entorno virtual activado
# Uso: .\run.ps1

# Verificar si es primera ejecucion y mostrar aviso sobre Stereo Mix
if (-not (Test-Path ".stereo-mix-checked")) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  CONFIGURACION DE AUDIO DEL SISTEMA" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Para capturar audio del sistema (reuniones, videos, etc.)," -ForegroundColor White
    Write-Host "necesitas habilitar Stereo Mix / Mezcla estereo." -ForegroundColor White
    Write-Host ""
    Write-Host "Ejecuta este comando para mas informacion:" -ForegroundColor Green
    Write-Host "  .\enable-stereo-mix.ps1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "O presiona Enter para continuar sin configurar (solo microfono)..." -ForegroundColor Gray
    Write-Host ""
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
