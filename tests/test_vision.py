"""Bucle de visión (vision.py): el comportamiento "a prueba de todo".

Se inyecta una cámara SIMULADA (cv2 falso) que muere un rato (el USB caído)
y vuelve sola. Lo que se verifica:
  * la cámara NO se rinde jamás (sigue reintentando tras los 5 intentos);
  * se recupera SOLA cuando el dispositivo vuelve;
  * los avisos no se desparraman (solo un aviso de corriente/cable).
"""
from __future__ import annotations

import sys
import threading
import time
import types

import pytest

import config
import vision
from conftest import esperar


class _FakeArduino:
    def __init__(self):
        self.moves = []
        self.stops = 0

    def move(self, *a):
        self.moves.append(a)

    def stop_motors(self):
        self.stops += 1

    def set_mode(self, *a, **k):
        pass


class _FakeApp:
    def __init__(self):
        self.logs = []
        self.state = {"voice_phase": "dormant", "current_mode": None}
        self.arduino = _FakeArduino()

    def log(self, msg, lvl="info"):
        self.logs.append((lvl, msg))

    def emit(self, *a, **k):
        pass

    def on_user_detected(self):
        pass

    def on_user_lost(self):
        pass


class _FakeDetector:
    name = "fake"

    def detect(self, frame):
        return []  # nunca hay caras: nos concentramos en la supervivencia

    def close(self):
        pass


class _FakeCap:
    """Cámara scripteada: las lecturas 3..N fallan (USB caído), después vuelve."""

    contador = 0
    MUERTA_HASTA = 45

    def __init__(self, idx):
        self.idx = idx
        self.opened = True

    def isOpened(self):
        return self.opened

    def set(self, *a):
        pass

    def read(self):
        _FakeCap.contador += 1
        n = _FakeCap.contador
        muerta = 3 <= n <= _FakeCap.MUERTA_HASTA
        return (not muerta, "frame")

    def release(self):
        self.opened = False


def _fabricar_cv2():
    cv2 = types.ModuleType("cv2")
    cv2.VideoCapture = _FakeCap
    cv2.VideoWriter_fourcc = lambda *a: 0x1234
    cv2.CAP_PROP_FOURCC = 3
    cv2.CAP_PROP_FRAME_WIDTH = 3
    cv2.CAP_PROP_FRAME_HEIGHT = 4
    cv2.CAP_PROP_FPS = 5
    return cv2


@pytest.fixture
def vision_lista(monkeypatch):
    """Vision con cámara falsa y tiempos comprimidos, ya arrancada."""
    _FakeCap.contador = 0
    monkeypatch.setitem(sys.modules, "cv2", _fabricar_cv2())
    monkeypatch.setattr(vision, "_SIN_IMAGEN_S", 0.05)
    monkeypatch.setattr(vision, "_CALENTAMIENTO_S", 0.05)
    monkeypatch.setattr(vision, "_REINTENTOS_REABRIR", 2)
    monkeypatch.setattr(vision, "_make_detector", lambda app: (_FakeDetector(), None))
    monkeypatch.setattr(config, "VISION_CAMERA_INDEX", 0)

    app = _FakeApp()
    vis = vision.Vision(app)
    vis.start()
    return app, vis


def test_la_camara_nunca_se_rinde_y_se_recupera_sola(vision_lista):
    app, vis = vision_lista

    # Debe pasar por la caída, el mensaje de "NO me rindo" y recuperarse.
    esperar(lambda: any("NO me rindo" in m for _, m in app.logs), timeout=30)
    esperar(lambda: any("Cámara recuperada" in m for _, m in app.logs), timeout=30)

    # Y NUNCA debe decir lo de antes ("dejo de intentarlo").
    assert not any("dejo de intentarlo" in m for _, m in app.logs)

    # Un solo aviso de corriente/cable, no uno por reintento.
    avisos_poder = [m for _, m in app.logs if "CORRIENTE o CABLE" in m]
    assert len(avisos_poder) == 1

    vis.stop()
    assert not vis.running


def test_la_vision_sigue_viva_despues_de_la_caida(vision_lista):
    app, vis = vision_lista
    esperar(lambda: any("Cámara recuperada" in m for _, m in app.logs), timeout=30)
    # El hilo sigue corriendo (no se cortó en el camino de recuperación).
    assert vis.running
    vis.stop()


def test_sin_camara_el_hilo_no_revienta(monkeypatch):
    """Cero cámaras en el sistema: el loop declara que no hay nada y termina
    con estado acorde (sin excepciones ni hilos zombies)."""
    _FakeCap.contador = 1 << 30  # todas las lecturas fallan

    class _SiempreMuerta:
        def __init__(self, idx):
            pass

        def isOpened(self):
            return False

        def set(self, *a):
            pass

        def read(self):
            return False, None

        def release(self):
            pass

    cv2 = types.ModuleType("cv2")
    cv2.VideoCapture = _SiempreMuerta
    cv2.VideoWriter_fourcc = lambda *a: 0
    cv2.CAP_PROP_FOURCC = 3
    cv2.CAP_PROP_FRAME_WIDTH = 3
    cv2.CAP_PROP_FRAME_HEIGHT = 4
    cv2.CAP_PROP_FPS = 5
    monkeypatch.setitem(sys.modules, "cv2", cv2)
    monkeypatch.setattr(vision, "_SIN_IMAGEN_S", 0.05)
    monkeypatch.setattr(vision, "_CALENTAMIENTO_S", 0.1)
    monkeypatch.setattr(vision, "_make_detector", lambda app: (_FakeDetector(), None))

    app = _FakeApp()
    vis = vision.Vision(app)
    vis.start()
    esperar(
        lambda: any("NINGUNA cámara" in m for _, m in app.logs),
        timeout=10,
    )
    esperar(lambda: not vis.running, timeout=10)  # el loop termina solo, sin boom
    assert app.state["vision"]["enabled"] is False