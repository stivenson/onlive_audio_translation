# Desktop Live Audio Translator

Aplicación de escritorio Python para traducción y análisis en tiempo real de audio del sistema, con soporte para Windows 11 y macOS.

## Características

- **Captura de audio del sistema**: Captura el audio que pasa por tu tarjeta de audio (loopback)
- **Transcripción en tiempo real**: Con detección automática de idioma y diarización (múltiples hablantes)
- **Traducción automática**: Traduce de inglés a español (o mantiene español si ya lo es)
- **Asignación automática de roles**: Detecta múltiples hablantes y asigna User_1, User_2, etc.
- **Resumen contextual**: Genera un resumen vivo de la conversación con contexto acumulado
- **Sugerencias de preguntas**: Genera preguntas/replicas relevantes en inglés y español
- **Alta disponibilidad**: Sistema redundante con fallback automático entre múltiples proveedores

## Requisitos

- Python 3.10 o superior
- Windows 11 o macOS
- **Para Windows**: Necesitas habilitar "Stereo Mix" o un dispositivo de loopback para capturar el audio del sistema (ver instrucciones abajo)
- **Para macOS**: Necesitas instalar [BlackHole](https://github.com/ExistentialAudio/BlackHole) para captura de audio del sistema

### Configuración de Audio en Windows

Para capturar el audio del sistema en Windows, necesitas habilitar "Stereo Mix":

1. **Clic derecho en el ícono de volumen** en la barra de tareas
2. Selecciona **"Sonidos"** o **"Configuración de sonido"**
3. Ve a la pestaña **"Grabación"**
4. **Clic derecho en el espacio vacío** y marca **"Mostrar dispositivos deshabilitados"**
5. Busca **"Mezcla estéreo"** o **"Stereo Mix"**
6. **Clic derecho** en "Mezcla estéreo" y selecciona **"Habilitar"**
7. **Clic derecho** nuevamente y selecciona **"Establecer como dispositivo predeterminado"**

**Nota**: Si no ves "Stereo Mix", tu tarjeta de audio puede no soportarlo. En ese caso, puedes usar software como [VB-Audio Virtual Cable](https://vb-audio.com/Cable/) para crear un dispositivo de loopback virtual.

## Instalación

1. Clona el repositorio:
```bash
git clone <repo-url>
cd traducción_on_live_audio
```

2. Crea un entorno virtual:
```bash
python -m venv .venv
```

3. Activa el entorno virtual e instala las dependencias:

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS/Linux:**
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

4. Configura las variables de entorno:
```bash
cp .env.example .env
# Edita .env con tus API keys
```

## Configuración

Edita el archivo `.env` con tus credenciales de API:

- **STT Providers**: Deepgram
- **LLM Providers**: OpenAI
- **Translation Providers**: Hugging Face (recomendado), OpenAI LLM (fallback)

La aplicación usa Hugging Face como proveedor principal de traducción y OpenAI como fallback. Si Hugging Face falla, automáticamente cambiará a OpenAI.

### Configuración de Hugging Face para Traducción

Para usar Hugging Face como proveedor de traducción (recomendado para mejor rendimiento y costo):

1. Obtén tu API token de Hugging Face: https://huggingface.co/settings/tokens
2. Configura en `.env`:
   ```env
   HF_API_TOKEN=tu_token_aqui
   HF_TRANSLATION_MODEL=Helsinki-NLP/opus-mt-en-es
   TRANSLATE_PROVIDER_CHAIN=huggingface,llm
   ```

El modelo por defecto `Helsinki-NLP/opus-mt-en-es` está optimizado para traducción inglés→español. Puedes cambiar el modelo según tus necesidades.

### Modelos por Servicio

Cada servicio puede usar un modelo diferente de IA:

- **`TRANSLATION_MODEL_FALLBACK`**: Modelo usado para traducir transcripciones cuando LLM es usado como fallback (por defecto: `gpt-4o`)
- **`SUMMARY_MODEL`**: Modelo usado para generar resúmenes de conversaciones (por defecto: `gpt-4o`)
- **`QUESTIONS_MODEL`**: Modelo usado para generar preguntas/replicas relevantes (por defecto: `gpt-4o`)

Ejemplo de configuración:
```env
TRANSLATION_MODEL_FALLBACK=gpt-4o
SUMMARY_MODEL=gpt-4o-mini
QUESTIONS_MODEL=gpt-4o
```

Esto te permite optimizar costos usando modelos más económicos para tareas simples (como traducción) y modelos más potentes para análisis complejos (como resúmenes y preguntas).

## Uso

### Windows (PowerShell)

**Recomendado - Usar el script de ejecución:**
```powershell
.\run.ps1
```

Este script automáticamente:
- Activa el entorno virtual (`.venv`)
- Verifica que estás usando el Python correcto
- Ejecuta la aplicación

**Alternativa - Ejecución manual:**
```powershell
# 1. Activar el entorno virtual
.\.venv\Scripts\Activate.ps1

# 2. Ejecutar la aplicación
python -m app.main
```

**Nota sobre permisos en PowerShell:**
Si encuentras un error de política de ejecución, ejecuta:
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### macOS/Linux

**Recomendado - Usar el script de ejecución:**
```bash
# Dar permisos de ejecución (solo la primera vez)
chmod +x run.sh

# Ejecutar la aplicación
./run.sh
```

**Alternativa - Ejecución manual:**
```bash
# 1. Activar el entorno virtual
source .venv/bin/activate

# 2. Ejecutar la aplicación
python -m app.main
```

**IMPORTANTE**: 
- Siempre debes activar el entorno virtual antes de ejecutar la aplicación, de lo contrario los proveedores no se inicializarán correctamente.
- El script `run.ps1` (Windows) o `run.sh` (macOS/Linux) lo hace automáticamente por ti.

### Instalación de Paquetes Adicionales

Si necesitas instalar un paquete adicional y actualizar `requirements.txt`:

**Windows:**
```powershell
.\install-package.ps1 <nombre-paquete>
```

**Ejemplo:**
```powershell
.\install-package.ps1 requests
```

Este script automáticamente:
- Activa el entorno virtual
- Instala el paquete
- Actualiza `requirements.txt` con la versión exacta instalada

## Estructura del Proyecto

```
app/
├── main.py              # Punto de entrada
├── ui/                  # Interfaz gráfica (PySide6)
├── audio/               # Captura de audio
├── stt/                 # Proveedores STT y router
├── translate/           # Proveedores de traducción y router
├── llm/                 # Proveedores LLM y router
├── core/                # Event bus, memoria, schemas, circuit breaker
├── config/              # Configuración y carga de .env
└── storage/             # Persistencia y exportación
```

## Licencia

MIT

