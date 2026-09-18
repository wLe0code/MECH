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

Hay CUATRO idiomas (es/en/fr/pt). Cada lista de `config.py` tiene sus
variantes `_EN`, `_FR` y `_PT`; `_todos_los_idiomas()` las junta.

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

import config
import lang


def normalize(text: str) -> str:
    """Minúsculas, sin acentos ni signos."""
    t = unicodedata.normalize("NFD", text.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = "".join(c if (c.isalnum() or c.isspace()) else " " for c in t)
    return " ".join(t.split())


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


def matches_any(text: str, phrases: list[str]) -> bool:
    norm_text = normalize(text)
    tokens = norm_text.split()
    if not tokens:
        return False
    for p in phrases:
        words = normalize(p).split()
        if words and all(any(_word_matches(w, tok) for tok in tokens) for w in words):
            return True
    return False


def _todos_los_idiomas(base: str) -> list[str]:
    """Junta la lista `base` con sus versiones _EN, _FR y _PT.

    Se aceptan TODAS siempre, sin mirar el idioma activo: si MECH narra en
    español y alguien le suelta "hey MECH" o "escuta MECH", igual queremos
    parar. Son frases largas y distintivas, no chocan entre sí.
    """
    frases: list[str] = []
    for sufijo in ("", "_EN", "_FR", "_PT"):
        frases += list(getattr(config, base + sufijo, []) or [])
    return frases


def _interrupt_phrases() -> list[str]:
    """Frases de interrupción de TODOS los idiomas."""
    return _todos_los_idiomas("VOICE_INTERRUPT_PHRASES")


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
        for w in normalize(phrase).split():
            hit = next(
                (i for i, tok in enumerate(norm)
                 if i not in usados and _word_matches(w, tok)),
                None,
            )
            if hit is None:
                usados = []
                break
            usados.append(hit)
        if usados:
            resto = text[tokens[max(usados)].end():]
            return resto.strip(" \t,.;:¿?¡!-–—\"'")
    return ""


# --- Órdenes de movimiento (no pasan por Claude) --------------------------
# "mira hacia afuera" / "regresa a proyectar". Se aceptan las listas de los
# CUATRO idiomas siempre: son frases largas y distintivas, no chocan con
# nada, y si Whisper transcribió en el idioma equivocado igual queremos
# obedecer.


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
}


def extract_seconds(text: str) -> float | None:
    """Los segundos que pide una orden, o None si no dice ninguno.

    Acepta dígitos ("avanza 10 segundos") y letra ("avanza diez segundos"),
    que es como lo transcribe Whisper casi siempre. Si no hay número, quien
    llame decide el valor por defecto.
    """
    tokens = normalize(text).split()
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
    return matches_any(text, _todos_los_idiomas("VOICE_ADVANCE_PHRASES"))


def is_retreat(text: str) -> bool:
    """¿Piden retroceder? ("retrocede cinco segundos")"""
    return matches_any(text, _todos_los_idiomas("VOICE_RETREAT_PHRASES"))


def is_look_outward(text: str) -> bool:
    """¿Le están pidiendo que gire 180° y salude hacia afuera?"""
    return matches_any(text, _todos_los_idiomas("VOICE_OUTWARD_PHRASES"))


def is_back_to_projection(text: str) -> bool:
    """¿Le están pidiendo que vuelva a su posición de proyección?"""
    return matches_any(text, _todos_los_idiomas("VOICE_PROJECT_PHRASES"))


def is_play_marketing(text: str) -> bool:
    """¿Piden proyectar el slot de marketing? ("proyecta marketing")

    Se aceptan las listas de todos los idiomas: "marketing" se escribe igual
    en los cuatro, así que no hay ambigüedad posible.
    """
    return matches_any(text, _todos_los_idiomas("VOICE_MARKETING_PHRASES"))


def is_translate(text: str) -> bool:
    """¿Piden entrar en modo traductor? ("traduce MECH", "modo traductor")"""
    return matches_any(text, _todos_los_idiomas("VOICE_TRANSLATE_PHRASES"))


def is_translate_stop(text: str) -> bool:
    """¿Piden salir del modo traductor? ("deja de traducir")"""
    return matches_any(text, _todos_los_idiomas("VOICE_TRANSLATE_STOP_PHRASES"))


def extract_language_pair(text: str) -> tuple[str | None, str | None]:
    """Los idiomas nombrados en "de español a francés", en ese orden.

    Devuelve `(origen, destino)`. Si solo se nombra UNO ("traduce al
    francés"), vuelve como destino y el origen queda en None — quien llame
    decide que el origen es el idioma activo. Si no se nombra ninguno,
    `(None, None)`.

    Los nombres de cada idioma (en los cuatro idiomas) están en
    `lang.language_words()`; el match usa el mismo matcher tolerante que el
    resto, así que "espanol", "espagnol" y "espanhol" caen todos en "es".
    """
    tokens = normalize(text).split()
    palabras = lang.language_words()
    encontrados: list[str] = []
    for tok in tokens:
        for code, variantes in palabras.items():
            if code in encontrados:
                continue
            if any(_word_matches(v, tok) for v in variantes):
                encontrados.append(code)
                break
    if len(encontrados) >= 2:
        return encontrados[0], encontrados[1]
    if len(encontrados) == 1:
        return None, encontrados[0]
    return None, None


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
    ("es", None, "VOICE_WAKE_PHRASES"),
)


def wake_language(text: str) -> str | None:
    """Idioma con el que se despertó a MECH, o None si no fue un despertar.

    Los idiomas extra se comprueban PRIMERO (ver `_WAKE_LISTS`) y solo si su
    interruptor está encendido; el español siempre, y de último.
    """
    for code, flag, lista in _WAKE_LISTS:
        if flag and not getattr(config, flag, False):
            continue
        if matches_any(text, getattr(config, lista, []) or []):
            return code
    return None


def is_sleep_any(text: str) -> bool:
    """Frase de reposo en cualquiera de los idiomas.

    Dormirse es inofensivo, así que se aceptan todas las listas sin importar
    el idioma activo (si Whisper transcribió raro, igual obedece).
    """
    return matches_any(text, _todos_los_idiomas("VOICE_SLEEP_PHRASES"))
