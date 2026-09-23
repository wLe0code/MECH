"""Modo TRIVIA — el juego de preguntas que MECH proyecta al terminar.

Idea (pedido del equipo, sep 2026): cuando MECH acaba de contar una obra,
ofrece jugar una trivia sobre lo que acaba de narrar. Se proyecta la pregunta
con tres opciones, el visitante contesta EN VOZ ALTA («la A», «la segunda», o
diciendo la opción), y la pantalla celebra el acierto o revela la respuesta
correcta.

    MECH:     ...termina de narrar Don Quijote...
    MECH:     «¿Quieres jugar una trivia sobre lo que te conté?»   (+ chime)
    Visitante:«sí»
    MECH:     «Dame un momento, preparo las preguntas.»
    MECH:     «Pregunta 1 de 3. ¿En qué año se publicó la primera parte?
               A: 1605. B: 1700. C: 1492.»                        (+ chime)
              -> la proyección muestra la pregunta y las tres opciones
    Visitante:«la a»
    MECH:     «¡Correcto!»      -> animación de victoria en la pantalla
    ...
    MECH:     «Acertaste 2 de 3.»

**Por qué opción múltiple y no respuesta libre**: esto se juega hablándole a
un robot en un stand con ruido. Con tres opciones leídas en voz alta, el
visitante solo tiene que decir una letra, y eso Whisper lo acierta casi
siempre; una respuesta libre habría que interpretarla (otra llamada a la API)
y en un stand ruidoso fallaría a cada rato.

**El juego corre ENTERO en el servidor.** La proyección solo pinta lo que le
mandan (evento WS `trivia` + `state["trivia"]`): así el marcador, el turno y
las respuestas correctas viven en un solo sitio, y da igual que la pantalla se
recargue a media partida.

Este módulo guarda SOLO el estado, igual que `translator.py` y por el mismo
motivo: lo importan `mech_app` y `server` sin ciclos. Quien habla, proyecta y
llama a Claude es `mech_app`.
"""

from __future__ import annotations

from collections import deque

import config

# Las letras que se leen en voz alta y se pintan en la proyección.
LETTERS = ("A", "B", "C", "D")

# En qué punto va el juego:
#   "off"      = no se está jugando
#   "offer"    = MECH ofreció la trivia y espera un sí o un no
#   "question" = pregunta en pantalla, esperando la respuesta
#   "result"   = acaba de responder; la pantalla muestra acierto o fallo
#   "final"    = marcador final en pantalla
_stage: str = "off"

# Preguntas de la partida. Cada una:
#   {"question": str, "options": [str, ...], "correct": int, "explanation": str}
_questions: list[dict] = []
_index: int = 0          # pregunta actual (0-based)
_score: int = 0
_title: str = ""         # sobre qué va la partida ("Don Quijote de la Mancha")

# Resultado de la pregunta que se acaba de contestar (para la pantalla).
_chosen: int | None = None
_result: str | None = None      # "correct" | "wrong" | "pass"

# Intentos fallidos de ENTENDER la respuesta en la pregunta actual. A la
# segunda, MECH revela la respuesta y sigue: quedarse insistiendo con
# «decí A, B o C» a alguien que no le entiende es la peor experiencia posible.
_misses: int = 0

# Lo último que dijo MECH dentro del modo, para descartar su propio eco por el
# parlante (mismo criterio que el traductor: el micrófono se abre justo
# después de que hable).
_MAX_RECUERDOS = 3
_spoken: deque[str] = deque(maxlen=_MAX_RECUERDOS)


def stage() -> str:
    return _stage


def is_active() -> bool:
    """¿Estamos dentro del juego (ofreciendo, preguntando o mostrando)?"""
    return _stage != "off"


def is_offering() -> bool:
    """¿MECH preguntó si quieren jugar y espera el sí o el no?"""
    return _stage == "offer"


def is_asking() -> bool:
    """¿Hay una pregunta en pantalla esperando respuesta?"""
    return _stage == "question"


def offer(title: str) -> None:
    """MECH acaba de ofrecer la trivia: esperamos un sí o un no."""
    global _stage, _title
    reset()
    _stage = "offer"
    _title = title or ""


def load(questions: list[dict], title: str = "") -> bool:
    """Carga las preguntas ya generadas y arranca la partida.

    Devuelve False si no hay ninguna utilizable (ahí `mech_app` lo dice en
    voz alta en vez de dejar al visitante esperando).
    """
    global _questions, _index, _score, _stage, _title, _chosen, _result, _misses
    limpias = [q for q in (questions or []) if _es_valida(q)]
    if not limpias:
        return False
    _questions = limpias[: max(1, config.TRIVIA_QUESTIONS)]
    _index = 0
    _score = 0
    _chosen = None
    _result = None
    _misses = 0
    _stage = "question"
    if title:
        _title = title
    return True


def _es_valida(q: dict) -> bool:
    """Una pregunta sirve si tiene enunciado, al menos dos opciones y su
    índice correcto cae dentro. Filtramos aquí para que un fallo del modelo
    no reviente la partida a mitad."""
    if not isinstance(q, dict):
        return False
    opciones = q.get("options") or []
    correcta = q.get("correct")
    return bool(
        q.get("question")
        and 2 <= len(opciones) <= len(LETTERS)
        and isinstance(correcta, int)
        and 0 <= correcta < len(opciones)
    )


def current() -> dict | None:
    """La pregunta que está en pantalla, o None si no hay."""
    if 0 <= _index < len(_questions):
        return _questions[_index]
    return None


def total() -> int:
    return len(_questions)


def number() -> int:
    """Número de la pregunta actual, 1-based (para «pregunta 2 de 3»)."""
    return _index + 1


def score() -> int:
    return _score


def title() -> str:
    return _title


def answer(choice: int) -> bool:
    """Registra la respuesta del visitante. Devuelve True si acertó.

    Pasa a la etapa "result": la pantalla enseña el acierto o el fallo y
    `advance()` decide si queda otra pregunta.
    """
    global _stage, _chosen, _result, _score, _misses
    pregunta = current()
    if pregunta is None:
        return False
    _chosen = choice
    acerto = choice == pregunta["correct"]
    if acerto:
        _score += 1
    _result = "correct" if acerto else "wrong"
    _stage = "result"
    _misses = 0
    return acerto


def give_up() -> None:
    """Nadie contestó algo entendible: se revela la respuesta y se sigue."""
    global _stage, _chosen, _result, _misses
    _chosen = None
    _result = "pass"
    _stage = "result"
    _misses = 0


def miss() -> int:
    """Una respuesta que no se entendió. Devuelve cuántas van seguidas."""
    global _misses
    _misses += 1
    return _misses


def misses() -> int:
    return _misses


def advance() -> bool:
    """Pasa a la siguiente pregunta. False si la partida terminó."""
    global _index, _stage, _chosen, _result, _misses
    _chosen = None
    _result = None
    _misses = 0
    _index += 1
    if _index >= len(_questions):
        _stage = "final"
        return False
    _stage = "question"
    return True


def reset() -> None:
    """Sale del juego del todo y olvida la partida."""
    global _stage, _questions, _index, _score, _title, _chosen, _result, _misses
    _stage = "off"
    _questions = []
    _index = 0
    _score = 0
    _title = ""
    _chosen = None
    _result = None
    _misses = 0
    _spoken.clear()


def remember_spoken(text: str) -> None:
    """Guarda algo que MECH acaba de decir (para la guarda anti-eco)."""
    if text:
        _spoken.append(text)


def spoken() -> tuple[str, ...]:
    """Lo último que dijo MECH dentro del modo."""
    return tuple(_spoken)


def snapshot() -> dict:
    """Lo que ven la proyección y el panel (`state["trivia"]`).

    Se manda TODO lo que hace falta para pintar la pantalla desde cero: si el
    proyector se recarga a media partida, vuelve a la pregunta correcta sin
    tener que preguntar nada.
    """
    pregunta = current()
    opciones = list(pregunta["options"]) if pregunta else []
    # La respuesta correcta solo se manda cuando ya se puede enseñar. Si no,
    # cualquiera con el panel abierto vería la solución antes de contestar.
    correcta = pregunta["correct"] if (pregunta and _stage in ("result", "final")) else None
    return {
        "active": _stage != "off",
        "stage": _stage,
        "title": _title,
        "number": number() if _questions else 0,
        "total": len(_questions),
        "question": pregunta["question"] if pregunta else "",
        "options": opciones,
        "letters": list(LETTERS[: len(opciones)]),
        "chosen": _chosen,
        "correct": correcta,
        "result": _result,
        "explanation": (pregunta.get("explanation") or "") if (pregunta and _stage == "result") else "",
        "score": _score,
    }
