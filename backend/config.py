"""Configuración centralizada del backend MECH.

Lee variables de entorno desde .env y las expone como constantes.
Todos los demás módulos importan de aquí en vez de leer os.environ.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# Claude
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-7")

# ElevenLabs
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "8mBRP99B2Ng2QwsJMFQl")
ELEVENLABS_MODEL_ID = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
# Modo ahorro: si es true, el TTS NO llama a ElevenLabs (no gasta créditos).
# MECH "narra" en seco: loguea el texto y simula la duración para que el
# flujo (gestos, fases, proyección) corra igual. Útil para probar sin gastar.
TTS_DRY_RUN = os.environ.get("TTS_DRY_RUN", "false").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)

# Gemini (NanoBanana)
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GEMINI_IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

# Arduino
ARDUINO_PORT = os.environ.get("ARDUINO_PORT", "/dev/ttyACM0")
ARDUINO_BAUD = int(os.environ.get("ARDUINO_BAUD", "115200"))

# RoboKit RS — movimiento por "bus de pines".
# La Pi pone estos pines GPIO (BCM) en alto/bajo; el RoboKit corre un programa
# Rogic que los lee y se mueve. Un pin activo a la vez = un comando.
# GND de la Pi -> GND del RoboKit (tierra común, obligatorio).
ROBOKIT_PIN_FWD = int(os.environ.get("ROBOKIT_PIN_FWD", "17"))    # adelante  -> RoboKit pin 2
ROBOKIT_PIN_LEFT = int(os.environ.get("ROBOKIT_PIN_LEFT", "27"))  # girar izq -> RoboKit pin 3
ROBOKIT_PIN_RIGHT = int(os.environ.get("ROBOKIT_PIN_RIGHT", "22"))  # girar der -> RoboKit pin 4

# STT
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")
WHISPER_LANGUAGE = os.environ.get("WHISPER_LANGUAGE", "es")

# Audio
AUDIO_SAMPLE_RATE = int(os.environ.get("AUDIO_SAMPLE_RATE", "48000"))
VAD_AGGRESSIVENESS = int(os.environ.get("VAD_AGGRESSIVENESS", "2"))
VAD_SILENCE_TIMEOUT = float(os.environ.get("VAD_SILENCE_TIMEOUT", "1.2"))
# Segundos máximos que el micrófono espera por voz en cada turno. Súbelo si
# el juez/usuario tarda en empezar a hablar.
LISTEN_MAX_SECONDS = float(os.environ.get("AUDIO_LISTEN_MAX_SECONDS", "20"))

# --- Control del bucle de voz por palabra clave ---------------------------
# Si VOICE_AUTOSTART=true, el bucle de voz arranca solo al iniciar el server,
# pero EN REPOSO: el micrófono escucha únicamente la palabra para despertar.
# Así MECH queda esperando "despierta MECH" sin tocar el panel.
VOICE_AUTOSTART = os.environ.get("VOICE_AUTOSTART", "true").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)
# Frases (separadas por coma) que ACTIVAN a MECH cuando está en reposo.
VOICE_WAKE_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_WAKE_PHRASES",
        "despierta mech,despierta,activa mech,mech despierta",
    ).split(",") if p.strip()
]
# Frases que ponen a MECH EN REPOSO (deja de responder, sigue oyendo el wake).
VOICE_SLEEP_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_SLEEP_PHRASES",
        "para de escuchar,deja de escuchar,para de recibir,ya no escuches,"
        "duermete mech,ponte en reposo,descansa mech,modo reposo",
    ).split(",") if p.strip()
]
# Micrófono de entrada. Vacío = dispositivo por defecto del sistema.
# Se puede poner el índice (número) o parte del nombre del dispositivo.
# El mic del proyecto es el Steren MIC-9010 (receptor USB); la C930e queda
# solo para video. Lista los dispositivos con:
#   python -c "import sounddevice as sd; print(sd.query_devices())"
# y pon aquí "Steren", "MIC-9010" o el número que corresponda.
AUDIO_INPUT_DEVICE = os.environ.get("AUDIO_INPUT_DEVICE", "")
# Segundos de silencio antepuestos a cada respuesta TTS. Compensa el
# arranque lento de parlantes Bluetooth (que se comen la primera palabra).
# Súbelo si el parlante sigue cortando el inicio.
AUDIO_LEAD_SILENCE = float(os.environ.get("AUDIO_LEAD_SILENCE", "1.0"))

# Proyección
PROJECTOR_DISPLAY = os.environ.get("PROJECTOR_DISPLAY", ":0")
IMAGE_OUTPUT_DIR = Path(os.environ.get("IMAGE_OUTPUT_DIR", BASE_DIR / "generated_images"))
IMAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Biblioteca de videos pre-renderizados (Opción B).
# Cada obra vive en un subdirectorio (slug) con archivos seg01.mp4, seg02.mp4, ...
# Ver backend/video_library.py para el manifest y backend/video_library/README.md.
VIDEO_LIBRARY_DIR = Path(os.environ.get("VIDEO_LIBRARY_DIR", BASE_DIR / "video_library"))
VIDEO_LIBRARY_DIR.mkdir(parents=True, exist_ok=True)


def assert_required() -> None:
    """Falla rápido si falta alguna API key crítica."""
    missing = []
    if not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not ELEVENLABS_API_KEY:
        missing.append("ELEVENLABS_API_KEY")
    if not GOOGLE_API_KEY:
        missing.append("GOOGLE_API_KEY")
    if missing:
        raise RuntimeError(
            f"Faltan variables de entorno: {', '.join(missing)}. "
            "Copia backend/.env.example a backend/.env y rellénalas."
        )


def update_env_file(updates: dict[str, str]) -> None:
    """Reescribe backend/.env aplicando `updates` (clave -> valor).

    - Conserva comentarios y líneas no tocadas.
    - Si una clave ya existe, reemplaza su valor; si no, la añade al final.
    - Usado por el panel web (vista Ajustes) para persistir cambios sin
      tener que editar el archivo a mano por SSH.

    OJO: la mayoría de las constantes de este módulo se leen UNA vez al
    importar. Escribir el .env no las cambia en caliente — para eso el
    endpoint también hace setattr() sobre las que sí son seguras en vivo.
    Las demás (API keys, modelo, sample rate, dispositivo) requieren
    reiniciar el servidor.
    """
    lines: list[str] = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()

    remaining = dict(updates)
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in remaining:
                out.append(f"{key}={remaining.pop(key)}")
                continue
        out.append(line)

    # Claves nuevas que no existían en el archivo.
    for key, value in remaining.items():
        out.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
