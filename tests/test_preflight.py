"""Chequeo previo (preflight.py §5): el micrófono se prueba AISLADO y el
diagnóstico nunca revienta — un fallo de hardware se reporta, no se crashea.
"""
from __future__ import annotations

import preflight
import stt


def _chequear(monkeypatch, probe_result):
    preflight._resultados.clear()
    monkeypatch.setattr(stt, "probe_microphone", lambda seconds: probe_result)
    monkeypatch.setattr(
        preflight.shutil,
        "which",
        lambda name: "/usr/bin/pw-play" if name == "pw-play" else None,
    )
    preflight.check_audio()
    return list(preflight._resultados)


def _buscar(resultados, estado=None, titulo=""):
    return [r for r in resultados if (estado is None or r[0] == estado)
            and (not titulo or titulo in r[1])]


def test_mic_sano_se_reporta_ok(monkeypatch):
    resultados = _chequear(monkeypatch, {
        "device": None, "nombre": "WXMH", "rate": 48000,
        "nivel": 0.02, "pico": 0.3, "frames": 12, "error": None,
    })
    ok = _buscar(resultados, "OK  ", "Grabé")
    assert ok, resultados


def test_mic_apagado_se_dice_claro(monkeypatch):
    resultados = _chequear(monkeypatch, {
        "device": None, "nombre": None, "rate": 48000,
        "nivel": 0.0, "pico": 0.0, "frames": 0, "error": None,
    })
    falla = _buscar(resultados, "FALLA", "se abrió pero no entregó")
    assert falla, resultados


def test_crash_del_hijo_no_revienta_el_chequeo(monkeypatch):
    resultados = _chequear(monkeypatch, {
        "device": None, "nombre": None, "rate": 48000,
        "nivel": 0.0, "pico": 0.0, "frames": 0,
        "error": "El proceso del micrófono murió (código -6). Es el bug de ALSA",
    })
    falla = _buscar(resultados, "FALLA", "No pude abrir el micrófono")
    assert falla, resultados


def test_probe_microphone_real_devuelve_dict_con_error_sin_explotar(mic_en_proceso):
    # El flujo REAL de la probe (sin monkeypatch): el micro "no está" y el
    # dict vuelve con el motivo — el preflight lo puede leer.
    import sounddevice as sd

    sd.FAIL_OPEN = sd.PortAudioError("Error opening RawInputStream: no such device")
    info = stt.probe_microphone(0.2)
    assert isinstance(info, dict)
    assert info["frames"] == 0
    assert info["error"]