"""Text-to-Speech con ElevenLabs en streaming.

Usamos streaming porque:
- El audio empieza a sonar antes de que termine de generarse.
- En frases largas (narración de Romeo y Julieta) la latencia baja de
  ~5s a <1s hasta el primer audio.

Reproducimos con sounddevice para no depender de aplay/ffplay externos.
"""

from __future__ import annotations

import base64
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
import subtitles


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


def play_chime() -> None:
    """Sonido corto de 'listo' (dos notas ascendentes), sin gastar créditos.

    Lo usa el arranque del bucle de voz para avisar que MECH ya está activo y
    se le puede hablar / decir 'despierta MECH'. Es un tono puro generado en
    el momento; no es voz, así que no dispara la detección de palabras.
    """
    try:
        sr = 44100

        def _tone(freq: float, dur: float) -> np.ndarray:
            t = np.linspace(0, dur, int(sr * dur), endpoint=False)
            wave = 0.30 * np.sin(2 * np.pi * freq * t)
            fade = max(1, int(sr * 0.012))  # micro fade in/out (evita clics)
            env = np.ones_like(wave)
            env[:fade] = np.linspace(0, 1, fade)
            env[-fade:] = np.linspace(1, 0, fade)
            return (wave * env).astype(np.float32)

        gap = np.zeros(int(sr * 0.04), dtype=np.float32)
        # Un pelín de silencio al inicio para que el parlante BT no se coma la
        # primera nota, pero corto (no el silencio largo de la voz).
        audio = np.concatenate([_tone(660, 0.14), gap, _tone(988, 0.18)])
        _stop_event.clear()
        _play_audio(audio, sr, lead_silence=0.25)
    except Exception:
        pass


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


def _synthesize(text: str, voice_id: str) -> tuple[np.ndarray, int, list[float] | None]:
    """Pide el audio a ElevenLabs. Devuelve (audio, samplerate, char_times).

    Intenta primero el endpoint CON marcas de tiempo por carácter (para
    sincronizar los subtítulos con las pausas). Si esta versión del SDK o de
    la API no lo soporta, cae al `convert` de siempre y devuelve
    `char_times=None`.
    """
    client = get_client()
    con_marcas = getattr(client.text_to_speech, "convert_with_timestamps", None)
    if con_marcas is not None:
        try:
            resp = con_marcas(
                voice_id=voice_id,
                model_id=config.ELEVENLABS_MODEL_ID,
                text=text,
                output_format="mp3_44100_128",
            )
            b64 = resp.get("audio_base64") if isinstance(resp, dict) else getattr(resp, "audio_base64", None)
            alignment = resp.get("alignment") if isinstance(resp, dict) else getattr(resp, "alignment", None)
            if b64:
                data, sr = sf.read(io.BytesIO(base64.b64decode(b64)), dtype="float32", always_2d=False)
                return data, sr, subtitles.char_times(alignment, text)
        except Exception as e:
            print(f"[TTS] Sin marcas de tiempo ({e}); uso el modo normal.")

    stream = client.text_to_speech.convert(
        voice_id=voice_id,
        model_id=config.ELEVENLABS_MODEL_ID,
        text=text,
        output_format="mp3_44100_128",
    )
    audio, sr = _stream_to_audio(stream)
    return audio, sr, None


# Segundos de silencio que se añaden al inicio del audio. Los parlantes
# Bluetooth tardan en "despertar" y se comen el principio del sonido; este
# silencio inicial evita que se pierdan las primeras palabras.
# Se lee de config.AUDIO_LEAD_SILENCE EN VIVO (no se cachea) para que la
# vista Ajustes del panel pueda subirlo (1.2, 1.5) sin reiniciar.


def _pad_lead_silence(audio: np.ndarray, samplerate: int, seconds: float | None = None) -> np.ndarray:
    """Antepone un breve silencio al audio (para el arranque del Bluetooth).

    `seconds=None` usa config.AUDIO_LEAD_SILENCE; pasar 0 lo desactiva (ej.
    para el chime, que no necesita ese silencio largo)."""
    lead = config.AUDIO_LEAD_SILENCE if seconds is None else seconds
    pad = int(samplerate * lead)
    if pad <= 0:
        return audio
    if audio.ndim == 1:
        silence = np.zeros(pad, dtype=audio.dtype)
    else:
        silence = np.zeros((pad, audio.shape[1]), dtype=audio.dtype)
    return np.concatenate([silence, audio], axis=0)


def _play_audio(
    audio: np.ndarray,
    samplerate: int,
    lead_silence: float | None = None,
    on_started: Callable[[], None] | None = None,
) -> None:
    """Reproduce el audio por el parlante del sistema.

    `on_started` se llama en cuanto el reproductor arranca de verdad (no
    antes de escribir el archivo temporal ni de lanzar el proceso): es el
    t=0 que usan los subtítulos. Si el primer reproductor falla y hay que
    probar el siguiente, se vuelve a llamar — los subtítulos reinician
    solos y siguen cuadrando.

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
    audio = _pad_lead_silence(audio, samplerate, lead_silence)
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
            if on_started:
                try:
                    on_started()
                except Exception as e:
                    print(f"[TTS] on_started falló: {e}")
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
        if on_started:
            try:
                on_started()
            except Exception as e:
                print(f"[TTS] on_started falló: {e}")
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
    on_playback: Callable[[dict], None] | None = None,
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
        on_playback: Callback que se llama JUSTO cuando arranca el sonido,
            con `{"duration", "lead", "char_times"}`. Lo usan los subtítulos
            para sincronizarse con la voz de verdad (no con una estimación):
            `duration` = segundos de voz, `lead` = silencio inicial que se le
            antepone, `char_times` = segundo de cada carácter del texto (o
            None si la API no lo dio).
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
            simulada = min(8.0, max(1.0, len(text) / 15.0))
            if on_start:
                on_start()
            if on_playback:
                on_playback({"duration": simulada, "lead": 0.0, "char_times": None})
            time.sleep(simulada)
            if on_end:
                on_end()
            return

        audio, sr, char_times = _synthesize(text, chosen_voice)
        if on_start:
            on_start()
        # Los subtítulos arrancan cuando el sonido empieza a salir de verdad
        # (dentro de _play_audio), con `lead` segundos de silencio delante.
        info = {
            "duration": len(audio) / float(sr or 1),
            "lead": config.AUDIO_LEAD_SILENCE,
            "char_times": char_times,
        }
        _play_audio(
            audio,
            sr,
            on_started=(lambda: on_playback(info)) if on_playback else None,
        )
        if on_end:
            on_end()

    if blocking:
        _run()
    else:
        threading.Thread(target=_run, daemon=True).start()
