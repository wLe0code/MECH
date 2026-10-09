"""Buscar el video de una canción en YouTube (para el modo música).

De aquí sale TODO lo que suena en el modo música (decisión del equipo, oct
2026: solo YouTube). Tienen YouTube Premium: con la sesión iniciada en el
Chromium de la Pi, sin anuncios.

Reparto del trabajo:
  - `llm.interpret_song` pone en limpio lo que se pidió (título y artista);
  - este módulo busca qué VIDEO de YouTube es esa canción;
  - `frontend/music.js` lo reproduce en la pantalla con el reproductor
    oficial de YouTube (IFrame API). Nada se descarga ni se extrae: es el
    reproductor de YouTube, a la vista, como piden sus condiciones.

Usa la «YouTube Data API v3», que pide una CLAVE gratuita de Google
(`YOUTUBE_API_KEY` en el `.env`). Tiene que ser una «Clave de API» de las de
siempre, las que empiezan por «AIza»: las nuevas de Google AI Studio («AQ.…»,
como la de Gemini) YouTube las rechaza. Cada canción gasta 101 unidades de
las 10 000 diarias: unas 99 canciones al día. Lo ya buscado se recuerda unas
horas para no gastar de más.

La clave se lee del `.env` EN VIVO y perdonando los deslices de pegarla a
mano (ver «La clave», más abajo). ⚠️ Nada de este módulo imprime la clave.

Solo se devuelven videos que YouTube deja reproducir fuera de youtube.com
(`videoEmbeddable`), de duración de canción, y sin restricción de edad. Aun
así un video puede negarse al reproducirlo: por eso se devuelven VARIOS, y la
pantalla prueba el siguiente.

Solo librería estándar.
"""

from __future__ import annotations

import html
import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

import config

API = "https://www.googleapis.com/youtube/v3/"
ESPERA_RED_S = 10
CACHE_S = 6 * 3600
CANDIDATOS = 3

# Palabras que delatan que el video NO es la canción tal cual. Solo restan si
# el visitante no las pidió («Despacito remix» sí quiere el remix).
_DISTINTO = ("karaoke", "cover", "remix", "reaction", "reaccion", "tutorial",
             "slowed", "sped up", "nightcore", "8d", "1 hour", "1 hora",
             "10 hours", "loop", "live", "en vivo", "instrumental", "parodia",
             "parody", "mashup")

_cache: dict[tuple, tuple[float, list[dict]]] = {}
# Si la clave no sirve (no es válida, o su proyecto no tiene la API de YouTube
# activada) no tiene sentido preguntar en cada canción: se apunta el motivo y
# se deja de intentar hasta `_hasta`. El bloqueo es de ESA clave: si la
# cambian en el `.env`, la nueva se prueba enseguida. Y no dura hasta
# reiniciar (así era antes): lo normal es arreglarlo en la consola de Google,
# donde la clave no cambia, y MECH se quedaba diciendo que no podía.
_bloqueo: str = ""
_bloqueo_clave: str = ""
_hasta: float = 0.0
REINTENTO_S = 120          # clave rechazada: se vuelve a probar pasado esto
CUOTA_S = 3600             # cuota agotada: se vuelve a probar en una hora


def _plano(texto: str) -> str:
    """Minúsculas, sin acentos ni signos: para comparar nombres."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    return re.sub(r"[^\w]+", " ", texto, flags=re.UNICODE).strip()


class ErrorYouTube(RuntimeError):
    """YouTube no dejó buscar. `motivo` es su código; el mensaje, en cristiano."""

    def __init__(self, motivo: str, mensaje: str) -> None:
        super().__init__(mensaje)
        self.motivo = motivo


# ── La clave ────────────────────────────────────────────────────────────────
#
# Se lee de `backend/.env` EN VIVO, no solo al arrancar (oct 2026). El equipo
# pegó la clave a mano al final del `.env` y «no se conectaba»: con el `.env`
# leído una vez al arrancar, cualquier desliz al pegarla (o no reiniciar)
# dejaba el modo sin clave, y encima se probaba con la de Gemini, que YouTube
# rechaza con un mensaje en inglés que no dice qué hacer. Ahora:
#   - si el archivo cambia se vuelve a leer: no hace falta reiniciar;
#   - se entiende lo que se cuela al pegar a mano: comillas, espacios, el
#     nombre en minúsculas, «:» en vez de «=», la línea pegada a la de antes,
#     una línea vacía de la plantilla más arriba o más abajo, y la clave
#     suelta sin nombre delante;
#   - y si no está, se mira si la pusieron en un archivo que MECH no lee.

_FORMA_NORMAL = re.compile(r"AIza[\w-]{35}$")      # una «Clave de API» de siempre
_LINEA = re.compile(r"YOUTUBE[ _-]?API[ _-]?KEY\s*[=:]\s*(.*)$", re.IGNORECASE)
_SOBRA = " \t\"'“”‘’`<>"

_env_visto: tuple | None = None                    # (ruta, fecha, tamaño) ya leídos
_env_leido: tuple[str, bool] = ("", False)


def _en_texto(texto: str) -> tuple[str, bool]:
    """(clave, ¿iba suelta?) de un `.env`. Manda la ÚLTIMA línea con valor."""
    con_nombre = suelta = ""
    # Los ceros: `>>` en PowerShell añade en UTF-16 (una letra, un cero…).
    for linea in texto.replace("\x00", "").replace("﻿", "").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        m = _LINEA.search(linea)
        if m:
            con_nombre = m.group(1).split(" #", 1)[0].strip(_SOBRA) or con_nombre
        elif _FORMA_NORMAL.match(linea.strip(_SOBRA)):
            suelta = linea.strip(_SOBRA)
    return (con_nombre, False) if con_nombre else (suelta, bool(suelta))


def _leer(ruta) -> tuple[str, bool]:
    try:
        return _en_texto(ruta.read_bytes().decode("utf-8", "ignore"))
    except Exception:
        return "", False


def _del_env() -> tuple[str, bool]:
    """La clave que hay AHORA en backend/.env (se relee solo si cambió)."""
    global _env_visto, _env_leido
    ruta = getattr(config, "ENV_PATH", None)
    try:
        st = ruta.stat()
        visto = (str(ruta), st.st_mtime_ns, st.st_size)
    except Exception:                               # no hay .env
        _env_visto, _env_leido = None, ("", False)
        return _env_leido
    if visto != _env_visto:
        _env_visto, _env_leido = visto, _leer(ruta)
    return _env_leido


def _clave() -> tuple[str, str]:
    """(clave, de dónde sale): "YOUTUBE_API_KEY", "GOOGLE_API_KEY" o ""."""
    propia = _del_env()[0] or (config.YOUTUBE_API_KEY or "").strip()
    if propia:
        return propia, "YOUTUBE_API_KEY"
    # La de Gemini solo se prueba si es una clave de las de siempre. Las
    # nuevas de AI Studio («AQ.…») YouTube las rechaza con un 401 (comprobado
    # el 9 oct 2026): probar con ellas solo servía para entrar al modo,
    # preguntar la canción y fallar después.
    gemini = (config.GOOGLE_API_KEY or "").strip()
    return (gemini, "GOOGLE_API_KEY") if _FORMA_NORMAL.match(gemini) else ("", "")


def clave() -> str:
    return _clave()[0]


def aviso() -> str:
    """Algo mal escrito en el `.env` que se entendió igual (para el panel)."""
    if _del_env()[1]:
        return ("en backend/.env la clave está suelta, sin nombre delante. La "
                "uso igual, pero la línea tiene que ser YOUTUBE_API_KEY=<la clave>")
    return ""


def _falta() -> str:
    """Por qué no hay clave, con la pista de dónde puede haber quedado."""
    falta = "falta YOUTUBE_API_KEY en backend/.env"
    ruta = getattr(config, "ENV_PATH", None)
    try:
        if not ruta.exists():
            return ("no existe backend/.env (se crea copiando backend/.env.example); "
                    "ahí va la línea YOUTUBE_API_KEY=<la clave>")
        for otro, nombre, ojo in (
            (ruta.with_name(".env.example"), "backend/.env.example",
             " y bórrala de ahí: ese archivo es la plantilla y se sube a GitHub"),
            (ruta.parent.parent / ".env", "un .env que está fuera de la carpeta backend", ""),
        ):
            if _leer(otro)[0]:
                return f"{falta}: la clave está en {nombre}, que MECH no lee. Pásala a backend/.env{ojo}"
    except Exception:
        pass
    return falta + " (una línea así: YOUTUBE_API_KEY=<la clave>, sin espacios ni comillas)"


def disponible() -> bool:
    """¿Se puede buscar en YouTube ahora mismo?"""
    k = clave()
    if not k:
        return False
    if _bloqueo and _bloqueo_clave == k and time.time() < _hasta:
        return False
    return True


def por_que_no() -> str:
    """Por qué no se puede usar YouTube (para decirlo en el panel)."""
    k = clave()
    if not k:
        return _falta()
    return _bloqueo if _bloqueo_clave == k else ""


_CONSOLA = "console.cloud.google.com → «APIs y servicios» → «Credenciales»"
_CUOTA = ("quotaExceeded", "dailyLimitExceeded")
_EXPLICADO = {
    "quotaExceeded": "se acabaron las búsquedas de hoy en YouTube (vuelven mañana)",
    "dailyLimitExceeded": "se acabaron las búsquedas de hoy en YouTube (vuelven mañana)",
    "keyInvalid": (
        "Google dice que esa clave no existe o caducó: cópiala otra vez, "
        "entera, en YOUTUBE_API_KEY de backend/.env"),
    "tipoDeClave": (
        "esa clave no es del tipo que acepta YouTube. Tiene que ser una «Clave "
        "de API» normal (empieza por «AIza» y tiene 39 caracteres), creada en "
        + _CONSOLA + " → «Crear credenciales» → «Clave de API», sin vincularla "
        "a una cuenta de servicio. Las de Google AI Studio (Gemini) no valen"),
    "accessNotConfigured": (
        "el proyecto de Google de esa clave no tiene activada «YouTube Data "
        "API v3»: actívala en console.cloud.google.com → «APIs y servicios» → "
        "«Habilitar APIs y servicios» (tarda un par de minutos en hacer efecto)"),
    "restriccionApi": (
        "la clave está limitada a otras APIs: en " + _CONSOLA + " → la clave → "
        "«Restricciones de API», añade «YouTube Data API v3» (o «No "
        "restringir clave»)"),
    "restriccionApp": (
        "la clave tiene una restricción de aplicaciones (sitios web, "
        "direcciones IP o apps) que deja fuera al robot: en " + _CONSOLA
        + " → la clave → «Restricciones de aplicaciones» → «Ninguna»"),
    "forbidden": (
        "esa clave no tiene permiso para YouTube: actívale «YouTube Data API "
        "v3» o crea una clave nueva (YOUTUBE_API_KEY)"),
}


def _pedir(recurso: str, **params) -> dict:
    """Una llamada a la API. Traduce los errores de Google a algo legible."""
    global _bloqueo, _bloqueo_clave, _hasta
    k, origen = _clave()
    url = API + recurso + "?" + urllib.parse.urlencode(dict(params, key=k))
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=ESPERA_RED_S) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        motivo, detalle = "", ""
        try:
            cuerpo = json.loads(e.read().decode("utf-8")).get("error", {})
            detalle = cuerpo.get("message", "")
            motivo = (cuerpo.get("errors") or [{}])[0].get("reason", "")
            if not motivo and cuerpo.get("status") == "PERMISSION_DENIED":
                motivo = "forbidden"
        except Exception:
            pass
        if "API key not valid" in detalle or "API key expired" in detalle:
            motivo = "keyInvalid"
        elif "not supported by this API" in detalle:
            motivo = "tipoDeClave"
        elif "has not been used" in detalle or "is disabled" in detalle:
            motivo = "accessNotConfigured"
        elif "Requests to this API" in detalle:
            motivo = "restriccionApi"
        elif "are blocked" in detalle or "restriction" in detalle:
            motivo = "restriccionApp"
        mensaje = _EXPLICADO.get(motivo) or f"YouTube contestó {e.code}: {detalle or motivo or '?'}"
        if origen == "GOOGLE_API_KEY" and motivo not in _CUOTA and e.code in (400, 401, 403):
            mensaje = ("no encontré YOUTUBE_API_KEY en backend/.env; probé con la "
                       "clave de Gemini (GOOGLE_API_KEY) y YouTube no la acepta. "
                       "Añade la línea YOUTUBE_API_KEY=<la clave de YouTube>")
        if motivo in _CUOTA:
            _bloqueo, _bloqueo_clave, _hasta = mensaje, k, time.time() + CUOTA_S
        elif e.code in (400, 401, 403):
            _bloqueo, _bloqueo_clave, _hasta = mensaje, k, time.time() + REINTENTO_S
        raise ErrorYouTube(motivo or str(e.code), mensaje)
    except ValueError:
        # Contestó algo que no es de YouTube: típico del wifi que pide entrar
        # por una página antes de dejar navegar.
        raise ErrorYouTube("respuestaRara", (
            "en vez de YouTube contestó otra cosa: ¿el wifi pide iniciar "
            "sesión en una página antes de dejar navegar?"))
    except OSError as e:
        raise ErrorYouTube("sinRed", (
            f"no llego a YouTube ({getattr(e, 'reason', e)}): revisa el "
            "internet de la Pi (hay redes de colegio que bloquean YouTube)"))


def comprobar() -> str:
    """Le pregunta a YouTube si la clave sirve. "" = sirve; si no, el motivo.

    Gasta 1 unidad de las 10 000 del día. Se usa al arrancar: sin esto, una
    clave mala no se notaba hasta la primera canción, con MECH ya habiendo
    preguntado cuál y de quién.
    """
    if not clave():
        return por_que_no()
    try:
        _pedir("videos", part="id", id="jNQXAC9IVRw")
    except ErrorYouTube as e:
        return str(e)
    return ""


_DURACION = re.compile(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$")


def segundos(iso: str) -> int:
    """«PT3M49S» -> 229. 0 si no se entiende (un directo: «P0D»)."""
    m = _DURACION.match(iso or "")
    if not m:
        return 0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return ((d * 24 + h) * 60 + mi) * 60 + s


def _puntos(titulo_video: str, canal: str, titulo: str, artista: str) -> int:
    tv, ca = _plano(titulo_video), _plano(canal)
    pt, pa = _plano(titulo), _plano(artista)
    puntos = 0
    if pt and pt in tv:
        puntos += 4
    if pa and (pa in tv or pa in ca):
        puntos += 3
    # Canales oficiales: «LuisFonsiVEVO», «Queen Official», «Malpaís - Topic».
    if ca.endswith("vevo") or ca.endswith("topic") or "official" in ca or "oficial" in ca:
        puntos += 2
    if "official" in tv or "oficial" in tv:
        puntos += 1
    pedido = pt + " " + pa
    for palabra in _DISTINTO:
        if re.search(r"\b" + re.escape(palabra) + r"\b", tv) and palabra not in pedido:
            puntos -= 4
            break
    return puntos


def buscar(titulo: str, artista: str = "") -> list[dict]:
    """Videos de YouTube para esa canción, el mejor primero. [] si no hay.

    Cada uno: `{id, title, channel, seconds, thumb}`. Lanza `ErrorYouTube` si
    la clave no sirve o se acabó la cuota, y una excepción de red si no hay
    internet: quien llama se lo dice al visitante.
    """
    titulo, artista = (titulo or "").strip(), (artista or "").strip()
    if not (titulo or artista):
        return []
    llave = (_plano(titulo), _plano(artista), config.MUSIC_COUNTRY,
             bool(config.MUSIC_ALLOW_EXPLICIT))
    guardado = _cache.get(llave)
    if guardado and time.time() - guardado[0] < CACHE_S:
        return [dict(v) for v in guardado[1]]

    comun = {
        "part": "snippet", "type": "video", "maxResults": 10,
        "q": f"{titulo} {artista}".strip(),
        "videoEmbeddable": "true",      # que deje reproducirse fuera de youtube.com
        "videoSyndicated": "true",
        "regionCode": config.MUSIC_COUNTRY,
        "safeSearch": "none" if config.MUSIC_ALLOW_EXPLICIT else "strict",
    }
    # Primero solo la categoría Música (10); si no sale nada, sin categoría.
    encontrados = _pedir("search", videoCategoryId="10", **comun).get("items") or []
    if not encontrados:
        encontrados = _pedir("search", **comun).get("items") or []
    fichas = {}
    for it in encontrados:
        vid = (it.get("id") or {}).get("videoId")
        sn = it.get("snippet") or {}
        if not vid or sn.get("liveBroadcastContent") not in (None, "none"):
            continue        # los directos no terminan nunca
        minis = sn.get("thumbnails") or {}
        mini = (minis.get("high") or minis.get("medium") or minis.get("default") or {}).get("url", "")
        fichas[vid] = {
            "id": vid,
            "title": html.unescape(sn.get("title") or ""),
            "channel": html.unescape(sn.get("channelTitle") or ""),
            "thumb": mini,
            "seconds": 0,
        }
    if not fichas:
        _cache[llave] = (time.time(), [])
        return []

    # La duración y los permisos no vienen en la búsqueda: otra llamada (1 unidad).
    detalles = _pedir("videos", part="contentDetails,status", id=",".join(fichas)).get("items") or []
    validos = []
    orden = list(fichas)
    for d in detalles:
        ficha = fichas.get(d.get("id"))
        if not ficha:
            continue
        contenido, estado = d.get("contentDetails") or {}, d.get("status") or {}
        ficha["seconds"] = segundos(contenido.get("duration", ""))
        bloqueados = (contenido.get("regionRestriction") or {}).get("blocked") or []
        permitidos = (contenido.get("regionRestriction") or {}).get("allowed")
        if estado.get("embeddable") is False:
            continue
        if (contenido.get("contentRating") or {}).get("ytRating") == "ytAgeRestricted":
            continue        # los de mayores de edad no se reproducen incrustados
        if config.MUSIC_COUNTRY in bloqueados or (permitidos is not None and config.MUSIC_COUNTRY not in permitidos):
            continue
        # Duración de canción: ni un corto de 20 s ni «10 horas de…».
        if not (45 <= ficha["seconds"] <= config.MUSIC_MAX_SECONDS):
            continue
        validos.append(ficha)
    # `sorted` es estable: a igualdad manda el orden de YouTube (relevancia).
    validos.sort(key=lambda v: (-_puntos(v["title"], v["channel"], titulo, artista),
                                orden.index(v["id"])))
    validos = validos[:CANDIDATOS]
    _cache[llave] = (time.time(), validos)
    return [dict(v) for v in validos]
