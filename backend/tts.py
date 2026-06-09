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
import time
from typing import Callable, Iterator

import numpy as np
import soundfile as sf
import sounddevice as sd
from elevenlabs.client import ElevenLabs

import config


_client: ElevenLabs | None = None

# --- Interrupción de la voz en curso --------------------------------------
# Permite cortar el TTS al instante (ej. cuando el usuario dice "duérmete"
# mientras MECH narra). request_stop() mata el reproductor actual; speak()
# revisa el flag para no empezar/seguir.
_stop_event = threading.Event()
_current_proc: subprocess.Popen | None = None
_proc_lock = threading.Lock()


def request_stop() -> None:
    """Interrumpe la reproducción de voz en curso."""
    _stop_event.set()
    with _proc_lock:
        if _current_proc is not None and _current_proc.poll() is None:
            try:
                _current_proc.terminate()
            except Exception:
                pass
    try:
        sd.stop()
    except Exception:
        pass


def clear_stop() -> None:
    """Rehabilita la reproducción (antes de un nuevo plan)."""
    _stop_event.clear()


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
# Se lee de config.AUDIO_LEAD_SILENCE EN VIVO (no se cachea) para que la
# vista Ajustes del panel pueda subirlo (1.2, 1.5) sin reiniciar.


def _pad_lead_silence(audio: np.ndarray, samplerate: int) -> np.ndarray:
    """Antepone un breve silencio al audio (para el arranque del Bluetooth)."""
    pad = int(samplerate * config.AUDIO_LEAD_SILENCE)
    if pad <= 0:
        return audio
    if audio.ndim == 1:
        silence = np.zeros(pad, dtype=audio.dtype)
    else:
        silence = np.zeros((pad, audio.shape[1]), dtype=audio.dtype)
    return np.concatenate([silence, audio], axis=0)


def _play_audio(audio: np.ndarray, samplerate: int) -> None:
    """Reproduce el audio por el parlante del sistema.

    Usa pw-play / paplay / ffplay (que salen por el sink por defecto del
    sistema —incluido un parlante Bluetooth/USB— y se MEZCLAN con la música
    de fondo), porque sounddevice apunta directo al hardware ALSA (que en la
    Pi 5 suele ser el HDMI, no el parlante). Importante: ffplay está en la
    lista porque es el mismo reproductor de la música de fondo; si la música
    se oye pero la voz no, era porque la voz no tenía esta opción y caía al
    HDMI. sounddevice queda como último recurso.
    """
    global _current_proc
    if _stop_event.is_set():
        return
    audio = _pad_lead_silence(audio, samplerate)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        sf.write(tmp_path, audio, samplerate)
        players = (
            ["pw-play", tmp_path],
            ["paplay", tmp_path],
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", tmp_path],
        )
        for player in players:
            if _stop_event.is_set():
                return
            try:
                proc = subprocess.Popen(player, stdin=subprocess.DEVNULL)
            except FileNotFoundError:
                continue  # ese reproductor no está instalado; probar el siguiente
            with _proc_lock:
                _current_proc = proc
            proc.wait()
            with _proc_lock:
                _current_proc = None
            if _stop_event.is_set():
                return  # nos interrumpieron a propósito
            if proc.returncode == 0:
                return  # reproducido OK
            # returncode != 0 sin interrupción → ese player falló, probar el siguiente
        # Último recurso: sounddevice (irá al dispositivo por defecto de PortAudio).
        sd.play(audio, samplerate)
        try:
            stream = sd.get_stream()
            while stream is not None and stream.active:
                if _stop_event.is_set():
                    sd.stop()
                    break
                sd.sleep(50)
        except Exception:
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
        if _stop_event.is_set():
            return  # interrupción pedida: no empezamos a hablar
        # Modo ahorro: no se llama a ElevenLabs (no gasta créditos). Se simula
        # la duración (~15 caracteres/seg, tope 8s) para que gestos y fases
        # mantengan un timing realista.
        if config.TTS_DRY_RUN:
            print(f"[TTS ahorro] {text}")
            if on_start:
                on_start()
            time.sleep(min(8.0, max(1.0, len(text) / 15.0)))
            if on_end:
                on_end()
            return

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
