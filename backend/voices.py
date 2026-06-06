"""Catálogo de voces dinámicas de ElevenLabs.

Para que MECH no narre TODO con la misma voz, definimos aquí una tabla
de personajes (Don Quijote, Sancho, Shrek, Julieta, ...) con su voice_id
correspondiente en la cuenta de ElevenLabs.

Cómo conseguir un voice_id:
  1. Entra a https://elevenlabs.io/app/voice-library
  2. Busca o clona una voz que encaje con el personaje.
  3. "Add to my voices". Después, en https://elevenlabs.io/app/voice-lab,
     hacé clic en la voz y copiá su Voice ID (string de ~20 caracteres).
  4. Pegalo abajo en el campo `voice_id` del personaje correspondiente.

Si un personaje tiene `voice_id` vacío, MECH cae a la voz por defecto
(`ELEVENLABS_VOICE_ID` del .env). Esto deja que se rellene de a poco sin
romper la demo.

El system prompt de Claude se compone dinámicamente con los personajes
que SÍ tienen voice_id definido — así Claude solo elige entre voces que
realmente existen.
"""

from __future__ import annotations

from typing import TypedDict

import config


class VoiceMeta(TypedDict):
    voice_id: str
    description: str  # cuándo usar esta voz (lo lee Claude)


# Catálogo. Para activar una voz, pegale el voice_id de ElevenLabs.
# El slug (la clave del dict) es lo que Claude usa en `Segment.voice`.
VOICES: dict[str, VoiceMeta] = {
    # Narrador por defecto — MECH cuando habla "como MECH".
    "narrator": {
        "voice_id": "",  # vacío = usa ELEVENLABS_VOICE_ID
        "description": (
            "Voz narrativa neutra del propio MECH. Úsala cuando MECH habla "
            "como sí mismo (presentaciones, Q&A, transiciones) y como "
            "narrador omnisciente entre escenas."
        ),
    },
    # --- Don Quijote ---
    "don_quijote": {
        "voice_id": "",
        "description": (
            "Voz masculina española madura, tono solemne y caballeresco "
            "(el Hidalgo). Úsala cuando hable Don Quijote o cuando alguien "
            "le pregunte a MECH quién es Don Quijote y querés simular su voz."
        ),
    },
    "sancho": {
        "voice_id": "",
        "description": (
            "Voz masculina española campechana, tono jovial. Para Sancho Panza."
        ),
    },
    # --- Romeo y Julieta ---
    "romeo": {
        "voice_id": "",
        "description": "Voz masculina joven, romántica y apasionada. Para Romeo.",
    },
    "julieta": {
        "voice_id": "",
        "description": "Voz femenina joven, dulce y soñadora. Para Julieta.",
    },
    # --- Shrek ---
    "shrek": {
        "voice_id": "",
        "description": (
            "Voz masculina grave, ruda pero con corazón. Para el ogro Shrek."
        ),
    },
    "burro": {
        "voice_id": "",
        "description": (
            "Voz masculina aguda y parlanchina, cómica. Para el Burro de Shrek."
        ),
    },
    # --- La Odisea ---
    "odiseo": {
        "voice_id": "",
        "description": (
            "Voz masculina épica, tono heroico y cansado por el viaje. "
            "Para Odiseo / Ulises."
        ),
    },
}


def resolve(name: str | None) -> str:
    """Devuelve el voice_id de ElevenLabs para un nombre de personaje.

    Cae al default (`config.ELEVENLABS_VOICE_ID`) si:
      - `name` es None o "narrator".
      - El personaje no existe en el catálogo.
      - El personaje existe pero su `voice_id` está vacío (aún sin clonar).
    """
    if not name or name == "narrator":
        return config.ELEVENLABS_VOICE_ID
    entry = VOICES.get(name)
    if entry is None or not entry["voice_id"]:
        return config.ELEVENLABS_VOICE_ID
    return entry["voice_id"]


def available_voices() -> list[dict]:
    """Lista de voces que realmente están configuradas (voice_id no vacío)."""
    out: list[dict] = []
    for slug, meta in VOICES.items():
        if slug == "narrator" or meta["voice_id"]:
            out.append({"slug": slug, **meta, "active": bool(meta["voice_id"]) or slug == "narrator"})
    return out


def system_prompt_section() -> str:
    """Sección del system prompt que le dice a Claude qué voces puede pedir.

    Solo aparecen los personajes con voice_id configurado (más narrator).
    Si no hay ninguna voz extra cargada, se devuelve string vacío para no
    ensuciar el prompt.
    """
    active = [
        (slug, meta) for slug, meta in VOICES.items()
        if slug == "narrator" or meta["voice_id"]
    ]
    if len(active) <= 1:
        # Solo narrator → no vale la pena mencionarlo, MECH habla con su voz.
        return ""

    lines = [
        "## Voces disponibles (TTS multi-personaje)",
        "",
        "Para hacer la narración más viva podés pedir distintas voces por "
        "segmento. En el campo `voice` de cada `Segment`, poné el slug de la "
        "voz que querés que suene durante esa narración. Si lo dejás vacío "
        "(o pones `narrator`), suena la voz por defecto de MECH.",
        "",
        "### Voces que existen ahora mismo",
        "",
    ]
    for slug, meta in active:
        lines.append(f"- `{slug}` — {meta['description']}")

    lines += [
        "",
        "Reglas:",
        "- En modo `immersive`, podés alternar voces por escena para diálogos "
        "(ej: una escena con `voice: romeo`, la siguiente con `voice: julieta`).",
        "- En modo `qa`, si el usuario pregunta por un personaje específico "
        "(\"¿quién es Don Quijote?\"), respondé EN PRIMERA PERSONA como ese "
        "personaje y poné su slug en `voice` para que suene auténtico.",
        "- NO inventes slugs que no estén en la lista de arriba — si el "
        "personaje no tiene voz dedicada, dejá `voice` vacío.",
    ]
    return "\n".join(lines)
