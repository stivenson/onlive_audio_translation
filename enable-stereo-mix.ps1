# Script para habilitar "Stereo Mix" / "Mezcla estereo" en Windows
# Requiere ejecutarse como Administrador
# Uso: .\enable-stereo-mix.ps1

# Verificar si se esta ejecutando como administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Este script requiere permisos de administrador." -ForegroundColor Yellow
    Write-Host "Intentando ejecutar como administrador..." -ForegroundColor Cyan
    Write-Host ""
    
    # Auto-elevar el script
    $scriptPath = $MyInvocation.MyCommand.Path
    $scriptArgs = $MyInvocation.BoundParameters
    
    try {
        # Ejecutar el script como administrador
        Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
        exit 0
    } catch {
        Write-Host "No se pudo elevar automaticamente. Por favor, ejecuta PowerShell como administrador manualmente." -ForegroundColor Red
        Write-Host ""
        Write-Host "Para ejecutar como administrador manualmente:" -ForegroundColor Cyan
        Write-Host "1. Cierra esta ventana" -ForegroundColor White
        Write-Host "2. Haz clic derecho en PowerShell" -ForegroundColor White
        Write-Host "3. Selecciona 'Ejecutar como administrador'" -ForegroundColor White
        Write-Host "4. Ejecuta: .\enable-stereo-mix.ps1" -ForegroundColor White
        pause
        exit 1
    }
}

Write-Host "Buscando dispositivos de audio deshabilitados..." -ForegroundColor Yellow
Write-Host ""

# Codigo C# para acceder a la API de audio de Windows
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

namespace AudioDevices
{
    public class DeviceHelper
    {
        [DllImport("winmm.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        public static extern int waveInGetNumDevs();
        
        [DllImport("winmm.dll", SetLastError = true, CharSet = CharSet.Unicode)]
        public static extern int waveInGetDevCaps(IntPtr deviceId, ref WaveInCaps wic, int size);
        
        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
        public struct WaveInCaps
        {
            public ushort wMid;
            public ushort wPid;
            public uint vDriverVersion;
            [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
            public string szPname;
            public uint dwFormats;
            public ushort wChannels;
            public ushort wReserved1;
        }
    }
}
"@

# Intentar usando comandos de PowerShell y WMI
try {
    # Metodo alternativo: Usando DevCon (si esta disponible)
    # O usando la API de dispositivos de Windows
    
    Write-Host "NOTA: Windows no proporciona un comando PowerShell nativo simple para habilitar Stereo Mix." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Opciones disponibles:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. METODO MANUAL (Recomendado):" -ForegroundColor Green
    Write-Host "   - Presiona Win + R" -ForegroundColor White
    Write-Host "   - Escribe: mmsys.cpl" -ForegroundColor White
    Write-Host "   - Presiona Enter" -ForegroundColor White
    Write-Host "   - Ve a la pestaña 'Grabacion'" -ForegroundColor White
    Write-Host "   - Clic derecho en espacio vacio -> 'Mostrar dispositivos deshabilitados'" -ForegroundColor White
    Write-Host "   - Clic derecho en 'Mezcla estereo' -> 'Habilitar'" -ForegroundColor White
    Write-Host "   - Clic derecho en 'Mezcla estereo' -> 'Establecer como predeterminado'" -ForegroundColor White
    Write-Host ""
    Write-Host "2. ABRIR CONFIGURACION AUTOMATICAMENTE:" -ForegroundColor Green
    Write-Host ""
    
    $response = Read-Host "Quieres abrir la configuracion de sonido ahora? (S/N)"
    
    if ($response -eq 'S' -or $response -eq 's') {
        Write-Host "Abriendo configuracion de sonido..." -ForegroundColor Green
        Start-Process "mmsys.cpl"
        Write-Host ""
        Write-Host "Sigue los pasos manuales mostrados arriba." -ForegroundColor Cyan
    }
    
    Write-Host ""
    Write-Host "3. ALTERNATIVA - VB-Audio Virtual Cable:" -ForegroundColor Green
    Write-Host "   Si tu tarjeta de audio no tiene Stereo Mix, puedes usar:" -ForegroundColor White
    Write-Host "   https://vb-audio.com/Cable/" -ForegroundColor Cyan
    Write-Host ""
    
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Presiona cualquier tecla para salir..." -ForegroundColor Gray
pause
