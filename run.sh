#!/bin/bash
# Script para ejecutar la aplicación con el entorno virtual activado (macOS/Linux)
# Uso: ./run.sh

# Activar el entorno virtual
source .venv/bin/activate

# Verificar que el entorno está activo
echo "Usando Python de: $(which python)"

# Ejecutar la aplicación
python -m app.main

