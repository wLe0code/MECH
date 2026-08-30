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
import os
import queue
import sys
import time
from typing import Callable, Iterator

import numpy as np
import sounddevice as sd
import webrtcvad
from faster_whisper import WhisperModel

import config
import lang


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
# Equivalente para el modo inglés (se activa con "wake up MECH"). Mismo
# criterio: solo el nombre y el contexto, NADA de títulos de obras.
INITIAL_PROMPT_EN = "A conversation in English with a robot named MECH."


def _initial_prompt(language: str) -> str:
    return INITIAL_PROMPT_EN if language == "en" else INITIAL_PROMPT


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
    """Carga perezosa del modelo Whisper. En Pi 5 usa CPU + int8.

    Con WHISPER_OFFLINE=true (default) usa el modelo YA DESCARGADO del disco
    y NO toca internet: ni descarga ni chequea actualizaciones en Hugging
    Face. La descarga (~150 MB) ocurre UNA sola vez, la primera vez que se
    corre con red; después el modelo queda cacheado y se carga siempre local.
    """
    global _model
    if _model is None:
        # Las variables de entorno son un refuerzo, pero el interruptor que
        # de verdad garantiza "solo disco" es local_files_only (se lo pasa
        # directo a la descarga, sin depender de cuándo se leyó el entorno).
        if config.WHISPER_OFFLINE:
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
        modo = "solo disco (offline)" if config.WHISPER_OFFLINE else "con descarga si falta"
        print(f"[STT] Cargando faster-whisper '{config.WHISPER_MODEL}' — {modo}...")
        try:
            _model = WhisperModel(
                config.WHISPER_MODEL,
                device="cpu",
                compute_type="int8",  # menos RAM, suficiente para Pi 5
                local_files_only=config.WHISPER_OFFLINE,  # NO toca la red
            )
        except Exception as e:
            # Caso típico: WHISPER_OFFLINE=true pero el modelo aún no se ha
            # descargado nunca. Damos un mensaje claro en vez de un error
            # de red críptico.
            if config.WHISPER_OFFLINE:
                raise RuntimeError(
                    f"No encontré el modelo Whisper '{config.WHISPER_MODEL}' en "
                    "el disco y WHISPER_OFFLINE=true (no descarga). Corré UNA "
                    "vez con internet y WHISPER_OFFLINE=false para descargarlo, "
                    "y después volvé a poner true."
                ) from e
            raise
        print("[STT] Modelo listo (cargado desde disco, sin internet).")
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


def _frame_rms(frame: bytes) -> float:
    """RMS normalizado (0..1) de un frame int16."""
    samples = np.frombuffer(frame, dtype=np.int16).astype(np.float32)
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(samples * samples)) / 32768.0)


def record_until_silence(
    max_seconds: float = 15.0,
    on_phase: Callable[[str], None] | None = None,
    cancel_event=None,
    max_utterance_seconds: float | None = None,
    on_level: Callable[[float, float, bool], None] | None = None,
    silence_timeout: float | None = None,
) -> np.ndarray | None:
    """Graba desde el micrófono hasta detectar silencio prolongado.

    Devuelve un array float32 mono a WHISPER_SAMPLE_RATE Hz, o None si nunca
    detectó voz dentro del tiempo máximo.

    Detección HÍBRIDA (clave para ambientes ruidosos como la olimpiada):
    el detector mide continuamente el piso de ruido del ambiente (RMS) y solo
    considera "voz" un frame si webrtcvad dice que es voz Y su amplitud supera
    `piso * VAD_ENERGY_FACTOR`. El fin de la frase se detecta cuando la
    amplitud CAE de vuelta cerca del piso de ruido — así el murmullo del
    público no mantiene la grabación abierta para siempre ni dispara
    grabaciones fantasma.

    Args:
        max_seconds: tiempo máximo de espera por voz.
        on_phase: callback opcional que recibe la fase actual del micrófono
            para que el panel la muestre en vivo:
              - "waiting": micrófono abierto, esperando que la persona hable
                (esta es la señal para decirle al juez "ya puedes hablar").
              - "listening": se detectó voz, grabando hasta que haya silencio.
        max_utterance_seconds: tope de duración de la grabación una vez que
            arrancó la voz (None = sin tope). En reposo se usa un tope corto
            porque "ok MECH" dura ~1s y queremos revisarlo rápido.
        on_level: callback opcional (rms, umbral, grabando) ~cada frame, para
            mostrar el nivel del micrófono en vivo en el panel.
        silence_timeout: segundos de silencio que dan por terminada la frase
            (None = config.VAD_SILENCE_TIMEOUT). El listener de interrupción
            usa uno más corto: solo espera "oye MECH", y cada décima cuenta
            porque MECH sigue hablando mientras tanto. Este valor también
            marca lo rápido que DISPARA (pide media ventana de voz).
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

    silencio = config.VAD_SILENCE_TIMEOUT if silence_timeout is None else silence_timeout
    silence_frames_needed = max(4, int(silencio * 1000 / FRAME_DURATION_MS))
    ring_buffer = collections.deque(maxlen=silence_frames_needed)
    voiced_frames: list[bytes] = []
    triggered = False
    start = time.monotonic()
    triggered_at = 0.0

    # Piso de ruido adaptativo: baja rápido (sigue al ambiente cuando se
    # calma) y sube lento (un grito puntual no lo arrastra hacia arriba).
    noise_floor: float | None = None
    start_factor = max(1.2, config.VAD_ENERGY_FACTOR)
    # El umbral para CORTAR es más bajo que el de arranque: basta con que la
    # amplitud caiga significativamente para considerar que terminó la frase.
    end_factor = 1.0 + (start_factor - 1.0) * 0.5

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
            # Cancelación externa (ej. terminó la narración): soltamos el mic ya.
            if cancel_event is not None and cancel_event.is_set():
                return None
            if time.monotonic() - start > max_seconds:
                break

            rms = _frame_rms(frame)
            if noise_floor is None:
                noise_floor = max(rms, 1e-4)
            elif not triggered:
                # Solo medimos ambiente cuando NO estamos grabando voz.
                alpha = 0.20 if rms < noise_floor else 0.02
                noise_floor += (rms - noise_floor) * alpha
                noise_floor = max(noise_floor, 1e-4)

            loud = rms > noise_floor * start_factor
            vad_speech = vad.is_speech(frame, config.AUDIO_SAMPLE_RATE)
            is_speech = vad_speech and loud
            # Para terminar: o el VAD ya no oye voz, o la amplitud cayó cerca
            # del piso de ruido (la "caída de onda" que marca el fin).
            still_talking = vad_speech and rms > noise_floor * end_factor

            if on_level:
                try:
                    on_level(rms, noise_floor * start_factor, triggered)
                except Exception:
                    pass

            if not triggered:
                ring_buffer.append((frame, is_speech))
                num_voiced = sum(1 for _, sp in ring_buffer if sp)
                if num_voiced > 0.5 * ring_buffer.maxlen:
                    triggered = True
                    triggered_at = time.monotonic()
                    _phase("listening")  # grabando la voz del usuario
                    print("[STT] Detectada voz.")
                    voiced_frames.extend(f for f, _ in ring_buffer)
                    ring_buffer.clear()
            else:
                voiced_frames.append(frame)
                ring_buffer.append((frame, still_talking))
                num_unvoiced = sum(1 for _, sp in ring_buffer if not sp)
                if num_unvoiced > 0.9 * ring_buffer.maxlen:
                    print("[STT] Fin de voz (amplitud cayó al piso de ruido).")
                    break
                if (
                    max_utterance_seconds is not None
                    and time.monotonic() - triggered_at > max_utterance_seconds
                ):
                    print("[STT] Tope de duración alcanzado; transcribiendo.")
                    break

    if not voiced_frames:
        return None

    pcm_bytes = b"".join(voiced_frames)
    audio_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
    audio_f32 = audio_int16.astype(np.float32) / 32768.0
    # Bajamos de la tasa de captura (ej. 48000) a la que Whisper exige (16000).
    # Sin esto, Whisper malinterpreta el audio y transcribe basura.
    return _resample(audio_f32, config.AUDIO_SAMPLE_RATE, WHISPER_SAMPLE_RATE)


def transcribe(audio: np.ndarray, language: str | None = None) -> str:
    """Transcribe audio mono float32 a texto.

    `language`: código ISO ("es", "en"). Si es None usa el idioma ACTIVO de
    MECH (`lang.whisper_language()`), que es español salvo que lo hayan
    despertado con "wake up MECH". Se pasa explícito en el bucle de voz para
    reintentar en inglés la frase de despertar.
    """
    lang_code = language or lang.whisper_language()
    model = get_model()
    segments, _ = model.transcribe(
        audio,
        language=lang_code,
        beam_size=1,  # más rápido; suficiente para frases cortas
        vad_filter=False,  # ya pre-filtramos con webrtcvad
        initial_prompt=_initial_prompt(lang_code),  # ayuda a reconocer "MECH"
        # Defensas contra alucinaciones cuando el audio entra con ruido:
        condition_on_previous_text=False,  # no arrastrar contexto entre turnos
        no_speech_threshold=0.6,  # descarta tramos sin habla clara
        log_prob_threshold=-1.0,  # descarta transcripciones de baja confianza
    )
    return " ".join(seg.text.strip() for seg in segments).strip()


def listen_once(
    max_seconds: float = 15.0,
    on_phase: Callable[[str], None] | None = None,
    cancel_event=None,
    max_utterance_seconds: float | None = None,
    on_level: Callable[[float, float, bool], None] | None = None,
    language: str | None = None,
) -> str | None:
    """Atajo: graba hasta silencio y devuelve la transcripción.

    `on_phase` recibe "waiting"/"listening" durante la grabación y
    "transcribing" mientras Whisper convierte el audio a texto.
    `cancel_event`: si se activa, aborta la escucha y devuelve None.
    `max_utterance_seconds`/`on_level`: ver record_until_silence().
    `language`: idioma para transcribir (None = el idioma activo de MECH).
    """
    audio = record_until_silence(
        max_seconds=max_seconds,
        on_phase=on_phase,
        cancel_event=cancel_event,
        max_utterance_seconds=max_utterance_seconds,
        on_level=on_level,
    )
    if audio is None:
        return None
    if on_phase:
        try:
            on_phase("transcribing")
        except Exception:
            pass
    return transcribe(audio, language=language)
