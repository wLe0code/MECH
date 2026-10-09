"""Prueba el MODO MÚSICA entero, en los diez idiomas, sin robot ni internet.

Por qué existe: el modo son cuatro preguntas seguidas con el micrófono
abriéndose detrás de cada una, en diez idiomas. Lo que se rompe aquí no da
error: MECH se contesta a sí mismo, o «no» pone otra canción, o la frase de
despedida vuelve a meterlo en el modo. Aquí se mira:

  1. Las FRASES, con el reconocedor de verdad y en cada idioma: que cada
     lista se reconozca, que entrar no sea salir, y que nada de lo que MECH
     dice con el micrófono a punto de abrirse sea una orden (ni un sí/no).
     La despedida es al revés: TIENE que casar con «salir», para que su eco
     muera en silencio.
  2. El MODO ENTERO por el bucle de voz real (`server._voice_loop_worker`),
     con micrófono, Whisper, voz, Claude, YouTube y pantalla de mentira: en
     cada idioma, una sesión completa (canción sin artista, pregunta el
     artista, suena, «otra», suena, «no»); cada frase que dice MECH tiene
     que ser la de ese idioma.
  3. Los casos raros: cortar con «oye MECH» (sola y con un pedido pegado),
     canción que no existe, sin internet, sin pantalla, no entender dos
     veces, cambiar de tema, dormirlo en medio, sin clave de YouTube, la
     cuota agotada, y el eco de la despedida.
  4. La BÚSQUEDA en YouTube con respuestas de mentira de Google: que descarte
     lo que no se puede o no se debe poner (videos que no dejan incrustarse,
     de mayores de edad, directos, «10 horas de…») y deje los karaokes al
     final.

Con `--red` busca además canciones de verdad en YouTube. Necesita la clave:
la variable `YOUTUBE_API_KEY` (o la línea en `backend/.env`).

    python scripts/probar_musica.py
    python scripts/probar_musica.py --red

Sale 1 si algo falla. No necesita hardware ni claves de API. Reutiliza el
arnés de `probar_comandos_idioma.py` (los módulos de mentira y `montar()`).

⚠️ Comprueba el TEXTO y el flujo. Cómo transcribe Whisper un título de
canción, lo que Claude entiende de verdad y que la pantalla de la Pi suene,
solo se ve con el robot.
"""

from __future__ import annotations

import io
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import probar_comandos_idioma as base  # noqa: E402  (instala los módulos de mentira)

config, lang, vp, check, SUFIJO = base.config, base.lang, base.vp, base.check, base.SUFIJO

# Lo que MECH dice con el micrófono a punto de abrirse DENTRO del modo.
ANTES_DEL_MICRO = ["music_ask", "music_ask_more", "music_artist",
                   "music_not_understood", "music_not_found", "music_error",
                   "music_again", "music_ack"]


def lista(nombre: str, code: str) -> list[str]:
    return getattr(config, nombre + SUFIJO[code])


def ordenes() -> dict:
    return {
        "entrar al modo": vp.is_music, "salir del modo": vp.is_music_stop,
        "otra canción": vp.is_music_more, "sí": vp.is_yes, "no": vp.is_no,
        "dormir": vp.is_sleep_any, "trivia": vp.is_trivia,
        "traducir": vp.is_translate, "mirar afuera": vp.is_look_outward,
        "volver a proyectar": vp.is_back_to_projection, "avanzar": vp.is_advance,
        "retroceder": vp.is_retreat, "marketing": vp.is_play_marketing,
        "interrumpir": vp.is_interrupt,
    }


def probar_frases() -> None:
    print("\n=== 1. Las frases del modo música, idioma por idioma ===")
    for code in lang.SUPPORTED:
        lang.set_current(code)
        malas: list[str] = []
        total = 0
        for nombre, fn in (("VOICE_MUSIC_PHRASES", vp.is_music),
                           ("VOICE_MUSIC_STOP_PHRASES", vp.is_music_stop),
                           ("VOICE_MUSIC_MORE_PHRASES", vp.is_music_more)):
            for frase in lista(nombre, code):
                total += 1
                if not fn(frase):
                    malas.append(f"{nombre}: no se reconoce «{frase}»")
        for frase in lista("VOICE_MUSIC_PHRASES", code):
            if vp.is_music_stop(frase):
                malas.append(f"entrar «{frase}» también sale")
            if vp.wake_language(frase) or vp.is_sleep_any(frase):
                malas.append(f"entrar «{frase}» despierta o duerme")
        for frase in lista("VOICE_MUSIC_STOP_PHRASES", code):
            if vp.is_music(frase):
                malas.append(f"salir «{frase}» también entra")
            if vp.is_sleep_any(frase):
                malas.append(f"salir «{frase}» duerme")
        for frase in lista("VOICE_MUSIC_MORE_PHRASES", code):
            # «otra» puede casar con el NO (en alemán «noch EIN Lied» está a
            # una letra de «nein»): por eso en el modo se mira antes que el no.
            for n, fn in ordenes().items():
                if n not in ("otra canción", "no") and fn(frase):
                    malas.append(f"otra «{frase}» también es «{n}»")
        # Lo que MECH dice justo antes de abrir el micrófono.
        dichas = [(k, lang.say(k, code)) for k in ANTES_DEL_MICRO]
        dichas += [(k + "+again", lang.say(k, code) + " " + lang.say("music_again", code))
                   for k in ("music_not_found", "music_error", "music_ack")]
        for clave, frase in dichas:
            total += 1
            if not frase:
                malas.append(f"falta {clave}")
            for n, fn in ordenes().items():
                if fn(frase):
                    malas.append(f"{clave} «{frase}» casa con «{n}»")
            if vp.wake_language(frase):
                malas.append(f"{clave} despierta")
        # Las dos que se dicen FUERA del modo (después se oyen órdenes
        # normales; un sí o un no ahí no significan nada).
        adios = lang.say("music_off", code)
        no_puedo = lang.say("music_unavailable", code)
        total += 2
        # La despedida casa con salir (su eco muere en silencio) y con nada más.
        if not vp.is_music_stop(adios):
            malas.append(f"la despedida «{adios}» NO casa con salir")
        for clave, frase in (("la despedida", adios), ("«no puedo poner música»", no_puedo)):
            if not frase:
                malas.append(f"falta {clave}")
            for n, fn in ordenes().items():
                if n in ("sí", "no") or (clave == "la despedida" and n == "salir del modo"):
                    continue
                if fn(frase):
                    malas.append(f"{clave} «{frase}» casa con «{n}»")
            if vp.wake_language(frase):
                malas.append(f"{clave} despierta")
        for clave, fmt in (("music_playing", {"title": "Despacito", "artist": "Luis Fonsi"}),
                           ("music_playing_title", {"title": "Despacito"})):
            anuncio = lang.say(clave, code, **fmt)
            if "{" in anuncio or any(v not in anuncio for v in fmt.values()):
                malas.append(f"{clave} mal formado: «{anuncio}»")
        if not lang.say("music_label", code):
            malas.append("falta music_label")
        check(not malas, f"{lang.label(code):<10} {total} frases" + ("" if not malas else ": " + "; ".join(malas)))
    lang.set_current("es")

    print("\n  -- una frase de bandera por idioma no vale en los otros nueve --")
    banderas = {"es": "pon música mech", "en": "play some music mech",
                "fr": "mets de la musique mech", "pt": "toca música mech",
                "de": "aktiviere den Musikmodus", "it": "attiva la modalità musica",
                "ja": "音楽モードにして", "ru": "поставь музыку MECH",
                "zh": "打开音乐模式", "ko": "음악 모드 켜줘"}
    for code, frase in banderas.items():
        lang.set_current(code)
        propio = vp.is_music(frase)
        ajenos = []
        for otro in lang.SUPPORTED:
            if otro != code:
                lang.set_current(otro)
                if vp.is_music(frase):
                    ajenos.append(otro)
        # «mets de la musique» y «metti la musica» son la misma frase en francés
        # y en italiano: el reconocedor perdona esa letra a propósito (mismo
        # sonido). Igual que «modo música» / «mode musique» / «music mode».
        sobran = [o for o in ajenos if (code, o) != ("fr", "it")]
        check(propio and not sobran,
              f"{lang.label(code):<10} «{frase}»" + (f" → también vale en {sobran}" if sobran else ""))
    lang.set_current("es")


# --- El mundo de mentira ----------------------------------------------------

CONOCIDAS = ("Despacito", "Thriller", "Lemon")
ARTISTAS = ("Luis Fonsi", "Michael Jackson", "Queen")


def montar():
    h = base.montar()
    app = h.app
    import music
    import youtube_music
    h.music = music
    h.youtube = youtube_music
    h.buscadas = []          # lo que se buscó en YouTube
    h.esperas = []           # cuánto iba a esperar el final de cada canción
    h.pantalla = "normal"    # cómo se porta la pantalla de proyección
    h.yt = "bien"            # cómo se porta YouTube: bien | sin clave | cuota | caida

    def interpreta(frase, language=None):
        h.pedidos.append(("cancion", frase))
        t = frase.lower()
        titulo = next((x for x in CONOCIDAS if x.lower() in t), "")
        artista = next((x for x in ARTISTAS if x.lower() in t), "")
        return {"is_song_request": bool(titulo or artista), "title": titulo, "artist": artista}

    def buscar(titulo, artista=""):
        h.buscadas.append((titulo, artista))
        if h.yt == "caida":
            raise OSError("sin internet")
        if h.yt == "cuota":
            raise youtube_music.ErrorYouTube("quotaExceeded", "se acabaron las búsquedas de hoy")
        if titulo == "Lemon":
            return []        # YouTube no tiene un video que se pueda poner
        return [{"id": "VIDEO000001", "title": titulo, "channel": "Canal", "seconds": 229, "thumb": ""},
                {"id": "VIDEO000002", "title": titulo + " (letra)", "channel": "Otro", "seconds": 231, "thumb": ""}]

    youtube_music.disponible = lambda: h.yt != "sin clave"
    youtube_music.por_que_no = lambda: "falta YOUTUBE_API_KEY en backend/.env"
    youtube_music.buscar = buscar
    h.mech_app.llm.interpret_song = interpreta
    app.interrupts = types.SimpleNamespace(start=lambda *a, **k: True, stop=lambda *a, **k: None)
    config.MUSIC_START_TIMEOUT = 0.05

    def emitir(tipo, **datos):
        h.eventos.append((tipo, datos))
        # La «pantalla»: cuando llega una canción, contesta como lo haría
        # frontend/music.js.
        if tipo == "music" and datos.get("stage") == "playing" and datos.get("track"):
            pid = datos["play_id"]
            videos = datos["track"]["youtube"]
            if h.pantalla == "apagada":
                return                       # nadie contesta
            if h.pantalla == "error":
                app.music_event(pid, "error", "YouTube no dejó reproducir el video aquí (código 150)")
                return
            # «segundo»: el primer video se negó y arrancó el siguiente.
            elegido = videos[1] if h.pantalla == "segundo" else videos[0]
            app.music_event(pid, "playing", "youtube:" + elegido["id"])
            h.esperas.append(app._music_wait_seconds(datos["track"]))
            if h.pantalla == "panel":
                # Alguien pulsa «Parar» en el panel a media canción.
                app.stop_music(announce=False)
                h.pantalla = "normal"
            elif h.pantalla.startswith("corta"):
                # Alguien dice «oye MECH» a media canción.
                resto = h.pantalla[len("corta"):].strip()
                app._on_interrupt((interrumpe(lang.current()) + " " + resto).strip())
                h.pantalla = "normal"
            else:
                app.music_event(pid, "ended")

    app.emit = emitir

    def correr(guion, idioma="es", awake=True):
        music.reset()
        del h.buscadas[:], h.esperas[:]
        app._music_play_id = 0
        return h.correr(guion, awake=awake, idioma=idioma)

    h.sesion = correr
    return h


def interrumpe(code: str) -> str:
    return base.BANDERAS["interrumpir"][1][code]


def dice(code: str, clave: str, **fmt) -> str:
    return lang.say(clave, code, **fmt)


def sonadas(h) -> list[dict]:
    return [d for t, d in h.eventos if t == "music" and d.get("stage") == "playing"]


def probar_sesiones(h) -> None:
    print("\n=== 2. Una sesión entera en cada idioma (bucle de voz real) ===")
    for code in lang.SUPPORTED:
        entrar = lista("VOICE_MUSIC_PHRASES", code)[0]
        otra = lista("VOICE_MUSIC_MORE_PHRASES", code)[0]
        no = lista("VOICE_NO_PHRASES", code)[0]
        h.pantalla, h.yt = "normal", "bien"
        h.sesion([entrar, "Despacito", "Luis Fonsi", otra, "Thriller Michael Jackson", no],
                 idioma=code)
        esperado = [
            dice(code, "music_ask"),
            dice(code, "music_artist"),
            dice(code, "music_playing", title="Despacito", artist="Luis Fonsi"),
            dice(code, "music_again"),
            dice(code, "music_ask_more"),
            dice(code, "music_playing", title="Thriller", artist="Michael Jackson"),
            dice(code, "music_again"),
            dice(code, "music_off"),
        ]
        ok = h.dicho == esperado
        check(ok, f"{lang.label(code):<10} dice las 8 frases en su idioma"
              + ("" if ok else f"\n           dijo:     {h.dicho}\n           esperado: {esperado}"))
        s = sonadas(h)
        check(len(s) == 2 and {d.get("label") for d in s} == {dice(code, "music_label")}
              and all(d.get("lang") == code and d.get("note") == "YouTube" for d in s)
              and [v["id"] for v in s[0]["track"]["youtube"]] == ["VIDEO000001", "VIDEO000002"],
              f"{'':<10} la pantalla recibe 2 canciones con sus videos, y el rótulo en {lang.label(code)}")
        check(h.buscadas == [("Despacito", "Luis Fonsi"), ("Thriller", "Michael Jackson")],
              f"{'':<10} busca con título Y artista -> {h.buscadas}")
        check(not h.a_claude and not h.music.is_active(),
              f"{'':<10} nada se va al Claude de las narraciones, y termina fuera del modo")


def probar_casos(h) -> None:
    print("\n=== 3. Los casos raros (en español, y los de eco en los diez) ===")
    es = "es"
    entrar = lista("VOICE_MUSIC_PHRASES", es)[1]     # «modo musica»
    A = lambda k, **f: dice(es, k, **f)
    again = A("music_again")

    h.pantalla, h.yt = "normal", "bien"
    h.sesion([entrar, "Despacito de Luis Fonsi", "no"])
    check(h.dicho == [A("music_ask"), A("music_playing", title="Despacito", artist="Luis Fonsi"), again, A("music_off")],
          "canción y artista dichos de una: no pregunta el artista")
    check(h.esperas == [229 + 90], f"espera el final lo que dura el video, con margen -> {h.esperas}")

    h.pantalla = "segundo"
    h.sesion([entrar, "Despacito de Luis Fonsi", "no"])
    check(h.esperas == [231 + 90], "si el primer video se niega y suena el segundo, espera lo que dura ESE")
    h.pantalla = "normal"

    h.sesion([entrar, "Despacito", "no sé", "no"])
    check(h.buscadas == [("Despacito", "")] and A("music_artist") in h.dicho
          and A("music_playing_title", title="Despacito") in h.dicho,
          "«no sé» de quién es: busca solo por el título y la anuncia sin artista")

    h.sesion([entrar, "algo de Queen", "no"])
    check(h.buscadas == [("", "Queen")] and A("music_playing_title", title="Queen") in h.dicho,
          "«algo de Queen»: busca por el artista y lo anuncia tal cual")

    h.pantalla = "corta"
    h.sesion([entrar, "Thriller de Michael Jackson", "sí", "Despacito de Luis Fonsi", "no"])
    check(h.dicho[2] == A("music_ack") + " " + again and h.dicho[3] == A("music_ask_more"),
          "«oye MECH» a media canción: para, «Entendido» y pregunta si seguimos")
    check(len([1 for t, d in h.eventos if t == "music" and d.get("track") is None and d.get("stage") == "again"]) >= 1,
          "...y a la pantalla le llega la orden de callar")

    h.pantalla = "corta Despacito de Luis Fonsi"
    h.sesion([entrar, "Thriller de Michael Jackson", "no"])
    check(h.buscadas == [("Thriller", "Michael Jackson"), ("Despacito", "Luis Fonsi")]
          and A("music_ack") not in " ".join(h.dicho),
          "«oye MECH, Despacito de Luis Fonsi»: pone la nueva sin preguntar")

    h.pantalla = "corta cuéntame de Don Quijote"
    h.sesion([entrar, "Thriller de Michael Jackson"])
    check(h.a_claude == ["cuéntame de Don Quijote"] and not h.music.is_active(),
          "«oye MECH, cuéntame de Don Quijote»: sale del modo y lo atiende normal")

    h.pantalla = "normal"
    h.sesion([entrar, "Lemon de Queen", "no"])
    check(h.dicho[1] == A("music_not_found") + " " + again and h.dicho[-1] == A("music_off"),
          "YouTube no tiene un video que se pueda poner: lo dice y pregunta si seguimos")

    h.yt = "caida"
    h.sesion([entrar, "Despacito de Luis Fonsi", "no"])
    check(h.dicho[1] == A("music_error") + " " + again and not sonadas(h),
          "sin internet al buscar: lo dice y pregunta si seguimos")
    h.yt = "cuota"
    h.sesion([entrar, "Despacito de Luis Fonsi", "no"])
    check(h.dicho[1] == A("music_error") + " " + again and not sonadas(h),
          "se acabaron las búsquedas del día: lo dice y pregunta si seguimos")
    h.yt = "sin clave"
    h.sesion([entrar, "cuéntame de Don Quijote"])
    check(h.dicho == [A("music_unavailable")] and not h.buscadas and not h.music.is_active()
          and h.a_claude == ["cuéntame de Don Quijote"],
          "sin clave de YouTube: dice que no puede, NO entra al modo, y sigue oyendo órdenes")
    h.yt = "bien"

    for modo, nombre in (("apagada", "sin ninguna pantalla abierta"), ("error", "ningún video se deja reproducir")):
        h.pantalla = modo
        h.sesion([entrar, "Despacito de Luis Fonsi", "no"])
        check(h.dicho[2] == A("music_error") + " " + again, f"{nombre}: no espera la canción entera, lo dice")
    h.pantalla = "normal"

    h.sesion([entrar, "bla bla bla", "más ruido sin sentido", "no"])
    check(h.dicho[:3] == [A("music_ask"), A("music_not_understood"), A("music_not_found") + " " + again],
          "no entiende el pedido: lo pide otra vez, y a la segunda deja de insistir")

    h.sesion([entrar, "Despacito de Luis Fonsi", "cuéntame de Don Quijote"])
    check(h.a_claude == ["cuéntame de Don Quijote"] and not h.music.is_active(),
          "al preguntar si seguimos, pedir otra cosa: sale del modo y la atiende")

    h.sesion([entrar, "Despacito de Luis Fonsi", "Thriller de Michael Jackson", "no"])
    check(h.buscadas == [("Despacito", "Luis Fonsi"), ("Thriller", "Michael Jackson")],
          "al preguntar si seguimos, decir la canción de una: la pone")

    h.pantalla = "panel"
    h.sesion([entrar, "Thriller de Michael Jackson", entrar, "Despacito de Luis Fonsi", "no"])
    check(h.dicho[2:] == [A("music_ask"), A("music_playing", title="Despacito", artist="Luis Fonsi"), again, A("music_off")],
          "«Parar» desde el panel a media canción: se calla, y MECH sigue oyendo órdenes después")

    despierto, _ = h.sesion([entrar, base.BANDERAS["dormir"][1][es]])
    check(not despierto and not h.music.is_active(), "dormirlo en medio: sale del modo")

    h.sesion([entrar, "apaga la música"])
    check(h.dicho == [A("music_ask"), A("music_off")] and not h.music.is_active(),
          "«apaga la música» mientras pregunta: sale")

    h.sesion(["¿qué importancia tuvo Malpaís y por qué quita la música el silencio de sus conciertos largos?"])
    check(len(h.a_claude) == 1, "una pregunta LARGA que lleva «quita… la música» no se pierde: va a Claude")

    config.MUSIC_ENABLED = False
    h.sesion([entrar])
    check(h.a_claude == [entrar] and not h.dicho, "con el modo apagado en Ajustes, la frase va a Claude como cualquier otra")
    config.MUSIC_ENABLED = True

    print("\n  -- el ECO, en los diez idiomas --")
    for code in lang.SUPPORTED:
        entrar = lista("VOICE_MUSIC_PHRASES", code)[0]
        no = lista("VOICE_NO_PHRASES", code)[0]
        # MECH se oye a sí mismo en cada pregunta: no puede contestarse.
        guion = [entrar, dice(code, "music_ask"), "Despacito de Luis Fonsi",
                 dice(code, "music_again"), no, dice(code, "music_off")]
        h.pantalla = "normal"
        h.sesion(guion, idioma=code)
        esperado = [dice(code, "music_ask"),
                    dice(code, "music_playing", title="Despacito", artist="Luis Fonsi"),
                    dice(code, "music_again"), dice(code, "music_off")]
        ok = h.dicho == esperado and not h.a_claude and not h.music.is_active()
        check(ok, f"{lang.label(code):<10} oye sus 3 preguntas y su despedida, y no se contesta"
              + ("" if ok else f"\n           dijo: {h.dicho}\n           a Claude: {h.a_claude}"))


def probar_busqueda() -> None:
    print("\n=== 4. La búsqueda en YouTube, con respuestas de mentira de Google ===")
    import importlib
    import urllib.error
    import youtube_music
    yt = importlib.reload(youtube_music)
    config.YOUTUBE_API_KEY = "clave-de-mentira"
    config.MUSIC_COUNTRY, config.MUSIC_ALLOW_EXPLICIT, config.MUSIC_MAX_SECONDS = "CR", False, 600.0
    check(yt.segundos("PT3M49S") == 229 and yt.segundos("PT1H2M3S") == 3723 and yt.segundos("P0D") == 0,
          "duraciones de YouTube («PT3M49S» = 229 s)")
    check(yt.disponible(), "con una clave puesta, YouTube está disponible")
    llamadas = []
    nada = {"liveBroadcastContent": "none"}
    BUSQUEDA = {"items": [
        {"id": {"videoId": "karaoke0001"}, "snippet": dict(nada, title="Despacito KARAOKE", channelTitle="Karaokes")},
        {"id": {"videoId": "oficial0001"}, "snippet": dict(nada, title="Luis Fonsi - Despacito ft. Daddy Yankee", channelTitle="LuisFonsiVEVO",
                                                           thumbnails={"high": {"url": "https://i.ytimg.com/vi/x/hq.jpg"}})},
        {"id": {"videoId": "nodeja00001"}, "snippet": dict(nada, title="Despacito (Official)", channelTitle="X")},
        {"id": {"videoId": "adultos0001"}, "snippet": dict(nada, title="Despacito", channelTitle="X")},
        {"id": {"videoId": "diezhoras01"}, "snippet": dict(nada, title="Despacito 10 hours", channelTitle="X")},
        {"id": {"videoId": "endirecto01"}, "snippet": {"title": "Despacito radio", "channelTitle": "X", "liveBroadcastContent": "live"}},
        {"id": {"videoId": "letra000001"}, "snippet": dict(nada, title="Luis Fonsi &amp; Daddy Yankee - Despacito (Letra)", channelTitle="Letras")},
        {"id": {"videoId": "bloqueado01"}, "snippet": dict(nada, title="Despacito", channelTitle="X")},
    ]}
    DETALLES = {"items": [
        {"id": "karaoke0001", "contentDetails": {"duration": "PT3M50S"}, "status": {"embeddable": True}},
        {"id": "oficial0001", "contentDetails": {"duration": "PT4M42S"}, "status": {"embeddable": True}},
        {"id": "nodeja00001", "contentDetails": {"duration": "PT4M42S"}, "status": {"embeddable": False}},
        {"id": "adultos0001", "contentDetails": {"duration": "PT4M", "contentRating": {"ytRating": "ytAgeRestricted"}}, "status": {"embeddable": True}},
        {"id": "diezhoras01", "contentDetails": {"duration": "PT10H"}, "status": {"embeddable": True}},
        {"id": "letra000001", "contentDetails": {"duration": "PT3M48S"}, "status": {"embeddable": True}},
        {"id": "bloqueado01", "contentDetails": {"duration": "PT4M", "regionRestriction": {"blocked": ["CR", "PA"]}}, "status": {"embeddable": True}},
    ]}

    def pedir(recurso, **params):
        llamadas.append((recurso, params))
        return BUSQUEDA if recurso == "search" else DETALLES

    yt._pedir = pedir
    r = yt.buscar("Despacito", "Luis Fonsi")
    check([v["id"] for v in r] == ["oficial0001", "letra000001", "karaoke0001"],
          f"se queda con los que se pueden poner, el oficial primero y el karaoke último -> {[v['id'] for v in r]}")
    check(r[0]["seconds"] == 282 and r[1]["title"] == "Luis Fonsi & Daddy Yankee - Despacito (Letra)",
          "con su duración y el título sin códigos raros")
    b = llamadas[0][1]
    check(b["videoEmbeddable"] == "true" and b["safeSearch"] == "strict" and b["type"] == "video"
          and b["videoCategoryId"] == "10" and b["regionCode"] == "CR" and b["q"] == "Despacito Luis Fonsi",
          "pide solo videos de música que dejen incrustarse, con el filtro estricto")
    yt.buscar("Despacito", "Luis Fonsi")
    check(len(llamadas) == 2, "la misma canción otra vez no vuelve a gastar búsquedas")
    config.MUSIC_ALLOW_EXPLICIT = True
    yt.buscar("Otra", "Distinta")
    check(llamadas[2][1]["safeSearch"] == "none", "con «contenido explícito» permitido en Ajustes, busca sin filtro")
    config.MUSIC_ALLOW_EXPLICIT = False

    # Y ahora Google contesta «se acabó la cuota» (un 403 con su motivo).
    cuerpo = b'{"error": {"code": 403, "message": "quota", "errors": [{"reason": "quotaExceeded"}]}}'
    yt = importlib.reload(yt)                          # con su `_pedir` de verdad
    original = yt.urllib.request.urlopen

    def abrir(req, timeout=0):
        raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, io.BytesIO(cuerpo))

    yt.urllib.request.urlopen = abrir
    try:
        yt.buscar("Otra", "Cualquiera")
        check(False, "cuota agotada: tenía que avisar")
    except yt.ErrorYouTube as e:
        check(e.motivo == "quotaExceeded" and not yt.disponible() and "mañana" in yt.por_que_no(),
              f"cuota agotada: lo explica y deja de intentarlo un rato -> «{e}»")
    finally:
        yt.urllib.request.urlopen = original
    config.YOUTUBE_API_KEY, guardada = "", config.GOOGLE_API_KEY
    config.GOOGLE_API_KEY = ""
    yt = importlib.reload(yt)
    check(not yt.disponible() and "YOUTUBE_API_KEY" in yt.por_que_no(),
          "sin ninguna clave: no disponible, y dice qué falta")
    config.GOOGLE_API_KEY = guardada


def clave_real() -> str:
    """La clave para `--red`: del entorno, o de backend/.env si está ahí."""
    import os
    valor = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if valor:
        return valor
    env = base.RAIZ / "backend" / ".env"
    if env.exists():
        for linea in env.read_text(encoding="utf-8").splitlines():
            if linea.strip().startswith("YOUTUBE_API_KEY="):
                return linea.split("=", 1)[1].strip()
    return ""


def probar_red() -> None:
    print("\n=== 5. YouTube DE VERDAD (necesita internet y la clave) ===")
    import importlib
    import youtube_music
    clave = clave_real()
    if not clave:
        check(False, "no hay clave: pon YOUTUBE_API_KEY en backend/.env (o como variable) y repite")
        return
    config.YOUTUBE_API_KEY = clave
    config.MUSIC_COUNTRY, config.MUSIC_ALLOW_EXPLICIT, config.MUSIC_MAX_SECONDS = "CR", False, 600.0
    yt = importlib.reload(youtube_music)
    for titulo, artista in [("Despacito", "Luis Fonsi"), ("Bohemian Rhapsody", "Queen"),
                            ("Shape of You", "Ed Sheeran"), ("Como un pájaro", "Malpaís")]:
        try:
            r = yt.buscar(titulo, artista)
        except Exception as e:
            check(False, f"{titulo} / {artista}: {e}")
            continue
        check(bool(r) and all(45 <= v["seconds"] <= 600 and len(v["id"]) == 11 for v in r),
              f"{titulo} / {artista} → "
              + (" | ".join(f"{v['title'][:38]} [{v['channel'][:16]}] {v['seconds']} s" for v in r) if r else "NADA"))


def main() -> int:
    probar_frases()
    try:
        h = montar()
        probar_sesiones(h)
        probar_casos(h)
        probar_busqueda()
    except Exception as e:
        import traceback
        traceback.print_exc()
        check(False, f"no se pudo simular el backend: {e!r}")
    if "--red" in sys.argv:
        probar_red()
    print()
    if base.fallos:
        print(f"{len(base.fallos)} FALLO(S):")
        for f in base.fallos:
            print("  -", f)
        return 1
    print("TODO BIEN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
