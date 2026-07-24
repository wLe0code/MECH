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

# Gestos de los brazos mientras MECH habla.
#   "full"   = gestos reales según lo que pida Claude (wave, excited...),
#              con movimiento suave interpolado (default).
#   "subtle" = movimiento pequeño adelante/atrás cerca del reposo.
#   "off"    = los brazos NO se mueven al hablar.
ARM_GESTURE_MODE = os.environ.get("ARM_GESTURE_MODE", "full").strip().lower()
# Amplitud (grados) del movimiento suave respecto a la posición neutra (90°).
ARM_GESTURE_AMPLITUDE = int(os.environ.get("ARM_GESTURE_AMPLITUDE", "12"))
# Si true, algunos gestos también mueven las ruedas (giro corto, balanceo).
# Los movimientos son cortos y siempre terminan en STOP.
GESTURE_WHEELS = os.environ.get("GESTURE_WHEELS", "true").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)

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
# Modo offline: usa el modelo ya descargado del disco SIN tocar internet, así
# no se cuelga esperando la red (clave en eventos con wifi mala). Default true.
# Ponlo en false SOLO si necesitas DESCARGAR un modelo nuevo de Whisper.
WHISPER_OFFLINE = os.environ.get("WHISPER_OFFLINE", "true").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)

# Audio
AUDIO_SAMPLE_RATE = int(os.environ.get("AUDIO_SAMPLE_RATE", "48000"))
VAD_AGGRESSIVENESS = int(os.environ.get("VAD_AGGRESSIVENESS", "2"))
VAD_SILENCE_TIMEOUT = float(os.environ.get("VAD_SILENCE_TIMEOUT", "1.2"))
# Cuánto más fuerte que el ruido de fondo debe sonar la voz para que MECH
# empiece a grabar (y al revés: cuando la amplitud cae cerca del piso de
# ruido, se considera que terminó de hablar). El piso de ruido se mide solo
# y se adapta al ambiente (clave en stands ruidosos como la olimpiada).
#   2.0 = sensible · 2.5 = equilibrado · 4.0+ = solo voz fuerte y cercana
VAD_ENERGY_FACTOR = float(os.environ.get("VAD_ENERGY_FACTOR", "2.5"))
# En reposo (esperando "ok MECH"), tope de duración de cada grabación: la
# frase de despertar es corta, así que cortamos rápido y revisamos enseguida.
WAKE_MAX_UTTERANCE = float(os.environ.get("WAKE_MAX_UTTERANCE", "4.0"))
# Segundos máximos que el micrófono espera por voz en cada turno. Súbelo si
# el juez/usuario tarda en empezar a hablar.
LISTEN_MAX_SECONDS = float(os.environ.get("AUDIO_LISTEN_MAX_SECONDS", "20"))

# --- Control del bucle de voz por palabra clave ---------------------------
# Si VOICE_AUTOSTART=true, el bucle de voz arranca solo al iniciar el server,
# pero EN REPOSO: el micrófono escucha únicamente la palabra para despertar.
# Así MECH queda esperando "ok MECH" sin tocar el panel.
VOICE_AUTOSTART = os.environ.get("VOICE_AUTOSTART", "true").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)
# Frases (separadas por coma) que ACTIVAN a MECH cuando está en reposo.
# El comando principal es "ok mech" (estilo Alexa/Google). Se incluyen
# variantes de cómo suele transcribirlo Whisper ("okay", "oye", etc.).
VOICE_WAKE_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_WAKE_PHRASES",
        "ok mech,okay mech,okey mech,ok mek,oye mech,"
        "despierta mech,despierta,activa mech,mech despierta",
    ).split(",") if p.strip()
]
# Frases que ponen a MECH EN REPOSO (deja de responder, sigue oyendo el wake).
# El match es por palabras en cualquier orden (ver _matches_any en server.py),
# así que "duermete", "duermete mech" y "mech duermete" funcionan igual.
VOICE_SLEEP_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_SLEEP_PHRASES",
        "para de escuchar,deja de escuchar,para de recibir,ya no escuches,"
        "duermete,duerme,descansa mech,ponte en reposo,modo reposo",
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
# Volumen (0-100) de la música de fondo bajo la narración (solo obras con
# música, ej. Malpaís). Bajo a propósito para que la voz quede por encima.
BACKGROUND_MUSIC_VOLUME = int(os.environ.get("BACKGROUND_MUSIC_VOLUME", "18"))

# Proyección
PROJECTOR_DISPLAY = os.environ.get("PROJECTOR_DISPLAY", ":0")
IMAGE_OUTPUT_DIR = Path(os.environ.get("IMAGE_OUTPUT_DIR", BASE_DIR / "generated_images"))
IMAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Biblioteca de videos pre-renderizados (Opción B).
# Cada obra vive en un subdirectorio (slug) con archivos seg01.mp4, seg02.mp4, ...
# Ver backend/video_library.py para el manifest y backend/video_library/README.md.
VIDEO_LIBRARY_DIR = Path(os.environ.get("VIDEO_LIBRARY_DIR", BASE_DIR / "video_library"))
VIDEO_LIBRARY_DIR.mkdir(parents=True, exist_ok=True)


def _bool_env(key: str, default: str) -> bool:
    return os.environ.get(key, default).strip().lower() in (
        "1", "true", "yes", "on", "si", "sí",
    )


# === Visión (Logitech C930e + MediaPipe) =====================================
# Detección de usuarios frente al robot: presencia, posición y distancia
# estimada (por el tamaño de la cara). Ver backend/vision.py.
VISION_ENABLED = _bool_env("VISION_ENABLED", "false")
# Índice de la cámara para OpenCV (/dev/videoN en la Pi; 0 = primera).
VISION_CAMERA_INDEX = int(os.environ.get("VISION_CAMERA_INDEX", "0"))
# Distancia mínima (metros) a la que debe estar un usuario para que MECH
# proyecte y deje de acercarse. Ajustable en vivo desde el panel (Ajustes).
VISION_MIN_DISTANCE = float(os.environ.get("VISION_MIN_DISTANCE", "1.2"))
# Si true, MECH avanza hacia el usuario hasta quedar a VISION_MIN_DISTANCE.
# Solo se mueve cuando NO está narrando (fases waiting/dormant).
VISION_APPROACH = _bool_env("VISION_APPROACH", "true")
# SIN EFECTO desde jul 2026: el robot ya no gira hacia el usuario (las
# mecanum solo van bien adelante/atrás; girar es manual desde el panel).
# La clave se conserva por compatibilidad con .env existentes.
VISION_FOLLOW = _bool_env("VISION_FOLLOW", "false")
# Si true, NO se proyectan visuales cuando no hay un usuario dentro de la
# distancia mínima (la cámara manda: sin usuario cerca = sin proyección).
# ⚠️ APAGADO por defecto (jul 2026): con la visión encendida podía suprimir
# TODA la proyección si la cámara no detectaba al usuario dentro de la
# distancia (p. ej. operando desde el laptop, o con el detector Haar que
# estima mal la distancia). Actívalo solo si de verdad querés ese
# comportamiento y ya calibraste la distancia mínima.
VISION_PROJECT_GATE = _bool_env("VISION_PROJECT_GATE", "false")
# Velocidad máxima (0-100) de los movimientos autónomos de visión.
VISION_MAX_SPEED = int(os.environ.get("VISION_MAX_SPEED", "35"))


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
