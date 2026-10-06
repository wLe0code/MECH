"""Comprueba la regla de oct 2026: cada comando, en el idioma del despertar.

Por qué existe: lo que pidió el equipo es fácil de romper sin darse cuenta,
porque no da error — simplemente «hey MECH» vuelve a cortar a un MECH
despierto en español y nadie lo nota hasta el evento. Aquí se mira, en los
NUEVE idiomas:

  1. que cada idioma entienda TODAS sus frases (las listas de `config.py`);
  2. que en cada idioma valgan SUS comandos y no los de los otros ocho;
  3. el despertar: en reposo elige idioma cualquiera, despierto queda fijo;
  4. el saludo: en español, y que su propio eco no despierte a MECH;
  5. el bucle de voz DE VERDAD (`server._voice_loop_worker`) con un
     micrófono, un Whisper y una voz de mentira, de punta a punta.

    python scripts/probar_comandos_idioma.py

Sale 1 si algo falla. No necesita hardware ni claves de API.

`scripts/probar_idiomas.py` mide otra cosa: que las frases de los nueve
idiomas no se pisen con TODAS las listas juntas (apaga esta regla a
propósito). Al tocar las listas o el matcher, correr los dos.

⚠️ Esto comprueba el TEXTO. Cómo transcribe Whisper cada idioma en la Pi
solo se ve con el micrófono de verdad.
"""

from __future__ import annotations

import importlib.abc
import importlib.machinery
import importlib.util
import os
import sys
import time
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))
for _k in ("ANTHROPIC_API_KEY", "ELEVENLABS_API_KEY", "GOOGLE_API_KEY"):
    os.environ.setdefault(_k, "x")
# Lo que se mide aquí son los DEFAULTS del código, no lo que tenga guardado
# el .env de esta máquina.
os.environ["GREETING_LANGUAGE"] = "es"
os.environ["VOICE_STRICT_LANGUAGE"] = "true"


# --- Módulos de mentira para lo que no esté instalado ---------------------
# En el laptop casi nunca están las dependencias del robot (micrófono,
# Whisper, FastAPI...). Nada de eso hace falta para decidir si una frase es
# un comando, así que lo que falte se sustituye por un módulo vacío.
class _Any:
    def __init__(self, *a, **k):
        pass

    def __getattr__(self, n):
        return _Any()

    def __call__(self, *a, **k):
        return _Any()


class _ModuloFalso(types.ModuleType):
    def __getattr__(self, n):
        if n.startswith("__"):
            raise AttributeError(n)
        # En mayúscula suele ser una clase de la que se hereda (BaseModel).
        return _Any if n[:1].isupper() else _Any()


class _Falsos(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    RAICES = ("dotenv", "sounddevice", "soundfile", "webrtcvad", "elevenlabs",
              "anthropic", "faster_whisper", "serial", "google", "fastapi",
              "pydantic", "uvicorn", "cv2", "PIL", "requests", "httpx")

    def __init__(self):
        self.faltan = set()
        for raiz in self.RAICES:
            try:
                if importlib.util.find_spec(raiz) is None:
                    self.faltan.add(raiz)
            except Exception:
                self.faltan.add(raiz)
        if "google" not in self.faltan:
            try:
                if importlib.util.find_spec("google.genai") is None:
                    self.faltan.add("google")
            except Exception:
                self.faltan.add("google")

    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in self.faltan:
            return importlib.machinery.ModuleSpec(name, self, is_package=True)
        return None

    def create_module(self, spec):
        mod = _ModuloFalso(spec.name)
        mod.__path__ = []
        return mod

    def exec_module(self, module):
        pass


sys.meta_path.insert(0, _Falsos())

import config  # noqa: E402
import lang  # noqa: E402
import voice_phrases as vp  # noqa: E402

SUFIJO = {"es": "", "en": "_EN", "fr": "_FR", "pt": "_PT", "de": "_DE",
          "it": "_IT", "ja": "_JA", "ru": "_RU", "zh": "_ZH"}

fallos: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("  ok   " if cond else "  FALLA") + " " + msg)
    if not cond:
        fallos.append(msg)


# Cada lista de `config` con la función que la reconoce.
FAMILIAS = {
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

# Una frase "de bandera" por comando e idioma, escrita como la diría un
# visitante. Están elegidas para que NO se parezcan a la de otro idioma: hay
# palabras casi idénticas («avanza» / «avance» / «avança», «traduce» /
# «traduz» / «traduci», «claro» / «klar») que el matcher perdona a propósito,
# y esas no sirven para medir la separación (salen en el punto 2 bis).
BANDERAS = {
    "interrumpir": (vp.is_interrupt, {
        "es": "oye mech", "en": "hey mech", "fr": "attends mech",
        "pt": "escuta mech", "de": "warte, MECH", "it": "aspetta, MECH",
        "ja": "ねえ、MECH", "ru": "Эй, MECH", "zh": "嘿，MECH"}),
    "dormir": (vp.is_sleep_any, {
        "es": "para de escuchar", "en": "stop listening",
        "fr": "bonne nuit mech", "pt": "boa noite mech",
        "de": "Gute Nacht, MECH", "it": "Buonanotte, MECH",
        "ja": "おやすみ、MECH", "ru": "Спокойной ночи, MECH", "zh": "晚安，MECH"}),
    "mirar afuera": (vp.is_look_outward, {
        "es": "mira hacia afuera", "en": "look outside",
        "fr": "regarde dehors", "pt": "olha para fora", "de": "Schau raus",
        "it": "Guarda fuori", "ja": "外を見て", "ru": "Посмотри наружу",
        "zh": "向外看"}),
    "volver a proyectar": (vp.is_back_to_projection, {
        "es": "regresa a proyectar", "en": "back to projecting",
        "fr": "retourne projeter", "pt": "volta a projetar",
        "de": "Zurück zur Projektion", "it": "Torna a proiettare",
        "ja": "投影に戻って", "ru": "Вернись к проекции", "zh": "回去投影"}),
    "marketing": (vp.is_play_marketing, {
        "es": "proyecta marketing", "en": "play marketing",
        "fr": "lance le marketing", "pt": "toca marketing",
        "de": "Zeig Marketing", "it": "Riproduci marketing",
        "ja": "マーケティングを再生して", "ru": "Покажи маркетинг",
        "zh": "播放宣传片"}),
    "trivia": (vp.is_trivia, {
        "es": "juguemos una trivia", "en": "quiz me", "fr": "jouons au quiz",
        "pt": "vamos jogar o quiz", "de": "Quiz spielen",
        "it": "Facciamo un quiz", "ja": "クイズをしよう",
        "ru": "Сыграем в викторину", "zh": "玩问答"}),
    "sí": (vp.is_yes, {
        "es": "por supuesto", "en": "yes", "fr": "oui", "pt": "com certeza",
        "de": "gerne", "it": "volentieri", "ja": "はい", "ru": "Конечно",
        "zh": "好的"}),
    # «traduce» / «traduis» / «traduz» / «traduci» son la misma palabra con
    # una letra de diferencia: entre lenguas romances no se pueden separar.
    "traducir": (vp.is_translate, {
        "es": "traduce mech", "en": "translate mech", "de": "Übersetze, MECH",
        "ja": "翻訳して、MECH", "ru": "Переведи, MECH", "zh": "翻译，MECH"}),
}


def probar_frases() -> None:
    print("\n=== 1. Cada idioma entiende todas sus frases ===")
    for code in lang.SUPPORTED:
        lang.set_current(code)
        total, malas = 0, []
        for base, fn in FAMILIAS.items():
            for frase in getattr(config, base + SUFIJO[code]):
                total += 1
                if not fn(frase):
                    malas.append(f"{base} «{frase}»")
        check(not malas, f"[{code}] {lang.label(code):<10} {total} frases"
              + (" — no se reconocen: " + "; ".join(malas) if malas else ""))

    print("\n=== 2. En cada idioma valen SUS comandos, no los de los otros ===")
    for nombre, (fn, frases) in BANDERAS.items():
        for activo in frases:
            lang.set_current(activo)
            propia = fn(frases[activo])
            ajenas = [f"{c}:«{f}»" for c, f in frases.items()
                      if c != activo and fn(f)]
            check(
                propia and not ajenas,
                f"[{activo}] {nombre}: «{frases[activo]}» sí"
                + (f" — y se cuela {ajenas}" if ajenas
                   else f", las de los otros {len(frases) - 1} no"),
            )

    print("\n  -- 2 bis. (informativo) lo que sigue valiendo de otro idioma --")
    print("     Es casi la misma palabra en los dos idiomas; no es un fallo.")
    for activo in lang.SUPPORTED:
        lang.set_current(activo)
        cuelan: list[str] = []
        for otro in lang.SUPPORTED:
            if otro == activo:
                continue
            for base, fn in FAMILIAS.items():
                cuelan += [f for f in getattr(config, base + SUFIJO[otro])
                           if fn(f) and f not in cuelan]
        muestra = ", ".join(cuelan[:6]) + ("…" if len(cuelan) > 6 else "")
        print(f"     [{activo}] {len(cuelan):>2}: {muestra}")

    print("\n  -- «oye MECH, <algo más>»: la petición pegada --")
    lang.set_current("en")
    check(vp.strip_interrupt("Hey Mech, tell me about Malpaís") == "tell me about Malpaís",
          "[en] «hey MECH, tell me about Malpaís» se queda con la petición")
    check(vp.strip_interrupt("oye mech, cuéntame de Malpaís") == "",
          "[en] «oye MECH, cuéntame…» no se toma como interrupción")
    lang.set_current("es")
    check(vp.strip_interrupt("Oye MECH, cuéntame de Malpaís") == "cuéntame de Malpaís",
          "[es] «oye MECH, cuéntame de Malpaís» se queda con la petición")
    lang.set_current("ja")
    check(vp.strip_interrupt("ねえMECH、別の話をして") == "別の話をして",
          "[ja] «ねえMECH、別の話をして» se queda con la petición")
    check(vp.strip_interrupt("oye mech, cuéntame otra cosa") == "",
          "[ja] «oye MECH, cuéntame…» no se toma como interrupción")

    print("\n  -- el eco de «dejo de traducir» se reconoce en su idioma --")
    for code in lang.SUPPORTED:
        lang.set_current(code)
        dicho = lang.say("translate_off", code)
        check(vp.is_translate_stop(dicho), f"[{code}] «{dicho}»")

    print("\n  -- con la regla APAGADA vuelve lo de antes --")
    config.VOICE_STRICT_LANGUAGE = False
    lang.set_current("es")
    check(vp.is_interrupt("hey mech") and vp.is_sleep_any("stop listening")
          and vp.is_interrupt("ねえ、MECH"),
          "[es] «hey MECH», «stop listening» y «ねえ MECH» vuelven a valer")
    config.VOICE_STRICT_LANGUAGE = True
    check(not vp.is_interrupt("hey mech") and not vp.is_interrupt("ねえ、MECH"),
          "y al encenderla de nuevo, ya no")
    lang.reset()


# Cómo se despierta en cada idioma, escrito como lo escribe Whisper.
DESPERTAR = {
    "es": "ok mech", "en": "wake up mech", "fr": "bonjour mech",
    "pt": "bom dia mech", "de": "Guten Tag, MECH", "it": "Ciao MECH",
    "ja": "こんにちは、MECH", "ru": "Привет, MECH", "zh": "你好，MECH",
}


def probar_despertar() -> None:
    print("\n=== 3. Despertar: en reposo eligen idioma los nueve ===")
    lang.reset()
    for code, frase in DESPERTAR.items():
        check(vp.wake_language(frase) == code, f"reposo: «{frase}» -> {code}")
    for frase in ("hola mech", "hello mech", "cuéntame de malpaís"):
        check(vp.wake_language(frase) is None, f"reposo: «{frase}» -> no despierta")

    print("\n  -- despierto, el idioma queda fijo --")
    for activo, propia in DESPERTAR.items():
        lang.set_current(activo)
        ajenas = [f for c, f in DESPERTAR.items() if c != activo]
        if activo != "es":
            ajenas.append("oye mech")  # también está en la lista de despertar española
        cuelan = [f for f in ajenas if vp.wake_language_awake(f)]
        check(
            vp.wake_language_awake(propia) == activo and not cuelan,
            f"[{activo}] «{propia}» es la suya; las de los otros {len(ajenas)} "
            "no cambian el idioma" + (f" — se cuela {cuelan}" if cuelan else ""),
        )
    lang.reset()


def probar_saludo() -> None:
    print("\n=== 4. El saludo ===")
    check(config.GREETING_LANGUAGE == "es", "por defecto el saludo va en español")
    texto = lang.say("greeting", config.GREETING_LANGUAGE)
    print(f"         «{texto}»")
    check(texto.startswith("¡Hola! Soy MECH"), "es la frase en español")
    # Lo que Whisper puede escribir al oír el saludo por el parlante. Ninguna
    # puede contar como un despertar (en NINGUNO de los nueve idiomas), o MECH
    # se despertaría solo al saludar.
    for eco in (texto, "Hola, soy Mec. Un gusto verte hoy aquí.",
                "ola soy mesh un gusto verte hoy aqui", "soy MECH un gusto verte",
                "Hola, soy Mech.", "un gusto verte hoy aquí"):
        sale = vp.wake_language(eco)
        check(sale is None, f"su eco no lo despierta: «{eco}»"
              + (f" — despierta en {sale}" if sale else ""))


# ===========================================================================
# 5. El bucle de voz DE VERDAD, con micrófono/Whisper/voz de mentira
# ===========================================================================
def probar_bucle() -> None:
    print("\n=== 5. Bucle de voz real (micrófono, Whisper y voz simulados) ===")
    import numpy as np

    import mech_app

    class LinkFalso:
        is_connected = False
        on_status = None

        def __getattr__(self, n):
            return lambda *a, **k: None

    mech_app.get_link = lambda: LinkFalso()
    import maneuvers
    import server
    import stt
    import tts

    app = mech_app.get_app()
    dicho: list[str] = []          # lo que MECH dice en voz alta
    a_claude: list[str] = []       # lo que llega como petición normal
    maniobras: list[str] = []      # órdenes de movimiento ejecutadas
    dormir_real = time.sleep

    tts.speak = lambda texto, *a, **k: dicho.append(texto)
    tts.play_chime = lambda *a, **k: None
    stt.get_model = lambda *a, **k: None
    stt.get_interrupt_model = lambda *a, **k: None
    app.log = lambda *a, **k: None
    maneuvers.look_outward = lambda *a, **k: maniobras.append("afuera")
    maneuvers.back_to_projection = lambda *a, **k: maniobras.append("proyectar")
    maneuvers.advance = lambda *a, **k: maniobras.append("avanzar")
    app.play_playlist = lambda *a, **k: maniobras.append("marketing")
    app.start_translator = lambda *a, **k: maniobras.append("traductor")
    app.start_trivia = lambda *a, **k: maniobras.append("trivia")

    class PlanFalso:
        mode, title = "narration", "simulado"

    def _plan(texto, **k):
        a_claude.append(texto)
        return PlanFalso()

    mech_app.llm.plan_response = _plan
    mech_app.llm.append_turn = lambda h, t, p: h
    app.execute_plan = lambda plan: None

    def correr(guion, awake=False, idioma="es", antes=None, tarda=0.0):
        """Pasa `guion` (lo que "oye" el micrófono) por el bucle real.

        `antes(i)` se llama justo cuando termina de grabarse la frase i;
        `tarda` son los segundos que finge tardar Whisper en transcribir.
        """
        del dicho[:], a_claude[:], maniobras[:]
        lang.set_current(idioma)
        app.state.update(voice_awake=awake, voice_loop_active=True, language=idioma)
        app.chime_pending = False
        app.greeting_until = 0.0
        app.set_voice_phase("waiting" if awake else "dormant")
        cola = list(guion)
        actual = {"i": -1, "texto": ""}

        def grabar(**k):
            if not cola:
                app.state["voice_loop_active"] = False
                return None
            actual["i"] += 1
            actual["texto"] = cola.pop(0)
            if antes:
                antes(actual["i"])
            return np.zeros(stt.WHISPER_SAMPLE_RATE, dtype=np.float32)  # 1 s

        def transcribir(audio, *a, **k):
            if tarda:
                dormir_real(tarda)
            return actual["texto"]

        stt.record_until_silence = grabar
        stt.transcribe = transcribir
        stt.transcribe_any = lambda audio, *a, **k: (transcribir(audio), None)
        time.sleep = lambda s: None  # sin esperar los drenajes del parlante
        try:
            server._voice_loop_worker()
        finally:
            time.sleep = dormir_real
        return bool(app.state["voice_awake"]), lang.current()

    # -- Los nueve, de punta a punta ------------------------------------------
    # Despertar -> dos órdenes de OTRO idioma (no tienen que hacer nada: ni
    # cortar, ni dormir, ni cambiar el idioma; siguen como una frase normal)
    # -> girar con la suya -> dormir con la suya.
    for code in lang.SUPPORTED:
        ajenas = (["hey mech", "stop listening"] if code == "es"
                  else ["oye mech", "para de escuchar"])
        despierto, idioma = correr([
            DESPERTAR[code], *ajenas,
            BANDERAS["mirar afuera"][1][code], BANDERAS["dormir"][1][code],
        ])
        bien = (
            dicho[:1] == [lang.say("awake", code)]       # contesta en su idioma
            and a_claude == ajenas                       # las ajenas, a Claude
            and maniobras == ["afuera"]                  # la suya sí gira
            and not despierto and idioma == "es"         # se durmió y volvió a es
            and dicho[-1] == lang.say("dormant", code)   # y se despidió en el suyo
            and len(dicho) == 2                          # sin anunciar cambios
        )
        check(bien, f"[{code}] despierta, ignora {' / '.join('«%s»' % a for a in ajenas)}, "
                    "gira y se duerme con las suyas"
              + ("" if bien else f" — dijo {dicho}, a Claude {a_claude}, "
                                 f"maniobras {maniobras}, despierto={despierto}, idioma={idioma}"))

    # -- Despierto en español, la frase de despertar inglesa no lo cambia ----
    despierto, idioma = correr(["ok mech", "wake up mech", "こんにちは、MECH"])
    check(despierto and idioma == "es" and lang.say("switched", "en") not in dicho,
          "[es] «wake up MECH» / «こんにちは MECH» a media charla no cambian el idioma")
    despierto, idioma = correr(["wake up mech", "ok mech", "oye mech"])
    check(despierto and idioma == "en" and a_claude == ["ok mech", "oye mech"],
          "[en] «ok MECH» / «oye MECH» no lo pasan a español")

    # -- Con la regla apagada, lo de antes -----------------------------------
    config.VOICE_STRICT_LANGUAGE = False
    despierto, idioma = correr(["ok mech", "wake up mech", "para de escuchar"])
    check(lang.say("switched", "en") in dicho and not despierto,
          "regla APAGADA: «wake up MECH» cambia a inglés y «para de escuchar» lo duerme")
    config.VOICE_STRICT_LANGUAGE = True

    # -- El eco del saludo ----------------------------------------------------
    # MECH saluda en reposo, el micrófono lo graba y Whisper TARDA en
    # transcribirlo. Peor caso: lo que entiende suena a un despertar.
    def saludando(i):
        if i == 0:
            app.greeting_until = time.time() + 0.15   # el saludo acaba ya mismo

    despierto, _ = correr(["oye, soy mech"], antes=saludando, tarda=0.4)
    check(not despierto,
          "el eco del saludo no lo despierta aunque Whisper tarde en transcribirlo")

    def saludo_viejo(i):
        if i == 0:
            app.greeting_until = time.time() - 3.0    # saludó hace rato

    despierto, idioma = correr(["ok mech"], antes=saludo_viejo, tarda=0.4)
    check(despierto and idioma == "es",
          "y un «ok MECH» dicho después del saludo sí lo despierta")
    lang.reset()


def main() -> int:
    probar_frases()
    probar_despertar()
    probar_saludo()
    try:
        probar_bucle()
    except Exception as e:  # el bucle arrastra medio backend: que se vea por qué
        import traceback
        traceback.print_exc()
        check(False, f"no se pudo simular el bucle de voz: {e!r}")

    print()
    if fallos:
        print(f"{len(fallos)} FALLO(S):")
        for f in fallos:
            print("  -", f)
        return 1
    print("TODO BIEN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
