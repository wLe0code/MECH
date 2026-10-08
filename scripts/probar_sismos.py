"""Prueba la pieza que consulta los SISMOS (backend/sismos.py), sin el robot.

Dos partes:

  1. Sin internet: fichas de mentira con la forma exacta de cada fuente.
     Que se entiendan, que el lugar salga en espanol, que el mismo sismo
     contado por las dos fuentes se pinte UNA vez, que solo lo que aparece
     despues de la primera carga cuente como «nuevo», y que lo viejo caduque.

  2. Con --red: consulta EMSC y USGS de verdad y ensena lo que traen (cuantos,
     cuantos cerca de «mi zona», los ultimos). Es la forma rapida de saber si
     las fuentes siguen contestando igual.

    python scripts/probar_sismos.py          (sin internet)
    python scripts/probar_sismos.py --red    (consulta las fuentes reales)

Sale 1 si algo falla. No necesita claves de API ni hardware.
"""
import sys, types, os, time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))
for k in ("ANTHROPIC_API_KEY", "ELEVENLABS_API_KEY", "GOOGLE_API_KEY"):
    os.environ.setdefault(k, "x")
# Que el .env de esta maquina no cambie la zona de la prueba.
for k in list(os.environ):
    if k.startswith("SISMOS_"):
        del os.environ[k]
try:
    import dotenv  # noqa: F401
except Exception:
    d = types.ModuleType("dotenv"); d.load_dotenv = lambda *a, **k: None
    sys.modules["dotenv"] = d

import config, sismos

config.SISMOS_ENABLED = True
config.SISMOS_ZONE_NAME = "Costa Rica"
config.SISMOS_ZONE_LAT, config.SISMOS_ZONE_LON = 9.9, -84.1
config.SISMOS_ZONE_RADIUS_KM = 300.0
config.SISMOS_MIN_MAG_WORLD, config.SISMOS_MIN_MAG_ZONE = 4.0, 2.5

fallos = []
def check(c, m):
    print(("ok   " if c else "FALLA"), m)
    if not c: fallos.append(m)

class AppFalsa:
    def __init__(self): self.logs = []; self.eventos = []
    def log(self, m, nivel="info"): self.logs.append((nivel, m))
    def emit(self, tipo, **d): self.eventos.append((tipo, d))

def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t)) + ".0Z"

def emsc(unid, t, lat, lon, mag, region, auth="UNA", prof=20.0, evtype="ke"):
    return {"type": "Feature", "id": unid,
            "geometry": {"type": "Point", "coordinates": [lon, lat, -prof]},
            "properties": {"source_id": "2071602", "source_catalog": "EMSC-RTS",
                           "lastupdate": iso(t + 400), "time": iso(t),
                           "flynn_region": region, "lat": lat, "lon": lon,
                           "depth": prof, "evtype": evtype, "auth": auth,
                           "mag": mag, "magtype": "m", "unid": unid}}

def usgs(ident, t, lat, lon, mag, place, tsunami=0, tipo="earthquake", prof=10.0):
    return {"type": "Feature", "id": ident,
            "properties": {"mag": mag, "place": place, "time": int(t * 1000),
                           "updated": int((t + 120) * 1000), "tsunami": tsunami,
                           "url": "https://earthquake.usgs.gov/earthquakes/eventpage/" + ident,
                           "net": "us", "type": tipo},
            "geometry": {"type": "Point", "coordinates": [lon, lat, prof]}}

# ---------------------------------------------------------------- 1. lugares
print("-- El lugar, en espanol")
for ingles, esperado in [
    ("18 km NNE of Posoltega, Nicaragua", "A 18 km al NNE de Posoltega, Nicaragua"),
    ("79 km WSW of Masachapa, Nicaragua", "A 79 km al OSO de Masachapa, Nicaragua"),
    ("12 km N of Villa El Carmen, Nicaragua", "A 12 km al norte de Villa El Carmen, Nicaragua"),
    ("295 km S of Burica, Panama", "A 295 km al sur de Burica, Panamá"),
    ("PANAMA-COSTA RICA BORDER REGION", "Frontera Panamá-Costa Rica"),
    ("NEAR COAST OF NICARAGUA", "Cerca de la costa de Nicaragua"),
    ("OFF COAST OF COSTA RICA", "Frente a la costa de Costa Rica"),
    ("OFFSHORE TARAPACA, CHILE", "Frente a la costa de Tarapaca, Chile"),
    ("SOUTH OF PANAMA", "Al sur de Panamá"),
    ("SOUTHERN SUMATRA, INDONESIA", "Sur de Sumatra, Indonesia"),
    ("CENTRAL PERU", "Centro de Perú"),
    ("SOUTHWEST OF SUMATRA, INDONESIA", "Al suroeste de Sumatra, Indonesia"),
    ("NEAR EAST COAST OF HONSHU, JAPAN", "Cerca de la costa este de Honshu, Japón"),
    ("OFF EAST COAST OF KAMCHATKA", "Frente a la costa este de Kamchatka"),
    ("NORTHERN MID-ATLANTIC RIDGE", "Norte de la dorsal Mesoatlántica"),
    ("south of the Fiji Islands", "Al sur de Fiji Islands"),
    ("COSTA RICA", "Costa Rica"),
    ("CARIBBEAN SEA", "Mar Caribe"),
    ("HOKKAIDO, JAPAN REGION", "Región de Hokkaido, Japón"),
    ("GULF OF CALIFORNIA", "Gulf of California"),
    ("", "Lugar sin nombre"),
]:
    sale = sismos.lugar_es(ingles)
    check(sale == esperado, "%r -> %r" % (ingles, sale))

# ------------------------------------------------------------- 2. las fichas
print("-- Las fichas de cada fuente")
T = time.time()
s = sismos._de_emsc(emsc("20261008_0000111", T - 600, 9.5, -84.0, 4.2, "COSTA RICA"))
check(s and s["mag"] == 4.2 and s["prof"] == 20.0 and abs(s["t"] - (T - 600)) < 1.5,
      "EMSC: magnitud, profundidad (positiva) y hora")
check(s["agencia"] == "OVSICORI-UNA (Costa Rica)", "EMSC: la firma «UNA» es el OVSICORI -> %r" % s["agencia"])
check(sismos._de_emsc(emsc("x", T, 1, 1, 3.0, "X", evtype="se")) is None, "EMSC: una explosion no es un sismo")
check(abs(sismos._epoch("2026-10-04T14:06:09.72Z") - sismos._epoch("2026-10-04T14:06:09.0Z") - 0.72) < 1e-6,
      "EMSC: horas con dos decimales (Python viejo no las lee solo)")
u = sismos._de_usgs(usgs("us7000abcd", T - 300, 12.5, -87.0, 4.64, "18 km NNE of Posoltega, Nicaragua", tsunami=1))
check(u and u["mag"] == 4.6 and u["tsunami"] is True and u["lugar"].startswith("A 18 km al NNE"),
      "USGS: magnitud redondeada, marca de tsunami y lugar")
check(sismos._de_usgs(usgs("ci1", T, 34, -118, 1.2, "Quarry", tipo="quarry blast")) is None,
      "USGS: una cantera no es un sismo")
check(abs(sismos.distancia_km(9.9, -84.1, 9.9, -84.1)) < 0.01
      and 330 < sismos.distancia_km(9.93, -84.08, 12.13, -86.25) < 350,
      "distancia San Jose - Managua: %.0f km (son unos 340)" % sismos.distancia_km(9.93, -84.08, 12.13, -86.25))

# ------------------------------------------------- 3. el ciclo, sin internet
print("-- El ciclo completo, con las fuentes de mentira")
app = AppFalsa()
S = sismos.Sismos(app)
RED = {"emsc": [], "usgs": [], "caida": set()}
def bajar_emsc(completa, zona, ahora):
    if "emsc" in RED["caida"]: raise OSError("sin red")
    return [x for x in map(sismos._de_emsc, RED["emsc"]) if x]
def bajar_usgs(completa):
    if "usgs" in RED["caida"]: raise OSError("sin red")
    return [x for x in map(sismos._de_usgs, RED["usgs"]) if x]
S._bajar_emsc, S._bajar_usgs = bajar_emsc, bajar_usgs

T = time.time()
RED["emsc"] = [
    emsc("e1", T - 3 * 86400, 9.6, -84.2, 2.7, "COSTA RICA"),               # chico, en la zona
    emsc("e2", T - 2 * 3600, -30.5, -69.1, 2.6, "SAN JUAN, ARGENTINA"),     # chico y lejos: fuera
    emsc("e3", T - 86400, 12.42, -86.90, 4.6, "NICARAGUA", auth="INET"),    # el mismo que u1
    emsc("e4", T - 8 * 86400, 9.0, -83.0, 5.0, "COSTA RICA"),               # de hace 8 dias: fuera
    emsc("e5", T - 1200, 35.0, 139.0, 5.8, "NEAR EAST COAST OF HONSHU, JAPAN", auth="JMA"),
]
RED["usgs"] = [
    usgs("u1", T - 86400 + 6, 12.50, -86.95, 4.6, "18 km NNE of Posoltega, Nicaragua", tsunami=1),
    usgs("u2", T - 5000, 61.0, -150.0, 3.1, "30 km N of Anchorage, Alaska"),   # chico y lejos: fuera
    usgs("u3", T - 4000, -20.0, -175.0, 6.2, "Tonga"),
]
S._consultar()
snap = S.snapshot()
ids = [x["id"] for x in snap["sismos"]]
check(ids == ["emsc:e5", "usgs:u3", "emsc:e3", "emsc:e1"], "se guardan 4, del mas reciente al mas viejo -> %s" % ids)
e3 = [x for x in snap["sismos"] if x["id"] == "emsc:e3"][0]
check(e3["fuentes"] == ["EMSC", "USGS"] and e3["tsunami"] is True,
      "el sismo que cuentan las DOS fuentes sale una vez, con las dos anotadas")
e1 = [x for x in snap["sismos"] if x["id"] == "emsc:e1"][0]
check(e1["cerca"] is True and 20 < e1["dist"] < 60, "el de Costa Rica esta «cerca» (%s km)" % e1["dist"])
check(e3["cerca"] is False and 380 < e3["dist"] < 480, "el de Nicaragua queda fuera del radio de 300 km (%s km)" % e3["dist"])
ev = app.eventos[-1]
check(ev[0] == "sismos" and ev[1]["nuevos"] == [] and ev[1]["total"] == 4,
      "la PRIMERA carga no anuncia nada como nuevo (es historia)")
check(snap["zona"]["nombre"] == "Costa Rica" and snap["activo"] and snap["consultado"] > 0 and snap["error"] is None,
      "la respuesta para el panel trae zona, hora de consulta y sin error")
check(any("4 en los últimos 7 días" in m for _, m in app.logs), "avisa en el registro al conectar")

# Aparece uno nuevo en la zona y otro fuerte lejos.
RED["emsc"].append(emsc("e6", time.time() - 420, 9.4, -84.6, 4.8, "OFF COAST OF COSTA RICA"))
RED["usgs"].append(usgs("u4", time.time() - 200, 38.0, 142.0, 7.1, "100 km E of Sendai, Japan"))
S._consultar()
nuevos = [x["id"] for x in app.eventos[-1][1]["nuevos"]]
check(sorted(nuevos) == ["emsc:e6", "usgs:u4"], "los dos que aparecen despues SI son nuevos -> %s" % nuevos)
check(any(n == "warn" and "magnitud 4.8" in m and "Costa Rica" in m for n, m in app.logs),
      "el de la zona se avisa en el registro, con los km")
check(any("Sismo fuerte en el mundo: magnitud 7.1" in m for _, m in app.logs), "el de 7.1 tambien se avisa")
S._consultar()
check(app.eventos[-1][1]["nuevos"] == [], "consultar otra vez lo mismo no repite el aviso")

# La red revisa la magnitud: misma ficha, otro numero.
RED["emsc"][-1] = emsc("e6", time.time() - 430, 9.4, -84.6, 5.1, "OFF COAST OF COSTA RICA")
S._consultar()
e6 = [x for x in S.snapshot()["sismos"] if x["id"] == "emsc:e6"][0]
check(e6["mag"] == 5.1 and app.eventos[-1][1]["nuevos"] == [], "una magnitud revisada se actualiza sin contar como sismo nuevo")

# Se cae internet: el mapa se queda con lo que tenia y lo dice UNA vez.
RED["caida"] = {"emsc", "usgs"}
antes = len(S.snapshot()["sismos"])
S._consultar(); S._consultar()
snap = S.snapshot()
check(len(snap["sismos"]) == antes and snap["error"], "sin internet conserva la lista y marca el error")
check(sum(1 for _, m in app.logs if "no pude consultar" in m) == 1, "y lo avisa una sola vez, no cada minuto")
RED["caida"] = {"usgs"}
S._consultar()
check(S.snapshot()["error"].startswith("USGS"), "si solo falla una fuente, sigue con la otra y lo anota")
RED["caida"] = set()
S._consultar()
check(S.snapshot()["error"] is None, "al volver internet se limpia el error")

# Cambia «mi zona»: se recarga todo y no anuncia la historia como nueva.
config.SISMOS_ZONE_NAME, config.SISMOS_ZONE_LAT, config.SISMOS_ZONE_LON = "Japón", 35.7, 139.7
S._consultar()
snap = S.snapshot()
e5 = [x for x in snap["sismos"] if x["id"] == "emsc:e5"][0]
check(e5["cerca"] is True and app.eventos[-1][1]["nuevos"] == [],
      "al cambiar la zona se recalcula quien esta cerca, sin avisos falsos")
check(not any(x["id"] == "emsc:e1" for x in snap["sismos"]), "y el chico de Costa Rica ya no entra (ahora queda lejos)")

if "--red" in sys.argv:
    print("-- Con las fuentes DE VERDAD (necesita internet)")
    config.SISMOS_ZONE_NAME, config.SISMOS_ZONE_LAT, config.SISMOS_ZONE_LON = "Costa Rica", 9.9, -84.1
    app = AppFalsa()
    S = sismos.Sismos(app)
    t0 = time.time()
    S._consultar()
    snap = S.snapshot()
    lista = snap["sismos"]
    print("   tardo %.1f s · %d sismos · error: %s" % (time.time() - t0, len(lista), snap["error"]))
    check(len(lista) > 50 and snap["error"] is None, "las dos fuentes contestan y traen datos")
    cerca = [x for x in lista if x["cerca"]]
    dobles = [x for x in lista if len(x["fuentes"]) > 1]
    print("   cerca de Costa Rica: %d · contados por las dos fuentes: %d" % (len(cerca), len(dobles)))
    check(len(dobles) > 5, "se juntan los sismos repetidos entre fuentes")
    check(all(x["mag"] >= 4.0 or x["cerca"] for x in lista), "lejos de la zona solo quedan los de 4.0 para arriba")
    for x in lista[:6] + cerca[:6]:
        print("   M%.1f  hace %4d min  %5d km  %-12s %s" % (
            x["mag"], (time.time() - x["t"]) / 60, x["dist"], "+".join(x["fuentes"]), x["lugar"]))
    t0 = time.time()
    S._consultar()
    print("   la consulta de cada minuto tardo %.1f s y trajo %d nuevos" % (
        time.time() - t0, len(app.eventos[-1][1]["nuevos"])))

print()
if fallos:
    print("FALLARON %d:" % len(fallos))
    for f in fallos: print("  -", f)
    sys.exit(1)
print("TODO BIEN")
