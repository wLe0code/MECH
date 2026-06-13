"""Gestos físicos de MECH (brazos + ruedas) mientras habla.

Tres modos, según `config.ARM_GESTURE_MODE`:
  - "full"   (default): cada gesto que pide Claude (wave, excited, point...)
              tiene su coreografía real de brazos, con movimiento SUAVE
              (interpolado en pasos pequeños, nada de saltos bruscos que
              hacían que los servos parecieran "locos").
  - "subtle": el comportamiento anterior — un vaivén pequeño cerca del reposo.
  - "off":    los brazos no se mueven.

Si `config.GESTURE_WHEELS` es true, algunos gestos añaden un movimiento
corto de ruedas (balanceo, giro pequeño). Siempre terminan en STOP.

`perform()` acepta `user_x` opcional (posición horizontal del usuario según
la cámara, -1=izquierda .. +1=derecha): si viene, MECH gira un toque hacia
la persona antes del gesto, para "mirarla" al narrar.

Un lock global evita que dos gestos se encimen (si llega uno nuevo mientras
otro corre, se descarta) — sin esto los servos temblaban.
"""

from __future__ import annotations

import threading
import time

import config
from arduino_link import ArduinoLink

# Solo un gesto a la vez. Si está tomado, los gestos nuevos se descartan.
_gesture_lock = threading.Lock()

_NEUTRAL = 90  # posición de reposo de los brazos

# Última posición conocida de cada brazo (para interpolar desde ahí).
_current = {"L": _NEUTRAL, "R": _NEUTRAL}

# Paso de interpolación: cada cuántos segundos mandamos un ángulo nuevo.
_STEP_S = 0.03


def _move_smooth(link: ArduinoLink, target_l: int, target_r: int, duration: float) -> None:
    """Lleva ambos brazos de su posición actual a la meta, interpolando."""
    target_l = max(0, min(180, int(target_l)))
    target_r = max(0, min(180, int(target_r)))
    start_l, start_r = _current["L"], _current["R"]
    steps = max(1, int(duration / _STEP_S))
    for i in range(1, steps + 1):
        t = i / steps
        link.arm("L", round(start_l + (target_l - start_l) * t))
        link.arm("R", round(start_r + (target_r - start_r) * t))
        time.sleep(_STEP_S)
    _current["L"], _current["R"] = target_l, target_r


def _wheels(link: ArduinoLink, moves: list[tuple[int, int, int, float]]) -> None:
    """Secuencia corta de movimientos de ruedas; siempre termina en STOP."""
    if not config.GESTURE_WHEELS:
        return
    try:
        for vx, vy, w, dur in moves:
            link.move(vx, vy, w)
            time.sleep(dur)
    finally:
        link.stop_motors()


def _face_user(link: ArduinoLink, user_x: float | None) -> None:
    """Giro corto hacia el usuario (si la visión nos dio su posición)."""
    if user_x is None or not config.GESTURE_WHEELS:
        return
    if abs(user_x) < 0.18:  # ya está más o menos de frente
        return
    w = int(max(-1.0, min(1.0, user_x)) * 30)
    _wheels(link, [(0, 0, w, 0.35)])


# ── Coreografías (modo "full") ───────────────────────────────────────

def _g_neutral(link: ArduinoLink) -> None:
    _move_smooth(link, _NEUTRAL, _NEUTRAL, 0.5)


def _g_excited(link: ArduinoLink) -> None:
    # Brazos arriba con un par de rebotes + balanceo corto del cuerpo.
    threading.Thread(
        target=_wheels, args=(link, [(0, 0, 18, 0.25), (0, 0, -18, 0.25)]), daemon=True
    ).start()
    _move_smooth(link, 165, 165, 0.6)
    for _ in range(2):
        _move_smooth(link, 140, 140, 0.3)
        _move_smooth(link, 165, 165, 0.3)
    time.sleep(0.4)
    _move_smooth(link, _NEUTRAL, _NEUTRAL, 0.7)


def _g_wave(link: ArduinoLink) -> None:
    # Saludo: brazo derecho arriba oscilando, izquierdo quieto.
    _move_smooth(link, _NEUTRAL, 160, 0.5)
    for _ in range(3):
        _move_smooth(link, _NEUTRAL, 135, 0.25)
        _move_smooth(link, _NEUTRAL, 165, 0.25)
    _move_smooth(link, _NEUTRAL, _NEUTRAL, 0.6)


def _g_point(link: ArduinoLink) -> None:
    # Señalar (hacia la proyección): brazo derecho extendido, sostiene.
    _move_smooth(link, _NEUTRAL, 150, 0.5)
    time.sleep(2.0)
    _move_smooth(link, _NEUTRAL, _NEUTRAL, 0.6)


def _g_arms_open(link: ArduinoLink) -> None:
    # Brazos abiertos, invitando; sostiene un momento.
    _move_smooth(link, 145, 145, 0.8)
    time.sleep(2.2)
    _move_smooth(link, _NEUTRAL, _NEUTRAL, 0.8)


def _g_thoughtful(link: ArduinoLink) -> None:
    # Introspectivo: un brazo a medio camino, el otro abajo.
    _move_smooth(link, 120, 65, 0.7)
    time.sleep(2.0)
    _move_smooth(link, _NEUTRAL, _NEUTRAL, 0.7)


_FULL_GESTURES = {
    "neutral": _g_neutral,
    "excited": _g_excited,
    "wave": _g_wave,
    "point": _g_point,
    "arms_open": _g_arms_open,
    "thoughtful": _g_thoughtful,
}


def _g_subtle(link: ArduinoLink) -> None:
    # Modo "subtle": un pequeño adelante y atrás cerca del reposo.
    amp = max(0, min(45, config.ARM_GESTURE_AMPLITUDE))
    _move_smooth(link, _NEUTRAL - amp, _NEUTRAL - amp, 0.45)
    _move_smooth(link, _NEUTRAL, _NEUTRAL, 0.45)


def perform(link: ArduinoLink, gesture: str, user_x: float | None = None) -> None:
    """Ejecuta el gesto en segundo plano (no bloquea la narración).

    `user_x`: posición horizontal del usuario según la cámara (-1..+1),
    para girar hacia la persona antes del gesto. None = no girar.
    """

    def _run():
        if not _gesture_lock.acquire(blocking=False):
            return
        try:
            mode = config.ARM_GESTURE_MODE
            if mode == "off":
                link.arm("L", _NEUTRAL)
                link.arm("R", _NEUTRAL)
                _current["L"] = _current["R"] = _NEUTRAL
                return
            _face_user(link, user_x)
            if mode == "subtle":
                _g_subtle(link)
                return
            # Modo "full" (default): coreografía real del gesto pedido.
            fn = _FULL_GESTURES.get(gesture, _g_neutral)
            fn(link)
        finally:
            _gesture_lock.release()

    threading.Thread(target=_run, daemon=True).start()
