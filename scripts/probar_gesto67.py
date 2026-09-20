"""Mide el detector del gesto "67" contra videos de prueba.

Para qué sirve: los umbrales de `GESTURE67_*` son un equilibrio. Aflojarlos
para que pille un caso que falla hace que empiece a dispararse solo con
cualquier movimiento; apretarlos hace lo contrario. Este script pasa las DOS
listas de golpe, así que el efecto de un cambio se ve de una vez.

    python scripts/probar_gesto67.py                 # solo los sintéticos
    python scripts/probar_gesto67.py v1.mp4 v2.mp4   # + videos reales

Los videos que se pasen por línea de comandos se tratan como POSITIVOS (se
espera que disparen). Los negativos se generan aquí mismo con OpenCV, así que
el script funciona en cualquier máquina sin tener que cargar videos al repo.

Necesita `opencv-python` y `numpy` (los mismos que la visión).
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import config  # noqa: E402
from gesture_detect import SixtySevenDetector  # noqa: E402

_W, _H, _FPS, _SEC = 640, 360, 15, 6


def _cuerpo(f, cx=320):
    """Una persona de mentira: cabeza y torso, quietos."""
    cv2.circle(f, (cx, 110), 42, (150, 160, 190), -1)
    cv2.rectangle(f, (cx - 60, 150), (cx + 60, 330), (90, 90, 120), -1)


def _mano(f, x, y):
    cv2.circle(f, (x, y), 28, (170, 180, 205), -1)


def _sintetico(pintar):
    """Genera los fotogramas de un video de prueba (lista de arrays BGR).

    No se escriben a disco: el códec mp4 deduplica los fotogramas casi
    iguales y eso falseaba la medición (inventaba huecos que la cámara real
    no tiene).
    """
    rng = np.random.default_rng(7)
    frames = []
    for i in range(_FPS * _SEC):
        f = np.full((_H, _W, 3), 40, np.uint8)
        # Ruido de sensor: sin él la escena es TAN limpia que no se parece a
        # nada que salga de una cámara de verdad.
        f = cv2.add(f, rng.integers(0, 6, (_H, _W, 3), dtype=np.int16).astype(np.uint8))
        cv2.rectangle(f, (0, 0), (_W, 120), (70, 60, 55), -1)
        pintar(f, i / _FPS)
        frames.append(f)
    return frames


def _quieto(f, t):
    _cuerpo(f, 320 + int(2 * math.sin(t * 2)))


def _una_mano(f, t):
    _cuerpo(f)
    _mano(f, 410, 150 + int(70 * math.sin(t * 2 * math.pi * 1.5)))


def _en_fase(f, t):
    _cuerpo(f)
    y = 150 + int(70 * math.sin(t * 2 * math.pi * 1.5))
    _mano(f, 230, y)
    _mano(f, 410, y)


def _horizontal(f, t):
    _cuerpo(f)
    dx = int(60 * math.sin(t * 2 * math.pi * 1.5))
    _mano(f, 230 + dx, 190)
    _mano(f, 410 - dx, 190)


def _camina(f, t):
    _cuerpo(f, int(60 + t * 90))


def _antifase(f, t):
    """El gesto de verdad: una mano sube mientras la otra baja."""
    _cuerpo(f)
    fase = t * 2 * math.pi * 1.5
    _mano(f, 230, 150 + int(70 * math.sin(fase)))
    _mano(f, 410, 150 + int(70 * math.sin(fase + math.pi)))


def _correr(frames, fps: float) -> list[float]:
    """Devuelve los segundos en que el detector disparó."""
    det = SixtySevenDetector()
    # El cooldown estorba aquí: queremos ver TODOS los disparos.
    config.GESTURE67_COOLDOWN = 0.0
    disparos = []
    for i, fr in enumerate(frames):
        if det.feed(fr, i / fps):
            disparos.append(round(i / fps, 2))
    return disparos


def _frames_de_video(path: str):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
    frames = []
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        frames.append(fr)
    cap.release()
    return frames, fps


def main() -> int:
    casos: list[tuple[str, list, float, bool]] = []

    for ruta in sys.argv[1:]:
        frames, fps = _frames_de_video(ruta)
        if not frames:
            print(f"!! No pude leer {ruta}")
            return 2
        casos.append((f"REAL {Path(ruta).name}", frames, fps, True))

    casos += [
        ("antifase (el gesto)", _sintetico(_antifase), _FPS, True),
        ("quieto", _sintetico(_quieto), _FPS, False),
        ("saluda con UNA mano", _sintetico(_una_mano), _FPS, False),
        ("dos manos EN FASE", _sintetico(_en_fase), _FPS, False),
        ("manos en horizontal", _sintetico(_horizontal), _FPS, False),
        ("alguien camina", _sintetico(_camina), _FPS, False),
    ]

    fallos = 0
    print(
        f"umbrales: amp>={config.GESTURE67_MIN_AMPLITUDE} "
        f"corr<={config.GESTURE67_MAX_CORR} "
        f"alt>={config.GESTURE67_MIN_ALTERNATIONS} "
        f"equilibrio>={config.GESTURE67_BALANCE}\n"
    )
    for nombre, frames, fps, esperado in casos:
        disparos = _correr(frames, fps)
        ok = bool(disparos) == esperado
        fallos += not ok
        marca = "ok  " if ok else "FALLA"
        quiere = "debe disparar" if esperado else "NO debe disparar"
        print(f"{marca} {nombre:28s} ({quiere:15s}) -> {disparos or 'ninguno'}")

    print()
    if fallos:
        print(f"{fallos} caso(s) mal. No subas este cambio de umbrales.")
        return 1
    print(f"Los {len(casos)} casos pasan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
