"""Cliente Claude — el cerebro de MECH.

Decisiones de diseño:

1. **Salida estructurada en vez de tool-use.** Para una narración como
   "Romeo y Julieta", una llamada con tool_use por escena tendría 5-10
   round trips. En su lugar, Claude devuelve un plan completo (varios
   segmentos con narración + prompt de imagen + gesto) en una sola
   respuesta, y el backend lo ejecuta secuencialmente.

2. **Prompt caching del system prompt.** El system prompt es largo (incluye
   conocimiento de las obras y el contexto del stand). Con cache_control
   los siguientes requests cuestan ~10% del primero.

3. **Modelo Opus 4.7** por defecto. Para tareas creativas (narración en
   español, decisiones de escena) la diferencia con Sonnet vale la pena.
   Si el costo importa, cambia CLAUDE_MODEL a claude-sonnet-4-6.
"""

from __future__ import annotations

from typing import Literal

import anthropic
from pydantic import BaseModel, Field

import config
import video_library


SYSTEM_PROMPT = """Eres MECH, un robot interactivo de un stand de la WRO 2026
(World Robot Olympiad, categoría "Robots and Culture"). Tu propósito es crear
experiencias inmersivas que mezclan ingeniería y cultura.

Cuando un usuario te habla, decides qué hacer y devuelves un plan estructurado.
El backend ejecuta el plan: para cada segmento, genera la imagen (si la pides),
te hace narrar el texto con TTS, y le pide al cuerpo del robot que haga el gesto.

# Modos de interacción

Decides el modo según lo que pregunte el usuario:

1. **stand**: información sobre ti mismo (qué eres, cómo funcionas, quién te
   construyó, qué hardware usas). Responde 1-2 segmentos, voz cercana, sin
   imagen (o con una imagen tuya tipo render).

2. **immersive**: el usuario pide una obra cultural (Romeo y Julieta, Shrek,
   El Quijote, La Odisea, etc.). Cuenta la historia en 3-6 escenas. Cada
   escena tiene un visual (ver "Biblioteca de videos" abajo: si la obra
   está pre-renderizada usás `video_slug`+`video_segment`; si no, usás
   `image_prompt`) y una narración corta (2-4 frases en español, tono
   dramático pero accesible).

3. **qa**: pregunta libre sobre cualquier tema (puede ser sobre la obra que
   está contando, sobre el stand, sobre cultura general). Responde en 1
   segmento, sin imagen por defecto (o con imagen si ayuda).

4. **movement**: el usuario pide que el robot haga algo físico ("camina",
   "saluda", "explora"). 1 segmento, gesto correspondiente, narración corta
   confirmando.

# Cómo escribir narraciones

- En español neutro, evita modismos muy regionales.
- Frases cortas. ElevenLabs respira mejor con frases de 10-20 palabras.
- Tono dramático para inmersivo, conversacional para stand/qa.
- NO uses asteriscos ni marcadores de formato — esto va directo a TTS.
- NO digas "voy a contarte" — entra directo a la escena.

# Cómo escribir prompts de imagen

- En inglés (el modelo rinde mejor).
- Estilo: cinematográfico, painterly, dramatic lighting.
- Especifica época, lugar, personajes, atmósfera.
- Ejemplo: "Renaissance Verona, moonlit balcony, young woman in white
  dress leaning down, young man below in red doublet, dramatic chiaroscuro,
  oil painting style."

# Gestos disponibles (mapean a movimientos físicos del robot)

- `neutral`: pose por defecto
- `excited`: brazos arriba, cabeza erguida (para momentos épicos)
- `thoughtful`: cabeza ladeada, un brazo abajo (para introspección)
- `wave`: saludo (al iniciar interacción o despedirse)
- `point`: señalar (cuando se proyecta algo importante)
- `arms_open`: brazos abiertos (para invitar, para finales emotivos)
"""


class Segment(BaseModel):
    """Una unidad de la performance: narración + visual (video o imagen) + gesto.

    Lógica de visual:
      - Si `video_slug` Y `video_segment` están presentes → MECH reproduce
        el video pre-renderizado correspondiente (Opción B).
      - Si no, y `image_prompt` está presente → MECH genera la imagen con
        NanoBanana en vivo (fallback para obras no pre-renderizadas y para
        preguntas espontáneas).
      - Si ninguno está presente → segmento sin visual nuevo (mantiene el
        anterior).
    """

    narration: str = Field(
        ...,
        description="Texto en español que el robot narrará con TTS. Sin markdown.",
    )
    image_prompt: str | None = Field(
        None,
        description=(
            "Prompt en inglés para generar la imagen de fondo con NanoBanana. "
            "None si vas a usar un video pre-renderizado (video_slug) o si no "
            "querés cambiar el visual."
        ),
    )
    video_slug: str | None = Field(
        None,
        description=(
            "Slug exacto de una obra de la biblioteca de videos "
            "pre-renderizados (ver lista en el system prompt). Si lo das, "
            "también das video_segment y el `image_prompt` se ignora."
        ),
    )
    video_segment: int | None = Field(
        None,
        ge=1,
        description=(
            "Número 1-indexed del segmento dentro de la obra (1, 2, 3, ...). "
            "Debe estar entre 1 y el total de segmentos de esa obra."
        ),
    )
    gesture: Literal[
        "neutral", "excited", "thoughtful", "wave", "point", "arms_open"
    ] = Field("neutral", description="Gesto físico durante la narración.")


class Plan(BaseModel):
    """Plan completo de la respuesta de Claude a una petición del usuario."""

    mode: Literal["stand", "immersive", "qa", "movement"]
    title: str = Field(..., description="Título corto, sirve de log/depuración.")
    segments: list[Segment] = Field(..., min_length=1, max_length=8)


_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def plan_response(user_message: str, conversation_history: list[dict] | None = None) -> Plan:
    """Pide a Claude un plan estructurado para responder al usuario.

    Args:
        user_message: La transcripción de lo que dijo el usuario.
        conversation_history: Lista de turnos previos en formato Anthropic
            ({"role": ..., "content": ...}). Para mantener contexto entre
            preguntas dentro de una obra.

    Returns:
        Un Plan con los segmentos a ejecutar.
    """
    client = get_client()
    messages = list(conversation_history or [])
    messages.append({"role": "user", "content": user_message})

    # Componemos el system prompt con la lista dinámica de obras pre-renderizadas
    # presentes en disco (Opción B). Si no hay videos, esa sección dice "vacía".
    full_system_prompt = SYSTEM_PROMPT + "\n\n" + video_library.system_prompt_section()

    response = client.messages.parse(
        model=config.CLAUDE_MODEL,
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": full_system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=messages,
        output_format=Plan,
    )

    if response.parsed_output is None:
        raise RuntimeError(
            f"Claude no devolvió un Plan válido. stop_reason={response.stop_reason}"
        )
    return response.parsed_output


def append_turn(history: list[dict], user_message: str, plan: Plan) -> list[dict]:
    """Añade un turno al historial para la próxima llamada.

    Guardamos solo el texto de las narraciones (no las imágenes ni los
    gestos) — es lo que Claude necesita para mantener contexto.
    """
    assistant_text = "\n".join(seg.narration for seg in plan.segments)
    return history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": assistant_text},
    ]
