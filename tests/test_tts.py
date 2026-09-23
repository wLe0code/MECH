"""Salida de voz (tts.py): el orden de reproductores y el último recurso
(backend.wav_play) en proceso aparte. Ningún binario real se ejecuta: se
intercepta subprocess.Popen y se simula cada reproductor.
"""
from __future__ import annotations

import sys

import numpy as np
import pytest

import sounddevice as sd
import tts


class _FakePopen:
    """Intercepta subprocess.Popen y simula los reproductores según su nombre."""

    llamados: list[list[str]] = []
    wav_rc = 0  # rc que devuelve `python -m backend.wav_play`
    otros_rc = 1  # rc de pw-play / ffplay

    def __init__(self, cmd, stdin=None):
        _FakePopen.llamados.append(list(cmd))
        base = cmd[0]
        if base == "paplay":
            raise FileNotFoundError("paplay no está instalado")
        if base.endswith("wav_play"):
            rc = _FakePopen.wav_rc
        else:
            rc = _FakePopen.otros_rc
        self._rc = rc

    @property
    def returncode(self):
        return self._rc

    def poll(self):
        return self._rc

    def wait(self):
        return self._rc

    def terminate(self):
        self._rc = -15

    def kill(self):
        self._rc = -9


def _audio():
    return np.zeros(44100, dtype=np.float32)


def test_orden_de_reproductores_y_ultimo_recurso_exitoso(monkeypatch):
    _FakePopen.llamados = []
    _FakePopen.wav_rc = 0
    monkeypatch.setattr(tts.subprocess, "Popen", _FakePopen)

    arranques = []
    tts._play_audio(_audio(), 44100, lead_silence=0.0,
                    on_started=lambda: arranques.append(1))

    bases = [c[0] for c in _FakePopen.llamados]
    assert bases[:3] == ["pw-play", "paplay", "ffplay"]  # wav_play último
    assert bases[3] == sys.executable  # el python real, en subproceso propio
    assert _FakePopen.llamados[-1][2] == "backend.wav_play"
    # on_started se llama por cada reproductor que ARRANCA: paplay no está
    # instalado (FileNotFoundError) y salta sin arrancar → 3 llamadas.
    assert len(arranques) == 3, f"on_started: {len(arranques)}"


def test_si_todo_falla_se_loguea_y_no_explota(monkeypatch, capsys):
    _FakePopen.llamados = []
    _FakePopen.wav_rc = 1
    monkeypatch.setattr(tts.subprocess, "Popen", _FakePopen)

    tts._play_audio(_audio(), 44100, lead_silence=0.0)  # no debe lanzar

    assert len(_FakePopen.llamados) == 4
    assert "Ningún reproductor" in capsys.readouterr().out


def test_stop_event_cancela_antes_de_abrir(monkeypatch):
    _FakePopen.llamados = []
    monkeypatch.setattr(tts.subprocess, "Popen", _FakePopen)
    tts._stop_event.set()
    try:
        tts._play_audio(_audio(), 44100, lead_silence=0.0)
        assert _FakePopen.llamados == []
    finally:
        tts._stop_event.clear()


# ── backend/wav_play.py (el hijo reproductor aislado) ─────────────────────
def test_wav_play_requiere_archivo(monkeypatch):
    import wav_play

    monkeypatch.setattr("sys.argv", ["wav_play"])
    assert wav_play.main() == 1


def test_wav_play_reproduce_y_termina(monkeypatch):
    import wav_play

    monkeypatch.setattr("sys.argv", ["wav_play", "x.wav"])
    assert wav_play.main() == 0
    assert sd.PLAYED, "sd.play debió llamarse"
    assert sd.PLAYED[-1][1] == 44100  # samplerate


def test_wav_play_no_puede_leer_devuelve_1(monkeypatch):
    import wav_play

    def _leer_rota(path, dtype="float32"):
        raise OSError("archivo corrupto")

    monkeypatch.setattr(wav_play.sf, "read", _leer_rota)
    monkeypatch.setattr("sys.argv", ["wav_play", "roto.wav"])
    assert wav_play.main() == 1


def test_wav_play_salida_fallida_devuelve_1(monkeypatch):
    import wav_play

    def _play_roto(data, sr):
        raise sd.PortAudioError("no such device")

    monkeypatch.setattr(wav_play.sd, "play", _play_roto)
    monkeypatch.setattr("sys.argv", ["wav_play", "x.wav"])
    assert wav_play.main() == 1