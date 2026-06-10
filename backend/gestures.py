"""Gestos de los brazos mientras MECH habla.

Por pedido del usuario, los brazos NO hacen poses grandes en cada segmento
(eso se veía como si se movieran "como locos"). En su lugar hacen un
movimiento SUAVE y pequeño adelante/atrás cerca del reposo — o nada, según
`config.ARM_GESTURE_MODE` ("subtle" | "off").

Sea cual sea el gesto que pida Claude (excited, wave, point...), aquí se
traduce todo al mismo gesto sutil, para que el movimiento sea siempre discreto
y los brazos terminen en reposo (90°).

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


def perform(link: ArduinoLink, gesture: str) -> None:
    """Movimiento suave de brazos al hablar (no bloqueante, sin encimarse).

    `gesture` se ignora a propósito: todos los gestos se reducen al mismo
    movimiento discreto (o a nada). Se mantiene el parámetro para no cambiar
    las llamadas existentes."""

    def _run():
        if not _gesture_lock.acquire(blocking=False):
            return
        try:
            if config.ARM_GESTURE_MODE == "off":
                # Sin movimiento: dejamos los brazos en reposo.
                link.arm("L", _NEUTRAL)
                link.arm("R", _NEUTRAL)
                return
            # Modo "subtle": un pequeño adelante y atrás cerca del reposo.
            amp = max(0, min(45, config.ARM_GESTURE_AMPLITUDE))
            fwd = _NEUTRAL - amp  # "adelante" un poquito (si va al revés, usa +)
            for angle in (fwd, _NEUTRAL):
                link.arm("L", angle)
                link.arm("R", angle)
                time.sleep(0.45)
        finally:
            _gesture_lock.release()

    threading.Thread(target=_run, daemon=True).start()
