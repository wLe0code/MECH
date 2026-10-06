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

La maniobra es **UN SOLO tramo de `vy`**, exactamente el mismo movimiento
de los botones «GIRO» del panel, mantenido hasta que el robot queda de
espaldas. (En el código `vy` se llama "lateral" por la mecanum de libro, pero
con estas ruedas es el que GIRA; desde sep 2026 el panel lo etiqueta así.)

⚠️ **No se usa `w` (rotación) — y es a propósito** (sep 2026). Sobre el suelo
del stand, con estas ruedas, el patrón de rotación hacía "un movimiento raro y
muy corto"; el que de verdad hace girar al robot es `vy`. Es coherente
con el resto del proyecto: la cinemática de este robot está calibrada a mano
y no coincide con la mecanum de libro (ver `driveOmni` en el .ino). Si alguien
vuelve a meter `w` aquí, va a repetir el mismo problema.

La vuelta es el MISMO tramo con el signo cambiado, así que termina justo donde
empezó.

⚠️ **No hay encoders: el giro se mide POR TIEMPO.** `TURN_180_SECONDS` HAY
QUE CALIBRARLO en el robot real — se ajusta en vivo desde Ajustes del panel
hasta que la media vuelta quede en media vuelta. Si gira hacia el lado
equivocado, `TURN_180_INVERT` le cambia el sentido (también en vivo).

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
# ⚠️ Las de alemán, italiano, japonés, ruso y chino están escritas para NO
# contener la orden que las dispara: justo después de decirlas se abre el
# micrófono, y si MECH se oye decir «…schau nach außen» volvería a obedecerse.
_SAY = {
    "outward": {
        "es": "¡Hola! Miren hacia acá.",
        "en": "Hello there! Look over here.",
        "fr": "Bonjour ! Regardez par ici.",
        "pt": "Olá! Olhem para cá.",
        "de": "Hallo zusammen! Schaut mal hierher.",
        "it": "Ciao a tutti! Guardate qui.",
        "ja": "みなさん、こんにちは！こちらをご覧ください。",
        "ru": "Привет всем! Посмотрите сюда.",
        "zh": "大家好！请看这边。",
        "ko": "여러분, 반갑습니다! 이쪽을 봐 주세요.",
    },
    "back": {
        "es": "Vuelvo a la proyección.",
        "en": "Back to the projection.",
        "fr": "Je retourne à la projection.",
        "pt": "Volto para a projeção.",
        "de": "Ich wende mich wieder der Leinwand zu.",
        "it": "Mi rigiro verso la proiezione.",
        "ja": "投影の位置に戻ります。",
        "ru": "Возвращаюсь к проекции.",
        "zh": "我转回投影那边了。",
        "ko": "다시 투영 위치로 돌아갈게요.",
    },
    "already_outward": {
        "es": "Ya estoy mirando hacia afuera.",
        "en": "I'm already facing outside.",
        "fr": "Je regarde déjà vers l'extérieur.",
        "pt": "Já estou olhando para fora.",
        "de": "Ich blicke bereits zum Publikum.",
        "it": "Sto già guardando verso l'esterno.",
        "ja": "すでに外側を向いています。",
        "ru": "Я уже повёрнут к публике.",
        "zh": "我已经面向外面了。",
        "ko": "이미 바깥쪽을 향하고 있어요.",
    },
    "already_projecting": {
        "es": "Ya estoy en posición de proyectar.",
        "en": "I'm already in projecting position.",
        "fr": "Je suis déjà en position de projection.",
        "pt": "Já estou na posição de projetar.",
        "de": "Ich bin schon in Projektionsposition.",
        "it": "Sono già in posizione di proiezione.",
        "ja": "すでに投影の位置にいます。",
        "ru": "Я уже на месте для проекции.",
        "zh": "我已经在投影的位置了。",
        "ko": "이미 투영 위치에 있어요.",
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


def _side() -> int:
    """+1 o −1: hacia qué lado desliza para darse la vuelta.

    Si en el robot gira al revés, se cambia con `TURN_180_INVERT` desde
    Ajustes (en vivo), sin tocar código ni reflashear el Arduino."""
    return -1 if config.TURN_180_INVERT else 1


def _turn(app, direction: int) -> None:
    """Media vuelta: UN solo tramo de `vy`, igual que los botones GIRO del panel.

    `direction` +1 = ida (mirar hacia afuera), −1 = vuelta."""
    speed = max(10, min(100, config.TURN_180_SPEED))
    _drive(app, 0, speed * direction * _side(), 0, config.TURN_180_SECONDS)


def _unturn(app, direction: int) -> None:
    """Deshace `_turn`: el mismo tramo con el signo cambiado."""
    _turn(app, -direction)


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
    """Hacia dónde mira MECH, según lo que él sabe:

    - "projection": mirando a donde proyecta (su sitio de trabajo).
    - "outward":    de espaldas, mirando al público.
    - "manual":     NO LO SABE. Alguien lo giró a mano desde el panel (los
                    botones GIRO/LATERAL, el comando crudo o «PROBAR MEDIA
                    VUELTA»), y esos giros no le dicen cuánto giró.
    """
    return app.state.get("facing", "projection")


def mark_manual(app) -> None:
    """Lo movieron a mano: ya no sabemos hacia dónde mira.

    Sin esto pasaba lo que reportó el equipo (sep 2026): lo daban vuelta con
    el panel, MECH seguía creyendo que miraba a la proyección, y al decirle
    «regresa a proyectar» contestaba «ya estoy en posición» y NO giraba.

    Con el estado en "manual", las dos órdenes EXPLÍCITAS («regresa a
    proyectar» / «mira hacia afuera») obedecen siempre: quien las da está
    viendo el robot. Lo AUTOMÁTICO (volver solo antes de narrar) NO gira en
    este estado, porque ahí nadie está mirando y un giro a ciegas podría
    dejar la proyección apuntando al público.
    """
    if facing(app) == "manual":
        return
    app.state["facing"] = "manual"
    app.emit("facing", facing="manual")
    app.log(
        "Me giraste a mano: ya no sé hacia dónde miro. «Regresa a proyectar» "
        "y «mira hacia afuera» girarán igual cuando me lo pidas.",
        "info",
    )


def look_outward(app, greet: bool = True) -> bool:
    """Gira 180° y saluda al público. True si de verdad se movió."""
    import lang
    import tts

    if not _lock.acquire(blocking=False):
        app.log("Ya estoy girando; espera a que termine.", "warn")
        return False
    try:
        if facing(app) == "outward":
            # Solo se niega si SABE que ya está afuera: evita que un «mira
            # hacia afuera» repetido lo deje otra vez mirando a la proyección.
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
        # Saludo CONTENIDO: se tiene que notar que saluda, pero el equipo
        # pidió que aquí moviera los brazos menos que en la bienvenida por
        # cámara (sep 2026). Ver gestures.wave_outward().
        gestures.wave_outward(app.arduino)
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
        # Solo se niega si SABE que ya está proyectando (así un «regresa a
        # proyectar» repetido no lo da vuelta de nuevo). Si lo giraron a mano
        # ("manual"), obedece: quien lo pide está viendo el robot.
        if facing(app) == "projection":
            if announce:
                app.log(
                    "Ya estoy en posición de proyectar (si no es así, gírame "
                    "desde el panel o pulsa «REGRESA A PROYECTAR» otra vez "
                    "después de moverme a mano).",
                    "info",
                )
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


def advance(app, seconds: float | None = None, backwards: bool = False) -> bool:
    """Avanza (o retrocede) durante unos segundos, a potencia máxima.

    `seconds=None` usa `config.ADVANCE_SECONDS`. Se topa en
    `ADVANCE_MAX_SECONDS`: en un stand, un robot lanzado varios metros es un
    problema, y una orden mal entendida no debería poder provocarlo.

    Al terminar se **resetea el odómetro**: si alguien pide expresamente
    mover el robot, esa pasa a ser su nueva posición de trabajo. Si no,
    `return_to_start()` desharía el movimiento antes de la siguiente
    narración, que es justo lo contrario de lo que se pidió.
    """
    if seconds is None:
        seconds = config.ADVANCE_SECONDS
    seconds = max(0.1, min(float(seconds), config.ADVANCE_MAX_SECONDS))
    velocidad = max(10, min(100, config.ADVANCE_SPEED))
    if backwards:
        velocidad = -velocidad

    if not _lock.acquire(blocking=False):
        app.log("Ya estoy en movimiento; espera a que termine.", "warn")
        return False
    try:
        app.log(
            f"{'Retrocedo' if backwards else 'Avanzo'} {seconds:g} s "
            f"a potencia {abs(velocidad)}.",
            "ok",
        )
        with _WheelsHeld(app):
            _drive(app, velocidad, 0, 0, seconds)
        # Nueva posición de partida (ver el docstring).
        try:
            app.arduino.reset_odometer()
        except Exception:
            pass
        return True
    finally:
        _lock.release()


def test_half_turn(app) -> None:
    """Ejecuta el tramo de media vuelta SIN cambiar hacia dónde mira.

    Es para calibrar: se pulsa, se mira cuánto giró, se ajustan los segundos
    y se vuelve a pulsar. Con «mira hacia afuera» no se puede hacer eso — a
    la segunda vez ya está de espaldas y no se mueve, y habría que alternar
    con «regresa a proyectar», acumulando el error de los dos tramos.
    """
    if not _lock.acquire(blocking=False):
        app.log("Ya estoy girando; espera a que termine.", "warn")
        return
    try:
        app.log(
            f"PRUEBA de media vuelta: giro a {config.TURN_180_SPEED} "
            f"durante {config.TURN_180_SECONDS} s. Mirá cuánto gira y ajustá "
            f"los segundos en Ajustes.",
            "info",
        )
        with _WheelsHeld(app):
            _turn(app, +1)
        # La prueba NO cambia hacia dónde "cree" que mira, a propósito (así
        # se puede repetir para calibrar). Pero tras ella ya no lo sabemos:
        # sin esto, un «regresa a proyectar» después de probar se negaba.
        mark_manual(app)
    finally:
        _lock.release()


def assume_projection(app) -> None:
    """Declara que MECH está en posición de proyectar, SIN moverlo.

    Lo usa el paro de emergencia: tras un paro no sabemos hacia dónde quedó
    apuntando, y lo último que queremos es que la próxima orden dispare un
    giro "de vuelta" a ciegas. El operador lo recoloca a mano."""
    app.state["facing"] = "projection"
    app.emit("facing", facing="projection")
