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

- **Brazos MIENTRAS PROYECTA** (ago 2026): el equipo pidió gestos "muy
  simples, para que no gaste casi energía — que simplemente mueva un brazo".
  Por eso `perform_talking()` usa `_TALK_GESTURES`: UN solo brazo, ±25° sobre
  el reposo, lento y sin ruedas. `perform()` (saludo, panel) sigue con la
  coreografía completa. Se vuelve al comportamiento anterior con
  `NARRATION_GESTURE_MODE=full`.

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
    quedar en alto, pequeño vaivén arriba, y baja suave. Una sola vez.

    Velocidad y AMPLITUD se configuran (ajustables en vivo desde el panel):
      - `ARM_WAVE_SECONDS` (2.2): lo que tarda en subir y en bajar. El equipo
        lo pidió lento (ago 2026): rápido se veía nervioso.
      - `ARM_WAVE_HIGH` (180): hasta dónde sube. Antes eran 170.
      - `ARM_WAVE_SWING` (65): cuánto baja y sube en cada agitada.
      - `ARM_WAVE_REPEATS` (3): cuántas veces sube y baja EN TOTAL, contando
        la subida inicial. O sea: sube, agita 2 veces más, y baja. El equipo
        lo bajó de 4 a 3 ("daba demasiadas revoluciones", sep 2026) pero
        pidió que quedara en más de 2. El mínimo es 2.

    Solo se mueve HACIA ARRIBA (90 → 180). Por debajo de 90 el brazo choca
    con el cuerpo del robot: no bajar de ahí."""
    subida = max(0.4, config.ARM_WAVE_SECONDS)
    vaiven = max(0.25, subida * 0.35)  # cada agitada de arriba
    alto = max(_NEUTRAL + 10, min(180, config.ARM_WAVE_HIGH))
    # El vaivén nunca baja del reposo (ahí choca con el cuerpo).
    bajo = max(_NEUTRAL, alto - max(10, config.ARM_WAVE_SWING))
    # Brazo izquierdo: sube y se queda arriba acompañando (no agita, para que
    # el gesto se lea claro). Con ARM_WAVE_BOTH=false vuelve a ser un brazo.
    izq = alto if config.ARM_WAVE_BOTH else _NEUTRAL
    # ARM_WAVE_REPEATS cuenta las subidas TOTALES: la primera es este arco,
    # así que arriba quedan REPEATS-1 agitadas. Con 3 se ve "sube, agita,
    # agita, baja" — que es lo que pidió el equipo.
    agitadas = max(1, config.ARM_WAVE_REPEATS - 1)
    _move_smooth(link, izq, alto, subida)   # suben en arco hasta arriba
    for _ in range(agitadas):
        _move_smooth(link, izq, bajo, vaiven)   # el derecho agita, amplio
        _move_smooth(link, izq, alto, vaiven)
    _move_smooth(link, _NEUTRAL, _NEUTRAL, subida)  # bajan hasta el reposo


def _g_excited(link: ArduinoLink) -> None:
    # Entusiasmo CONTENIDO (video 2): ambos brazos suben poco y rebotan
    # suave; balanceo corto adelante/atrás del cuerpo.
    # Golpecito adelante/atrás a POTENCIA MÁXIMA (a media no se movía) pero
    # muy corto, para que sea un acento y no un desplazamiento.
    v = max(10, min(100, config.GESTURE_WHEEL_SPEED))
    d = config.GESTURE_WHEEL_SECONDS
    threading.Thread(
        target=_wheels, args=(link, [(v, d), (-v, d)]), daemon=True
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


# ── Gestos MIENTRAS NARRA (modo "simple", default) ───────────────────
# Pedido del equipo (ago 2026): "cuando proyecte que utilice un poco los
# brazos, pero muy simple para que no gaste casi energía, que simplemente
# mueva un brazo por ejemplo".
#
# Por eso, al narrar:
#   - se mueve UN SOLO brazo (el derecho; "thoughtful" usa el izquierdo para
#     que se note la diferencia),
#   - recorridos cortos (±25° como mucho sobre el reposo de 90°),
#   - lento, sin rebotes ni repeticiones,
#   - NUNCA las ruedas (mover el robot mientras proyecta desalinea la
#     proyección, y es lo que más batería gasta),
#   - y siempre termina en reposo (90°), que es donde el servo menos fuerza
#     hace.
# El SALUDO no pasa por aquí: ese sí es la coreografía completa.

_TALK_UP = 115      # tope del brazo al narrar (reposo 90°)
_TALK_UP_SOFT = 105  # elevación mínima, para gestos "tranquilos"


def _t_still(link: ArduinoLink) -> None:
    """Sin gesto: los brazos se quedan (o vuelven) al reposo. Consumo mínimo."""
    if _current["L"] != _NEUTRAL or _current["R"] != _NEUTRAL:
        _move_smooth(link, _NEUTRAL, _NEUTRAL, 0.8)


def _t_right(link: ArduinoLink, top: int, hold: float) -> None:
    """Sube SOLO el brazo derecho, lo sostiene y lo baja. Suave."""
    _move_smooth(link, _NEUTRAL, top, 1.0)
    time.sleep(hold)
    _move_smooth(link, _NEUTRAL, _NEUTRAL, 1.0)


def _t_left(link: ArduinoLink, top: int, hold: float) -> None:
    """Igual, pero con el brazo izquierdo."""
    _move_smooth(link, top, _NEUTRAL, 1.0)
    time.sleep(hold)
    _move_smooth(link, _NEUTRAL, _NEUTRAL, 1.0)


_TALK_GESTURES = {
    # neutral: literalmente no gastar nada.
    "neutral": _t_still,
    # excited / wave: el brazo derecho sube un poco y vuelve.
    "excited": lambda link: _t_right(link, _TALK_UP, 0.6),
    "wave": lambda link: _t_right(link, _TALK_UP, 0.6),
    # point: señala hacia la proyección y sostiene un momento.
    "point": lambda link: _t_right(link, _TALK_UP, 1.8),
    # arms_open: invitación contenida, un solo brazo abierto.
    "arms_open": lambda link: _t_right(link, _TALK_UP_SOFT, 1.8),
    # thoughtful: el brazo IZQUIERDO, apenas, para que se note distinto.
    "thoughtful": lambda link: _t_left(link, _TALK_UP_SOFT, 1.8),
}


def _g_subtle(link: ArduinoLink) -> None:
    # Modo "subtle": un pequeño adelante y atrás cerca del reposo.
    amp = max(0, min(45, config.ARM_GESTURE_AMPLITUDE))
    _move_smooth(link, _NEUTRAL - amp, _NEUTRAL - amp, 0.45)
    _move_smooth(link, _NEUTRAL, _NEUTRAL, 0.45)


def _perform(link: ArduinoLink, gesture: str, talking: bool) -> None:
    """Motor común de `perform` y `perform_talking`.

    `talking=True` = el gesto acompaña a la narración: se usa la versión
    simple (un brazo, corto, sin ruedas) salvo que se pida "full"."""

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
            # El SALUDO nunca se encoge: es el gesto que ve todo el que se
            # acerca al stand, y con ARM_GESTURE_MODE=subtle quedaba en un
            # vaivén de 12° que no se notaba. Solo "off" lo desactiva.
            if mode == "subtle" and not (gesture == "wave" and not talking):
                _g_subtle(link)
                return
            if talking and config.NARRATION_GESTURE_MODE != "full":
                # Narrando: gesto mínimo de un solo brazo (ver _TALK_GESTURES).
                _TALK_GESTURES.get(gesture, _t_still)(link)
                return
            # Modo "full": coreografía real del gesto pedido.
            fn = _FULL_GESTURES.get(gesture, _g_neutral)
            fn(link)
        finally:
            _gesture_lock.release()

    threading.Thread(target=_run, daemon=True).start()


def perform(link: ArduinoLink, gesture: str, user_x: float | None = None) -> None:
    """Ejecuta el gesto COMPLETO en segundo plano (no bloquea a quien llama).

    Es el que se usa fuera de la narración: el saludo al detectar a alguien
    con la cámara, el saludo hacia afuera y los botones del panel.

    `user_x` se acepta por compatibilidad pero YA NO se usa: el robot no
    gira hacia el usuario (las ruedas solo van adelante/atrás)."""
    _perform(link, gesture, talking=False)


def perform_talking(link: ArduinoLink, gesture: str) -> None:
    """Gesto MIENTRAS NARRA: por defecto, la versión simple de un solo brazo.

    Lo llama `mech_app.execute_plan` por cada segmento. Con
    `NARRATION_GESTURE_MODE=full` vuelven las coreografías completas."""
    _perform(link, gesture, talking=True)
