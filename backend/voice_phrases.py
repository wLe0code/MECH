"""Detección de las frases de mando de MECH.

Aquí vive TODO lo que se reconoce por palabras sueltas y no pasa por Claude:
despertar, dormir, interrumpir, las órdenes de movimiento, "proyecta
marketing" y el modo traductor ("traduce MECH" + el par de idiomas).
Centralizado para que lo usen el bucle de voz (server.py), el listener de
interrupción y mech_app sin duplicar listas.

El match es por palabras en cualquier orden: una frase coincide si TODAS sus
palabras aparecen en el texto (cada una como parte de algún token). Así
"duermete mech", "mech duermete" y "duermete" funcionan igual, y tolera mejor
lo que transcribe Whisper.

Hay DIEZ idiomas (es/en/fr/pt + de/it/ja/ru/zh + ko). Cada lista de
`config.py` tiene sus variantes `_EN`, `_FR`, `_PT`, `_DE`, `_IT`, `_JA`,
`_RU`, `_ZH` y `_KO`, y `_frases_activas()` elige la del idioma ACTIVO: un
comando solo vale en el idioma con el que se despertó a MECH (oct 2026). Las
de despertar son la excepción — en reposo se miran las diez, porque son las
que deciden el idioma.

Cuatro de ellos NO se escriben con letras latinas, y eso cambia dos cosas
(todo lo demás de este módulo sigue igual para los idiomas de siempre):

  - **Japonés y chino van sin espacios.** No hay "palabras" que comparar, así
    que cada trozo de una frase de `config` se busca DENTRO de lo que se oyó
    (`_contiene`). «こんにちは mech» casa con «こんにちはMECH» y con
    «こんにちは、メック».
  - **El coreano sí lleva espacios, pero pega las terminaciones** a la
    palabra («번역해줘», «번역해 주세요»), así que se trata igual: cada trozo
    se busca dentro de lo oído. La excepción es una sílaba suelta dentro de
    una orden de varias («앞으로 가»): esa tiene que ser la palabra entera.
  - **El nombre no sale siempre como "MECH".** Whisper lo escribe como suena
    («メック», «мек», «麦克», «멕»). Cualquier frase que lleve la palabra
    "mech" acepta también las formas de `config.VOICE_NAME_ALIASES`.

Cómo se compara cada palabra (`_word_matches`), de más barato a más caro:

  1. igual;
  2. **suena igual** en español (`_fonetica`) — Whisper escribe lo que oye, y
     "olle"/"oye", "marqueting"/"marketing", "asia"/"hacia" o "mesh"/"mech"
     son el mismo sonido escrito distinto;
  3. el token empieza igual y trae como mucho una letra de más
     ("mech" -> "mecha", "va" -> "vai");
  4. está a pocas letras de distancia: 1 para palabras de 4-6 letras, 2 para
     las de 7+ **si además empiezan igual**.

El punto 4 con 2 errores es lo que hace falta para «trasluce» -> «traduce»,
que es el fallo real que reportó el equipo. El "si empiezan igual" es lo que
evita que «produce» active el traductor.

⚠️ Al añadir frases, ojo con las colisiones entre idiomas: el portugués no
usa "desperta" porque caería en el español "despierta", ni "olá" porque cae
en "hola". Hay un corpus de prueba con casos reales de mala transcripción.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

import config
import lang

# Marcas de sonoridad del kana (が = か + ゛). Para Unicode son "acentos", pero
# en japonés cambian la palabra: si se quitaran, «はい» (sí) aparecería dentro
# de «いっぱい».
_MARCAS_KANA = "゙゚"
# Katakana -> hiragana. Whisper escribe la misma palabra en un silabario o en
# el otro según le da («メック» / «めっく»): se comparan las dos en hiragana.
_KATA_A_HIRA = {c: c - 0x60 for c in range(0x30A1, 0x30F7)}


def _es_hangul(c: str) -> bool:
    """¿Es una sílaba coreana?"""
    return 0xAC00 <= ord(c) <= 0xD7A3


def _es_cjk(c: str) -> bool:
    """¿Es un carácter chino, japonés o coreano?

    Son los idiomas donde un comando no se puede comparar palabra por
    palabra: el chino y el japonés van sin espacios, y el coreano pega las
    terminaciones a la palabra («번역해줘», «번역해 주세요»). En los tres, cada
    trozo de una frase de `config` se busca DENTRO de lo que se oyó.
    """
    o = ord(c)
    return (
        0x3040 <= o <= 0x30FF       # hiragana y katakana
        or 0x4E00 <= o <= 0x9FFF    # ideogramas
        or 0x3400 <= o <= 0x4DBF
        or 0xF900 <= o <= 0xFAFF
        or 0x3005 <= o <= 0x3007    # 々 〆 〇
        or 0xAC00 <= o <= 0xD7A3    # hangul (coreano)
    )


def _tiene_cjk(t: str) -> bool:
    return any(_es_cjk(c) for c in t)


def normalize(text: str) -> str:
    """Minúsculas, sin acentos ni signos.

    Con japonés y chino hace además lo necesario para poder compararlos: las
    letras de ancho completo pasan a las normales («ＭＥＣＨ» -> «mech»), el
    katakana pasa a hiragana, y se mete un espacio donde cambia la escritura
    («こんにちはmech» -> «こんにちは mech»). Con texto en letras latinas el
    resultado es exactamente el de siempre.
    """
    t = text
    if not t.isascii():
        t = "".join(
            unicodedata.normalize("NFKC", c) if 0xFF00 <= ord(c) <= 0xFFEF else c
            for c in t
        )
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(
        c for c in t if unicodedata.category(c) != "Mn" or c in _MARCAS_KANA
    )
    if not t.isascii():
        t = unicodedata.normalize("NFC", t).translate(_KATA_A_HIRA)
    salida: list[str] = []
    previo: bool | None = None  # ¿el carácter anterior era chino/japonés?
    for c in t:
        if not c.isalnum():
            salida.append(" ")
            previo = None
            continue
        cjk = _es_cjk(c)
        if previo is not None and cjk != previo:
            salida.append(" ")
        salida.append(c)
        previo = cjk
    return " ".join("".join(salida).split())


@lru_cache(maxsize=4096)
def _palabras(frase: str) -> tuple[str, ...]:
    """Las palabras de una frase de `config`, ya normalizadas.

    Con nueve idiomas son varios cientos de frases y se comparan todas en cada
    cosa que se oye: se normalizan una sola vez.
    """
    return tuple(normalize(frase).split())


# --- Cómo suena una palabra en español -----------------------------------
# Whisper escribe lo que OYE, y en español hay sonidos que se escriben de
# varias formas. Comparando el SONIDO en vez de las letras, muchos errores de
# transcripción dejan de serlo:
#
#     "olle mech"        -> "oye mech"        (yeísmo: ll = y)
#     "proyecta marqueting" -> "...marketing" (qu = k)
#     "mira asia afuera" -> "mira hacia..."   (h muda)
#     "traduse"          -> "traduce"         (seseo: c/z/s)
#     "boy"              -> "voy"             (b = v)
#
# No es fonética de verdad, es una reducción rápida y suficiente. El objetivo
# no es transcribir bien, es que dos formas de escribir el MISMO sonido
#     "mesh"             -> "mech"            (sh = ch al oído español)
_DIGRAFOS = (("ll", "y"), ("qu", "k"), ("ch", "\x01"), ("sh", "\x01"),
             ("rr", "r"))


@lru_cache(maxsize=8192)
def _fonetica(palabra: str) -> str:
    """Reduce una palabra a un esqueleto de cómo SUENA en español."""
    p = palabra
    for viejo_, nuevo_ in _DIGRAFOS:
        p = p.replace(viejo_, nuevo_)
    p = p.replace("h", "")  # muda: "hacia" y "asia" acaban igual
    salida = []
    for i, ch in enumerate(p):
        sig = p[i + 1] if i + 1 < len(p) else ""
        if ch == "c":
            salida.append("s" if sig and sig in "ei" else "k")   # seseo / c fuerte
        elif ch == "g":
            salida.append("j" if sig and sig in "ei" else "g")   # "gente" = "jente"
        elif ch in "zx":
            salida.append("s")
        elif ch == "v":
            salida.append("b")                            # b y v suenan igual
        else:
            salida.append(ch)
    p = "".join(salida).replace("\x01", "ch")
    # Letras repetidas seguidas: en español casi nunca cambian el sonido.
    fuera = []
    for ch in p:
        if not fuera or fuera[-1] != ch:
            fuera.append(ch)
    return "".join(fuera)


def _lev(a: str, b: str, tope: int) -> int:
    """Distancia de edición entre a y b, cortando en cuanto supera `tope`.

    Devuelve `tope + 1` si se pasa (no interesa el valor exacto).
    """
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if abs(la - lb) > tope:
        return tope + 1
    anterior = list(range(lb + 1))
    for i in range(1, la + 1):
        actual = [i] + [0] * lb
        mejor = actual[0]
        for j in range(1, lb + 1):
            coste = 0 if a[i - 1] == b[j - 1] else 1
            actual[j] = min(anterior[j] + 1, actual[j - 1] + 1, anterior[j - 1] + coste)
            mejor = min(mejor, actual[j])
        if mejor > tope:
            return tope + 1
        anterior = actual
    return anterior[lb]


def _tolerancia(n: int) -> int:
    """Cuántos errores de letra se le perdonan a una palabra de `n` letras.

    - 1-3 letras: NINGUNO. Son "oye", "ok", "de"... y con tolerancia
      disparaban solas. (Con substring, "oye" incluso coincidía DENTRO de
      "pr-oye-cto": «el proyecto se llama mech» activaba la interrupción.)
    - 4-6 letras: uno. Cubre "mech" -> "mec", "mek", "meche".
    - 7+ letras: dos, pero pidiendo que empiecen igual (ver `_word_matches`).
      Es lo que hace falta para "traduce" -> "trasluce", que es un error de
      DOS letras y el caso que reportó el equipo.
    """
    if n >= 7:
        return 2
    if n >= 4:
        return 1
    return 0


def _word_matches(w: str, tok: str) -> bool:
    """¿La palabra `w` de un comando coincide con el token `tok` que oyó Whisper?

    Se prueba, de más barato a más caro: igual → suena igual → una está
    dentro de la otra (solo palabras largas) → está a pocas letras.
    """
    if w == tok:
        return True
    fw, ft = _fonetica(w), _fonetica(tok)
    if fw == ft:
        return True
    # "Casi la misma palabra": el token EMPIEZA igual y trae como mucho una
    # letra de más ("mech" -> "mecha", "va" -> "vai"). Antes esto era un
    # substring libre, y eso producía dos falsos positivos reales:
    #   - "oye" coincidía DENTRO de "pr-oye-cto", así que «el proyecto se
    #     llama mech» disparaba la interrupción;
    #   - "avanza" coincidía dentro de "avanzada", así que «qué avanzada
    #     tecnología» ponía al robot a caminar.
    # Pidiendo prefijo y una sola letra de más, los dos desaparecen sin
    # perder los casos buenos.
    if len(tok) - len(w) <= 1 and (tok.startswith(w) or ft.startswith(fw)):
        return True
    tope = _tolerancia(len(w))
    if tope == 0:
        return False
    if tope >= 2 and fw[:2] != ft[:2]:
        # Dos errores es mucha manga ancha: se exige que arranquen igual.
        # Así "trasluce" sigue casando con "traduce" (las dos "tra...") pero
        # "produce" NO — si no, «produce» activaría el traductor.
        tope = 1
    return _lev(fw, ft, tope) <= tope


# El nombre del robot tal como va escrito en las listas de `config`.
_NOMBRE = "mech"
# Lo que se le pega al nombre en coreano al llamar a alguien o hablar de él:
# «멕아» / «멕이» (vocativo), «멕씨» / «멕님» (señor MECH), «멕은» / «멕을»…
_TRAS_NOMBRE_KO = "아야이씨님은을도"


@lru_cache(maxsize=8)
def _alias_normalizados(crudos: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(a for a in (normalize(x) for x in crudos) if a)


def _nombre_en(tokens: list[str]) -> bool:
    """¿Dijeron «MECH», escrito como lo escribe Whisper en otra escritura?

    En japonés, ruso o chino el nombre no siempre sale en letras latinas:
    sale como suena («メック», «мек», «麦克»). Las formas aceptadas están en
    `config.VOICE_NAME_ALIASES`. Ninguna usa letras latinas, así que esto no
    le abre la puerta a nada en los idiomas de siempre.
    """
    crudos = tuple(getattr(config, "VOICE_NAME_ALIASES", ()) or ())
    for alias in _alias_normalizados(crudos):
        if _tiene_cjk(alias):
            if len(alias) == 1:
                # Un nombre de UNA sílaba («멕», «맥») es demasiado poco para
                # buscarlo dentro de otra palabra: «멕시코» (México) y «맥주»
                # (cerveza) llevarían el nombre. Solo vale suelto o con la
                # sílaba con que se llama a alguien en coreano («멕아», «맥씨»).
                if any(
                    tok == alias
                    or (len(tok) == 2 and tok[0] == alias and tok[1] in _TRAS_NOMBRE_KO)
                    for tok in tokens
                ):
                    return True
            elif any(alias in tok for tok in tokens):
                return True
        elif any(_word_matches(alias, tok) for tok in tokens):
            return True
    return False


def _contiene(w: str, tokens: list[str], sola: bool = False) -> bool:
    """¿La palabra `w` de un comando aparece en lo que se oyó (`tokens`)?

    - Letras latinas o cirílico: como siempre, token a token (`_word_matches`).
    - Japonés y chino: no hay espacios, así que `w` se busca DENTRO de cada
      trozo. Un comando de un solo carácter («好», «不») es demasiado poco para
      eso: solo cuenta si la respuesta es corta y EMPIEZA por él (`sola`), o
      «你好» (hola) sería un sí.
    - El nombre: además de "mech", vale escrito en otra escritura.
    - Coreano: va con espacios, pero la terminación se pega a la palabra, así
      que también se busca dentro. Una sílaba suelta DENTRO de una orden de
      varias («앞으로 가», «잘 자 mech») tiene que ser la palabra entera: «가»
      es además la partícula más común del idioma y aparece pegada a medio
      diccionario («앞으로 가져올…» no es "avanza").
    """
    if _es_cjk(w[0]):
        if sola and len(w) == 1:
            return any(tok.startswith(w) and len(tok) <= 3 for tok in tokens)
        if len(w) == 1 and _es_hangul(w):
            return w in tokens
        return any(w in tok for tok in tokens)
    if any(_word_matches(w, tok) for tok in tokens):
        return True
    return w == _NOMBRE and _nombre_en(tokens)


def matches_any(text: str, phrases: list[str]) -> bool:
    tokens = normalize(text).split()
    if not tokens:
        return False
    for p in phrases:
        words = _palabras(p)
        sola = len(words) == 1
        if words and all(_contiene(w, tokens, sola) for w in words):
            return True
    return False


# Idioma -> sufijo de su lista en `config` (`VOICE_X_PHRASES` + sufijo; el
# español no lleva).
_SUFIJOS = {"es": "", "en": "_EN", "fr": "_FR", "pt": "_PT", "de": "_DE",
            "it": "_IT", "ja": "_JA", "ru": "_RU", "zh": "_ZH", "ko": "_KO"}


def _frases_activas(base: str) -> list[str]:
    """La lista `base` de config, en el idioma ACTIVO de MECH.

    Regla del equipo (oct 2026): un comando solo vale si se dice en el idioma
    con el que se despertó a MECH. Despierto con "wake up MECH", lo corta
    "hey MECH" y NO "oye MECH"; despierto con "ok MECH", al revés. Aquí pasan
    TODAS las frases de mando menos las de despertar (esas son las que eligen
    el idioma: ver `wake_language`).

    Con `VOICE_STRICT_LANGUAGE=false` vuelve lo de antes: se juntan las
    listas de todos los idiomas y se aceptan todas siempre.
    """
    if config.VOICE_STRICT_LANGUAGE:
        sufijo = _SUFIJOS.get(lang.current(), "")
        return list(getattr(config, base + sufijo, []) or [])
    frases: list[str] = []
    for sufijo in _SUFIJOS.values():
        frases += list(getattr(config, base + sufijo, []) or [])
    return frases


def _interrupt_phrases() -> list[str]:
    """Frases de interrupción (del idioma activo: ver `_frases_activas`)."""
    return _frases_activas("VOICE_INTERRUPT_PHRASES")


def is_interrupt(text: str) -> bool:
    """¿El visitante está pidiendo cortar la narración? ("oye MECH")."""
    return matches_any(text, _interrupt_phrases())


def strip_interrupt(text: str) -> str:
    """Devuelve lo que queda tras quitar la frase de interrupción.

    Sirve para que "oye MECH, cuéntame otra cosa" no obligue a repetir: se
    corta la narración Y se atiende "cuéntame otra cosa" enseguida. Si solo
    se dijo la frase ("oye MECH"), devuelve cadena vacía.
    """
    tokens = list(re.finditer(r"\S+", text or ""))
    if not tokens:
        return ""
    norm = [normalize(t.group(0)) for t in tokens]
    for phrase in _interrupt_phrases():
        usados: list[int] = []
        for w in _palabras(phrase):
            hit = next(
                (i for i, tok in enumerate(norm)
                 if i not in usados and _contiene(w, [tok])),
                None,
            )
            if hit is None:
                usados = []
                break
            usados.append(hit)
        if usados:
            resto = text[tokens[max(usados)].end():]
            return resto.strip(_SIGNOS)
    # Japonés y chino van sin espacios: la frase y la petición llegan pegadas
    # («ねえMECH、別の話をして») y arriba no hay dónde cortar. Ahí se corta justo
    # después del nombre.
    if _tiene_cjk(text) and is_interrupt(text):
        return _tras_el_nombre(text)
    return ""


# Signos que se recortan de los bordes de una petición.
_SIGNOS = " \t,.;:¿?¡!-–—\"'、。，！？：；　"


def _tras_el_nombre(text: str) -> str:
    """Lo que viene después de «MECH» (o de cómo lo escribió Whisper)."""
    bajo = text.lower()
    fin = -1
    for forma in (_NOMBRE, *(getattr(config, "VOICE_NAME_ALIASES", ()) or ())):
        i = bajo.rfind(forma.lower())
        if i >= 0:
            fin = max(fin, i + len(forma))
    return text[fin:].strip(_SIGNOS) if fin >= 0 else ""


# --- Órdenes de movimiento (no pasan por Claude) --------------------------
# "mira hacia afuera" / "regresa a proyectar". Como todos los comandos, solo
# valen en el idioma con el que se despertó a MECH (ver `_frases_activas`).


# Números escritos con letra, para "avanza DIEZ segundos". Whisper los
# transcribe casi siempre en letra, no en dígito.
_NUMEROS = {
    "medio": 0.5, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3,
    "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
    "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14,
    "quince": 15, "dieciseis": 16, "diecisiete": 17, "dieciocho": 18,
    "diecinueve": 19, "veinte": 20, "veinticinco": 25, "treinta": 30,
    # Los grandes también, aunque el tope de seguridad los recorte: es mejor
    # entenderlos y toparlos que ignorarlos y hacer otra cosa distinta.
    "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "cien": 100,
    # inglés, por si le hablan en modo EN
    "half": 0.5, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30,
    # francés (modo FR). "un/une" ya están arriba con el mismo valor.
    "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "sept": 7, "huit": 8,
    "neuf": 9, "dix": 10, "douze": 12, "quinze": 15, "vingt": 20,
    "trente": 30,
    # portugués (modo PT). Los que se escriben igual que en español
    # ("cinco", "seis", "sete"≈"siete", "quinze"≈francés) ya están arriba.
    "um": 1, "uma": 1, "dois": 2, "quatro": 4, "dez": 10, "doze": 12,
    "vinte": 20, "trinta": 30, "meio": 0.5,
    # alemán (modo DE). Escritos ya sin diéresis, que es como quedan al
    # normalizar ("fünf" -> "funf").
    "ein": 1, "eine": 1, "eins": 1, "zwei": 2, "drei": 3, "vier": 4,
    "funf": 5, "sechs": 6, "sieben": 7, "acht": 8, "neun": 9, "zehn": 10,
    "elf": 11, "zwolf": 12, "funfzehn": 15, "zwanzig": 20, "dreißig": 30,
    "dreissig": 30, "halbe": 0.5,
    # italiano (modo IT). "un/uno/una" ya están arriba.
    "due": 2, "tre": 3, "quattro": 4, "cinque": 5, "sei": 6, "sette": 7,
    "otto": 8, "nove": 9, "dieci": 10, "undici": 11, "dodici": 12,
    "quindici": 15, "venti": 20, "trenta": 30, "mezzo": 0.5,
    # ruso (modo RU)
    "один": 1, "одну": 1, "одна": 1, "два": 2, "две": 2, "три": 3,
    "четыре": 4, "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9,
    "десять": 10, "пятнадцать": 15, "двадцать": 20, "тридцать": 30,
}

# Japonés y chino: el número va pegado a «秒» (segundos) y casi siempre en
# cifras («10秒»), pero también puede salir en ideogramas («十秒», «两秒»).
_SEGUNDOS_CJK = re.compile(r"([0-9]+|[零〇一二两兩三四五六七八九十半]+)\s*秒")
_DIGITOS_CJK = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "兩": 2, "三": 3,
                "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def _numero_cjk(s: str) -> float | None:
    """«10», «十», «二十五» o «半» -> el número (hasta 99), o None."""
    if s.isdigit():
        return float(s)
    if s == "半":
        return 0.5
    if "十" in s:
        izq, _, der = s.partition("十")
        decenas = _DIGITOS_CJK.get(izq) if izq else 1
        unidades = _DIGITOS_CJK.get(der) if der else 0
        if decenas is None or unidades is None:
            return None
        return float(decenas * 10 + unidades)
    if len(s) == 1 and s in _DIGITOS_CJK:
        return float(_DIGITOS_CJK[s])
    return None


# Coreano: el número va delante de «초» (segundos). Casi siempre en cifras
# («10초»), a veces con los números chinos («십 초», «이십오 초») y, aunque
# con segundos no es lo correcto, también con los propios («다섯 초»).
# El número no puede venir pegado a otra palabra: en «로봇이 초록색» el «이»
# es una partícula, no un dos.
_SEGUNDOS_KO = re.compile(
    r"(?<![가-힣])([0-9]+|[일이삼사오육칠팔구십]+|다섯|여섯|일곱|여덟|아홉"
    r"|스무|서른|한|두|세|네|열)\s*초"
)
_DIGITOS_KO = {"일": 1, "이": 2, "삼": 3, "사": 4, "오": 5, "육": 6, "칠": 7,
               "팔": 8, "구": 9}
_NATIVOS_KO = {"한": 1, "두": 2, "세": 3, "네": 4, "다섯": 5, "여섯": 6,
               "일곱": 7, "여덟": 8, "아홉": 9, "열": 10, "스무": 20, "서른": 30}


def _numero_ko(s: str) -> float | None:
    """«10», «십», «이십오» o «다섯» -> el número (hasta 99), o None."""
    if s.isdigit():
        return float(s)
    if s in _NATIVOS_KO:
        return float(_NATIVOS_KO[s])
    if "십" in s:
        izq, _, der = s.partition("십")
        decenas = _DIGITOS_KO.get(izq) if izq else 1
        unidades = _DIGITOS_KO.get(der) if der else 0
        if decenas is None or unidades is None:
            return None
        return float(decenas * 10 + unidades)
    if len(s) == 1 and s in _DIGITOS_KO:
        return float(_DIGITOS_KO[s])
    return None


def extract_seconds(text: str) -> float | None:
    """Los segundos que pide una orden, o None si no dice ninguno.

    Acepta dígitos ("avanza 10 segundos") y letra ("avanza diez segundos"),
    que es como lo transcribe Whisper casi siempre. Si no hay número, quien
    llame decide el valor por defecto.
    """
    norm = normalize(text)
    if _tiene_cjk(norm):
        m = _SEGUNDOS_CJK.search(norm)
        valor = _numero_cjk(m.group(1)) if m else None
        if valor is not None:
            return valor
        m = _SEGUNDOS_KO.search(norm)
        valor = _numero_ko(m.group(1)) if m else None
        if valor is not None:
            return valor
    tokens = norm.split()
    for i, tok in enumerate(tokens):
        valor = None
        if tok.isdigit():
            valor = float(tok)
        elif tok in _NUMEROS:
            valor = float(_NUMEROS[tok])
        if valor is None:
            continue
        # "diez segundos" sí; "diez" suelto también (si dijeron un número en
        # una orden de movimiento, es el tiempo: no hay otra cosa que contar).
        siguiente = tokens[i + 1] if i + 1 < len(tokens) else ""
        if not siguiente or siguiente.startswith("segundo") or siguiente.startswith("second"):
            return valor
        return valor
    return None


def is_advance(text: str) -> bool:
    """¿Piden avanzar? ("avanza diez segundos")"""
    return matches_any(text, _frases_activas("VOICE_ADVANCE_PHRASES"))


def is_retreat(text: str) -> bool:
    """¿Piden retroceder? ("retrocede cinco segundos")"""
    return matches_any(text, _frases_activas("VOICE_RETREAT_PHRASES"))


def is_look_outward(text: str) -> bool:
    """¿Le están pidiendo que gire 180° y salude hacia afuera?"""
    return matches_any(text, _frases_activas("VOICE_OUTWARD_PHRASES"))


def is_back_to_projection(text: str) -> bool:
    """¿Le están pidiendo que vuelva a su posición de proyección?"""
    return matches_any(text, _frases_activas("VOICE_PROJECT_PHRASES"))


def is_play_marketing(text: str) -> bool:
    """¿Piden proyectar el slot de marketing? ("proyecta marketing")"""
    return matches_any(text, _frases_activas("VOICE_MARKETING_PHRASES"))


def is_translate(text: str) -> bool:
    """¿Piden entrar en modo traductor? ("traduce MECH", "modo traductor")"""
    return matches_any(text, _frases_activas("VOICE_TRANSLATE_PHRASES"))


def is_translate_stop(text: str) -> bool:
    """¿Piden salir del modo traductor? ("deja de traducir")"""
    return matches_any(text, _frases_activas("VOICE_TRANSLATE_STOP_PHRASES"))


@lru_cache(maxsize=1)
def _palabras_de_idioma() -> dict[str, tuple[str, ...]]:
    """`lang.language_words()` con cada nombre ya normalizado."""
    return {
        code: tuple(v for v in (normalize(x) for x in variantes) if v)
        for code, variantes in lang.language_words().items()
    }


def extract_language_pair(text: str) -> tuple[str | None, str | None]:
    """Los idiomas nombrados en "de español a francés", en ese orden.

    Devuelve `(origen, destino)`. Si solo se nombra UNO ("traduce al
    francés"), vuelve como destino y el origen queda en None — quien llame
    decide que el origen es el idioma activo. Si no se nombra ninguno,
    `(None, None)`.

    Los nombres de cada idioma (en todos los idiomas) están en
    `lang.language_words()`; el match usa el mismo matcher tolerante que el
    resto, así que "espanol", "espagnol" y "espanhol" caen todos en "es".

    En japonés y chino la frase va sin espacios («日本語からスペイン語に»):
    los dos idiomas pueden venir en el MISMO trozo, y el orden lo da la
    posición de cada nombre dentro de él.
    """
    tokens = normalize(text).split()
    palabras = _palabras_de_idioma()
    encontrados: list[str] = []
    for tok in tokens:
        if _tiene_cjk(tok):
            dentro = []
            for code, variantes in palabras.items():
                sitios = [tok.find(v) for v in variantes if _es_cjk(v[0])]
                sitios = [s for s in sitios if s >= 0]
                if sitios:
                    dentro.append((min(sitios), code))
            for _, code in sorted(dentro):
                if code not in encontrados:
                    encontrados.append(code)
            continue
        for code, variantes in palabras.items():
            if code in encontrados:
                continue
            if any(_word_matches(v, tok) for v in variantes if not _es_cjk(v[0])):
                encontrados.append(code)
                break
    if len(encontrados) >= 2:
        return encontrados[0], encontrados[1]
    if len(encontrados) == 1:
        return None, encontrados[0]
    return None, None


# ---------------------------------------------------------------------------
# Modo TRIVIA (ver backend/trivia.py)
# ---------------------------------------------------------------------------

def is_trivia(text: str) -> bool:
    """¿Piden jugar la trivia? ("juguemos una trivia")"""
    if is_trivia_stop(text):
        return False
    return matches_any(text, _frases_activas("VOICE_TRIVIA_PHRASES"))


def is_trivia_stop(text: str) -> bool:
    """¿Piden salir del juego? ("deja la trivia")"""
    return matches_any(text, _frases_activas("VOICE_TRIVIA_STOP_PHRASES"))


def is_yes(text: str) -> bool:
    """¿Es un sí? Solo se mira cuando MECH acaba de preguntar algo."""
    return matches_any(text, _frases_activas("VOICE_YES_PHRASES"))


def is_no(text: str) -> bool:
    """¿Es un no? Se comprueba ANTES que el sí: "no, gracias" trae los dos."""
    return matches_any(text, _frases_activas("VOICE_NO_PHRASES"))


# ---------------------------------------------------------------------------
# Modo música (ver backend/music.py)
# ---------------------------------------------------------------------------

def is_music(text: str) -> bool:
    """¿Piden el modo música? («modo música MECH», «activa modo música»)"""
    if is_music_stop(text):
        # «sal del modo música» lleva dentro las palabras de «modo música»:
        # salir se mira antes que entrar, como en el traductor y la trivia.
        return False
    return matches_any(text, _frases_activas("VOICE_MUSIC_PHRASES"))


def is_music_stop(text: str) -> bool:
    """¿Piden salir del modo música? («apaga la música»)"""
    return matches_any(text, _frases_activas("VOICE_MUSIC_STOP_PHRASES"))


def is_music_more(text: str) -> bool:
    """¿Piden otra canción? Solo se mira cuando MECH pregunta si seguimos."""
    return matches_any(text, _frases_activas("VOICE_MUSIC_MORE_PHRASES"))


# Cómo suena cada letra de opción al decirla. La clave es el índice (0 = A).
#
# ⚠️ Todas son AMBIGUAS en español y por eso no basta con verlas en la frase:
# "a" es una preposición, "ve" y "se" son verbos corrientes, "de" es la
# preposición más común del idioma. Solo cuentan si la frase es CORTA (una
# respuesta suelta, "la a") o si delante va una palabra que las presenta
# ("la", "opción", "letra"). Ver `_letra_en()`.
def _n(*palabras: str) -> tuple[str, ...]:
    """Normaliza palabras escritas "al natural" (con diéresis, й, ё…)."""
    return tuple(normalize(p) for p in palabras)


# Lo que va dentro de `_n(...)` es cómo nombran esas letras en alemán ("tse")
# y en italiano ("bi", "ci", "di"), y cómo las escribe Whisper en CIRÍLICO
# cuando el visitante habla ruso: la «А» rusa y la «A» latina se ven iguales
# pero son caracteres distintos.
_LETRA_TOKENS: dict[int, tuple[str, ...]] = {
    0: ("a", "ah", "ha") + _n("а"),
    1: ("b", "be", "ve", "uve", "bee") + _n("bi", "б", "бэ", "бе", "би"),
    2: ("c", "ce", "se", "cee")
       + _n("ci", "tse", "zeh", "ц", "цэ", "це", "си", "с"),
    3: ("d", "de", "dee") + _n("di", "д", "дэ", "де", "ди"),
}

# Palabras que PRESENTAN una letra o un número de opción.
_MARCADORES = (
    "la", "el", "opcion", "letra", "respuesta", "numero", "eleccion", "elijo",
    "escojo", "digo", "creo", "es", "seria", "pongo", "marco",
    "option", "letter", "answer", "number", "choose", "pick", "say",
    "lettre", "reponse", "numero", "choix", "opcao", "resposta", "escolho",
) + _n(
    "die", "der", "das", "antwort", "buchstabe", "nummer", "nehme", "wähle",
    "il", "opzione", "lettera", "risposta", "scelgo", "dico",
    "ответ", "вариант", "буква", "номер", "выбираю", "это",
)

# Ordinales y números por índice, en los idiomas que se escriben con espacios.
# ⚠️ En italiano van solo los femeninos ("la seconda"): «secondo me» significa
# "en mi opinión", y «secondo me la B» se leería como la segunda.
_ORDINAL_TOKENS: dict[int, tuple[str, ...]] = {
    0: ("primera", "primero", "primer", "uno", "una", "1", "first", "one",
        "premiere", "premier", "un", "primeira", "primeiro")
       + _n("erste", "erster", "erstes", "ersten", "eins", "prima",
            "первая", "первый", "первое", "первую", "один"),
    1: ("segunda", "segundo", "dos", "2", "second", "two", "deuxieme",
        "deux", "segunda", "duas")
       + _n("zweite", "zweiter", "zweites", "zweiten", "zwei", "seconda",
            "due", "вторая", "второй", "второе", "вторую", "два"),
    2: ("tercera", "tercero", "tres", "3", "third", "three", "troisieme",
        "trois", "terceira", "terceiro")
       + _n("dritte", "dritter", "drittes", "dritten", "drei", "terza", "tre",
            "третья", "третий", "третье", "третью", "три"),
    3: ("cuarta", "cuarto", "cuatro", "4", "fourth", "four", "quatrieme",
        "quatre", "quarta", "quarto")
       + _n("vierte", "vierter", "viertes", "vierten", "vier", "quattro",
            "четвёртая", "четвёртый", "четвёртое", "четвёртую", "четыре"),
}
# Japonés y chino: van pegados al resto («二番目です», «我选第二个»), así que
# se buscan DENTRO del trozo. Con cifra («2番», «第2个») no hacen falta: la
# cifra queda separada sola y la reconoce la tabla de arriba.
_ORDINAL_CJK: dict[int, tuple[str, ...]] = {
    0: _n("第一", "一番", "いちばん", "一つ目", "ひとつめ", "最初", "一号", "一號"),
    1: _n("第二", "二番", "にばん", "二つ目", "ふたつめ", "二号", "二號"),
    2: _n("第三", "三番", "さんばん", "三つ目", "みっつめ", "三号", "三號"),
    3: _n("第四", "四番", "よんばん", "四つ目", "よっつめ", "四号", "四號"),
}
# Las letras dichas en japonés. Whisper casi siempre escribe «A», pero a
# veces lo deja en kana. Solo valen si son la respuesta ENTERA («えー» es
# también lo que dice alguien que duda).
_LETRA_KANA: dict[str, int] = {
    normalize(k): v for k, v in {
        "エー": 0, "エイ": 0, "ビー": 1, "シー": 2, "ディー": 3,
    }.items()
}
# Coreano. Los ordinales van en dos palabras («두 번째») que Whisper junta o
# separa a su antojo, así que se buscan con los espacios quitados. Con cifra
# («2번») no hacen falta: la cifra queda suelta y la reconoce la tabla de
# arriba. ⚠️ Nada de «이번» por "número dos": es también "esta vez".
_ORDINAL_HANGUL: dict[int, tuple[str, ...]] = {
    0: ("첫번째", "첫째"),
    1: ("두번째", "둘째"),
    2: ("세번째", "셋째"),
    3: ("네번째", "넷째"),
}
# Las letras dichas en coreano y escritas en hangul. Como en japonés, solo
# valen si son la respuesta ENTERA («비» es también "lluvia"), con o sin la
# terminación de cortesía («비요», «비입니다»).
_LETRA_HANGUL: dict[str, int] = {"에이": 0, "비": 1, "씨": 2, "시": 2, "디": 3}
_COLETILLAS_KO = ("입니다", "이에요", "예요", "이요", "요")

# Palabras que no aportan nada al comparar el TEXTO de una opción.
_VACIAS = {
    "de", "del", "la", "el", "los", "las", "un", "una", "unos", "unas", "y",
    "o", "en", "con", "por", "para", "que", "es", "al", "se", "su", "sus",
    "the", "of", "and", "a", "an", "in", "on", "to", "is", "it",
    "le", "les", "des", "du", "et", "dans", "est",
    "do", "da", "dos", "das", "em", "com", "para", "que",
    # alemán, italiano y ruso
    "der", "die", "das", "und", "ein", "eine", "von", "im", "ist", "den",
    "il", "lo", "gli", "di", "e", "della", "che", "per",
    "и", "в", "на", "с", "из", "это", "по",
    # japonés y chino (cuando quedan sueltos junto a una cifra: «1605年»)
    "年", "的", "是", "了", "在", "和", "个", "個",
    "です", "の", "は", "が", "を", "に", "で", "と", "も",
}


# "No sé" no es una opción: es rendirse. Hay que reconocerlo ANTES que las
# letras porque en español lleva dentro un "se" que suena igual que la C — sin
# esto, quien admite que no lo sabe estaría contestando la opción C.
_NO_SE = (
    ("no", "se"), ("no", "lo", "se"), ("ni", "idea"), ("no", "tengo", "idea"),
    ("paso",), ("ni", "idea", "mech"), ("no", "sabria"),
    ("i", "dont", "know"), ("no", "idea"), ("dunno"), ("pass",),
    ("je", "ne", "sais", "pas"), ("aucune", "idee"),
    ("nao", "sei"), ("nem", "ideia"),
    ("weiß", "nicht"), ("weiss", "nicht"), ("keine", "ahnung"),
    ("non", "lo", "so"), ("non", "so"), ("boh",), ("nessuna", "idea"),
    ("не", "знаю"), ("без", "понятия"), ("понятия", "не", "имею"), ("пас",),
)
# En japonés y chino va pegado al resto, así que se busca dentro del trozo.
# ⚠️ En chino «不知道» EMPIEZA por «不», que suelto es un "no": por eso esto se
# mira antes que nada.
_NO_SE_CJK = _n(
    "不知道", "不清楚", "不晓得", "不曉得", "不确定", "不確定",
    "わからない", "分からない", "わかりません", "分かりません",
    "知らない", "しらない", "知りません", "パス",
    # coreano: «모르겠어요», «몰라요», «모릅니다», «패스»
    "모르겠", "몰라", "모릅니다", "모르는", "패스",
)


def is_dont_know(text: str) -> bool:
    """¿Está diciendo que no lo sabe? (no cuenta como respuesta)"""
    tokens = normalize(text).split()
    if not tokens:
        return False
    juego = set(tokens)
    for frase in _NO_SE:
        if isinstance(frase, str):
            frase = (frase,)
        if all(w in juego for w in frase):
            return True
    return any(f in tok for f in _NO_SE_CJK for tok in tokens)


def _letra_en(tokens: list[str], corta: bool) -> int | None:
    """Índice de la opción nombrada por su LETRA, o None.

    `corta` = la frase entera es una respuesta suelta. Con frases largas se
    exige que delante de la letra vaya un marcador ("la a", "opción b"), o si
    no "se dice que..." se leería como la C.
    """
    for i, tok in enumerate(tokens):
        for idx, formas in _LETRA_TOKENS.items():
            if tok in formas:
                if corta or (i > 0 and tokens[i - 1] in _MARCADORES):
                    return idx
    # La letra dicha en japonés y escrita en kana («ビー», «ビーです»).
    if len(tokens) == 1:
        suelta = tokens[0].removesuffix("です")
        if suelta in _LETRA_KANA:
            return _LETRA_KANA[suelta]
        # Lo mismo en coreano («비», «비요», «씨입니다»).
        entera = tokens[0]
        if entera in _LETRA_HANGUL:
            return _LETRA_HANGUL[entera]
        for coletilla in _COLETILLAS_KO:
            suelta = entera[: -len(coletilla)]
            if entera.endswith(coletilla) and suelta in _LETRA_HANGUL:
                return _LETRA_HANGUL[suelta]
    return None


def _ordinal_en(tokens: list[str], corta: bool) -> int | None:
    """Índice de la opción nombrada por su ORDEN ("la segunda", "la 3")."""
    for i, tok in enumerate(tokens):
        for idx, formas in _ORDINAL_TOKENS.items():
            if tok in formas:
                # Los ordinales de verdad ("segunda") son inequívocos; los
                # números sueltos ("dos") pueden ser parte de una opción, así
                # que esos piden frase corta o marcador delante.
                claro = len(tok) > 4 and not tok.isdigit()
                if claro or corta or (i > 0 and tokens[i - 1] in _MARCADORES):
                    return idx
    for tok in tokens:
        if _tiene_cjk(tok):
            for idx, formas in _ORDINAL_CJK.items():
                if any(f in tok for f in formas):
                    return idx
    # Coreano: «두 번째요» y «두번째요» son lo mismo.
    pegado = "".join(t for t in tokens if _es_hangul(t[0]))
    if pegado:
        for idx, formas in _ORDINAL_HANGUL.items():
            if any(f in pegado for f in formas):
                return idx
    return None


def _peso_opcion(opcion: str, tokens: list[str]) -> float:
    """Cuánto se parece lo que se oyó al TEXTO de una opción (0 a 1).

    Se mide por las palabras con contenido de la opción: cuántas aparecen en
    lo que dijo el visitante. Así "el año 1605" acierta la opción "1605" y
    "Sancho Panza" acierta aunque diga "creo que Sancho Panza".
    """
    palabras = [w for w in normalize(opcion).split() if w not in _VACIAS]
    if not palabras:
        palabras = normalize(opcion).split()
    if not palabras:
        return 0.0
    aciertos = sum(1 for w in palabras if _contiene(w, tokens))
    return aciertos / len(palabras)


def parse_answer(text: str, options: list[str]) -> int | None:
    """Qué opción eligió el visitante, o None si no se entendió.

    Acepta las tres formas naturales de contestar:
      - por el texto      -> "mil seiscientos cinco", "Sancho Panza"
      - por la letra      -> "la a", "opción B", "ce"
      - por el orden      -> "la segunda", "la 3"

    El TEXTO se mira PRIMERO a propósito: si alguien responde diciendo la
    opción, dentro de esa frase puede aparecer un "se" o un "de" que se
    confundiría con una letra.
    """
    if not text or not options:
        return None
    if is_dont_know(text):
        return None  # se rindió: no es la opción C aunque lleve un "se"
    tokens = normalize(text).split()
    if not tokens:
        return None
    # En japonés y chino no hay espacios y TODO son "pocas palabras": ahí lo
    # que dice si la respuesta es corta son los caracteres.
    corta = len(tokens) <= 4 and sum(len(t) for t in tokens if _tiene_cjk(t)) <= 8

    # 1) ¿Dijo el texto de una opción? Si la frase CONTIENE la opción entera,
    #    no hay más que discutir.
    norm_text = " ".join(tokens)
    for i, opcion in enumerate(options):
        norm_op = normalize(opcion)
        if norm_op and len(norm_op) >= 4 and norm_op in norm_text:
            return i
    # Lo mismo en japonés y chino, comparando sin espacios (el visitante dice
    # «桑丘潘沙» y la opción está escrita «桑丘·潘沙»). Si caben varias —una
    # opción dentro de otra—, gana la más larga.
    pegado = "".join(tokens)
    dentro = []
    for i, opcion in enumerate(options):
        op = normalize(opcion).replace(" ", "")
        if len(op) >= 2 and _tiene_cjk(op) and op in pegado:
            dentro.append((len(op), i))
    if dentro:
        dentro.sort(reverse=True)
        if len(dentro) == 1 or dentro[0][0] > dentro[1][0]:
            return dentro[0][1]
    pesos = [_peso_opcion(op, tokens) for op in options]
    mejor = max(range(len(pesos)), key=lambda i: pesos[i])
    ordenados = sorted(pesos, reverse=True)
    segundo = ordenados[1] if len(ordenados) > 1 else 0.0
    # Basta con media opción ("Dulcinea" por "Dulcinea del Toboso"), pero
    # tiene que ganar con CLARIDAD: si dos opciones comparten palabras
    # ("Miguel de Cervantes" / "Miguel de Unamuno"), mejor no adivinar.
    if pesos[mejor] >= 0.5 and pesos[mejor] - segundo >= 0.2:
        return mejor

    # 2) Por ORDEN, y 3) por letra.
    #
    # ⚠️ El orden importa: en español y portugués el artículo que acompaña al
    # ordinal ES una letra de opción ("a terceira", "la a"). Mirando primero
    # el ordinal, "a terceira" es la tercera; al revés era la A.
    idx = _ordinal_en(tokens, corta)
    if idx is None:
        idx = _letra_en(tokens, corta)
    if idx is not None and idx < len(options):
        return idx
    return None


def sounds_like_same(a: str, b: str) -> bool:
    """¿Dos frases son prácticamente la misma cosa dicha?

    Se usa como guarda anti-eco: lo que entra por el micrófono justo después
    de que MECH hable suele ser su propio parlante, pero recortado, no
    idéntico. Por eso se compara por contención con un mínimo de longitud,
    igual que en el traductor.
    """
    na, nb = normalize(a or ""), normalize(b or "")
    if not na or not nb:
        return False
    if na == nb:
        return True
    corto, largo = (na, nb) if len(na) <= len(nb) else (nb, na)
    # En japonés y chino cada carácter dice mucho más: con 4 ya es una frase.
    minimo = 4 if _tiene_cjk(corto) else 8
    return corto in largo and len(corto) >= 0.6 * len(largo) and len(corto) >= minimo


def is_sleep(text: str) -> bool:
    """Frase de reposo en español."""
    return matches_any(text, config.VOICE_SLEEP_PHRASES)


def is_wake(text: str) -> bool:
    """Frase de despertar en español ("ok MECH", "despierta MECH")."""
    return matches_any(text, config.VOICE_WAKE_PHRASES)


def is_sleep_en(text: str) -> bool:
    """Frase de reposo en inglés ("stop listening", "go to sleep")."""
    return matches_any(text, config.VOICE_SLEEP_PHRASES_EN)


def is_wake_en(text: str) -> bool:
    """Frase de despertar en INGLÉS ("wake up MECH")."""
    return matches_any(text, config.VOICE_WAKE_PHRASES_EN)


def is_wake_fr(text: str) -> bool:
    """Frase de despertar en FRANCÉS ("bonjour MECH", "réveille MECH")."""
    return matches_any(text, config.VOICE_WAKE_PHRASES_FR)


def is_wake_pt(text: str) -> bool:
    """Frase de despertar en PORTUGUÉS ("bom dia MECH", "acorda MECH")."""
    return matches_any(text, config.VOICE_WAKE_PHRASES_PT)


# Idioma -> (interruptor en config, lista de frases de despertar). El orden
# importa: los idiomas EXTRA se comprueban ANTES que el español, porque el
# español tiene frases muy cortas ("despierta" a secas) y podría quedarse con
# un despertar que era de otro idioma.
_WAKE_LISTS = (
    ("en", "WAKE_ENGLISH_ENABLED", "VOICE_WAKE_PHRASES_EN"),
    ("fr", "WAKE_FRENCH_ENABLED", "VOICE_WAKE_PHRASES_FR"),
    ("pt", "WAKE_PORTUGUESE_ENABLED", "VOICE_WAKE_PHRASES_PT"),
    ("de", "WAKE_GERMAN_ENABLED", "VOICE_WAKE_PHRASES_DE"),
    ("it", "WAKE_ITALIAN_ENABLED", "VOICE_WAKE_PHRASES_IT"),
    ("ja", "WAKE_JAPANESE_ENABLED", "VOICE_WAKE_PHRASES_JA"),
    ("ru", "WAKE_RUSSIAN_ENABLED", "VOICE_WAKE_PHRASES_RU"),
    ("zh", "WAKE_CHINESE_ENABLED", "VOICE_WAKE_PHRASES_ZH"),
    ("ko", "WAKE_KOREAN_ENABLED", "VOICE_WAKE_PHRASES_KO"),
    ("es", None, "VOICE_WAKE_PHRASES"),
)


def wake_language(text: str, only: str | None = None) -> str | None:
    """Idioma con el que se despertó a MECH, o None si no fue un despertar.

    Los idiomas extra se comprueban PRIMERO (ver `_WAKE_LISTS`) y solo si su
    interruptor está encendido; el español siempre, y de último.

    `only` limita la búsqueda a UN idioma (ver `wake_language_awake`).
    """
    for code, flag, lista in _WAKE_LISTS:
        if only and code != only:
            continue
        if flag and not getattr(config, flag, False):
            continue
        if matches_any(text, getattr(config, lista, []) or []):
            return code
    return None


def wake_language_awake(text: str) -> str | None:
    """Lo mismo que `wake_language`, pero con MECH ya DESPIERTO.

    En reposo cualquiera de los nueve idiomas lo despierta (así se elige el
    idioma). Despierto, el idioma ya está elegido y queda fijo hasta que se
    duerme: solo se reconoce la frase de despertar del idioma ACTIVO (que el
    bucle ignora, no es un comando). La de otro idioma devuelve None y sigue
    su camino como una frase cualquiera — sin esto, un «OK MECH, tell me
    about…» dicho en inglés lo pasaba a español.

    Con `VOICE_STRICT_LANGUAGE=false` vuelve lo de antes: la frase de otro
    idioma cambia el idioma estando despierto.
    """
    if config.VOICE_STRICT_LANGUAGE:
        return wake_language(text, only=lang.current())
    return wake_language(text)


def is_sleep_any(text: str) -> bool:
    """Frase de reposo.

    Igual que el resto de comandos, en el idioma con el que se despertó a
    MECH (ver `_frases_activas`); las de todos a la vez solo con
    `VOICE_STRICT_LANGUAGE=false`.
    """
    return matches_any(text, _frases_activas("VOICE_SLEEP_PHRASES"))
