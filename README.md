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
- Para macOS: Necesitas instalar [BlackHole](https://github.com/ExistentialAudio/BlackHole) para captura de audio del sistema

## Instalación

1. Clona el repositorio:
```bash
git clone <repo-url>
cd traducción_on_live_audio
```

2. Crea un entorno virtual:
```bash
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
```

3. Instala las dependencias:
```bash
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

```bash
python -m app.main
```

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

