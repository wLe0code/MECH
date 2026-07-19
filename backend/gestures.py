"""Gestos físicos de MECH (brazos + ruedas) mientras habla.

CALIBRADO CON VIDEOS DEL EQUIPO (jul 2026):

- **Protocolo de saludo** (video 1): UN solo arco amplio y lento — el brazo
  sube desde el reposo, pasa por la horizontal hasta quedar en alto, hace un
  pequeño vaivén arriba y baja suave hasta el reposo. Sin oscilaciones
  rápidas. Es el ÚNICO gesto que recorre todo el rango del brazo.

- **Brazos al hablar** (video 2): gestos PEQUEÑOS cerca del cuerpo — el
  brazo sube apenas ~30-45° y vuelve. NUNCA girar todo el brazo mientras
  narra (máximo ~125° con reposo en 90°).

- **Ruedas**: SOLO adelante/atrás. Las mecanum de este robot no giran bien
  en el sitio (decisión jul 2026: girar se hace manual, estilo carro, desde
  el panel). Los gestos no rotan; a lo sumo un balanceo corto
  adelante/atrás. El desplazamiento queda registrado en el odómetro de
  arduino_link para poder volver al punto de inicio.

Tres modos, según `config.ARM_GESTURE_MODE`:
  - "full"   (default): coreografías de arriba.
  - "subtle": un vaivén pequeño cerca del reposo.
  - "off":    los brazos no se mueven.

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

# Tope de elevación de los brazos MIENTRAS HABLA (video 2: no girar todo el
# brazo). El saludo es la excepción y sí llega arriba.
_TALK_MAX = 125


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


def _wheels(link: ArduinoLink, moves: list[tuple[int, float]]) -> None:
    """Secuencia corta de movimientos SOLO adelante/atrás (vx, duración).
    Siempre termina en STOP. El odómetro de arduino_link registra el
    desplazamiento para poder volver al punto de inicio."""
    if not config.GESTURE_WHEELS:
        return
    try:
        for vx, dur in moves:
            link.move(vx, 0, 0)
            time.sleep(dur)
    finally:
        link.stop_motors()


# ── Coreografías (modo "full") ───────────────────────────────────────

def _g_neutral(link: ArduinoLink) -> None:
    _move_smooth(link, _NEUTRAL, _NEUTRAL, 0.5)


def _g_wave(link: ArduinoLink) -> None:
    """PROTOCOLO DE SALUDO (video 1): arco completo, lento y amable.

    Sube el brazo derecho desde el reposo pasando por la horizontal hasta
    quedar en alto, pequeño vaivén arriba, y baja suave. Una sola vez."""
    _move_smooth(link, _NEUTRAL, 170, 1.3)   # sube en arco (pasa por horizontal)
    _move_smooth(link, _NEUTRAL, 150, 0.5)   # vaivén suave arriba
    _move_smooth(link, _NEUTRAL, 170, 0.5)
    _move_smooth(link, _NEUTRAL, _NEUTRAL, 1.3)  # baja hasta el reposo


def _g_excited(link: ArduinoLink) -> None:
    # Entusiasmo CONTENIDO (video 2): ambos brazos suben poco y rebotan
    # suave; balanceo corto adelante/atrás del cuerpo.
    threading.Thread(
        target=_wheels, args=(link, [(14, 0.3), (-14, 0.3)]), daemon=True
    ).start()
    _move_smooth(link, 122, 122, 0.6)
    for _ in range(2):
        _move_smooth(link, 108, 108, 0.35)
        _move_smooth(link, 122, 122, 0.35)
    _move_smooth(link, _NEUTRAL, _NEUTRAL, 0.6)


def _g_point(link: ArduinoLink) -> None:
    # Señalar (hacia la proyección): elevación media, sostiene.
    _move_smooth(link, _NEUTRAL, _TALK_MAX, 0.7)
    time.sleep(2.0)
    _move_smooth(link, _NEUTRAL, _NEUTRAL, 0.7)


def _g_arms_open(link: ArduinoLink) -> None:
    # Brazos apenas abiertos, invitando; sostiene un momento.
    _move_smooth(link, 118, 118, 0.8)
    time.sleep(2.2)
    _move_smooth(link, _NEUTRAL, _NEUTRAL, 0.8)


def _g_thoughtful(link: ArduinoLink) -> None:
    # Introspectivo: un brazo sube un poco, el otro queda en reposo.
    _move_smooth(link, 112, _NEUTRAL, 0.7)
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

    `user_x` se acepta por compatibilidad pero YA NO se usa: el robot no
    gira hacia el usuario (las ruedas solo van adelante/atrás)."""

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
            if mode == "subtle":
                _g_subtle(link)
                return
            # Modo "full" (default): coreografía real del gesto pedido.
            fn = _FULL_GESTURES.get(gesture, _g_neutral)
            fn(link)
        finally:
            _gesture_lock.release()

    threading.Thread(target=_run, daemon=True).start()
