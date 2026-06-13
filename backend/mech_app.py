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
import llm
import background_audio
import tts
import video_library
import voices
from arduino_link import ArduinoLink, get_link

EventCallback = Callable[[dict], Awaitable[None]]


class MechApp:
    """Singleton con el estado global y un event bus para WebSockets."""

    def __init__(self) -> None:
        self.arduino: ArduinoLink = get_link()
        self.history: list[dict] = []
        self._narration_interrupted: bool = False
        # Cuando MECH termina de hablar y queda listo para escuchar, se marca
        # esto para que el worker suene el chime ANTES de abrir el micrófono.
        self.chime_pending: bool = False
        # Último patrón enviado al aro de LEDs (para no repetir comandos).
        self._last_led: str | None = None
        # Throttle del nivel de micrófono que se emite al panel.
        self._last_mic_level_emit: float = 0.0

        self.state: dict[str, Any] = {
            "voice_loop_active": False,
            "voice_listening": False,
            # voice_awake: dentro de un bucle activo, si MECH responde (True) o
            # está en reposo escuchando solo la palabra para despertar (False).
            "voice_awake": True,
            # Fase detallada del ciclo de voz para el panel. Una de:
            # off | dormant | waiting | listening | transcribing | thinking | speaking
            "voice_phase": "off",
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
            self.arduino.set_mode(self.state.get("current_mode", "IDLE"))
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

    def go_dormant(self) -> None:
        """Pone a MECH en reposo: deja de responder (no gasta créditos), pero
        el bucle sigue oyendo para captar la palabra de despertar.

        IMPORTANTE: el mensaje de confirmación NO debe contener las palabras de
        despertar ("despierta"/"activa"), porque el micrófono sigue escuchando
        en reposo y, por el eco del parlante, captaría su propia voz diciendo
        "despierta MECH" y se despertaría solo."""
        self.state["voice_awake"] = False
        self.log("MECH en reposo. Di 'ok MECH' para reactivarlo.", "info")
        tts.speak("De acuerdo, hasta luego.", blocking=True)
        # Pequeña pausa para que el parlante (sobre todo Bluetooth) drene su
        # buffer antes de volver a escuchar, y no captarse a sí mismo.
        time.sleep(0.8)
        self.set_voice_phase("dormant")

    def go_awake(self) -> None:
        """Despierta a MECH: vuelve a responder comandos."""
        self.state["voice_awake"] = True
        # Animación de despertar del aro (como el aro azul de un Alexa Echo):
        # el usuario VE que el comando "ok MECH" funcionó, además de oírlo.
        self.set_led("WAKE")
        self.log("MECH despierto. Escuchando comandos.", "ok")
        tts.speak("Hola, ya te escucho.", blocking=True)
        # El worker sonará el chime y drenará el parlante antes de grabar.
        self.chime_pending = True
        self.set_voice_phase("waiting")

    # ------------------------------------------------------------------
    # Visión (backend/vision.py llama estos hooks)
    # ------------------------------------------------------------------

    def on_user_detected(self) -> None:
        """Alguien entró al campo de la cámara: MECH saluda con el brazo
        (sin gastar créditos de voz) y gira hacia la persona."""
        v = self.state.get("vision", {})
        if self.state.get("voice_phase") not in ("speaking", "thinking", "transcribing"):
            gestures.perform(self.arduino, "wave", user_x=v.get("x"))

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
        # Fallback / flujo original
        if seg.image_prompt:
            try:
                img = image_gen.generate_image(
                    seg.image_prompt,
                    filename=f"{plan_title.replace(' ', '_')}_{idx}.png",
                )
                self.show_ai_image(img)
            except Exception as e:
                self.log(f"Imagen falló: {e}", "err")

    def execute_plan(self, plan: "llm.Plan") -> None:
        """Ejecuta el plan de Claude (varios segmentos)."""
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
        try:
            for i, seg in enumerate(plan.segments, 1):
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
                # Gira hacia el usuario (si la cámara sabe dónde está) y gesticula.
                v = self.state.get("vision", {})
                user_x = v.get("x") if (v.get("enabled") and v.get("user_present")) else None
                gestures.perform(self.arduino, seg.gesture, user_x=user_x)
                self.state["last_ai_response"] = seg.narration
                voice_id = voices.resolve(seg.voice)
                self.emit(
                    "ai_response",
                    text=seg.narration,
                    segment=i,
                    total=len(plan.segments),
                    voice=seg.voice or "narrator",
                )
                tts.speak(seg.narration, blocking=True, voice_id=voice_id)
        finally:
            background_audio.stop()
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

    def handle_text_command(self, text: str) -> None:
        """Procesa un comando de texto (de voz o frontend)."""
        if not text.strip():
            return
        self.state["last_transcript"] = text
        self.emit("transcript", text=text)
        self.log(f"Comando: {text!r}", "info")
        try:
            self.set_voice_phase("thinking")
            plan = llm.plan_response(text, conversation_history=self.history)
            self.log(f"Plan: {plan.mode} — {plan.title}", "ok")
            self.execute_plan(plan)
            self.history = llm.append_turn(self.history, text, plan)
            if len(self.history) > 12:
                self.history = self.history[-12:]
        except Exception as e:
            self.log(f"Error procesando comando: {e}", "err")
            tts.speak("Disculpa, tuve un problema. ¿Puedes repetirme?", blocking=True)
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
