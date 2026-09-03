"""Servidor de control de MECH — FastAPI + WebSocket.

Funciones:
- Sirve el frontend (panel de control y página de proyector).
- Expone REST para acciones (subir archivos, encender/apagar, etc).
- Expone un WebSocket /ws para estado en vivo + comandos.
- Corre el bucle de voz como tarea en background (controlable desde el panel).

Arranque:
    python -m backend.server
o
    uvicorn backend.server:app --host 0.0.0.0 --port 8000

Endpoints REST:
    GET  /                              → panel de control
    GET  /projector                     → página de proyector (Pi → Chromium)
    POST /api/voice/text                → envía un comando de texto
    POST /api/voice/loop/{on|off}       → arranca/detiene el bucle de voz
    POST /api/projector/{id}/upload     → sube imagen/video (multipart)
    POST /api/projector/{id}/{on|off}   → enciende/apaga proyector
    POST /api/arduino/raw               → envía comando crudo al Arduino
    POST /api/arduino/move              → MOVE:vx:vy:w
    POST /api/arduino/head              → HEAD:pan:tilt
    POST /api/arduino/arm               → ARM:L/R:angle
    POST /api/arduino/mode/{mode}       → MODE:...
    POST /api/language/{es|en}          → cambia el idioma (voz + subtítulos)
    POST /api/emergency/stop            → PARO DE EMERGENCIA
    GET  /api/state                     → estado completo (JSON)

WebSocket /ws:
    Server → Client:  {type: "state"|"log"|"transcript"|"ai_response"
                        |"projector"|"image"|"video"|"subtitle"|"arduino", ...}
    Client → Server:  {type: "ping"} (servidor responde pong)
"""

from __future__ import annotations

import asyncio
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Permite ejecutar `python -m backend.server` sin definir PYTHONPATH: añade la
# carpeta backend/ al path para que los imports planos (import config, etc.) se
# resuelvan siempre.
import os
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import lang
import maneuvers
import stt
import tts
import video_library
import vision
import voice_phrases
from mech_app import get_app

# -- Paths -------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
UPLOADS_DIR = config.IMAGE_OUTPUT_DIR.parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# -- Voice loop --------------------------------------------------------------


def _voice_loop_worker():
    """Bucle de voz: escucha → transcribe → procesa. Lo corremos en un
    hilo aparte porque sd.rec/whisper son bloqueantes.

    Tiene dos estados (voice_awake):
      - Despierto: procesa comandos normalmente. Si oye una frase de reposo
        ("para de escuchar"), pasa a reposo.
      - En reposo: NO llama a Claude ni gasta créditos; solo escucha y, si oye
        la palabra de despertar ("despierta MECH"), vuelve a despierto.

    INTERRUPCIÓN: mientras narra, un hilo aparte escucha solo "oye MECH" /
    "hey MECH" y corta la presentación si alguien lo dice (ver
    backend/interrupt_listener.py). Si dijo "oye MECH, <otra cosa>", esa
    petición se atiende enseguida.

    IDIOMA: con "ok MECH" / "despierta MECH" despierta en español; con
    "wake up MECH" despierta en INGLÉS y a partir de ahí todo (lo que
    entiende, lo que narra y los subtítulos) va en inglés hasta que se
    duerme. Ver backend/lang.py.
    """
    app_state = get_app()
    app_state.log("Bucle de voz iniciado", "ok")
    app_state.arduino.set_mode("IDLE")
    # Precargamos Whisper para que el primer "despierta MECH" responda rápido
    # (la primera vez puede tardar si tiene que descargar el modelo).
    try:
        stt.get_model()
        # El de las interrupciones también, para no cargarlo a mitad de una
        # narración (eso sí que entrecortaría el audio).
        if config.VOICE_INTERRUPT_ENABLED:
            stt.get_interrupt_model()
    except Exception as e:
        app_state.log(f"No se pudo precargar Whisper: {e}", "warn")
    # Sonido de "listo": a partir de aquí el micrófono está activo y ya se le
    # puede hablar / decir "despierta MECH".
    tts.play_chime()
    app_state.log("Voz lista: ya puedes decir 'ok MECH'.", "ok")
    if not app_state.state.get("voice_awake", True):
        app_state.set_voice_phase("dormant")

    while app_state.state["voice_loop_active"]:
        try:
            awake = app_state.state.get("voice_awake", True)

            # Mientras MECH narra NO abrimos el micrófono: lo está usando el
            # listener de interrupción ("oye MECH"). Pasa cuando la narración
            # se lanzó desde el panel (con voz, este hilo ya está ocupado).
            if app_state.state.get("voice_phase") in ("thinking", "speaking"):
                time.sleep(0.3)
                continue

            # Las ruedas están en medio de una maniobra (giro de 180°, vuelta
            # al punto de inicio): no tocamos el Arduino hasta que termine.
            if app_state.wheels_busy.is_set():
                time.sleep(0.2)
                continue

            # OJO: esto va AQUÍ, justo antes de grabar, y NO al principio de
            # la vuelta. En el firmware `MODE:LISTEN` ejecuta
            # `stopAllMotors()`; mandarlo en cada iteración frenaba cualquier
            # movimiento de ruedas a los ~300 ms de empezar (por eso el giro
            # de 180° "no se movía"). Además `set_mode` ya no reenvía el modo
            # que ya está puesto.
            app_state.arduino.set_mode("LISTEN")

            # Si MECH acaba de terminar de hablar y quedó listo, sonamos el
            # chime y drenamos el parlante ANTES de abrir el micrófono — así no
            # empezamos a grabar antes de que el sonido termine de emitirse.
            if awake and app_state.chime_pending:
                tts.play_chime()
                time.sleep(0.5)  # deja salir el sonido por completo (latencia BT)
                app_state.chime_pending = False

            # En reposo no mostramos las fases (queda el banner "dormant").
            # En reposo también acotamos la grabación: "ok MECH" dura ~1 s,
            # así que cortamos rápido y revisamos enseguida (despertar ágil).
            # Grabamos y transcribimos en dos pasos (en vez de listen_once)
            # porque en reposo puede hacer falta re-transcribir el MISMO audio
            # en inglés para reconocer "wake up MECH".
            audio = stt.record_until_silence(
                max_seconds=config.LISTEN_MAX_SECONDS,
                on_phase=app_state.set_voice_phase if awake else None,
                max_utterance_seconds=None if awake else config.WAKE_MAX_UTTERANCE,
                on_level=app_state.report_mic_level,
                # Si entra un comando por el panel, soltamos el micrófono para
                # que lo pueda usar el listener de interrupción.
                cancel_event=app_state.mic_release,
            )
            if audio is None:
                app_state.set_voice_phase(
                    "waiting" if app_state.state.get("voice_awake", True) else "dormant"
                )
                continue
            if awake:
                app_state.set_voice_phase("transcribing")
            text = stt.transcribe(audio)

            if text is None or not text.strip():
                app_state.set_voice_phase(
                    "waiting" if app_state.state.get("voice_awake", True) else "dormant"
                )
                continue

            # Si MECH estaba dando su saludo de bienvenida (la visión lo
            # dispara de forma asíncrona), lo que se transcribió es su propio
            # eco por el parlante: se descarta.
            if time.time() < app_state.greeting_until:
                app_state.log("Ignoro la transcripción: era mi propio saludo.", "info")
                app_state.set_voice_phase(
                    "waiting" if app_state.state.get("voice_awake", True) else "dormant"
                )
                continue

            awake = app_state.state.get("voice_awake", True)

            if not awake:
                # En reposo: solo reacciona a la palabra de despertar, y de
                # paso decide el IDIOMA con el que despierta.
                wake_lang = voice_phrases.wake_language(text)
                if wake_lang is None and config.WAKE_ENGLISH_ENABLED:
                    # Estábamos escuchando en un idioma, así que la frase del
                    # OTRO pudo salir deformada (lo normal: oímos en español y
                    # dijeron "wake up MECH"). Reintentamos el MISMO audio en
                    # el otro idioma; es corto (máx. WAKE_MAX_UTTERANCE s).
                    otro = "es" if lang.current() == "en" else "en"
                    try:
                        text_otro = stt.transcribe(audio, language=otro)
                    except Exception as e:
                        app_state.log(f"Reintento en {otro} falló: {e}", "warn")
                        text_otro = ""
                    if text_otro and voice_phrases.wake_language(text_otro) == otro:
                        wake_lang = otro
                        text = text_otro
                if wake_lang:
                    app_state.go_awake(language=wake_lang)
                else:
                    app_state.set_voice_phase("dormant")
                continue

            # Despierto: ¿pidió reposo? (se aceptan las frases de los dos idiomas)
            if voice_phrases.is_sleep_any(text):
                app_state.go_dormant()
                continue
            # Ya despierto y volvió a decir la frase de despertar: si es la del
            # OTRO idioma, cambia de idioma; si es la del mismo, se ignora.
            wake_lang = voice_phrases.wake_language(text)
            if wake_lang:
                if wake_lang != lang.current():
                    app_state.set_language(wake_lang, announce=True)
                    app_state.chime_pending = True
                app_state.set_voice_phase("waiting")
                continue

            # handle_text_command pone thinking → speaking y al final waiting.
            app_state.handle_text_command(text)
            # Si lo interrumpieron con "oye MECH, <otra cosa>", esa petición
            # quedó guardada: la atendemos sin que la tenga que repetir.
            pendiente = app_state.take_pending_command()
            while pendiente and app_state.state["voice_loop_active"]:
                app_state.handle_text_command(pendiente)
                pendiente = app_state.take_pending_command()
        except Exception as e:
            app_state.log(f"Error en bucle de voz: {e}", "err")
    app_state.arduino.set_mode("IDLE")
    app_state.set_voice_phase("off")
    app_state.log("Bucle de voz detenido", "info")


_voice_thread: threading.Thread | None = None


def start_voice_loop(awake: bool = True):
    global _voice_thread
    app_state = get_app()
    if app_state.state["voice_loop_active"]:
        # Ya corriendo: si estaba en reposo y se pide despierto, lo despertamos.
        if awake and not app_state.state.get("voice_awake", True):
            app_state.go_awake()
        return
    app_state.state["voice_awake"] = awake
    app_state.state["voice_loop_active"] = True
    _voice_thread = threading.Thread(target=_voice_loop_worker, daemon=True)
    _voice_thread.start()
    app_state.emit("state", state=app_state.state)


def stop_voice_loop():
    app_state = get_app()
    app_state.state["voice_loop_active"] = False
    app_state.emit("state", state=app_state.state)


# Versión del subsistema de MOVILIDAD (giro de 180°, saludo, gestos). Se
# loguea al arrancar para poder confirmar QUÉ código está corriendo en la Pi.
# Súbela cuando cambies algo de movimiento.
MOVILIDAD_VERSION = "v2 (sep 2026)"


# -- FastAPI lifespan --------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.assert_required()
    mech = get_app()
    mech.bind_loop(asyncio.get_running_loop())
    mech.log("Servidor MECH iniciado", "ok")
    # Huella de la versión de MOVILIDAD. Sirve para saber de un vistazo si la
    # Pi está corriendo el código nuevo: si esta línea NO sale en el arranque,
    # hiciste `git pull` pero NO reiniciaste el server, y "mira hacia afuera"
    # se la va a comer Claude como un plan de gestos (solo ACK:ARM, sin ruedas).
    mech.log(
        f"Movilidad {MOVILIDAD_VERSION}: 'mira hacia afuera' / 'regresa a "
        f"proyectar' activas · giro {config.TURN_180_SECONDS} s a potencia "
        f"{config.TURN_180_SPEED} (lateral {config.TURN_LATERAL_SECONDS} s a "
        f"{config.TURN_LATERAL_SPEED})",
        "ok",
    )
    # Autostart en reposo: MECH queda escuchando solo "ok MECH".
    if config.VOICE_AUTOSTART:
        mech.log("Voz en reposo: di 'ok MECH' para activarlo.", "info")
        start_voice_loop(awake=False)
    # Visión (cámara C930e): arranca sola si está habilitada en .env.
    if config.VISION_ENABLED:
        vision.get_vision(mech).start()
    yield
    stop_voice_loop()
    vision.get_vision(mech).stop()
    mech.close()


app = FastAPI(title="MECH Control", lifespan=lifespan)

# -- Static --------------------------------------------------------------------

# Imágenes generadas por NanoBanana (la página de proyector las consume).
app.mount("/generated", StaticFiles(directory=str(config.IMAGE_OUTPUT_DIR)), name="generated")
# Archivos subidos desde el panel (stand projectors).
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
# Biblioteca de videos pre-renderizados (Opción B).
app.mount("/videos", StaticFiles(directory=str(config.VIDEO_LIBRARY_DIR)), name="videos")
# Frontend.
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# -- Páginas -----------------------------------------------------------------


@app.get("/")
async def root():
    index = FRONTEND_DIR / "index.html"
    if not index.exists():
        return JSONResponse(
            {"error": "frontend/index.html no existe — clona el repo completo"},
            status_code=500,
        )
    return FileResponse(index)


@app.get("/projector")
@app.get("/proyector")  # alias en español (error de dedo común)
async def projector_page():
    page = FRONTEND_DIR / "projector.html"
    if not page.exists():
        raise HTTPException(404, "Proyector no encontrado")
    return FileResponse(page)


@app.get("/projector/vr")
@app.get("/proyector/vr")  # alias en español
async def projector_vr_page():
    """Vista estéreo lado a lado para Google Cardboard.

    Se abre EN EL TELÉFONO (misma wifi que la Pi):
    http://<ip-pi>:8000/projector/vr — tocar para fullscreen y meter el
    teléfono en el visor. Muestra lo mismo que /projector, duplicado por ojo.
    """
    page = FRONTEND_DIR / "cardboard.html"
    if not page.exists():
        raise HTTPException(404, "Página VR no encontrada")
    return FileResponse(page)


@app.get("/library")
async def library_page():
    """UI sencilla para subir/borrar videos pre-renderizados por obra."""
    page = FRONTEND_DIR / "library.html"
    if not page.exists():
        raise HTTPException(404, "Página de biblioteca no encontrada")
    return FileResponse(page)


@app.get("/manifest.json")
async def manifest():
    f = FRONTEND_DIR / "manifest.json"
    if f.exists():
        return FileResponse(f, media_type="application/manifest+json")
    raise HTTPException(404)


@app.get("/sw.js")
async def service_worker():
    """Servir el SW desde la raíz para que su scope cubra toda la app."""
    f = FRONTEND_DIR / "sw.js"
    if f.exists():
        return FileResponse(
            f,
            media_type="application/javascript",
            headers={"Service-Worker-Allowed": "/"},
        )
    raise HTTPException(404)


@app.get("/favicon.ico")
async def favicon():
    f = FRONTEND_DIR / "icon.svg"
    if f.exists():
        return FileResponse(f, media_type="image/svg+xml")
    raise HTTPException(404)


# -- REST API ----------------------------------------------------------------


class TextCommand(BaseModel):
    text: str


@app.post("/api/voice/text")
async def voice_text(cmd: TextCommand):
    # Procesar en un hilo aparte para no bloquear el event loop con TTS.
    threading.Thread(
        target=get_app().handle_text_command, args=(cmd.text,), daemon=True
    ).start()
    return {"ok": True}


@app.post("/api/voice/loop/on")
async def voice_on():
    start_voice_loop()
    return {"ok": True}


@app.post("/api/voice/loop/off")
async def voice_off():
    stop_voice_loop()
    return {"ok": True}


@app.post("/api/projector/{pid}/upload")
async def projector_upload(pid: str, file: UploadFile = File(...)):
    if pid not in ("s1", "s2", "imm"):
        raise HTTPException(400, "Proyector inválido")
    safe_name = Path(file.filename or "upload.bin").name
    dest = UPLOADS_DIR / f"{pid}_{safe_name}"
    with dest.open("wb") as f:
        while chunk := await file.read(1 << 20):  # 1 MB chunks
            f.write(chunk)
    url = f"/uploads/{dest.name}"
    mech = get_app()
    mech.state["projectors"][pid]["file"] = url
    mech.emit("projector", id=pid, on=mech.state["projectors"][pid]["on"], file=url)
    mech.log(f"Archivo cargado en {pid}: {dest.name}", "ok")
    return {"ok": True, "url": url}


@app.post("/api/projector/{pid}/on")
async def projector_on(pid: str):
    get_app().set_projector(pid, True)
    return {"ok": True}


@app.post("/api/projector/{pid}/off")
async def projector_off(pid: str):
    get_app().set_projector(pid, False)
    return {"ok": True}


class RawCommand(BaseModel):
    cmd: str


@app.post("/api/arduino/raw")
async def arduino_raw(c: RawCommand):
    get_app().arduino.send(c.cmd)
    return {"ok": True}


class MoveCmd(BaseModel):
    vx: int = 0
    vy: int = 0
    w: int = 0


@app.post("/api/arduino/move")
async def arduino_move(m: MoveCmd):
    get_app().arduino.move(m.vx, m.vy, m.w)
    return {"ok": True}


class HeadCmd(BaseModel):
    pan: int = 90
    tilt: int = 90


@app.post("/api/arduino/head")
async def arduino_head(h: HeadCmd):
    get_app().arduino.head(h.pan, h.tilt)
    return {"ok": True}


class ArmCmd(BaseModel):
    side: Literal["L", "R"]
    angle: int = 90


@app.post("/api/arduino/arm")
async def arduino_arm(a: ArmCmd):
    get_app().arduino.arm(a.side, a.angle)
    return {"ok": True}


@app.post("/api/arduino/mode/{mode}")
async def arduino_mode(mode: str):
    mode = mode.upper()
    if mode not in ("AUTO", "IDLE", "LISTEN", "SPEAK", "STOP"):
        raise HTTPException(400, "Modo inválido")
    get_app().arduino.set_mode(mode)
    return {"ok": True}


@app.post("/api/arduino/reconnect")
async def arduino_reconnect():
    """Fuerza un intento de reconexión al Arduino (también reintenta solo)."""
    link = get_app().arduino
    if link.is_connected:
        return {"ok": True, "connected": True}
    try:
        link.connect()
    except Exception as e:
        return {"ok": False, "connected": False, "error": str(e)}
    return {"ok": True, "connected": link.is_connected}


@app.post("/api/move/outward")
async def move_outward():
    """"Mira hacia afuera": gira 180° y saluda al público.

    Lo mismo que decirle "mira hacia afuera" por voz, pero desde el panel.
    Corre en segundo plano porque la maniobra dura varios segundos (y la
    petición HTTP no debe quedarse esperando)."""
    mech = get_app()
    if mech.state.get("voice_phase") in ("speaking", "thinking"):
        return {"ok": False, "reason": "MECH está narrando; espera o interrúmpelo"}
    threading.Thread(
        target=maneuvers.look_outward, args=(mech,), daemon=True
    ).start()
    return {"ok": True}


@app.post("/api/move/projection")
async def move_projection():
    """"Regresa a proyectar": deshace el giro y vuelve a su posición."""
    mech = get_app()
    threading.Thread(
        target=maneuvers.back_to_projection, args=(mech,), daemon=True
    ).start()
    return {"ok": True}


@app.post("/api/move/greet")
async def move_greet():
    """Dispara el saludo de bienvenida AHORA (sin esperar a la cámara).

    Útil para probar el arco del brazo y la frase sin tener que entrar y
    salir del campo de visión."""
    mech = get_app()
    if mech.state.get("voice_phase") in ("speaking", "thinking"):
        return {"ok": False, "reason": "MECH está narrando ahora mismo"}
    threading.Thread(target=mech.greet_now, daemon=True).start()
    return {"ok": True}


@app.post("/api/vision/{onoff}")
async def vision_toggle(onoff: str):
    """Enciende/apaga el módulo de visión (cámara + detección de usuarios).
    También persiste VISION_ENABLED en .env para que sobreviva reinicios."""
    if onoff not in ("on", "off"):
        raise HTTPException(400, "Usa /api/vision/on o /api/vision/off")
    mech = get_app()
    v = vision.get_vision(mech)
    if onoff == "on":
        started = v.start()
        config.VISION_ENABLED = started
        config.update_env_file({"VISION_ENABLED": "true" if started else "false"})
        if not started:
            raise HTTPException(500, "No se pudo iniciar la visión (revisa el log)")
    else:
        v.stop()
        config.VISION_ENABLED = False
        config.update_env_file({"VISION_ENABLED": "false"})
    return {"ok": True, "enabled": config.VISION_ENABLED}


@app.post("/api/voice/interrupt")
async def voice_interrupt():
    """Interrumpe la narración a mano, como si alguien dijera "oye MECH".

    Dos usos: (1) botón de "cállate" en el stand que NO es el paro de
    emergencia; (2) diagnóstico — si por aquí corta pero por voz no, el
    problema está en el micrófono o en lo que entiende Whisper, no en el
    mecanismo de interrupción.
    """
    mech = get_app()
    if mech.state.get("voice_phase") not in ("speaking", "thinking"):
        return {"ok": False, "reason": "MECH no está narrando ahora mismo"}
    threading.Thread(target=mech.interrupts.trigger, daemon=True).start()
    return {"ok": True}


@app.post("/api/language/{code}")
async def set_language(code: str):
    """Cambia el idioma a mano desde el panel (sin usar la palabra clave).

    En el stand el idioma lo decide la voz: "ok MECH" = español,
    "wake up MECH" = inglés. Este endpoint existe para probar sin micrófono
    y para corregir sobre la marcha si Whisper entendió mal.
    """
    code = code.strip().lower()
    if code not in lang.SUPPORTED:
        raise HTTPException(400, f"Idioma inválido: {code}. Usa 'es' o 'en'.")
    mech = get_app()
    mech.set_language(code)
    return {"ok": True, "language": lang.current()}


@app.post("/api/emergency/stop")
async def emergency_stop():
    stop_voice_loop()
    try:
        vision.get_vision(get_app()).stop()
        config.VISION_ENABLED = False
    except Exception:
        pass
    get_app().emergency_stop()
    return {"ok": True}


@app.get("/api/state")
async def api_state():
    return get_app().state


# -- Configuración en vivo (vista Ajustes del panel) -------------------------

def _to_bool(v: str) -> bool:
    return str(v).strip().lower() in ("1", "true", "yes", "on", "si", "sí")


# Claves que se pueden aplicar SIN reiniciar (se leen en cada turno).
_LIVE_KEYS = {
    "VAD_AGGRESSIVENESS": int,
    "VAD_SILENCE_TIMEOUT": float,
    "VAD_ENERGY_FACTOR": float,  # umbral de voz sobre el ruido ambiente
    "AUDIO_LEAD_SILENCE": float,
    "AUDIO_LISTEN_MAX_SECONDS": float,  # se guarda en config.LISTEN_MAX_SECONDS
    "WHISPER_LANGUAGE": str,
    "TTS_DRY_RUN": _to_bool,  # modo ahorro de créditos de voz
    "SUBTITLES_ENABLED": _to_bool,  # subtítulos en la proyección
    "VOICE_INTERRUPT_ENABLED": _to_bool,  # cortar la narración con "oye MECH"
    "INTERRUPT_ENERGY_FACTOR": float,  # umbral de voz MIENTRAS narra
    # Visión / comportamiento físico (se leen en cada frame/gesto).
    "VISION_MIN_DISTANCE": float,
    "VISION_APPROACH": _to_bool,
    "VISION_FOLLOW": _to_bool,
    "VISION_PROJECT_GATE": _to_bool,
    "VISION_MAX_SPEED": int,
    "GESTURE_WHEELS": _to_bool,
    "ARM_GESTURE_MODE": str,
    "NARRATION_GESTURE_MODE": str,  # gestos simples (un brazo) al proyectar
    "ARM_WAVE_SECONDS": float,      # qué tan lento es el saludo
    "ARM_WAVE_HIGH": int,           # hasta dónde sube el brazo al saludar
    "ARM_WAVE_SWING": int,          # amplitud de las agitadas de arriba
    "ARM_WAVE_REPEATS": int,
    "GREETING_COOLDOWN": float,
    "MOTOR_KICK_SECONDS": float,    # pulso a fondo para romper la fricción
    "ARM_WAVE_BOTH": _to_bool,      # el saludo levanta los dos brazos
    "RETURN_SPEED": int,
    "GESTURE_WHEEL_SPEED": int,
    "GESTURE_WHEEL_SECONDS": float,
    # Maniobra "mira hacia afuera" (se calibra EN EL ROBOT, sin encoders).
    "TURN_180_SPEED": int,
    "TURN_180_SECONDS": float,
    "TURN_LATERAL_SPEED": int,
    "TURN_LATERAL_SECONDS": float,
}
# Claves que solo tienen efecto tras reiniciar el servidor.
_RESTART_KEYS = {
    "AUDIO_INPUT_DEVICE",
    "AUDIO_SAMPLE_RATE",
    "WHISPER_MODEL",
    "CLAUDE_MODEL",
    "ELEVENLABS_VOICE_ID",
}


@app.get("/api/config")
async def get_config():
    """Valores actuales de configuración para la vista Ajustes.

    No devuelve las API keys (seguridad): solo parámetros operativos.
    """
    return {
        "live": {
            "VAD_AGGRESSIVENESS": config.VAD_AGGRESSIVENESS,
            "VAD_SILENCE_TIMEOUT": config.VAD_SILENCE_TIMEOUT,
            "VAD_ENERGY_FACTOR": config.VAD_ENERGY_FACTOR,
            "AUDIO_LEAD_SILENCE": config.AUDIO_LEAD_SILENCE,
            "AUDIO_LISTEN_MAX_SECONDS": config.LISTEN_MAX_SECONDS,
            "WHISPER_LANGUAGE": config.WHISPER_LANGUAGE,
            "TTS_DRY_RUN": config.TTS_DRY_RUN,
            "SUBTITLES_ENABLED": config.SUBTITLES_ENABLED,
            "VOICE_INTERRUPT_ENABLED": config.VOICE_INTERRUPT_ENABLED,
            "INTERRUPT_ENERGY_FACTOR": config.INTERRUPT_ENERGY_FACTOR,
            "VISION_ENABLED": config.VISION_ENABLED,
            "VISION_MIN_DISTANCE": config.VISION_MIN_DISTANCE,
            "VISION_APPROACH": config.VISION_APPROACH,
            "VISION_FOLLOW": config.VISION_FOLLOW,
            "VISION_PROJECT_GATE": config.VISION_PROJECT_GATE,
            "GESTURE_WHEELS": config.GESTURE_WHEELS,
            "ARM_GESTURE_MODE": config.ARM_GESTURE_MODE,
            "NARRATION_GESTURE_MODE": config.NARRATION_GESTURE_MODE,
            "ARM_WAVE_SECONDS": config.ARM_WAVE_SECONDS,
            "ARM_WAVE_HIGH": config.ARM_WAVE_HIGH,
            "ARM_WAVE_SWING": config.ARM_WAVE_SWING,
            "ARM_WAVE_REPEATS": config.ARM_WAVE_REPEATS,
            "GREETING_COOLDOWN": config.GREETING_COOLDOWN,
            "MOTOR_KICK_SECONDS": config.MOTOR_KICK_SECONDS,
            "ARM_WAVE_BOTH": config.ARM_WAVE_BOTH,
            "RETURN_SPEED": config.RETURN_SPEED,
            "GESTURE_WHEEL_SPEED": config.GESTURE_WHEEL_SPEED,
            "GESTURE_WHEEL_SECONDS": config.GESTURE_WHEEL_SECONDS,
            "TURN_180_SPEED": config.TURN_180_SPEED,
            "TURN_180_SECONDS": config.TURN_180_SECONDS,
            "TURN_LATERAL_SPEED": config.TURN_LATERAL_SPEED,
            "TURN_LATERAL_SECONDS": config.TURN_LATERAL_SECONDS,
        },
        "restart": {
            "AUDIO_INPUT_DEVICE": config.AUDIO_INPUT_DEVICE,
            "AUDIO_SAMPLE_RATE": config.AUDIO_SAMPLE_RATE,
            "WHISPER_MODEL": config.WHISPER_MODEL,
            "CLAUDE_MODEL": config.CLAUDE_MODEL,
            "ELEVENLABS_VOICE_ID": config.ELEVENLABS_VOICE_ID,
        },
    }


class ConfigUpdate(BaseModel):
    updates: dict[str, str]


@app.post("/api/config")
async def set_config(c: ConfigUpdate):
    """Persiste cambios en backend/.env y aplica en vivo los que se pueda.

    Devuelve qué claves se aplicaron al instante y cuáles necesitan
    reiniciar el servidor para tener efecto.
    """
    if not c.updates:
        return {"ok": True, "applied": [], "restart_needed": []}

    # 1) Persistir al archivo .env (sobrevive reinicios).
    try:
        config.update_env_file(c.updates)
    except Exception as e:
        raise HTTPException(500, f"No se pudo escribir .env: {e}")

    # 2) Aplicar en caliente las claves seguras.
    applied: list[str] = []
    restart_needed: list[str] = []
    for key, raw in c.updates.items():
        if key in _LIVE_KEYS:
            try:
                value = _LIVE_KEYS[key](raw)
            except (ValueError, TypeError):
                raise HTTPException(400, f"Valor inválido para {key}: {raw!r}")
            if key == "AUDIO_LISTEN_MAX_SECONDS":
                config.LISTEN_MAX_SECONDS = value
            else:
                setattr(config, key, value)
            applied.append(key)
        else:
            restart_needed.append(key)

    mech = get_app()
    if applied:
        mech.log(f"Ajustes aplicados en vivo: {', '.join(applied)}", "ok")
    if restart_needed:
        mech.log(
            f"Ajustes guardados (requieren reiniciar): {', '.join(restart_needed)}",
            "warn",
        )
    return {"ok": True, "applied": applied, "restart_needed": restart_needed}


@app.get("/api/audio/devices")
async def audio_devices():
    """Lista los micrófonos disponibles para elegir AUDIO_INPUT_DEVICE."""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
    except Exception as e:
        raise HTTPException(500, f"No se pudo consultar audio: {e}")
    inputs = [
        {"index": i, "name": d["name"], "channels": d["max_input_channels"]}
        for i, d in enumerate(devices)
        if d["max_input_channels"] > 0
    ]
    return {"devices": inputs, "current": config.AUDIO_INPUT_DEVICE}


class TTSTest(BaseModel):
    text: str = "Hola, soy MECH. Esta es una prueba de sonido."


@app.post("/api/tts/test")
async def tts_test(t: TTSTest):
    """Reproduce una frase con ElevenLabs para verificar TTS + parlante,
    sin pasar por Claude. Útil para probar el audio de salida."""
    threading.Thread(
        target=tts.speak, args=(t.text,), kwargs={"blocking": True}, daemon=True
    ).start()
    return {"ok": True}


# -- Biblioteca de videos pre-renderizados (Opción B) ------------------------


@app.get("/api/library")
async def library_list():
    """Devuelve todas las obras del catálogo con su estado de disponibilidad."""
    return {"works": video_library.available_works()}


@app.post("/api/library/{slug}/{segment:int}")
async def library_upload(slug: str, segment: int, file: UploadFile = File(...)):
    """Sube el material de una obra+segmento. Puede ser VIDEO o IMAGEN.
    Se guarda con la extensión real y reemplaza cualquier archivo previo
    de ese segmento (de cualquier extensión)."""
    meta = video_library.WORKS.get(slug)
    if meta is None:
        raise HTTPException(404, f"Obra desconocida: {slug}")
    if not (1 <= segment <= meta["segments"]):
        raise HTTPException(
            400,
            f"Segmento {segment} fuera de rango (1-{meta['segments']}) para {slug}",
        )
    ext = Path(file.filename or "seg.mp4").suffix.lower() or ".mp4"
    if ext not in video_library._SEG_EXTS:
        raise HTTPException(
            400,
            f"Formato no soportado: {ext}. Usa video (mp4, mov, webm…) o "
            f"imagen (jpg, png, webp…).",
        )
    folder = config.VIDEO_LIBRARY_DIR / slug
    folder.mkdir(parents=True, exist_ok=True)
    # Quita cualquier archivo previo de este segmento (cualquier extensión),
    # así no quedan un video y una imagen compitiendo para el mismo slot.
    base = video_library.segment_basename(segment)
    for e in video_library._SEG_EXTS:
        old = folder / f"{base}{e}"
        if old.exists():
            old.unlink()
    dest = folder / f"{base}{ext}"
    with dest.open("wb") as f:
        while chunk := await file.read(1 << 20):  # 1 MB
            f.write(chunk)
    size_mb = dest.stat().st_size / (1024 * 1024)
    kind = "imagen" if ext in video_library._SEG_IMAGE_EXTS else "video"
    get_app().log(f"Subido ({kind}): {slug}/{dest.name} ({size_mb:.1f} MB)", "ok")
    return {"ok": True, "url": video_library.segment_url(slug, segment), "kind": kind}


@app.delete("/api/library/{slug}/{segment:int}")
async def library_delete(slug: str, segment: int):
    """Elimina el material de un segmento (video o imagen, cualquier extensión)."""
    path = video_library.segment_file(slug, segment)
    if path is not None:
        path.unlink()
        get_app().log(f"Segmento eliminado: {slug}/{path.name}", "info")
    return {"ok": True}


@app.post("/api/library/{slug}/music")
async def library_music_upload(slug: str, file: UploadFile = File(...)):
    """Sube el sample de música de fondo de una exposición (ej. Malpaís).

    Solo para obras marcadas con ``music: True``. Se guarda como
    ``music.<ext>`` y reemplaza cualquier sample previo.
    """
    meta = video_library.WORKS.get(slug)
    if meta is None:
        raise HTTPException(404, f"Obra desconocida: {slug}")
    if not video_library.supports_music(slug):
        raise HTTPException(400, f"La obra {slug} no admite música de fondo")
    ext = Path(file.filename or "music.mp3").suffix.lower() or ".mp3"
    if ext not in video_library._MUSIC_EXTS:
        raise HTTPException(400, f"Formato de audio no soportado: {ext}")
    folder = config.VIDEO_LIBRARY_DIR / slug
    folder.mkdir(parents=True, exist_ok=True)
    # Quita cualquier sample previo (cualquier extensión).
    for e in video_library._MUSIC_EXTS:
        old = folder / f"music{e}"
        if old.exists():
            old.unlink()
    dest = folder / f"music{ext}"
    with dest.open("wb") as f:
        while chunk := await file.read(1 << 20):
            f.write(chunk)
    size_mb = dest.stat().st_size / (1024 * 1024)
    get_app().log(f"Música subida: {slug}/{dest.name} ({size_mb:.1f} MB)", "ok")
    return {"ok": True, "url": video_library.background_audio_url(slug)}


@app.delete("/api/library/{slug}/music")
async def library_music_delete(slug: str):
    """Elimina el sample de música de fondo de una obra."""
    path = video_library.background_audio_path(slug)
    if path is not None:
        path.unlink()
        get_app().log(f"Música eliminada: {slug}", "info")
    return {"ok": True}


# -- WebSocket ---------------------------------------------------------------


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    mech = get_app()
    queue: asyncio.Queue[dict] = asyncio.Queue()

    async def cb(message: dict) -> None:
        await queue.put(message)

    mech.subscribe(cb)

    # Estado inicial
    await ws.send_json({"type": "state", "state": mech.state})

    sender_task = asyncio.create_task(_ws_sender(ws, queue))
    try:
        while True:
            data = await ws.receive_json()
            if data.get("type") == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        mech.unsubscribe(cb)
        sender_task.cancel()


async def _ws_sender(ws: WebSocket, queue: asyncio.Queue):
    try:
        while True:
            message = await queue.get()
            await ws.send_json(message)
    except (WebSocketDisconnect, asyncio.CancelledError):
        return
    except Exception:
        return


# -- Entry point -------------------------------------------------------------


def main():
    import uvicorn
    uvicorn.run(
        "backend.server:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()
