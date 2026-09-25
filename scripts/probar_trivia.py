"""Comprueba cómo entiende MECH las respuestas de la trivia.

Por qué existe: en el juego, entender mal una respuesta no da un error — da
un RESULTADO FALSO. El visitante dice "la A", MECH apunta la C y le dice que
ha fallado. Eso es peor que no entender nada, así que aquí se miden las dos
caras:

  - ACIERTOS: las tres formas naturales de contestar (la letra, el orden y el
    texto de la opción), incluidas transcripciones deformadas de Whisper.
  - PRUDENCIA: lo que NO se puede interpretar (un "no sé", una opción a
    medias que vale para dos, ruido). Ahí la respuesta correcta es None:
    MECH vuelve a preguntar en vez de inventarse una respuesta.

    python scripts/probar_trivia.py

Sale 1 si algo falla. No necesita hardware ni claves de API.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import voice_phrases as vp  # noqa: E402

# Las opciones de tres preguntas tipo: años, nombres y frases.
ANOS = ["1605", "1700", "1492"]
NOMBRES = ["Sancho Panza", "Dulcinea del Toboso", "Rocinante"]
PARECIDAS = ["Miguel de Cervantes", "Miguel de Unamuno", "Lope de Vega"]
FRASES = ["Se volvió loco leyendo", "Heredó un castillo", "Nunca salió de casa"]

# (opciones, lo que se oyó, índice esperado)
ACIERTOS: list[tuple[list[str], str, int]] = [
    # --- Por la LETRA ---
    (ANOS, "la a", 0),
    (ANOS, "A", 0),
    (ANOS, "la be", 1),
    (ANOS, "b", 1),
    (ANOS, "opción B", 1),
    (ANOS, "la ce", 2),
    (ANOS, "c", 2),
    (ANOS, "creo que la letra C", 2),
    (ANOS, "yo digo la a", 0),
    # Whisper escribe las letras como suenan.
    (ANOS, "ah", 0),
    (ANOS, "ve", 1),
    (ANOS, "se", 2),
    # --- Por el ORDEN ---
    (ANOS, "la primera", 0),
    (ANOS, "la segunda", 1),
    (ANOS, "la tercera", 2),
    (ANOS, "la opción número 2", 1),
    (ANOS, "la 3", 2),
    (NOMBRES, "el primero", 0),
    # --- Por el TEXTO de la opción ---
    (ANOS, "1605", 0),
    (ANOS, "el año 1605", 0),
    (ANOS, "1492", 2),
    (NOMBRES, "Sancho Panza", 0),
    (NOMBRES, "creo que Sancho Panza", 0),
    (NOMBRES, "Sancho", 0),
    (NOMBRES, "Dulcinea", 1),
    (NOMBRES, "Dulcinea del Toboso", 1),
    (NOMBRES, "el caballo Rocinante", 2),
    (PARECIDAS, "Cervantes", 0),
    (PARECIDAS, "Miguel de Cervantes", 0),
    (PARECIDAS, "Unamuno", 1),
    (PARECIDAS, "Lope de Vega", 2),
    (FRASES, "se volvió loco leyendo", 0),
    (FRASES, "que heredó un castillo", 1),
    # --- En los otros idiomas ---
    (ANOS, "the first one", 0),
    (ANOS, "the second", 1),
    (ANOS, "la deuxième", 1),
    (ANOS, "a terceira", 2),
]

# (opciones, lo que se oyó) -> tiene que devolver None
PRUDENCIA: list[tuple[list[str], str]] = [
    # No lo sabe. ⚠️ En español lleva un "se" dentro, que suena igual que la
    # C: sin la guarda, rendirse contaría como responder la tercera.
    (ANOS, "no sé"),
    (ANOS, "no lo sé"),
    (ANOS, "ni idea"),
    (ANOS, "a ver, no sé"),
    (NOMBRES, "no tengo idea"),
    (ANOS, "I don't know"),
    (ANOS, "não sei"),
    # Una palabra que vale para DOS opciones: mejor volver a preguntar.
    (PARECIDAS, "Miguel"),
    (PARECIDAS, "Miguel de"),
    # Ruido y cosas que no responden nada.
    (ANOS, "mmm"),
    (ANOS, "espera"),
    (NOMBRES, "¿puedes repetir la pregunta?"),
    (FRASES, "qué difícil"),
]


def main() -> int:
    fallos = 0

    print("── ACIERTOS (tiene que entender la respuesta) ──")
    for opciones, texto, esperado in ACIERTOS:
        sale = vp.parse_answer(texto, opciones)
        ok = sale == esperado
        if not ok:
            fallos += 1
        letra = vp.normalize(texto)[:34]
        print(f"  {'ok ' if ok else 'MAL'}  {letra:<36} → {sale}  (esperado {esperado})")

    print("\n── PRUDENCIA (NO puede inventarse una respuesta) ──")
    for opciones, texto in PRUDENCIA:
        sale = vp.parse_answer(texto, opciones)
        ok = sale is None
        if not ok:
            fallos += 1
        print(f"  {'ok ' if ok else 'MAL'}  {texto:<36} → {sale}  (esperado None)")

    total = len(ACIERTOS) + len(PRUDENCIA)
    print(f"\n{total - fallos}/{total} bien.")
    if fallos:
        print(
            f"\n⚠️  {fallos} fallo(s). Si aflojas el matcher para pillar uno, "
            "vuelve a correr esto Y scripts/probar_frases.py: en este repo, "
            "aflojar por un lado rompe el otro."
        )
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
