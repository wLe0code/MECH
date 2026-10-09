"""Modo MÚSICA — MECH pone la canción que le pidan.

Idea (pedido del equipo, oct 2026): «como en Alexa». Se le dice **«modo
música MECH»** o **«activa modo música»**; pregunta qué canción y de qué
artista (el artista es lo que garantiza que sea la correcta), busca su video
en YouTube, lo pone, y al terminar pregunta si quiere otra o hacer otra cosa.

    Usuario:  «ok MECH»                -> despierta
    Usuario:  «activa modo música»
    MECH:     «¿Qué canción quieres escuchar, y de qué artista?»   (+ chime)
    Usuario:  «Despacito»
    MECH:     «¿De qué artista es?»                                (+ chime)
    Usuario:  «de Luis Fonsi»
    MECH:     «Ahí va: Despacito, de Luis Fonsi y Daddy Yankee.»
              ... suena la canción (la carátula, en la proyección) ...
    MECH:     «¿Seguimos con la música, o prefieres hacer algo distinto?»
    Usuario:  «otra canción»  -> vuelve a preguntar cuál
    Usuario:  «no»            -> «Listo, apago la música.» y sale del modo
    Usuario:  cualquier otra orden -> sale del modo y la atiende

Mientras suena se puede cortar con **«oye MECH»** (en el idioma en que
despertó), igual que una narración: para la música y vuelve a preguntar.

**Qué suena.** La canción entera, con su video, desde YouTube (ver
`youtube_music.py`). Necesita la clave `YOUTUBE_API_KEY`; sin ella MECH dice
que no puede poner música y no entra al modo.

**Dónde suena.** En la PANTALLA de proyección (`frontend/music.js`), no en
este proceso: ahí vive el reproductor oficial de YouTube, y es el mismo
camino que los videos de marketing. La pantalla avisa cuando empieza y
cuando termina.

**El eco.** MECH habla y enseguida abre el micrófono, cuatro veces por
canción. Tres defensas, las mismas del traductor y la trivia: la espera de
`MUSIC_DRAIN_SECONDS`, la guarda de `spoken()` (descarta lo que se parezca a
lo último que dijo), y que las preguntas están escritas para no contener
ninguna orden (ver `lang.py`, `music_*`).

Este módulo guarda SOLO el estado, como `translator.py` y `trivia.py`. Quien
habla, busca y manda la canción a la pantalla es `mech_app`.
"""

from __future__ import annotations

from collections import deque

# En qué punto está:
#   "off"     = fuera del modo
#   "ask"     = preguntó qué canción (y de quién) y espera la respuesta
#   "artist"  = ya sabe la canción; preguntó de qué artista es
#   "playing" = está sonando una canción
#   "again"   = terminó; preguntó si seguimos con la música o no
_stage: str = "off"
# Título que ya dijo el visitante, mientras se le pregunta el artista.
_pending_title: str = ""
# La canción que suena (o la última que sonó):
#   {title, artist, seconds, youtube: [{id, title, channel, seconds, thumb}]}
_track: dict | None = None
# Veces seguidas que no se entendió el pedido. A la segunda se deja de
# insistir (ver `mech_app.handle_music_request`).
_misses: int = 0
# Lo último que dijo MECH dentro del modo, para descartar su propio eco.
_spoken: deque = deque(maxlen=3)


def stage() -> str:
    return _stage


def is_active() -> bool:
    """¿Está dentro del modo música (preguntando o sonando)?"""
    return _stage != "off"


def is_asking() -> bool:
    """¿Espera que le digan una canción o un artista?"""
    return _stage in ("ask", "artist")


def is_awaiting_artist() -> bool:
    return _stage == "artist"


def is_offering_more() -> bool:
    """¿Acaba de preguntar si seguimos con la música?"""
    return _stage == "again"


def is_playing() -> bool:
    return _stage == "playing"


def ask() -> None:
    """Entra al modo (o vuelve a él) esperando un pedido nuevo."""
    global _stage, _pending_title, _misses
    _stage = "ask"
    _pending_title = ""
    _misses = 0


def ask_artist(title: str) -> None:
    """Ya se sabe la canción; falta de quién es."""
    global _stage, _pending_title
    _stage = "artist"
    _pending_title = title or ""


def pending_title() -> str:
    return _pending_title


def miss() -> int:
    """Apunta un pedido que no se entendió. Devuelve cuántos van seguidos."""
    global _misses
    _misses += 1
    return _misses


def play(track: dict) -> None:
    global _stage, _track, _pending_title, _misses
    _stage = "playing"
    _track = dict(track)
    _pending_title = ""
    _misses = 0


def offer_more() -> None:
    """La canción terminó (o no se encontró): toca preguntar si seguimos."""
    global _stage, _pending_title
    _stage = "again"
    _pending_title = ""


def track() -> dict | None:
    return _track


def reset() -> None:
    """Sale del modo del todo."""
    global _stage, _pending_title, _track, _misses
    _stage = "off"
    _pending_title = ""
    _track = None
    _misses = 0
    _spoken.clear()


def remember_spoken(text: str) -> None:
    if text:
        _spoken.append(text)


def spoken() -> tuple:
    return tuple(_spoken)


def snapshot() -> dict:
    """Lo que ven el panel y la pantalla en `state["music"]`."""
    return {
        "stage": _stage,
        "active": _stage != "off",
        "pending_title": _pending_title,
        "track": dict(_track) if (_track and _stage == "playing") else None,
        "last": dict(_track) if _track else None,
    }
