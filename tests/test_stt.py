"""Backend de voz (stt.py): framing, vigilia del worker, errores, resolución
de dispositivo, rescan ALSA, probe y el flujo completo de record_until_silence
con VAD — todo por el camino in-process (el aislamiento por subproceso se
prueba en test_mic_worker.py con hijos reales).
"""
from __future__ import annotations

import time
from itertools import islice

import numpy as np
import pytest

import config
import sounddevice as sd
import stt
import webrtcvad


# ── _frame_generator ──────────────────────────────────────────────────────
def test_frames_se_reencuadran_como_antes():
    gen = stt._frame_generator(iter([b"a" * 1000, b"b" * stt.FRAME_BYTES, b"c" * 1000]))
    frames = list(gen)
    assert len(frames) == 1 and len(frames[0]) == stt.FRAME_BYTES

    gen2 = stt._frame_generator(iter([b"x" * stt.FRAME_BYTES, None, b"y" * stt.FRAME_BYTES]))
    assert len(list(gen2)) == 2


# ── _worker_chunks (vigilia) ─────────────────────────────────────────────
class _MicQueMuere:
    alive = True

    def read_chunk(self, timeout):
        raise stt.MicProcessCrashed("El proceso del micrófono murió (código -6).")


class _MicSilencioso:
    alive = True

    def read_chunk(self, timeout):
        time.sleep(0.02)
        return None


class _MicQueEntrega:
    alive = True

    def read_chunk(self, timeout):
        return b"z" * stt.FRAME_BYTES


def test_muerte_del_hijo_es_error_recuperable():
    with pytest.raises(stt.MicProcessCrashed):
        list(stt._worker_chunks(_MicQueMuere()))


def test_mic_abierto_pero_mudo_se_declara_caido():
    # Antes esto colgaba la escucha para siempre; ahora es un error recuperable.
    t0 = time.monotonic()
    with pytest.raises(stt.MicProcessCrashed) as ei:
        list(stt._worker_chunks(_MicSilencioso(), idle_limit=0.5, gracia_inicial=0))
    assert time.monotonic() - t0 < 5.0
    assert ei.value.silencioso is True
    assert "NO llega audio" in str(ei.value)


def test_gracia_inicial_aguanta_arranque_lento():
    """Recién abierto, el receptor puede tardar en transmitir (bajón del USB):
    la gracia inicial evita cortar el intento justo cuando iba a arrancar."""
    class _MicQueArrancaTarde:
        alive = True
        inicio = time.monotonic()

        def read_chunk(self, timeout):
            if time.monotonic() - self.inicio < 0.6:
                return None
            return b"z" * stt.FRAME_BYTES

    chunks = list(islice(
        stt._worker_chunks(_MicQueArrancaTarde(), idle_limit=0.3, gracia_inicial=1.0),
        2,
    ))
    assert len(chunks) == 2, "con gracia inicial el arranque lento no se corta"


def test_idle_sin_gracia_corta_a_tiempo():
    with pytest.raises(stt.MicProcessCrashed):
        list(stt._worker_chunks(_MicSilencioso(), idle_limit=0.4, gracia_inicial=0))


def test_flujo_normal_entrega_chunks():
    chunks = list(islice(stt._worker_chunks(_MicQueEntrega(), idle_limit=5.0), 3))
    assert len(chunks) == 3


# ── is_audio_device_error (el bucle de voz decide acá) ───────────────────
def test_errores_de_dispositivo_se_clasifican_bien():
    assert stt.is_audio_device_error(stt.MicProcessCrashed("x")) is True
    assert stt.is_audio_device_error(sd.PortAudioError("Error opening stream")) is True
    assert stt.is_audio_device_error(ValueError("PaErrorCode -9999")) is True
    assert stt.is_audio_device_error(RuntimeError("otra cosa")) is False


def test_crash_silencioso_se_distingue_para_la_guia():
    assert stt.MicProcessCrashed("a").silencioso is False
    assert stt.MicProcessCrashed("a", silencioso=True).silencioso is True


# ── _resolve_input_device ─────────────────────────────────────────────────
def test_dev_vacio_deja_al_sistema(monkeypatch):
    monkeypatch.setattr(config, "AUDIO_INPUT_DEVICE", "")
    assert stt._resolve_input_device() is None


def test_dev_por_indice_valido(monkeypatch):
    monkeypatch.setattr(config, "AUDIO_INPUT_DEVICE", "0")
    assert stt._resolve_input_device() == 0


def test_dev_por_nombre(monkeypatch):
    monkeypatch.setattr(config, "AUDIO_INPUT_DEVICE", "WXMH mini")
    assert stt._resolve_input_device() == 0


def test_indice_que_ya_no_existe_busca_solo(monkeypatch):
    monkeypatch.setattr(config, "AUDIO_INPUT_DEVICE", "8")
    assert stt._resolve_input_device() == 2  # el Steren (nunca la webcam)


def test_la_webcam_nunca_se_elige(monkeypatch):
    # el índice 1 es la C930e (cámara): aunque se pida, se busca otro.
    monkeypatch.setattr(config, "AUDIO_INPUT_DEVICE", "C930e")
    dev = stt._resolve_input_device()
    assert dev != 1
    assert dev in (0, 2)


# ── reset_audio / rescan ALSA ─────────────────────────────────────────────
def test_reset_audio_reinicializa_portaudio():
    antes = sd.INIT_COUNT
    assert stt.reset_audio() is True
    assert sd.INIT_COUNT == antes + 1


def test_rescan_solo_cuando_cambio_alsa(monkeypatch):
    llamadas = {"n": 0}

    def reset_fake():
        llamadas["n"] += 1
        return True

    monkeypatch.setattr(stt, "reset_audio", reset_fake)
    monkeypatch.setattr(stt, "_ultimo_alsa", "SNAPSHOT-INICIAL")

    assert stt._rescan_si_cambio_alsa() is True
    assert llamadas["n"] == 1
    assert stt._ultimo_alsa == stt._snapshot_alsa()

    assert stt._rescan_si_cambio_alsa() is False
    assert llamadas["n"] == 1, "sin cambios no se vuelve a reinicializar"


def test_rescan_que_falla_se_reintenta(monkeypatch):
    llamadas = {"n": 0}

    def reset_fake():
        llamadas["n"] += 1
        return False  # había un stream ocupado: no pudo rescanear

    monkeypatch.setattr(stt, "reset_audio", reset_fake)
    monkeypatch.setattr(stt, "_ultimo_alsa", "SNAPSHOT-INICIAL")

    assert stt._rescan_si_cambio_alsa() is False
    assert stt._ultimo_alsa == "SNAPSHOT-INICIAL", "no se marca hasta rescanear"
    assert stt._rescan_si_cambio_alsa() is False
    assert llamadas["n"] == 2, "el rescan pendiente se reintenta en la próxima"

    monkeypatch.setattr(stt, "_ultimo_alsa", stt._snapshot_alsa())
    assert stt._rescan_si_cambio_alsa() is False
    assert llamadas["n"] == 2


# ── probe_microphone ──────────────────────────────────────────────────────
def test_probe_ok_mide_audio(mic_en_proceso):
    sd.set_amp(0.3)
    info = stt.probe_microphone(0.25)
    assert info["error"] is None
    assert info["frames"] > 0
    assert info["nivel"] > 0.01
    assert info["pico"] > 0.01


def test_probe_abre_mudo_queda_en_cero(mic_en_proceso):
    sd.set_amp(0.0)  # "receptor encendido pero micrófono apagado": silencio
    info = stt.probe_microphone(0.3)
    assert info["error"] is None
    assert info["frames"] > 0
    assert info["pico"] == 0.0


def test_probe_falla_abrir_devuelve_error_no_excepcion(mic_en_proceso):
    sd.FAIL_OPEN = sd.PortAudioError("Error opening RawInputStream: no such device")
    info = stt.probe_microphone(0.2)
    assert info["frames"] == 0
    assert info["error"]


def test_probe_con_crash_del_hijo_devuelve_error(mic_en_proceso, monkeypatch):
    # El hijo (aislado) murió por el bug de ALSA: la probe no puede reventar,
    # devuelve el motivo en el dict (el preflight y el panel lo muestran).
    class MicRoto:
        alive = True

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read_chunk(self, timeout):
            raise stt.MicProcessCrashed("El proceso del micrófono murió (código -6).")

    monkeypatch.setattr(stt, "abrir_mic_stream", lambda dev: MicRoto())
    info = stt.probe_microphone(0.2)
    assert info["frames"] == 0
    assert "murió" in info["error"]


# ── record_until_silence: flujo completo con VAD simulado ─────────────────
def _simular_voz(cuadros_silencio=2, cuadros_voz=12):
    """Deja el stub en modo "voz": primero silencio (para que el piso de
    ruido arranque bajo, como pasa en la realidad), después N cuadros con
    amplitud, y vuelve el silencio (corte de frase)."""
    llamadas = {"n": 0}
    ini = cuadros_silencio
    fin = cuadros_silencio + cuadros_voz

    def amp_por_frame():
        llamadas["n"] += 1
        return 0.4 if ini < llamadas["n"] <= fin else 0.0

    sd.set_amp(amp_por_frame)
    webrtcvad.VAD_RESULT = lambda: ini < llamadas["n"] <= fin
    return llamadas


def test_escucha_voz_detecta_corte_y_devuelve_audio(mic_en_proceso):
    _simular_voz()
    fases = []
    audio = stt.record_until_silence(
        max_seconds=10.0,
        on_phase=fases.append,
        silence_timeout=0.3,  # ventanas chicas → la prueba es rápida
    )
    assert audio is not None, "debió detectar voz"
    assert audio.dtype == np.float32
    assert len(audio) > 0
    assert "waiting" in fases and "listening" in fases
    assert float(np.abs(audio).max()) > 0.01  # la voz pasó normalizada


def test_silencio_puro_agota_max_seconds(mic_en_proceso):
    sd.set_amp(0.0)
    webrtcvad.VAD_RESULT = False
    assert stt.record_until_silence(max_seconds=0.4) is None


def test_cancel_event_suelta_el_mic_inmediatamente(mic_en_proceso):
    import threading

    sd.set_amp(0.3)
    webrtcvad.VAD_RESULT = True
    cancel = threading.Event()
    cancel.set()
    assert stt.record_until_silence(max_seconds=5.0, cancel_event=cancel) is None


def test_mic_que_muere_propaga_error_recuperable(mic_en_proceso, monkeypatch):
    # Con el hijo muerto, la escucha NO se congela: lanza MicProcessCrashed,
    # que es justo lo que el bucle de voz trata como error de dispositivo.
    class MicRoto:
        alive = True

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read_chunk(self, timeout):
            raise stt.MicProcessCrashed("El proceso del micrófono murió (código -6).")

    monkeypatch.setattr(stt, "abrir_mic_stream", lambda dev: MicRoto())
    with pytest.raises(stt.MicProcessCrashed):
        stt.record_until_silence(max_seconds=2.0)