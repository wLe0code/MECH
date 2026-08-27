"""Idioma activo de MECH — español (default) o inglés (opcional).

Regla del equipo (ago 2026):

- MECH SIEMPRE arranca en **español**.
- El **inglés se activa si y solo si** alguien lo despierta en inglés:
  «wake up MECH». A partir de ahí TODO va en inglés (lo que MECH entiende,
  lo que narra y los subtítulos).
- Con «ok MECH» / «despierta MECH» sigue en español, como siempre.
- Al dormirse (frase de reposo o botón), vuelve solo a español: así el
  siguiente visitante del stand encuentra a MECH en español.

Este módulo es a propósito muy simple (una variable + tablas de texto) para
que lo puedan importar `stt`, `llm`, `mech_app` y `server` sin ciclos.
"""

from __future__ import annotations

import config

DEFAULT = "es"
SUPPORTED = ("es", "en")

_current: str = DEFAULT


def current() -> str:
    """Código del idioma activo: 'es' o 'en'."""
    return _current


def is_english() -> bool:
    return _current == "en"


def set_current(code: str | None) -> str:
    """Cambia el idioma activo. Devuelve el idioma que quedó vigente.

    Un código desconocido no rompe nada: se ignora y se mantiene el actual.
    """
    global _current
    if code:
        code = code.strip().lower()[:2]
        if code in SUPPORTED:
            _current = code
    return _current


def reset() -> str:
    """Vuelve al idioma por defecto (español)."""
    return set_current(DEFAULT)


def label(code: str | None = None) -> str:
    """Nombre legible del idioma, para logs y para el panel."""
    return {"es": "español", "en": "inglés"}.get(code or _current, code or _current)


# ---------------------------------------------------------------------------
# Frases fijas que MECH dice fuera del plan de Claude
# ---------------------------------------------------------------------------
# OJO: la frase de reposo NO puede contener ninguna palabra de despertar
# ("despierta", "wake"...): el micrófono sigue abierto en reposo y captaría
# el eco del parlante, despertándose solo.
_PHRASES: dict[str, dict[str, str]] = {
    "awake": {
        "es": "Hola, ya te escucho.",
        "en": "Hi, I'm listening.",
    },
    "dormant": {
        "es": "De acuerdo, hasta luego.",
        "en": "All right, see you later.",
    },
    "greeting": {
        "es": "¡Hola! Soy MECH. Un gusto verte hoy aquí.",
        "en": "Hello! I am MECH. It's a pleasure to see you here today.",
    },
    "error": {
        "es": "Disculpa, tuve un problema. ¿Puedes repetirme?",
        "en": "Sorry, I ran into a problem. Could you say that again?",
    },
    "switched": {
        "es": "Listo, sigo en español.",
        "en": "All right, I'll continue in English.",
    },
}


def say(key: str, code: str | None = None) -> str:
    """Texto de una frase fija en el idioma activo (o en el que se pida)."""
    entry = _PHRASES.get(key, {})
    return entry.get(code or _current) or entry.get(DEFAULT, "")


# ---------------------------------------------------------------------------
# Integración con Whisper y con Claude
# ---------------------------------------------------------------------------


def whisper_language() -> str:
    """Idioma que se le pasa a faster-whisper para transcribir.

    En español respeta `config.WHISPER_LANGUAGE` (el panel lo puede cambiar
    en vivo); en modo inglés fuerza "en", porque si Whisper transcribe con
    el idioma equivocado devuelve basura y MECH no entiende nada.
    """
    if _current == "en":
        return "en"
    return config.WHISPER_LANGUAGE


def llm_directive(code: str | None = None) -> str:
    """Bloque que se añade al system prompt de Claude con el idioma activo.

    Va en un bloque de system APARTE (sin cache_control) para no invalidar
    el caché del prompt grande cada vez que se cambia de idioma.
    """
    if (code or _current) == "en":
        return (
            "# IDIOMA ACTIVO: INGLÉS\n\n"
            "El visitante está hablando en INGLÉS y te despertó con "
            "'wake up MECH'. Reglas para ESTA respuesta:\n"
            "- Escribe TODAS las `narration` en inglés natural y fluido "
            "(no traduzcas literalmente del español).\n"
            "- Mantén los nombres propios y los títulos originales "
            "(Don Quijote, Campaña Nacional de 1856, Malpaís, Jiménez "
            "Deredia, Isidro Con Wong) y, si hace falta, explícalos en "
            "inglés entre paréntesis la primera vez.\n"
            "- El campo `image_prompt` sigue en inglés, como siempre.\n"
            "- El resto de las reglas (modos, gestos, biblioteca de videos, "
            "información nuestra) no cambian.\n"
            "- Los datos verificados y la 'Información nuestra' están en "
            "español: tradúcelos al inglés, pero NO inventes datos nuevos."
        )
    return (
        "# IDIOMA ACTIVO: ESPAÑOL\n\n"
        "Escribe todas las `narration` en español neutro, como indica el "
        "resto del prompt."
    )
