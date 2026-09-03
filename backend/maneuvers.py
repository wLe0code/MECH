"""Maniobras de MECH: girar hacia el público y volver a proyectar.

Pedido del equipo (ago 2026):

    «Cuando le digamos "mira hacia afuera" haga un giro de 180 grados con
    movimiento lateral, salude hacia afuera, y cuando le digamos "regresa a
    proyectar" vuelva a hacer un giro de 180 grados para que esté en su
    posición original proyectando.»

Cómo está hecho
---------------

En el stand MECH mira hacia la superficie donde proyecta. Cuando pasa gente
por detrás, "mira hacia afuera" lo pone de cara al público, saluda con el
brazo, y "regresa a proyectar" deshace la maniobra EXACTA para que el
proyector vuelva a apuntar a donde estaba calibrado.

La maniobra tiene dos tramos, en este orden:

  1. **Lateral** (`vy`): se aparta de la pared/mesa antes de girar, para no
     rozarla al rotar. Las mecanum lo permiten sin cambiar de orientación.
  2. **Giro** (`w`): rota sobre sí mismo hasta quedar de espaldas.

La vuelta hace lo mismo al revés y con el signo cambiado (giro y luego
lateral), así que termina donde empezó.

⚠️ **No hay encoders: el giro se mide POR TIEMPO.** `TURN_180_SECONDS` HAY
QUE CALIBRARLO en el robot real — se ajusta en vivo desde Ajustes del panel
hasta que 180° queden 180°. Lo mismo con `TURN_LATERAL_SECONDS`.

El estado ("¿estoy mirando a la proyección o al público?") vive en
`mech_app.state["facing"]`, para que:
  - el panel lo muestre,
  - no se gire dos veces seguidas hacia el mismo lado,
  - y `execute_plan` pueda volver solo a la posición de proyección si alguien
    pide una historia mientras MECH está de espaldas.
"""

from __future__ import annotations

import threading
import time

import config
import gestures

# Un solo giro a la vez: si llega otra orden mientras rota, se descarta (si no,
# dos hilos mandarían MOVE contradictorios y el robot quedaría en cualquier
# ángulo, que es justo lo que no podemos permitirnos sin encoders).
_lock = threading.Lock()

# Frases que dice al girar. Van aquí y no en lang.py porque son de esta
# maniobra; si algún día hay más, se mueven allá.
_SAY = {
    "outward": {
        "es": "¡Hola! Miren hacia acá.",
        "en": "Hello there! Look over here.",
    },
    "back": {
        "es": "Vuelvo a la proyección.",
        "en": "Back to the projection.",
    },
    "already_outward": {
        "es": "Ya estoy mirando hacia afuera.",
        "en": "I'm already facing outside.",
    },
    "already_projecting": {
        "es": "Ya estoy en posición de proyectar.",
        "en": "I'm already in projecting position.",
    },
}


def _sign(v: int) -> int:
    return (v > 0) - (v < 0)


def _drive(app, vx: int, vy: int, w: int, seconds: float) -> None:
    """Manda un MOVE durante `seconds` y SIEMPRE termina en STOP.

    Empieza con un pulso a potencia MÁXIMA (`MOTOR_KICK_SECONDS`) para romper
    la fricción estática: con estos motores y el L298N, arrancar a media
    potencia hace que zumben sin moverse. Si la velocidad pedida ya es 100,
    el pulso no cambia nada."""
    if seconds <= 0:
        app.log(
            f"Tramo de ruedas saltado: duran 0 s "
            f"(MOVE:{vx}:{vy}:{w}). Revisa TURN_*_SECONDS en Ajustes.",
            "warn",
        )
        return
    kick = min(config.MOTOR_KICK_SECONDS, seconds)
    # Log explícito: si en el stand "no se mueve", aquí se ve si la orden
    # llegó a salir y con qué potencia.
    app.log(f"Ruedas: MOVE:{vx}:{vy}:{w} durante {seconds:.2f} s", "info")
    try:
        if kick > 0 and max(abs(vx), abs(vy), abs(w)) < 100:
            app.arduino.move(_sign(vx) * 100, _sign(vy) * 100, _sign(w) * 100)
            time.sleep(kick)
        app.arduino.move(vx, vy, w)
        time.sleep(seconds - kick)
    finally:
        app.arduino.stop_motors()


def _turn(app, direction: int) -> None:
    """Media vuelta. `direction` +1 = horario, −1 = antihorario.

    Tramo lateral primero (apartarse) y luego el giro, tal como se pidió."""
    speed = max(10, min(100, config.TURN_180_SPEED))
    lateral = max(10, min(100, config.TURN_LATERAL_SPEED))
    _drive(app, 0, lateral * direction, 0, config.TURN_LATERAL_SECONDS)
    _drive(app, 0, 0, speed * direction, config.TURN_180_SECONDS)


def _unturn(app, direction: int) -> None:
    """Deshace `_turn`: mismo recorrido, orden inverso y signo contrario."""
    speed = max(10, min(100, config.TURN_180_SPEED))
    lateral = max(10, min(100, config.TURN_LATERAL_SPEED))
    _drive(app, 0, 0, -speed * direction, config.TURN_180_SECONDS)
    _drive(app, 0, -lateral * direction, 0, config.TURN_LATERAL_SECONDS)


class _WheelsHeld:
    """Toma las ruedas mientras dura la maniobra.

    Sin esto, el bucle de voz manda `MODE:LISTEN` en su siguiente vuelta y el
    firmware ejecuta `stopAllMotors()`: el robot arrancaba y se paraba en
    seguida (por eso "no se movía"). Además pone el Arduino en AUTO, que es
    un modo que NO frena los motores."""

    def __init__(self, app):
        self.app = app

    def __enter__(self):
        self.app.wheels_busy.set()
        try:
            self.app.arduino.set_mode("AUTO")
        except Exception:
            pass
        return self

    def __exit__(self, *exc):
        try:
            self.app.arduino.stop_motors()
        finally:
            self.app.wheels_busy.clear()
        return False


def facing(app) -> str:
    """"projection" (mirando a donde proyecta) o "outward" (al público)."""
    return app.state.get("facing", "projection")


def look_outward(app, greet: bool = True) -> bool:
    """Gira 180° y saluda al público. True si de verdad se movió."""
    import lang
    import tts

    if not _lock.acquire(blocking=False):
        app.log("Ya estoy girando; espera a que termine.", "warn")
        return False
    try:
        if facing(app) == "outward":
            app.log("Ya estoy mirando hacia afuera.", "info")
            if greet:
                tts.speak(_SAY["already_outward"].get(lang.current(), ""), blocking=True)
            return False
        app.log(
            f"Giro 180° para mirar hacia afuera "
            f"(potencia {config.TURN_180_SPEED}, {config.TURN_180_SECONDS} s).",
            "ok",
        )
        with _WheelsHeld(app):
            _turn(app, +1)
        app.state["facing"] = "outward"
        app.emit("facing", facing="outward")
        # Saludo COMPLETO (el arco lento del video del equipo), no el gesto
        # pequeño de narrar: aquí es justo lo que queremos que se vea.
        gestures.perform(app.arduino, "wave")
        if greet:
            # Ventana anti-eco: el bucle de voz descarta lo que transcriba
            # mientras MECH habla, para no oírse a sí mismo por el parlante.
            app.greeting_until = time.time() + 12
            try:
                tts.speak(_SAY["outward"].get(lang.current(), ""), blocking=True)
            finally:
                app.greeting_until = time.time() + 1.5
        return True
    finally:
        _lock.release()


def back_to_projection(app, announce: bool = True) -> bool:
    """Deshace el giro: vuelve a la posición de proyección. True si se movió."""
    import lang
    import tts

    if not _lock.acquire(blocking=False):
        app.log("Ya estoy girando; espera a que termine.", "warn")
        return False
    try:
        if facing(app) == "projection":
            if announce:
                app.log("Ya estoy en posición de proyectar.", "info")
                tts.speak(
                    _SAY["already_projecting"].get(lang.current(), ""), blocking=True
                )
            return False
        app.log("Giro 180° de vuelta a la posición de proyección.", "ok")
        if announce:
            app.greeting_until = time.time() + 10
            try:
                tts.speak(_SAY["back"].get(lang.current(), ""), blocking=True)
            finally:
                app.greeting_until = time.time() + 1.5
        with _WheelsHeld(app):
            _unturn(app, +1)
        app.state["facing"] = "projection"
        app.emit("facing", facing="projection")
        return True
    finally:
        _lock.release()


def assume_projection(app) -> None:
    """Declara que MECH está en posición de proyectar, SIN moverlo.

    Lo usa el paro de emergencia: tras un paro no sabemos hacia dónde quedó
    apuntando, y lo último que queremos es que la próxima orden dispare un
    giro "de vuelta" a ciegas. El operador lo recoloca a mano."""
    app.state["facing"] = "projection"
    app.emit("facing", facing="projection")
