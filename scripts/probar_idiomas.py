"""Comprueba los idiomas de MECH sin micrófono, sin hardware y sin claves.

Por qué existe: cada idioma nuevo mete un centenar de frases en un matcher
que perdona errores de letra, y lo que falla no avisa — una frase alemana que
se parece a una inglesa despierta a MECH en el idioma equivocado, y una orden
italiana que se parece a una española lo hace girar al revés. Aquí se miden
las dos caras:

  - que cada idioma se entienda (despertar, órdenes, números, traductor,
    trivia), escrito como lo escribe Whisper — también en japonés, ruso y
    chino, donde el nombre «MECH» sale como suena («メック», «мек», «麦克»);
  - que NO se pisen entre ellos ni con lo que se dice normalmente en el stand.

    python scripts/probar_idiomas.py

Sale 1 si algo falla. Correrlo al tocar las listas `VOICE_*_PHRASES_*` de
`backend/config.py`, `backend/lang.py` o el matcher de `voice_phrases.py`.

⚠️ Esto comprueba el TEXTO. No sustituye a probarlo hablando: cómo transcribe
Whisper cada idioma en la Pi solo se ve con el micrófono de verdad.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))

import config  # noqa: E402
import lang  # noqa: E402
import subtitles  # noqa: E402
import voice_phrases as vp  # noqa: E402

# Aquí se miden las colisiones con las listas de TODOS los idiomas juntas,
# así que se apaga la regla de «cada comando en el idioma del despertar»
# (oct 2026): juntas es el peor caso, y es lo que vale si alguien la apaga en
# Ajustes. La regla en sí la mide `scripts/probar_comandos_idioma.py`.
config.VOICE_STRICT_LANGUAGE = False

NUEVOS = ("de", "it", "ja", "ru", "zh", "ko")
SUFIJO = {"en": "_EN", "fr": "_FR", "pt": "_PT", "de": "_DE", "it": "_IT",
          "ja": "_JA", "ru": "_RU", "zh": "_ZH", "ko": "_KO"}

fallos = 0


def comprobar(ok: bool, texto: str, detalle: str = "") -> None:
    global fallos
    if not ok:
        fallos += 1
    print(f"  {'ok ' if ok else 'MAL'}  {texto}" + (f"   {detalle}" if detalle and not ok else ""))


def movimiento(texto: str) -> str | None:
    """Lo que haría `mech_app.handle_movement_command`, en el MISMO orden."""
    if vp.is_look_outward(texto):
        return "afuera"
    if vp.is_back_to_projection(texto):
        return "proyectar"
    if vp.is_advance(texto) or vp.is_retreat(texto):
        return "retroceder" if vp.is_retreat(texto) else "avanzar"
    if vp.is_play_marketing(texto):
        return "marketing"
    return None


# ---------------------------------------------------------------------------
# 1. Despertar: la frase decide el idioma
# ---------------------------------------------------------------------------
DESPERTAR = [
    # Los de siempre no pueden haber cambiado.
    ("ok MECH", "es"), ("despierta MECH", "es"), ("wake up MECH", "en"),
    ("bonjour MECH", "fr"), ("bom dia MECH", "pt"),
    # Alemán
    ("Guten Tag, MECH!", "de"), ("Guten Morgen Mech", "de"),
    ("Wach auf, Mech", "de"), ("Aufwachen, MECH", "de"),
    # Italiano
    ("Ciao MECH", "it"), ("Buongiorno, Mech!", "it"), ("Buon giorno Mech", "it"),
    ("Svegliati, MECH", "it"), ("Salve Mech", "it"),
    # Japonés: con el nombre en letras latinas y como lo escribe Whisper.
    ("こんにちは、MECH", "ja"), ("こんにちはメック", "ja"), ("おはようメッチ", "ja"),
    ("起きて、MECH", "ja"), ("おきてメック", "ja"), ("こんにちは ＭＥＣＨ", "ja"),
    # Ruso
    ("Привет, MECH", "ru"), ("Привет, Мек!", "ru"), ("привет мех", "ru"),
    ("Проснись, Мэк", "ru"), ("Добрый день, MECH", "ru"),
    ("Здравствуйте, Мек", "ru"),
    # Mandarín: simplificado y tradicional.
    ("你好，MECH", "zh"), ("你好麦克", "zh"), ("你好,麥克", "zh"),
    ("早上好 MECH", "zh"), ("醒醒，麦克", "zh"), ("醒來 MECH", "zh"),
    # Coreano: con el nombre en letras latinas y como lo escribe Whisper.
    ("안녕, MECH", "ko"), ("안녕하세요 멕", "ko"), ("안녕 메크", "ko"),
    ("일어나, 맥!", "ko"), ("좋은 아침이야 MECH", "ko"), ("일어나세요, MECH", "ko"),
]

# Nada de esto puede despertar a MECH (en ningún idioma).
NO_DESPERTAR = [
    # «hello MECH» es lo primero que dice un visitante que habla inglés. Con
    # "hallo MECH" en la lista alemana despertaba EN ALEMÁN.
    "hello MECH", "Hello, MECH!", "hi MECH",
    "hola MECH", "chao MECH", "gracias MECH", "watch MECH", "let's watch MECH",
    "el proyecto se llama MECH", "buena nota, MECH", "un momento, MECH",
    # Un saludo SIN el nombre no es una orden.
    "Guten Tag", "ciao", "buongiorno", "こんにちは", "привет", "你好",
    "こんにちは、元気ですか", "你好，请问这是什么",
    "안녕하세요", "안녕하세요, 이건 뭐예요?",
    # El nombre coreano de UNA sílaba («멕», «맥») no puede salir de dentro de
    # otra palabra: México y la cerveza no son MECH.
    "안녕하세요, 멕시코에서 왔어요", "안녕, 맥주 한 잔 주세요",
]

# ---------------------------------------------------------------------------
# 2. Órdenes de cada idioma nuevo, escritas como las escribiría Whisper
# ---------------------------------------------------------------------------
# (texto, comprobación, nombre de la comprobación)
ORDENES = {
    "de": [
        ("Hör auf zuzuhören", vp.is_sleep_any, "dormir"),
        ("Gute Nacht, MECH", vp.is_sleep_any, "dormir"),
        ("Geh schlafen", vp.is_sleep_any, "dormir"),
        ("Entschuldigung, MECH", vp.is_interrupt, "interrumpir"),
        ("Warte, MECH", vp.is_interrupt, "interrumpir"),
        ("Zeig Marketing", vp.is_play_marketing, "marketing"),
        ("Übersetze, MECH", vp.is_translate, "traducir"),
        ("Hör auf zu übersetzen", vp.is_translate_stop, "dejar de traducir"),
        ("Lass uns ein Quiz spielen", vp.is_trivia, "trivia"),
        ("Quiz beenden", vp.is_trivia_stop, "salir de la trivia"),
        ("Ja", vp.is_yes, "sí"), ("Na klar", vp.is_yes, "sí"),
        ("Gerne", vp.is_yes, "sí"),
        ("Nein danke", vp.is_no, "no"), ("Lieber nicht", vp.is_no, "no"),
    ],
    "it": [
        ("Smetti di ascoltare", vp.is_sleep_any, "dormir"),
        ("Buonanotte, MECH", vp.is_sleep_any, "dormir"),
        ("Vai a dormire", vp.is_sleep_any, "dormir"),
        ("Scusa, MECH", vp.is_interrupt, "interrumpir"),
        ("Ehi MECH", vp.is_interrupt, "interrumpir"),
        ("Mostra il marketing", vp.is_play_marketing, "marketing"),
        ("Traduci, MECH", vp.is_translate, "traducir"),
        ("Smetti di tradurre", vp.is_translate_stop, "dejar de traducir"),
        ("Facciamo un quiz", vp.is_trivia, "trivia"),
        ("Basta quiz", vp.is_trivia_stop, "salir de la trivia"),
        ("Sì", vp.is_yes, "sí"), ("Certo", vp.is_yes, "sí"),
        ("Va bene", vp.is_yes, "sí"),
        ("No grazie", vp.is_no, "no"), ("Non ora", vp.is_no, "no"),
    ],
    "ja": [
        ("聞くのをやめて", vp.is_sleep_any, "dormir"),
        ("おやすみ、MECH", vp.is_sleep_any, "dormir"),
        ("おやすみメック", vp.is_sleep_any, "dormir"),
        ("ねえ、MECH", vp.is_interrupt, "interrumpir"),
        ("すみません、メック", vp.is_interrupt, "interrumpir"),
        ("マーケティングを再生して", vp.is_play_marketing, "marketing"),
        ("マーケティングのビデオを見せて", vp.is_play_marketing, "marketing"),
        ("翻訳して、MECH", vp.is_translate, "traducir"),
        ("翻訳モード", vp.is_translate, "traducir"),
        ("翻訳をやめて", vp.is_translate_stop, "dejar de traducir"),
        ("クイズをしよう", vp.is_trivia, "trivia"),
        ("クイズを始めてください", vp.is_trivia, "trivia"),
        ("クイズをやめて", vp.is_trivia_stop, "salir de la trivia"),
        ("はい", vp.is_yes, "sí"), ("はい、やります", vp.is_yes, "sí"),
        ("お願いします", vp.is_yes, "sí"),
        ("いいえ", vp.is_no, "no"), ("結構です", vp.is_no, "no"),
    ],
    "ru": [
        ("Перестань слушать", vp.is_sleep_any, "dormir"),
        ("Спокойной ночи, MECH", vp.is_sleep_any, "dormir"),
        ("Иди спать", vp.is_sleep_any, "dormir"),
        ("Эй, MECH", vp.is_interrupt, "interrumpir"),
        ("Подожди, Мек", vp.is_interrupt, "interrumpir"),
        ("Покажи маркетинг", vp.is_play_marketing, "marketing"),
        ("Переведи, MECH", vp.is_translate, "traducir"),
        ("Режим переводчика", vp.is_translate, "traducir"),
        ("Хватит переводить", vp.is_translate_stop, "dejar de traducir"),
        ("Давай сыграем в викторину", vp.is_trivia, "trivia"),
        ("Останови викторину", vp.is_trivia_stop, "salir de la trivia"),
        ("Да", vp.is_yes, "sí"), ("Конечно", vp.is_yes, "sí"),
        ("Давай", vp.is_yes, "sí"),
        ("Нет", vp.is_no, "no"), ("Нет, спасибо", vp.is_no, "no"),
        ("Не хочу", vp.is_no, "no"),
    ],
    "zh": [
        ("别听了", vp.is_sleep_any, "dormir"),
        ("晚安，MECH", vp.is_sleep_any, "dormir"),
        ("晚安麦克", vp.is_sleep_any, "dormir"),
        ("嘿，MECH", vp.is_interrupt, "interrumpir"),
        ("等一下，麦克", vp.is_interrupt, "interrumpir"),
        ("播放营销视频", vp.is_play_marketing, "marketing"),
        ("播放宣传片", vp.is_play_marketing, "marketing"),
        ("翻译，MECH", vp.is_translate, "traducir"),
        ("开始翻译", vp.is_translate, "traducir"),
        ("停止翻译", vp.is_translate_stop, "dejar de traducir"),
        ("我们玩问答游戏吧", vp.is_trivia, "trivia"),
        ("开始问答", vp.is_trivia, "trivia"),
        ("不玩了", vp.is_trivia_stop, "salir de la trivia"),
        ("好", vp.is_yes, "sí"), ("好的", vp.is_yes, "sí"),
        ("是的", vp.is_yes, "sí"), ("可以", vp.is_yes, "sí"),
        ("那好吧", vp.is_yes, "sí"),
        ("不", vp.is_no, "no"), ("不要", vp.is_no, "no"),
        ("不用了", vp.is_no, "no"),
    ],
    "ko": [
        ("그만 들어", vp.is_sleep_any, "dormir"),
        ("잘 자, MECH", vp.is_sleep_any, "dormir"),
        ("잘자 멕", vp.is_sleep_any, "dormir"),
        ("이제 듣지 마", vp.is_sleep_any, "dormir"),
        ("저기, MECH", vp.is_interrupt, "interrumpir"),
        ("잠깐만 멕", vp.is_interrupt, "interrumpir"),
        ("실례합니다, MECH", vp.is_interrupt, "interrumpir"),
        ("마케팅 영상 재생해 줘", vp.is_play_marketing, "marketing"),
        ("마케팅을 보여줘", vp.is_play_marketing, "marketing"),
        ("번역해 줘, MECH", vp.is_translate, "traducir"),
        ("통역해줘 멕", vp.is_translate, "traducir"),
        ("번역 모드", vp.is_translate, "traducir"),
        ("번역 그만", vp.is_translate_stop, "dejar de traducir"),
        ("번역 그만해, MECH", vp.is_translate_stop, "dejar de traducir"),
        ("퀴즈 하자", vp.is_trivia, "trivia"),
        ("퀴즈 풀래요", vp.is_trivia, "trivia"),
        ("퀴즈 그만", vp.is_trivia_stop, "salir de la trivia"),
        ("네", vp.is_yes, "sí"), ("네, 좋아요", vp.is_yes, "sí"),
        ("응", vp.is_yes, "sí"), ("할게요", vp.is_yes, "sí"),
        ("아니요", vp.is_no, "no"), ("아니요, 괜찮아요", vp.is_no, "no"),
        ("안 할래요", vp.is_no, "no"),
    ],
}

# Movimiento: (texto, lo que tiene que hacer, segundos que pide o None)
MOVIMIENTO = [
    # Alemán
    ("Geh vorwärts", "avanzar", None),
    ("Fahr zehn Sekunden vorwärts", "avanzar", 10),
    ("Rückwärts", "retroceder", None),
    ("Geh zurück", "retroceder", None),
    ("Schau nach draußen", "afuera", None),
    ("Schau nach draussen", "afuera", None),
    ("Dreh dich um", "afuera", None),
    ("Zurück zur Projektion", "proyectar", None),
    # «geh ZURÜCK zur Projektion» lleva dentro la orden de retroceder.
    ("Geh zurück zur Projektion", "proyectar", None),
    # Italiano
    ("Vai avanti", "avanzar", None),
    ("Avanti cinque secondi", "avanzar", 5),
    ("Indietro", "retroceder", None),
    ("Torna indietro", "retroceder", None),
    ("Guarda fuori", "afuera", None),
    ("Girati", "afuera", None),
    ("Saluta il pubblico", "afuera", None),
    ("Torna a proiettare", "proyectar", None),
    ("Torna alla proiezione", "proyectar", None),
    # Japonés
    ("前に進んで", "avanzar", None),
    ("10秒前に進んで", "avanzar", 10),
    ("十秒前に進んで", "avanzar", 10),
    ("前進", "avanzar", None),
    ("後ろに下がって", "retroceder", None),
    ("下がって", "retroceder", None),
    ("外を見て", "afuera", None),
    ("振り向いて", "afuera", None),
    ("後ろを向いて", "afuera", None),
    ("投影に戻って", "proyectar", None),
    ("スクリーンを見て", "proyectar", None),
    # Ruso (Whisper escribe "вперед" sin la ё casi siempre)
    ("Иди вперёд", "avanzar", None),
    ("Вперед на двадцать секунд", "avanzar", 20),
    ("Назад", "retroceder", None),
    ("Иди назад", "retroceder", None),
    ("Посмотри наружу", "afuera", None),
    ("Повернись", "afuera", None),
    ("Вернись к проекции", "proyectar", None),
    ("Посмотри на экран", "proyectar", None),
    # Mandarín
    ("前进", "avanzar", None),
    ("往前走十秒", "avanzar", 10),
    ("前进15秒", "avanzar", 15),
    ("往前走两秒", "avanzar", 2),
    ("后退", "retroceder", None),
    ("往後退", "retroceder", None),
    ("向外看", "afuera", None),
    ("转身", "afuera", None),
    ("转过去", "afuera", None),
    ("回去投影", "proyectar", None),
    ("看屏幕", "proyectar", None),
    ("转回来", "proyectar", None),
    # Coreano. Whisper junta o separa la terminación a su antojo.
    ("앞으로 가", "avanzar", None),
    ("앞으로 가 줘", "avanzar", None),
    ("앞으로 가줘", "avanzar", None),
    ("10초 동안 앞으로 가", "avanzar", 10),
    ("앞으로 십 초 가", "avanzar", 10),
    ("이십 초 뒤로 가", "retroceder", 20),
    ("전진해", "avanzar", None),
    ("뒤로 가", "retroceder", None),
    ("후진", "retroceder", None),
    ("밖을 봐", "afuera", None),
    ("바깥을 봐 줘", "afuera", None),
    ("뒤돌아봐", "afuera", None),
    ("사람들에게 인사해", "afuera", None),
    ("투영으로 돌아가", "proyectar", None),
    ("제자리로 돌아가 줘", "proyectar", None),
    ("화면을 봐", "proyectar", None),
    ("스크린을 보세요", "proyectar", None),
    ("마케팅 재생", "marketing", None),
    # Los de antes, que no se pueden haber movido.
    ("avanza diez segundos", "avanzar", 10),
    ("retrocede cinco segundos", "retroceder", 5),
    ("mira hacia afuera", "afuera", None),
    ("regresa a proyectar", "proyectar", None),
    ("go back to projecting", "proyectar", None),
    ("proyecta marketing", "marketing", None),
    # ⚠️ El italiano "voltati" caía en el español "voltea": esta orden hacía
    # girar a MECH hacia AFUERA.
    ("voltea hacia la proyección", "proyectar", None),
    ("mira hacia la proyección", "proyectar", None),
]

# (texto, comprobación que tiene que dar FALSO, por qué)
NO_CONFUNDIR = [
    ("buena nota, MECH", vp.is_sleep_any, "«buona notte MECH» lo dormía"),
    ("avanza dos segundos, MECH", vp.is_sleep_any, "el «dors» francés"),
    ("你好", vp.is_yes, "«hola» en chino lleva dentro el carácter de «sí»"),
    ("你好，给我讲讲堂吉诃德", vp.is_yes, "una petición no es un sí"),
    ("はい、やります", vp.is_no, "«sí, juego» no es un no"),
    ("好的", vp.is_no, "«vale» no es un no"),
    ("¿cómo se dice hola en alemán?", vp.is_translate, "pregunta normal"),
    ("cuéntame algo de Italia", vp.is_play_marketing, "pregunta normal"),
    ("el proyecto se llama MECH", vp.is_interrupt, "frase normal del stand"),
    ("qué avanzada tecnología", vp.is_advance, "frase normal del stand"),
    # Coreano: «가» es una orden ("ve") y además la partícula más común.
    ("앞으로 인공지능이 가져올 변화는 뭐야?", vp.is_advance, "«가» dentro de otra palabra"),
    ("로봇이 초록색이야", vp.extract_seconds, "«이 초» no son dos segundos"),
    ("이 단어는 어떻게 번역해?", vp.is_translate, "pregunta normal"),
    ("마케팅이 뭐야?", vp.is_play_marketing, "pregunta normal"),
    ("돈키호테에 대해 들려줘", vp.is_sleep_any, "pedir una obra no lo duerme"),
    ("MECH는 로봇입니다", vp.is_interrupt, "frase normal del stand"),
    ("아니요", vp.is_yes, "«no» no es un sí"),
    ("네", vp.is_no, "«sí» no es un no"),
]

# ---------------------------------------------------------------------------
# 3. Traductor: el par de idiomas
# ---------------------------------------------------------------------------
PARES = [
    ("de español a francés", ("es", "fr")),
    ("de español a japonés", ("es", "ja")),
    ("del alemán al italiano", ("de", "it")),
    ("al chino", (None, "zh")),
    ("from Russian to English", ("ru", "en")),
    ("von Deutsch nach Spanisch", ("de", "es")),
    ("dall'italiano allo spagnolo", ("it", "es")),
    ("с русского на испанский", ("ru", "es")),
    ("日本語からスペイン語に", ("ja", "es")),
    ("英語から日本語", ("en", "ja")),
    ("从中文到西班牙语", ("zh", "es")),
    ("把英文翻译成中文", ("en", "zh")),
    ("한국어에서 스페인어로", ("ko", "es")),
    ("영어를 한국어로 번역해 줘", ("en", "ko")),
    ("일본어로", (None, "ja")),
    ("de coreano a español", ("ko", "es")),
    ("from Korean to English", ("ko", "en")),
    ("du coréen au français", ("ko", "fr")),
    ("韓国語から日本語に", ("ko", "ja")),
    ("从韩语到中文", ("ko", "zh")),
    ("с корейского на русский", ("ko", "ru")),
    ("cuéntame de Don Quijote", (None, None)),
]

# ---------------------------------------------------------------------------
# 4. Trivia en los idiomas nuevos
# ---------------------------------------------------------------------------
ANOS = ["1605", "1700", "1492"]
ANOS_ZH = ["1605年", "1700年", "1492年"]
NOMBRES_ZH = ["塞万提斯", "桑丘·潘沙", "杜尔西内亚"]
NOMBRES_JA = ["セルバンテス", "サンチョ・パンサ", "ドゥルシネア"]
NOMBRES_KO = ["세르반테스", "산초 판사", "둘시네아"]

RESPUESTAS = [
    (ANOS, "die B", 1), (ANOS, "die zweite", 1), (ANOS, "Antwort C", 2),
    (ANOS, "ich nehme A", 0),
    (ANOS, "la seconda", 1), (ANOS, "la terza", 2), (ANOS, "la bi", 1),
    # «secondo me» es "en mi opinión", no "la segunda".
    (ANOS, "secondo me la C", 2),
    (ANOS, "вторая", 1), (ANOS, "третий", 2), (ANOS, "ответ Б", 1),
    (ANOS, "А", 0),  # la A en cirílico
    (ANOS, "Bです", 1), (ANOS, "答えはA", 0), (ANOS, "二番目", 1),
    (ANOS, "2番", 1), (ANOS, "ビー", 1),
    (ANOS, "我选B", 1), (ANOS, "第二个", 1), (ANOS, "选第三个", 2),
    (ANOS_ZH, "1605年", 0), (ANOS_ZH, "是1492年", 2),
    (NOMBRES_ZH, "塞万提斯", 0), (NOMBRES_ZH, "我觉得是桑丘潘沙", 1),
    (NOMBRES_JA, "セルバンテス", 0), (NOMBRES_JA, "サンチョパンサです", 1),
    # No lo sabe: no puede contar como una opción.
    (ANOS, "weiß nicht", None), (ANOS, "keine Ahnung", None),
    (ANOS, "non lo so", None), (ANOS, "не знаю", None),
    (ANOS, "わかりません", None), (ANOS, "不知道", None),
    (ANOS, "えーと", None),
    # Coreano: la letra (también dicha en hangul), el número, el orden y el
    # texto, con y sin la terminación de cortesía pegada.
    (ANOS, "B요", 1), (ANOS, "C입니다", 2), (ANOS, "비", 1), (ANOS, "에이요", 0),
    (ANOS, "씨입니다", 2), (ANOS, "1번", 0), (ANOS, "2번이요", 1),
    (ANOS, "첫 번째", 0), (ANOS, "두 번째요", 1), (ANOS, "세번째", 2),
    (ANOS, "정답은 B", 1), (ANOS, "1605년", 0), (ANOS, "1492년이요", 2),
    (NOMBRES_KO, "세르반테스", 0), (NOMBRES_KO, "산초 판사입니다", 1),
    (NOMBRES_KO, "산초판사", 1), (NOMBRES_KO, "둘시네아요", 2),
    (ANOS, "모르겠어요", None), (ANOS, "잘 모르겠습니다", None),
    (ANOS, "몰라요", None), (ANOS, "음", None),
]

# ---------------------------------------------------------------------------
# 5. Subtítulos: partir líneas en idiomas sin espacios
# ---------------------------------------------------------------------------
GUIONES = {
    "es": ("En un lugar de la Mancha, de cuyo nombre no quiero acordarme, no ha "
           "mucho tiempo que vivía un hidalgo de los de lanza en astillero, "
           "adarga antigua, rocín flaco y galgo corredor. Leía tantos libros de "
           "caballerías que perdió el juicio."),
    "ru": ("В некоем селе ламанчском, которого название у меня нет охоты "
           "припоминать, не так давно жил-был один из тех идальго, чьё "
           "имущество заключается в фамильном копье, древнем щите, тощей кляче "
           "и борзой собаке. Он читал столько рыцарских романов, что лишился "
           "рассудка."),
    "ja": ("ラ・マンチャのある村に、名前は思い出したくありませんが、少し前まで一人の郷士が"
           "住んでいました。槍掛けに槍、古い盾、やせた馬、そして足の速い猟犬を持っていました。"
           "彼は騎士道物語を読みすぎて、とうとう正気を失ってしまったのです。"),
    "zh": ("在拉曼查的一个村庄里，村名我不想提起，不久以前住着一位绅士。他有一支长矛、"
           "一面旧盾牌、一匹瘦马和一只跑得很快的猎狗。他读了太多的骑士小说，最后失去了理智，"
           "决定自己也去当一名游侠骑士，周游世界，行侠仗义。"),
    # Coreano: letras anchas como las de arriba, pero CON espacios — las
    # líneas se cortan entre palabras, nunca por la mitad de una.
    "ko": ("라만차의 어느 마을에, 그 이름은 떠올리고 싶지 않지만, 그리 오래되지 않은 옛날에 "
           "한 시골 귀족이 살고 있었습니다. 그는 창걸이에 걸린 창과 낡은 방패, 여윈 말과 "
           "날쌘 사냥개를 가지고 있었습니다. 기사 이야기를 너무 많이 읽은 나머지 마침내 "
           "제정신을 잃고 말았습니다."),
}


def main() -> int:
    print("── DESPERTAR: la frase decide el idioma ──")
    for texto, esperado in DESPERTAR:
        sale = vp.wake_language(texto)
        comprobar(sale == esperado, f"{texto:<28} → {sale}", f"(esperado {esperado})")

    print("\n── NO DESPERTAR ──")
    for texto in NO_DESPERTAR:
        sale = vp.wake_language(texto)
        comprobar(sale is None, f"{texto:<32} → {sale}", "(esperado None)")

    for code in NUEVOS:
        print(f"\n── ÓRDENES en {lang.label(code)} ──")
        for texto, prueba, nombre in ORDENES[code]:
            comprobar(bool(prueba(texto)), f"{texto:<30} → {nombre}")

    print("\n── MOVIMIENTO (en el orden en que lo decide mech_app) ──")
    for texto, esperado, segundos in MOVIMIENTO:
        sale = movimiento(texto)
        seg = vp.extract_seconds(texto) if esperado in ("avanzar", "retroceder") else None
        ok = sale == esperado and (segundos is None or seg == segundos) \
            and not (segundos is None and seg and esperado in ("avanzar", "retroceder"))
        comprobar(ok, f"{texto:<30} → {sale}" + (f" {seg:g} s" if seg else ""),
                  f"(esperado {esperado}" + (f" {segundos} s)" if segundos else ")"))

    print("\n── NO CONFUNDIR ──")
    for texto, prueba, motivo in NO_CONFUNDIR:
        comprobar(not prueba(texto), f"{texto:<34} ✗ {prueba.__name__}", f"({motivo})")

    print("\n── TRADUCTOR: el par de idiomas ──")
    for texto, esperado in PARES:
        sale = vp.extract_language_pair(texto)
        comprobar(sale == esperado, f"{texto:<30} → {sale}", f"(esperado {esperado})")

    print("\n── TRADUCTOR: salir no se confunde con entrar ──")
    # `mech_app` mira «deja de traducir» ANTES que «traduce MECH». Para que
    # eso no rompa nada, ninguna frase de ENTRAR puede leerse como salir; y
    # las de SALIR tienen que seguir siéndolo con el nombre pegado («deja de
    # traducir, MECH» casa también con «traduce MECH»: por eso va primero).
    for code in lang.SUPPORTED:
        suf = SUFIJO.get(code, "")
        malas = []
        for frase in getattr(config, "VOICE_TRANSLATE_PHRASES" + suf):
            if vp.is_translate_stop(frase):
                malas.append(f"entrar «{frase}» se lee como salir")
        for frase in getattr(config, "VOICE_TRANSLATE_STOP_PHRASES" + suf):
            for variante in (frase, frase + ", MECH", "MECH, " + frase):
                if not vp.is_translate_stop(variante):
                    malas.append(f"salir «{variante}» no se reconoce")
        # La confirmación que dice MECH tiene que casar con la orden de
        # salir: así su propio eco se ignora en silencio (ver lang.py).
        if not vp.is_translate_stop(lang.say("translate_off", code)):
            malas.append(f"la confirmación «{lang.say('translate_off', code)}» "
                         "no casa con la orden de salir: su eco iría a Claude")
        comprobar(not malas, f"{lang.label(code):<10} entrar / salir / eco", "; ".join(malas))

    print("\n── TRIVIA en los idiomas nuevos ──")
    for opciones, texto, esperado in RESPUESTAS:
        sale = vp.parse_answer(texto, opciones)
        comprobar(sale == esperado, f"{texto:<24} → {sale}", f"(esperado {esperado})")

    print("\n── CADA FRASE DE config SE RECONOCE A SÍ MISMA ──")
    # Si una frase de las listas no pasa su propia comprobación, es que el
    # matcher no sabe leerla (un carácter que se pierde al normalizar…).
    propias = {
        "VOICE_SLEEP_PHRASES": vp.is_sleep_any,
        "VOICE_INTERRUPT_PHRASES": vp.is_interrupt,
        "VOICE_ADVANCE_PHRASES": vp.is_advance,
        "VOICE_RETREAT_PHRASES": vp.is_retreat,
        "VOICE_OUTWARD_PHRASES": vp.is_look_outward,
        "VOICE_PROJECT_PHRASES": vp.is_back_to_projection,
        "VOICE_MARKETING_PHRASES": vp.is_play_marketing,
        "VOICE_TRANSLATE_PHRASES": vp.is_translate,
        "VOICE_TRANSLATE_STOP_PHRASES": vp.is_translate_stop,
        "VOICE_TRIVIA_PHRASES": vp.is_trivia,
        "VOICE_TRIVIA_STOP_PHRASES": vp.is_trivia_stop,
        "VOICE_YES_PHRASES": vp.is_yes,
        "VOICE_NO_PHRASES": vp.is_no,
    }
    for code in NUEVOS:
        malas = []
        total = 0
        for frase in getattr(config, "VOICE_WAKE_PHRASES" + SUFIJO[code]):
            total += 1
            if vp.wake_language(frase) != code:
                malas.append(f"despertar «{frase}» → {vp.wake_language(frase)}")
            # Una frase de despertar no puede dormirlo ni moverlo.
            if vp.is_sleep_any(frase) or movimiento(frase):
                malas.append(f"despertar «{frase}» también duerme o mueve")
        for base, prueba in propias.items():
            for frase in getattr(config, base + SUFIJO[code]):
                total += 1
                if not prueba(frase):
                    malas.append(f"{base} «{frase}»")
                if base != "VOICE_SLEEP_PHRASES" and vp.is_sleep_any(frase):
                    malas.append(f"{base} «{frase}» lo duerme")
                if vp.wake_language(frase):
                    malas.append(f"{base} «{frase}» lo despierta")
        # Salir del giro no puede leerse como girar hacia afuera, ni al revés.
        for frase in getattr(config, "VOICE_PROJECT_PHRASES" + SUFIJO[code]):
            if movimiento(frase) != "proyectar":
                malas.append(f"«{frase}» → {movimiento(frase)} (esperado proyectar)")
        for frase in getattr(config, "VOICE_OUTWARD_PHRASES" + SUFIJO[code]):
            if movimiento(frase) != "afuera":
                malas.append(f"«{frase}» → {movimiento(frase)} (esperado afuera)")
        comprobar(not malas, f"{lang.label(code):<10} {total} frases", "; ".join(malas))

    print("\n── ECO: lo que DICE MECH no puede ser una orden ──")
    # Justo después de hablar se abre el micrófono. Si la frase que acaba de
    # decir casa con una orden, MECH se obedece a sí mismo.
    dichos = ast.literal_eval(
        re.search(r"^_SAY = (\{.*?^\})", (RAIZ / "backend" / "maneuvers.py")
                  .read_text(encoding="utf-8"), re.S | re.M).group(1)
    )
    for code in NUEVOS:
        malas = []
        frases = [(k, v[code]) for k, v in lang._PHRASES.items()]
        frases += [("giro:" + k, v.get(code, "")) for k, v in dichos.items()]
        for clave, frase in frases:
            if not frase:
                malas.append(f"falta {clave}")
                continue
            if vp.wake_language(frase):
                malas.append(f"{clave} despierta")
            if vp.is_sleep_any(frase):
                malas.append(f"{clave} duerme")
            if movimiento(frase):
                malas.append(f"{clave} mueve ({movimiento(frase)})")
            if clave == "trivia_offer" and vp.is_trivia(frase):
                malas.append("el ofrecimiento arranca la trivia")
        comprobar(not malas, f"{lang.label(code):<10} {len(frases)} frases", "; ".join(malas))

    print("\n── SUBTÍTULOS: líneas que caben, sin perder texto ──")
    for code, guion in GUIONES.items():
        lineas = subtitles.split(guion)
        anchos = [subtitles._ancho(t) for _, t in lineas]
        cabe = max(anchos) <= subtitles.MAX_CHARS
        entero = "".join(t for _, t in lineas).replace(" ", "") == guion.replace(" ", "")
        en_sitio = all(guion[o:o + len(t)] == t for o, t in lineas)
        empieza_bien = all(t[0] not in subtitles._NO_ABRE for _, t in lineas)
        # Donde hay espacios (todos menos japonés y chino) ninguna palabra
        # puede quedar partida entre dos líneas. Importa en coreano: sus
        # letras son anchas como las chinas, pero sus palabras NO se cortan.
        sin_partir = code in ("ja", "zh") or all(
            w in guion.split() for _, t in lineas for w in t.split())
        comprobar(
            cabe and entero and en_sitio and empieza_bien and sin_partir
            and len(lineas) > 1,
            f"{lang.label(code):<10} {len(lineas)} líneas, la más ancha {max(anchos)}",
            f"cabe={cabe} entero={entero} en_sitio={en_sitio} "
            f"empieza_bien={empieza_bien} sin_partir={sin_partir}",
        )

    print(f"\n── TABLAS completas en los {len(lang.SUPPORTED)} idiomas ──")
    faltan = [f"{k}/{c}" for k, v in lang._PHRASES.items()
              for c in lang.SUPPORTED if not v.get(c)]
    comprobar(not faltan, f"lang._PHRASES ({len(lang._PHRASES)} frases)", ", ".join(faltan))
    huecos = []
    for clave, v in lang._PHRASES.items():
        base = sorted(set(re.findall(r"\{(\w+)\}", v["es"])))
        huecos += [f"{clave}/{c}" for c in lang.SUPPORTED
                   if sorted(set(re.findall(r"\{(\w+)\}", v.get(c, "")))) != base]
    comprobar(not huecos, "los huecos {…} coinciden en todos", ", ".join(huecos))
    comprobar(
        all(set(v) == set(lang.SUPPORTED) for v in lang._LANGUAGE_NAMES.values())
        and set(lang._LANGUAGE_NAMES) == set(lang.SUPPORTED),
        f"lang._LANGUAGE_NAMES ({len(lang.SUPPORTED)} × {len(lang.SUPPORTED)})",
    )
    comprobar(set(lang.language_words()) == set(lang.SUPPORTED), "lang._LANGUAGE_WORDS")
    comprobar(all(lang.llm_directive(c).startswith("# IDIOMA ACTIVO") for c in lang.SUPPORTED),
              "directiva de idioma para Claude")
    comprobar(all(set(v) == set(lang.SUPPORTED) for v in dichos.values()),
              "maneuvers._SAY (frases del giro)")
    trivia_js = (RAIZ / "frontend" / "trivia.js").read_text(encoding="utf-8")
    sin_pantalla = [c for c in lang.SUPPORTED if not re.search(rf"^    {c}: \{{", trivia_js, re.M)]
    comprobar(not sin_pantalla, "frontend/trivia.js (textos de la pantalla)",
              "faltan: " + ", ".join(sin_pantalla))
    panel = (RAIZ / "frontend" / "index.html").read_text(encoding="utf-8")
    sin_chip = [c for c in lang.SUPPORTED if f'id="lang-{c}"' not in panel]
    comprobar(not sin_chip, "frontend/index.html (un chip por idioma)",
              "faltan: " + ", ".join(sin_chip))

    print(f"\n{'TODO BIEN' if not fallos else f'⚠️  {fallos} fallo(s)'}.")
    if fallos:
        print(
            "Si aflojas el matcher para arreglar uno, vuelve a correr esto y\n"
            "scripts/probar_trivia.py: aflojar por un lado rompe el otro."
        )
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
