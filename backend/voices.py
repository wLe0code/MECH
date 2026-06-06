"""Catálogo de voces dinámicas de ElevenLabs.

Dos tipos de voz:

1. **Voces por categoría demográfica** (hombre, mujer, niño, niña, adulto
   mayor). Sirven para CUALQUIER personaje sin voz propia: discursos
   históricos, simulaciones, diálogos inventados. Claude elige la categoría
   según quién habla (género y edad). Las dos de adulto (`male`, `female`)
   vienen pre-cargadas con voces *premade* de ElevenLabs (existen en toda
   cuenta, no hay que clonar nada).

2. **Voces de personaje específico** (Don Quijote, Julieta, Shrek...). Voz
   dedicada y reconocible. Opcional: hay que clonarla y pegar su `voice_id`.
   Si está vacía, se usa el fallback demográfico o el narrador.

Cómo conseguir un voice_id:
  1. Entra a https://elevenlabs.io/app/voice-library
  2. Busca/clona una voz que encaje y "Add to my voices".
  3. En https://elevenlabs.io/app/voice-lab copia su Voice ID (~20 chars).
  4. Pégalo abajo en el campo `voice_id` correspondiente.

Si una voz premade pre-cargada diera error (ElevenLabs a veces renombra su
biblioteca), reemplaza su `voice_id` por uno de tu cuenta. El sistema nunca
rompe: si una voz no existe, cae al fallback (ver `resolve`).

El system prompt de Claude se compone dinámicamente con las voces que SÍ
tienen voice_id (más el narrador), así Claude solo elige entre voces reales.
"""

from __future__ import annotations

from typing import TypedDict

import config


class VoiceMeta(TypedDict):
    voice_id: str
    description: str  # cuándo usar esta voz (lo lee Claude)


# IDs de voces "premade" de ElevenLabs (públicas, estables, en toda cuenta).
# Funcionan con el modelo multilingüe en español (la voz da el timbre; el
# modelo pone el idioma). Si alguna fallara, cámbiala por una de tu cuenta.
_PREMADE_MALE = "pNInz6obpgDQGcFmaJgB"    # "Adam" — masculina neutra, adulta
_PREMADE_FEMALE = "21m00Tcm4TlvDq8ikWAM"  # "Rachel" — femenina neutra, adulta


# Catálogo. El slug (clave) es lo que Claude pone en `Segment.voice`.
VOICES: dict[str, VoiceMeta] = {
    # ── Narrador / MECH ───────────────────────────────────────────────
    "narrator": {
        "voice_id": "",  # vacío = usa ELEVENLABS_VOICE_ID del .env
        "description": (
            "Voz del propio MECH. Para cuando habla como sí mismo "
            "(presentaciones, Q&A) y como NARRADOR omnisciente que enlaza "
            "escenas o describe el contexto histórico."
        ),
    },

    # ── Voces por categoría demográfica (genéricas, reutilizables) ────
    "male": {
        "voice_id": _PREMADE_MALE,
        "description": (
            "HOMBRE adulto, voz neutra. Úsala para cualquier personaje "
            "masculino adulto sin voz propia: un orador, un rey, un soldado, "
            "un político en un discurso histórico."
        ),
    },
    "female": {
        "voice_id": _PREMADE_FEMALE,
        "description": (
            "MUJER adulta, voz neutra. Para cualquier personaje femenino "
            "adulto sin voz propia: una reina, una líder, una madre, una "
            "oradora."
        ),
    },
    "male_elderly": {
        "voice_id": "",  # opcional; si vacío cae a `male`
        "description": (
            "HOMBRE MAYOR / anciano, tono pausado y grave. Para sabios, "
            "abuelos, estadistas veteranos. (Si no está configurada, suena "
            "como `male`.)"
        ),
    },
    "female_elderly": {
        "voice_id": "",  # opcional; si vacío cae a `female`
        "description": (
            "MUJER MAYOR / anciana, tono cálido y pausado. Para abuelas, "
            "matriarcas. (Si no está configurada, suena como `female`.)"
        ),
    },
    "boy": {
        "voice_id": "",  # recomendado clonar/elegir de la Voice Library
        "description": (
            "NIÑO, voz infantil masculina. Para personajes niños. (Si no "
            "está configurada, cae a `male`; conviene clonar una voz "
            "infantil real desde la Voice Library.)"
        ),
    },
    "girl": {
        "voice_id": "",  # recomendado clonar/elegir de la Voice Library
        "description": (
            "NIÑA, voz infantil femenina. Para personajes niñas. (Si no "
            "está configurada, cae a `female`; conviene clonar una voz "
            "infantil real desde la Voice Library.)"
        ),
    },

    # ── Voces de personaje específico (opcionales) ────────────────────
    "don_quijote": {
        "voice_id": "",
        "description": (
            "Voz masculina española madura y solemne (el Hidalgo). Para "
            "Don Quijote, o si preguntan quién es y querés simular su voz."
        ),
    },
    "sancho": {
        "voice_id": "",
        "description": "Voz masculina española campechana y jovial. Para Sancho Panza.",
    },
    "romeo": {
        "voice_id": "",
        "description": "Voz masculina joven, romántica y apasionada. Para Romeo.",
    },
    "julieta": {
        "voice_id": "",
        "description": "Voz femenina joven, dulce y soñadora. Para Julieta.",
    },
    "shrek": {
        "voice_id": "",
        "description": "Voz masculina grave, ruda pero con corazón. Para el ogro Shrek.",
    },
    "burro": {
        "voice_id": "",
        "description": "Voz masculina aguda, parlanchina y cómica. Para el Burro de Shrek.",
    },
    "odiseo": {
        "voice_id": "",
        "description": "Voz masculina épica, heroica y cansada por el viaje. Para Odiseo.",
    },
}


# Cadena de fallback cuando un slug existe en el catálogo pero su voice_id
# está vacío. Así un niño sin voz infantil suena al menos con género correcto
# (hombre/mujer) en vez de saltar directo al narrador.
_FALLBACK_CHAIN: dict[str, str] = {
    "male_elderly": "male",
    "female_elderly": "female",
    "boy": "male",
    "girl": "female",
    # Personajes específicos → categoría demográfica si no tienen voz propia.
    "don_quijote": "male_elderly",
    "sancho": "male",
    "romeo": "male",
    "julieta": "female",
    "shrek": "male",
    "burro": "male",
    "odiseo": "male",
}


def resolve(name: str | None, _seen: set[str] | None = None) -> str:
    """Devuelve el voice_id de ElevenLabs para un slug de voz.

    Lógica:
      - None / "narrator" / desconocido → voz por defecto del .env.
      - Slug con voice_id configurado → ese voice_id.
      - Slug sin voice_id pero con fallback (ej. boy→male) → resuelve el
        fallback recursivamente.
      - Si la cadena se agota → voz por defecto del .env.
    """
    if not name or name == "narrator":
        return config.ELEVENLABS_VOICE_ID

    _seen = _seen or set()
    if name in _seen:  # evita ciclos
        return config.ELEVENLABS_VOICE_ID
    _seen.add(name)

    entry = VOICES.get(name)
    if entry and entry["voice_id"]:
        return entry["voice_id"]

    # Sin voice_id: probamos el fallback (boy→male, don_quijote→male_elderly...).
    fallback = _FALLBACK_CHAIN.get(name)
    if fallback:
        return resolve(fallback, _seen)

    return config.ELEVENLABS_VOICE_ID


def available_voices() -> list[dict]:
    """Voces realmente disponibles (con voice_id, o resolubles vía fallback)."""
    out: list[dict] = []
    for slug, meta in VOICES.items():
        resolved = resolve(slug)
        usable = slug == "narrator" or resolved != config.ELEVENLABS_VOICE_ID or bool(meta["voice_id"])
        out.append({"slug": slug, **meta, "usable": usable})
    return out


def system_prompt_section() -> str:
    """Sección del system prompt: qué voces puede pedir Claude y cómo.

    Lista las voces utilizables (con voice_id propio o resolubles por
    fallback) y explica cómo asignarlas por género/edad en simulaciones.
    """
    # Voces que suenan distinto del narrador (tienen voz real o fallback útil).
    usable = [
        (slug, meta) for slug, meta in VOICES.items()
        if slug != "narrator" and resolve(slug) != config.ELEVENLABS_VOICE_ID
    ]
    if not usable:
        return ""

    lines = [
        "## Voces dinámicas (TTS multi-personaje)",
        "",
        "Podés cambiar de voz por segmento con el campo `voice` de cada "
        "`Segment` (poné el slug de la voz). Vacío o `narrator` = la voz "
        "normal de MECH.",
        "",
        "### Cómo elegir la voz",
        "",
        "Cuando simules una ESCENA con personajes que hablan (un discurso "
        "histórico, un diálogo, una dramatización), asigná a cada segmento "
        "la voz del personaje que habla, según su **género y edad**:",
        "",
        "- Hombre adulto → `male`  ·  Mujer adulta → `female`",
        "- Niño → `boy`  ·  Niña → `girl`",
        "- Anciano → `male_elderly`  ·  Anciana → `female_elderly`",
        "- Si hay un personaje con voz dedicada en la lista de abajo, usá esa.",
        "- La narración de contexto (tú como MECH presentando o enlazando) va "
        "con `narrator` o el campo vacío.",
        "",
        "En un discurso de UNA persona, todos sus segmentos llevan su misma "
        "voz. En un diálogo, alterná la voz segmento a segmento según quién "
        "habla. Empezá el texto del segmento directo en la voz del personaje "
        "(sin 'él dijo:'), porque va a sonar con su voz.",
        "",
        "### Voces disponibles ahora",
        "",
    ]
    for slug, meta in usable:
        lines.append(f"- `{slug}` — {meta['description']}")

    lines += [
        "",
        "No inventes slugs fuera de esta lista. Si un personaje no encaja en "
        "ninguna, usá la categoría demográfica más cercana.",
    ]
    return "\n".join(lines)
