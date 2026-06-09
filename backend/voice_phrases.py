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


def matches_any(text: str, phrases: list[str]) -> bool:
    norm_text = normalize(text)
    tokens = norm_text.split()
    if not tokens:
        return False
    for p in phrases:
        words = normalize(p).split()
        if words and all(any(w in tok for tok in tokens) for w in words):
            return True
    return False


def is_sleep(text: str) -> bool:
    return matches_any(text, config.VOICE_SLEEP_PHRASES)


def is_wake(text: str) -> bool:
    return matches_any(text, config.VOICE_WAKE_PHRASES)
