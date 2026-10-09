"""Idioma activo de MECH — español (default) y ocho idiomas más.

Regla del equipo (ago 2026, ampliada sep y oct 2026):

- MECH SIEMPRE arranca en **español**.
- Los otros idiomas se activan si y solo si alguien lo despierta en ese
  idioma. A partir de ahí TODO va en ese idioma (lo que MECH entiende, lo que
  narra y los subtítulos):

      «ok MECH» / «despierta MECH»   -> español   (es)
      «wake up MECH»                 -> inglés    (en)
      «bonjour MECH» / «réveille MECH» -> francés (fr)
      «bom dia MECH» / «acorda MECH» -> portugués (pt)
      «guten Tag MECH» / «wach auf MECH» -> alemán (de)
      «ciao MECH» / «buongiorno MECH» -> italiano (it)
      «こんにちは MECH» / «起きて MECH» -> japonés (ja)
      «привет MECH» / «проснись MECH» -> ruso     (ru)
      «你好 MECH» / «醒醒 MECH»        -> mandarín (zh)
      «안녕 MECH» / «일어나 MECH»      -> coreano  (ko)

- Al dormirse (frase de reposo o botón), vuelve solo a español: así el
  siguiente visitante del stand encuentra a MECH en español.
- Los COMANDOS también van en ese idioma, y solo en ese (oct 2026): despierto
  con «wake up MECH» lo corta «hey MECH» y no «oye MECH». Y el idioma queda
  fijo hasta que se duerme. Ver `voice_phrases._frases_activas()` y
  `config.VOICE_STRICT_LANGUAGE`.

Este módulo es a propósito muy simple (una variable + tablas de texto) para
que lo puedan importar `stt`, `llm`, `mech_app` y `server` sin ciclos.

Para AÑADIR un idioma nuevo hacen falta cuatro cosas:
  1. su código en `SUPPORTED` y su nombre en `_LABELS`,
  2. su columna en `_PHRASES` (todas las claves) y en `_LLM_DIRECTIVES`,
  3. sus listas de frases en `config.py` (wake/sleep/interrupt/movimiento) y
     su interruptor `WAKE_<IDIOMA>_ENABLED`,
  4. su entrada en `_WAKE_FLAGS` (aquí abajo) y su chip en el panel.

Y si NO se escribe con letras latinas (japonés, ruso, chino, coreano), además:
  5. cómo escribe Whisper el nombre «MECH» en esa escritura, en
     `config.VOICE_NAME_ALIASES`,
  6. revisar que los subtítulos partan bien las líneas
     (`backend/subtitles.py` cuenta el ANCHO, no las letras) y que la Pi tenga
     una fuente con esos caracteres (`python -m backend.preflight` lo mira).

Antes de darlo por bueno: `python scripts/probar_idiomas.py`.
"""

from __future__ import annotations

import config

DEFAULT = "es"
SUPPORTED = ("es", "en", "fr", "pt", "de", "it", "ja", "ru", "zh", "ko")

# Interruptor de config que habilita cada idioma EXTRA (el español no se
# puede apagar: es el idioma base del stand).
_WAKE_FLAGS = {
    "en": "WAKE_ENGLISH_ENABLED",
    "fr": "WAKE_FRENCH_ENABLED",
    "pt": "WAKE_PORTUGUESE_ENABLED",
    "de": "WAKE_GERMAN_ENABLED",
    "it": "WAKE_ITALIAN_ENABLED",
    "ja": "WAKE_JAPANESE_ENABLED",
    "ru": "WAKE_RUSSIAN_ENABLED",
    "zh": "WAKE_CHINESE_ENABLED",
    "ko": "WAKE_KOREAN_ENABLED",
}

_LABELS = {
    "es": "español", "en": "inglés", "fr": "francés", "pt": "portugués",
    "de": "alemán", "it": "italiano", "ja": "japonés", "ru": "ruso",
    "zh": "mandarín", "ko": "coreano",
}

_current: str = DEFAULT


def current() -> str:
    """Código del idioma activo: uno de `SUPPORTED` ('es', 'en', 'ja'…)."""
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
# Los saludos de alemán, italiano, japonés, ruso, chino y coreano evitan sus
# propias palabras de despertar ("Willkommen" en vez de "guten Tag", "ようこそ"
# en vez de "こんにちは", "환영합니다" en vez de "안녕하세요"): así
# `GREETING_LANGUAGE` se puede poner en cualquiera de ellos sin que el saludo,
# dicho en reposo, despierte a MECH.
_PHRASES: dict[str, dict[str, str]] = {
    "awake": {
        "es": "Hola, ya te escucho.",
        "en": "Hi, I'm listening.",
        "fr": "Salut, je t'écoute.",
        "pt": "Olá, já te escuto.",
        "de": "Hallo, ich höre zu.",
        "it": "Ciao, ti ascolto.",
        "ja": "はい、聞いています。",
        "ru": "Привет, я слушаю.",
        "zh": "你好，我在听。",
        "ko": "네, 듣고 있어요.",
    },
    "dormant": {
        "es": "De acuerdo, hasta luego.",
        "en": "All right, see you later.",
        "fr": "D'accord, à bientôt.",
        "pt": "Está bem, até logo.",
        "de": "In Ordnung, bis später.",
        "it": "D'accordo, a dopo.",
        "ja": "わかりました。また後で。",
        "ru": "Хорошо, до встречи.",
        "zh": "好的，回头见。",
        "ko": "알겠습니다. 다음에 또 봬요.",
    },
    "greeting": {
        "es": "¡Hola! Soy MECH. Un gusto verte hoy aquí.",
        "en": "Hello! I am MECH. It's a pleasure to see you here today.",
        "fr": "Bonjour ! Je suis MECH. Ravi de te voir ici aujourd'hui.",
        "pt": "Olá! Eu sou o MECH. É um prazer ver você aqui hoje.",
        "de": "Willkommen! Ich bin MECH. Schön, dich heute hier zu sehen.",
        "it": "Benvenuto! Sono MECH. È un piacere vederti qui oggi.",
        "ja": "ようこそ！私はMECHです。今日ここでお会いできて嬉しいです。",
        "ru": "Добро пожаловать! Я MECH. Рад видеть тебя здесь сегодня.",
        "zh": "欢迎！我是MECH。很高兴今天在这里见到你。",
        "ko": "환영합니다! 저는 MECH입니다. 오늘 여기서 만나서 반갑습니다.",
    },
    "error": {
        "es": "Disculpa, tuve un problema. ¿Puedes repetirme?",
        "en": "Sorry, I ran into a problem. Could you say that again?",
        "fr": "Désolé, j'ai eu un problème. Peux-tu répéter ?",
        "pt": "Desculpa, tive um problema. Pode repetir?",
        "de": "Entschuldigung, ich hatte ein Problem. Kannst du das wiederholen?",
        "it": "Scusa, ho avuto un problema. Puoi ripetere?",
        "ja": "すみません、問題が起きました。もう一度言ってもらえますか？",
        "ru": "Извини, у меня возникла проблема. Можешь повторить?",
        "zh": "抱歉，我遇到了一点问题。可以再说一遍吗？",
        "ko": "죄송합니다, 문제가 생겼어요. 다시 말씀해 주시겠어요?",
    },
    # Lo que dice al ser interrumpido con "oye MECH" / "hey MECH".
    # Es una PREGUNTA a propósito: así el visitante sabe que le toca hablar
    # (y justo después suena el chime de "puedes hablar").
    "interrupted": {
        "es": "Claro, ¿de qué quieres que hable?",
        "en": "Of course, what would you like me to talk about?",
        "fr": "Bien sûr, de quoi veux-tu que je parle ?",
        "pt": "Claro, sobre o que você quer que eu fale?",
        "de": "Klar, worüber soll ich sprechen?",
        "it": "Certo, di cosa vuoi che parli?",
        "ja": "もちろんです。何について話しましょうか？",
        "ru": "Конечно, о чём мне рассказать?",
        "zh": "当然，你想让我讲什么？",
        "ko": "물론이죠. 어떤 이야기를 해 드릴까요?",
    },
    # Cuando piden proyectar un slot que todavía no tiene videos subidos.
    "empty_playlist": {
        "es": "Todavía no tengo videos en ese espacio.",
        "en": "I don't have any videos in that slot yet.",
        "fr": "Je n'ai pas encore de vidéos dans cet espace.",
        "pt": "Ainda não tenho vídeos nesse espaço.",
        "de": "In diesem Bereich habe ich noch keine Videos.",
        "it": "Non ho ancora video in questo spazio.",
        "ja": "そのスペースにはまだ動画がありません。",
        "ru": "В этом разделе у меня пока нет видео.",
        "zh": "这个栏目里还没有视频。",
        "ko": "그 칸에는 아직 영상이 없어요.",
    },
    "switched": {
        "es": "Listo, sigo en español.",
        "en": "All right, I'll continue in English.",
        "fr": "D'accord, je continue en français.",
        "pt": "Certo, vou continuar em português.",
        "de": "Alles klar, ich mache auf Deutsch weiter.",
        "it": "Va bene, continuo in italiano.",
        "ja": "わかりました。日本語で続けます。",
        "ru": "Хорошо, продолжаю по-русски.",
        "zh": "好的，我接下来说中文。",
        "ko": "알겠습니다. 한국어로 계속할게요.",
    },
    # --- Modo traductor (ver backend/translator.py) ------------------------
    # Lo que pregunta al entrar. Es una PREGUNTA: justo después suena el
    # chime de "puedes hablar", igual que al interrumpirlo.
    # --- Modo TRIVIA (ver backend/trivia.py) ---
    # ⚠️ Estas frases las DICE MECH con el micrófono a punto de abrirse, así
    # que son eco en potencia. La guarda de `trivia.py` las descarta si
    # vuelven a entrar, pero conviene que no repitan literalmente un comando.
    "trivia_offer": {
        "es": "¿Te gustaría realizar una trivia para comprobar tu conocimiento?",
        "en": "Would you like to take a trivia to test your knowledge?",
        "fr": "Aimerais-tu faire un quiz pour tester tes connaissances ?",
        "pt": "Gostarias de fazer uma trivia para testar o teu conhecimento?",
        "de": "Möchtest du ein Quiz machen, um dein Wissen zu testen?",
        "it": "Ti piacerebbe fare un quiz per mettere alla prova le tue conoscenze?",
        "ja": "知識を試すクイズに挑戦してみませんか？",
        "ru": "Хочешь пройти викторину, чтобы проверить свои знания?",
        "zh": "想不想做个小测验，检验一下你学到了什么？",
        "ko": "배운 내용을 확인하는 퀴즈를 풀어 보시겠어요?",
    },
    "trivia_preparing": {
        "es": "Dame un momento, preparo las preguntas.",
        "en": "Give me a moment, I'm writing the questions.",
        "fr": "Un instant, je prépare les questions.",
        "pt": "Um momento, estou a preparar as perguntas.",
        "de": "Einen Moment, ich bereite die Fragen vor.",
        "it": "Dammi un momento, preparo le domande.",
        "ja": "少々お待ちください。問題を準備しています。",
        "ru": "Одну минуту, я готовлю вопросы.",
        "zh": "请稍等，我正在准备题目。",
        "ko": "잠시만요, 문제를 준비하고 있어요.",
    },
    "trivia_intro": {
        "es": "Allá vamos. Son {total} preguntas.",
        "en": "Here we go. {total} questions.",
        "fr": "C'est parti. {total} questions.",
        "pt": "Vamos lá. São {total} perguntas.",
        "de": "Los geht's. Es sind {total} Fragen.",
        "it": "Si parte. Sono {total} domande.",
        "ja": "それでは始めます。全部で{total}問です。",
        "ru": "Поехали. Количество вопросов: {total}.",
        "zh": "开始吧。一共{total}道题。",
        "ko": "시작할게요. 모두 {total}문제예요.",
    },
    "trivia_failed": {
        "es": "No pude preparar las preguntas. ¿Te cuento otra cosa?",
        "en": "I couldn't put the questions together. Shall I tell you something else?",
        "fr": "Je n'ai pas pu préparer les questions. Je te raconte autre chose ?",
        "pt": "Não consegui preparar as perguntas. Conto-te outra coisa?",
        "de": "Ich konnte die Fragen nicht vorbereiten. Soll ich dir etwas anderes erzählen?",
        "it": "Non sono riuscito a preparare le domande. Ti racconto qualcos'altro?",
        "ja": "問題を準備できませんでした。ほかの話をしましょうか？",
        "ru": "Не получилось подготовить вопросы. Рассказать что-нибудь другое?",
        "zh": "题目没有准备好。要不要我讲点别的？",
        "ko": "문제를 준비하지 못했어요. 다른 이야기를 해 드릴까요?",
    },
    "trivia_question_header": {
        "es": "Pregunta {n} de {total}.",
        "en": "Question {n} of {total}.",
        "fr": "Question {n} sur {total}.",
        "pt": "Pergunta {n} de {total}.",
        "de": "Frage {n} von {total}.",
        "it": "Domanda {n} di {total}.",
        "ja": "{total}問中、第{n}問。",
        "ru": "Вопрос {n} из {total}.",
        "zh": "第{n}题，共{total}题。",
        "ko": "{total}문제 중 {n}번 문제.",
    },
    "trivia_correct": {
        "es": "¡Correcto!",
        "en": "That's right!",
        "fr": "Exact !",
        "pt": "Certo!",
        "de": "Richtig!",
        "it": "Esatto!",
        "ja": "正解です！",
        "ru": "Верно!",
        "zh": "答对了！",
        "ko": "정답입니다!",
    },
    "trivia_wrong": {
        "es": "No has acertado. La respuesta correcta es la {letter}: {answer}.",
        "en": "You didn't get it. The correct answer is {letter}: {answer}.",
        "fr": "Raté. La bonne réponse est la {letter} : {answer}.",
        "pt": "Não acertaste. A resposta certa é a {letter}: {answer}.",
        "de": "Leider falsch. Die richtige Antwort ist {letter}: {answer}.",
        "it": "Non hai indovinato. La risposta corretta è la {letter}: {answer}.",
        "ja": "残念、不正解です。正解は{letter}、{answer}です。",
        "ru": "Не угадал. Правильный ответ — {letter}: {answer}.",
        "zh": "答错了。正确答案是{letter}：{answer}。",
        "ko": "아쉽지만 틀렸어요. 정답은 {letter}, {answer}입니다.",
    },
    "trivia_pass": {
        "es": "Te la dejo: la respuesta correcta es la {letter}: {answer}.",
        "en": "I'll give you that one: the right answer is {letter}: {answer}.",
        "fr": "Je te la donne : la bonne réponse est la {letter} : {answer}.",
        "pt": "Fica esta: a resposta certa é a {letter}: {answer}.",
        "de": "Die verrate ich dir: Die richtige Antwort ist {letter}: {answer}.",
        "it": "Te la dico io: la risposta corretta è la {letter}: {answer}.",
        "ja": "では答えを言います。正解は{letter}、{answer}です。",
        "ru": "Подскажу: правильный ответ — {letter}: {answer}.",
        "zh": "这题我来公布：正确答案是{letter}：{answer}。",
        "ko": "정답을 알려 드릴게요. 정답은 {letter}, {answer}입니다.",
    },
    "trivia_repeat": {
        "es": "Contesta diciendo la letra, por ejemplo: la A.",
        "en": "Answer with a letter, for example: A.",
        "fr": "Réponds avec une lettre, par exemple : la A.",
        "pt": "Responde com uma letra, por exemplo: a A.",
        "de": "Antworte mit einem Buchstaben, zum Beispiel: A.",
        "it": "Rispondi con una lettera, per esempio: la A.",
        "ja": "アルファベットで答えてください。たとえば、A。",
        "ru": "Ответь буквой, например: A.",
        "zh": "请用字母回答，比如：A。",
        "ko": "알파벳으로 대답해 주세요. 예를 들면, A.",
    },
    "trivia_final": {
        "es": "Fin del juego. Acertaste {score} de {total}.",
        "en": "Game over. You got {score} out of {total}.",
        "fr": "Fin du jeu. Tu as {score} bonnes réponses sur {total}.",
        "pt": "Fim do jogo. Acertaste {score} de {total}.",
        "de": "Spiel vorbei. Du hast {score} von {total} richtig.",
        "it": "Fine del gioco. Ne hai indovinate {score} su {total}.",
        "ja": "ゲーム終了です。{total}問中{score}問正解でした。",
        "ru": "Игра окончена. Правильных ответов: {score} из {total}.",
        "zh": "游戏结束。{total}道题你答对了{score}道。",
        "ko": "게임이 끝났어요. {total}문제 중 {score}문제를 맞혔어요.",
    },
    "trivia_perfect": {
        "es": "¡Perfecto! Las {total} correctas. Estabas atento.",
        "en": "Perfect! All {total} correct. You were paying attention.",
        "fr": "Parfait ! Les {total} bonnes. Tu étais attentif.",
        "pt": "Perfeito! As {total} certas. Estavas atento.",
        "de": "Perfekt! Alle {total} richtig. Du hast gut aufgepasst.",
        "it": "Perfetto! Tutte e {total} corrette. Eri attento.",
        "ja": "完璧です！{total}問すべて正解。よく聞いていましたね。",
        "ru": "Отлично! Все {total} верно. Ты слушал внимательно.",
        "zh": "太棒了！{total}道题全对。你听得很认真。",
        "ko": "완벽해요! {total}문제를 모두 맞혔어요. 정말 잘 들으셨네요.",
    },
    "trivia_zero": {
        "es": "Ninguna esta vez, pero ahora ya te las sabes.",
        "en": "None this time, but now you know them.",
        "fr": "Aucune cette fois, mais maintenant tu les connais.",
        "pt": "Nenhuma desta vez, mas agora já as sabes.",
        "de": "Diesmal keine, aber jetzt kennst du die Antworten.",
        "it": "Nessuna questa volta, ma ora le sai.",
        "ja": "今回は全問不正解でしたが、これで覚えましたね。",
        "ru": "В этот раз ни одного, зато теперь ты их знаешь.",
        "zh": "这次一题都没答对，不过现在你都知道了。",
        "ko": "이번에는 하나도 못 맞혔지만, 이제는 다 아시겠죠.",
    },
    "trivia_off": {
        "es": "Listo, dejamos el juego.",
        "en": "All right, we'll stop the game.",
        "fr": "D'accord, on arrête le jeu.",
        "pt": "Pronto, paramos o jogo.",
        "de": "Alles klar, wir beenden das Spiel.",
        "it": "Va bene, lasciamo il gioco.",
        "ja": "わかりました。ゲームを終わります。",
        "ru": "Хорошо, заканчиваем игру.",
        "zh": "好的，游戏到此结束。",
        "ko": "알겠습니다. 게임을 마칠게요.",
    },
    "trivia_declined": {
        "es": "Sin problema. ¿Qué más quieres saber?",
        "en": "No problem. What else would you like to know?",
        "fr": "Pas de souci. Que veux-tu savoir d'autre ?",
        "pt": "Sem problema. Que mais queres saber?",
        "de": "Kein Problem. Was möchtest du noch wissen?",
        "it": "Nessun problema. Cos'altro vuoi sapere?",
        "ja": "大丈夫です。ほかに知りたいことはありますか？",
        "ru": "Без проблем. Что ещё ты хочешь узнать?",
        "zh": "没关系。你还想了解什么？",
        "ko": "괜찮아요. 또 무엇이 궁금하세요?",
    },
    # De qué va la partida cuando MECH todavía no ha narrado nada: se PROYECTA
    # en la pantalla del juego («Sobre: …»), así que va en el idioma activo.
    "trivia_about_us": {
        "es": "MECH y su equipo",
        "en": "MECH and its team",
        "fr": "MECH et son équipe",
        "pt": "MECH e a sua equipa",
        "de": "MECH und sein Team",
        "it": "MECH e il suo team",
        "ja": "MECHとそのチーム",
        "ru": "MECH и его команда",
        "zh": "MECH和它的团队",
        "ko": "MECH와 팀",
    },
    "translate_ask": {
        "es": "Modo traductor. ¿De qué idioma a qué idioma traduzco?",
        "en": "Translator mode. Which language should I translate from and into?",
        "fr": "Mode traducteur. De quelle langue vers quelle langue dois-je traduire ?",
        "pt": "Modo tradutor. De que idioma para que idioma devo traduzir?",
        "de": "Übersetzermodus. Aus welcher Sprache in welche Sprache soll ich übersetzen?",
        "it": "Modalità traduttore. Da quale lingua a quale lingua devo tradurre?",
        "ja": "通訳モードです。何語から何語に翻訳しますか？",
        "ru": "Режим переводчика. С какого языка на какой мне переводить?",
        "zh": "翻译模式。要从哪种语言翻译成哪种语言？",
        "ko": "통역을 도와 드릴게요. 어떤 언어에서 어떤 언어로 번역할까요?",
    },
    # Al fijar el par: confirma y pide la frase de una vez (una sola
    # intervención, que en un stand se agradece).
    "translate_ready": {
        "es": "Listo, traduzco entre {src} y {dst}. ¿Qué quieres que traduzca?",
        "en": "Got it, I'll translate between {src} and {dst}. What should I translate?",
        "fr": "D'accord, je traduis entre {src} et {dst}. Que dois-je traduire ?",
        "pt": "Certo, traduzo entre {src} e {dst}. O que você quer que eu traduza?",
        "de": "Alles klar, ich übersetze zwischen {src} und {dst}. Was soll ich übersetzen?",
        "it": "Va bene, traduco tra {src} e {dst}. Cosa vuoi che traduca?",
        "ja": "わかりました。{src}と{dst}の間で翻訳します。何を翻訳しますか？",
        "ru": "Хорошо, перевожу между языками: {src} и {dst}. Что перевести?",
        "zh": "好的，我在{src}和{dst}之间翻译。要翻译什么？",
        "ko": "알겠습니다. {src}와 {dst} 사이에서 통역할게요. 무엇을 번역할까요?",
    },
    # A partir de la segunda vez ya sabe el par, así que va directo al grano.
    "translate_ask_phrase": {
        "es": "¿Qué quieres que traduzca?",
        "en": "What should I translate?",
        "fr": "Que dois-je traduire ?",
        "pt": "O que você quer que eu traduza?",
        "de": "Was soll ich übersetzen?",
        "it": "Cosa vuoi che traduca?",
        "ja": "何を翻訳しますか？",
        "ru": "Что перевести?",
        "zh": "要翻译什么？",
        "ko": "무엇을 번역할까요?",
    },
    "translate_pair_unknown": {
        "es": "No entendí el par de idiomas. Dime, por ejemplo: de español a francés.",
        "en": "I didn't catch the language pair. Say, for example: from English to Spanish.",
        "fr": "Je n'ai pas compris les deux langues. Dis par exemple : du français à l'espagnol.",
        "pt": "Não entendi o par de idiomas. Diga, por exemplo: de português para espanhol.",
        "de": "Ich habe das Sprachpaar nicht verstanden. Sag zum Beispiel: von Deutsch nach Spanisch.",
        "it": "Non ho capito le due lingue. Di' per esempio: dall'italiano allo spagnolo.",
        "ja": "言語の組み合わせが分かりませんでした。たとえば「日本語からスペイン語」と言ってください。",
        "ru": "Я не понял, какие языки. Скажи, например: с русского на испанский.",
        "zh": "我没听清是哪两种语言。比如你可以说：从中文到西班牙语。",
        "ko": "어떤 언어인지 잘 못 들었어요. 예를 들어 “한국어에서 스페인어로”라고 말해 주세요.",
    },
    "translate_same": {
        "es": "Son el mismo idioma. Dime dos distintos.",
        "en": "That's the same language twice. Give me two different ones.",
        "fr": "C'est deux fois la même langue. Donne-m'en deux différentes.",
        "pt": "É o mesmo idioma duas vezes. Diga dois diferentes.",
        "de": "Das ist zweimal dieselbe Sprache. Nenne mir zwei verschiedene.",
        "it": "È la stessa lingua due volte. Dimmene due diverse.",
        "ja": "同じ言語が二つです。別々の言語を二つ言ってください。",
        "ru": "Это один и тот же язык. Назови два разных.",
        "zh": "这是同一种语言。请说两种不同的语言。",
        "ko": "같은 언어예요. 서로 다른 두 언어를 말해 주세요.",
    },
    # ⚠️ En TODOS los idiomas esta frase casa, a propósito, con la orden de
    # salir («deja de traducir»). Justo después de decirla se abre el
    # micrófono: si MECH se oye a sí mismo, eso se lee como otro «deja de
    # traducir» y, como ya no hay nada que olvidar, se ignora en silencio. Si
    # NO casara, su eco se iría a Claude como una pregunta cualquiera.
    # `scripts/probar_idiomas.py` lo comprueba: no la reescribas sin correrlo.
    "translate_off": {
        "es": "Listo, dejo de traducir.",
        "en": "All right, I'll stop translating.",
        "fr": "D'accord, j'arrête de traduire.",
        "pt": "Certo, paro de traduzir.",
        "de": "Alles klar, ich höre auf zu übersetzen.",
        "it": "Va bene, smetto di tradurre.",
        "ja": "わかりました。翻訳を終了します。",
        "ru": "Хорошо, перестаю переводить.",
        "zh": "好的，我停止翻译了。",
        "ko": "알겠습니다. 번역을 종료할게요.",
    },
    "translate_error": {
        "es": "No pude traducir eso. ¿Puedes repetirlo?",
        "en": "I couldn't translate that. Could you say it again?",
        "fr": "Je n'ai pas pu traduire ça. Peux-tu répéter ?",
        "pt": "Não consegui traduzir isso. Pode repetir?",
        "de": "Das konnte ich nicht übersetzen. Kannst du es wiederholen?",
        "it": "Non sono riuscito a tradurlo. Puoi ripetere?",
        "ja": "翻訳できませんでした。もう一度言ってもらえますか？",
        "ru": "Не получилось это перевести. Можешь повторить?",
        "zh": "这句我没能翻译出来。可以再说一遍吗？",
        "ko": "그 문장은 번역하지 못했어요. 다시 말씀해 주시겠어요?",
    },
    # --- Modo MÚSICA (ver backend/music.py) --------------------------------
    # ⚠️ Casi todas se dicen con el micrófono a punto de abrirse, así que son
    # eco en potencia. Por eso están escritas con cuidado:
    #   - ninguna pregunta lleva un sí/no del idioma («Claro», «No encontré»,
    #     «sin», «nos»…) ni las frases de «otra canción» o de salir del modo:
    #     MECH se contestaría a sí mismo;
    #   - `music_off` es la EXCEPCIÓN: tiene que casar con la orden de salir
    #     (igual que «Listo, dejo de traducir»), para que su eco se reconozca
    #     y muera en silencio en vez de irse a Claude.
    # `scripts/probar_musica.py` lo comprueba en los diez idiomas: no las
    # reescribas sin correrlo.
    "music_ask": {
        "es": "¿Qué canción quieres escuchar, y de qué artista?",
        "en": "Which song would you like to hear, and by which artist?",
        "fr": "Quelle chanson veux-tu écouter, et de quel artiste ?",
        "pt": "Que música queres ouvir, e de que artista?",
        "de": "Welches Lied möchtest du hören, und von wem ist es?",
        "it": "Quale canzone vuoi ascoltare, e di quale artista?",
        "ja": "どの曲を聴きたいですか？アーティストの名前も教えてください。",
        "ru": "Какую песню ты хочешь послушать, и кто её исполняет?",
        "zh": "你想听哪首歌？是哪位歌手唱的？",
        "ko": "어떤 노래를 듣고 싶으세요? 가수 이름도 알려 주세요.",
    },
    # Cuando ya dijo que quiere otra.
    "music_ask_more": {
        "es": "¿Cuál ponemos? Dime la canción y el artista.",
        "en": "Which one? Tell me the song and the artist.",
        "fr": "Laquelle ? Dis-moi la chanson et l'artiste.",
        "pt": "Qual? Diz-me a música e o artista.",
        "de": "Welches? Sag mir das Lied und den Künstler.",
        "it": "Quale? Dimmi la canzone e l'artista.",
        "ja": "どれにしますか？曲名とアーティストを教えてください。",
        "ru": "Какую? Назови песню и исполнителя.",
        "zh": "想听哪一首？告诉我歌名和歌手。",
        "ko": "어떤 곡으로 할까요? 노래 제목과 가수를 말씀해 주세요.",
    },
    # Dijo la canción pero no de quién es.
    "music_artist": {
        "es": "¿De qué artista es?",
        "en": "Who is it by?",
        "fr": "C'est de quel artiste ?",
        "pt": "De que artista é?",
        "de": "Von wem ist das Lied?",
        "it": "Di quale artista è?",
        "ja": "どのアーティストの曲ですか？",
        "ru": "Кто её исполняет?",
        "zh": "这首歌是谁唱的？",
        "ko": "어느 가수의 노래인가요?",
    },
    # Justo antes de que suene (aquí el micrófono está cerrado).
    "music_playing": {
        "es": "Ahí va: {title}, de {artist}.",
        "en": "Here it is: {title}, by {artist}.",
        "fr": "C'est parti : {title}, de {artist}.",
        "pt": "Aqui vai: {title}, de {artist}.",
        "de": "Los geht's: {title}, von {artist}.",
        "it": "Eccola: {title}, di {artist}.",
        "ja": "{artist}の「{title}」をかけます。",
        "ru": "Ставлю: {title}, исполняет {artist}.",
        "zh": "这就播放{artist}的《{title}》。",
        "ko": "{artist}의 '{title}' 들려 드릴게요.",
    },
    # No entendió el pedido: lo vuelve a pedir.
    "music_not_understood": {
        "es": "Me perdí. Dime el nombre de la canción y quién la canta.",
        "en": "I missed that. Tell me the song title and who sings it.",
        "fr": "J'ai mal compris. Dis-moi le titre de la chanson et qui la chante.",
        "pt": "Perdi-me. Diz-me o nome da música e quem a canta.",
        "de": "Das habe ich verpasst. Sag mir den Titel und wer das Lied singt.",
        "it": "Mi sono perso. Dimmi il titolo della canzone e chi la canta.",
        "ja": "聞き取れませんでした。曲名と歌っている人を教えてください。",
        "ru": "Я плохо расслышал. Назови песню и того, кто её поёт.",
        "zh": "我没听清。请告诉我歌名，还有谁唱的。",
        "ko": "잘 못 들었어요. 노래 제목과 가수를 다시 말씀해 주세요.",
    },
    # Estas dos van SEGUIDAS de `music_again` (la pregunta de si seguimos).
    "music_not_found": {
        "es": "Esa canción se me escapa.",
        "en": "I couldn't find that song.",
        "fr": "Cette chanson m'échappe.",
        "pt": "Essa música escapa-me.",
        "de": "Dieses Lied entgeht mir gerade.",
        "it": "Quella canzone mi sfugge.",
        "ja": "その曲は見つかりませんでした。",
        "ru": "Эта песня от меня ускользает.",
        "zh": "这首歌我找不到。",
        "ko": "그 곡은 찾지 못했어요.",
    },
    "music_error": {
        "es": "Algo falló al reproducirla.",
        "en": "Something went wrong while playing it.",
        "fr": "Un souci est survenu pendant la lecture.",
        "pt": "Algo falhou ao reproduzi-la.",
        "de": "Beim Abspielen ist etwas schiefgelaufen.",
        "it": "Qualcosa è andato storto durante la riproduzione.",
        "ja": "再生中に問題が起きました。",
        "ru": "При воспроизведении случилась ошибка.",
        "zh": "播放的时候出了点问题。",
        "ko": "재생하는 중에 문제가 생겼어요.",
    },
    # Lo dice al terminar cada canción: ¿otra, o hacemos otra cosa?
    "music_again": {
        "es": "¿Seguimos con la música, o prefieres hacer algo distinto?",
        "en": "Want to keep listening, or would you rather do something else?",
        "fr": "On continue en musique, ou tu préfères faire autre chose ?",
        "pt": "Continuamos com a música, ou preferes fazer algo diferente?",
        "de": "Weiter mit Musik, oder möchtest du etwas anderes machen?",
        "it": "Continuiamo con la musica, o preferisci fare qualcosa di diverso?",
        "ja": "音楽を続けますか？それとも、ほかのことをしますか？",
        "ru": "Продолжим слушать музыку или займёмся чем-то другим?",
        "zh": "还想继续听歌吗？还是做点别的？",
        "ko": "음악을 계속 들을까요? 혹은 다른 걸 하고 싶으세요?",
    },
    # Lo antepone a `music_again` cuando lo cortan con «oye MECH». No puede
    # ser «Claro»: en español es un sí.
    "music_ack": {
        "es": "Entendido.",
        "en": "Got it.",
        "fr": "Entendu.",
        "pt": "Entendido.",
        "de": "Verstanden.",
        "it": "Capito.",
        "ja": "わかりました。",
        "ru": "Понял.",
        "zh": "明白。",
        "ko": "알겠습니다.",
    },
    # ⚠️ Esta SÍ tiene que casar con la orden de salir (ver arriba).
    "music_off": {
        "es": "Listo, apago la música.",
        "en": "All right, I'll stop the music.",
        "fr": "Très bien, on arrête la musique.",
        "pt": "Certo, desligo a música.",
        "de": "Alles klar, ich stoppe die Musik.",
        "it": "Va bene, fermo la musica.",
        "ja": "わかりました。音楽を止めます。",
        "ru": "Хорошо, останавливаю музыку.",
        "zh": "好的，我停止音乐了。",
        "ko": "알겠습니다. 음악을 끌게요.",
    },
    # Estas dos NO se dicen: son rótulos de la pantalla mientras suena.
    "music_label": {
        "es": "Modo música",
        "en": "Music mode",
        "fr": "Mode musique",
        "pt": "Modo música",
        "de": "Musikmodus",
        "it": "Modalità musica",
        "ja": "音楽モード",
        "ru": "Режим музыки",
        "zh": "音乐模式",
        "ko": "음악 모드",
    },
    "music_preview_note": {
        "es": "Fragmento de 30 segundos · Apple Music",
        "en": "30-second preview · Apple Music",
        "fr": "Extrait de 30 secondes · Apple Music",
        "pt": "Excerto de 30 segundos · Apple Music",
        "de": "30-Sekunden-Ausschnitt · Apple Music",
        "it": "Anteprima di 30 secondi · Apple Music",
        "ja": "30秒の試聴 · Apple Music",
        "ru": "Отрывок 30 секунд · Apple Music",
        "zh": "30秒试听 · Apple Music",
        "ko": "30초 미리듣기 · Apple Music",
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
    "es": {"es": "español", "en": "inglés", "fr": "francés", "pt": "portugués",
           "de": "alemán", "it": "italiano", "ja": "japonés", "ru": "ruso",
           "zh": "chino mandarín", "ko": "coreano"},
    "en": {"es": "Spanish", "en": "English", "fr": "French", "pt": "Portuguese",
           "de": "German", "it": "Italian", "ja": "Japanese", "ru": "Russian",
           "zh": "Mandarin Chinese", "ko": "Korean"},
    "fr": {"es": "espagnol", "en": "anglais", "fr": "français", "pt": "portugais",
           "de": "allemand", "it": "italien", "ja": "japonais", "ru": "russe",
           "zh": "chinois mandarin", "ko": "coréen"},
    "pt": {"es": "espanhol", "en": "inglês", "fr": "francês", "pt": "português",
           "de": "alemão", "it": "italiano", "ja": "japonês", "ru": "russo",
           "zh": "chinês mandarim", "ko": "coreano"},
    "de": {"es": "Spanisch", "en": "Englisch", "fr": "Französisch",
           "pt": "Portugiesisch", "de": "Deutsch", "it": "Italienisch",
           "ja": "Japanisch", "ru": "Russisch", "zh": "Chinesisch",
           "ko": "Koreanisch"},
    "it": {"es": "spagnolo", "en": "inglese", "fr": "francese",
           "pt": "portoghese", "de": "tedesco", "it": "italiano",
           "ja": "giapponese", "ru": "russo", "zh": "cinese", "ko": "coreano"},
    "ja": {"es": "スペイン語", "en": "英語", "fr": "フランス語", "pt": "ポルトガル語",
           "de": "ドイツ語", "it": "イタリア語", "ja": "日本語", "ru": "ロシア語",
           "zh": "中国語", "ko": "韓国語"},
    "ru": {"es": "испанский", "en": "английский", "fr": "французский",
           "pt": "португальский", "de": "немецкий", "it": "итальянский",
           "ja": "японский", "ru": "русский", "zh": "китайский",
           "ko": "корейский"},
    "zh": {"es": "西班牙语", "en": "英语", "fr": "法语", "pt": "葡萄牙语",
           "de": "德语", "it": "意大利语", "ja": "日语", "ru": "俄语",
           "zh": "中文", "ko": "韩语"},
    # En coreano todos acaban en «어», que es lo que permite decir
    # «{src}와 {dst}» en `translate_ready` sin mirar la última letra.
    "ko": {"es": "스페인어", "en": "영어", "fr": "프랑스어", "pt": "포르투갈어",
           "de": "독일어", "it": "이탈리아어", "ja": "일본어", "ru": "러시아어",
           "zh": "중국어", "ko": "한국어"},
}

# Cómo puede llamarse cada idioma en una frase hablada, en cualquiera de los
# nueve. Se compara con el matcher tolerante de `voice_phrases`, así que no
# hacen falta todas las variantes ortográficas — pero sí las que NO están a
# una letra de distancia ("francais" vs "frances", "portugais" vs "portugues").
#
# En ruso van el nominativo y el genitivo ("русский" / "русского"), porque la
# frase natural es «с русского на испанский» y el genitivo queda a tres letras
# del nominativo. En japonés y chino el nombre se busca DENTRO de lo oído
# («日本語からスペイン語に» va todo pegado); el chino lleva las formas
# simplificada y tradicional.
_LANGUAGE_WORDS: dict[str, tuple[str, ...]] = {
    "es": ("espanol", "espanhol", "castellano", "spanish", "espagnol",
           "spanisch", "spagnolo", "испанский", "испанского",
           "スペイン語", "西班牙语", "西班牙語", "西班牙文", "西语", "西語",
           "스페인어"),
    "en": ("ingles", "english", "anglais", "englisch", "inglese",
           "английский", "английского", "英語", "英语", "英文", "영어"),
    "fr": ("frances", "francais", "french", "französisch", "francese",
           "французский", "французского", "フランス語", "法语", "法語", "法文",
           "프랑스어"),
    "pt": ("portugues", "portugais", "portuguese", "brasileiro",
           "portugiesisch", "portoghese", "португальский", "португальского",
           "ポルトガル語", "葡萄牙语", "葡萄牙語", "葡萄牙文", "葡语", "葡語",
           "포르투갈어"),
    "de": ("aleman", "alemao", "german", "allemand", "deutsch", "tedesco",
           "немецкий", "немецкого", "ドイツ語", "德语", "德語", "德文", "독일어"),
    "it": ("italiano", "italian", "italien", "italienisch",
           "итальянский", "итальянского", "イタリア語",
           "意大利语", "意大利語", "義大利語", "意大利文", "義大利文",
           "이탈리아어"),
    "ja": ("japones", "japanese", "japonais", "japanisch", "giapponese",
           "японский", "японского", "日本語", "日语", "日語", "日文", "일본어"),
    "ru": ("ruso", "russian", "russe", "russisch", "russo",
           "русский", "русского", "ロシア語", "俄语", "俄語", "俄文", "러시아어"),
    "zh": ("chino", "mandarin", "chinese", "chinois", "chinesisch", "cinese",
           "китайский", "китайского", "中国語", "中文", "汉语", "漢語",
           "普通话", "普通話", "国语", "國語", "华语", "華語", "중국어"),
    "ko": ("coreano", "korean", "coreen", "koreanisch",
           "корейский", "корейского", "韓国語", "韩语", "韓語", "韩文", "韓文",
           "한국어", "한국말"),
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
    "de": ("ALEMÁN", "alemán natural y fluido", "Deutsch"),
    "it": ("ITALIANO", "italiano natural y fluido", "italiano"),
    "ja": ("JAPONÉS", "japonés natural y fluido, en forma cortés (です/ます)",
           "日本語"),
    "ru": ("RUSO", "ruso natural y fluido", "русский"),
    # Simplificados a propósito: es lo que lee la mayoría y lo que casa con
    # el `initial_prompt` de Whisper para este idioma.
    "zh": ("CHINO MANDARÍN",
           "chino mandarín natural y fluido, en caracteres SIMPLIFICADOS",
           "中文"),
    "ko": ("COREANO", "coreano natural y fluido, en forma cortés (해요체)",
           "한국어"),
}


def writing_style(code: str | None = None) -> str:
    """Cómo se le pide a Claude que escriba en ese idioma, en una frase.

    Es la misma indicación que lleva la narración («japonés en forma cortés»,
    «chino en caracteres SIMPLIFICADOS»), para lo que se le pide APARTE del
    prompt grande: las preguntas de la trivia. Así el juego sale escrito
    igual que la obra que el visitante acaba de oír.
    """
    datos = _LLM_DIRECTIVES.get(code or _current)
    return datos[1] if datos else "español neutro"


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
            # El título no es solo para el log: la trivia lo PROYECTA
            # («Sobre: …»), así que tiene que salir en el mismo idioma.
            f"- El `title` del plan también va en {propio}.\n"
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
