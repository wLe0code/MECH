"""Modo TRADUCTOR — MECH como intérprete entre dos personas.

Idea (pedido del equipo, sep 2026): en el stand se acerca alguien que no
habla español y MECH hace de intérprete. Hay **dos formas de usarlo**, y la
diferencia es cuántas frases traduce antes de callarse:

| Se le dice | Qué hace |
|---|---|
| «traduce MECH» | traduce UNA frase y se calla |
| «activa modo traductor» | se queda traduciendo, frase tras frase |
| «desactiva el modo traductor» | sale del continuo |

El modo de UNA frase es el original y sigue igual. El CONTINUO lo pidió el
equipo en sep 2026 para conversaciones de verdad, donde repetir el comando
en cada frase es insufrible.

⚠️ **El continuo reabre el problema del eco a propósito, y por eso está
blindado aparte.** La primera versión del traductor (jul 2026) era continua
y se traducía a sí misma sin fin: MECH hablaba, el micrófono captaba su
parlante, traducía su traducción, y la de esa. Lo que lo resolvió entonces
fue ir por turnos. Ahora que el continuo vuelve por pedido explícito, lo que
impide el bucle son TRES cosas, y hay que mantener las tres:

  1. `TRANSLATOR_CONTINUOUS_DRAIN_SECONDS` (1.2 s, más que en el modo de una
     frase): el micrófono no se abre hasta que el parlante ha drenado.
  2. `looks_like_own_echo()` compara contra las ÚLTIMAS `_MAX_RECUERDOS`
     cosas que MECH dijo, no solo contra la última. Con el buffer del
     parlante Bluetooth, lo que entra puede ser de dos frases atrás.
  3. Y lo más importante: **cuando la guarda salta, MECH no dice nada** —
     descarta y vuelve a escuchar. Sin voz nueva no hay nada que realimentar,
     así que el bucle infinito no puede existir aunque la guarda falle a
     ratos.

Si aun así entra eco en el evento, la perilla es la 1 (Ajustes -> «Espera
del traductor continuo»), y después el «Umbral ruido».

    Usuario:  «ok MECH»               -> despierta
    Usuario:  «traduce MECH»          -> traduce UNA frase
    MECH:     «¿De qué idioma a qué idioma traduzco?»   (+ chime)
    Usuario:  «de español a francés»
    MECH:     «Listo, traduzco entre español y francés. ¿Qué quieres que
               traduzca?»                                (+ chime)
    Usuario:  «Buenos días, ¿cómo está?»
    MECH:     «Bonjour, comment allez-vous ?»   -> y se CALLA
    Usuario:  «traduce MECH»          -> ya sabe el par, va directo:
    MECH:     «¿Qué quieres que traduzca?»                (+ chime)
    Visitante:«Très bien, merci»
    MECH:     «Muy bien, gracias.»              -> y se calla otra vez

Y en CONTINUO, lo mismo pero sin repetir el comando:

    Usuario:  «activa modo traductor»
    MECH:     «¿De qué idioma a qué idioma traduzco?»   (+ chime)
    Usuario:  «de español a francés»
    MECH:     «Modo traductor activado. Traduzco entre español y francés
               hasta que me digas que lo desactive.»     (+ chime)
    Usuario:  «Buenos días»
    MECH:     «Bonjour»                      -> y sigue escuchando
    Visitante:«Merci beaucoup»
    MECH:     «Muchas gracias»                -> y sigue escuchando
    Usuario:  «desactiva el modo traductor»
    MECH:     «Listo, dejo de traducir.»

**El par de idiomas se RECUERDA** entre un «traduce MECH» y el siguiente: en
una conversación real sería insufrible repetirlo cada frase. Se olvida al
dormirse, con «deja de traducir» o con el paro de emergencia. Para cambiarlo
sin dormir a MECH, basta nombrar los idiomas en el propio comando
(«traduce MECH del inglés al portugués»).

**Va en LOS DOS SENTIDOS** (`TRANSLATOR_AUTO_DETECT`, por defecto sí): Whisper
detecta en cuál de los dos idiomas del par se dijo la frase y MECH la traduce
al otro. Ponerlo en false fija el sentido (origen -> destino): menos cómodo,
pero no se equivoca nunca. Útil si el par es español/portugués, que Whisper
confunde en frases muy cortas.

**No pasa por el flujo normal de Claude.** Nada de obras, gestos, videos ni
proyección: es una llamada corta de traducción (`llm.translate`) y el TTS.

Este módulo guarda SOLO el estado (igual de simple que `lang.py`, y por el
mismo motivo: lo importan `mech_app` y `server` sin ciclos). Quien habla, pide
la traducción y pinta subtítulos es `mech_app`.
"""

from __future__ import annotations

from collections import deque

import config
import lang

# En qué punto del proceso estamos:
#   "off"    = no está traduciendo (puede conservar el par de la vez anterior)
#   "pair"   = preguntó de qué idioma a qué idioma y espera la respuesta
#   "phrase" = preguntó qué traducir y espera LA frase
_stage: str = "off"
# ¿Modo CONTINUO? Con True, tras cada traducción vuelve a "phrase" en vez de
# apagarse, y solo sale con «desactiva el modo traductor», al dormirlo o con
# el paro de emergencia.
_continuous: bool = False
# Par de idiomas. Sobrevive a "off" a propósito: ver el docstring.
_src: str | None = None
_dst: str | None = None
# Las últimas cosas que MECH dijo en voz alta dentro del modo (preguntas y
# traducciones). Guarda anti-eco: si lo siguiente que oye es prácticamente
# una de ellas, es su propio parlante y se descarta.
#
# Son VARIAS y no una sola por el modo continuo: el parlante Bluetooth
# arrastra buffer, así que lo que entra tarde puede ser de dos frases atrás.
_MAX_RECUERDOS = 3
_spoken: deque[str] = deque(maxlen=_MAX_RECUERDOS)
# Ecos seguidos que se han descartado. Solo sirve para avisar en el panel: si
# se descartan varios seguidos, el parlante está entrando siempre y hay que
# subir `TRANSLATOR_CONTINUOUS_DRAIN_SECONDS`.
_echo_streak: int = 0


def stage() -> str:
    """En qué punto está: "off", "pair" o "phrase"."""
    return _stage


def is_active() -> bool:
    """¿Está en medio de un turno de traducción (preguntando o escuchando)?"""
    return _stage != "off"


def is_awaiting_pair() -> bool:
    """¿Espera que le digan «de X a Y»?"""
    return _stage == "pair"


def is_awaiting_phrase() -> bool:
    """¿Espera LA frase que hay que traducir?"""
    return _stage == "phrase"


def pair() -> tuple[str | None, str | None]:
    return _src, _dst


def has_pair() -> bool:
    return bool(_src and _dst)


def is_continuous() -> bool:
    """¿Está en modo continuo (traduce hasta que le digan que pare)?"""
    return _continuous


def begin(
    src: str | None = None,
    dst: str | None = None,
    continuous: bool = False,
) -> str:
    """Arranca el traductor. Devuelve la etapa en que quedó.

    Con un par válido (dicho en el comando o elegido en el panel) lo fija y
    va directo a pedir la frase. Sin él, reutiliza el par que ya se sabía de
    la vez anterior. Y si no hay ninguno, pregunta por los idiomas.

    `continuous=True` es «activa modo traductor»: no se apaga solo al
    terminar una frase.
    """
    global _stage, _continuous, _echo_streak
    _spoken.clear()
    _echo_streak = 0
    _continuous = continuous
    if src and dst:
        set_pair(src, dst)
    _stage = "phrase" if has_pair() else "pair"
    return _stage


def set_pair(src: str, dst: str) -> bool:
    """Fija el par de idiomas y pasa a pedir la frase. False si no es válido."""
    global _src, _dst, _stage
    if src not in lang.SUPPORTED or dst not in lang.SUPPORTED or src == dst:
        return False
    _src, _dst = src, dst
    _stage = "phrase"
    return True


def finish() -> bool:
    """Acaba de traducir una frase. Devuelve True si SIGUE escuchando.

    - En modo de una frase: se calla y espera otro «traduce MECH».
      **Conserva el par de idiomas**, que es lo que permite encadenar frases
      sin repetirlo. Para olvidarlo del todo está `reset()`.
    - En modo CONTINUO: vuelve a quedarse esperando la siguiente frase, sin
      preguntar nada (una pregunta por frase sería insoportable, y además
      cada cosa que dice es eco en potencia).
    """
    global _stage
    _stage = "phrase" if _continuous else "off"
    return _continuous


def reset() -> None:
    """Sale del modo del todo (continuo incluido) y olvida el par."""
    global _stage, _continuous, _src, _dst, _echo_streak
    _stage = "off"
    _continuous = False
    _src = _dst = None
    _spoken.clear()
    _echo_streak = 0


def direction(detected: str | None) -> tuple[str, str]:
    """Para una frase, `(idioma en que se dijo, idioma al que hay que pasarla)`.

    Con detección automática, si Whisper dice que se habló en el idioma
    DESTINO se invierte el sentido (es el otro interlocutor contestando).
    Cualquier otra cosa —incluido no haber detectado nada— se trata como el
    idioma ORIGEN, que es la dirección que pidió el usuario.
    """
    src, dst = _src or lang.DEFAULT, _dst or lang.DEFAULT
    if detected == dst:
        return dst, src
    return src, dst


def remember_spoken(text: str) -> None:
    """Guarda algo que MECH acaba de decir, para la guarda anti-eco.

    Se llama con las PREGUNTAS y también con cada TRADUCCIÓN. Lo segundo es
    lo que hace falta en el modo continuo: ahí lo que más se puede colar por
    el micrófono es la traducción que acaba de decir.
    """
    if text:
        _spoken.append(text)


def _es_el_mismo(a: str, b: str) -> bool:
    """¿Dos textos ya normalizados son prácticamente el mismo?

    Se compara por contención porque el parlante suele entrar recortado, no
    idéntico. El umbral del 60 % y el mínimo de 8 caracteres evitan que una
    palabra suelta que coincida bloquee a un visitante que sí está hablando.
    """
    if not a or not b:
        return False
    if a == b:
        return True
    corto, largo = (a, b) if len(a) <= len(b) else (b, a)
    return corto in largo and len(corto) >= 0.6 * len(largo) and len(corto) >= 8


def looks_like_own_echo(text: str, normalize) -> bool:
    """¿Lo que acaba de oír es su propia voz saliendo del parlante?

    En el modo de UNA frase queda un hueco: entre la PREGUNTA («¿Qué quieres
    que traduzca?») y la frase del visitante el micrófono sí está abierto, y
    el parlante Bluetooth arrastra su buffer.

    En el modo CONTINUO el hueco es todavía más claro, porque el micrófono se
    abre justo detrás de cada traducción. Por eso se compara contra las
    últimas `_MAX_RECUERDOS` cosas que dijo y no solo contra la última: con
    buffer de por medio, lo que entra tarde puede ser de dos frases atrás.

    `normalize` es `voice_phrases.normalize` (se pasa como argumento para no
    importar ese módulo aquí y evitar un ciclo).
    """
    global _echo_streak
    if not text or not _spoken:
        return False
    oido = normalize(text)
    if any(_es_el_mismo(oido, normalize(dicho)) for dicho in _spoken):
        _echo_streak += 1
        return True
    _echo_streak = 0
    return False


def echo_streak() -> int:
    """Ecos seguidos descartados. Si sube, hay que alargar la espera."""
    return _echo_streak


def snapshot() -> dict:
    """Lo que ve el panel en `state["translator"]`."""
    return {
        "stage": _stage,
        "active": _stage != "off",
        "awaiting_pair": _stage == "pair",
        "awaiting_phrase": _stage == "phrase",
        "continuous": _continuous,
        "src": _src,
        "dst": _dst,
        "auto_detect": bool(config.TRANSLATOR_AUTO_DETECT),
    }
