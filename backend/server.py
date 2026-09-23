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
    POST /api/language/{es|en|fr|pt}    → cambia el idioma (voz + subtítulos)
    POST /api/translate/start           → modo traductor (?src=&dst= opcional)
    POST /api/translate/stop            → sale del modo traductor
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
import translator
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

    IDIOMA: el despertar decide el idioma — "ok MECH" (español),
    "wake up MECH" (inglés), "bonjour MECH" (francés), "bom dia MECH"
    (portugués). A partir de ahí todo (lo que entiende, lo que narra y los
    subtítulos) va en ese idioma hasta que se duerme, y al dormirse vuelve
    solo a español. Ver backend/lang.py.
    """
    app_state = get_app()
    try:
        _voice_loop_body(app_state)
    except Exception as e:
        # Sin esto, un fallo ANTES del bucle (cargar Whisper, el Arduino, el
        # audio) mataba el hilo en silencio y dejaba `voice_loop_active` en
        # True: el panel decía que la voz estaba encendida, el micrófono
        # nunca se abría, y apagar/encender desde el botón era la única
        # forma de salir. Ahora se ve el error y el estado dice la verdad.
        app_state.log(f"El bucle de voz se cayó: {e}", "err")
    finally:
        app_state.state["voice_loop_active"] = False
        try:
            app_state.arduino.set_mode("IDLE")
        except Exception:
            pass
        app_state.set_voice_phase("off")
        app_state.emit("state", state=app_state.state)
        app_state.log("Bucle de voz detenido", "info")


def _reportar_microfono(app_state) -> None:
    """Mide el micrófono y escribe el veredicto en el panel.

    Tres desenlaces, y cada uno dice qué hacer:
      - no se pudo abrir  -> el dispositivo del .env no existe o está ocupado.
      - se abrió pero MUDO -> el micrófono está apagado, silenciado o es el
        equipado equivocado (p. ej. el de la webcam, que ya no se usa).
      - se abrió con señal -> todo bien; queda el nivel apuntado por si luego
        hay que tocar el umbral.
    """
    try:
        info = stt.probe_microphone(1.0)
    except Exception as e:  # nunca puede impedir que MECH arranque
        app_state.log(f"No pude probar el micrófono: {e}", "warn")
        return

    pedido = info.get("device") or "(el que tenga puesto el sistema)"
    nombre = info.get("nombre") or "?"

    if info.get("error"):
        app_state.log(
            f"NO pude abrir el micrófono ({pedido}): {info['error']}. "
            "MECH no va a oír nada. Revisá que esté enchufado y que "
            "AUDIO_INPUT_DEVICE del .env coincida con un dispositivo real "
            "(la lista sale en Ajustes o con `python -m backend.preflight`).",
            "err",
        )
        return

    if not info.get("frames"):
        app_state.log(
            f"El micrófono '{nombre}' se abrió pero NO llegó audio. "
            "Suele ser que está desenchufado o apagado.",
            "err",
        )
        return

    nivel, pico = info["nivel"], info["pico"]
    app_state.log(
        f"Micrófono: '{nombre}' a {info['rate']} Hz "
        f"(pedido en .env: {pedido}) — nivel {nivel:.4f}, pico {pico:.4f}.",
        "info",
    )
    # 0.0005 es ruido de fondo de un micrófono vivo en una sala en silencio.
    # Por debajo de eso, lo que entra es literalmente silencio digital.
    if pico < 0.0005:
        app_state.log(
            "El micrófono NO capta nada (silencio digital). MECH va a estar "
            "sordo. Revisá: que sea el dispositivo correcto (el del proyecto "
            "es el Steren, NO el de la cámara), que el receptor esté "
            "encendido y con batería, y que no esté silenciado en el sistema.",
            "err",
        )
    else:
        app_state.log("Micrófono OK: capta señal.", "ok")


def _voice_loop_body(app_state) -> None:
    """El bucle en sí. Lo envuelve `_voice_loop_worker` para que un fallo no
    deje el hilo muerto y el estado mintiendo."""
    app_state.log("Bucle de voz iniciado", "ok")
    app_state.arduino.set_mode("IDLE")
    # ⚠️ ESTO TARDA, y mientras tanto el micrófono está CERRADO.
    #
    # Cargar los dos modelos de Whisper lleva de varios segundos a casi un
    # minuto en la Pi (y la PRIMERA vez, si hay que descargarlos, mucho más).
    # Antes esto no se decía en el panel: MECH aparecía "en reposo", que es
    # su estado normal, así que parecía que estaba escuchando cuando todavía
    # no. El equipo lo reportó como "al encender el server no oye 'ok MECH',
    # pero si toco el botón sí" — el botón "arreglaba" el problema porque
    # para entonces los modelos ya estaban cargados en memoria.
    #
    # Por eso ahora hay una fase propia ("loading") y se dice cuánto tardó.
    app_state.set_voice_phase("loading")
    app_state.log(
        f"Cargando Whisper '{config.WHISPER_MODEL}' — MECH todavía NO "
        "escucha. Espera a que diga «Voz lista».",
        "warn",
    )
    t0 = time.monotonic()
    try:
        stt.get_model()
        # El de las interrupciones también, para no cargarlo a mitad de una
        # narración (eso sí que entrecortaría el audio).
        if config.VOICE_INTERRUPT_ENABLED:
            stt.get_interrupt_model()
    except Exception as e:
        app_state.log(f"No se pudo precargar Whisper: {e}", "warn")
    app_state.log(f"Whisper cargado en {time.monotonic() - t0:.1f} s.", "ok")
    # PRUEBA REAL DEL MICRÓFONO antes de ponerse a escuchar.
    #
    # El equipo reportó "al inicio está sordo, como si no tuviera micrófono".
    # Desde fuera, tres causas muy distintas se ven exactamente igual: el
    # dispositivo equivocado, el micrófono mudo, o el umbral mal puesto.
    # Esto las separa con un número y lo deja escrito en el panel en CADA
    # arranque, así no hay que adivinar nunca más.
    _reportar_microfono(app_state)
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
            # con detección de idioma, para reconocer "wake up MECH",
            # "bonjour MECH" o "bom dia MECH".
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
            # En modo traductor el idioma de CADA turno no es el activo de
            # MECH: es uno de los dos del par. Con detección automática
            # (bidireccional) dejamos que Whisper diga en cuál habló; si no
            # reconoce ninguno de los dos, se repite forzando el de ORIGEN,
            # que es la dirección que pidió el usuario.
            detected: str | None = None
            if translator.is_awaiting_phrase():
                src, dst = translator.pair()
                if config.TRANSLATOR_AUTO_DETECT:
                    text, detected = stt.transcribe_any(audio)
                    if detected not in (src, dst):
                        text, detected = stt.transcribe(audio, language=src), src
                else:
                    text, detected = stt.transcribe(audio, language=src), src
            else:
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
                if wake_lang is None and len(lang.enabled_languages()) > 1:
                    # En reposo escuchamos en español, así que un despertar en
                    # otro idioma ("wake up MECH", "bonjour MECH", "bom dia
                    # MECH") pudo salir deformado. Reintentamos el MISMO audio
                    # UNA vez dejando que Whisper detecte el idioma solo: con
                    # cuatro idiomas, probarlos uno a uno dejaría la Pi varios
                    # segundos sin escuchar. El clip es corto (máx.
                    # WAKE_MAX_UTTERANCE s).
                    try:
                        text_auto, detectado = stt.transcribe_any(audio)
                    except Exception as e:
                        app_state.log(f"Reintento multi-idioma falló: {e}", "warn")
                        text_auto, detectado = "", None
                    otro = voice_phrases.wake_language(text_auto) if text_auto else None
                    if otro:
                        app_state.log(
                            f"Despertar en {lang.label(otro)} reconocido al "
                            f"reintentar (Whisper oyó '{detectado or '?'}').",
                            "info",
                        )
                        wake_lang = otro
                        text = text_auto
                if wake_lang:
                    app_state.go_awake(language=wake_lang)
                else:
                    app_state.set_voice_phase("dormant")
                continue

            # MODO TRADUCTOR: MECH acaba de preguntar y esto es la
            # respuesta — o el par de idiomas, o LA frase a traducir. Se
            # reconocen además salir del modo, dormirse y repetir el comando
            # (por si se arrepiente a medias). Cualquier otra cosa se traduce:
            # es lo correcto, un intérprete no obedece lo que traduce (si no,
            # "mira hacia afuera" giraría el robot en vez de traducirse).
            if translator.is_active():
                # OJO con el ORDEN: "desactiva el modo traductor" contiene
                # "modo traductor", así que salir se comprueba PRIMERO. Los
                # helpers de voice_phrases ya lo tienen en cuenta, pero el
                # orden de aquí es la segunda red.
                if voice_phrases.is_translate_stop(text):
                    app_state.stop_translator()
                    app_state.set_voice_phase("waiting")
                elif voice_phrases.is_sleep_any(text):
                    app_state.go_dormant()
                elif voice_phrases.is_translate_on(text):
                    # "activa modo traductor" estando ya dentro: pasa a
                    # continuo (o cambia el par si nombró idiomas).
                    src, dst = voice_phrases.extract_language_pair(text)
                    app_state.start_translator(src, dst, continuous=True)
                elif voice_phrases.is_translate(text):
                    # Volvió a decir "traduce MECH": vuelve a preguntar (y si
                    # nombró idiomas, cambia el par sin salir del modo).
                    src, dst = voice_phrases.extract_language_pair(text)
                    app_state.start_translator(src, dst)
                elif translator.is_awaiting_pair():
                    app_state.handle_translator_pair(text)
                else:
                    app_state.handle_translation(text, detected)
                continue

            # Despierto: ¿pidió reposo? (se aceptan las frases de los 4 idiomas)
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
    # El apagado (modo IDLE, fase "off", log) lo hace el `finally` de
    # `_voice_loop_worker`, para que valga también si esto se cae.


_voice_thread: threading.Thread | None = None


def _loop_vivo() -> bool:
    """¿Hay de verdad un hilo de voz corriendo?

    `voice_loop_active` es solo una bandera: si el hilo muere, se queda en
    True y el panel muestra la voz como encendida aunque el micrófono esté
    cerrado. Mirar el hilo es lo único que no miente.
    """
    return _voice_thread is not None and _voice_thread.is_alive()


def start_voice_loop(awake: bool = True):
    global _voice_thread
    app_state = get_app()
    if app_state.state["voice_loop_active"] and _loop_vivo():
        # Ya corriendo: si estaba en reposo y se pide despierto, lo despertamos.
        if awake and not app_state.state.get("voice_awake", True):
            app_state.go_awake()
        return
    if app_state.state["voice_loop_active"]:
        # La bandera decía que sí, pero el hilo no existe: se cayó. Lo
        # decimos y arrancamos otro, en vez de no hacer nada (que es lo que
        # obligaba a pulsar el botón dos veces).
        app_state.log(
            "El bucle de voz estaba marcado como activo pero el hilo no "
            "existía. Lo arranco de nuevo.",
            "warn",
        )
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
MOVILIDAD_VERSION = "v3 (sep 2026)"


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
        f"proyectar' activas · media vuelta = lateral "
        f"{config.TURN_180_SECONDS} s a potencia {config.TURN_180_SPEED}"
        f"{' (invertido)' if config.TURN_180_INVERT else ''}",
        "ok",
    )
    # Idiomas activos. Misma idea que la línea de arriba: si en la Pi solo
    # aparece "español · inglés", está corriendo el código viejo (o alguien
    # apagó francés/portugués en el .env).
    mech.log(
        "Idiomas: " + " · ".join(lang.label(c) for c in lang.enabled_languages())
        + " — «ok MECH» (es) · «wake up MECH» (en) · «bonjour MECH» (fr) · "
          "«bom dia MECH» (pt)",
        "ok",
    )
    if config.TRANSLATOR_ENABLED:
        mech.log(
            "Modo traductor: decí «traduce MECH», te pregunta qué traducir, "
            "traduce UNA frase y se calla (para otra, repetí el comando)"
            + (" (traduce en los dos sentidos)." if config.TRANSLATOR_AUTO_DETECT
               else " (sentido fijo: origen → destino)."),
            "ok",
        )
    # Autostart en reposo: MECH queda escuchando solo "ok MECH".
    if config.VOICE_AUTOSTART:
        mech.log("Voz en reposo: di 'ok MECH' para activarlo.", "info")
        start_voice_loop(awake=False)
    else:
        # ⚠️ Antes esto era SILENCIO ABSOLUTO: con VOICE_AUTOSTART=false el
        # bucle no arrancaba y el arranque no lo mencionaba, así que MECH
        # parecía "sordo, como si no tuviera micrófono" — y pulsar el botón
        # del panel lo "arreglaba" porque era lo único que lo encendía.
        # Recordá que el .env de la Pi TAPA el default del código.
        mech.log(
            "VOICE_AUTOSTART=false: el bucle de voz NO arranca solo, así que "
            "MECH no va a oír nada todavía. Pulsá el micrófono del panel (o "
            "la tecla V) para encenderlo. Para que arranque solo, poné "
            "VOICE_AUTOSTART=true en backend/.env.",
            "warn",
        )
    # Slots de proyección directa (marketing): decir cuántos videos hay, para
    # que se vea de un vistazo si están subidos y si esta es la versión nueva.
    for slug in (s for s in video_library.WORKS if video_library.is_promo(s)):
        n = len(video_library.playlist(slug))
        mech.log(
            f"Slot '{slug}': {n} video(s) — decí 'proyecta {slug}' para "
            f"reproducirlos enteros y con su audio."
            if n else
            f"Slot '{slug}': vacío. Subí videos en /library.",
            "ok" if n else "info",
        )
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
# Iconos y fuentes del panel, servidos EN LOCAL. Van montados aparte de
# /static y con ruta RELATIVA en el HTML para que las páginas funcionen igual
# servidas por el server (/ y /library) que abiertas con doble click.
_VENDOR_DIR = FRONTEND_DIR / "vendor"
if _VENDOR_DIR.exists():
    app.mount("/vendor", StaticFiles(directory=str(_VENDOR_DIR)), name="vendor")

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


class AdvanceCmd(BaseModel):
    seconds: float | None = None
    backwards: bool = False


@app.post("/api/move/advance")
async def move_advance(c: AdvanceCmd):
    """Avanza (o retrocede) unos segundos, a potencia máxima.

    Sin `seconds` usa el valor de Ajustes. Es lo mismo que decirle
    "avanza diez segundos" por voz."""
    mech = get_app()
    if mech.state.get("voice_phase") in ("speaking", "thinking"):
        return {"ok": False, "reason": "MECH está narrando; espera o interrúmpelo"}
    threading.Thread(
        target=maneuvers.advance, args=(mech, c.seconds),
        kwargs={"backwards": c.backwards}, daemon=True,
    ).start()
    return {"ok": True, "seconds": c.seconds or config.ADVANCE_SECONDS,
            "backwards": c.backwards}


@app.post("/api/move/testturn")
async def move_test_turn():
    """Repite el tramo de media vuelta SIN cambiar la orientación guardada.

    Es el botón de calibración: pulsar, mirar cuánto giró, ajustar los
    segundos en Ajustes, volver a pulsar."""
    mech = get_app()
    if mech.state.get("voice_phase") in ("speaking", "thinking"):
        return {"ok": False, "reason": "MECH está narrando; espera o interrúmpelo"}
    threading.Thread(
        target=maneuvers.test_half_turn, args=(mech,), daemon=True
    ).start()
    return {"ok": True, "seconds": config.TURN_180_SECONDS,
            "speed": config.TURN_180_SPEED}


@app.post("/api/move/greet")
async def move_greet():
    """Dispara el saludo de bienvenida AHORA (sin esperar a la cámara).

    Útil para probar el arco del brazo y la frase sin tener que entrar y
    salir del campo de visión. Se salta el cooldown, pero NO la regla de
    "solo en reposo" (ver mech_app.greet_now)."""
    mech = get_app()
    if mech.state.get("voice_phase") in ("speaking", "thinking"):
        return {"ok": False, "reason": "MECH está narrando ahora mismo"}
    if config.GREETING_ONLY_DORMANT and mech.state.get("voice_awake", True):
        return {
            "ok": False,
            "reason": "MECH está despierto y el saludo solo va en reposo. "
                      "Dormilo, o apagá la regla en Ajustes.",
        }
    threading.Thread(target=mech.greet_now, daemon=True).start()
    return {"ok": True}


@app.post("/api/move/67")
async def move_sixty_seven():
    """Hace el gesto del "67" AHORA, sin cámara.

    Es el botón para PROBAR la coreografía de los brazos (y para hacerlo a
    propósito en el stand). El reconocimiento por cámara va aparte, en
    backend/gesture_detect.py.
    """
    mech = get_app()
    if mech.state.get("voice_phase") in ("speaking", "thinking"):
        return {"ok": False, "reason": "MECH está narrando ahora mismo"}
    threading.Thread(target=mech.do_sixty_seven, daemon=True).start()
    return {"ok": True}


# -- Playlist promo (marketing) ---------------------------------------------


@app.post("/api/marketing/play")
async def marketing_play(slug: str = "marketing"):
    """Proyecta el slot promo entero, con su propio audio y sin narración.

    Lo mismo que decirle "proyecta marketing" por voz. Corre en segundo plano
    porque la reproducción dura minutos.
    """
    if not video_library.is_promo(slug):
        raise HTTPException(404, f"'{slug}' no es un slot de proyección directa")
    mech = get_app()
    if mech.state.get("voice_phase") in ("speaking", "thinking"):
        return {"ok": False, "reason": "MECH está ocupado; espera o interrúmpelo"}
    items = video_library.playlist(slug)
    if not items:
        return {"ok": False, "reason": f"El slot '{slug}' no tiene videos todavía"}
    threading.Thread(
        target=mech.play_playlist, args=(slug,), daemon=True
    ).start()
    return {"ok": True, "items": len(items)}


@app.post("/api/marketing/stop")
async def marketing_stop():
    """Corta la proyección promo en curso (botón de "ya está" del stand)."""
    mech = get_app()
    if not mech.state.get("current_playlist"):
        return {"ok": False, "reason": "No hay ninguna proyección en curso"}
    mech.log("Proyección cortada desde el panel.", "info")
    mech.stop_presentation()
    return {"ok": True}


class PlaybackPos(BaseModel):
    url: str | None = None
    position: float = 0.0
    index: int | None = None
    slug: str | None = None


@app.post("/api/playback")
async def playback_report(p: PlaybackPos):
    """La pantalla principal reporta por qué segundo va el video que muestra.

    Es lo que permite que el visor VR del teléfono **no empiece el video
    desde cero**: se engancha en el mismo punto que el proyector, que es el
    que va sincronizado con el audio. Lo manda `/projector` cada pocos
    segundos y cada vez que cambia de archivo.
    """
    get_app().report_playback(p.url, p.position, p.index, p.slug)
    return {"ok": True}


class PlaylistEnded(BaseModel):
    slug: str | None = None
    # Cuántos archivos llegaron al final de verdad, y cuáles no se pudieron
    # reproducir. Sin esto, una playlist entera que falla se veía igual que
    # una que terminó bien.
    played: int = 0
    failed: list[dict] = []


@app.post("/api/playlist/ended")
async def playlist_ended(p: PlaylistEnded):
    """La PANTALLA avisa que terminó el último video de la playlist.

    El backend no sabe cuánto dura cada mp4, así que el fin de la
    reproducción lo marca quien de verdad lo sabe: el `<video>` del
    proyector, cuando dispara su evento `ended` en el último archivo.

    También nos dice cuáles NO pudo reproducir: si el navegador no sabe
    decodificar el archivo, la playlist "termina" en milisegundos y hay que
    poder distinguir eso de una proyección que salió bien.
    """
    ok = get_app().playlist_finished(p.slug, played=p.played, failed=p.failed)
    return {"ok": ok}


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
    "wake up MECH" = inglés, "bonjour MECH" = francés, "bom dia MECH" =
    portugués. Este endpoint existe para probar sin micrófono y para
    corregir sobre la marcha si Whisper entendió mal.
    """
    code = code.strip().lower()
    if code not in lang.SUPPORTED:
        raise HTTPException(
            400, f"Idioma inválido: {code}. Usa {' / '.join(lang.SUPPORTED)}."
        )
    mech = get_app()
    mech.set_language(code)
    return {"ok": True, "language": lang.current()}


# -- Modo traductor ("traduce MECH") -----------------------------------------


@app.post("/api/translate/start")
async def translate_start(
    src: str | None = None,
    dst: str | None = None,
    continuous: bool = False,
):
    """Arranca el traductor desde el panel.

    - `continuous=false` (por defecto) = lo mismo que decir «traduce MECH»:
      MECH traduce UNA frase y se calla.
    - `continuous=true` = lo mismo que «activa modo traductor»: se queda
      traduciendo hasta que le digan que lo desactive (o hasta `/stop`).

    Sin `src`/`dst` reutiliza el par de la vez anterior y, si no hay ninguno,
    pregunta por los idiomas en voz alta.
    """
    if not config.TRANSLATOR_ENABLED:
        raise HTTPException(400, "El modo traductor está desactivado (TRANSLATOR_ENABLED).")
    for code in (src, dst):
        if code and code not in lang.SUPPORTED:
            raise HTTPException(
                400, f"Idioma inválido: {code}. Usa {' / '.join(lang.SUPPORTED)}."
            )
    if src and dst and src == dst:
        raise HTTPException(400, "El origen y el destino no pueden ser el mismo idioma.")
    mech = get_app()
    # En un hilo: habla (bloqueante) y no queremos colgar la petición HTTP.
    threading.Thread(
        target=mech.start_translator,
        args=(src, dst),
        kwargs={"continuous": continuous},
        daemon=True,
    ).start()
    return {"ok": True, "continuous": continuous}


@app.post("/api/translate/stop")
async def translate_stop():
    """Sale del traductor Y olvida el par («desactiva el modo traductor»)."""
    mech = get_app()
    if not (translator.is_active() or translator.has_pair()):
        return {"ok": False, "reason": "El modo traductor no está activo."}
    threading.Thread(target=mech.stop_translator, daemon=True).start()
    return {"ok": True}


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
    mech = get_app()
    # El visor VR se alimenta de este sondeo: necesita saber cuántos segundos
    # han pasado desde el último reporte de la pantalla principal AHORA, no
    # cuando se reportó. Ver mech_app.report_playback().
    mech.refresh_playback()
    return mech.state


# -- Configuración en vivo (vista Ajustes del panel) -------------------------

def _to_bool(v: str) -> bool:
    return str(v).strip().lower() in ("1", "true", "yes", "on", "si", "sí")


# Claves que se pueden aplicar SIN reiniciar (se leen en cada turno).
_LIVE_KEYS = {
    "VAD_AGGRESSIVENESS": int,
    "VAD_SILENCE_TIMEOUT": float,
    "VAD_ENERGY_FACTOR": float,  # umbral de voz sobre el ruido ambiente
    # Cadena de audio antes de Whisper (ver docs/AUDIO.md).
    "AUDIO_HIGHPASS_HZ": float,   # quita continua y retumbe
    "AUDIO_TARGET_DBFS": float,   # nivel objetivo ("AGC")
    "TTS_GAIN_DB": float,         # empuje de volumen de la VOZ
    "TTS_NORMALIZE": _to_bool,
    "WHISPER_BEAM_SIZE": int,     # hipótesis que explora Whisper
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
    # Índice de la cámara. Cambiarlo NO reabre la que ya está en uso:
    # hay que apagar y encender la visión (o reiniciar) para que valga.
    "VISION_CAMERA_INDEX": int,
    "GESTURE_WHEELS": _to_bool,
    "ARM_GESTURE_MODE": str,
    "NARRATION_GESTURE_MODE": str,  # gestos simples (un brazo) al proyectar
    "ARM_WAVE_SECONDS": float,      # qué tan lento es el saludo
    "ARM_WAVE_HIGH": int,           # hasta dónde sube el brazo al saludar
    "ARM_WAVE_SWING": int,          # amplitud de las agitadas de arriba
    "ARM_WAVE_REPEATS": int,
    "GREETING_COOLDOWN": float,
    "GREETING_ONLY_DORMANT": _to_bool,  # saludar solo con MECH en reposo
    "GREETING_LANGUAGE": str,       # idioma del saludo por cámara
    "GREETING_REARM_SECONDS": float,   # ausencia para "visitante nuevo"
    "MOTOR_KICK_SECONDS": float,    # pulso a fondo para romper la fricción
    "ARM_WAVE_BOTH": _to_bool,      # el saludo levanta los dos brazos
    "ARM_INVERT_R": _to_bool,       # sentido de giro de cada brazo
    "ARM_INVERT_L": _to_bool,
    "RETURN_SPEED": int,
    "GESTURE_WHEEL_SPEED": int,
    "GESTURE_WHEEL_SECONDS": float,
    # Maniobra "mira hacia afuera" (se calibra EN EL ROBOT, sin encoders).
    "TURN_180_SPEED": int,
    "TURN_180_SECONDS": float,
    "TURN_180_INVERT": _to_bool,   # hacia qué lado se da la vuelta
    "ADVANCE_SECONDS": float,      # "avanza diez segundos"
    "ADVANCE_SPEED": int,
    "ADVANCE_MAX_SECONDS": float,
    "TURN_LATERAL_SPEED": int,
    "TURN_LATERAL_SECONDS": float,
    # Gesto "67" (ver backend/gesture_detect.py). Todo en vivo: se calibra
    # en el stand, con la luz y la distancia reales.
    "GESTURE67_ENABLED": _to_bool,
    "GESTURE67_WINDOW": float,
    "GESTURE67_MIN_AMPLITUDE": float,
    "GESTURE67_MAX_CORR": float,
    "GESTURE67_MIN_ALTERNATIONS": int,
    "GESTURE67_MIN_MOTION": float,
    "GESTURE67_BALANCE": float,
    "GESTURE67_COOLDOWN": float,
    "GESTURE67_ARM_HIGH": int,
    "GESTURE67_ARM_SECONDS": float,
    "GESTURE67_REPEATS": int,
    "GESTURE67_SAY": _to_bool,
    # Modo traductor.
    "TRANSLATOR_AUTO_DETECT": _to_bool,
    "TRANSLATOR_DRAIN_SECONDS": float,
    "TRANSLATOR_CONTINUOUS_DRAIN_SECONDS": float,
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
            "AUDIO_HIGHPASS_HZ": config.AUDIO_HIGHPASS_HZ,
            "AUDIO_TARGET_DBFS": config.AUDIO_TARGET_DBFS,
            "TTS_GAIN_DB": config.TTS_GAIN_DB,
            "TTS_NORMALIZE": config.TTS_NORMALIZE,
            "WHISPER_BEAM_SIZE": config.WHISPER_BEAM_SIZE,
            "TTS_DRY_RUN": config.TTS_DRY_RUN,
            "SUBTITLES_ENABLED": config.SUBTITLES_ENABLED,
            "VOICE_INTERRUPT_ENABLED": config.VOICE_INTERRUPT_ENABLED,
            "INTERRUPT_ENERGY_FACTOR": config.INTERRUPT_ENERGY_FACTOR,
            "VISION_ENABLED": config.VISION_ENABLED,
            "VISION_MIN_DISTANCE": config.VISION_MIN_DISTANCE,
            "VISION_APPROACH": config.VISION_APPROACH,
            "VISION_FOLLOW": config.VISION_FOLLOW,
            "VISION_PROJECT_GATE": config.VISION_PROJECT_GATE,
            "VISION_CAMERA_INDEX": config.VISION_CAMERA_INDEX,
            "GESTURE_WHEELS": config.GESTURE_WHEELS,
            "ARM_GESTURE_MODE": config.ARM_GESTURE_MODE,
            "NARRATION_GESTURE_MODE": config.NARRATION_GESTURE_MODE,
            "ARM_WAVE_SECONDS": config.ARM_WAVE_SECONDS,
            "ARM_WAVE_HIGH": config.ARM_WAVE_HIGH,
            "ARM_WAVE_SWING": config.ARM_WAVE_SWING,
            "ARM_WAVE_REPEATS": config.ARM_WAVE_REPEATS,
            "GREETING_COOLDOWN": config.GREETING_COOLDOWN,
            "GREETING_ONLY_DORMANT": config.GREETING_ONLY_DORMANT,
            "GREETING_LANGUAGE": config.GREETING_LANGUAGE,
            "GREETING_REARM_SECONDS": config.GREETING_REARM_SECONDS,
            "MOTOR_KICK_SECONDS": config.MOTOR_KICK_SECONDS,
            "ARM_WAVE_BOTH": config.ARM_WAVE_BOTH,
            "ARM_INVERT_R": config.ARM_INVERT_R,
            "ARM_INVERT_L": config.ARM_INVERT_L,
            "RETURN_SPEED": config.RETURN_SPEED,
            "GESTURE_WHEEL_SPEED": config.GESTURE_WHEEL_SPEED,
            "GESTURE_WHEEL_SECONDS": config.GESTURE_WHEEL_SECONDS,
            "TURN_180_SPEED": config.TURN_180_SPEED,
            "TURN_180_SECONDS": config.TURN_180_SECONDS,
            "TURN_180_INVERT": config.TURN_180_INVERT,
            "ADVANCE_SECONDS": config.ADVANCE_SECONDS,
            "ADVANCE_SPEED": config.ADVANCE_SPEED,
            "ADVANCE_MAX_SECONDS": config.ADVANCE_MAX_SECONDS,
            "TURN_LATERAL_SPEED": config.TURN_LATERAL_SPEED,
            "TURN_LATERAL_SECONDS": config.TURN_LATERAL_SECONDS,
            "GESTURE67_ENABLED": config.GESTURE67_ENABLED,
            "GESTURE67_WINDOW": config.GESTURE67_WINDOW,
            "GESTURE67_MIN_AMPLITUDE": config.GESTURE67_MIN_AMPLITUDE,
            "GESTURE67_MAX_CORR": config.GESTURE67_MAX_CORR,
            "GESTURE67_MIN_ALTERNATIONS": config.GESTURE67_MIN_ALTERNATIONS,
            "GESTURE67_MIN_MOTION": config.GESTURE67_MIN_MOTION,
            "GESTURE67_BALANCE": config.GESTURE67_BALANCE,
            "GESTURE67_COOLDOWN": config.GESTURE67_COOLDOWN,
            "GESTURE67_ARM_HIGH": config.GESTURE67_ARM_HIGH,
            "GESTURE67_ARM_SECONDS": config.GESTURE67_ARM_SECONDS,
            "GESTURE67_REPEATS": config.GESTURE67_REPEATS,
            "GESTURE67_SAY": config.GESTURE67_SAY,
            "TRANSLATOR_AUTO_DETECT": config.TRANSLATOR_AUTO_DETECT,
            "TRANSLATOR_DRAIN_SECONDS": config.TRANSLATOR_DRAIN_SECONDS,
            "TRANSLATOR_CONTINUOUS_DRAIN_SECONDS":
                config.TRANSLATOR_CONTINUOUS_DRAIN_SECONDS,
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
