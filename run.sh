#!/bin/bash
# Script para ejecutar la aplicación con el entorno virtual activado (macOS/Linux)
# Uso: ./run.sh

# Verificar y configurar audio del sistema si es necesario
if [ ! -f ".stereo-mix-checked" ]; then
    echo ""
    echo "========================================"
    echo "  CONFIGURACIÓN DE AUDIO DEL SISTEMA"
    echo "========================================"
    echo ""
    echo "Para capturar audio del sistema (reuniones, videos, etc.),"
    echo "necesitas configurar un dispositivo de captura de audio."
    echo ""

    # Detectar el sistema operativo
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo "INSTRUCCIONES PARA macOS:"
        echo "1. Necesitas instalar 'BlackHole' (dispositivo de audio virtual)"
        echo "2. Descarga desde: https://github.com/ExistentialAudio/BlackHole"
        echo "3. Instala BlackHole 2ch"
        echo "4. Ve a 'Configuración del Sistema' → 'Sonido'"
        echo "5. Crea un dispositivo de salida múltiple en 'Audio MIDI Setup'"
        echo "   (Aplicaciones → Utilidades → Configuración de Audio MIDI)"
        echo "6. Incluye BlackHole y tus altavoces en el dispositivo múltiple"
        echo "7. Selecciona BlackHole como dispositivo de entrada en la aplicación"
        echo ""

        read -p "¿Quieres abrir Audio MIDI Setup ahora? (S/N): " response

        if [[ "$response" == "S" || "$response" == "s" ]]; then
            echo "Abriendo Audio MIDI Setup..."
            open -a "Audio MIDI Setup"
            echo ""
            echo "Sigue las instrucciones mostradas arriba."
            echo ""
        fi
    else
        # Linux
        echo "INSTRUCCIONES PARA LINUX:"
        echo "1. Necesitas configurar PulseAudio o PipeWire para capturar audio"
        echo "2. Instala 'pavucontrol' si no lo tienes:"
        echo "   - Ubuntu/Debian: sudo apt install pavucontrol"
        echo "   - Fedora: sudo dnf install pavucontrol"
        echo "   - Arch: sudo pacman -S pavucontrol"
        echo "3. Ejecuta 'pavucontrol'"
        echo "4. Ve a la pestaña 'Grabación'"
        echo "5. Selecciona 'Monitor' de tu dispositivo de salida"
        echo ""

        read -p "¿Quieres abrir pavucontrol ahora? (S/N): " response

        if [[ "$response" == "S" || "$response" == "s" ]]; then
            echo "Abriendo pavucontrol..."
            if command -v pavucontrol &> /dev/null; then
                pavucontrol &
                echo ""
                echo "Sigue las instrucciones mostradas arriba."
                echo ""
            else
                echo "pavucontrol no está instalado. Por favor, instálalo primero."
                echo ""
            fi
        fi
    fi

    echo "Presiona Enter para continuar con la aplicación..."
    read

    # Marcar como verificado
    touch .stereo-mix-checked
fi

# Activar el entorno virtual
source .venv/bin/activate

# Verificar que el entorno está activo
echo "Usando Python de: $(which python)"

# Ejecutar la aplicación
python -m app.main

