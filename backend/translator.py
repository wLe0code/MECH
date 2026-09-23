"""Modo TRADUCTOR — MECH como intérprete entre dos personas.

Idea (pedido del equipo, sep 2026): en el stand se acerca alguien que no
habla español. Se le dice **«traduce MECH»**, él pregunta qué hay que
traducir, escucha UNA frase, la dice en el otro idioma y **se calla**. Para
traducir otra frase hay que volver a decir «traduce MECH».

    Usuario:  «ok MECH»               -> despierta
    Usuario:  «traduce MECH»          -> entra en modo traductor
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

**Un turno por comando, a propósito.** La primera versión se quedaba
escuchando en bucle y el problema gordo era el eco: MECH hablaba, el
micrófono captaba su propio parlante, traducía su traducción, y la de esa —
sin fin. Con un turno por comando el micrófono nunca está abierto justo
después de que MECH hable, así que ese bucle no puede existir. **No lo
vuelvas a hacer continuo sin resolver el eco de otra manera.**

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

import config
import lang

# En qué punto del proceso estamos:
#   "off"    = no está traduciendo (puede conservar el par de la vez anterior)
#   "pair"   = preguntó de qué idioma a qué idioma y espera la respuesta
#   "phrase" = preguntó qué traducir y espera LA frase (una sola)
_stage: str = "off"
# Par de idiomas. Sobrevive a "off" a propósito: ver el docstring.
_src: str | None = None
_dst: str | None = None
# Lo último que MECH dijo en voz alta dentro del modo (la pregunta o la
# traducción). Guarda anti-eco: si lo siguiente que oye es prácticamente eso,
# es su propio parlante y se descarta.
_last_spoken: str = ""


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


def begin(src: str | None = None, dst: str | None = None) -> str:
    """Arranca un turno de traducción. Devuelve la etapa en que quedó.

    Con un par válido (dicho en el comando o elegido en el panel) lo fija y
    va directo a pedir la frase. Sin él, reutiliza el par que ya se sabía de
    la vez anterior. Y si no hay ninguno, pregunta por los idiomas.
    """
    global _stage, _last_spoken
    _last_spoken = ""
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


def finish() -> None:
    """Terminó de traducir UNA frase: se calla y espera otro «traduce MECH».

    **Conserva el par de idiomas**, que es lo que permite encadenar frases sin
    repetirlo. Para olvidarlo del todo está `reset()`.
    """
    global _stage
    _stage = "off"


def reset() -> None:
    """Sale del modo del todo y olvida el par de idiomas."""
    global _stage, _src, _dst, _last_spoken
    _stage = "off"
    _src = _dst = None
    _last_spoken = ""


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
    """Guarda lo último que MECH dijo, para la guarda anti-eco."""
    global _last_spoken
    _last_spoken = text or ""


def looks_like_own_echo(text: str, normalize) -> bool:
    """¿Lo que acaba de oír es su propia voz saliendo del parlante?

    Con un turno por comando el eco ya casi no puede aparecer, pero queda un
    hueco: entre la PREGUNTA («¿Qué quieres que traduzca?») y la frase del
    visitante el micrófono sí está abierto, y el parlante Bluetooth arrastra
    su buffer. Sin esta guarda, MECH traduciría su propia pregunta.

    `normalize` es `voice_phrases.normalize` (se pasa como argumento para no
    importar ese módulo aquí y evitar un ciclo). Se compara por contención:
    el parlante suele entrar recortado, no idéntico.
    """
    if not _last_spoken or not text:
        return False
    a, b = normalize(text), normalize(_last_spoken)
    if not a or not b:
        return False
    if a == b:
        return True
    corto, largo = (a, b) if len(a) <= len(b) else (b, a)
    # Solo cuenta si lo corto es una parte GRANDE de lo largo: una palabra
    # suelta que coincida no puede bloquear a un visitante que habla.
    return corto in largo and len(corto) >= 0.6 * len(largo) and len(corto) >= 8


def snapshot() -> dict:
    """Lo que ve el panel en `state["translator"]`."""
    return {
        "stage": _stage,
        "active": _stage != "off",
        "awaiting_pair": _stage == "pair",
        "awaiting_phrase": _stage == "phrase",
        "src": _src,
        "dst": _dst,
        "auto_detect": bool(config.TRANSLATOR_AUTO_DETECT),
    }
