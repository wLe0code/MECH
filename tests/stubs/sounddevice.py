"""Stub controlable de sounddevice para las pruebas sin hardware.

Comportamiento:
- `query_devices()` devuelve `DEVICE_LIST` (leer/reescribir desde los tests).
- `RawInputStream` arranca un hilo que alimenta el callback con int16:
    * amplitud = módulo global `SET_AMP(v)` (0 = silencio digital).
    * si el env `MECH_SD_FAIL_OPEN` está seteado (o `FAIL_OPEN` no es None),
      __init__ lanza PortAudioError — simula "no pude abrir el micrófono".
- Lleva contadores globales (`INIT_COUNT`) para verificar `reset_audio()`.
"""
from __future__ import annotations

import os
import threading
import time

import numpy as np

PortAudioError = type("PortAudioError", (Exception,), {})

DEVICE_LIST = [
    {"name": "WXMH mini: USB Audio (hw:2,0)", "max_input_channels": 2, "max_output_channels": 0},
    {"name": "C930e (camera)", "max_input_channels": 1, "max_output_channels": 0},
    {"name": "Steren MIC-9010: USB PnP (hw:1,0)", "max_input_channels": 1, "max_output_channels": 0},
    {"name": "Built-in Audio (hw:0,0)", "max_input_channels": 2, "max_output_channels": 2},
]

INIT_COUNT = 0
_AMP = 0.0
FAIL_OPEN = None  # excepción a lanzar en el próximo RawInputStream
PLAYED = []  # (len, samplerate) de cada sd.play()


def reset_state():
    global _AMP, FAIL_OPEN, INIT_COUNT, PLAYED
    _AMP = 0.0
    FAIL_OPEN = None
    INIT_COUNT = 0
    PLAYED = []


def set_amp(v) -> None:
    """v puede ser un float o un callable que devuelva la amplitud por frame."""
    global _AMP
    _AMP = v


def query_devices(device=None, kind=None):
    return list(DEVICE_LIST)


class RawInputStream:
    """Como el sounddevice real: ABRIR ya empieza la captura (start automático);
    `close()`/`__exit__` la detienen."""

    def __init__(self, samplerate, blocksize, dtype, channels, device, callback):
        if FAIL_OPEN is not None:
            raise FAIL_OPEN
        if os.environ.get("MECH_SD_FAIL_OPEN"):
            raise PortAudioError(
                "Error opening RawInputStream: Unanticipated host error "
                "[PaErrorCode -9999]: 'No such device' [ALSA error -19]"
            )
        self._cb = callback
        self._blocksize = int(blocksize)
        self._rate = int(samplerate)
        self._alive = True
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._alive = False
        return False

    def close(self):
        self._alive = False

    def _run(self):
        n = 0
        while self._alive:
            amp = _AMP() if callable(_AMP) else _AMP
            if amp > 0:
                t = np.arange(self._blocksize) / float(self._rate)
                wave = amp * np.sin(2 * np.pi * 440.0 * t)
                data = (wave.astype(np.float32) * 32767.0).astype(np.int16)
                data = data.reshape(-1, 1)
            else:
                data = np.zeros((self._blocksize, 1), dtype=np.int16)
            try:
                self._cb(data, self._blocksize, None, None)
            except Exception:
                pass
            n += 1
            time.sleep(0.005)

    def __exit__(self, *exc):
        self._alive = False
        return False

    def close(self):
        self._alive = False


def get_stream():
    return None


def play(data, samplerate):
    global PLAYED
    PLAYED.append((len(data), samplerate))


def _terminate():
    return None


def _initialize():
    global INIT_COUNT
    INIT_COUNT += 1


def stop():
    return None