"""Idioma activo de MECH — español (default), inglés, francés o portugués.

Regla del equipo (ago 2026, ampliada sep 2026):

- MECH SIEMPRE arranca en **español**.
- Los otros idiomas se activan si y solo si alguien lo despierta en ese
  idioma. A partir de ahí TODO va en ese idioma (lo que MECH entiende, lo que
  narra y los subtítulos):

      «ok MECH» / «despierta MECH»   -> español   (es)
      «wake up MECH»                 -> inglés    (en)
      «bonjour MECH» / «réveille MECH» -> francés (fr)
      «bom dia MECH» / «acorda MECH» -> portugués (pt)

- Al dormirse (frase de reposo o botón), vuelve solo a español: así el
  siguiente visitante del stand encuentra a MECH en español.

Este módulo es a propósito muy simple (una variable + tablas de texto) para
que lo puedan importar `stt`, `llm`, `mech_app` y `server` sin ciclos.

Para AÑADIR un idioma nuevo hacen falta cuatro cosas:
  1. su código en `SUPPORTED` y su nombre en `_LABELS`,
  2. su columna en `_PHRASES` (todas las claves) y en `_LLM_DIRECTIVES`,
  3. sus listas de frases en `config.py` (wake/sleep/interrupt/movimiento) y
     su interruptor `WAKE_<IDIOMA>_ENABLED`,
  4. su entrada en `_WAKE_FLAGS` (aquí abajo) y su chip en el panel.
"""

from __future__ import annotations

import config

DEFAULT = "es"
SUPPORTED = ("es", "en", "fr", "pt")

# Interruptor de config que habilita cada idioma EXTRA (el español no se
# puede apagar: es el idioma base del stand).
_WAKE_FLAGS = {
    "en": "WAKE_ENGLISH_ENABLED",
    "fr": "WAKE_FRENCH_ENABLED",
    "pt": "WAKE_PORTUGUESE_ENABLED",
}

_LABELS = {"es": "español", "en": "inglés", "fr": "francés", "pt": "portugués"}

_current: str = DEFAULT


def current() -> str:
    """Código del idioma activo: 'es', 'en', 'fr' o 'pt'."""
    return _current


def is_english() -> bool:
    return _current == "en"


def enabled_languages() -> tuple[str, ...]:
    """Idiomas realmente disponibles ahora mismo (según el `.env`).

    Siempre incluye el español. Los demás dependen de su interruptor, que se
    lee en caliente: el panel puede apagarlos sin reiniciar.
    """
    extras = tuple(c for c, flag in _WAKE_FLAGS.items() if getattr(config, flag, False))
    return (DEFAULT,) + extras


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
    code = code or _current
    return _LABELS.get(code, code)


# ---------------------------------------------------------------------------
# Frases fijas que MECH dice fuera del plan de Claude
# ---------------------------------------------------------------------------
# OJO: la frase de reposo NO puede contener ninguna palabra de despertar
# ("despierta", "wake", "bonjour", "acorda"...): el micrófono sigue abierto en
# reposo y captaría el eco del parlante, despertándose solo.
# El saludo francés SÍ dice "Bonjour" y "MECH", pero no puede auto-despertarlo:
# en reposo MECH siempre está en español (así que ese saludo no se dice), y
# despierto el bucle ignora un despertar del idioma que ya está activo.
_PHRASES: dict[str, dict[str, str]] = {
    "awake": {
        "es": "Hola, ya te escucho.",
        "en": "Hi, I'm listening.",
        "fr": "Salut, je t'écoute.",
        "pt": "Olá, já te escuto.",
    },
    "dormant": {
        "es": "De acuerdo, hasta luego.",
        "en": "All right, see you later.",
        "fr": "D'accord, à bientôt.",
        "pt": "Está bem, até logo.",
    },
    "greeting": {
        "es": "¡Hola! Soy MECH. Un gusto verte hoy aquí.",
        "en": "Hello! I am MECH. It's a pleasure to see you here today.",
        "fr": "Bonjour ! Je suis MECH. Ravi de te voir ici aujourd'hui.",
        "pt": "Olá! Eu sou o MECH. É um prazer ver você aqui hoje.",
    },
    "error": {
        "es": "Disculpa, tuve un problema. ¿Puedes repetirme?",
        "en": "Sorry, I ran into a problem. Could you say that again?",
        "fr": "Désolé, j'ai eu un problème. Peux-tu répéter ?",
        "pt": "Desculpa, tive um problema. Pode repetir?",
    },
    # Lo que dice al ser interrumpido con "oye MECH" / "hey MECH".
    # Es una PREGUNTA a propósito: así el visitante sabe que le toca hablar
    # (y justo después suena el chime de "puedes hablar").
    "interrupted": {
        "es": "Claro, ¿de qué quieres que hable?",
        "en": "Of course, what would you like me to talk about?",
        "fr": "Bien sûr, de quoi veux-tu que je parle ?",
        "pt": "Claro, sobre o que você quer que eu fale?",
    },
    # Cuando piden proyectar un slot que todavía no tiene videos subidos.
    "empty_playlist": {
        "es": "Todavía no tengo videos en ese espacio.",
        "en": "I don't have any videos in that slot yet.",
        "fr": "Je n'ai pas encore de vidéos dans cet espace.",
        "pt": "Ainda não tenho vídeos nesse espaço.",
    },
    "switched": {
        "es": "Listo, sigo en español.",
        "en": "All right, I'll continue in English.",
        "fr": "D'accord, je continue en français.",
        "pt": "Certo, vou continuar em português.",
    },
    # --- Modo traductor (ver backend/translator.py) ------------------------
    # Lo que pregunta al entrar. Es una PREGUNTA: justo después suena el
    # chime de "puedes hablar", igual que al interrumpirlo.
    # --- Modo TRIVIA (ver backend/trivia.py) ---
    # ⚠️ Estas frases las DICE MECH con el micrófono a punto de abrirse, así
    # que son eco en potencia. La guarda de `trivia.py` las descarta si
    # vuelven a entrar, pero conviene que no repitan literalmente un comando.
    "trivia_offer": {
        "es": "¿Te animas a una trivia sobre lo que acabo de contarte?",
        "en": "Shall we see how much you remember about that?",
        "fr": "Ça te dit un petit quiz sur ce que je viens de raconter ?",
        "pt": "Que tal um quiz sobre o que acabei de contar?",
    },
    "trivia_preparing": {
        "es": "Dame un momento, preparo las preguntas.",
        "en": "Give me a moment, I'm writing the questions.",
        "fr": "Un instant, je prépare les questions.",
        "pt": "Um momento, estou a preparar as perguntas.",
    },
    "trivia_intro": {
        "es": "Allá vamos. Son {total} preguntas.",
        "en": "Here we go. {total} questions.",
        "fr": "C'est parti. {total} questions.",
        "pt": "Vamos lá. São {total} perguntas.",
    },
    "trivia_failed": {
        "es": "No pude preparar las preguntas. ¿Te cuento otra cosa?",
        "en": "I couldn't put the questions together. Shall I tell you something else?",
        "fr": "Je n'ai pas pu préparer les questions. Je te raconte autre chose ?",
        "pt": "Não consegui preparar as perguntas. Conto-te outra coisa?",
    },
    "trivia_question_header": {
        "es": "Pregunta {n} de {total}.",
        "en": "Question {n} of {total}.",
        "fr": "Question {n} sur {total}.",
        "pt": "Pergunta {n} de {total}.",
    },
    "trivia_correct": {
        "es": "¡Correcto!",
        "en": "That's right!",
        "fr": "Exact !",
        "pt": "Certo!",
    },
    "trivia_wrong": {
        "es": "No acertaste. La respuesta correcta es la {letter}: {answer}.",
        "en": "Not quite. The right answer is {letter}: {answer}.",
        "fr": "Raté. La bonne réponse est la {letter} : {answer}.",
        "pt": "Não acertaste. A resposta certa é a {letter}: {answer}.",
    },
    "trivia_pass": {
        "es": "Te la dejo: la respuesta correcta es la {letter}: {answer}.",
        "en": "I'll give you that one: the right answer is {letter}: {answer}.",
        "fr": "Je te la donne : la bonne réponse est la {letter} : {answer}.",
        "pt": "Fica esta: a resposta certa é a {letter}: {answer}.",
    },
    "trivia_repeat": {
        "es": "Contesta diciendo la letra, por ejemplo: la A.",
        "en": "Answer with a letter, for example: A.",
        "fr": "Réponds avec une lettre, par exemple : la A.",
        "pt": "Responde com uma letra, por exemplo: a A.",
    },
    "trivia_final": {
        "es": "Fin del juego. Acertaste {score} de {total}.",
        "en": "Game over. You got {score} out of {total}.",
        "fr": "Fin du jeu. Tu as {score} bonnes réponses sur {total}.",
        "pt": "Fim do jogo. Acertaste {score} de {total}.",
    },
    "trivia_perfect": {
        "es": "¡Perfecto! Las {total} correctas. Estabas atento.",
        "en": "Perfect! All {total} correct. You were paying attention.",
        "fr": "Parfait ! Les {total} bonnes. Tu étais attentif.",
        "pt": "Perfeito! As {total} certas. Estavas atento.",
    },
    "trivia_zero": {
        "es": "Ninguna esta vez, pero ahora ya te las sabes.",
        "en": "None this time, but now you know them.",
        "fr": "Aucune cette fois, mais maintenant tu les connais.",
        "pt": "Nenhuma desta vez, mas agora já as sabes.",
    },
    "trivia_off": {
        "es": "Listo, dejamos el juego.",
        "en": "All right, we'll stop the game.",
        "fr": "D'accord, on arrête le jeu.",
        "pt": "Pronto, paramos o jogo.",
    },
    "trivia_declined": {
        "es": "Sin problema. ¿Qué más quieres saber?",
        "en": "No problem. What else would you like to know?",
        "fr": "Pas de souci. Que veux-tu savoir d'autre ?",
        "pt": "Sem problema. Que mais queres saber?",
    },
    "translate_ask": {
        "es": "Modo traductor. ¿De qué idioma a qué idioma traduzco?",
        "en": "Translator mode. Which language should I translate from and into?",
        "fr": "Mode traducteur. De quelle langue vers quelle langue dois-je traduire ?",
        "pt": "Modo tradutor. De que idioma para que idioma devo traduzir?",
    },
    # Al fijar el par: confirma y pide la frase de una vez (una sola
    # intervención, que en un stand se agradece).
    "translate_ready": {
        "es": "Listo, traduzco entre {src} y {dst}. ¿Qué quieres que traduzca?",
        "en": "Got it, I'll translate between {src} and {dst}. What should I translate?",
        "fr": "D'accord, je traduis entre {src} et {dst}. Que dois-je traduire ?",
        "pt": "Certo, traduzo entre {src} e {dst}. O que você quer que eu traduza?",
    },
    # A partir de la segunda vez ya sabe el par, así que va directo al grano.
    "translate_ask_phrase": {
        "es": "¿Qué quieres que traduzca?",
        "en": "What should I translate?",
        "fr": "Que dois-je traduire ?",
        "pt": "O que você quer que eu traduza?",
    },
    "translate_pair_unknown": {
        "es": "No entendí el par de idiomas. Dime, por ejemplo: de español a francés.",
        "en": "I didn't catch the language pair. Say, for example: from English to Spanish.",
        "fr": "Je n'ai pas compris les deux langues. Dis par exemple : du français à l'espagnol.",
        "pt": "Não entendi o par de idiomas. Diga, por exemplo: de português para espanhol.",
    },
    "translate_same": {
        "es": "Son el mismo idioma. Dime dos distintos.",
        "en": "That's the same language twice. Give me two different ones.",
        "fr": "C'est deux fois la même langue. Donne-m'en deux différentes.",
        "pt": "É o mesmo idioma duas vezes. Diga dois diferentes.",
    },
    "translate_off": {
        "es": "Listo, dejo de traducir.",
        "en": "All right, I'll stop translating.",
        "fr": "D'accord, j'arrête de traduire.",
        "pt": "Certo, paro de traduzir.",
    },
    "translate_error": {
        "es": "No pude traducir eso. ¿Puedes repetirlo?",
        "en": "I couldn't translate that. Could you say it again?",
        "fr": "Je n'ai pas pu traduire ça. Peux-tu répéter ?",
        "pt": "Não consegui traduzir isso. Pode repetir?",
    },
    # Al ENTRAR en modo traductor continuo (se queda traduciendo hasta que le
    # digan "desactiva el modo traductor").
    "translate_on_continuous": {
        "es": "Modo traductor activado. Traduzco entre {src} y {dst} "
              "hasta que me digas que lo desactive.",
        "en": "Translator mode on. I'll translate between {src} and {dst} "
              "until you tell me to turn it off.",
        "fr": "Mode traducteur activé. Je traduis entre {src} et {dst} "
              "jusqu'à ce que tu me dises de l'arrêter.",
        "pt": "Modo tradutor ativado. Traduzo entre {src} e {dst} "
              "até você mandar desativar.",
    },
    # --- Gesto "67" (ver backend/gesture_detect.py) ------------------------
    # Lo que dice al imitar el gesto. Corto a propósito: la gracia está en el
    # movimiento de los brazos, no en la frase, y una frase larga taparía el
    # gesto. Los puntos suspensivos le dan a ElevenLabs la pausa del meme.
    "sixty_seven": {
        "es": "¡Seis... siete!",
        "en": "Six... seven!",
        "fr": "Six... sept !",
        "pt": "Seis... sete!",
    },
}


def say(key: str, code: str | None = None, **fmt: object) -> str:
    """Texto de una frase fija en el idioma activo (o en el que se pida).

    Si la frase lleva huecos (`{src}`, `{dst}`), se rellenan con `fmt`. Un
    hueco sin valor no revienta: se devuelve la frase tal cual.
    """
    entry = _PHRASES.get(key, {})
    texto = entry.get(code or _current) or entry.get(DEFAULT, "")
    if fmt and texto:
        try:
            return texto.format(**fmt)
        except (KeyError, IndexError):
            return texto
    return texto


# ---------------------------------------------------------------------------
# Nombres de los idiomas, escritos EN cada idioma
# ---------------------------------------------------------------------------
# Para que MECH diga "Traduzco entre español y francés" en español pero
# "Je traduis entre l'espagnol et le français" en francés. También es la tabla
# que usa `voice_phrases.extract_language_pair()` para entender "de español a
# francés" (normalizada: sin acentos y en minúsculas).
_LANGUAGE_NAMES: dict[str, dict[str, str]] = {
    "es": {"es": "español", "en": "inglés", "fr": "francés", "pt": "portugués"},
    "en": {"es": "Spanish", "en": "English", "fr": "French", "pt": "Portuguese"},
    "fr": {"es": "espagnol", "en": "anglais", "fr": "français", "pt": "portugais"},
    "pt": {"es": "espanhol", "en": "inglês", "fr": "francês", "pt": "português"},
}

# Cómo puede llamarse cada idioma en una frase hablada, en cualquiera de los
# cuatro. Se compara con el matcher tolerante de `voice_phrases`, así que no
# hacen falta todas las variantes ortográficas — pero sí las que NO están a
# una letra de distancia ("francais" vs "frances", "portugais" vs "portugues").
_LANGUAGE_WORDS: dict[str, tuple[str, ...]] = {
    "es": ("espanol", "espanhol", "castellano", "spanish", "espagnol"),
    "en": ("ingles", "english", "anglais"),
    "fr": ("frances", "francais", "french"),
    "pt": ("portugues", "portugais", "portuguese", "brasileiro"),
}


def language_name(code: str, in_language: str | None = None) -> str:
    """Nombre del idioma `code` escrito en `in_language` (o en el activo)."""
    tabla = _LANGUAGE_NAMES.get(in_language or _current, _LANGUAGE_NAMES[DEFAULT])
    return tabla.get(code, code)


def language_words() -> dict[str, tuple[str, ...]]:
    """Cómo se puede nombrar cada idioma al hablar. Ver `_LANGUAGE_WORDS`."""
    return _LANGUAGE_WORDS


# ---------------------------------------------------------------------------
# Integración con Whisper y con Claude
# ---------------------------------------------------------------------------


def whisper_language() -> str:
    """Idioma que se le pasa a faster-whisper para transcribir.

    En español respeta `config.WHISPER_LANGUAGE` (el panel lo puede cambiar
    en vivo); en los demás idiomas fuerza el código activo, porque si Whisper
    transcribe con el idioma equivocado devuelve basura y MECH no entiende
    nada.
    """
    if _current != DEFAULT:
        return _current
    return config.WHISPER_LANGUAGE


# Nombre del idioma EN el idioma, para escribírselo a Claude sin ambigüedad.
_LLM_DIRECTIVES = {
    "en": ("INGLÉS", "inglés natural y fluido", "English"),
    "fr": ("FRANCÉS", "francés natural y fluido", "français"),
    "pt": ("PORTUGUÉS", "portugués natural y fluido (de Brasil)", "português"),
}


def llm_directive(code: str | None = None) -> str:
    """Bloque que se añade al system prompt de Claude con el idioma activo.

    Va en un bloque de system APARTE (sin cache_control) para no invalidar
    el caché del prompt grande cada vez que se cambia de idioma.
    """
    code = code or _current
    datos = _LLM_DIRECTIVES.get(code)
    if datos:
        nombre, estilo, propio = datos
        return (
            f"# IDIOMA ACTIVO: {nombre}\n\n"
            f"El visitante está hablando en {nombre} y despertó a MECH en ese "
            "idioma. Reglas para ESTA respuesta:\n"
            f"- Escribe TODAS las `narration` en {estilo} "
            "(no traduzcas literalmente del español).\n"
            "- Mantén los nombres propios y los títulos originales "
            "(Don Quijote, Campaña Nacional de 1856, Malpaís, Jiménez "
            "Deredia, Isidro Con Wong) y, si hace falta, explícalos en "
            f"{propio} entre paréntesis la primera vez.\n"
            "- El campo `image_prompt` sigue en inglés, como siempre.\n"
            "- El resto de las reglas (modos, gestos, biblioteca de videos, "
            "información nuestra) no cambian.\n"
            "- Los datos verificados y la 'Información nuestra' están en "
            f"español: tradúcelos al {nombre.lower()}, pero NO inventes datos "
            "nuevos."
        )
    return (
        "# IDIOMA ACTIVO: ESPAÑOL\n\n"
        "Escribe todas las `narration` en español neutro, como indica el "
        "resto del prompt."
    )
