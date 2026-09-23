"""El protocolo del subproceso del micrófono, probado con hijos REALES.

Lo que se valida (y no se puede validar con mocks del lado padre):
  * el hijo parsea argv y muere limpio con argv inválido;
  * si el hijo no puede IMPORTAR sounddevice (entorno roto), muere con
    código 1 y el padre lo reporta como MicProcessCrashed (nunca un crash);
  * si el sonido no se puede ABRIR (el caso del receptor desenchufado),
    el hijo muere con código 1 y el padre lo reporta igual;
  * flujo feliz: el hijo (con sounddevice SIMULADO vía PYTHONPATH) entrega
    bytes de audio reales por el pipe, y al cerrar el padre sale LIMPIO
    (código 0) — la maquinaria de cierre EPIPE funciona.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

import pytest

import stt

STUBS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stubs")


def _spec(device=None, samplerate=48000, blocksize=stt.FRAME_BYTES // 2):
    return json.dumps({"device": device, "samplerate": samplerate, "blocksize": blocksize})


def _aguardar_muerte(mic, limite=5.0):
    fin = time.monotonic() + limite
    while mic.alive and time.monotonic() < fin:
        time.sleep(0.02)


def test_argv_invalido_es_limpio():
    cp = subprocess.run(
        [sys.executable, "-m", "backend._mic_worker", "no-es-un-fd"],
        capture_output=True,
        timeout=20,
    )
    assert cp.returncode == 2


def test_hijo_sin_sounddevice_muere_y_el_padre_lo_detecta(monkeypatch):
    # Sin PYTHONPATH el hijo no encuentra sounddevice (en este entorno no
    # está instalado): es "un ALSA roto" y debe morir solo, no tumbar al padre.
    monkeypatch.delenv("PYTHONPATH", raising=False)
    with stt._MicWorker(None, 48000, stt.FRAME_BYTES // 2) as mic:
        _aguardar_muerte(mic)
        with pytest.raises(stt.MicProcessCrashed) as ei:
            mic.read_chunk(0.2)
        assert "código 1" in str(ei.value)
        assert "server sigue vivo" in str(ei.value)


def test_hijo_falla_al_abrir_y_el_padre_lo_detecta(monkeypatch):
    # El caso real del bug: "No such device" / ALSA error -19 al abrir.
    monkeypatch.setenv("PYTHONPATH", STUBS_DIR)
    monkeypatch.setenv("MECH_SD_FAIL_OPEN", "1")
    with stt._MicWorker(None, 48000, stt.FRAME_BYTES // 2) as mic:
        _aguardar_muerte(mic)
        with pytest.raises(stt.MicProcessCrashed) as ei:
            mic.read_chunk(0.2)
        assert "código 1" in str(ei.value)


def test_flujo_feliz_datos_reales_y_cierre_limpio(monkeypatch):
    # Hijo con sounddevice SIMULADO: entrega audio y el cierre del padre lo
    # termina por EPIPE (código 0) — el shutdown es suave, no un kill.
    monkeypatch.setenv("PYTHONPATH", STUBS_DIR)
    w = stt._MicWorker("WXMH mini: USB Audio (hw:2,0)", 48000, stt.FRAME_BYTES // 2)
    w.start()
    proc = w._proc
    try:
        primer = w.read_chunk(timeout=5.0)
        assert primer is not None and len(primer) >= stt.FRAME_BYTES, "no llegó audio del hijo"
        segundo = w.read_chunk(timeout=2.0)
        assert segundo is not None
    finally:
        w.close()
    assert proc is not None
    assert proc.wait(timeout=3.0) == 0, "el hijo debió salir limpio por EPIPE"


def test_el_hijo_entrega_mismo_devices_por_nombre_e_indice(monkeypatch):
    monkeypatch.setenv("PYTHONPATH", STUBS_DIR)
    for device in (None, 0, "Steren MIC-9010: USB PnP (hw:1,0)"):
        with stt._MicWorker(device, 48000, stt.FRAME_BYTES // 2) as mic:
            chunk = mic.read_chunk(timeout=5.0)
            assert chunk, f"device={device!r} no entregó audio"
            assert len(chunk) >= stt.FRAME_BYTES


def test_close_no_cuelga_con_hijo_vivo(monkeypatch):
    monkeypatch.setenv("PYTHONPATH", STUBS_DIR)
    w = stt._MicWorker(None, 48000, stt.FRAME_BYTES // 2)
    w.start()
    t0 = time.monotonic()
    w.close()
    assert time.monotonic() - t0 < 3.0, "close() colgó"


def test_no_se_multiplexan_descritores():
    """close() dos veces o tras el cierre no debe explotar."""
    with stt._MicWorker(None, 48000, stt.FRAME_BYTES // 2) as mic:
        mic.close()
        mic.close()
    with pytest.raises(stt.MicProcessCrashed):
        mic.read_chunk(0.05)  # r ya cerrado → error limpio, no OSError crudo