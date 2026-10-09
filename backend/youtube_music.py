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
(`YOUTUBE_API_KEY` en el `.env`; si no está, se prueba con `GOOGLE_API_KEY`,
la de Gemini, que sirve solo si ese proyecto de Google tiene activada la API
de YouTube). Cada canción gasta 101 unidades de las 10 000 diarias: unas 99
canciones al día. Lo ya buscado se recuerda unas horas para no gastar de más.

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
# se deja de intentar hasta reiniciar. Con la cuota agotada, hasta `_hasta`.
_bloqueo: str = ""
_hasta: float = 0.0


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


def clave() -> str:
    return (config.YOUTUBE_API_KEY or config.GOOGLE_API_KEY or "").strip()


def disponible() -> bool:
    """¿Se puede buscar en YouTube ahora mismo?"""
    if not clave():
        return False
    if _bloqueo and (not _hasta or time.time() < _hasta):
        return False
    return True


def por_que_no() -> str:
    """Por qué no se puede usar YouTube (para decirlo en el panel)."""
    if not clave():
        return "falta YOUTUBE_API_KEY en backend/.env"
    return _bloqueo


_EXPLICADO = {
    "quotaExceeded": "se acabaron las búsquedas de hoy en YouTube (vuelven mañana)",
    "dailyLimitExceeded": "se acabaron las búsquedas de hoy en YouTube (vuelven mañana)",
    "keyInvalid": "la clave de YouTube no es válida: revisa YOUTUBE_API_KEY en backend/.env",
    "badRequest": "la clave de YouTube no es válida: revisa YOUTUBE_API_KEY en backend/.env",
    "accessNotConfigured": (
        "el proyecto de Google de esa clave no tiene activada «YouTube Data "
        "API v3»: actívala en console.cloud.google.com"),
    "forbidden": (
        "esa clave no tiene permiso para YouTube: actívale «YouTube Data API "
        "v3» o crea una clave nueva (YOUTUBE_API_KEY)"),
}


def _pedir(recurso: str, **params) -> dict:
    """Una llamada a la API. Traduce los errores de Google a algo legible."""
    global _bloqueo, _hasta
    url = API + recurso + "?" + urllib.parse.urlencode(dict(params, key=clave()))
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
        if "API key not valid" in detalle:
            motivo = "keyInvalid"
        elif "has not been used" in detalle or "is disabled" in detalle:
            motivo = "accessNotConfigured"
        elif "are blocked" in detalle:
            motivo = "forbidden"
        mensaje = _EXPLICADO.get(motivo) or f"YouTube contestó {e.code}: {detalle or motivo or '?'}"
        if motivo in ("quotaExceeded", "dailyLimitExceeded"):
            _bloqueo, _hasta = mensaje, time.time() + 3600   # se reintenta en una hora
        elif e.code in (400, 401, 403):
            _bloqueo, _hasta = mensaje, 0.0                   # hasta reiniciar
        raise ErrorYouTube(motivo or str(e.code), mensaje)


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
