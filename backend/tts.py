"""Text-to-Speech con ElevenLabs en streaming.

Usamos streaming porque:
- El audio empieza a sonar antes de que termine de generarse.
- En frases largas (narración de Romeo y Julieta) la latencia baja de
  ~5s a <1s hasta el primer audio.

Reproducimos con sounddevice para no depender de aplay/ffplay externos.
"""

from __future__ import annotations

import io
import os
import subprocess
import tempfile
import threading
from typing import Callable, Iterator

import numpy as np
import soundfile as sf
import sounddevice as sd
from elevenlabs.client import ElevenLabs

import config


_client: ElevenLabs | None = None


def get_client() -> ElevenLabs:
    global _client
    if _client is None:
        _client = ElevenLabs(api_key=config.ELEVENLABS_API_KEY)
    return _client


def _stream_to_audio(byte_stream: Iterator[bytes]) -> tuple[np.ndarray, int]:
    """Acumula chunks MP3 y los decodifica a PCM float32."""
    buffer = io.BytesIO()
    for chunk in byte_stream:
        if chunk:
            buffer.write(chunk)
    buffer.seek(0)
    data, samplerate = sf.read(buffer, dtype="float32", always_2d=False)
    return data, samplerate


# Segundos de silencio que se añaden al inicio del audio. Los parlantes
# Bluetooth tardan en "despertar" y se comen el principio del sonido; este
# silencio inicial evita que se pierdan las primeras palabras.
# Configurable con AUDIO_LEAD_SILENCE en .env: súbelo (1.2, 1.5) si el
# parlante Bluetooth sigue comiéndose la primera palabra.
LEAD_SILENCE_SEC = config.AUDIO_LEAD_SILENCE


def _pad_lead_silence(audio: np.ndarray, samplerate: int) -> np.ndarray:
    """Antepone un breve silencio al audio (para el arranque del Bluetooth)."""
    pad = int(samplerate * LEAD_SILENCE_SEC)
    if pad <= 0:
        return audio
    if audio.ndim == 1:
        silence = np.zeros(pad, dtype=audio.dtype)
    else:
        silence = np.zeros((pad, audio.shape[1]), dtype=audio.dtype)
    return np.concatenate([silence, audio], axis=0)


def _play_audio(audio: np.ndarray, samplerate: int) -> None:
    """Reproduce el audio por el parlante del sistema.

    Usa pw-play / paplay (PipeWire / PulseAudio) para que salga por el sink
    por defecto —incluido un parlante Bluetooth—, porque sounddevice apunta
    directo al hardware ALSA (que en la Pi 5 suele ser el HDMI, no la JBL).
    Si ningún reproductor del sistema está disponible, cae a sounddevice.
    """
    audio = _pad_lead_silence(audio, samplerate)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        sf.write(tmp_path, audio, samplerate)
        for player in (["pw-play", tmp_path], ["paplay", tmp_path]):
            try:
                subprocess.run(player, check=True)
                return
            except FileNotFoundError:
                continue  # ese reproductor no está instalado; probar el siguiente
            except subprocess.CalledProcessError:
                continue
        # Último recurso: sounddevice (irá al dispositivo por defecto de PortAudio).
        sd.play(audio, samplerate)
        sd.wait()
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def speak(
    text: str,
    on_start: Callable[[], None] | None = None,
    on_end: Callable[[], None] | None = None,
    blocking: bool = True,
    voice_id: str | None = None,
) -> None:
    """Sintetiza `text` y lo reproduce por el parlante por defecto.

    Args:
        text: Texto a hablar (español).
        on_start: Callback al iniciar la reproducción (útil para activar
            gestos del Arduino).
        on_end: Callback al terminar la reproducción.
        blocking: Si True, bloquea hasta terminar. Si False, devuelve
            inmediatamente y reproduce en un hilo.
        voice_id: Voice ID de ElevenLabs a usar SOLO para esta llamada
            (multi-personaje, ver backend/voices.py). Si es None o vacío,
            usa `config.ELEVENLABS_VOICE_ID` por defecto.
    """
    if not text.strip():
        return
    chosen_voice = voice_id or config.ELEVENLABS_VOICE_ID

    def _run():
        client = get_client()
        stream = client.text_to_speech.convert(
            voice_id=chosen_voice,
            model_id=config.ELEVENLABS_MODEL_ID,
            text=text,
            output_format="mp3_44100_128",
        )
        audio, sr = _stream_to_audio(stream)
        if on_start:
            on_start()
        _play_audio(audio, sr)
        if on_end:
            on_end()

    if blocking:
        _run()
    else:
        threading.Thread(target=_run, daemon=True).start()
