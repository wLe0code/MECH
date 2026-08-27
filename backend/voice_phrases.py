"""Detección de las frases para despertar / dormir a MECH.

Centralizado aquí para que lo usen tanto el bucle de voz (server.py) como
el listener de interrupción durante la narración (mech_app.py).

El match es por palabras en cualquier orden: una frase coincide si TODAS sus
palabras aparecen en el texto (cada una como parte de algún token). Así
"duermete mech", "mech duermete" y "duermete" funcionan igual, y tolera mejor
lo que transcribe Whisper.
"""

from __future__ import annotations

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
