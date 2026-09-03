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
from pathlib import Path
from typing import Any, Awaitable, Callable

import sounddevice as sd

import config
import gestures
import image_gen
import lang
import llm
import maneuvers
import background_audio
import subtitles
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
        # Subtítulos: hilo que va sacando las líneas al ritmo real de la voz.
        self._subs_cancel: threading.Event | None = None
        # Mientras esto está activo, las RUEDAS están en medio de una maniobra
        # (giro de 180°, vuelta al punto de inicio). El bucle de voz no debe
        # tocar el modo del Arduino en ese rato: `MODE:LISTEN` ejecuta
        # `stopAllMotors()` en el firmware y cortaría el movimiento.
        self.wheels_busy = threading.Event()

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
            # Hacia dónde mira el robot: "projection" (a la superficie
            # donde proyecta, que es su sitio de trabajo) u "outward" (de
            # espaldas, saludando al público). Lo cambia backend/maneuvers.py
            # con las órdenes "mira hacia afuera" / "regresa a proyectar".
            "facing": "projection",
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
        print(f"[{level}] {message}")
        self.emit("log", message=message, level=level, ts=time.time())

    # Patrón del aro de LEDs (estilo Alexa) para cada fase de voz.
    _LED_BY_PHASE = {
        "off": "OFF",
        "dormant": "IDLE",
        "waiting": "LISTEN",
        "listening": "LISTEN",
        "transcribing": "THINK",
        "thinking": "THINK",
        "speaking": "SPEAK",
    }

    def set_voice_phase(self, phase: str) -> None:
        """Actualiza la fase del ciclo de voz y la difunde al panel.

        Fases: off | waiting | listening | transcribing | thinking | speaking.
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
    # Subtítulos de la proyección (estilo cine: abajo, centrados)
    # ------------------------------------------------------------------

    def set_subtitle(self, text: str | None) -> None:
        """Publica (o borra con None) el subtítulo que se ve en la pantalla.

        Va al `state` ADEMÁS de emitirse por WebSocket porque la vista VR del
        teléfono se alimenta del sondeo HTTP a /api/state cuando el WS no
        conecta — sin esto, en el visor no habría subtítulos.
        """
        if text and not config.SUBTITLES_ENABLED:
            return  # apagados desde Ajustes (borrar SIEMPRE se permite)
        clean = (text or "").strip() or None
        self.state["current_subtitle"] = clean
        self.state["subtitle_lang"] = lang.current()
        self.emit("subtitle", text=clean, lang=lang.current())

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

    def start_subtitles(self, text: str, info: dict) -> None:
        """Arranca los subtítulos de `text` sincronizados con la voz.

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
                self.set_subtitle(linea)

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
    # El texto vive en lang.py (una sola fuente para los dos idiomas); esta
    # constante se conserva porque está documentada y se usa en pruebas.
    GREETING_TEXT = lang.say("greeting", "es")

    def on_user_detected(self) -> None:
        """Alguien entró al campo de la cámara: MECH hace el protocolo de
        saludo (arco de brazo del video del equipo) y da la bienvenida por
        voz. Con cooldown para no saludar en bucle a la misma persona.

        El gesto y la voz van JUNTOS y bajo el MISMO cooldown (antes el brazo
        se disparaba en cada detección, también dentro del cooldown: como la
        visión se pausa mientras narra, al terminar cada narración volvía a
        "detectar" y el brazo se movía solo, sin decir nada)."""
        if self.state.get("voice_phase") in ("speaking", "thinking", "transcribing"):
            return  # no interrumpir una narración
        now = time.time()
        if now - self._last_greeting < config.GREETING_COOLDOWN:
            return  # ya saludó hace poco
        self._last_greeting = now
        self.log("Saludo al visitante que detectó la cámara.", "ok")
        # El arco lento del brazo (config.ARM_WAVE_SECONDS) corre en paralelo
        # a la voz: gestures.perform ya lanza su propio hilo.
        gestures.perform(self.arduino, "wave")

        def _greet():
            # Ventana provisional amplia mientras habla; al terminar se
            # ajusta a un margen corto para drenar el eco del parlante.
            self.greeting_until = time.time() + 20
            texto = lang.say("greeting")
            try:
                tts.speak(
                    texto,
                    blocking=True,
                    on_playback=lambda info: self.start_subtitles(texto, info),
                )
            finally:
                self.greeting_until = time.time() + 1.5
                self.stop_subtitles()

        threading.Thread(target=_greet, daemon=True).start()

    def greet_now(self) -> None:
        """Fuerza el saludo AHORA, saltándose el cooldown (botón del panel).

        Sirve para probar el saludo sin tener que salir y volver a entrar al
        campo de la cámara."""
        self._last_greeting = 0.0
        self.on_user_detected()

    def on_user_lost(self) -> None:
        """El usuario salió de cámara. (El propio módulo de visión ya detuvo
        los motores; aquí solo queda el hook por si se quiere más lógica.)"""

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
        # Proyección
        self.state["current_image"] = None
        self.state["current_video"] = None
        self.emit("image", url=None)
        self.emit("video", url=None)
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
        self.emit("image", url=None)
        self.emit("video", url=None)

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

    def return_to_start(self) -> None:
        """Vuelve al punto donde el robot empezó (odómetro adelante/atrás),
        para que la proyección no quede desfasada tras acercarse a alguien.

        Es una estimación por tiempo (sin encoders): suficiente para el
        stand. Con tope de seguridad de 6 s de retorno."""
        net = self.arduino.net_forward()
        if abs(net) < 8:  # desplazamiento despreciable
            self.arduino.reset_odometer()
            return
        speed = 40
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
        if voice_phrases.is_look_outward(text):
            maneuvers.look_outward(self)
            return True
        if voice_phrases.is_back_to_projection(text):
            maneuvers.back_to_projection(self)
            return True
        return False

    def handle_text_command(self, text: str) -> None:
        """Procesa un comando de texto (de voz o frontend)."""
        if not text.strip():
            return
        self.state["last_transcript"] = text
        self.emit("transcript", text=text)
        self.log(f"Comando: {text!r}", "info")
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
