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

# Caracteres por línea. ~90 son unas 2 líneas en el proyector; la vista VR
# usa menos porque cada ojo es media pantalla.
MAX_CHARS = 90
# Una "frase" = texto hasta un signo que cierra una idea (incluido el signo).
_FRASE_RE = re.compile(r"\S[^.!?…:;]*[.!?…:;]*")


def _partir_frase(offset: int, frase: str, max_chars: int) -> list[tuple[int, str]]:
    """Parte UNA frase demasiado larga en trozos parejos, por palabras.

    Parejos a propósito: cortar a lo bruto en `max_chars` deja colas de dos
    palabras, que en pantalla se ven como un parpadeo.
    """
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
        if len(frase) > max_chars:
            cerrar()
            lineas.extend(_partir_frase(m.start(), frase, max_chars))
            continue
        if inicio is not None and (m.end() - inicio) > max_chars:
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
