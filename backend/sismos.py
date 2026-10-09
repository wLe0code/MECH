"""Sismos recientes — los consulta en fuentes PÚBLICAS y se los pasa al panel.

Alimenta la vista «Sismos» del panel (el mapa). Pedido del equipo, oct 2026.

Qué es y qué NO es
------------------
Es un mapa de lo que YA tembló, en cuanto las redes sísmicas lo publican
(entre 2 y 10 minutos después). **No predice nada y no es una alerta
temprana**: cuando el dato llega aquí, la sacudida ya pasó. Sirve para
informar («acaba de temblar en tal sitio, a tantos km»), no para avisar
antes. La alerta de verdad (segundos de ventaja) necesita un acuerdo con el
OVSICORI o con el USGS; ver handoff.md.

De dónde salen los datos (las dos son gratis y sin clave)
---------------------------------------------------------
- **EMSC** (seismicportal.eu): reúne lo que publican las redes de cada país.
  Es la que trae los sismos de Centroamérica: los de Costa Rica llegan
  firmados «UNA» (OVSICORI-UNA), los de Panamá «IGC», los de Nicaragua
  «INET». Tardan unos 5-10 minutos en aparecer.
- **USGS**: muy rápida en Estados Unidos (1-3 minutos) y fiable para los
  grandes de todo el mundo, pero casi no trae los pequeños de Costa Rica.

El mismo sismo suele salir en las dos: se juntan en uno (ver `_mismo`).

Qué se guarda
-------------
Los últimos 7 días de:
  - todo el mundo, de magnitud `SISMOS_MIN_MAG_WORLD` (4.0) para arriba, y
  - «mi zona» (un círculo de `SISMOS_ZONE_RADIUS_KM` alrededor de
    `SISMOS_ZONE_LAT/LON`), desde `SISMOS_MIN_MAG_ZONE` (2.5): ahí interesan
    también los pequeños, que son los que la gente siente.

Cuánto internet gasta
---------------------
Cada `SISMOS_POLL_SECONDS` (60 s) pide «lo último» a cada fuente (unos 8 KB
comprimidos entre las dos) y cada media hora la semana entera (unos 60 KB).
Son ~15 MB al día: se puede dejar encendido con el hotspot del celular.

La lista NO va en `state` (ese viaja entero por WebSocket en cada cambio de
fase): el panel la pide por `GET /api/sismos`, y los sismos NUEVOS llegan por
el evento WS `sismos`.

Sin dependencias nuevas: solo la librería estándar.
"""

from __future__ import annotations

import calendar
import gzip
import json
import math
import re
import threading
import time
import urllib.parse
import urllib.request

import config

USGS_HORA = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
USGS_SEMANA = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.geojson"
EMSC_CONSULTA = "https://www.seismicportal.eu/fdsnws/event/1/query"
EMSC_FICHA = "https://www.emsc-csem.org/Earthquake_information/earthquake.php?id="

VENTANA_S = 7 * 86400          # cuánto hacia atrás se guarda
REFRESCO_COMPLETO_S = 30 * 60  # cada cuánto se vuelve a pedir la semana entera
ESPERA_RED_S = 15              # tope de cada petición
# Un sismo que aparece por primera vez pero ocurrió hace más que esto no se
# anuncia como «nuevo» (es una revisión tardía, no algo que acabe de pasar).
NUEVO_HASTA_S = 2 * 3600

# Quién firma cada sismo en EMSC (tabla de contribuyentes de emsc-csem.org).
AGENCIAS = {
    "UNA": "OVSICORI-UNA (Costa Rica)",
    "UCR": "RSN-UCR (Costa Rica)",
    "IGC": "Universidad de Panamá",
    "INET": "INETER (Nicaragua)",
    "NEIC": "USGS (EE. UU.)",
    "EMSC": "EMSC",
}


def distancia_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia sobre la Tierra entre dos puntos (fórmula del haversine)."""
    f1, f2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((f2 - f1) / 2) ** 2
         + math.cos(f1) * math.cos(f2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 6371.0 * 2 * math.asin(min(1.0, math.sqrt(a)))


_FECHA = re.compile(r"(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(\.\d+)?")


def _epoch(iso: str) -> float:
    """«2026-10-08T22:13:19.0Z» (hora UTC) -> segundos desde 1970."""
    m = _FECHA.match(iso or "")
    if not m:
        raise ValueError(f"fecha rara: {iso!r}")
    partes = [int(x) for x in m.groups()[:6]]
    return calendar.timegm(tuple(partes) + (0, 0, 0)) + float(m.group(7) or 0)


# -- El lugar, en español ------------------------------------------------------
# Las fuentes lo dan en inglés («18 km NNE of Posoltega, Nicaragua», «NEAR
# COAST OF NICARAGUA»). Se traduce lo que sigue un patrón; el resto se deja
# como viene. Es para leerlo en el panel, no un diccionario completo.

_RUMBO = {"N": "norte", "S": "sur", "E": "este", "W": "oeste"}
_NOMBRES = [
    ("Central America", "Centroamérica"), ("Caribbean Sea", "Mar Caribe"),
    ("Dominican Republic", "República Dominicana"), ("New Zealand", "Nueva Zelanda"),
    ("Papua New Guinea", "Papúa Nueva Guinea"), ("United States", "Estados Unidos"),
    ("Philippines", "Filipinas"), ("New Mexico", "Nuevo México"),
    ("Mid-Atlantic Ridge", "la dorsal Mesoatlántica"),
    ("Panama", "Panamá"), ("Mexico", "México"), ("Peru", "Perú"), ("Japan", "Japón"),
    ("Greece", "Grecia"), ("Turkey", "Turquía"), ("Italy", "Italia"),
    ("Russia", "Rusia"), ("Spain", "España"), ("Iran", "Irán"), ("Haiti", "Haití"),
    ("Brazil", "Brasil"), ("Canada", "Canadá"), ("Taiwan", "Taiwán"),
]
_PUNTO = {"north": "norte", "south": "sur", "east": "este", "west": "oeste",
          "northeast": "noreste", "northwest": "noroeste",
          "southeast": "sureste", "southwest": "suroeste"}
_DONDE = r"(north(?:east|west)?|south(?:east|west)?|east|west)"
# (patrón, plantilla). En las que llevan punto cardinal, {0} es el punto ya
# en español y {1} el sitio; en las demás, {0} es el sitio.
_ZONAS = [
    (r"near (?:the )?" + _DONDE + r" coast of (.+)", "Cerca de la costa {0} de {1}"),
    (r"off (?:the )?" + _DONDE + r" coast of (.+)", "Frente a la costa {0} de {1}"),
    (r"near (?:the )?coast of (.+)", "Cerca de la costa de {0}"),
    (r"off (?:the )?coast of (.+)", "Frente a la costa de {0}"),
    (r"offshore (.+)", "Frente a la costa de {0}"),
    (r"(.+?) border reg(?:ion)?\.?", "Frontera {0}"),
    (r"" + _DONDE + r" of (?:the )?(.+)", "Al {0} de {1}"),          # «South of Panama»
    (r"(north|south|east|west)ern (.+)", "{0} de {1}"),              # «Southern Peru»
    (r"central (.+)", "Centro de {0}"),
    (r"(.+?) region", "Región de {0}"),
]


def _titulo(texto: str) -> str:
    """EMSC lo manda TODO EN MAYÚSCULAS; se pasa a «Así Escrito»."""
    if texto != texto.upper():
        return texto
    texto = re.sub(r"[A-Za-zÀ-ÿ']+", lambda m: m.group(0).capitalize(), texto.lower())
    return re.sub(r"\b(Of|The|And)\b", lambda m: m.group(0).lower(), texto)


def lugar_es(texto: str) -> str:
    texto = _titulo((texto or "").strip())
    if not texto:
        return "Lugar sin nombre"
    for ingles, espanol in _NOMBRES:
        texto = re.sub(r"\b" + re.escape(ingles) + r"\b", espanol, texto, flags=re.I)
    # USGS: «18 km NNE of Posoltega, Nicaragua»
    m = re.match(r"(\d+)\s*km\s+([NSEW]{1,3})\s+of\s+(.+)$", texto)
    if m:
        rumbo = m.group(2)
        nombre = _RUMBO[rumbo] if len(rumbo) == 1 else rumbo.replace("W", "O")
        return f"A {m.group(1)} km al {nombre} de {m.group(3)}"
    for patron, plantilla in _ZONAS:
        m = re.fullmatch(patron, texto, flags=re.I)
        if m:
            partes = list(m.groups())
            if len(partes) == 2:
                partes[0] = _PUNTO[partes[0].lower()]
            salida = plantilla.format(*partes)
            return salida[0].upper() + salida[1:]
    return texto


# -- De cada fuente a un sismo «nuestro» ---------------------------------------

def _de_usgs(f: dict) -> dict | None:
    p = f.get("properties") or {}
    c = (f.get("geometry") or {}).get("coordinates") or []
    if p.get("type") != "earthquake" or p.get("mag") is None or len(c) < 2:
        return None   # también publica canteras y explosiones: fuera
    prof = c[2] if len(c) > 2 and c[2] is not None else None
    return {
        "id": "usgs:" + str(f.get("id")),
        "t": float(p["time"]) / 1000.0,
        "lat": float(c[1]), "lon": float(c[0]),
        "prof": None if prof is None else round(max(0.0, float(prof)), 1),
        "mag": round(float(p["mag"]), 1),
        "lugar": lugar_es(p.get("place") or ""),
        "fuentes": ["USGS"],
        "agencia": "USGS (EE. UU.)",
        "url": p.get("url") or "",
        # No es un aviso de tsunami: es la marca del USGS de «revisar el aviso».
        "tsunami": bool(p.get("tsunami")),
    }


def _de_emsc(f: dict) -> dict | None:
    p = f.get("properties") or {}
    if p.get("mag") is None or p.get("lat") is None or p.get("lon") is None:
        return None
    if p.get("evtype") not in (None, "ke"):
        return None   # «se» = sospecha de explosión, etc.
    firma = (p.get("auth") or "").upper()
    prof = p.get("depth")
    return {
        "id": "emsc:" + str(p.get("unid") or f.get("id")),
        "t": _epoch(p.get("time") or ""),
        "lat": float(p["lat"]), "lon": float(p["lon"]),
        "prof": None if prof is None else round(abs(float(prof)), 1),
        "mag": round(float(p["mag"]), 1),
        "lugar": lugar_es(p.get("flynn_region") or ""),
        "fuentes": ["EMSC"],
        "agencia": AGENCIAS.get(firma, firma or "EMSC"),
        "url": (EMSC_FICHA + str(p["source_id"])) if p.get("source_id") else "",
        "tsunami": False,
    }


def _mismo(a: dict, b: dict) -> bool:
    """¿Es el MISMO sismo contado por dos fuentes?

    Cada red lo localiza por su cuenta, así que la hora y el sitio no
    coinciden exactos: se aceptan 40 s y 150 km de diferencia. Dos sismos
    distintos tan pegados son rarísimos, y juntarlos por error solo quitaría
    un punto del mapa.
    """
    return (abs(a["t"] - b["t"]) <= 40
            and distancia_km(a["lat"], a["lon"], b["lat"], b["lon"]) <= 150)


def _descargar(url: str) -> dict:
    req = urllib.request.Request(url, headers={
        "User-Agent": "MECH-robot/1.0 (proyecto educativo WRO)",
        "Accept-Encoding": "gzip",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=ESPERA_RED_S) as r:
        cuerpo = r.read()
        if (r.headers.get("Content-Encoding") or "").lower() == "gzip":
            cuerpo = gzip.decompress(cuerpo)
    if not cuerpo.strip():
        return {"features": []}   # EMSC contesta vacío (204) si no hay nada
    return json.loads(cuerpo.decode("utf-8"))


def _iso(epoch: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(epoch))


class Sismos:
    """Hilo que consulta las fuentes y guarda la lista. Uno por servidor."""

    def __init__(self, app) -> None:
        self.app = app
        self._lock = threading.Lock()
        self._sismos: dict[str, dict] = {}   # id -> sismo
        self._alias: dict[str, str] = {}     # id en la otra fuente -> id guardado
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._despierta = threading.Event()
        self._consultado = 0.0    # última consulta que salió bien
        self._completa = 0.0      # última vez que se pidió la semana entera
        self._zona_cargada: tuple | None = None
        # Fuentes de las que ya se tiene la semana cargada (con esta zona).
        # Lo primero que trae cada una es historia: no se anuncia como nuevo.
        self._cargadas: set[str] = set()
        self._error: str | None = None
        self._en_linea: bool | None = None   # para avisar solo cuando cambia

    # -- Vida del hilo ---------------------------------------------------------

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="sismos")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._despierta.set()

    def despertar(self) -> None:
        """Consultar YA (botón «Actualizar» o cambio de zona en el panel)."""
        self._despierta.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            if config.SISMOS_ENABLED:
                try:
                    self._consultar()
                except Exception as e:   # nunca dejar morir el hilo
                    self._fallo(f"error inesperado: {e}")
            elif self._en_linea is not None:
                self._en_linea = None
                self._avisar([])
            self._despierta.wait(timeout=max(20.0, float(config.SISMOS_POLL_SECONDS)))
            self._despierta.clear()

    # -- Consulta --------------------------------------------------------------

    @staticmethod
    def _zona() -> tuple:
        return (float(config.SISMOS_ZONE_LAT), float(config.SISMOS_ZONE_LON),
                float(config.SISMOS_ZONE_RADIUS_KM),
                float(config.SISMOS_MIN_MAG_WORLD), float(config.SISMOS_MIN_MAG_ZONE))

    def _bajar_usgs(self, completa: bool) -> list[dict]:
        datos = _descargar(USGS_SEMANA if completa else USGS_HORA)
        return [s for s in map(_de_usgs, datos.get("features") or []) if s]

    def _bajar_emsc(self, completa: bool, zona: tuple, ahora: float) -> list[dict]:
        lat, lon, radio, min_mundo, min_zona = zona
        if completa:
            desde = _iso(ahora - VENTANA_S)
            consultas = [
                {"minmag": min_mundo, "start": desde, "limit": 1000},
                {"minmag": min_zona, "start": desde, "limit": 1000,
                 "lat": lat, "lon": lon, "maxradius": round(radio / 111.19, 3)},
            ]
        else:
            # «Los últimos 80 del mundo»: cubre varias horas y pesa 7 KB.
            consultas = [{"minmag": min(min_mundo, min_zona), "limit": 80}]
        salida = []
        for q in consultas:
            url = EMSC_CONSULTA + "?" + urllib.parse.urlencode(dict(q, format="json"))
            for f in _descargar(url).get("features") or []:
                try:
                    s = _de_emsc(f)
                except (ValueError, TypeError, KeyError):
                    continue   # una ficha mal formada no tumba el resto
                if s:
                    salida.append(s)
        return salida

    def _consultar(self) -> None:
        zona = self._zona()
        ahora = time.time()
        if zona != self._zona_cargada:
            # Cambió «mi zona» (o los umbrales): lo guardado ya no vale.
            with self._lock:
                self._sismos.clear()
                self._alias.clear()
            self._cargadas.clear()
            self._completa = 0.0
        completa = ahora - self._completa > REFRESCO_COMPLETO_S

        crudos: list[dict] = []
        fallos: list[str] = []
        bien: list[str] = []
        for nombre, bajar in (("EMSC", lambda: self._bajar_emsc(completa, zona, ahora)),
                              ("USGS", lambda: self._bajar_usgs(completa))):
            try:
                crudos += bajar()
                bien.append(nombre)
            except Exception as e:
                fallos.append(f"{nombre}: {e}")
        if not bien:
            self._fallo("; ".join(fallos))
            return

        nuevos = self._mezclar(crudos, zona, ahora, anunciar=set(self._cargadas))
        if completa:
            self._cargadas.update(bien)
        self._zona_cargada = zona
        self._consultado = ahora
        if completa:
            # Si una de las dos fuentes falló, la semana entera se vuelve a
            # pedir en 5 minutos, no en cada vuelta (gastaría datos de más).
            self._completa = ahora if not fallos else ahora - REFRESCO_COMPLETO_S + 300
        self._error = "; ".join(fallos) or None

        nombre_zona = config.SISMOS_ZONE_NAME
        if self._en_linea is not True:
            with self._lock:
                total = len(self._sismos)
                cerca = sum(1 for s in self._sismos.values() if s["cerca"])
            self.app.log(
                f"Sismos: {total} en los últimos 7 días, {cerca} de ellos cerca de "
                f"{nombre_zona}. Están en la vista «Sismos» del panel.", "ok")
        self._en_linea = True
        for s in nuevos:
            minutos = max(0, round((ahora - s["t"]) / 60))
            if s["cerca"]:
                self.app.log(
                    f"Sismo de magnitud {s['mag']} a {s['dist']} km de {nombre_zona} "
                    f"({s['lugar']}), hace {minutos} min.", "warn")
            elif s["mag"] >= 6:
                self.app.log(
                    f"Sismo fuerte en el mundo: magnitud {s['mag']}, {s['lugar']}, "
                    f"hace {minutos} min.", "info")
        self._avisar(nuevos)

    def _mezclar(self, crudos: list[dict], zona: tuple, ahora: float,
                 anunciar: set) -> list[dict]:
        """Mete lo bajado en la lista. Devuelve los que son NUEVOS de verdad.

        `anunciar` = las fuentes de las que ya se tenía la semana cargada: solo
        lo que ellas traen de más es una novedad.
        """
        lat0, lon0, radio, min_mundo, min_zona = zona
        nuevos: list[dict] = []
        with self._lock:
            for s in sorted(crudos, key=lambda x: x["t"]):
                if not (ahora - VENTANA_S <= s["t"] <= ahora + 300):
                    continue
                dist = distancia_km(lat0, lon0, s["lat"], s["lon"])
                s["dist"] = int(round(dist))
                s["cerca"] = dist <= radio
                if not (s["mag"] >= min_mundo or (s["cerca"] and s["mag"] >= min_zona)):
                    continue
                guardado = self._sismos.get(self._alias.get(s["id"], s["id"]))
                if guardado is None:
                    fuente = s["fuentes"][0]
                    guardado = next((v for v in self._sismos.values()
                                     if fuente not in v["fuentes"] and _mismo(v, s)), None)
                    if guardado is not None:
                        # El mismo sismo, contado por la otra fuente: se anota
                        # y no se pinta dos veces.
                        self._alias[s["id"]] = guardado["id"]
                        guardado["fuentes"] = guardado["fuentes"] + [fuente]
                        guardado["tsunami"] = guardado["tsunami"] or s["tsunami"]
                        continue
                    s["visto"] = ahora
                    self._sismos[s["id"]] = s
                    if fuente in anunciar and ahora - s["t"] <= NUEVO_HASTA_S:
                        nuevos.append(dict(s))
                elif guardado["id"] == s["id"]:
                    # La misma ficha, revisada por su red (cambia la magnitud
                    # o el sitio en los primeros minutos).
                    for k in ("t", "lat", "lon", "prof", "mag", "lugar", "dist",
                              "cerca", "agencia", "url"):
                        guardado[k] = s[k]
                    guardado["tsunami"] = guardado["tsunami"] or s["tsunami"]
                else:
                    guardado["tsunami"] = guardado["tsunami"] or s["tsunami"]
            # Fuera lo que ya salió de la ventana de 7 días.
            viejos = [k for k, v in self._sismos.items() if v["t"] < ahora - VENTANA_S]
            for k in viejos:
                del self._sismos[k]
            if viejos:
                self._alias = {a: k for a, k in self._alias.items() if k in self._sismos}
        return nuevos

    def _fallo(self, motivo: str) -> None:
        self._error = motivo
        if self._en_linea is not False:
            self.app.log(
                "Sismos: no pude consultar las fuentes (¿hay internet?). El mapa "
                f"se queda con lo último que bajó. [{motivo[:160]}]", "warn")
        self._en_linea = False
        self._avisar([])

    # -- Lo que ve el panel ----------------------------------------------------

    def _meta(self) -> dict:
        with self._lock:
            total = len(self._sismos)
        return {
            # La hora del servidor: el panel la usa para calcular «hace X min»
            # aunque el reloj del equipo donde se abre no coincida con el de
            # la Pi.
            "ahora": time.time(),
            "activo": bool(config.SISMOS_ENABLED),
            "consultado": self._consultado,
            "error": self._error,
            "total": total,
        }

    def _avisar(self, nuevos: list[dict]) -> None:
        self.app.emit("sismos", nuevos=nuevos, **self._meta())

    def snapshot(self) -> dict:
        """Todo lo que necesita la vista del panel (GET /api/sismos)."""
        with self._lock:
            lista = [dict(s) for s in self._sismos.values()]
        lista.sort(key=lambda s: -s["t"])
        datos = self._meta()
        datos.update(
            zona={
                "nombre": config.SISMOS_ZONE_NAME,
                "lat": float(config.SISMOS_ZONE_LAT),
                "lon": float(config.SISMOS_ZONE_LON),
                "radio_km": float(config.SISMOS_ZONE_RADIUS_KM),
            },
            min_mag_mundo=float(config.SISMOS_MIN_MAG_WORLD),
            min_mag_zona=float(config.SISMOS_MIN_MAG_ZONE),
            cada_s=max(20.0, float(config.SISMOS_POLL_SECONDS)),
            sismos=lista,
        )
        return datos


    # -- Lo que sabe MECH (se lo cuenta a Claude) ------------------------------

    def para_claude(self, ahora: float | None = None) -> str:
        """El resumen de sismos que se le pasa a Claude con cada pregunta.

        Así MECH puede contestar «¿ha temblado hoy?» con los MISMOS datos del
        mapa, en vez de inventar. Va corto a propósito (viaja en cada
        petición): lo último cerca de «mi zona» y lo más fuerte del mundo.
        Las reglas del final importan tanto como los datos: MECH informa de
        lo que ya tembló; no predice ni alerta.
        """
        ahora = time.time() if ahora is None else ahora
        zona = config.SISMOS_ZONE_NAME
        titulo = "## Sismos recientes — datos EN VIVO de las redes sísmicas\n"
        no_inventes = ("Si preguntan por sismos recientes, di que ahora mismo "
                       "no tienes esos datos. No inventes ninguno.")
        if not config.SISMOS_ENABLED:
            return titulo + "La consulta de sismos está apagada en el panel. " + no_inventes
        if not self._consultado:
            return (titulo + "MECH todavía no ha podido consultar las redes sísmicas "
                    "(¿no hay internet?). " + no_inventes)
        with self._lock:
            lista = [dict(s) for s in self._sismos.values()]
        cerca = sorted((s for s in lista if s["cerca"]), key=lambda s: -s["t"])
        lejos = [s for s in lista if not s["cerca"]]

        def linea(s: dict, de_la_zona: bool) -> str:
            partes = [f"{_hace(ahora - s['t'])} ({_hora_local(s['t'])})",
                      f"magnitud {s['mag']}", s["lugar"], f"a {s['dist']} km de aquí"]
            if s.get("prof") is not None:
                partes.append(f"{s['prof']:.0f} km de profundidad")
            if de_la_zona:
                partes.append(f"lo reportó {s['agencia']}")
            return "- " + " · ".join(partes)

        minutos = max(0, round((ahora - self._consultado) / 60))
        t = [titulo.rstrip(),
             f"(consultados hace {minutos} min a EMSC y USGS; ahora son las "
             f"{_hora_local(ahora)}, hora del robot)"]
        if minutos > 15:
            t.append("OJO: desde entonces no hubo conexión; puede faltar lo más reciente. Dilo si preguntan.")
        t.append(f"MECH está en {zona}: «de aquí» es la distancia a ese punto.")
        t.append("")
        radio = float(config.SISMOS_ZONE_RADIUS_KM)
        if cerca:
            hoy = sum(1 for s in cerca if ahora - s["t"] <= 86400)
            fuerte = max(cerca, key=lambda s: (s["mag"], s["t"]))
            t.append(f"Cerca de {zona} (hasta {radio:.0f} km), en los últimos 7 días: "
                     f"{len(cerca)} sismos de magnitud {config.SISMOS_MIN_MAG_ZONE} o más; "
                     f"{hoy} en las últimas 24 horas. Los más recientes:")
            t += [linea(s, True) for s in cerca[:PARA_CLAUDE_CERCA]]
            if fuerte not in cerca[:PARA_CLAUDE_CERCA]:
                t.append("El más fuerte de la semana en la zona:")
                t.append(linea(fuerte, True))
        else:
            t.append(f"Cerca de {zona} (hasta {radio:.0f} km) no hay ningún sismo de magnitud "
                     f"{config.SISMOS_MIN_MAG_ZONE} o más en los últimos 7 días.")
        if lejos:
            t.append("")
            t.append(f"En el resto del mundo, los más fuertes de los últimos 7 días "
                     f"(de {len(lejos)} de magnitud {config.SISMOS_MIN_MAG_WORLD} o más):")
            fuertes = sorted(lejos, key=lambda s: (-s["mag"], -s["t"]))[:PARA_CLAUDE_MUNDO]
            t += [linea(s, False) for s in fuertes]
            ultimo = max(lejos, key=lambda s: s["t"])
            if ultimo not in fuertes:
                t.append("El más reciente del mundo:")
                t.append(linea(ultimo, False))
        t += ["", _REGLAS_CLAUDE]
        return "\n".join(t)


# Cuántos sismos se le cuentan a Claude: los más recientes de la zona y los
# más fuertes del mundo. Más no ayuda a contestar y viaja en cada petición.
PARA_CLAUDE_CERCA = 8
PARA_CLAUDE_MUNDO = 5

_REGLAS_CLAUDE = """Cómo usar estos datos:
- SOLO si preguntan por sismos, temblores o terremotos. No los menciones por tu cuenta ni los metas en una obra.
- Son sismos que YA ocurrieron: las redes los publican entre 2 y 10 minutos después. MECH NO predice sismos y NO es una alerta temprana; si lo preguntan, dilo así de claro.
- No inventes ninguno ni cambies cifras. Solo tienes los últimos 7 días: si preguntan por otra fecha u otro lugar que no está aquí, dilo.
- No tienes avisos de tsunami, ni de daños, ni de réplicas por venir: si preguntan, di que eso lo informan las autoridades.
- Contesta en modo `qa`, con UN segmento corto y sin `image_prompt` ni video (una imagen inventada de un sismo confunde): cuándo fue, de qué magnitud, dónde y a qué distancia. Es para oírlo: «magnitud cuatro coma ocho», «hace unas dos horas».
- Ante una emergencia lo que vale son las autoridades, no MECH."""


def _hace(segundos: float) -> str:
    """«hace 35 min», «hace 5 h», «hace 3 días»."""
    minutos = max(1, round(segundos / 60))
    if minutos < 60:
        return f"hace {minutos} min"
    if minutos < 36 * 60:
        return f"hace {round(minutos / 60)} h"
    return f"hace {round(minutos / 1440)} días"


def _hora_local(epoch: float) -> str:
    return time.strftime("%d/%m %H:%M", time.localtime(epoch))


_sismos: Sismos | None = None


def para_claude() -> str:
    """Lo que MECH sabe de sismos, para Claude. "" si no hay nada que pasar.

    "" cuando está apagado en la configuración o cuando no corre el hilo de
    sismos (el modo `python -m backend.main`, sin servidor).
    """
    if not config.SISMOS_ANSWERS_ENABLED or _sismos is None:
        return ""
    try:
        return _sismos.para_claude()
    except Exception:
        return ""       # esto nunca puede tumbar una respuesta de MECH


def get_sismos(app) -> Sismos:
    global _sismos
    if _sismos is None:
        _sismos = Sismos(app)
    return _sismos
