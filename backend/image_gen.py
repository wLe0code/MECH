"""Generación de imágenes con Gemini (NanoBanana = gemini-2.5-flash-image).

Las imágenes se proyectan en el espacio inmersivo (Romeo y Julieta, Shrek,
etc). Una imagen por escena; el guion de Claude decide qué escenas pedir.

Las guardamos en disco (IMAGE_OUTPUT_DIR) para que projector.py las muestre.
"""

from __future__ import annotations

import time
from pathlib import Path

from google import genai
from google.genai import types

import config


_client: genai.Client | None = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=config.GOOGLE_API_KEY)
    return _client


def generate_image(prompt: str, filename: str | None = None) -> Path:
    """Genera una imagen y la guarda en IMAGE_OUTPUT_DIR.

    Args:
        prompt: Descripción visual en inglés (Gemini rinde mejor en inglés
            para image gen, aunque acepta español). Ejemplo:
            "Renaissance Verona balcony at night, two young lovers, dramatic
            moonlight, cinematic, painterly style."
        filename: Nombre del archivo destino (sin path). Si no se da, usa
            un timestamp.

    Returns:
        Path al archivo PNG generado.
    """
    if filename is None:
        filename = f"scene_{int(time.time())}.png"
    output_path = config.IMAGE_OUTPUT_DIR / filename

    client = get_client()
    response = client.models.generate_content(
        model=config.GEMINI_IMAGE_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            output_path.write_bytes(part.inline_data.data)
            return output_path

    raise RuntimeError(f"Gemini no devolvió imagen para el prompt: {prompt!r}")
