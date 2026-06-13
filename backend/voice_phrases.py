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
    return matches_any(text, config.VOICE_SLEEP_PHRASES)


def is_wake(text: str) -> bool:
    return matches_any(text, config.VOICE_WAKE_PHRASES)
