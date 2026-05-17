"""Text-to-Speech con ElevenLabs en streaming.

Usamos streaming porque:
- El audio empieza a sonar antes de que termine de generarse.
- En frases largas (narración de Romeo y Julieta) la latencia baja de
  ~5s a <1s hasta el primer audio.

Reproducimos con sounddevice para no depender de aplay/ffplay externos.
"""

from __future__ import annotations

import io
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


def speak(
    text: str,
    on_start: Callable[[], None] | None = None,
    on_end: Callable[[], None] | None = None,
    blocking: bool = True,
) -> None:
    """Sintetiza `text` y lo reproduce por el parlante por defecto.

    Args:
        text: Texto a hablar (español).
        on_start: Callback al iniciar la reproducción (útil para activar
            gestos del Arduino).
        on_end: Callback al terminar la reproducción.
        blocking: Si True, bloquea hasta terminar. Si False, devuelve
            inmediatamente y reproduce en un hilo.
    """
    if not text.strip():
        return

    def _run():
        client = get_client()
        stream = client.text_to_speech.convert(
            voice_id=config.ELEVENLABS_VOICE_ID,
            model_id=config.ELEVENLABS_MODEL_ID,
            text=text,
            output_format="mp3_44100_128",
        )
        audio, sr = _stream_to_audio(stream)
        if on_start:
            on_start()
        sd.play(audio, sr)
        sd.wait()
        if on_end:
            on_end()

    if blocking:
        _run()
    else:
        threading.Thread(target=_run, daemon=True).start()
