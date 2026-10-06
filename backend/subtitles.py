"""Subtítulos: partir el guion en líneas y decir CUÁNDO va cada una.

Por qué vive en el backend y no en el navegador: la pantalla no sabe cuándo
empieza a sonar la voz ni dónde hace pausas MECH. El backend sí — tiene el
audio de ElevenLabs en la mano antes de reproducirlo, y (cuando la API lo
permite) hasta el instante exacto de cada carácter. Así los subtítulos se
quedan quietos mientras MECH respira, en vez de adelantarse.

Cada "cue" es `(segundo_desde_que_empieza_el_audio, texto_de_la_línea)`.
"""

from __future__ import annotations

import re
import unicodedata

# Caracteres por línea. ~90 son unas 2 líneas en el proyector; la vista VR
# usa menos porque cada ojo es media pantalla.
# Se mide en ANCHO, no en letras: un carácter chino o japonés ocupa el doble
# que una letra latina, así que de esos caben la mitad (ver `_ancho`).
MAX_CHARS = 90
# Una "frase" = texto hasta un signo que cierra una idea (incluido el signo).
# Los cinco últimos son los puntos y signos del chino y el japonés.
_FRASE_RE = re.compile(r"\S[^.!?…:;。！？；：]*[.!?…:;。！？；：]*")

# Signos que no pueden ABRIR una línea (se quedan pegados a lo anterior) ni
# CERRARLA (se van con lo siguiente). Solo cuentan al partir chino y japonés,
# que no tienen espacios: sin esto una línea empezaría por «。» o por «っ».
_NO_ABRE = "、。，．！？：；）」』】〉》〕…ー・々ぁぃぅぇぉっゃゅょァィゥェォッャュョ"
_NO_CIERRA = "（「『【〈《〔"
# Las comas del chino y el japonés: el mejor sitio para cortar una línea.
_PAUSA = "、，；："


def _es_ancho(c: str) -> bool:
    return unicodedata.east_asian_width(c) in ("W", "F")


def _se_corta(c: str) -> bool:
    """¿Se puede partir la línea justo en este carácter?

    En chino y japonés sí (no hay espacios). En coreano NO: sus letras
    también son anchas, pero las palabras van separadas por espacios y una
    palabra partida por la mitad no se lee.
    """
    return _es_ancho(c) and not (0xAC00 <= ord(c) <= 0xD7A3)


def _ancho(texto: str) -> int:
    """Cuánto ocupa en pantalla, en "letras latinas".

    Para un texto en letras latinas o cirílicas es su longitud de siempre.
    """
    if texto.isascii():
        return len(texto)
    return sum(2 if _es_ancho(c) else 1 for c in texto)


def _unidades(frase: str) -> list[tuple[int, int]]:
    """Trozos `(inicio, fin)` entre los que SÍ se puede cortar una línea.

    Una palabra en letras latinas (o en coreano) es un trozo; cada carácter
    chino o japonés es otro (ahí se puede cortar casi en cualquier sitio).
    """
    unidades: list[tuple[int, int]] = []
    i, n = 0, len(frase)
    while i < n:
        c = frase[i]
        if c.isspace():
            i += 1
            continue
        j = i + 1
        if c in _NO_CIERRA and j < n:
            j += 1
        elif not _se_corta(c):
            while j < n and not frase[j].isspace() and not _se_corta(frase[j]):
                j += 1
        while j < n and frase[j] in _NO_ABRE:
            j += 1
        unidades.append((i, j))
        i = j
    return unidades


def _partir_ancha(offset: int, frase: str, max_chars: int) -> list[tuple[int, str]]:
    """Como `_partir_frase`, para frases con letras anchas: chino y japonés
    (sin espacios) y coreano (con espacios, que es donde se corta)."""
    unidades = _unidades(frase)
    total = _ancho(frase)
    partes = max(1, -(-total // max_chars))  # ceil
    objetivo = -(-total // partes)
    trozos: list[tuple[int, str]] = []
    for ancho in range(objetivo, max_chars + 1, 4):
        trozos = []
        i = 0
        while i < len(unidades):
            inicio = unidades[i][0]
            j = i
            coma = None  # último sitio con coma donde se podría cortar
            while j < len(unidades) and _ancho(frase[inicio:unidades[j][1]]) <= ancho:
                if frase[unidades[j][1] - 1] in _PAUSA:
                    coma = j
                j += 1
            j = max(j, i + 1)  # un trozo más ancho que la línea va solo
            # Si la línea tiene que partirse, mejor en una coma que a media
            # palabra: se estira un poco si la coma está ahí mismo, o se
            # acorta hasta la anterior si no la deja demasiado corta.
            if j < len(unidades):
                tope = min(ancho + 8, max_chars)
                k = j
                while k < len(unidades) and _ancho(frase[inicio:unidades[k][1]]) <= tope:
                    if frase[unidades[k][1] - 1] in _PAUSA:
                        break
                    k += 1
                else:
                    k = None
                if k is not None and k < len(unidades):
                    j = k + 1
                elif (
                    coma is not None and coma + 1 < j
                    and _ancho(frase[inicio:unidades[coma][1]]) >= ancho * 0.45
                ):
                    j = coma + 1
            trozos.append((offset + inicio, frase[inicio:unidades[j - 1][1]]))
            i = j
        if len(trozos) <= partes:
            return trozos
    return trozos


def _partir_frase(offset: int, frase: str, max_chars: int) -> list[tuple[int, str]]:
    """Parte UNA frase demasiado larga en trozos parejos, por palabras.

    Parejos a propósito: cortar a lo bruto en `max_chars` deja colas de dos
    palabras, que en pantalla se ven como un parpadeo.
    """
    if _ancho(frase) != len(frase):
        return _partir_ancha(offset, frase, max_chars)
    partes = max(1, -(-len(frase) // max_chars))  # ceil
    objetivo = -(-len(frase) // partes)
    for ancho in range(objetivo, max_chars + 1, 4):
        trozos: list[tuple[int, str]] = []
        inicio = None
        fin = 0
        for m in re.finditer(r"\S+", frase):
            if inicio is not None and (fin - inicio) + 1 + len(m.group(0)) > ancho:
                trozos.append((offset + inicio, frase[inicio:fin]))
                inicio = None
            if inicio is None:
                inicio = m.start()
            fin = m.end()
        if inicio is not None:
            trozos.append((offset + inicio, frase[inicio:fin]))
        if len(trozos) <= partes:
            return trozos
    return trozos


def split(text: str, max_chars: int = MAX_CHARS) -> list[tuple[int, str]]:
    """Parte el guion en líneas de subtítulo, cortando por frases.

    Devuelve `(offset_en_caracteres, texto)` por línea. El offset es la
    posición REAL dentro de `text`: es lo que permite preguntarle a
    ElevenLabs en qué segundo empieza a pronunciarse esa línea.
    """
    lineas: list[tuple[int, str]] = []
    inicio: int | None = None
    fin = 0

    def cerrar() -> None:
        nonlocal inicio
        if inicio is not None:
            lineas.append((inicio, text[inicio:fin].strip()))
        inicio = None

    for m in _FRASE_RE.finditer(text or ""):
        frase = m.group(0).strip()
        if not frase:
            continue
        if _ancho(frase) > max_chars:
            cerrar()
            lineas.extend(_partir_frase(m.start(), frase, max_chars))
            continue
        if inicio is not None and _ancho(text[inicio:m.end()]) > max_chars:
            cerrar()
        if inicio is None:
            inicio = m.start()
        fin = m.end()
    cerrar()
    return lineas


def char_times(alignment, text: str) -> list[float] | None:
    """Convierte la alineación de ElevenLabs en "segundo de cada carácter".

    Es lo que permite que los subtítulos respeten las PAUSAS de MECH: sabemos
    exactamente cuándo empieza a pronunciarse cada letra del guion. Si la
    respuesta no cuadra con el texto devolvemos None, y `build_cues` reparte
    de forma proporcional (menos fino, pero nunca roto).
    """
    if alignment is None:
        return None

    def campo(nombre):
        if isinstance(alignment, dict):
            return alignment.get(nombre)
        return getattr(alignment, nombre, None)

    chars = campo("characters")
    starts = campo("character_start_times_seconds")
    if not chars or not starts or len(chars) != len(starts):
        return None
    if len(chars) != len(text) and "".join(chars) != text:
        return None
    try:
        return [float(t) for t in starts]
    except (TypeError, ValueError):
        return None


def build_cues(
    text: str,
    duration: float,
    char_times: list[float] | None = None,
    lead: float = 0.0,
    max_chars: int = MAX_CHARS,
) -> list[tuple[float, str]]:
    """Calcula en qué segundo debe aparecer cada línea de subtítulo.

    Args:
        text: el guion completo del segmento.
        duration: duración real del audio de la voz (sin el silencio inicial).
        char_times: segundo en que empieza cada carácter de `text`, si
            ElevenLabs nos lo dio. Con esto los subtítulos respetan las
            PAUSAS de MECH. Si es None, se reparte proporcionalmente al
            número de caracteres (aproximado, pero anclado a la duración
            real, así que no se va acumulando error).
        lead: silencio que se antepone al audio (config.AUDIO_LEAD_SILENCE);
            se suma a todos los tiempos.
    """
    lineas = split(text, max_chars)
    if not lineas:
        return []
    total = max(len(text), 1)
    cues: list[tuple[float, str]] = []
    for offset, linea in lineas:
        if char_times and offset < len(char_times):
            t = char_times[offset]
        else:
            t = duration * (offset / total)
        cues.append((max(0.0, lead + t), linea))
    # Nunca dejamos que una línea "adelante" a la anterior por un redondeo.
    for i in range(1, len(cues)):
        if cues[i][0] < cues[i - 1][0]:
            cues[i] = (cues[i - 1][0], cues[i][1])
    return cues
