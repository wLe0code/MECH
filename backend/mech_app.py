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

        self.state: dict[str, Any] = {
            "voice_loop_active": False,
            "voice_listening": False,
            # Fase detallada del ciclo de voz para el panel. Una de:
            # off | waiting | listening | transcribing | thinking | speaking
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
            "arduino_connected": self.arduino._ser is not None
            and self.arduino._ser.is_open,
            "last_transcript": "",
            "last_ai_response": "",
        }

        self._subscribers: set[EventCallback] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

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

    def set_voice_phase(self, phase: str) -> None:
        """Actualiza la fase del ciclo de voz y la difunde al panel.

        Fases: off | waiting | listening | transcribing | thinking | speaking.
        `voice_listening` se mantiene en sincronía (True solo cuando el
        micrófono está realmente abierto) para no romper indicadores viejos.
        """
        self.state["voice_phase"] = phase
        self.state["voice_listening"] = phase in ("waiting", "listening")
        self.emit("state", state=self.state)

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
        except Exception as e:
            self.log(f"Arduino no respondió al paro: {e}", "err")
        # Audio (TTS en curso)
        try:
            sd.stop()
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

    def show_library_video(self, slug: str, segment: int) -> None:
        """Llamado desde execute_plan cuando un segmento referencia un video
        pre-renderizado (Opción B)."""
        url = video_library.segment_url(slug, segment)
        self.state["current_video"] = url
        self.state["current_image"] = None
        self.emit("video", url=url)

    def _render_segment_visual(self, seg: "llm.Segment", plan_title: str, idx: int) -> None:
        """Decide qué visual mostrar para un segmento del plan.

        Prioridad:
          1. Video pre-renderizado (video_slug + video_segment), si existe en disco.
          2. Imagen generada con NanoBanana (image_prompt).
          3. Nada (mantiene el visual anterior).
        """
        # Video de biblioteca
        if seg.video_slug and seg.video_segment:
            if video_library.segment_exists(seg.video_slug, seg.video_segment):
                self.show_library_video(seg.video_slug, seg.video_segment)
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
            self._render_segment_visual(seg, plan.title, i)
            gestures.perform(self.arduino, seg.gesture)
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
        self.arduino.set_mode("IDLE")

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
            # Si el bucle de voz sigue activo, el worker volverá a poner
            # "waiting" en la próxima vuelta; si no, dejamos "off".
            self.set_voice_phase(
                "waiting" if self.state["voice_loop_active"] else "off"
            )

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
