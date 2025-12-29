# Script para instalar un paquete en el entorno virtual y actualizar requirements.txt
# Uso: .\install-package.ps1 <nombre-paquete>
# Ejemplo: .\install-package.ps1 requests

param(
    [Parameter(Mandatory=$true)]
    [string]$PackageName
)

# Activar el entorno virtual
& "$PSScriptRoot\.venv\Scripts\Activate.ps1"

# Verificar que el entorno está activo
Write-Host "Usando Python de:" (Get-Command python).Source -ForegroundColor Green
Write-Host ""

# Instalar el paquete
Write-Host "Instalando $PackageName..." -ForegroundColor Yellow
pip install $PackageName

if ($LASTEXITCODE -eq 0) {
    # Obtener la versión exacta instalada
    $packageInfo = pip freeze | Select-String "^$PackageName="
    
    if ($packageInfo) {
        $packageLine = $packageInfo.Line
        
        # Leer requirements.txt
        $requirementsPath = Join-Path $PSScriptRoot "requirements.txt"
        $lines = Get-Content $requirementsPath
        $updated = $false
        $newLines = @()
        
        # Buscar y reemplazar si el paquete ya existe
        foreach ($line in $lines) {
            if ($line -match "^$PackageName[=<>!]") {
                $newLines += $packageLine
                $updated = $true
                Write-Host "Actualizado $PackageName en requirements.txt" -ForegroundColor Green
            } else {
                $newLines += $line
            }
        }
        
        # Si no se encontró, agregar al final
        if (-not $updated) {
            $newLines += $packageLine
            Write-Host "Agregado $PackageName a requirements.txt" -ForegroundColor Green
        }
        
        # Guardar el archivo
        Set-Content -Path $requirementsPath -Value $newLines
        
        Write-Host "Versión instalada: $packageLine" -ForegroundColor Cyan
    } else {
        Write-Host "Advertencia: No se pudo obtener la versión del paquete instalado" -ForegroundColor Yellow
    }
} else {
    Write-Host "Error al instalar el paquete" -ForegroundColor Red
    exit 1
}

