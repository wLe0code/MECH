"""Biblioteca de videos pre-renderizados (Opción B de la arquitectura).

Para WRO 2026 evitamos generar video en vivo (latencia 30s–2min con
Kling/Veo/Runway mata la demo interactiva). En su lugar, los videos de
las obras culturales se generan UNA VEZ antes del evento (en otra
máquina, sin presión de latencia) y se guardan como .mp4 en
``VIDEO_LIBRARY_DIR``. MECH los reproduce en bucle mientras narra.

Estructura en disco esperada:

.. code-block:: text

    backend/video_library/
        romeo_julieta/
            seg01.mp4
            seg02.mp4
            ...
        shrek/
            seg01.mp4
            ...

El "slug" del subdirectorio es lo que Claude usa para referirse a la
obra en el `Plan`. Los archivos siguen el patrón ``seg{NN:02d}.mp4``.

Si una obra NO está en la biblioteca o le faltan segmentos, MECH cae al
flujo original de NanoBanana (generación de imagen en vivo) para no
romper preguntas espontáneas del usuario.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

import config


class WorkMeta(TypedDict):
    title: str
    author: str
    synopsis: str
    segments: int


# Catálogo de obras con video pre-renderizado.
#
# Para añadir una obra nueva:
#   1. Crea la entrada aquí con el slug que prefieras.
#   2. Crea el subdirectorio backend/video_library/<slug>/.
#   3. Sube los archivos seg01.mp4, seg02.mp4, ... según `segments`.
#   4. Reinicia el servidor (el system prompt se recompone al arrancar).
WORKS: dict[str, WorkMeta] = {
    "romeo_julieta": {
        "title": "Romeo y Julieta",
        "author": "William Shakespeare",
        "synopsis": (
            "Tragedia de amor entre dos jóvenes de familias rivales en la "
            "Verona del Renacimiento."
        ),
        "segments": 4,
    },
    "shrek": {
        "title": "Shrek",
        "author": "DreamWorks (basado en el libro de William Steig)",
        "synopsis": (
            "Un ogro solitario rescata a una princesa y descubre el amor "
            "verdadero junto a un burro parlanchín."
        ),
        "segments": 4,
    },
    "la_odisea": {
        "title": "La Odisea",
        "author": "Homero",
        "synopsis": (
            "El viaje de diez años de Odiseo de regreso a Ítaca tras la "
            "Guerra de Troya, enfrentando dioses y monstruos."
        ),
        "segments": 4,
    },
    "don_quijote": {
        "title": "Don Quijote de la Mancha",
        "author": "Miguel de Cervantes",
        "synopsis": (
            "Un hidalgo enloquecido por las novelas de caballería sale junto "
            "a Sancho Panza a buscar aventuras imposibles."
        ),
        "segments": 4,
    },
}


# ---------------------------------------------------------------------------
# Rutas y disponibilidad
# ---------------------------------------------------------------------------


def segment_filename(segment: int) -> str:
    """Convención: seg01.mp4, seg02.mp4, ..."""
    return f"seg{segment:02d}.mp4"


def segment_path(slug: str, segment: int) -> Path:
    """Ruta absoluta al archivo del segmento (no verifica existencia)."""
    return config.VIDEO_LIBRARY_DIR / slug / segment_filename(segment)


def segment_url(slug: str, segment: int) -> str:
    """URL relativa servida por el backend (montado en /videos)."""
    return f"/videos/{slug}/{segment_filename(segment)}"


def segment_exists(slug: str, segment: int) -> bool:
    return segment_path(slug, segment).exists()


def work_is_complete(slug: str) -> bool:
    """True si TODOS los segmentos definidos están físicamente presentes."""
    meta = WORKS.get(slug)
    if meta is None:
        return False
    return all(segment_exists(slug, i) for i in range(1, meta["segments"] + 1))


def available_works() -> list[dict]:
    """Reporte para el panel / API.

    Cada entrada: {slug, title, author, synopsis, segments,
                   present_segments, complete}.
    """
    out: list[dict] = []
    for slug, meta in WORKS.items():
        total = meta["segments"]
        present = sum(1 for i in range(1, total + 1) if segment_exists(slug, i))
        out.append(
            {
                "slug": slug,
                **meta,
                "present_segments": present,
                "complete": present == total,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Sección dinámica del system prompt
# ---------------------------------------------------------------------------


def system_prompt_section() -> str:
    """Texto que se inyecta al system prompt de Claude.

    Lista solo las obras que están **completas** en disco para que Claude
    sepa cuáles puede invocar vía ``video_slug``/``video_segment``.
    """
    complete = [w for w in available_works() if w["complete"]]
    if not complete:
        return (
            "## Biblioteca de videos pre-renderizados\n\n"
            "(Biblioteca vacía por ahora. Para cualquier obra que pida el "
            "usuario, usa `image_prompt` como siempre. NO uses `video_slug`.)"
        )

    lines = [
        "## Biblioteca de videos pre-renderizados",
        "",
        "Para estas obras hay videos pre-grabados en mp4 listos para "
        "proyectar. Cuando el usuario pida una de ellas:",
        "",
        "- Usa `mode: immersive`.",
        "- El `Plan` debe tener EXACTAMENTE el número de segmentos indicado "
        "abajo (uno por video).",
        "- En cada `Segment`, NO pongas `image_prompt`. En su lugar pon "
        "`video_slug` (texto, exacto al de la lista) y `video_segment` "
        "(número 1, 2, 3, ... que identifica qué video va con ese segmento).",
        "- La narración tuya en cada segmento debe encajar con lo que muestra "
        "el video correspondiente. Lee el sinopsis para saber el tono.",
        "",
        "### Obras disponibles",
        "",
    ]
    for w in complete:
        lines.append(
            f"- **{w['title']}** — `video_slug`: `{w['slug']}` — "
            f"{w['segments']} segmentos. _{w['synopsis']}_"
        )

    lines += [
        "",
        "Si la obra que pide el usuario NO está en la lista de arriba, "
        "vuelve al flujo original: deja `video_slug` y `video_segment` "
        "vacíos (null) y usa `image_prompt` con un prompt en inglés.",
    ]
    return "\n".join(lines)
