"""Speech-to-Text local con faster-whisper + VAD.

Por qué local en vez de API:
- Sin latencia de red (clave para una demo en vivo).
- Sin costo por minuto.
- Funciona aunque la wifi del evento falle.

VAD (Voice Activity Detection) detecta cuándo el usuario empieza y termina
de hablar, así no grabamos silencio innecesario.
"""

from __future__ import annotations

import collections
import queue
import sys
import time
from typing import Iterator

import numpy as np
import sounddevice as sd
import webrtcvad
from faster_whisper import WhisperModel

import config


# webrtcvad solo acepta frames de 10, 20 o 30 ms a 8/16/32/48 kHz.
FRAME_DURATION_MS = 30
FRAME_BYTES = int(config.AUDIO_SAMPLE_RATE * FRAME_DURATION_MS / 1000) * 2  # int16

_model: WhisperModel | None = None


def get_model() -> WhisperModel:
    """Carga perezosa del modelo Whisper. En Pi 5 usa CPU + int8."""
    global _model
    if _model is None:
        print(f"[STT] Cargando faster-whisper '{config.WHISPER_MODEL}'...")
        _model = WhisperModel(
            config.WHISPER_MODEL,
            device="cpu",
            compute_type="int8",  # menos RAM, suficiente para Pi 5
        )
        print("[STT] Modelo listo.")
    return _model


def _frame_generator(audio_queue: queue.Queue) -> Iterator[bytes]:
    """Convierte el stream del micrófono en frames de 30ms para el VAD."""
    buffer = b""
    while True:
        chunk = audio_queue.get()
        if chunk is None:
            return
        buffer += chunk
        while len(buffer) >= FRAME_BYTES:
            yield buffer[:FRAME_BYTES]
            buffer = buffer[FRAME_BYTES:]


def record_until_silence(max_seconds: float = 15.0) -> np.ndarray | None:
    """Graba desde el micrófono hasta detectar silencio prolongado.

    Devuelve un array float32 mono a AUDIO_SAMPLE_RATE Hz, o None si nunca
    detectó voz dentro del tiempo máximo.
    """
    vad = webrtcvad.Vad(config.VAD_AGGRESSIVENESS)
    audio_q: queue.Queue = queue.Queue()

    def callback(indata, frames, time_info, status):
        if status:
            print(f"[STT] sounddevice: {status}", file=sys.stderr)
        # int16 little-endian, como espera webrtcvad
        audio_q.put(bytes(indata))

    silence_frames_needed = int(config.VAD_SILENCE_TIMEOUT * 1000 / FRAME_DURATION_MS)
    ring_buffer = collections.deque(maxlen=silence_frames_needed)
    voiced_frames: list[bytes] = []
    triggered = False
    start = time.monotonic()

    with sd.RawInputStream(
        samplerate=config.AUDIO_SAMPLE_RATE,
        blocksize=FRAME_BYTES // 2,  # frames de int16
        dtype="int16",
        channels=1,
        callback=callback,
    ):
        for frame in _frame_generator(audio_q):
            if time.monotonic() - start > max_seconds:
                break

            is_speech = vad.is_speech(frame, config.AUDIO_SAMPLE_RATE)

            if not triggered:
                ring_buffer.append((frame, is_speech))
                num_voiced = sum(1 for _, sp in ring_buffer if sp)
                if num_voiced > 0.5 * ring_buffer.maxlen:
                    triggered = True
                    print("[STT] Detectada voz.")
                    voiced_frames.extend(f for f, _ in ring_buffer)
                    ring_buffer.clear()
            else:
                voiced_frames.append(frame)
                ring_buffer.append((frame, is_speech))
                num_unvoiced = sum(1 for _, sp in ring_buffer if not sp)
                if num_unvoiced > 0.9 * ring_buffer.maxlen:
                    print("[STT] Fin de voz.")
                    break

    if not voiced_frames:
        return None

    pcm_bytes = b"".join(voiced_frames)
    audio_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
    return audio_int16.astype(np.float32) / 32768.0


def transcribe(audio: np.ndarray) -> str:
    """Transcribe audio mono float32 a texto."""
    model = get_model()
    segments, _ = model.transcribe(
        audio,
        language=config.WHISPER_LANGUAGE,
        beam_size=1,  # más rápido; suficiente para frases cortas
        vad_filter=False,  # ya pre-filtramos con webrtcvad
    )
    return " ".join(seg.text.strip() for seg in segments).strip()


def listen_once(max_seconds: float = 15.0) -> str | None:
    """Atajo: graba hasta silencio y devuelve la transcripción."""
    audio = record_until_silence(max_seconds=max_seconds)
    if audio is None:
        return None
    return transcribe(audio)
