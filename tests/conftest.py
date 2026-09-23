"""Configuración global de las pruebas.

Orden de sys.path (importante):
  stubs/  primero  → tapa config/lang/sounddevice/webrtcvad/... reales,
  fix/backend      → importa el CÓDIGO DE PRODUCCIÓN tal cual se va a subir.

Además se cambia el cwd a fix/ para que los subprocesos reales
(`python -m backend._mic_worker`) resuelvan el paquete `backend`.
"""
from __future__ import annotations

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.abspath(os.path.join(HERE, "..", "fix"))
STUBS = os.path.join(HERE, "stubs")

sys.path.insert(0, os.path.join(FIX, "backend"))
sys.path.insert(0, STUBS)
os.chdir(FIX)


@pytest.fixture(autouse=True)
def _reset_stubs():
    """Cada prueba arranca con los simuladores de hardware en cero."""
    import serial
    import sounddevice
    import webrtcvad
    from serial.tools import list_ports

    sounddevice.reset_state()
    webrtcvad.reset_state()
    serial.reset_state()
    list_ports.reset_state()
    yield


@pytest.fixture
def mic_en_proceso(monkeypatch):
    """Fuerza el modo in-process (sin subprocesos) para las pruebas del FLUJO
    de voz/VAD. El aislamiento por subproceso se prueba aparte en
    test_mic_worker.py con hijos reales."""
    import stt

    monkeypatch.setattr(stt, "_FORZAR_INPROCESS", True)
    yield


def esperar(predicado, timeout=10.0, paso=0.02):
    """Espera hasta que `predicado()` sea verdadero; falla con timeout."""
    import time

    fin = time.monotonic() + timeout
    while time.monotonic() < fin:
        if predicado():
            return
        time.sleep(paso)
    raise AssertionError(f"timeout esperando condición (límite {timeout} s)")