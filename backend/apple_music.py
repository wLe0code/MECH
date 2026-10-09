"""Buscar canciones en el catálogo de Apple Music (para el modo música).

Usa el buscador PÚBLICO de Apple (iTunes Search API): no pide cuenta, clave
ni pago. De cada canción devuelve el título, el artista, la carátula y un
**fragmento oficial de 30 segundos** (`previewUrl`), que es lo que suena hoy.

Lo que este buscador NO da es la canción entera. Eso es otra cosa (MusicKit):
pide la cuenta de DESARROLLADOR de Apple —de pago, aparte de la suscripción a
Apple Music—, que alguien inicie sesión en la pantalla y que el navegador
pueda abrir audio protegido. Cuando eso exista, el `id` que se devuelve aquí
es el mismo que usa MusicKit: no hay que cambiar la búsqueda.

Solo librería estándar, como `sismos.py`.
"""

from __future__ import annotations

import json
import re
import unicodedata
import urllib.parse
import urllib.request

import config

BUSCADOR = "https://itunes.apple.com/search"
ESPERA_RED_S = 10


def _plano(texto: str) -> str:
    """Minúsculas, sin acentos ni signos: para comparar nombres."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    return re.sub(r"[^\w]+", " ", texto, flags=re.UNICODE).strip()


def _descargar(params: dict) -> list[dict]:
    url = BUSCADOR + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": "MECH-robot/1.0 (proyecto educativo WRO)",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=ESPERA_RED_S) as r:
        datos = json.loads(r.read().decode("utf-8"))
    return datos.get("results") or []


def _cancion(r: dict) -> dict | None:
    """Una ficha de Apple -> lo que usa MECH. None si no se puede reproducir."""
    if not r.get("previewUrl") or not r.get("trackName"):
        return None
    caratula = r.get("artworkUrl100") or ""
    return {
        "id": str(r.get("trackId") or ""),
        "title": r.get("trackName") or "",
        "artist": r.get("artistName") or "",
        "album": r.get("collectionName") or "",
        "seconds": round((r.get("trackTimeMillis") or 0) / 1000),
        # La carátula viene en 100x100: se pide grande para proyectarla.
        "artwork": caratula.replace("100x100bb", "600x600bb"),
        "preview": r["previewUrl"],
        "url": r.get("trackViewUrl") or "",
        "explicit": r.get("trackExplicitness") == "explicit",
    }


def _puntos(c: dict, titulo: str, artista: str) -> int:
    """Cuánto se parece una canción a lo pedido (más = mejor)."""
    t, a = _plano(c["title"]), _plano(c["artist"])
    pt, pa = _plano(titulo), _plano(artista)
    puntos = 0
    if pa:
        if pa == a:
            puntos += 5
        elif pa in a or a in pa:
            puntos += 4          # «Luis Fonsi» dentro de «Luis Fonsi & Daddy Yankee»
        elif set(pa.split()) & set(a.split()):
            puntos += 2
    if pt:
        if pt == t:
            puntos += 5
        elif t.startswith(pt):
            puntos += 3          # «Despacito» antes que «Despacito (Remix)»
        elif pt in t:
            puntos += 2
    # A igualdad, la versión normal antes que remezclas, directos y karaokes.
    if re.search(r"\b(remix|live|en vivo|karaoke|instrumental|cover|tribute)\b", t):
        puntos -= 2
    return puntos


def buscar(titulo: str, artista: str = "", limite: int = 8) -> list[dict]:
    """Canciones que encajan con el pedido, la mejor primero. [] si no hay.

    Si el artista se entendió mal y con él no sale nada, se prueba solo con
    el título: la gente recuerda mejor la canción que quién la canta.

    Puede lanzar una excepción de red (sin internet, Apple caído): quien
    llama decide qué decirle al visitante.
    """
    titulo, artista = (titulo or "").strip(), (artista or "").strip()
    if not titulo and not artista:
        return []
    params = {
        "media": "music", "entity": "song", "limit": limite,
        "country": config.MUSIC_COUNTRY,
    }
    if not config.MUSIC_ALLOW_EXPLICIT:
        params["explicit"] = "No"
    intentos = [f"{titulo} {artista}".strip()]
    if titulo and artista:
        intentos.append(titulo)
    for termino in intentos:
        crudos = _descargar(dict(params, term=termino))
        canciones = [c for c in map(_cancion, crudos) if c]
        if not config.MUSIC_ALLOW_EXPLICIT:
            canciones = [c for c in canciones if not c["explicit"]]
        if canciones:
            # `sorted` es estable: a igualdad de puntos manda el orden de
            # Apple, que ya viene por relevancia.
            return sorted(canciones, key=lambda c: -_puntos(c, titulo, artista))
    return []
