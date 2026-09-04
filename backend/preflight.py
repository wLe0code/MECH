"""Chequeo previo al evento: ¿está TODO listo para funcionar?

Correr en la Pi, con el server APAGADO (usa el micrófono y el Arduino):

    python -m backend.preflight

Y si querés simular que no hay internet (lo importante de verdad):

    python -m backend.preflight --sin-red

Qué responde
------------

La pregunta que importa en un evento no es "¿funciona?", sino **"¿qué deja de
funcionar si se cae el wifi?"**. Este script separa las dos cosas:

  - Lo que corre EN LOCAL (micrófono, Whisper, Arduino, motores, proyección,
    videos de la biblioteca, panel web) sigue funcionando sin red.
  - Lo que NECESITA internet (Claude para el guion, ElevenLabs para la voz,
    Gemini para las imágenes de respaldo) no tiene sustituto offline.

Códigos de salida: 0 = todo OK, 1 = hay algún FALLO.
"""

from __future__ import annotations

import os
import shutil
import socket
import sys
import time
from pathlib import Path

# Permite correrlo tanto con `python -m backend.preflight` como directo.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402


# Una herramienta de diagnóstico NO puede reventar: sería lo peor que podría
# pasar justo cuando la estás usando para saber qué falla. Las consolas de
# Windows (cp1252) no saben pintar acentos ni flechas, así que forzamos UTF-8
# y, si aun así falla, se reemplaza el carácter en vez de lanzar excepción.
for _flujo in (sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SIN_RED = "--sin-red" in sys.argv or "--offline" in sys.argv

_OK, _WARN, _FAIL = "OK  ", "AVISO", "FALLA"
_resultados: list[tuple[str, str, str]] = []


def _print(texto: str) -> None:
    """print() que nunca lanza, pase lo que pase con la codificación."""
    try:
        print(texto)
    except Exception:
        try:
            print(texto.encode("ascii", "replace").decode())
        except Exception:
            pass


def _di(estado: str, titulo: str, detalle: str = "") -> None:
    _resultados.append((estado, titulo, detalle))
    marca = {_OK: "  [ OK ]", _WARN: "  [aviso]", _FAIL: "  [FALLA]"}[estado]
    _print(f"{marca} {titulo}")
    for linea in (detalle.splitlines() if detalle else []):
        _print(f"          {linea}")


def _titulo(t: str) -> None:
    _print("")
    _print(t)
    _print("-" * len(t))


# ---------------------------------------------------------------------------
# 1. Dependencias de Python
# ---------------------------------------------------------------------------

def check_dependencias() -> None:
    _titulo("1. Dependencias de Python")
    _print(f"  Python {sys.version.split()[0]}")

    obligatorias = {
        "faster_whisper": "transcribir la voz (STT local)",
        "sounddevice": "grabar del micrófono",
        "webrtcvad": "detectar cuándo alguien habla",
        "numpy": "procesar el audio",
        "soundfile": "leer/escribir audio",
        "serial": "hablar con el Arduino",
        "anthropic": "pedirle el guion a Claude",
        "elevenlabs": "generar la voz",
        "fastapi": "el servidor y el panel",
        "uvicorn": "el servidor",
    }
    opcionales = {
        "cv2": "visión por cámara (saludo al detectar a alguien)",
        "mediapipe": "visión de largo alcance (opcional, no va en Python 3.13)",
        "google.genai": "imágenes de respaldo con Gemini",
    }

    faltan = []
    for mod, para in obligatorias.items():
        try:
            __import__(mod)
        except Exception as e:
            faltan.append(f"{mod} ({para}): {e}")
    if faltan:
        _di(_FAIL, "Faltan dependencias obligatorias",
            "\n".join(faltan) + "\n-> pip install -r backend/requirements.txt")
    else:
        _di(_OK, f"Las {len(obligatorias)} dependencias obligatorias están")

    sin_opcional = []
    for mod, para in opcionales.items():
        try:
            __import__(mod)
        except Exception:
            sin_opcional.append(f"{mod}: sin esto no hay {para}")
    if sin_opcional:
        _di(_WARN, "Faltan opcionales (el robot arranca igual)",
            "\n".join(sin_opcional))
    else:
        _di(_OK, "Las opcionales también están")


# ---------------------------------------------------------------------------
# 2. Whisper offline — lo que más duele si falla
# ---------------------------------------------------------------------------

def check_whisper() -> None:
    _titulo("2. Whisper (transcripción) — tiene que funcionar SIN internet")
    _print(f"  Modelo: {config.WHISPER_MODEL!r} · WHISPER_OFFLINE={config.WHISPER_OFFLINE}")

    if not config.WHISPER_OFFLINE:
        _di(_WARN, "WHISPER_OFFLINE=false: intentará ir a la red al arrancar",
            "Si el wifi del recinto va mal, eso puede COLGAR el arranque.\n"
            "-> Ponelo en true en backend/.env salvo que tengas que descargar "
            "un modelo nuevo ahora mismo.")

    try:
        import stt
        t0 = time.time()
        stt.get_model()
        _di(_OK, f"El modelo carga del disco ({time.time() - t0:.1f} s)",
            "Confirmado: transcribir NO necesita internet.")
    except Exception as e:
        _di(_FAIL, "Whisper NO puede cargar",
            f"{e}\n"
            "-> Con internet, UNA vez: WHISPER_OFFLINE=false en backend/.env, "
            "arrancá el server, esperá a que descargue, y volvé a poner true.")
        return

    # El de las interrupciones ("oye MECH") puede ser otro modelo distinto.
    if config.VOICE_INTERRUPT_ENABLED:
        objetivo = config.WHISPER_INTERRUPT_MODEL or config.WHISPER_MODEL
        try:
            import stt
            stt.get_interrupt_model()
            _di(_OK, f"El modelo de interrupción ({objetivo!r}) también carga")
        except Exception as e:
            _di(_WARN, f"El modelo de interrupción ({objetivo!r}) no carga",
                f"{e}\n"
                "-> Dejá WHISPER_INTERRUPT_MODEL vacío para reusar el normal, "
                "o apagá 'Interrumpir' en Ajustes.")


# ---------------------------------------------------------------------------
# 3. Claves de API
# ---------------------------------------------------------------------------

def check_claves() -> None:
    _titulo("3. Claves de API")
    env = Path(__file__).resolve().parent / ".env"
    if not env.exists():
        _di(_FAIL, "No existe backend/.env",
            "-> cp backend/.env.example backend/.env y rellenar las claves.")
        return
    _di(_OK, f"backend/.env existe ({env.stat().st_size} bytes)")

    for clave, valor, para in (
        ("ANTHROPIC_API_KEY", config.ANTHROPIC_API_KEY, "el guion (SIN esto MECH no narra nada)"),
        ("ELEVENLABS_API_KEY", config.ELEVENLABS_API_KEY, "la voz (SIN esto MECH no habla)"),
        ("GOOGLE_API_KEY", config.GOOGLE_API_KEY, "las imágenes de respaldo"),
    ):
        if valor:
            _di(_OK, f"{clave} configurada")
        elif clave == "GOOGLE_API_KEY":
            _di(_WARN, f"{clave} vacía", f"Sin esto no hay {para}.")
        else:
            _di(_FAIL, f"{clave} vacía", f"Se necesita para {para}.")


# ---------------------------------------------------------------------------
# 4. Qué necesita internet y qué no
# ---------------------------------------------------------------------------

def _llega(host: str, puerto: int = 443, espera: float = 4.0) -> bool:
    try:
        with socket.create_connection((host, puerto), timeout=espera):
            return True
    except OSError:
        return False


def check_red() -> None:
    _titulo("4. Internet: qué se cae si no hay wifi")

    servicios = [
        ("api.anthropic.com", "Claude", "MECH no puede armar el guion: no narra NADA."),
        ("api.elevenlabs.io", "ElevenLabs", "MECH se queda MUDO (no hay voz)."),
        ("generativelanguage.googleapis.com", "Gemini",
         "Sin imágenes de respaldo. Las obras CON video en la biblioteca no se enteran."),
    ]

    if SIN_RED:
        _di(_WARN, "Modo --sin-red: no compruebo la conexión",
            "Se asume que NO hay internet. Mirá abajo qué implica.")
        alcanzables = {n: False for _, n, _ in servicios}
    else:
        alcanzables = {}
        for host, nombre, _ in servicios:
            ok = _llega(host)
            alcanzables[nombre] = ok
            if ok:
                _di(_OK, f"{nombre} alcanzable ({host})")
            else:
                _di(_WARN, f"{nombre} NO alcanzable ({host})",
                    "Puede ser el wifi, un firewall o client isolation del recinto.")

    _print("")
    _print("  SIN internet SIGUE funcionando (todo esto es local):")
    for linea in (
        "micrófono y transcripción (Whisper corre en la Pi)",
        "palabra clave 'ok MECH', dormirse y despertarse",
        "'mira hacia afuera' / 'regresa a proyectar' (no pasan por Claude)",
        "'proyecta marketing' y los videos de la biblioteca, CON su audio",
        "el saludo al detectar a alguien con la cámara",
        "motores, brazos y toda la movilidad",
        "el panel web, el proyector y la vista VR",
    ):
        _print(f"    - {linea}")
    _print("")
    _print("  SIN internet NO funciona (no hay sustituto local):")
    for linea in (
        "narrar una obra: el guion lo escribe Claude",
        "hablar: la voz la genera ElevenLabs",
        "las imágenes de respaldo de Gemini",
    ):
        _print(f"    - {linea}")
    _print("")
    _print("  PLAN B si el wifi del recinto falla: hotspot del celular.")
    _print("    Y si no hay datos, lo que sigue en pie es la proyección de")
    _print("    marketing y los videos de biblioteca, que son archivos locales.")


# ---------------------------------------------------------------------------
# 5. Audio
# ---------------------------------------------------------------------------

def check_audio() -> None:
    _titulo("5. Audio (micrófono y parlante)")
    try:
        import sounddevice as sd
        dispositivos = sd.query_devices()
    except Exception as e:
        _di(_FAIL, "No puedo consultar el audio", str(e))
        return

    entradas = [(i, d) for i, d in enumerate(dispositivos) if d["max_input_channels"] > 0]
    if not entradas:
        _di(_FAIL, "No hay NINGÚN micrófono",
            "-> ¿Está enchufado el receptor USB del Steren?")
        return

    buscado = (config.AUDIO_INPUT_DEVICE or "").strip()
    if not buscado:
        _di(_WARN, "AUDIO_INPUT_DEVICE vacío: usa el micrófono por defecto",
            "Con varios dispositivos puede agarrar el equivocado.\n"
            "-> Poné 'Steren' (o el índice) en backend/.env.\n"
            "Entradas: " + ", ".join(f"[{i}] {d['name']}" for i, d in entradas))
    else:
        coincide = [
            (i, d) for i, d in entradas
            if buscado.lower() in d["name"].lower() or buscado == str(i)
        ]
        if coincide:
            _di(_OK, f"Micrófono {buscado!r} encontrado: {coincide[0][1]['name']}")
        else:
            _di(_FAIL, f"AUDIO_INPUT_DEVICE={buscado!r} no coincide con nada",
                "Entradas: " + ", ".join(f"[{i}] {d['name']}" for i, d in entradas))

    # Abrirlo de verdad: los mics USB baratos no aceptan cualquier sample rate.
    try:
        import sounddevice as sd
        grab = sd.rec(
            int(0.3 * config.AUDIO_SAMPLE_RATE),
            samplerate=config.AUDIO_SAMPLE_RATE,
            channels=1, dtype="int16",
            device=(buscado if buscado else None),
        )
        sd.wait()
        pico = int(abs(grab).max())
        _di(_OK, f"Grabé 0.3 s a {config.AUDIO_SAMPLE_RATE} Hz (pico {pico})",
            "Pico muy bajo puede ser normal en silencio; si al hablar sigue "
            "en cero, revisá el micrófono."
            if pico < 50 else "")
    except Exception as e:
        _di(_FAIL, f"No pude grabar a {config.AUDIO_SAMPLE_RATE} Hz",
            f"{e}\n-> Muchos mics USB no abren a 16000. Probá "
            "AUDIO_SAMPLE_RATE=48000 en backend/.env.")

    # Salida: el TTS prueba varios reproductores en orden.
    players = [p for p in ("pw-play", "paplay", "ffplay", "aplay") if shutil.which(p)]
    if players:
        _di(_OK, f"Reproductores de audio disponibles: {', '.join(players)}")
    else:
        _di(_FAIL, "No hay ningún reproductor (pw-play/paplay/ffplay/aplay)",
            "-> sudo apt install pipewire-audio-client-libraries ffmpeg")

    if shutil.which("ffplay"):
        _di(_OK, "ffplay presente (música de fondo y audio del marketing)")
    else:
        _di(_WARN, "Sin ffplay: no habrá música de fondo",
            "El resto funciona igual. -> sudo apt install ffmpeg")


# ---------------------------------------------------------------------------
# 6. Arduino
# ---------------------------------------------------------------------------

def check_arduino() -> None:
    _titulo("6. Arduino (motores y brazos)")
    try:
        from serial.tools import list_ports
    except Exception as e:
        _di(_FAIL, "pyserial no está", str(e))
        return

    puertos = list(list_ports.comports())
    if not puertos:
        _di(_FAIL, "No hay NINGÚN puerto serie",
            "-> ¿Está enchufado el Arduino por USB?\n"
            "El server arranca igual y reintenta solo, pero sin movimiento.")
        return

    _print("  Puertos: " + ", ".join(f"{p.device} ({p.description})" for p in puertos))
    pistas = ("arduino", "ch340", "ch341", "usb serial", "ttyacm", "usb-serial")
    candidatos = [
        p.device for p in puertos
        if any(h in f"{p.device} {p.description or ''}".lower() for h in pistas)
    ]
    if candidatos:
        _di(_OK, f"Arduino detectado en {candidatos[0]}")
    else:
        _di(_WARN, "Ningún puerto parece un Arduino",
            f"Configurado: ARDUINO_PORT={config.ARDUINO_PORT}. "
            "Se autodetecta al arrancar, pero revisá el cable.")


# ---------------------------------------------------------------------------
# 7. Biblioteca de videos
# ---------------------------------------------------------------------------

def check_biblioteca() -> None:
    _titulo("7. Biblioteca de videos (todo local, no necesita internet)")
    import video_library

    if not config.VIDEO_LIBRARY_DIR.exists():
        _di(_WARN, "No existe la carpeta de la biblioteca",
            f"{config.VIDEO_LIBRARY_DIR}\nSe crea sola al subir el primer video.")

    completas, incompletas, promo = [], [], []
    for w in video_library.available_works():
        etiqueta = f"{w['title']} ({w['present_segments']}/{w['segments']})"
        if w.get("promo"):
            promo.append(etiqueta)
        elif w["complete"]:
            completas.append(etiqueta)
        else:
            incompletas.append(etiqueta)

    if completas:
        _di(_OK, f"{len(completas)} obra(s) con video completo",
            "\n".join(completas))
    else:
        _di(_WARN, "Ninguna obra tiene el video completo",
            "MECH las narra igual generando imágenes con Gemini EN VIVO,\n"
            "pero eso SÍ necesita internet. Con los videos subidos, no.")
    if incompletas:
        _di(_WARN, f"{len(incompletas)} obra(s) sin completar (usarán Gemini)",
            "\n".join(incompletas))

    for etiqueta in promo:
        n = int(etiqueta.split("(")[1].split("/")[0])
        if n:
            _di(_OK, f"Slot de proyección directa: {etiqueta}",
                "Se proyecta con su propio audio diciendo 'proyecta marketing'.")
        else:
            _di(_WARN, f"Slot de proyección directa VACÍO: {etiqueta}",
                "-> Subí los videos en /library si lo vas a usar mañana.")


# ---------------------------------------------------------------------------
# 8. Frontend sin internet
# ---------------------------------------------------------------------------

def check_frontend() -> None:
    _titulo("8. Panel y proyección sin internet")
    front = Path(__file__).resolve().parent.parent / "frontend"

    necesarios = [
        front / "vendor" / "mech-icons.css",
        front / "vendor" / "mech-fonts.css",
        front / "vendor" / "fonts" / "tabler-icons.woff2",
    ]
    faltan = [str(p.relative_to(front.parent)) for p in necesarios if not p.exists()]
    if faltan:
        _di(_FAIL, "Faltan los iconos/fuentes locales",
            "\n".join(faltan) + "\n"
            "-> Sin esto, y sin internet, los botones del panel que son SOLO\n"
            "  icono se ven EN BLANCO. Ver scripts/README.md.")
    else:
        _di(_OK, "Iconos y fuentes servidos en local")

        # Que el CSS reducido tenga TODOS los iconos que usa el panel: si
        # alguien anade un icono nuevo y no regenera, ese boton sale vacio.
        import re
        css = (front / "vendor" / "mech-icons.css").read_text(encoding="utf-8")
        definidos = set(re.findall(r"\.ti-([a-z0-9-]+):before", css))
        usados = set()
        for f in list(front.glob("*.html")) + list(front.glob("*.js")):
            usados |= set(re.findall(r"ti ti-([a-z0-9-]+)", f.read_text(encoding="utf-8")))
        sin_definir = sorted(usados - definidos)
        if sin_definir:
            _di(_FAIL, f"{len(sin_definir)} icono(s) del panel sin glifo",
                ", ".join(sin_definir)
                + "\n-> Esos botones se ven VACIOS."
                + "\n-> Regeneralo con: python scripts/mkicons.py")
        else:
            _di(_OK, f"Los {len(usados)} iconos del panel tienen glifo")

        # Y que los archivos de fuente que pide el CSS existan de verdad.
        fcss = (front / "vendor" / "mech-fonts.css").read_text(encoding="utf-8")
        # Google Fonts escribe url(...) sin comillas; el CSS de iconos con
        # ellas. Aceptamos las dos formas.
        refs = re.findall(r'url\(["\']?\./fonts/([^"\')]+)["\']?\)', fcss)
        refs += re.findall(r'url\(["\']?\./fonts/([^"\')]+)["\']?\)',
                           (front / "vendor" / "mech-icons.css").read_text(encoding="utf-8"))
        perdidos = [r for r in refs if not (front / "vendor" / "fonts" / r).exists()]
        if perdidos:
            _di(_FAIL, "Faltan archivos de fuente", ", ".join(perdidos))
        else:
            _di(_OK, f"Las {len(set(refs))} fuentes del panel estan en disco")

    # Que no se haya colado otra vez una URL externa en las páginas.
    externas = []
    for p in sorted(front.glob("*.html")) + sorted(front.glob("*.css")):
        for n, linea in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for marca in ("http://", "https://"):
                if marca in linea and "ip-de-la-pi" not in linea and "localhost" not in linea:
                    # Los comentarios con enlaces de documentación no cuentan.
                    if any(t in linea for t in ("src=", "href=", "@import", "url(http")):
                        externas.append(f"{p.name}:{n}  {linea.strip()[:90]}")
    if externas:
        _di(_FAIL, "Hay recursos EXTERNOS en el frontend",
            "\n".join(externas) + "\n-> Sin wifi eso no carga. Bajalo a "
            "frontend/vendor/ (ver scripts/README.md).")
    else:
        _di(_OK, "Ninguna página carga nada de internet")


# ---------------------------------------------------------------------------
# 9. El .env que tapa los defaults (gotcha histórico del proyecto)
# ---------------------------------------------------------------------------

def check_env_sombra() -> None:
    _titulo("9. Claves del .env que TAPAN los defaults del código")
    env = Path(__file__).resolve().parent / ".env"
    if not env.exists():
        return

    vigiladas = {
        "VOICE_WAKE_PHRASES": "si no está 'ok mech' en tu lista, no despierta",
        "VOICE_WAKE_PHRASES_EN": "afecta a 'wake up MECH'",
        "VOICE_SLEEP_PHRASES": "afecta a dormirlo",
        "VOICE_INTERRUPT_PHRASES": "afecta a 'oye MECH'",
        "VOICE_OUTWARD_PHRASES": "afecta a 'mira hacia afuera'",
        "VOICE_PROJECT_PHRASES": "afecta a 'regresa a proyectar'",
        "VOICE_MARKETING_PHRASES": "afecta a 'proyecta marketing'",
        "ARM_GESTURE_MODE": "en 'subtle' los gestos casi no se ven",
    }
    encontradas = []
    for linea in env.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave = linea.split("=", 1)[0].strip()
        if clave in vigiladas:
            encontradas.append(f"{clave}  ->  {vigiladas[clave]}")

    if encontradas:
        _di(_WARN, "Estas claves están escritas a mano y GANAN al código",
            "\n".join(encontradas) + "\n"
            "Ya ha pasado: una lista vieja aquí hace que una frase nueva no\n"
            "funcione. Si algo 'no responde', borrá la línea y reiniciá.")
    else:
        _di(_OK, "El .env no tapa ninguna lista de frases")

    if config.ARM_GESTURE_MODE == "subtle":
        _di(_WARN, "ARM_GESTURE_MODE=subtle",
            "Los gestos quedan en un vaivén de pocos grados. El SALUDO ya no\n"
            "se encoge, pero el resto sí. Ponelo en 'full' para el evento.")


# ---------------------------------------------------------------------------
# 10. Disco
# ---------------------------------------------------------------------------

def check_disco() -> None:
    _titulo("10. Espacio en disco")
    try:
        uso = shutil.disk_usage(str(Path(__file__).resolve().parent))
        libre_gb = uso.free / (1024 ** 3)
        detalle = f"{libre_gb:.1f} GB libres de {uso.total / (1024 ** 3):.1f} GB"
        if libre_gb < 1:
            _di(_FAIL, "Queda muy poco disco", detalle)
        elif libre_gb < 3:
            _di(_WARN, "Disco justo", detalle + "\nLos videos y las imágenes generadas ocupan.")
        else:
            _di(_OK, "Espacio suficiente", detalle)
    except Exception as e:
        _di(_WARN, "No pude medir el disco", str(e))


# ---------------------------------------------------------------------------

def main() -> int:
    _print("=" * 68)
    _print("  MECH - chequeo previo al evento")
    if SIN_RED:
        _print("  (modo --sin-red: asumiendo que NO hay internet)")
    _print("=" * 68)

    for fn in (
        check_dependencias, check_whisper, check_claves, check_red,
        check_audio, check_arduino, check_biblioteca, check_frontend,
        check_env_sombra, check_disco,
    ):
        try:
            fn()
        except Exception as e:  # que un chequeo roto no tumbe el resto
            _di(_FAIL, f"El chequeo {fn.__name__} reventó", repr(e))

    fallos = [r for r in _resultados if r[0] == _FAIL]
    avisos = [r for r in _resultados if r[0] == _WARN]

    print()
    _print("=" * 68)
    _print(f"  RESUMEN: {len(_resultados) - len(fallos) - len(avisos)} OK · "
          f"{len(avisos)} avisos · {len(fallos)} fallos")
    _print("=" * 68)
    if fallos:
        print("\n  HAY QUE ARREGLAR ANTES DEL EVENTO:")
        for _, titulo, _d in fallos:
            _print(f"    - {titulo}")
    if avisos:
        print("\n  Avisos (no bloquean, pero míralos):")
        for _, titulo, _d in avisos:
            _print(f"    - {titulo}")
    if not fallos and not avisos:
        print("\n  Todo en orden. Suerte mañana.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
