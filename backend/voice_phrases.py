"""Detección de las frases para despertar / dormir a MECH.

Centralizado aquí para que lo usen tanto el bucle de voz (server.py) como
el listener de interrupción durante la narración (mech_app.py).

El match es por palabras en cualquier orden: una frase coincide si TODAS sus
palabras aparecen en el texto (cada una como parte de algún token). Así
"duermete mech", "mech duermete" y "duermete" funcionan igual, y tolera mejor
lo que transcribe Whisper.
"""

from __future__ import annotations

import re
import unicodedata

import config


def normalize(text: str) -> str:
    """Minúsculas, sin acentos ni signos."""
    t = unicodedata.normalize("NFD", text.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = "".join(c if (c.isalnum() or c.isspace()) else " " for c in t)
    return " ".join(t.split())


def _lev_leq1(a: str, b: str) -> bool:
    """True si la distancia de edición entre a y b es 0 o 1.

    Whisper a veces transcribe "mech" como "mec", "mek" o "meche"; con una
    edición de tolerancia el wake word sigue funcionando sin abrir la puerta
    a falsos positivos graves.
    """
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la > lb:
        a, b, la, lb = b, a, lb, la
    # la <= lb, diferencia 0 o 1.
    i = j = 0
    edited = False
    while i < la and j < lb:
        if a[i] == b[j]:
            i += 1
            j += 1
            continue
        if edited:
            return False
        edited = True
        if la == lb:
            i += 1  # sustitución
        j += 1  # inserción en b (o sustitución)
    return True


def _word_matches(w: str, tok: str) -> bool:
    """Una palabra del wake phrase coincide con un token de la transcripción
    si es substring (comportamiento original) o, para palabras de 4+ letras,
    si están a una edición de distancia (tolerancia a errores de Whisper)."""
    if w in tok:
        return True
    return len(w) >= 4 and _lev_leq1(w, tok)


def matches_any(text: str, phrases: list[str]) -> bool:
    norm_text = normalize(text)
    tokens = norm_text.split()
    if not tokens:
        return False
    for p in phrases:
        words = normalize(p).split()
        if words and all(any(_word_matches(w, tok) for tok in tokens) for w in words):
            return True
    return False


def _interrupt_phrases() -> list[str]:
    """Frases de interrupción de los DOS idiomas.

    Se aceptan ambas siempre: si MECH narra en español y alguien le suelta
    "hey MECH", igual queremos parar. Son frases distintivas, no chocan.
    """
    return list(config.VOICE_INTERRUPT_PHRASES) + list(config.VOICE_INTERRUPT_PHRASES_EN)


def is_interrupt(text: str) -> bool:
    """¿El visitante está pidiendo cortar la narración? ("oye MECH")."""
    return matches_any(text, _interrupt_phrases())


def strip_interrupt(text: str) -> str:
    """Devuelve lo que queda tras quitar la frase de interrupción.

    Sirve para que "oye MECH, cuéntame otra cosa" no obligue a repetir: se
    corta la narración Y se atiende "cuéntame otra cosa" enseguida. Si solo
    se dijo la frase ("oye MECH"), devuelve cadena vacía.
    """
    tokens = list(re.finditer(r"\S+", text or ""))
    if not tokens:
        return ""
    norm = [normalize(t.group(0)) for t in tokens]
    for phrase in _interrupt_phrases():
        usados: list[int] = []
        for w in normalize(phrase).split():
            hit = next(
                (i for i, tok in enumerate(norm)
                 if i not in usados and _word_matches(w, tok)),
                None,
            )
            if hit is None:
                usados = []
                break
            usados.append(hit)
        if usados:
            resto = text[tokens[max(usados)].end():]
            return resto.strip(" \t,.;:¿?¡!-–—\"'")
    return ""


# --- Órdenes de movimiento (no pasan por Claude) --------------------------
# "mira hacia afuera" / "regresa a proyectar". Se aceptan las listas de los
# DOS idiomas siempre: son frases largas y distintivas, no chocan con nada, y
# si Whisper transcribió en el idioma equivocado igual queremos obedecer.


# Números escritos con letra, para "avanza DIEZ segundos". Whisper los
# transcribe casi siempre en letra, no en dígito.
_NUMEROS = {
    "medio": 0.5, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3,
    "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
    "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14,
    "quince": 15, "dieciseis": 16, "diecisiete": 17, "dieciocho": 18,
    "diecinueve": 19, "veinte": 20, "veinticinco": 25, "treinta": 30,
    # Los grandes también, aunque el tope de seguridad los recorte: es mejor
    # entenderlos y toparlos que ignorarlos y hacer otra cosa distinta.
    "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "cien": 100,
    # inglés, por si le hablan en modo EN
    "half": 0.5, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30,
}


def extract_seconds(text: str) -> float | None:
    """Los segundos que pide una orden, o None si no dice ninguno.

    Acepta dígitos ("avanza 10 segundos") y letra ("avanza diez segundos"),
    que es como lo transcribe Whisper casi siempre. Si no hay número, quien
    llame decide el valor por defecto.
    """
    tokens = normalize(text).split()
    for i, tok in enumerate(tokens):
        valor = None
        if tok.isdigit():
            valor = float(tok)
        elif tok in _NUMEROS:
            valor = float(_NUMEROS[tok])
        if valor is None:
            continue
        # "diez segundos" sí; "diez" suelto también (si dijeron un número en
        # una orden de movimiento, es el tiempo: no hay otra cosa que contar).
        siguiente = tokens[i + 1] if i + 1 < len(tokens) else ""
        if not siguiente or siguiente.startswith("segundo") or siguiente.startswith("second"):
            return valor
        return valor
    return None


def is_advance(text: str) -> bool:
    """¿Piden avanzar? ("avanza diez segundos")"""
    return matches_any(
        text,
        list(config.VOICE_ADVANCE_PHRASES) + list(config.VOICE_ADVANCE_PHRASES_EN),
    )


def is_retreat(text: str) -> bool:
    """¿Piden retroceder? ("retrocede cinco segundos")"""
    return matches_any(
        text,
        list(config.VOICE_RETREAT_PHRASES) + list(config.VOICE_RETREAT_PHRASES_EN),
    )


def is_look_outward(text: str) -> bool:
    """¿Le están pidiendo que gire 180° y salude hacia afuera?"""
    return matches_any(
        text,
        list(config.VOICE_OUTWARD_PHRASES) + list(config.VOICE_OUTWARD_PHRASES_EN),
    )


def is_back_to_projection(text: str) -> bool:
    """¿Le están pidiendo que vuelva a su posición de proyección?"""
    return matches_any(
        text,
        list(config.VOICE_PROJECT_PHRASES) + list(config.VOICE_PROJECT_PHRASES_EN),
    )


def is_play_marketing(text: str) -> bool:
    """¿Piden proyectar el slot de marketing? ("proyecta marketing")

    Se aceptan las listas de los dos idiomas: "marketing" es la misma palabra
    en español y en inglés, así que no hay ambigüedad posible.
    """
    return matches_any(
        text,
        list(config.VOICE_MARKETING_PHRASES) + list(config.VOICE_MARKETING_PHRASES_EN),
    )


def is_sleep(text: str) -> bool:
    """Frase de reposo en español."""
    return matches_any(text, config.VOICE_SLEEP_PHRASES)


def is_wake(text: str) -> bool:
    """Frase de despertar en español ("ok MECH", "despierta MECH")."""
    return matches_any(text, config.VOICE_WAKE_PHRASES)


def is_sleep_en(text: str) -> bool:
    """Frase de reposo en inglés ("stop listening", "go to sleep")."""
    return matches_any(text, config.VOICE_SLEEP_PHRASES_EN)


def is_wake_en(text: str) -> bool:
    """Frase de despertar en INGLÉS ("wake up MECH").

    Es la única puerta al modo inglés: si no se dice esto, MECH sigue en
    español (y no entendería comandos en inglés).
    """
    return matches_any(text, config.VOICE_WAKE_PHRASES_EN)


def wake_language(text: str) -> str | None:
    """Idioma con el que se despertó a MECH, o None si no fue un despertar.

    El inglés se comprueba PRIMERO: "wake up mech" no colisiona con ninguna
    frase española de la lista, pero así queda explícito que el modo inglés
    manda cuando se pide de forma literal.
    """
    if config.WAKE_ENGLISH_ENABLED and is_wake_en(text):
        return "en"
    if is_wake(text):
        return "es"
    return None


def is_sleep_any(text: str) -> bool:
    """Frase de reposo en cualquiera de los dos idiomas.

    Dormirse es inofensivo, así que se aceptan ambas listas sin importar el
    idioma activo (si Whisper transcribió raro, igual obedece).
    """
    return is_sleep(text) or is_sleep_en(text)
