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


class WorkMeta(TypedDict, total=False):
    title: str
    author: str
    synopsis: str
    segments: int
    # Opcional: True si esta exposición admite música de fondo bajo la
    # narración (se sube un sample a video_library/<slug>/music.<ext>).
    music: bool


# Catálogo de obras con video pre-renderizado.
#
# Para añadir una obra nueva:
#   1. Crea la entrada aquí con el slug que prefieras.
#   2. Crea el subdirectorio backend/video_library/<slug>/.
#   3. Sube los archivos seg01.mp4, seg02.mp4, ... según `segments`.
#   4. Reinicia el servidor (el system prompt se recompone al arrancar).
WORKS: dict[str, WorkMeta] = {
    "don_quijote": {
        "title": "Don Quijote de la Mancha",
        "author": "Miguel de Cervantes",
        "synopsis": (
            "Un hidalgo enloquecido por las novelas de caballería sale junto "
            "a Sancho Panza a buscar aventuras imposibles."
        ),
        "segments": 4,
    },
    "campana_1856": {
        "title": "Campaña Nacional de 1856",
        "author": "Historia de Costa Rica",
        "synopsis": (
            "Costa Rica y Centroamérica se unen para expulsar al filibustero "
            "William Walker. Gesta del héroe Juan Santamaría, que incendia el "
            "mesón en la Batalla de Rivas."
        ),
        "segments": 4,
    },
    "jimenez_deredia": {
        "title": "Esculturas de Jiménez Deredia",
        "author": "Jorge Jiménez Deredia (escultor costarricense)",
        "synopsis": (
            "Exposición de la obra del escultor costarricense Jorge Jiménez "
            "Deredia, célebre por sus esferas y figuras en mármol y bronce. "
            "Su serie 'Génesis' fusiona el simbolismo de las esferas "
            "precolombinas de Costa Rica con temas universales de "
            "transformación, gestación y vida."
        ),
        "segments": 4,  # 3 videos reales + 1 imagen de una obra (cada slot acepta video o imagen)
    },
    "malpais": {
        "title": "Música de Malpaís",
        "author": "Malpaís (banda costarricense)",
        "synopsis": (
            "Exposición sobre Malpaís, banda costarricense fundada por Fidel "
            "Gamboa, ícono de la identidad nacional. Su música fusiona "
            "folclor y rock, evocando los paisajes, la nostalgia y el alma de "
            "Costa Rica."
        ),
        "segments": 4,
        "music": True,  # admite sample de música de fondo bajo la narración
    },
    "isidro_con_wong": {
        "title": "Cuadros de Isidro Con Wong",
        "author": "Isidro Con Wong (pintor costarricense)",
        "synopsis": (
            "Exposición de la pintura de Isidro Con Wong, pionero "
            "costarricense del realismo mágico. Famoso por sus toros rojos, "
            "soles y lunas que retratan la mística rural y el campo de Costa "
            "Rica con color vibrante."
        ),
        "segments": 4,  # 3 videos reales + 1 imagen de una obra (cada slot acepta video o imagen)
    },
}


# ---------------------------------------------------------------------------
# Rutas y disponibilidad
# ---------------------------------------------------------------------------


# Un segmento puede ser un VIDEO (clip que loopea) o una IMAGEN (foto fija de
# una obra). Se acepta cualquiera de estas extensiones; el nombre base es
# seg01, seg02, ... y la extensión define el tipo.
_SEG_VIDEO_EXTS = (".mp4", ".webm", ".mov", ".m4v", ".mkv")
_SEG_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")
_SEG_EXTS = _SEG_VIDEO_EXTS + _SEG_IMAGE_EXTS


def segment_filename(segment: int) -> str:
    """Nombre por defecto (mp4) — solo para logs/mensajes."""
    return f"seg{segment:02d}.mp4"


def segment_basename(segment: int) -> str:
    """Base sin extensión: seg01, seg02, ..."""
    return f"seg{segment:02d}"


def segment_file(slug: str, segment: int) -> Path | None:
    """Ruta del archivo del segmento si existe (video o imagen), o None."""
    folder = config.VIDEO_LIBRARY_DIR / slug
    base = segment_basename(segment)
    for ext in _SEG_EXTS:
        p = folder / f"{base}{ext}"
        if p.exists():
            return p
    return None


def segment_path(slug: str, segment: int) -> Path:
    """Ruta por defecto (.mp4) — para guardar cuando no se sabe la extensión."""
    return config.VIDEO_LIBRARY_DIR / slug / segment_filename(segment)


def segment_url(slug: str, segment: int) -> str | None:
    """URL relativa del segmento existente (o None si no hay archivo)."""
    p = segment_file(slug, segment)
    return f"/videos/{slug}/{p.name}" if p else None


def segment_is_video(path: Path) -> bool:
    return path.suffix.lower() in _SEG_VIDEO_EXTS


def segment_kind(slug: str, segment: int) -> str | None:
    """'video' | 'image' | None según el archivo del segmento."""
    p = segment_file(slug, segment)
    if p is None:
        return None
    return "video" if segment_is_video(p) else "image"


def segment_exists(slug: str, segment: int) -> bool:
    return segment_file(slug, segment) is not None


# --- Música de fondo (solo obras con "music": True, ej. Malpaís) ------------

# Extensiones de audio aceptadas para el sample de música de fondo.
# (ffplay reproduce todas; incluimos las que salen de descargas comunes.)
_MUSIC_EXTS = (
    ".mp3", ".ogg", ".wav", ".m4a", ".aac", ".flac",
    ".opus", ".weba", ".webm", ".aiff", ".aif", ".wma",
)


def background_audio_path(slug: str):
    """Ruta al sample de música de fondo de la obra, o None si no hay.

    El archivo se llama music.<ext> dentro de la carpeta de la obra.
    """
    folder = config.VIDEO_LIBRARY_DIR / slug
    for ext in _MUSIC_EXTS:
        p = folder / f"music{ext}"
        if p.exists():
            return p
    return None


def background_audio_exists(slug: str) -> bool:
    return background_audio_path(slug) is not None


def background_audio_url(slug: str) -> str | None:
    p = background_audio_path(slug)
    return f"/videos/{slug}/{p.name}" if p else None


def supports_music(slug: str) -> bool:
    """True si la obra está marcada como que admite música de fondo."""
    return bool(WORKS.get(slug, {}).get("music"))


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
        seg_files = []
        for i in range(1, total + 1):
            p = segment_file(slug, i)
            seg_files.append(
                {
                    "n": i,
                    "present": p is not None,
                    "url": (f"/videos/{slug}/{p.name}" if p else None),
                    "kind": ("video" if (p and segment_is_video(p)) else
                             ("image" if p else None)),
                }
            )
        present = sum(1 for s in seg_files if s["present"])
        out.append(
            {
                "slug": slug,
                **meta,
                "music": bool(meta.get("music")),
                "music_present": background_audio_exists(slug),
                "present_segments": present,
                "complete": present == total,
                "segment_files": seg_files,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Sección dinámica del system prompt
# ---------------------------------------------------------------------------


def system_prompt_section() -> str:
    """Texto que se inyecta al system prompt de Claude.

    Incluye:
      1. TODOS los temas/obras que MECH puede exponer (con sinopsis), para que
         narre con contexto incluso los que no tienen video.
      2. Cuáles tienen video pre-renderizado (para usar video_slug/segment).
      3. Cuáles tienen música de fondo (para usar el campo background_music).
    """
    works = available_works()
    complete = [w for w in works if w["complete"]]
    music_works = [w for w in works if w.get("music") and w.get("music_present")]

    lines = [
        "## Temas culturales que MECH puede exponer",
        "",
        "Estos son los temas/obras del stand. Usá su sinopsis para narrar con "
        "precisión (sobre todo los artistas costarricenses). Modo `immersive`.",
        "",
    ]
    for w in works:
        tag = " — [VIDEO disponible]" if w["complete"] else ""
        music_tag = " — [MÚSICA de fondo]" if (w.get("music") and w.get("music_present")) else ""
        lines.append(
            f"- **{w['title']}** (`{w['slug']}`){tag}{music_tag}: {w['synopsis']}"
        )
    lines.append("")

    if complete:
        lines += [
            "### Obras con material visual pre-cargado",
            "",
            "Para estas hay material listo (videos y/o imágenes reales). Usá "
            "EXACTAMENTE el número de segmentos indicado; en cada `Segment` "
            "poné `video_slug` (exacto) y `video_segment` (1, 2, 3...), y NO "
            "pongas `image_prompt`:",
            "",
        ]
        for w in complete:
            lines.append(f"- `{w['slug']}` — {w['segments']} segmentos.")
        lines += [
            "",
            "Para los temas SIN video, dejá `video_slug`/`video_segment` en "
            "null y usá `image_prompt` (en inglés) como siempre.",
        ]
    else:
        lines.append(
            "Ninguna obra tiene video completo aún: para los visuales usá "
            "`image_prompt` (en inglés) y dejá `video_slug` en null."
        )

    if music_works:
        lines += [
            "",
            "### Música de fondo",
            "",
            "Estas exposiciones tienen música ambiental ya subida. Al narrarlas, "
            "poné en el `Plan` el campo `background_music` con el slug, para que "
            "suene de fondo, suave, mientras hablás:",
            "",
        ]
        for w in music_works:
            lines.append(f"- {w['title']} → `background_music: {w['slug']}`")
        lines += [
            "",
            "IMPORTANTE para las exposiciones CON música: hacé una narración "
            "LARGA y pausada, que dure alrededor de DOS MINUTOS en total. "
            "Aprovechá los segmentos para contar bastante (contexto, historia, "
            "anécdotas, emoción) con párrafos de varias frases cada uno. La "
            "música suena en bucle por debajo todo el tiempo y se detiene sola "
            "cuando terminás de hablar.",
        ]

    return "\n".join(lines)
