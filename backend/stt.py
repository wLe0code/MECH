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
from typing import Callable, Iterator

import numpy as np
import sounddevice as sd
import webrtcvad
from faster_whisper import WhisperModel

import config


# webrtcvad solo acepta frames de 10, 20 o 30 ms a 8/16/32/48 kHz.
# `config.AUDIO_SAMPLE_RATE` es la tasa de CAPTURA del micrófono (la que el
# hardware soporta; el Steren WXMH/MIC-9010 pide 48000). webrtcvad acepta
# 8/16/32/48 kHz, así que la usamos tal cual para el VAD en vivo.
FRAME_DURATION_MS = 30
FRAME_BYTES = int(config.AUDIO_SAMPLE_RATE * FRAME_DURATION_MS / 1000) * 2  # int16

# Tasa que faster-whisper espera SIEMPRE cuando se le pasa un array de numpy.
# Whisper NO resamplea arrays: si le das audio a otra tasa lo interpreta mal
# (a 48 kHz lo "oye" 3x más rápido y agudo → transcribe basura y alucina).
# Por eso capturamos a AUDIO_SAMPLE_RATE y resampleamos a esto antes de
# transcribir. Si ambas son iguales (16000), el resample es un no-op.
WHISPER_SAMPLE_RATE = 16000

# Contexto mínimo que se le pasa a Whisper para reconocer el nombre "MECH".
# IMPORTANTE: NO listar aquí los títulos de las obras. Si el audio entra con
# ruido o cortado, Whisper tiende a "alucinar" y devolver justo lo que aparece
# en este prompt; si listáramos las obras, respondería esas obras sin que el
# usuario las haya pedido.
INITIAL_PROMPT = "Conversación en español con un robot llamado MECH."

_model: WhisperModel | None = None


def _resolve_input_device() -> int | str | None:
    """Dispositivo de micrófono configurado (índice o nombre), o None=default.

    El mic del proyecto es el Steren MIC-9010 (receptor USB); la C930e queda
    solo para video. Se configura con AUDIO_INPUT_DEVICE en .env.
    """
    dev = config.AUDIO_INPUT_DEVICE.strip()
    if not dev:
        return None
    try:
        return int(dev)  # índice numérico
    except ValueError:
        return dev  # nombre (sounddevice acepta coincidencia parcial)


def _resample(audio: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Resamplea audio mono float32 de `src_rate` a `dst_rate`.

    Sin dependencias extra (no usamos scipy). Para factores enteros
    (ej. 48000 -> 16000 = 3x) hace decimación con un filtro de caja simple
    que evita aliasing lo suficiente para reconocimiento de voz. Para
    factores no enteros cae a interpolación lineal.
    """
    if src_rate == dst_rate or audio.size == 0:
        return audio
    # Caso entero (el habitual: 48000/16000 = 3, 32000/16000 = 2).
    if src_rate % dst_rate == 0:
        factor = src_rate // dst_rate
        n = (len(audio) // factor) * factor
        if n == 0:
            return audio[:0]
        # Promedio de cada bloque de `factor` muestras = filtro anti-alias + decimación.
        return audio[:n].reshape(-1, factor).mean(axis=1).astype(np.float32)
    # Fallback general: interpolación lineal.
    dst_len = int(round(len(audio) * dst_rate / src_rate))
    if dst_len <= 0:
        return audio[:0]
    x_old = np.linspace(0.0, 1.0, num=len(audio), endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=dst_len, endpoint=False)
    return np.interp(x_new, x_old, audio).astype(np.float32)


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


def record_until_silence(
    max_seconds: float = 15.0,
    on_phase: Callable[[str], None] | None = None,
) -> np.ndarray | None:
    """Graba desde el micrófono hasta detectar silencio prolongado.

    Devuelve un array float32 mono a WHISPER_SAMPLE_RATE Hz, o None si nunca
    detectó voz dentro del tiempo máximo.

    Args:
        max_seconds: tiempo máximo de espera por voz.
        on_phase: callback opcional que recibe la fase actual del micrófono
            para que el panel la muestre en vivo:
              - "waiting": micrófono abierto, esperando que la persona hable
                (esta es la señal para decirle al juez "ya puedes hablar").
              - "listening": se detectó voz, grabando hasta que haya silencio.
    """
    def _phase(p: str) -> None:
        if on_phase:
            try:
                on_phase(p)
            except Exception:
                pass

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
        device=_resolve_input_device(),  # Steren MIC-9010 si está configurado
        callback=callback,
    ):
        _phase("waiting")  # micrófono abierto: ya se puede hablar
        for frame in _frame_generator(audio_q):
            if time.monotonic() - start > max_seconds:
                break

            is_speech = vad.is_speech(frame, config.AUDIO_SAMPLE_RATE)

            if not triggered:
                ring_buffer.append((frame, is_speech))
                num_voiced = sum(1 for _, sp in ring_buffer if sp)
                if num_voiced > 0.5 * ring_buffer.maxlen:
                    triggered = True
                    _phase("listening")  # grabando la voz del usuario
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
    audio_f32 = audio_int16.astype(np.float32) / 32768.0
    # Bajamos de la tasa de captura (ej. 48000) a la que Whisper exige (16000).
    # Sin esto, Whisper malinterpreta el audio y transcribe basura.
    return _resample(audio_f32, config.AUDIO_SAMPLE_RATE, WHISPER_SAMPLE_RATE)


def transcribe(audio: np.ndarray) -> str:
    """Transcribe audio mono float32 a texto."""
    model = get_model()
    segments, _ = model.transcribe(
        audio,
        language=config.WHISPER_LANGUAGE,
        beam_size=1,  # más rápido; suficiente para frases cortas
        vad_filter=False,  # ya pre-filtramos con webrtcvad
        initial_prompt=INITIAL_PROMPT,  # ayuda a reconocer el nombre "MECH"
        # Defensas contra alucinaciones cuando el audio entra con ruido:
        condition_on_previous_text=False,  # no arrastrar contexto entre turnos
        no_speech_threshold=0.6,  # descarta tramos sin habla clara
        log_prob_threshold=-1.0,  # descarta transcripciones de baja confianza
    )
    return " ".join(seg.text.strip() for seg in segments).strip()


def listen_once(
    max_seconds: float = 15.0,
    on_phase: Callable[[str], None] | None = None,
) -> str | None:
    """Atajo: graba hasta silencio y devuelve la transcripción.

    `on_phase` recibe "waiting"/"listening" durante la grabación y
    "transcribing" mientras Whisper convierte el audio a texto.
    """
    audio = record_until_silence(max_seconds=max_seconds, on_phase=on_phase)
    if audio is None:
        return None
    if on_phase:
        try:
            on_phase("transcribing")
        except Exception:
            pass
    return transcribe(audio)
