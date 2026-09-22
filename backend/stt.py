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
# Equivalentes para los idiomas extra (se activan al despertarlo en ellos).
# Mismo criterio: solo el nombre y el contexto, NADA de títulos de obras.
INITIAL_PROMPT_EN = "A conversation in English with a robot named MECH."
INITIAL_PROMPT_FR = "Une conversation en français avec un robot appelé MECH."
INITIAL_PROMPT_PT = "Uma conversa em português com um robô chamado MECH."

_INITIAL_PROMPTS = {
    "es": INITIAL_PROMPT,
    "en": INITIAL_PROMPT_EN,
    "fr": INITIAL_PROMPT_FR,
    "pt": INITIAL_PROMPT_PT,
}


def _initial_prompt(language: str | None) -> str | None:
    """Prompt de contexto para Whisper, o None si transcribimos "a ciegas".

    Con detección automática de idioma (`language=None`) NO se pasa prompt:
    el texto del prompt sesga la detección hacia el idioma en que está
    escrito, que es justo lo contrario de lo que queremos ahí.
    """
    if not language:
        return None
    return _INITIAL_PROMPTS.get(language, INITIAL_PROMPT)


_model: WhisperModel | None = None
_interrupt_model: WhisperModel | None = None


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


# Filtro anti-aliasing para bajar de la tasa de captura a los 16 kHz de
# Whisper. 63 coeficientes es el punto dulce medido: cuesta ~10 ms por cada
# 3 s de audio en un laptop (~40 ms en la Pi, nada al lado de Whisper) y
# rechaza 30-45 dB MÁS que el filtro de caja que había antes.
#
# Por qué importa: al pasar de 48000 a 16000 Hz, todo lo que esté por encima
# de 8 kHz se PLIEGA dentro de la banda de la voz si no se filtra primero.
# Con el filtro de caja de 3 muestras, un tono de 8.5 kHz (siseo de sala,
# zumbido eléctrico, roce de ropa en el micrófono de solapa) solo perdía 7 dB
# y reaparecía a 7.5 kHz ensuciando la señal. Medido:
#
#     Entrada   Reaparece a   caja (antes)   FIR (ahora)
#      8.5 kHz     7.5 kHz        -7 dB        -18 dB
#     10   kHz     6   kHz        -9 dB        -48 dB
#     12   kHz     4   kHz       -13 dB        -52 dB
#     15   kHz     1   kHz       -25 dB        -56 dB
#
# La banda de la voz (100-5000 Hz) pasa intacta en los dos casos.
_FIR_TAPS = 63
_fir_cache: dict[int, np.ndarray] = {}


def _decimation_fir(factor: int) -> np.ndarray:
    """Pasa-bajos ventaneado para decimar por `factor`, cacheado."""
    h = _fir_cache.get(factor)
    if h is None:
        # Corte en la mitad de la nueva tasa (Nyquist del destino).
        fc = 0.5 / factor
        n = np.arange(_FIR_TAPS) - (_FIR_TAPS - 1) / 2
        h = (np.sinc(2 * fc * n) * np.hamming(_FIR_TAPS)).astype(np.float32)
        h /= h.sum()  # ganancia 1 en continua: no cambia el volumen
        _fir_cache[factor] = h
    return h


def _resample(audio: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Resamplea audio mono float32 de `src_rate` a `dst_rate`.

    Sin dependencias extra (no usamos scipy). Para factores enteros
    (ej. 48000 -> 16000 = 3x) filtra con `_decimation_fir` y decima. Para
    factores no enteros cae a interpolación lineal.
    """
    if src_rate == dst_rate or audio.size == 0:
        return audio
    # Caso entero (el habitual: 48000/16000 = 3, 32000/16000 = 2).
    if src_rate % dst_rate == 0:
        factor = src_rate // dst_rate
        if len(audio) < factor:
            return audio[:0]
        h = _decimation_fir(factor)
        return np.convolve(audio, h, mode="same")[::factor].astype(np.float32)
    # Fallback general: interpolación lineal.
    dst_len = int(round(len(audio) * dst_rate / src_rate))
    if dst_len <= 0:
        return audio[:0]
    x_old = np.linspace(0.0, 1.0, num=len(audio), endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=dst_len, endpoint=False)
    return np.interp(x_new, x_old, audio).astype(np.float32)


def _dc_block(audio: np.ndarray, sample_rate: int, cutoff_hz: float) -> np.ndarray:
    """Quita la continua y el retumbe por debajo de `cutoff_hz`.

    Restar una media móvil = pasa-altos. No es un filtro fino, pero para
    matar offset de continua, zumbido de red y roce de ropa (el micrófono es
    de SOLAPA: va pegado a la camisa) sobra, y con `cumsum` es instantáneo.

    Importa por dos motivos: Whisper trabaja mejor sin continua, y sobre todo
    el piso de ruido del detector de voz se mide con el RMS — una continua
    constante lo infla y deja a MECH sordo para el "ok MECH".
    """
    if cutoff_hz <= 0 or audio.size == 0:
        return audio
    ventana = max(3, int(sample_rate / cutoff_hz))
    if audio.size <= ventana:
        return (audio - float(audio.mean())).astype(np.float32)
    # Media móvil con relleno en los bordes (si no, se comería el principio
    # y el final de la frase, que es justo donde está la primera palabra).
    pad = ventana // 2
    ext = np.pad(audio, (pad, ventana - 1 - pad), mode="edge")
    acum = np.cumsum(np.concatenate(([0.0], ext.astype(np.float64))))
    media = (acum[ventana:] - acum[:-ventana]) / ventana
    return (audio - media[: audio.size]).astype(np.float32)


def _normalize(audio: np.ndarray, target_dbfs: float) -> np.ndarray:
    """Sube (o baja) el audio a un volumen objetivo, sin saturar.

    Es el "AGC" de los teléfonos, en versión simple: Whisper se entrenó con
    audio a un nivel razonable y transcribe peor lo que entra muy bajito. En
    un stand la distancia y el volumen de cada visitante cambian mucho.

    Se mide sobre el percentil 90 de la envolvente, no sobre el total: si se
    midiera el total, una frase con pausas largas quedaría sobre-amplificada.
    Y el resultado se topa para que ningún pico sature.
    """
    if target_dbfs >= 0 or audio.size == 0:
        return audio
    picos = np.abs(audio)
    pico = float(picos.max())
    if pico < 1e-5:
        return audio  # silencio: amplificarlo solo subiría el ruido
    # Nivel de referencia: percentil 90 de la envolvente, que representa la
    # parte sonora y no las pausas.
    ref = float(np.percentile(picos, 90))
    if ref < 1e-5:
        return audio
    objetivo = 10.0 ** (target_dbfs / 20.0)
    ganancia = objetivo / ref
    # Tope 1: no saturar. Tope 2: no amplificar x30 un susurro (sería subir
    # el ruido de sala y regalarle alucinaciones a Whisper).
    ganancia = min(ganancia, 0.97 / pico, 8.0)
    if 0.95 < ganancia < 1.05:
        return audio  # ya estaba bien: no lo tocamos
    return (audio * ganancia).astype(np.float32)


def prepare_for_whisper(audio: np.ndarray, src_rate: int) -> np.ndarray:
    """Deja el audio como Whisper lo quiere: 16 kHz, sin retumbe y a nivel.

    Es la versión mínima de lo que hace la cadena de audio de un teléfono
    (ver docs/AUDIO.md): pasa-altos, remuestreo con anti-aliasing y control
    automático de ganancia. El orden importa: primero se quita el retumbe (si
    no, el normalizador contaría esa energía como señal), después se baja a
    16 kHz y por último se ajusta el nivel.
    """
    audio = _dc_block(audio, src_rate, config.AUDIO_HIGHPASS_HZ)
    audio = _resample(audio, src_rate, WHISPER_SAMPLE_RATE)
    return _normalize(audio, config.AUDIO_TARGET_DBFS)


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


def get_interrupt_model() -> WhisperModel:
    """Modelo aparte para escuchar "oye MECH" MIENTRAS MECH narra.

    Va limitado a `WHISPER_INTERRUPT_THREADS` hilos de CPU (1 por defecto)
    porque compite con el reproductor de audio: con todos los núcleos
    ocupados transcribiendo, la voz de MECH se entrecorta.

    Si no se puede cargar (p. ej. `WHISPER_INTERRUPT_MODEL=tiny` sin
    descargar y en modo offline), se usa el modelo principal y se avisa.
    """
    global _interrupt_model
    if _interrupt_model is None:
        nombre = config.WHISPER_INTERRUPT_MODEL or config.WHISPER_MODEL
        try:
            print(
                f"[STT] Cargando Whisper '{nombre}' para interrupciones "
                f"({config.WHISPER_INTERRUPT_THREADS} hilo/s de CPU)..."
            )
            _interrupt_model = WhisperModel(
                nombre,
                device="cpu",
                compute_type="int8",
                cpu_threads=max(1, config.WHISPER_INTERRUPT_THREADS),
                local_files_only=config.WHISPER_OFFLINE,
            )
        except Exception as e:
            print(
                f"[STT] No pude cargar '{nombre}' para interrupciones ({e}). "
                "Uso el modelo principal (puede entrecortar el audio; si pasa, "
                "poné WHISPER_INTERRUPT_MODEL vacío o descargá ese modelo una "
                "vez con WHISPER_OFFLINE=false)."
            )
            _interrupt_model = get_model()
    return _interrupt_model


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
    """RMS normalizado (0..1) de un frame int16, SIN la componente continua.

    Restar la media del frame es un pasa-altos pobre pero gratis, y aquí es
    justo lo que hace falta: si el micrófono trae offset de continua (los
    receptores USB baratos suelen traerlo), el RMS crudo lo cuenta como
    "ruido ambiente", el piso sube y MECH se queda sordo para el "ok MECH".
    Es el mismo síntoma que el equipo peleó en la olimpiada subiendo el
    umbral a mano.
    """
    samples = np.frombuffer(frame, dtype=np.int16).astype(np.float32)
    if samples.size == 0:
        return 0.0
    samples = samples - samples.mean()
    return float(np.sqrt(np.mean(samples * samples)) / 32768.0)


def probe_microphone(seconds: float = 1.0) -> dict:
    """Abre el micrófono un momento y MIDE lo que entra.

    Por qué existe: cuando alguien dice "MECH está sordo, es como si no
    tuviera micrófono", hay tres causas muy distintas y desde fuera se ven
    igual — el dispositivo equivocado, el micrófono apagado/silenciado, o un
    umbral mal puesto. Esto las separa con un número, y corre en CADA
    arranque del bucle de voz, así que el panel lo dice solo.

    Devuelve un dict con:
      - `device`: lo que pidió el .env (None = el que tenga el sistema puesto)
      - `nombre`: el dispositivo que de VERDAD se abrió
      - `rate`: la tasa de captura
      - `nivel`: RMS medio (0..1) de lo que se oyó
      - `pico`: RMS máximo
      - `frames`: cuántos bloques llegaron (0 = el micrófono no da datos)
      - `error`: texto del fallo, si no se pudo abrir

    No lanza excepciones: un fallo aquí NO puede impedir que MECH arranque.
    """
    info: dict = {
        "device": config.AUDIO_INPUT_DEVICE.strip() or None,
        "nombre": None,
        "rate": config.AUDIO_SAMPLE_RATE,
        "nivel": 0.0,
        "pico": 0.0,
        "frames": 0,
        "error": None,
    }
    try:
        dev = _resolve_input_device()
        try:
            info["nombre"] = sd.query_devices(dev, "input").get("name")
        except Exception:
            pass

        q: queue.Queue = queue.Queue()

        def cb(indata, frames, time_info, status):
            q.put(bytes(indata))

        suma = 0.0
        with sd.RawInputStream(
            samplerate=config.AUDIO_SAMPLE_RATE,
            blocksize=FRAME_BYTES // 2,
            dtype="int16",
            channels=1,
            device=dev,
            callback=cb,
        ):
            fin = time.monotonic() + max(0.2, seconds)
            while time.monotonic() < fin:
                try:
                    frame = q.get(timeout=0.3)
                except queue.Empty:
                    continue
                if len(frame) < FRAME_BYTES:
                    continue
                rms = _frame_rms(frame[:FRAME_BYTES])
                suma += rms
                info["frames"] += 1
                info["pico"] = max(info["pico"], rms)
        if info["frames"]:
            info["nivel"] = suma / info["frames"]
    except Exception as e:
        info["error"] = str(e)
    return info


def record_until_silence(
    max_seconds: float = 15.0,
    on_phase: Callable[[str], None] | None = None,
    cancel_event=None,
    max_utterance_seconds: float | None = None,
    on_level: Callable[[float, float, bool], None] | None = None,
    silence_timeout: float | None = None,
    energy_factor: float | None = None,
    floor_average: bool = False,
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
        energy_factor: cuánto más fuerte que el ruido de fondo debe sonar la
            voz para empezar a grabar (None = config.VAD_ENERGY_FACTOR). El
            listener de interrupción usa uno MÁS ALTO: mientras MECH habla,
            su propio parlante dispararía la grabación sin parar.
        floor_average: cómo sigue el piso de ruido al ambiente.
            False (normal) = baja rápido y sube lento, así se queda en los
            silencios y cualquier voz destaca — perfecto para escuchar a
            alguien en una sala tranquila.
            True (mientras MECH narra) = el piso SE PONE al nivel del
            parlante, y solo pasa quien hable claramente por encima. Es la
            clave para no transcribirse a sí mismo: con el piso pegado a los
            silencios (modo normal), los picos de su propia voz lo superan
            siempre por mucho. Funciona en dos tiempos: ~1 s CALIBRANDO
            (converge rápido y no dispara) y después seguimiento lento que
            IGNORA lo que esté por encima del umbral — si no, la propia voz
            del visitante subiría el listón y se quedaría sin oírlo.
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
    # Modo "media" (mientras MECH narra): ~1 s de calibración antes de poder
    # disparar, para que el piso se ponga al nivel del parlante.
    frames_vistos = 0
    frames_calibracion = 33 if floor_average else 0
    suma_calibracion = 0.0
    start_factor = max(
        1.2, config.VAD_ENERGY_FACTOR if energy_factor is None else energy_factor
    )
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
            frames_vistos += 1
            calibrando = frames_vistos <= frames_calibracion
            if noise_floor is None:
                noise_floor = max(rms, 1e-4)
            elif not triggered:
                # Solo medimos ambiente cuando NO estamos grabando voz.
                if floor_average and calibrando:
                    # MEDIA de verdad (no exponencial): la voz alterna picos y
                    # pausas, y una media exponencial se quedaría en el último
                    # tramo en vez de en el nivel medio del parlante.
                    suma_calibracion += rms
                    noise_floor = max(suma_calibracion / frames_vistos, 1e-4)
                    if on_level:
                        try:
                            on_level(rms, noise_floor * start_factor, False)
                        except Exception:
                            pass
                    continue
                if not floor_average:
                    alpha = 0.20 if rms < noise_floor else 0.02
                elif rms <= noise_floor * start_factor:
                    alpha = 0.03  # seguimiento lento del ambiente
                else:
                    alpha = 0.0   # pico: NO subimos el listón por una voz
                noise_floor += (rms - noise_floor) * alpha
                noise_floor = max(noise_floor, 1e-4)

            loud = rms > noise_floor * start_factor and not calibrando
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
    # Pasa-altos + bajada a 16 kHz (la tasa que Whisper EXIGE; sin esto
    # malinterpreta el audio y transcribe basura) + nivel. Ver docs/AUDIO.md.
    return prepare_for_whisper(audio_f32, config.AUDIO_SAMPLE_RATE)


def transcribe(
    audio: np.ndarray,
    language: str | None = None,
    model: WhisperModel | None = None,
) -> str:
    """Transcribe audio mono float32 a texto.

    `language`: código ISO ("es", "en", "fr", "pt"). Si es None usa el idioma
    ACTIVO de MECH (`lang.whisper_language()`), que es español salvo que lo
    hayan despertado en otro idioma.

    `model`: instancia de Whisper a usar. None = la principal. El listener de
    interrupción pasa la suya (limitada en CPU) para no entrecortar la voz.
    """
    texto, _ = _transcribe(audio, language or lang.whisper_language(), model)
    return texto


def transcribe_any(
    audio: np.ndarray,
    model: WhisperModel | None = None,
) -> tuple[str, str | None]:
    """Transcribe dejando que Whisper DETECTE el idioma solo.

    Se usa para el despertar: en reposo escuchamos en español, así que
    «bonjour MECH» o «bom dia MECH» pueden salir deformados. En vez de
    reintentar idioma por idioma (con cuatro idiomas serían 3 pasadas más y
    la Pi tardaría ~10 s en volver a escuchar), se re-transcribe UNA sola vez
    a ciegas y se compara el texto contra las listas de despertar de todos.

    Devuelve `(texto, idioma detectado)`; el idioma es informativo — quien
    decide es el matcher de `voice_phrases`.
    """
    return _transcribe(audio, None, model)


def _transcribe(
    audio: np.ndarray,
    language: str | None,
    model: WhisperModel | None = None,
) -> tuple[str, str | None]:
    """Motor común de transcripción. `language=None` = detección automática."""
    principal = get_model()
    model = model or principal
    # El modelo de interrupciones va a beam 1 (ahí manda el retardo); el
    # principal explora más hipótesis, que es lo que sube el acierto en las
    # frases cortas con ruido de un stand.
    beam = (
        config.WHISPER_BEAM_SIZE if model is principal
        else config.WHISPER_INTERRUPT_BEAM_SIZE
    )
    segments, info = model.transcribe(
        audio,
        language=language,
        beam_size=max(1, beam),
        vad_filter=False,  # ya pre-filtramos con webrtcvad
        initial_prompt=_initial_prompt(language),  # ayuda a reconocer "MECH"
        # Defensas contra alucinaciones cuando el audio entra con ruido:
        condition_on_previous_text=False,  # no arrastrar contexto entre turnos
        no_speech_threshold=0.6,  # descarta tramos sin habla clara
        log_prob_threshold=-1.0,  # descarta transcripciones de baja confianza
    )
    texto = " ".join(seg.text.strip() for seg in segments).strip()
    return texto, getattr(info, "language", None)


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
