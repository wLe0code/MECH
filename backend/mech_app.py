"""Estado compartido y event bus de MECH.

El servidor (server.py) y el bucle de voz (main.py) tocan los mismos
componentes (Arduino, proyectores, Claude, TTS). Para que ambos vean
los mismos cambios y emitan logs hacia el frontend, todo pasa por aquí.

Diseño:
- Singleton accesible vía `get_app()`.
- Eventos publicados con `emit(type, **data)` se difunden a todos los
  WebSockets suscritos. El servidor llama `subscribe(ws)` cuando un
  cliente abre el WS.
- Estado mutable en `state` (dict). El servidor lo envía completo al
  conectar un cliente nuevo.
"""

from __future__ import annotations

import asyncio
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Awaitable, Callable

import sounddevice as sd

import config
import gestures
import image_gen
import informacion_nuestra
import lang
import llm
import maneuvers
import background_audio
import subtitles
import translator
import trivia
import voice_phrases
import tts
import video_library
import voices
from arduino_link import ArduinoLink, get_link
from interrupt_listener import InterruptListener

EventCallback = Callable[[dict], Awaitable[None]]


class MechApp:
    """Singleton con el estado global y un event bus para WebSockets."""

    def __init__(self) -> None:
        self.arduino: ArduinoLink = get_link()
        self.history: list[dict] = []
        # Interrupción por voz: mientras MECH narra, un hilo aparte escucha
        # SOLO "oye MECH" / "hey MECH" (ver backend/interrupt_listener.py).
        self._narration_interrupted: bool = False
        # Sin `on_level`: emitir el nivel del micrófono durante toda la
        # narración llenaba el WebSocket de eventos y el panel iba a tirones.
        # Para diagnosticar ya está el log "Oí mientras narraba: ...".
        self.interrupts = InterruptListener(self._on_interrupt, self.log)
        # Si el visitante dijo "oye MECH, <otra cosa>", eso queda aquí para
        # atenderlo en cuanto se corte la narración (sin que lo repita).
        self.pending_command: str | None = None
        # Mientras esto está activo, el bucle de voz NO abre el micrófono: lo
        # necesita el listener de interrupción. Importa cuando la narración se
        # lanza desde el panel, porque ahí el bucle está esperando voz con el
        # micrófono abierto y los dos no caben.
        self.mic_release = threading.Event()
        # Cuando MECH termina de hablar y queda listo para escuchar, se marca
        # esto para que el worker suene el chime ANTES de abrir el micrófono.
        self.chime_pending: bool = False
        # Último patrón enviado al aro de LEDs (para no repetir comandos).
        self._last_led: str | None = None
        # Throttle del nivel de micrófono que se emite al panel.
        self._last_mic_level_emit: float = 0.0
        # Saludo al detectar usuario: cooldown para no saludar en bucle a la
        # misma persona, y ventana anti-eco (mientras MECH saluda, el bucle
        # de voz descarta lo que transcriba para no oírse a sí mismo).
        self._last_greeting: float = 0.0
        self.greeting_until: float = 0.0
        # Desde cuándo NO hay nadie delante de la cámara (None = hay alguien,
        # o nadie se ha ido desde el último saludo). Es lo que distingue a un
        # visitante NUEVO del mismo de antes: ver `_greeting_rearmed()`.
        self._user_gone_since: float | None = None
        # Throttle del aviso "no saludo porque estoy despierto": la visión
        # detecta a ~10 fps y si no llenaría el panel de logs iguales.
        self._last_greeting_skip_log: float = 0.0
        # Lo último que MECH narró (título, texto y obra), que es sobre lo
        # que van las preguntas de la trivia.
        self._last_presentation: dict | None = None
        # Subtítulos: hilo que va sacando las líneas al ritmo real de la voz.
        self._subs_cancel: threading.Event | None = None
        # Mientras esto está activo, las RUEDAS están en medio de una maniobra
        # (giro de 180°, vuelta al punto de inicio). El bucle de voz no debe
        # tocar el modo del Arduino en ese rato: `MODE:LISTEN` ejecuta
        # `stopAllMotors()` en el firmware y cortaría el movimiento.
        self.wheels_busy = threading.Event()
        # Se marca cuando la pantalla avisa que terminó el último video de la
        # playlist promo (POST /api/playlist/ended), o al cortarla.
        self._playlist_done = threading.Event()
        # Dónde va la reproducción en la pantalla principal (/projector), para
        # que el visor VR del teléfono se enganche en el mismo segundo en vez
        # de empezar el video desde cero. Lo reporta el propio <video>.
        self._playback: dict | None = None

        self.state: dict[str, Any] = {
            "voice_loop_active": False,
            "voice_listening": False,
            # voice_awake: dentro de un bucle activo, si MECH responde (True) o
            # está en reposo escuchando solo la palabra para despertar (False).
            "voice_awake": True,
            # Fase detallada del ciclo de voz para el panel. Una de:
            # off | dormant | waiting | listening | transcribing | thinking | speaking
            "voice_phase": "off",
            # Idioma activo: "es" (default) o "en" (solo si lo despertaron
            # con "wake up MECH"). Ver backend/lang.py.
            "language": lang.current(),
            "claude_model": config.CLAUDE_MODEL,
            "current_mode": "IDLE",
            "projectors": {
                "s1": {"on": False, "file": None},
                "s2": {"on": False, "file": None},
                "imm": {"on": False, "file": None},
            },
            "current_image": None,  # URL relativa de imagen en el proyector AI
            "current_video": None,  # URL relativa de video pre-renderizado (Opción B)
            "arduino_connected": self.arduino.is_connected,
            "last_transcript": "",
            "last_ai_response": "",
            # Subtítulo que se ve ahora en la proyección (estilo cine, abajo).
            # Es el texto del segmento que MECH está narrando.
            "current_subtitle": None,
            "subtitle_lang": lang.current(),
            # Por qué segundo va el video en la pantalla principal, para que
            # el visor VR se enganche ahí en vez de empezar de cero.
            "playback": None,
            # Playlist promo en curso (marketing): los videos se reproducen
            # ENTEROS, en fila y con su propio audio. None = no hay ninguna.
            # {slug, title, items:[{n,url,kind}], audio: bool}
            "current_playlist": None,
            # Hacia dónde mira el robot: "projection" (a la superficie
            # donde proyecta, que es su sitio de trabajo) u "outward" (de
            # espaldas, saludando al público). Lo cambia backend/maneuvers.py
            # con las órdenes "mira hacia afuera" / "regresa a proyectar".
            "facing": "projection",
            # Modo traductor: MECH de intérprete entre dos personas.
            # {active, awaiting_pair, src, dst, auto_detect}. Ver
            # backend/translator.py.
            "translator": translator.snapshot(),
            # Estado del juego de preguntas. OJO: esto es lo que se PINTA en
            # la proyección, no la verdad del juego — el marcador final se
            # queda unos segundos en pantalla cuando la partida ya terminó.
            # Para saber si se está jugando, `trivia.is_active()`.
            "trivia": trivia.snapshot(),
            # Estado de la visión (lo actualiza backend/vision.py).
            "vision": {
                "enabled": False,
                "user_present": False,
                "x": 0.0,
                "distance": None,
                "min_distance": config.VISION_MIN_DISTANCE,
            },
        }

        self._subscribers: set[EventCallback] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

        # Reflejar conexión/desconexión del Arduino en el panel en vivo
        # (el link reintenta solo en segundo plano si se desconecta).
        self.arduino.on_status = self._on_arduino_status

    def _on_arduino_status(self, connected: bool) -> None:
        self.state["arduino_connected"] = connected
        self.log(
            "Arduino conectado." if connected else "Arduino desconectado (reintentando).",
            "ok" if connected else "warn",
        )
        self.emit("state", state=self.state)
        if connected:
            # Restablecer modo y LEDs tras el reset que sufre al reconectar.
            # force=True: el Arduino olvidó su modo, hay que mandarlo aunque
            # sea el mismo que teníamos cacheado.
            self.arduino.set_mode(self.state.get("current_mode", "IDLE"), force=True)
            if self._last_led:
                self.arduino.led(self._last_led)

    # ------------------------------------------------------------------
    # Event bus
    # ------------------------------------------------------------------

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """El servidor llama esto al arrancar para que emit() pueda
        agendar corrutinas desde hilos no-async."""
        self._loop = loop

    def subscribe(self, callback: EventCallback) -> None:
        with self._lock:
            self._subscribers.add(callback)

    def unsubscribe(self, callback: EventCallback) -> None:
        with self._lock:
            self._subscribers.discard(callback)

    async def _broadcast(self, message: dict) -> None:
        with self._lock:
            subs = list(self._subscribers)
        for cb in subs:
            try:
                await cb(message)
            except Exception as e:
                print(f"[MechApp] subscriber falló: {e}")

    def emit(self, event_type: str, **data: Any) -> None:
        """Difunde un evento a todos los WS suscritos. Thread-safe."""
        message = {"type": event_type, **data}
        if self._loop is None:
            return
        if self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._broadcast(message), self._loop)

    def log(self, message: str, level: str = "info") -> None:
        """Emite un log y lo imprime en stdout."""
        try:
            print(f"[{level}] {message}")
        except UnicodeEncodeError:
            # Consolas cp1252 (Windows) con caracteres que no saben pintar.
            # Nunca dejamos que un log rompa lo que estaba haciendo el robot.
            print(f"[{level}] {message.encode('ascii', 'replace').decode()}")
        self.emit("log", message=message, level=level, ts=time.time())

    # Patrón del aro de LEDs (estilo Alexa) para cada fase de voz.
    _LED_BY_PHASE = {
        "off": "OFF",
        # Arrancando (cargando Whisper): el aro pulsa como "pensando", que es
        # lo que de verdad está haciendo. No "IDLE", que es el de reposo y
        # daría a entender que ya escucha.
        "loading": "THINK",
        # Sin micrófono (no se pudo abrir): rojo, como el paro. Es un fallo
        # que hay que ver desde lejos.
        "nomic": "ERR",
        "dormant": "IDLE",
        "waiting": "LISTEN",
        "listening": "LISTEN",
        "transcribing": "THINK",
        "thinking": "THINK",
        "speaking": "SPEAK",
    }

    def set_voice_phase(self, phase: str) -> None:
        """Actualiza la fase del ciclo de voz y la difunde al panel.

        Fases: off | loading | dormant | waiting | listening | transcribing |
        thinking | speaking. "loading" es mientras carga Whisper al arrancar:
        ahí el micrófono está CERRADO, y decirlo evita el susto de "MECH no
        me oye al encender el server".
        `voice_listening` se mantiene en sincronía (True solo cuando el
        micrófono está realmente abierto) para no romper indicadores viejos.
        También sincroniza el aro de LEDs del robot (como un Alexa Echo:
        encendido = puedes hablar, girando = pensando, etc.).
        """
        self.state["voice_phase"] = phase
        self.state["voice_listening"] = phase in ("waiting", "listening")
        self.set_led(self._LED_BY_PHASE.get(phase, "OFF"))
        self.emit("state", state=self.state)

    def set_led(self, pattern: str) -> None:
        """Manda un patrón al aro de LEDs solo si cambió (evita spam serial)."""
        if pattern != self._last_led:
            self._last_led = pattern
            self.arduino.led(pattern)

    def report_mic_level(self, rms: float, threshold: float, recording: bool) -> None:
        """Nivel del micrófono en vivo (lo manda stt vía callback). Se emite
        al panel con throttle para no inundar el WebSocket."""
        now = time.time()
        if now - self._last_mic_level_emit < 0.12:
            return
        self._last_mic_level_emit = now
        self.emit(
            "mic_level",
            level=round(rms, 4),
            threshold=round(threshold, 4),
            recording=recording,
        )

    # ------------------------------------------------------------------
    # Idioma (español por defecto, inglés con "wake up MECH")
    # ------------------------------------------------------------------

    def set_language(self, code: str, announce: bool = False) -> None:
        """Cambia el idioma en el que MECH escucha, narra y subtitula.

        `announce=True` hace que lo confirme en voz alta (se usa cuando el
        cambio ocurre con MECH ya despierto; al despertar no hace falta
        porque el saludo ya sale en el idioma nuevo).
        """
        before = lang.current()
        after = lang.set_current(code)
        self.state["language"] = after
        self.emit("state", state=self.state)
        if after != before:
            self.log(f"Idioma: {lang.label(after)}.", "ok")
        if announce and after != before:
            tts.speak(lang.say("switched", after), blocking=True)
            time.sleep(0.5)  # deja drenar el parlante antes de volver a oír

    # ------------------------------------------------------------------
    # Modo traductor ("traduce MECH") — ver backend/translator.py
    # ------------------------------------------------------------------

    def _emit_translator(self) -> None:
        self.state["translator"] = translator.snapshot()
        self.emit("state", state=self.state)

    @contextmanager
    def _talking_alone(self):
        """Mientras MECH habla aquí dentro, el bucle de voz suelta el micrófono.

        Hace falta cuando esto se llama desde OTRO hilo (los endpoints del
        panel): si no, el bucle sigue grabando y se transcribe a MECH
        preguntando por los idiomas. Es la misma guarda que usa
        `handle_text_command` para las narraciones lanzadas desde el panel.
        """
        self.mic_release.set()
        self.set_voice_phase("speaking")
        try:
            yield
        finally:
            self.mic_release.clear()
            self.set_voice_phase(
                "waiting" if self.state.get("voice_awake", True) else "dormant"
            )

    def start_translator(
        self,
        src: str | None = None,
        dst: str | None = None,
        continuous: bool = False,
    ) -> None:
        """Arranca el traductor: pregunta lo que falte y se queda escuchando.

        `continuous=False` («traduce MECH») traduce UNA frase y se calla; hay
        que repetir el comando para la siguiente. `continuous=True` («activa
        modo traductor») se queda traduciendo hasta que le digan que lo
        desactive. Ver backend/translator.py para por qué el continuo necesita
        más cuidado con el eco.

        Si ya sabe el par de idiomas (de una vez anterior, porque lo eligieron
        en el panel o porque lo dijeron en el propio comando), va directo a
        pedir la frase. Si no, pregunta primero por los idiomas.
        """
        src, dst = self._resolve_pair(src, dst)
        etapa = translator.begin(src, dst, continuous=continuous)
        with self._talking_alone():
            if etapa == "phrase":
                # Ya hay par: lo confirma (o va al grano) y se pone a escuchar.
                self._announce_pair(nuevo=bool(src and dst))
            else:
                modo = "continuo" if continuous else "de una frase"
                self.log(f"Modo traductor {modo}: pregunto el par de idiomas.", "ok")
                self._emit_translator()
                tts.speak(lang.say("translate_ask"), blocking=True)
                time.sleep(config.TRANSLATOR_DRAIN_SECONDS)
                self.chime_pending = True

    def _resolve_pair(
        self, src: str | None, dst: str | None
    ) -> tuple[str | None, str | None]:
        """Completa un par de idiomas a medias.

        Si solo se nombró UNO («traduce MECH al francés», «al portugués»), ese
        es el DESTINO y el origen es el idioma activo de MECH. Si no se nombró
        ninguno, se devuelve vacío para que quien llame use el par recordado o
        pregunte. Un par inválido (el mismo idioma dos veces) se descarta.
        """
        if dst and not src:
            src = lang.current()
        if src and dst and src == dst:
            self.log(
                f"Ignoro el par pedido: {lang.label(src)} a {lang.label(dst)} "
                "es el mismo idioma.",
                "warn",
            )
            return None, None
        return src, dst

    def _announce_pair(self, nuevo: bool = True) -> None:
        """Confirma el par de idiomas y se queda escuchando.

        `nuevo` distingue "acabamos de fijar este par" de "ya lo sabía de
        antes". En el segundo caso va al grano, que en un stand se agradece.
        En modo CONTINUO lo anuncia distinto: hay que decirle al visitante que
        no tiene que repetir el comando en cada frase.
        """
        src, dst = translator.pair()
        continuo = translator.is_continuous()
        self.log(
            f"Traduzco entre {lang.label(src)} y {lang.label(dst)}"
            f"{' (los dos sentidos)' if config.TRANSLATOR_AUTO_DETECT else ''}"
            f"{' — modo CONTINUO' if continuo else ''}.",
            "ok",
        )
        self._emit_translator()
        if continuo:
            texto = lang.say(
                "translate_on_continuous",
                src=lang.language_name(src),
                dst=lang.language_name(dst),
            )
        elif nuevo:
            texto = lang.say(
                "translate_ready",
                src=lang.language_name(src),
                dst=lang.language_name(dst),
            )
        else:
            texto = lang.say("translate_ask_phrase")
        self._say_and_listen(texto)

    def _say_and_listen(self, texto: str) -> None:
        """Dice una pregunta del traductor y deja el micrófono listo.

        Guarda lo dicho para la guarda anti-eco: entre la pregunta y la frase
        del visitante el micrófono SÍ está abierto, y el parlante Bluetooth
        arrastra su buffer. Sin esto MECH acabaría traduciendo su propia
        pregunta.
        """
        translator.remember_spoken(texto)
        tts.speak(texto, blocking=True)
        time.sleep(config.TRANSLATOR_DRAIN_SECONDS)
        # Chime de "puedes hablar", igual que tras "ok MECH".
        self.chime_pending = True

    def handle_translator_pair(self, text: str) -> None:
        """Interpreta la respuesta a "¿de qué idioma a qué idioma?".

        Acepta "de español a francés" y también un solo idioma ("al
        francés"), en cuyo caso el origen es el idioma activo de MECH.
        """
        crudo_src, crudo_dst = voice_phrases.extract_language_pair(text)
        src, dst = self._resolve_pair(crudo_src, crudo_dst)
        problema = None
        if not (src and dst):
            # Distinguimos "no entendí ningún idioma" de "me dijiste el mismo
            # dos veces": el aviso tiene que decirle qué arreglar.
            problema = ("translate_same" if crudo_src and crudo_dst
                        else "translate_pair_unknown")
        if problema:
            self._say_and_listen(lang.say(problema))
            self.set_voice_phase("waiting")
            return
        translator.set_pair(src, dst)
        self._announce_pair(nuevo=True)
        self.set_voice_phase("waiting")

    def handle_translation(self, text: str, detected: str | None = None) -> None:
        """Traduce UNA frase, la dice, y se calla hasta el próximo comando.

        `detected` es el idioma que Whisper creyó oír; con él se decide el
        sentido (ver `translator.direction`). El resultado se dice y se pinta
        como subtítulo en la proyección, que en un stand es media función: el
        visitante LEE la traducción además de oírla. El subtítulo se queda en
        pantalla (no se borra al terminar) para que dé tiempo a leerlo.
        """
        text = (text or "").strip()
        # Guarda anti-eco: si lo que oyó es casi algo que él mismo acaba de
        # decir (la pregunta, o la traducción anterior en modo continuo), es
        # su propio parlante. Se descarta y se vuelve a escuchar SIN DECIR
        # NADA — eso es lo que impide que el modo continuo se realimente.
        if text and translator.looks_like_own_echo(text, voice_phrases.normalize):
            self.log(f"Ignoro mi propio eco: {text!r}", "info")
            seguidos = translator.echo_streak()
            if seguidos >= 3:
                self.log(
                    f"Llevo {seguidos} ecos seguidos: me estoy oyendo a mí "
                    "mismo. Sube «Espera del traductor continuo» en Ajustes "
                    "(TRANSLATOR_CONTINUOUS_DRAIN_SECONDS).",
                    "warn",
                )
            text = ""
        if not text:
            self.set_voice_phase("waiting")
            return
        origen, destino = translator.direction(detected)
        self.state["last_transcript"] = text
        self.emit("transcript", text=text)
        self.set_voice_phase("thinking")
        try:
            traduccion = llm.translate(text, origen, destino)
        except Exception as e:
            self.log(f"No pude traducir: {e}", "err")
            traduccion = ""
        if not traduccion:
            # Falló la traducción: lo dice y vuelve a quedarse escuchando,
            # para no obligar a repetir el comando por un fallo suyo.
            with self._talking_alone():
                self._say_and_listen(lang.say("translate_error"))
            return
        self.log(f"{lang.label(origen)} → {lang.label(destino)}: {traduccion!r}", "ok")
        self.state["last_ai_response"] = traduccion
        self.emit("ai_response", text=traduccion)
        self.set_subtitle(traduccion, destino)
        # La traducción también se recuerda para la guarda anti-eco. En modo
        # continuo esto es IMPRESCINDIBLE: el micrófono se abre justo después
        # de decirla, así que es lo que más se puede colar.
        translator.remember_spoken(traduccion)
        self.set_voice_phase("speaking")
        tts.speak(traduccion, blocking=True)
        sigue = translator.finish()
        self._emit_translator()
        if sigue:
            # CONTINUO: no dice nada más (cada frase suya es eco en potencia),
            # solo espera más tiempo a que el parlante drene y vuelve a
            # escuchar. El chime avisa al visitante de que le toca.
            self.log("Traducción lista. Sigo escuchando (modo continuo).", "info")
            time.sleep(config.TRANSLATOR_CONTINUOUS_DRAIN_SECONDS)
            self.chime_pending = True
        else:
            # UNA FRASE: aquí se calla. Para la siguiente hay que volver a
            # decir «traduce MECH». El par de idiomas se recuerda.
            self.log(
                "Traducción lista. Decí «traduce MECH» otra vez para la "
                "siguiente, o «activa modo traductor» para que no pare.",
                "info",
            )
            time.sleep(config.TRANSLATOR_DRAIN_SECONDS)
        self.set_voice_phase("waiting")

    def stop_translator(self, announce: bool = True) -> None:
        """Sale del modo traductor Y olvida el par de idiomas.

        Ojo con la diferencia: `translator.finish()` (fin de UN turno) guarda
        el par para el siguiente «traduce MECH»; esto lo borra, que es lo que
        se quiere al decir «deja de traducir», al dormirlo o con el paro.
        """
        if not (translator.is_active() or translator.has_pair()):
            return
        translator.reset()
        self.log("Modo traductor apagado.", "info")
        self.set_subtitle(None)
        self._emit_translator()
        if announce:
            with self._talking_alone():
                tts.speak(lang.say("translate_off"), blocking=True)
                time.sleep(config.TRANSLATOR_DRAIN_SECONDS)

    # ------------------------------------------------------------------
    # Modo TRIVIA — el juego de preguntas (ver backend/trivia.py)
    # ------------------------------------------------------------------

    def _emit_trivia(self, snap: dict | None = None) -> None:
        """Manda a la proyección y al panel lo que hay que pintar.

        Va por evento WS **y** por `state`: el evento pinta al instante, y el
        estado hace que una pantalla que se recargue a media partida vuelva a
        la pregunta correcta sin preguntar nada.
        """
        snap = snap if snap is not None else trivia.snapshot()
        self.state["trivia"] = snap
        self.emit("trivia", **snap)

    def _clear_trivia_screen(self) -> None:
        """Quita el juego de la pantalla (la partida ya terminó)."""
        self._emit_trivia({"active": False, "stage": "off"})

    def _say_trivia(self, texto: str, listen: bool = True) -> None:
        """Dice algo del juego y deja el micrófono listo para contestar.

        Guarda lo dicho para la guarda anti-eco: el micrófono se abre justo
        después de hablar y el parlante arrastra buffer, así que sin esto
        MECH acabaría contestándose a sí mismo.
        """
        trivia.remember_spoken(texto)
        tts.speak(texto, blocking=True)
        time.sleep(config.TRIVIA_DRAIN_SECONDS)
        if listen:
            self.chime_pending = True  # chime de "te toca", como tras "ok MECH"

    def _remember_presentation(self, plan: "llm.Plan", narrados: list[str]) -> None:
        """Se queda con lo que MECH acaba de contar, para preguntar sobre eso.

        `narrados` son los segmentos que de verdad sonaron: si lo
        interrumpieron a la mitad, no tiene sentido preguntar por lo que el
        visitante no llegó a oír.
        """
        if not narrados:
            return
        slug = next((s.video_slug for s in plan.segments if s.video_slug), None)
        self._last_presentation = {
            "title": plan.title,
            "text": "\n".join(narrados),
            "slug": slug,
        }

    def _trivia_source(self) -> tuple[str, str]:
        """(título, material) sobre el que se escriben las preguntas.

        Lo normal es lo último que narró, más los **datos verificados** de esa
        obra (`facts` de video_library): así las preguntas salen de material
        comprobado y no de lo que el modelo recuerde. Si todavía no ha contado
        nada, la partida va sobre MECH y su proyecto.
        """
        pres = self._last_presentation
        if pres and pres.get("text"):
            partes = [pres["text"]]
            meta = video_library.WORKS.get(pres.get("slug") or "", {})
            datos = meta.get("facts") or []
            if datos:
                partes.append("Datos verificados de la obra:\n- " + "\n- ".join(datos))
            return pres.get("title") or meta.get("title", ""), "\n\n".join(partes)
        return (
            "MECH y su equipo",
            informacion_nuestra.system_prompt_section(),
        )

    def should_offer_trivia(self, plan: "llm.Plan") -> bool:
        """¿Toca ofrecer el juego al acabar esta narración?

        Solo tras una presentación de verdad (`immersive`): tras una respuesta
        suelta o una orden de movimiento, ofrecer un juego queda fuera de
        lugar. Y nunca si hay otra cosa en marcha (traductor) o si el bucle de
        voz está apagado, porque entonces nadie podría contestar.
        """
        return bool(
            config.TRIVIA_ENABLED
            and config.TRIVIA_OFFER_AFTER_PLAN
            and getattr(plan, "mode", "") == "immersive"
            and self._last_presentation
            and self.state["voice_loop_active"]
            and self.state.get("voice_awake", True)
            and not translator.is_active()
            and not trivia.is_active()
        )

    def offer_trivia(self, title: str = "") -> None:
        """Ofrece jugar y se queda esperando un sí o un no."""
        trivia.offer(title or (self._last_presentation or {}).get("title", ""))
        self.log("Ofrezco la trivia: espero un sí o un no.", "ok")
        self._emit_trivia()
        self._say_trivia(lang.say("trivia_offer"))

    def handle_trivia_offer(self, text: str) -> bool:
        """Interpreta la respuesta a "¿jugamos?".

        Devuelve True si la consumió. **False significa "esto no era para
        mí"**: el visitante cambió de tema («cuéntame otra cosa»), así que se
        cancela el ofrecimiento y quien llama lo procesa como un comando
        normal. Sin esto, decir cualquier otra cosa dejaría a MECH atascado
        preguntando por un juego que ya no interesa.
        """
        if self._trivia_echo(text):
            return True
        if voice_phrases.is_trivia_stop(text) or voice_phrases.is_no(text):
            trivia.reset()
            self._clear_trivia_screen()
            self.log("No quieren jugar: sigo normal.", "info")
            with self._talking_alone():
                self._say_trivia(lang.say("trivia_declined"))
            return True
        if voice_phrases.is_yes(text) or voice_phrases.is_trivia(text):
            self.start_trivia()
            return True
        # Cualquier otra cosa: no era una respuesta al ofrecimiento.
        trivia.reset()
        self._clear_trivia_screen()
        self.log("Cambió de tema: cancelo el ofrecimiento de la trivia.", "info")
        return False

    def _trivia_echo(self, text: str) -> bool:
        """¿Lo que oyó es su propia voz saliendo del parlante?"""
        if any(voice_phrases.sounds_like_same(text, d) for d in trivia.spoken()):
            self.log(f"Ignoro mi propio eco: {text!r}", "info")
            return True
        return False

    def start_trivia(self) -> None:
        """Genera las preguntas y lanza la primera.

        Avisa por voz antes de pedirle las preguntas a Claude: son varios
        segundos y, sin avisar, parece que MECH se colgó.
        """
        titulo, material = self._trivia_source()
        with self._talking_alone():
            trivia.reset()
            self._emit_trivia()
            tts.speak(lang.say("trivia_preparing"), blocking=True)
            self.set_voice_phase("thinking")
            try:
                preguntas = llm.make_quiz(
                    material,
                    title=titulo,
                    n=config.TRIVIA_QUESTIONS,
                    language=lang.current(),
                )
            except Exception as e:
                self.log(f"No pude preparar la trivia: {e}", "err")
                preguntas = []
            if not preguntas or not trivia.load(preguntas, titulo):
                trivia.reset()
                self._clear_trivia_screen()
                self._say_trivia(lang.say("trivia_failed"))
                return
            self.log(
                f"Trivia lista: {trivia.total()} preguntas sobre «{titulo}».", "ok"
            )
            self.set_voice_phase("speaking")
            tts.speak(lang.say("trivia_intro", total=trivia.total()), blocking=True)
            self._ask_trivia_question()

    def _ask_trivia_question(self) -> None:
        """Proyecta la pregunta actual y la lee en voz alta con sus opciones."""
        pregunta = trivia.current()
        if pregunta is None:
            self._finish_trivia()
            return
        self._emit_trivia()
        letras = trivia.LETTERS
        opciones = ". ".join(
            f"{letras[i]}. {op}" for i, op in enumerate(pregunta["options"])
        )
        texto = (
            lang.say("trivia_question_header", n=trivia.number(), total=trivia.total())
            + " " + pregunta["question"] + " " + opciones + "."
        )
        self.log(
            f"Pregunta {trivia.number()}/{trivia.total()}: {pregunta['question']}",
            "info",
        )
        self._say_trivia(texto)

    def handle_trivia_answer(self, text: str) -> None:
        """Interpreta la respuesta del visitante y revela el resultado."""
        if self._trivia_echo(text):
            return
        pregunta = trivia.current()
        if pregunta is None:
            self._finish_trivia()
            return
        self.state["last_transcript"] = text
        self.emit("transcript", text=text)
        eleccion = voice_phrases.parse_answer(text, pregunta["options"])
        if eleccion is None:
            # No se entendió (o dijo que no lo sabe). A la segunda se revela
            # la respuesta y se sigue: insistir con "decí A, B o C" a alguien
            # que no te entiende es la peor experiencia posible en un stand.
            if trivia.miss() >= 2:
                trivia.give_up()
                self._reveal_trivia()
            else:
                self.log(f"No entendí la respuesta: {text!r}", "warn")
                with self._talking_alone():
                    self._say_trivia(lang.say("trivia_repeat"))
            return
        acerto = trivia.answer(eleccion)
        self.log(
            f"Respondió {trivia.LETTERS[eleccion]} — "
            f"{'correcto' if acerto else 'incorrecto'}.",
            "ok" if acerto else "warn",
        )
        self._reveal_trivia()

    def _reveal_trivia(self) -> None:
        """Enseña el resultado en pantalla, lo dice, y pasa a la siguiente."""
        pregunta = trivia.current()
        snap = trivia.snapshot()
        self._emit_trivia(snap)          # la pantalla celebra o revela
        correcta = pregunta["correct"] if pregunta else 0
        letra = trivia.LETTERS[correcta]
        respuesta = pregunta["options"][correcta] if pregunta else ""
        if snap["result"] == "correct":
            texto = lang.say("trivia_correct")
        elif snap["result"] == "pass":
            texto = lang.say("trivia_pass", letter=letra, answer=respuesta)
        else:
            texto = lang.say("trivia_wrong", letter=letra, answer=respuesta)
        with self._talking_alone():
            # `listen=False`: aquí no toca contestar nada, y el chime sonaría
            # a destiempo justo antes de la siguiente pregunta.
            self._say_trivia(texto, listen=False)
            if trivia.advance():
                self._ask_trivia_question()
            else:
                self._finish_trivia()

    def _finish_trivia(self) -> None:
        """Marcador final: lo proyecta, lo dice y limpia la pantalla luego."""
        snap = trivia.snapshot()
        aciertos, total = snap["score"], snap["total"]
        self._emit_trivia(snap)
        if total and aciertos == total:
            texto = lang.say("trivia_perfect", total=total)
        elif not aciertos:
            texto = lang.say("trivia_zero")
        else:
            texto = lang.say("trivia_final", score=aciertos, total=total)
        self.log(f"Fin de la trivia: {aciertos} de {total}.", "ok")
        tts.speak(texto, blocking=True)
        trivia.reset()
        # El marcador se queda unos segundos en pantalla mientras MECH ya
        # vuelve a escuchar: por eso se limpia con un temporizador y no aquí.
        threading.Timer(
            config.TRIVIA_FINAL_SECONDS, self._clear_trivia_screen
        ).start()
        time.sleep(config.TRIVIA_DRAIN_SECONDS)
        self.chime_pending = True

    def stop_trivia(self, announce: bool = True) -> None:
        """Sale del juego (lo pidieron, se durmió, o paro de emergencia)."""
        if not trivia.is_active():
            return
        trivia.reset()
        self.log("Trivia cancelada.", "info")
        self._clear_trivia_screen()
        if announce:
            with self._talking_alone():
                tts.speak(lang.say("trivia_off"), blocking=True)
                time.sleep(config.TRIVIA_DRAIN_SECONDS)

    def answer_trivia_from_panel(self, choice: int) -> bool:
        """Responde desde el panel, sin micrófono (para probar el juego).

        Devuelve False si ahora mismo no hay una pregunta esperando.
        """
        pregunta = trivia.current()
        if not trivia.is_asking() or pregunta is None:
            return False
        if not (0 <= choice < len(pregunta["options"])):
            return False
        acerto = trivia.answer(choice)
        self.log(
            f"Respuesta desde el panel: {trivia.LETTERS[choice]} — "
            f"{'correcto' if acerto else 'incorrecto'}.",
            "ok" if acerto else "warn",
        )
        self._reveal_trivia()
        return True

    # ------------------------------------------------------------------
    # Subtítulos de la proyección (estilo cine: abajo, centrados)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Posición de reproducción (para sincronizar el visor VR)
    # ------------------------------------------------------------------

    def report_playback(
        self, url: str | None, position: float,
        index: int | None = None, slug: str | None = None,
    ) -> None:
        """La pantalla principal dice por qué segundo va el video que muestra.

        Sirve para que el visor VR del teléfono NO empiece el video desde
        cero: se engancha en el mismo punto que el proyector, que es el que
        va con el audio. Lo llama `POST /api/playback` cada pocos segundos.
        """
        if not url:
            self._playback = None
            self.state["playback"] = None
            return
        self._playback = {
            "url": url,
            "position": max(0.0, float(position)),
            "index": index,
            "slug": slug,
            "at": time.monotonic(),
        }
        snap = self.playback_snapshot()
        self.state["playback"] = snap
        # Por WebSocket llega al instante (age ~0); el sondeo HTTP del
        # teléfono recalcula la antigüedad al leerlo.
        self.emit("playback", **(snap or {}))

    def playback_snapshot(self) -> dict | None:
        """El último reporte + cuántos segundos han pasado desde entonces.

        Se manda `age` en vez de una marca de tiempo absoluta a propósito: el
        reloj del teléfono no tiene por qué coincidir con el de la Pi, y así
        el visor solo tiene que sumar (`position + age`).
        """
        p = self._playback
        if not p:
            return None
        return {
            "url": p["url"],
            "position": p["position"],
            "index": p["index"],
            "slug": p["slug"],
            "age": round(time.monotonic() - p["at"], 3),
        }

    def refresh_playback(self) -> None:
        """Actualiza `state["playback"]` con la antigüedad de AHORA.

        Lo llama `/api/state` antes de responder: el visor se alimenta de ese
        sondeo y necesita la antigüedad fresca, no la de cuando se reportó.
        """
        self.state["playback"] = self.playback_snapshot()

    def set_subtitle(self, text: str | None, code: str | None = None) -> None:
        """Publica (o borra con None) el subtítulo que se ve en la pantalla.

        Va al `state` ADEMÁS de emitirse por WebSocket porque la vista VR del
        teléfono se alimenta del sondeo HTTP a /api/state cuando el WS no
        conecta — sin esto, en el visor no habría subtítulos.

        `code` fuerza el idioma de la línea. Lo usa el modo traductor, que
        pinta la traducción en el idioma DESTINO aunque el idioma activo de
        MECH sea otro. Sin `code` se usa el activo, como siempre.
        """
        if text and not config.SUBTITLES_ENABLED:
            return  # apagados desde Ajustes (borrar SIEMPRE se permite)
        clean = (text or "").strip() or None
        idioma = code or lang.current()
        self.state["current_subtitle"] = clean
        self.state["subtitle_lang"] = idioma
        self.emit("subtitle", text=clean, lang=idioma)

    def stop_presentation(self) -> float:
        """Para TODO lo que forma parte de la presentación, de golpe.

        Voz, música de fondo, subtítulos, lo que se está proyectando y las
        ruedas. Se usa al interrumpir: si algo de esto sigue vivo mientras
        MECH pregunta qué querés, el audio se solapa y suena sucio.

        Devuelve los milisegundos que tardó en callarse la voz.
        """
        ms = 0.0
        try:
            ms = tts.request_stop() or 0.0
        except Exception:
            pass
        try:
            background_audio.stop()
        except Exception:
            pass
        self.stop_subtitles()
        self.clear_visual()  # el proyector deja de mostrar la obra
        # Si había una playlist promo sonando, `play_playlist` está esperando
        # a que la pantalla avise que terminó: lo soltamos aquí para que no
        # se quede colgado hasta el tope de tiempo.
        self._playlist_done.set()
        try:
            self.arduino.stop_motors()
        except Exception:
            pass
        return ms

    def _on_interrupt(self, text: str) -> None:
        """Alguien dijo "oye MECH" mientras MECH narraba: cortar YA.

        Lo llama el hilo del listener. Aquí se para toda la presentación y se
        marca la bandera; el bucle de `execute_plan` ve la bandera, deja de
        recorrer segmentos y pregunta qué quiere el visitante.
        """
        if self._narration_interrupted:
            # Ya estábamos cortando. Volver a cortar aquí mataría la pregunta
            # ("¿de qué quieres que hable?") a media palabra.
            return
        self._narration_interrupted = True
        self.log(f"Interrupción del visitante: {text!r}", "warn")
        ms = self.stop_presentation()
        if ms:
            self.log(f"Voz cortada en {ms:.0f} ms.", "info")
        # "oye MECH, cuéntame de Malpaís" → nos quedamos con la petición para
        # atenderla enseguida y que no tenga que repetirla.
        resto = voice_phrases.strip_interrupt(text)
        if len(resto.split()) >= 2:
            self.pending_command = resto
            self.log(f"Lo atiendo enseguida: {resto!r}", "info")

    def take_pending_command(self) -> str | None:
        """Devuelve (y limpia) la petición que quedó de una interrupción."""
        pendiente = self.pending_command
        self.pending_command = None
        return pendiente

    def start_subtitles(self, text: str, info: dict, code: str | None = None) -> None:
        """Arranca los subtítulos de `text` sincronizados con la voz.

        `code` fuerza el idioma del subtítulo. Hace falta para el saludo por
        cámara, que sale en `GREETING_LANGUAGE` (inglés) aunque MECH esté en
        español: sin esto, el subtítulo diría que es español y la pantalla lo
        etiquetaría mal. None = el idioma activo, que es lo normal.

        Lo llama `tts.speak` en el instante EXACTO en que empieza a sonar el
        audio, con su duración real (y, si ElevenLabs lo dio, el segundo de
        cada carácter). Antes se paceaban en el navegador a ojo — por eso se
        adelantaban en cuanto MECH hacía una pausa.
        """
        cues = subtitles.build_cues(
            text,
            duration=float(info.get("duration") or 0.0),
            char_times=info.get("char_times"),
            lead=float(info.get("lead") or 0.0),
        )
        self.stop_subtitles(clear=False)
        if not cues:
            return
        cancel = threading.Event()
        self._subs_cancel = cancel
        t0 = time.monotonic()

        def _run() -> None:
            for start, linea in cues:
                espera = start - (time.monotonic() - t0)
                if espera > 0 and cancel.wait(espera):
                    return  # nos cancelaron mientras esperábamos
                if cancel.is_set():
                    return
                self.set_subtitle(linea, code)

        threading.Thread(target=_run, daemon=True).start()

    def stop_subtitles(self, clear: bool = True) -> None:
        """Corta el hilo de subtítulos (y por defecto limpia la pantalla)."""
        if self._subs_cancel is not None:
            self._subs_cancel.set()
            self._subs_cancel = None
        if clear:
            self.set_subtitle(None)

    def go_dormant(self) -> None:
        """Pone a MECH en reposo: deja de responder (no gasta créditos), pero
        el bucle sigue oyendo para captar la palabra de despertar.

        IMPORTANTE: el mensaje de confirmación NO debe contener las palabras de
        despertar ("despierta"/"activa"), porque el micrófono sigue escuchando
        en reposo y, por el eco del parlante, captaría su propia voz diciendo
        "despierta MECH" y se despertaría solo."""
        self.state["voice_awake"] = False
        # Dormirse también saca del modo traductor y de la trivia (sin
        # anunciarlo: ya va a decir la frase de reposo justo aquí abajo).
        self.stop_translator(announce=False)
        self.stop_trivia(announce=False)
        self.log(
            "MECH en reposo. Di 'ok MECH' (o 'wake up MECH' para inglés).",
            "info",
        )
        tts.speak(lang.say("dormant"), blocking=True)
        # Pequeña pausa para que el parlante (sobre todo Bluetooth) drene su
        # buffer antes de volver a escuchar, y no captarse a sí mismo.
        time.sleep(0.8)
        # Al dormirse vuelve a español: el siguiente visitante del stand se
        # encuentra a MECH como siempre (el inglés hay que pedirlo de nuevo).
        self.set_language(lang.DEFAULT)
        self.stop_subtitles()
        self.set_voice_phase("dormant")

    def go_awake(self, language: str | None = None) -> None:
        """Despierta a MECH: vuelve a responder comandos.

        `language` = idioma con el que lo despertaron ("es" con "ok MECH",
        "en" con "wake up MECH"). El saludo ya sale en ese idioma.
        """
        if language:
            self.set_language(language)
        self.state["voice_awake"] = True
        # Animación de despertar del aro (como el aro azul de un Alexa Echo):
        # el usuario VE que el comando "ok MECH" funcionó, además de oírlo.
        self.set_led("WAKE")
        self.log(f"MECH despierto ({lang.label()}). Escuchando comandos.", "ok")
        tts.speak(lang.say("awake"), blocking=True)
        # El worker sonará el chime y drenará el parlante antes de grabar.
        self.chime_pending = True
        self.set_voice_phase("waiting")

    # ------------------------------------------------------------------
    # Visión (backend/vision.py llama estos hooks)
    # ------------------------------------------------------------------

    # Frase oficial de bienvenida (pedida por el equipo, jul 2026). En modo
    # inglés se dice su equivalente (ver backend/lang.py).
    # El texto vive en lang.py (una sola fuente para los cuatro idiomas); esta
    # constante se conserva porque está documentada y se usa en pruebas.
    GREETING_TEXT = lang.say("greeting", "es")

    # Fases en las que MECH está ocupado con alguien: no se le puede soltar
    # un saludo encima. `listening` incluida: está GRABANDO a un visitante.
    # Fases en las que MECH NO puede ponerse a saludar: está hablando,
    # procesando, grabando a alguien... o todavía arrancando ("loading",
    # mientras carga Whisper). Saludar recién encendido, antes de poder
    # escuchar la respuesta, deja al visitante hablándole a un robot sordo.
    _BUSY_PHASES = ("speaking", "thinking", "transcribing", "listening", "loading")

    def on_user_detected(self) -> None:
        """Alguien entró al campo de la cámara: MECH lo saluda.

        **Solo saluda EN REPOSO** (`GREETING_ONLY_DORMANT`, decisión del
        equipo de sep 2026). Despierto está narrando una obra, conversando o
        traduciendo, y soltar "¡Hola! Soy MECH" encima de eso le corta la
        experiencia al visitante que ya está atendiendo. En reposo es justo
        lo contrario: alguien se acerca al stand y MECH lo recibe.

        Con cooldown (`GREETING_COOLDOWN`) para no saludar en bucle a la
        misma persona. El gesto y la voz van JUNTOS y bajo el MISMO cooldown
        (antes el brazo se disparaba en cada detección, también dentro del
        cooldown: como la visión se pausa mientras narra, al terminar cada
        narración volvía a "detectar" y el brazo se movía solo, sin decir
        nada).
        """
        if config.GREETING_ONLY_DORMANT and self.state.get("voice_awake", True):
            self._log_greeting_skip(
                "No saludo al visitante: MECH está despierto (atendiendo a "
                "alguien). Se saluda solo en reposo."
            )
            return
        if self.state.get("voice_phase") in self._BUSY_PHASES:
            return  # no interrumpir una narración ni una grabación en curso
        if not self._greeting_rearmed():
            return  # es el mismo de antes, no un visitante nuevo
        now = time.time()
        if now - self._last_greeting < config.GREETING_COOLDOWN:
            return  # ya saludó hace poco
        self._perform_greeting()

    def _greeting_rearmed(self) -> bool:
        """¿Hay delante un visitante NUEVO, o es el mismo de antes?

        MECH saluda a quien llega, UNA vez. Para volver a saludar hace falta
        que la cámara se quede sin nadie durante `GREETING_REARM_SECONDS`
        seguidos — no basta con que el detector parpadee.

        Esto es lo que quita el saludo repetido "cada minuto aunque no haya
        nadie": `vision.LOST_AFTER_S` son 1.5 s, así que cualquier parpadeo
        (una cabeza que gira, un falso positivo con la luz de la proyección)
        contaba como una llegada nueva. El reloj de ausencia se REINICIA con
        cada pérdida, así que un detector que parpadea nunca lo completa.
        """
        if self._last_greeting == 0.0:
            return True  # todavía no ha saludado a nadie
        if self._user_gone_since is None:
            return False  # no se ha ido nadie desde el último saludo
        return time.time() - self._user_gone_since >= config.GREETING_REARM_SECONDS

    def _log_greeting_skip(self, mensaje: str) -> None:
        """Avisa de por qué NO saludó, como mucho una vez por minuto.

        La visión detecta a ~10 fps: sin el freno, esto llenaría el panel.
        """
        now = time.time()
        if now - self._last_greeting_skip_log < 60:
            return
        self._last_greeting_skip_log = now
        self.log(mensaje, "info")

    def _greeting_language(self) -> str:
        """Idioma en el que sale el saludo por cámara.

        `GREETING_LANGUAGE` (inglés por defecto). Si está vacío o trae algo
        que no reconocemos, se usa el idioma activo — que es como funcionaba
        antes, así que una clave mal escrita no deja a MECH mudo.
        """
        code = (config.GREETING_LANGUAGE or "").strip().lower()
        return code if code in lang.SUPPORTED else lang.current()

    def _perform_greeting(self) -> None:
        """El saludo en sí: brazo + voz, a la vez. Sin comprobar nada."""
        self._last_greeting = time.time()
        # A partir de aquí, quien está delante ya está saludado: hasta que la
        # cámara se quede vacía un buen rato, no hay "visitante nuevo".
        self._user_gone_since = None
        self.log("Saludo al visitante que detectó la cámara.", "ok")
        # El arco lento del brazo (config.ARM_WAVE_SECONDS) corre en paralelo
        # a la voz: gestures.perform ya lanza su propio hilo.
        gestures.perform(self.arduino, "wave")

        def _greet():
            # Ventana provisional amplia mientras habla; al terminar se
            # ajusta a un margen corto para drenar el eco del parlante.
            self.greeting_until = time.time() + 20
            # El saludo sale en `GREETING_LANGUAGE` (inglés por defecto), NO
            # en el idioma activo. Es lo primero que oye quien llega al
            # stand, y conviene que lo entienda cualquiera; el idioma de la
            # conversación lo sigue decidiendo la frase con que lo despierten.
            idioma = self._greeting_language()
            texto = lang.say("greeting", code=idioma)
            try:
                tts.speak(
                    texto,
                    blocking=True,
                    on_playback=lambda info: self.start_subtitles(
                        texto, info, code=idioma
                    ),
                )
            finally:
                self.greeting_until = time.time() + 1.5
                self.stop_subtitles()

        threading.Thread(target=_greet, daemon=True).start()

    def greet_now(self) -> None:
        """Saludo a mano (botón «SALUDAR AHORA» del panel).

        Se salta el COOLDOWN y la regla de "visitante nuevo" — para eso está,
        para poder probarlo sin salir y entrar del campo de la cámara.

        Pero **respeta la regla de "solo en reposo"** igual que el saludo por
        cámara (sep 2026, pedido del equipo: "que solo pueda saludar si está
        en reposo"). Antes era una excepción, y eso hacía que MECH saludara
        estando despierto cuando alguien pulsaba el botón — justo lo que se
        quería evitar. Ahora la regla es UNA y vale para todos los caminos.

        Para probar el saludo con MECH despierto, se apaga la regla en
        Ajustes → «Saludar por cámara solo en reposo».
        """
        if self.state.get("voice_phase") in self._BUSY_PHASES:
            self.log("No saludo: MECH está hablando o grabando ahora mismo.", "warn")
            return
        if config.GREETING_ONLY_DORMANT and self.state.get("voice_awake", True):
            self.log(
                "No saludo: MECH está DESPIERTO y el saludo solo va en "
                "reposo. Dormilo («duérmete MECH») o apagá la regla en "
                "Ajustes → «Saludar por cámara solo en reposo».",
                "warn",
            )
            return
        self._perform_greeting()

    def on_user_lost(self) -> None:
        """El usuario salió de cámara.

        Los motores ya los paró el módulo de visión. Lo que hacemos aquí es
        arrancar (o REINICIAR) el reloj de ausencia: cuando llegue a
        `GREETING_REARM_SECONDS` seguidos sin nadie, el siguiente que aparezca
        cuenta como visitante nuevo y se le saluda. Reiniciarlo en cada
        pérdida es lo que hace que un detector que parpadea no acumule.
        """
        self._user_gone_since = time.time()

    def user_in_range(self) -> bool:
        """True si hay un usuario dentro de la distancia mínima configurada.

        Si la visión está apagada, devuelve True (no bloquea la proyección)."""
        v = self.state.get("vision", {})
        if not v.get("enabled"):
            return True
        if not v.get("user_present"):
            return False
        dist = v.get("distance")
        return dist is not None and dist <= config.VISION_MIN_DISTANCE + 0.3

    # ------------------------------------------------------------------
    # Acciones de alto nivel — los endpoints del server las invocan
    # ------------------------------------------------------------------

    def emergency_stop(self) -> None:
        """PARO DE EMERGENCIA. Detiene motores, TTS, proyección, voz."""
        self.log("PARO DE EMERGENCIA activado", "err")
        # Motores y modo seguro
        try:
            self.arduino.stop_motors()
            self.arduino.set_mode("STOP")
            self.set_led("ERR")  # parpadeo rojo en el aro y se apaga
            # Tras un paro, la posición ya no es confiable: el punto donde
            # quede el robot pasa a ser el nuevo inicio. Lo mismo con la
            # ORIENTACIÓN: damos por hecho que el operador lo recoloca a
            # mano, para no disparar un giro "de vuelta" a ciegas.
            self.arduino.reset_odometer()
            maneuvers.assume_projection(self)
        except Exception as e:
            self.log(f"Arduino no respondió al paro: {e}", "err")
        # Audio (TTS en curso + música de fondo)
        try:
            tts.request_stop()  # corta el reproductor de voz actual
        except Exception:
            pass
        try:
            sd.stop()
        except Exception:
            pass
        try:
            background_audio.stop()
        except Exception:
            pass
        # Voz
        self.state["voice_loop_active"] = False
        # Modo traductor y trivia: se apagan sin anunciarlo (el TTS acaba de
        # cortarse, así que no habría con qué decirlo).
        try:
            self.stop_translator(announce=False)
        except Exception:
            pass
        try:
            trivia.reset()
            self._clear_trivia_screen()
        except Exception:
            pass
        # Proyección
        self.state["current_image"] = None
        self.state["current_video"] = None
        self.state["current_playlist"] = None
        self.emit("image", url=None)
        self.emit("video", url=None)
        self.emit("playlist", playlist=None)
        self._playlist_done.set()
        self.stop_subtitles()
        try:
            self.interrupts.stop()
        except Exception:
            pass
        for pid in ("s1", "s2", "imm"):
            self.state["projectors"][pid]["on"] = False
        self.emit("state", state=self.state)

    def set_projector(self, pid: str, on: bool, file_url: str | None = None) -> None:
        if pid not in self.state["projectors"]:
            self.log(f"Proyector desconocido: {pid}", "err")
            return
        self.state["projectors"][pid]["on"] = on
        if file_url is not None:
            self.state["projectors"][pid]["file"] = file_url
        self.emit("projector", id=pid, on=on, file=self.state["projectors"][pid]["file"])
        self.log(f"Proyector {pid}: {'ON' if on else 'OFF'}", "ok" if on else "info")

    def show_ai_image(self, image_path: Path) -> None:
        """Llamado desde el bucle de voz cuando Claude+NanoBanana
        generan una imagen. La publica al canal de proyección AI."""
        # URL relativa servida por el server estático.
        url = f"/generated/{image_path.name}"
        self.state["current_image"] = url
        self.state["current_video"] = None
        self.emit("image", url=url)

    def clear_visual(self) -> None:
        """Borra el visual actual (imagen o video) y avisa a panel/proyector.

        Se llama al empezar una historia nueva: si la nueva no trae video ni
        imagen, no queremos que quede colgado el video de la historia anterior.
        Si la nueva SÍ trae video, el primer segmento lo pone enseguida.
        """
        self.state["current_image"] = None
        self.state["current_video"] = None
        self.state["current_playlist"] = None
        self._playback = None
        self.state["playback"] = None
        self.emit("image", url=None)
        self.emit("video", url=None)
        self.emit("playlist", playlist=None)
        self.emit("playback", url=None)

    def show_library_segment(self, slug: str, segment: int) -> None:
        """Muestra el material de un segmento de la biblioteca, que puede ser
        un VIDEO (loop) o una IMAGEN (foto fija de una obra)."""
        url = video_library.segment_url(slug, segment)
        kind = video_library.segment_kind(slug, segment)
        if kind == "image":
            self.state["current_image"] = url
            self.state["current_video"] = None
            self.emit("image", url=url)
        else:
            self.state["current_video"] = url
            self.state["current_image"] = None
            self.emit("video", url=url)

    # Alias retro-compatible.
    show_library_video = show_library_segment

    def _render_segment_visual(self, seg: "llm.Segment", plan_title: str, idx: int) -> None:
        """Decide qué visual mostrar para un segmento del plan.

        Prioridad:
          1. Video pre-renderizado (video_slug + video_segment), si existe en disco.
          2. Imagen generada con NanoBanana (image_prompt).
          3. Nada (mantiene el visual anterior).
        """
        # Material de biblioteca (video o imagen)
        image_prompt = seg.image_prompt
        if seg.video_slug and seg.video_segment:
            if video_library.segment_exists(seg.video_slug, seg.video_segment):
                self.show_library_segment(seg.video_slug, seg.video_segment)
                return
            # Si Claude pidió un video que no existe, avisamos y caemos a imagen.
            self.log(
                f"Video no encontrado: {seg.video_slug}/"
                f"{video_library.segment_filename(seg.video_segment)}. "
                "Cayendo a NanoBanana.",
                "warn",
            )
            if not image_prompt:
                # Claude confió en la biblioteca y no trajo image_prompt: para
                # no dejar la proyección vacía, generamos una imagen genérica
                # de la obra a partir de su título.
                meta = video_library.WORKS.get(seg.video_slug)
                if meta:
                    image_prompt = (
                        f"{meta['title']}, cinematic cultural exhibition "
                        "scene, painterly style, dramatic lighting"
                    )
                    self.log(
                        "Segmento sin image_prompt: genero imagen genérica de la obra.",
                        "info",
                    )
        # Fallback / flujo original
        if image_prompt:
            try:
                img = image_gen.generate_image(
                    image_prompt,
                    filename=f"{plan_title.replace(' ', '_')}_{idx}.png",
                )
                self.show_ai_image(img)
            except Exception as e:
                self.log(f"Imagen falló: {e}", "err")

    # ------------------------------------------------------------------
    # Playlist promo (marketing): videos enteros, en fila y CON SU AUDIO
    # ------------------------------------------------------------------

    def play_playlist(self, slug: str) -> bool:
        """Reproduce un slot promo (ej. "marketing") de principio a fin.

        A diferencia de una historia normal, aquí MECH **no narra**: los
        videos traen su propio audio y se reproducen ENTEROS, uno tras otro,
        saltándose los espacios vacíos. MECH se calla y deja que suenen.

        Quién manda el tiempo: la PANTALLA. El backend no sabe cuánto dura
        cada mp4, así que manda la lista entera al proyector y este avisa por
        `POST /api/playlist/ended` cuando termina el último. Solo si no hay
        ninguna pantalla abierta entra el tope de `MARKETING_MAX_SECONDS`.

        Devuelve True si llegó a reproducir algo.
        """
        items = video_library.playlist(slug)
        meta = video_library.WORKS.get(slug, {})
        titulo = meta.get("title", slug)
        if not items:
            self.log(
                f"El slot '{titulo}' no tiene ningún video todavía. "
                f"Subilos en /library.",
                "warn",
            )
            tts.speak(lang.say("empty_playlist"), blocking=True)
            return False

        # Igual que una narración: si quedó de espaldas o desplazado, vuelve a
        # su sitio para que la proyección apunte a donde está calibrada.
        try:
            if maneuvers.facing(self) == "outward":
                maneuvers.back_to_projection(self, announce=False)
            self.return_to_start()
        except Exception as e:
            self.log(f"No pude recolocarme antes de proyectar: {e}", "warn")

        videos = sum(1 for i in items if i["kind"] == "video")
        self.log(
            f"Proyectando '{titulo}': {len(items)} archivos "
            f"({videos} con audio propio). MECH se queda callado.",
            "ok",
        )
        if not self._subscribers:
            self.log(
                "OJO: no hay ninguna pantalla conectada (/projector). "
                "Abrí el proyector para verlo.",
                "warn",
            )

        self.arduino.set_mode("SPEAK")
        self.set_voice_phase("speaking")  # el bucle de voz no abre el micrófono
        tts.clear_stop()
        self.clear_visual()
        self._narration_interrupted = False
        self.pending_command = None
        self._playlist_done.clear()

        payload = {
            "slug": slug,
            "title": titulo,
            "items": items,
            "audio": True,   # la pantalla NO debe silenciarlos
        }
        self.state["current_playlist"] = payload
        self.emit("playlist", playlist=payload)

        # Se puede cortar con "oye MECH" como cualquier presentación.
        if self.interrupts.start():
            self.log("Podés decir 'oye MECH' para cortar el video.", "info")
        self._playlist_failures = []
        self._playlist_played = 0
        t0 = time.monotonic()
        try:
            terminado = self._playlist_done.wait(timeout=config.MARKETING_MAX_SECONDS)
            transcurrido = time.monotonic() - t0
            if not terminado and not self._narration_interrupted:
                self.log(
                    "Se acabó el tiempo máximo de la proyección "
                    "(¿había alguna pantalla abierta?).",
                    "warn",
                )
            elif not self._narration_interrupted:
                self._report_playlist_failures(titulo, transcurrido)
                # Terminar casi al instante nunca es normal con videos de
                # verdad: si la pantalla no reportó fallos, el aviso genérico
                # al menos deja rastro de que algo raro pasó.
                if transcurrido < 3 and not self._playlist_failures:
                    self.log(
                        f"OJO: '{titulo}' terminó en {transcurrido:.1f} s. "
                        "Con videos reales eso no es normal — revisá que los "
                        "archivos se abran en el navegador "
                        "(http://<pi>:8000/videos/marketing/seg01.mp4).",
                        "warn",
                    )
        finally:
            self.interrupts.stop()
            self.state["current_playlist"] = None
            self.emit("playlist", playlist=None)
            self.clear_visual()
            self.arduino.set_mode("IDLE")
            if self._narration_interrupted:
                self.stop_presentation()
                tts.clear_stop()
                if not self.pending_command:
                    time.sleep(0.4)
                    tts.speak(lang.say("interrupted"), blocking=True)
                    time.sleep(0.5)
                    self.chime_pending = True
            # (el resumen de cómo terminó ya se logueó arriba, con detalle
            # de los archivos que la pantalla no pudo reproducir)
        return True

    # Códigos de error de <video> (HTML MediaError), en cristiano.
    _MEDIA_ERR = {
        1: "cancelado",
        2: "error de red al descargarlo",
        3: "el navegador no pudo DECODIFICARLO (¿codec raro?)",
        4: "formato no soportado por el navegador",
    }

    def playlist_finished(
        self, slug: str | None = None,
        played: int = 0, failed: list | None = None,
    ) -> bool:
        """La pantalla avisa que terminó el último video de la playlist.

        `failed` son los archivos que NO pudo reproducir. Importa mucho: si
        el navegador no sabe decodificarlos, la playlist "termina" en
        milisegundos y sin esto parecería que la proyección salió bien.
        """
        actual = self.state.get("current_playlist")
        if not actual:
            return False
        if slug and slug != actual.get("slug"):
            return False
        self._playlist_failures = list(failed or [])
        self._playlist_played = int(played)
        self._playlist_done.set()
        return True

    def _report_playlist_failures(self, titulo: str, segundos: float) -> None:
        """Explica en el panel por qué una proyección no salió como debía."""
        fallos = getattr(self, "_playlist_failures", []) or []
        reproducidos = getattr(self, "_playlist_played", 0)

        if not fallos:
            self.log(f"'{titulo}' terminó ({reproducidos} archivo(s), "
                     f"{segundos:.0f} s).", "ok")
            return

        detalle = []
        for f in fallos:
            nombre = str(f.get("url", "?")).rsplit("/", 1)[-1]
            motivo = self._MEDIA_ERR.get(f.get("code"), "no se pudo reproducir")
            detalle.append(f"{nombre}: {motivo}")
        self.log(
            f"LA PANTALLA NO PUDO REPRODUCIR {len(fallos)} archivo(s) de "
            f"'{titulo}' — " + " · ".join(detalle),
            "err",
        )
        if reproducidos == 0:
            self.log(
                "No se reprodujo NINGUNO, por eso terminó al instante. Casi "
                "siempre es el CODEC: Chromium no lee H.265/HEVC. Reconvertí "
                "los videos a H.264 con: ffmpeg -i original.mp4 -c:v libx264 "
                "-crf 23 -c:a aac -b:a 192k seg01.mp4",
                "err",
            )

    def return_to_start(self) -> None:
        """Vuelve al punto donde el robot empezó (odómetro adelante/atrás),
        para que la proyección no quede desfasada tras acercarse a alguien.

        Es una estimación por tiempo (sin encoders): suficiente para el
        stand. Con tope de seguridad de 6 s de retorno."""
        net = self.arduino.net_forward()
        if abs(net) < 8:  # desplazamiento despreciable
            self.arduino.reset_odometer()
            return
        # A fondo: a media potencia estos motores no arrancan. El odómetro
        # está en unidades %vel·s, así que a más velocidad, menos tiempo.
        speed = max(10, min(100, config.RETURN_SPEED))
        secs = min(abs(net) / speed, 6.0)
        self.log(
            f"Volviendo al punto de inicio ({secs:.1f} s hacia "
            f"{'atrás' if net > 0 else 'adelante'}) para proyectar alineado.",
            "info",
        )
        # Sin esto, el bucle de voz manda MODE:LISTEN a media vuelta y el
        # firmware para los motores (ver arduino_link.set_mode).
        self.wheels_busy.set()
        try:
            self.arduino.move(-speed if net > 0 else speed, 0, 0)
            time.sleep(secs)
            self.arduino.stop_motors()
            self.arduino.reset_odometer()
        finally:
            self.wheels_busy.clear()

    def execute_plan(self, plan: "llm.Plan") -> None:
        """Ejecuta el plan de Claude (varios segmentos)."""
        # Si quedó de espaldas ("mira hacia afuera"), primero vuelve a mirar a
        # la proyección: no tiene sentido narrar una historia proyectando
        # contra el público. Deshace el giro él solo, sin que se lo pidan.
        try:
            if maneuvers.facing(self) == "outward":
                self.log("Estaba de espaldas: vuelvo a la posición de proyectar.", "info")
                maneuvers.back_to_projection(self, announce=False)
        except Exception as e:
            self.log(f"No pude volver a la posición de proyección: {e}", "warn")
        # Si la visión acercó a MECH hacia el usuario, primero regresa a su
        # sitio: el proyector debe apuntar a donde estaba calibrado.
        try:
            self.return_to_start()
        except Exception as e:
            self.log(f"No pude volver al inicio: {e}", "warn")
        self.arduino.set_mode("SPEAK")
        self.set_voice_phase("speaking")
        tts.clear_stop()  # rehabilita la voz por si un paro la había cortado
        # Historia nueva → limpiamos el visual anterior. Cada segmento pondrá
        # el suyo (video o imagen); si ninguno trae, la pantalla queda limpia
        # en vez de mostrar el video de la historia anterior.
        self.clear_visual()
        # Gate de proyección por distancia: si la visión está activa y NO hay
        # un usuario dentro de la distancia mínima, narramos sin proyectar.
        project_ok = (not config.VISION_PROJECT_GATE) or self.user_in_range()
        if not project_ok:
            self.log(
                "Sin usuario dentro de la distancia mínima: narro sin proyectar.",
                "warn",
            )
        # Música de fondo (solo exposiciones que la tengan, ej. Malpaís).
        self._start_background_music(plan)
        # Escucha de interrupción: durante TODO el plan (también en las pausas
        # en que genera imágenes) se puede decir "oye MECH" para cortarlo.
        self._narration_interrupted = False
        self.pending_command = None
        guion = " ".join(seg.narration for seg in plan.segments)
        if self.interrupts.start(guard_text=guion):
            self.log("Puedes decir 'oye MECH' para interrumpirme.", "info")
        # Lo que de verdad llegó a sonar. Es lo que se usa para la trivia: si
        # lo interrumpen a la mitad, preguntar por lo que no oyó sería injusto.
        narrados: list[str] = []
        try:
            for i, seg in enumerate(plan.segments, 1):
                if self._narration_interrupted:
                    self.log("Narración interrumpida por el visitante.", "warn")
                    break
                if not self.state["voice_loop_active"]:
                    # Aborted (emergency stop o stop_voice)
                    self.log("Plan abortado", "warn")
                    return
                visual_kind = (
                    "video" if (seg.video_slug and seg.video_segment) else
                    ("imagen" if seg.image_prompt else "sin visual")
                )
                self.log(
                    f"Segmento {i}/{len(plan.segments)} — {seg.gesture} — {visual_kind}",
                    "info",
                )
                if project_ok:
                    self._render_segment_visual(seg, plan.title, i)
                # Gesto del segmento. Al narrar se usa la versión SIMPLE (un
                # solo brazo, corto y sin ruedas): la proyección tiene que
                # mandar y los servos casi no gastan. Ver backend/gestures.py.
                # EXCEPCIÓN: en modo "movement" le pidieron el gesto en sí
                # ("saluda al público"), así que ahí va la coreografía
                # completa — si no, un "saluda" se vería como un tic.
                if plan.mode == "movement":
                    gestures.perform(self.arduino, seg.gesture)
                else:
                    gestures.perform_talking(self.arduino, seg.gesture)
                self.state["last_ai_response"] = seg.narration
                voice_id = voices.resolve(seg.voice)
                self.emit(
                    "ai_response",
                    text=seg.narration,
                    segment=i,
                    total=len(plan.segments),
                    voice=seg.voice or "narrator",
                )
                # Los subtítulos (estilo cine, abajo) los dispara el propio
                # TTS cuando empieza a sonar la voz, así van a su ritmo real
                # y se quedan quietos en las pausas.
                tts.speak(
                    seg.narration,
                    blocking=True,
                    voice_id=voice_id,
                    on_playback=lambda info, t=seg.narration: self.start_subtitles(t, info),
                )
                self.stop_subtitles()  # calló: fuera el texto hasta el próximo
                narrados.append(seg.narration)
        finally:
            self.interrupts.stop()
            background_audio.stop()
            self.stop_subtitles()  # se acabó el guion: pantalla sin texto
            if self._narration_interrupted:
                # Nos aseguramos de que NADA de la presentación siga vivo
                # (por si nos interrumpieron entre segmentos) y dejamos los
                # brazos en reposo. Solo entonces hablamos.
                self.stop_presentation()
                try:
                    gestures.perform(self.arduino, "neutral")
                except Exception:
                    pass
                # La voz estaba cortada a propósito; la rehabilitamos para
                # poder contestar.
                tts.clear_stop()
                if self.pending_command:
                    # Ya dijeron qué querían ("oye MECH, cuéntame de X"): no
                    # los hacemos esperar una pregunta que sobra.
                    self.log("Atiendo lo que me pediste al interrumpirme.", "info")
                else:
                    # Pregunta explícita + el chime de "puedes hablar" (el
                    # mismo de después de "ok MECH"), para que se note que
                    # ahora le toca al visitante.
                    # La pausa es importante: el parlante (sobre todo por
                    # Bluetooth) todavía tiene dentro el final de la
                    # narración, y si hablamos encima se oye sucio.
                    time.sleep(0.4)
                    tts.speak(lang.say("interrupted"), blocking=True)
                    time.sleep(0.5)  # que el parlante drene antes de escuchar
                    self.chime_pending = True
                    self.log("Te escucho: dime de qué quieres que hable.", "ok")
            # Lo narrado se recuerda SIEMPRE (también si lo interrumpieron):
            # así un "juguemos una trivia" posterior pregunta sobre esto.
            self._remember_presentation(plan, narrados)
            if not self._narration_interrupted and self.should_offer_trivia(plan):
                # Se acabó la presentación y nadie la cortó: el mejor momento
                # para proponer el juego.
                self.offer_trivia(plan.title)
            self.arduino.set_mode("IDLE")

    def _start_background_music(self, plan: "llm.Plan") -> None:
        """Arranca la música de fondo si el plan la pide y el sample existe."""
        slug = getattr(plan, "background_music", None)
        if not slug:
            return
        path = video_library.background_audio_path(slug)
        if path is None:
            self.log(f"Música pedida pero sin sample en disco: {slug}", "warn")
            return
        if background_audio.start(path):
            self.log(f"Música de fondo: {slug}", "ok")
        else:
            self.log("No se pudo iniciar la música (¿falta ffplay?)", "warn")

    def handle_movement_command(self, text: str) -> bool:
        """¿Es una orden de movimiento? Si sí, la ejecuta y devuelve True.

        Son órdenes DIRECTAS: no pasan por Claude (respuesta inmediata y sin
        gastar crédito de API). Hoy hay dos:
            "mira hacia afuera"   -> gira 180° y saluda al público.
            "regresa a proyectar" -> deshace el giro.
        """
        # "avanza diez segundos" / "retrocede cinco segundos". El número es
        # opcional: sin él se usa el configurado en Ajustes.
        if voice_phrases.is_advance(text) or voice_phrases.is_retreat(text):
            atras = voice_phrases.is_retreat(text)
            maneuvers.advance(self, voice_phrases.extract_seconds(text), backwards=atras)
            return True
        if voice_phrases.is_look_outward(text):
            maneuvers.look_outward(self)
            return True
        if voice_phrases.is_back_to_projection(text):
            maneuvers.back_to_projection(self)
            return True
        # "proyecta marketing": la playlist promo, con su propio audio y sin
        # narración. Va aquí (y no por Claude) porque el modelo la contaría
        # como una obra: hablaría encima de los videos.
        if voice_phrases.is_play_marketing(text):
            self.play_playlist("marketing")
            return True
        return False

    def handle_text_command(self, text: str) -> None:
        """Procesa un comando de texto (de voz o frontend)."""
        if not text.strip():
            return
        self.state["last_transcript"] = text
        self.emit("transcript", text=text)
        self.log(f"Comando: {text!r}", "info")
        # REPOSO: "duérmete MECH". Va lo PRIMERO de todo y no pasa por Claude.
        #
        # ⚠️ Esto está aquí porque el equipo reportó (sep 2026) que a veces
        # MECH "decía una frase larga sobre que se iba a modo reposo, pero
        # volvía a abrir el micrófono". Era exactamente eso: la frase no
        # casaba con la lista, el texto llegaba a Claude, Claude improvisaba
        # una despedida bonita... y MECH NO se dormía, porque dormirse no es
        # algo que un plan pueda hacer. Interceptándolo aquí, cualquier
        # camino que llegue a un comando de texto (voz, panel, petición
        # pendiente tras un "oye MECH") duerme a MECH de verdad.
        if voice_phrases.is_sleep_any(text):
            self.log("Me piden reposo: me duermo (sin pasar por Claude).", "info")
            self.go_dormant()
            return
        # Traductor. El ORDEN importa: "desactiva el modo traductor" contiene
        # "modo traductor", así que apagar se mira antes que encender.
        if config.TRANSLATOR_ENABLED:
            if voice_phrases.is_translate_stop(text):
                self.stop_translator()
                return
            # "activa modo traductor": se queda traduciendo hasta que le digan
            # que lo desactive.
            if voice_phrases.is_translate_on(text):
                src, dst = voice_phrases.extract_language_pair(text)
                self.start_translator(src, dst, continuous=True)
                return
            # "traduce MECH": UNA frase y se calla. Si el comando nombra los
            # idiomas ("traduce MECH del inglés al portugués"), se toman de
            # ahí; si no, se reutiliza el par de la vez anterior y, si tampoco
            # lo hay, MECH pregunta.
            if voice_phrases.is_translate(text):
                src, dst = voice_phrases.extract_language_pair(text)
                self.start_translator(src, dst)
                return
        # Trivia. Igual que el traductor, salir se mira ANTES que entrar.
        if config.TRIVIA_ENABLED:
            if voice_phrases.is_trivia_stop(text):
                self.stop_trivia()
                return
            if voice_phrases.is_trivia(text):
                self.start_trivia()
                return
        # Órdenes de movimiento: se atienden aquí mismo, sin llamar a Claude.
        if self.handle_movement_command(text):
            if self.state["voice_loop_active"]:
                self.chime_pending = True
                self.set_voice_phase(
                    "waiting" if self.state.get("voice_awake", True) else "dormant"
                )
            return
        # Que el bucle de voz suelte el micrófono: a partir de aquí manda el
        # listener de interrupción ("oye MECH").
        self.mic_release.set()
        try:
            self.set_voice_phase("thinking")
            plan = llm.plan_response(
                text,
                conversation_history=self.history,
                language=lang.current(),
            )
            self.log(f"Plan: {plan.mode} — {plan.title}", "ok")
            # Tercera red del modo reposo: la frase no casó con ninguna lista
            # (Whisper la deformó), pero Claude sí entendió que le pedían
            # callarse. Nos dormimos aquí, SIN narrar el plan: si no, MECH
            # soltaría una despedida improvisada y seguiría despierto — el
            # fallo exacto que reportó el equipo (sep 2026).
            if plan.mode == "sleep":
                self.log("Claude entendió que me piden reposo: me duermo.", "info")
                self.go_dormant()
                return
            self.execute_plan(plan)
            self.history = llm.append_turn(self.history, text, plan)
            if len(self.history) > 12:
                self.history = self.history[-12:]
        except Exception as e:
            self.log(f"Error procesando comando: {e}", "err")
            tts.speak(lang.say("error"), blocking=True)
        finally:
            # Si quedó en reposo, mantenemos "dormant" (sin sonido).
            if not self.state.get("voice_awake", True):
                self.set_voice_phase("dormant")
            elif self.state["voice_loop_active"]:
                # Terminó de presentar y sigue activo: pedimos que el worker
                # suene el chime ANTES de empezar a grabar de nuevo.
                self.chime_pending = True
                self.set_voice_phase("waiting")
            else:
                self.set_voice_phase("off")
            self.mic_release.clear()  # el bucle puede volver a grabar

    def close(self) -> None:
        try:
            self.arduino.close()
        except Exception:
            pass


_app: MechApp | None = None


def get_app() -> MechApp:
    global _app
    if _app is None:
        _app = MechApp()
    return _app
