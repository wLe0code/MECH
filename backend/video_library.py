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
    # Opcional: lista de datos VERIFICADOS (fechas, nombres, hechos). Se
    # inyectan al system prompt para que Claude no los invente/alucine.
    # Solo poné aquí cosas que sepas ciertas; MECH tratará esto como verdad.
    facts: list[str]
    # Opcional: URLs de donde se verificaron los facts. Documentación para
    # humanos — NO se inyectan al prompt (no gastan tokens). Si corregís o
    # añadís un fact, anotá aquí de dónde lo sacaste.
    sources: list[str]
    # Opcional: True = "slot abierto" tipo MARKETING. Se comporta distinto a
    # una obra normal en cuatro cosas:
    #   1. `segments` es un MÁXIMO de espacios, no una cantidad exigida: se
    #      proyecta con los videos que haya, aunque falten (y aunque haya
    #      huecos en el medio).
    #   2. Los videos se reproducen ENTEROS y en fila (playlist), no en bucle
    #      bajo la narración de MECH.
    #   3. Suenan CON SU PROPIO AUDIO. MECH no narra encima.
    #   4. NO se le ofrece a Claude: se dispara con una orden directa
    #      ("proyecta marketing"), sin pasar por el modelo.
    promo: bool


# Catálogo de obras con video pre-renderizado.
#
# Para añadir una obra nueva:
#   1. Crea la entrada aquí con el slug que prefieras.
#   2. Crea el subdirectorio backend/video_library/<slug>/.
#   3. Sube los archivos seg01.mp4, seg02.mp4, ... según `segments`.
#   4. Reinicia el servidor (el system prompt se recompone al arrancar).
WORKS: dict[str, WorkMeta] = {
    # --- Slot abierto de MARKETING (promo) ---------------------------------
    # No es una obra cultural: es el material promocional del equipo. Se
    # proyecta entero y con su propio audio cuando alguien dice
    # "proyecta marketing". Ver `promo` en WorkMeta.
    "marketing": {
        "title": "Marketing",
        "author": "Equipo MECH",
        "synopsis": (
            "Videos promocionales del proyecto. Se proyectan enteros, en "
            "orden y con su propio audio, uno tras otro. No hace falta "
            "llenar todos los espacios: se reproduce lo que haya."
        ),
        # MÁXIMO de espacios disponibles (no hay que llenarlos todos).
        "segments": 12,
        "promo": True,
    },
    "don_quijote": {
        "title": "Don Quijote de la Mancha",
        "author": "Miguel de Cervantes",
        "synopsis": (
            "Un hidalgo enloquecido por las novelas de caballería sale junto "
            "a Sancho Panza a buscar aventuras imposibles."
        ),
        "facts": [
            "La primera parte se publicó en 1605 y la segunda en 1615.",
            "Miguel de Cervantes nació en Alcalá de Henares en 1547 y murió "
            "en Madrid en 1616 (un año después de publicar la segunda parte).",
            "El protagonista es el hidalgo Alonso Quijano (don Quijote); su "
            "escudero es Sancho Panza, su caballo Rocinante y su amada "
            "idealizada Dulcinea del Toboso.",
            "Es considerada la primera novela moderna y una de las obras "
            "cumbre de la literatura universal.",
        ],
        "sources": [
            "https://www.britannica.com/topic/Don-Quixote-novel",
            "https://en.wikipedia.org/wiki/Don_Quixote",
            "https://www.britannica.com/biography/Miguel-de-Cervantes",
        ],
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
        "facts": [
            "La Campaña Nacional fue de marzo de 1856 a mayo de 1857; el "
            "presidente de Costa Rica era Juan Rafael Mora Porras.",
            "La Batalla de Santa Rosa fue el 20 de marzo de 1856, en "
            "Guanacaste; la Batalla de Rivas fue el 11 de abril de 1856, en "
            "Nicaragua.",
            "Juan Santamaría, joven soldado y tambor de Alajuela, incendió el "
            "Mesón de Guerra en Rivas y murió en esa gesta; el 11 de abril es "
            "feriado nacional en Costa Rica en su honor.",
            "William Walker era un filibustero estadounidense que había "
            "ocupado Nicaragua desde 1855; se rindió el 1 de mayo de 1857.",
        ],
        "sources": [
            "https://es.wikipedia.org/wiki/Campa%C3%B1a_Nacional_de_1856-1857",
            "https://museojuansantamaria.go.cr/campana-nacional/",
        ],
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
        "facts": [
            "Jorge Jiménez Deredia nació en Heredia, Costa Rica, el 4 de "
            "octubre de 1954; su nombre artístico 'Deredia' viene de "
            "'de Heredia'.",
            "Vive y trabaja en Italia desde 1976; se formó en la Academia de "
            "Bellas Artes de Carrara y estudió arquitectura en Florencia.",
            "Es el PRIMER escultor latinoamericano con una obra en la "
            "Basílica de San Pedro del Vaticano: la estatua de San Marcelino "
            "Champagnat, develada el 20 de septiembre del año 2000 ante Juan "
            "Pablo II.",
            "Su obra está inspirada en las esferas de piedra precolombinas "
            "de Costa Rica; su serie más conocida es 'Génesis'. Es ESCULTOR "
            "(mármol y bronce), no pintor.",
        ],
        "sources": [
            "https://es.wikipedia.org/wiki/Jorge_Jim%C3%A9nez_Deredia",
            "https://www.deredia.com/en/bioagrafia",
        ],
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
        "facts": [
            "Fidel Gamboa fue MÚSICO, compositor, arreglista y cantante "
            "costarricense; NO fue médico ni tuvo otra profesión.",
            "Fidel Gamboa nació en Nicoya el 6 de agosto de 1961 y murió en "
            "Escazú el 28 de agosto de 2011, a los 50 años, por un infarto "
            "(NO murió en 2018).",
            "Malpaís se formó en 1999; entre sus fundadores están los "
            "hermanos Fidel y Jaime Gamboa, junto a músicos como Manuel "
            "Obregón.",
            "Su primer disco se llama 'Uno' y salió en 2002.",
            "Tras la muerte de Fidel, la banda decidió continuar en honor a "
            "su legado.",
            "Su música mezcla folclor costarricense (sobre todo guanacasteco) "
            "con rock, jazz y trova.",
        ],
        "sources": [
            "https://es.wikipedia.org/wiki/Fidel_Gamboa",
            "https://es.wikipedia.org/wiki/Malpa%C3%ADs_(banda)",
            "https://www.grupomalpais.com/pages/historia",
        ],
        "segments": 4,
        "music": True,  # admite sample de música de fondo bajo la narración
    },
    "isaac_newton": {
        "title": "Isaac Newton",
        "author": "Isaac Newton (1642-1727), físico y matemático inglés",
        "synopsis": (
            "Vida, logros y contexto de Isaac Newton: el niño de Woolsthorpe "
            "que quedó huérfano de padre antes de nacer, el joven que durante "
            "la peste de 1665 formuló el cálculo, descompuso la luz y "
            "concibió la gravitación universal, el autor de los 'Principia' "
            "que explicó con las mismas leyes la caída de una manzana y el "
            "giro de los planetas, y el hombre que terminó dirigiendo la Casa "
            "de la Moneda y enterrado entre reyes en la Abadía de "
            "Westminster."
        ),
        "facts": [
            "Isaac Newton nació el 25 de diciembre de 1642 según el "
            "calendario juliano que usaba Inglaterra entonces, que equivale "
            "al 4 de enero de 1643 del calendario actual. Murió el 20 de "
            "marzo de 1727 (juliano), o 31 de marzo de 1727 en el actual. "
            "Las dos fechas son correctas: depende del calendario.",
            "Nació en Woolsthorpe Manor, en Lincolnshire, Inglaterra. Su "
            "padre murió unos meses ANTES de que él naciera, y su madre lo "
            "dejó al cuidado de su abuela cuando se volvió a casar.",
            "Estudió en el Trinity College de Cambridge, donde ingresó en "
            "1661.",
            "Entre 1665 y 1667 la Universidad de Cambridge cerró por la Gran "
            "Peste y Newton volvió a Woolsthorpe. En ese retiro forzado "
            "sentó las bases del cálculo, de su teoría de la luz y de la "
            "gravitación universal. Ese periodo se conoce como su 'annus "
            "mirabilis' (año maravilloso).",
            "Lo de la manzana lo contó el propio Newton en su vejez: vio "
            "caer una manzana y se preguntó por qué caía siempre hacia el "
            "centro de la Tierra. NO le cayó en la cabeza — eso es un adorno "
            "posterior.",
            "Con un prisma demostró que la luz blanca no es simple: está "
            "compuesta por los colores del arcoíris, y el prisma los separa "
            "en vez de teñirla. Lo publicó en 'Opticks' (1704).",
            "Construyó el primer telescopio reflector práctico, que usa un "
            "espejo en lugar de lentes. Los grandes telescopios de hoy "
            "siguen ese principio.",
            "Fue profesor lucasiano de matemáticas en Cambridge desde 1669.",
            "Su obra cumbre es 'Philosophiae Naturalis Principia "
            "Mathematica' (los 'Principia'), publicada en 1687 gracias al "
            "empeño y al dinero del astrónomo Edmond Halley. Ahí enuncia las "
            "tres leyes del movimiento y la ley de gravitación universal.",
            "La idea revolucionaria de los 'Principia' es que las MISMAS "
            "leyes explican la caída de una manzana y el giro de la Luna "
            "alrededor de la Tierra: el cielo y la Tierra obedecen la misma "
            "física.",
            "En 1696 entró en la Real Casa de la Moneda como Warden "
            "(guardián) y en 1699 llegó a Master (director), cargo que "
            "mantuvo hasta su muerte. Persiguió a los falsificadores de "
            "moneda en persona.",
            "Fue presidente de la Royal Society desde 1703 hasta su muerte.",
            "La reina Ana lo nombró caballero (Sir Isaac Newton) en abril de "
            "1705, durante una visita real al Trinity College.",
            "Mantuvo una agria disputa con Gottfried Leibniz sobre quién "
            "inventó primero el cálculo. Hoy se acepta que lo desarrollaron "
            "de forma independiente, y la notación que usamos en clase es la "
            "de Leibniz.",
            "Dedicó muchísimo tiempo a la alquimia y a estudios religiosos y "
            "de cronología bíblica: escribió más sobre eso que sobre física.",
            "Nunca se casó. Murió en Kensington y está enterrado en la "
            "Abadía de Westminster, un honor reservado a reyes y grandes "
            "figuras de Inglaterra.",
            "La frase 'si he visto más lejos, es por estar de pie sobre "
            "hombros de gigantes' es suya, de una carta a Robert Hooke "
            "en 1675.",
        ],
        "sources": [
            "https://en.wikipedia.org/wiki/Isaac_Newton",
            "https://www.britannica.com/biography/Isaac-Newton",
            "https://www.newton.ac.uk/about/isaac-newton/isaac-newtons-life/",
            "https://www.westminster-abbey.org/abbey-commemorations/commemorations/sir-isaac-newton",
            "https://www.royalsocietypublishing.org/doi/10.1098/rsnr.1998.0053",
        ],
        "segments": 5,
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
        "facts": [
            "Isidro Con Wong nació en Puntarenas el 25 de febrero de 1931 y "
            "FALLECIÓ el 1 de septiembre de 2024, a los 93 años (no hablar "
            "de él como si estuviera vivo).",
            "Fue hijo de inmigrantes chinos de la provincia de Cantón "
            "(Zhongshan); parte de su educación temprana fue en China.",
            "Antes de dedicarse al arte fue agricultor, pescador y ganadero "
            "en Paquera y el Golfo de Nicoya; se dedicó de lleno al arte a "
            "partir de los 40 años.",
            "Su estilo se conoce como realismo mágico; las vacas y toros de "
            "sus fincas y los paisajes de Puntarenas son motivos centrales.",
            "Además de pintor fue escultor (bronce y madera).",
        ],
        "sources": [
            "https://es.wikipedia.org/wiki/Isidro_Con_Wong",
            "https://isidroconwong.com/historia/",
            "https://www.larepublica.net/noticia/isidro-con-wong-maestro-del-realismo-magico-y-escultor-costarricense-fallece-a-los-93-anos",
        ],
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


def is_promo(slug: str) -> bool:
    """True si es un slot abierto tipo marketing (ver `promo` en WorkMeta)."""
    return bool(WORKS.get(slug, {}).get("promo"))


def work_is_complete(slug: str) -> bool:
    """¿Está lista para proyectarse?

    Obra normal: TODOS los segmentos definidos tienen que estar en disco (si
    falta uno, la narración quedaría con un hueco visual).

    Slot promo (marketing): basta con que haya AL MENOS UN video. `segments`
    ahí es un máximo de espacios, no una cantidad exigida — el equipo pidió
    expresamente que proyecte aunque no estén los 5.
    """
    meta = WORKS.get(slug)
    if meta is None:
        return False
    if meta.get("promo"):
        return any(segment_exists(slug, i) for i in range(1, meta["segments"] + 1))
    return all(segment_exists(slug, i) for i in range(1, meta["segments"] + 1))


def playlist(slug: str) -> list[dict]:
    """Los archivos presentes de un slot, EN ORDEN y saltándose los huecos.

    Es lo que se reproduce en el modo promo: si están cargados los espacios
    1, 2 y 5, devuelve esos tres y se reproducen seguidos.

    Cada entrada: {n, url, kind, name}.
    """
    meta = WORKS.get(slug)
    if meta is None:
        return []
    items: list[dict] = []
    for i in range(1, meta["segments"] + 1):
        p = segment_file(slug, i)
        if p is None:
            continue
        items.append(
            {
                "n": i,
                "url": f"/videos/{slug}/{p.name}",
                "kind": "video" if segment_is_video(p) else "image",
                "name": p.name,
            }
        )
    return items


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
                "promo": bool(meta.get("promo")),
                "present_segments": present,
                # En un slot promo "listo" = tiene al menos un video; en una
                # obra normal = están todos.
                "complete": work_is_complete(slug),
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
    # Los slots promo (marketing) NO se le ofrecen a Claude: se disparan con
    # una orden directa y se reproducen con su propio audio, sin narración.
    # Si aparecieran aquí, el modelo intentaría contarlos como una obra.
    works = [w for w in available_works() if not w.get("promo")]
    complete = [w for w in works if w["complete"]]
    music_works = [w for w in works if w.get("music") and w.get("music_present")]

    lines = [
        "## Temas culturales que MECH puede exponer",
        "",
        "Estos son los temas/obras del stand. Usá su sinopsis para narrar con "
        "precisión (sobre todo los artistas costarricenses). Modo `immersive`.",
        "",
        "REGLA DE EXACTITUD (importante): NO inventes datos biográficos, "
        "fechas, profesiones ni hechos. Narrá usando la sinopsis, los 'Datos "
        "verificados' que se dan abajo, y solo conocimiento MUY establecido. "
        "Si no estás seguro de una fecha o un dato, NO lo digas: preferí una "
        "narración evocativa y emotiva antes que afirmar algo que podría ser "
        "falso. Nunca contradigas los 'Datos verificados'.",
        "",
        "REGLA DE VISUAL (importante): cuando el usuario pida cualquiera de "
        "estos temas del stand — aunque lo diga como 'háblame de…', 'qué "
        "es…' o 'explícame…' — usá el modo `immersive` y poné SIEMPRE un "
        "visual en cada segmento: `video_slug`+`video_segment` si la obra "
        "tiene video, o `image_prompt` si no. NUNCA narres un tema del stand "
        "sin visual — la proyección es parte del show (hay pantallas y "
        "visores esperando contenido).",
        "",
    ]
    for w in works:
        tag = " — [VIDEO disponible]" if w["complete"] else ""
        music_tag = " — [MÚSICA de fondo]" if (w.get("music") and w.get("music_present")) else ""
        lines.append(
            f"- **{w['title']}** (`{w['slug']}`){tag}{music_tag}: {w['synopsis']}"
        )
        for fact in w.get("facts", []):
            lines.append(f"    - Dato verificado: {fact}")
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
