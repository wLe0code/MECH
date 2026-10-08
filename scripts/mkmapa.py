"""Genera el MAPA del mundo de la vista «Sismos» del panel, para servirlo EN LOCAL.

Los mapas de internet (los de cuadritos que se bajan al moverse) no valen
aqui: el panel no puede cargar nada de fuera. Asi que el contorno de los
paises va dentro del repo, como los iconos y las fuentes.

Sale de Natural Earth a escala 1:50m (dominio publico), en el empaquetado
`world-atlas` (TopoJSON). Este script lo baja, se queda con lo que el panel
dibuja (costas y fronteras) y lo guarda compacto en
frontend/vendor/mech-mapa.json:

    q          cuantas unidades por grado (los numeros van como enteros)
    arcos      cada tramo de linea: [lon, lat, dlon, dlat, dlon, dlat, ...]
    tierra     anillos de tierra firme, como listas de arcos (un numero
               negativo ~i es el arco i recorrido al reves)
    fronteras  los arcos que separan dos paises

    python scripts/mkmapa.py          (necesita internet)

Solo hay que volver a correrlo si se pierde el archivo.
"""
import io, json, os, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, "frontend", "vendor", "mech-mapa.json")
URL = "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-50m.json"
Q = 200   # 1/200 de grado = unos 550 m: de sobra para lo que se acerca el mapa

print("Bajando", URL)
with urllib.request.urlopen(URL, timeout=60) as r:
    topo = json.loads(r.read().decode("utf-8"))

sx, sy = topo["transform"]["scale"]
tx, ty = topo["transform"]["translate"]


def puntos(arco):
    """Un arco de TopoJSON (diferencias acumuladas) -> [(lon, lat), ...] en unidades Q."""
    x = y = 0
    out = []
    for dx, dy in arco:
        x += dx
        y += dy
        p = (int(round((x * sx + tx) * Q)), int(round((y * sy + ty) * Q)))
        if not out or out[-1] != p:      # al redondear se repiten puntos: fuera
            out.append(p)
    return out


def anillos(geom):
    if geom["type"] == "Polygon":
        return list(geom["arcs"])
    if geom["type"] == "MultiPolygon":
        return [a for poligono in geom["arcs"] for a in poligono]
    return []


def base(i):
    return i if i >= 0 else ~i


# Tierra firme: el objeto `land` es la union de todos los paises (solo costas).
tierra = [a for g in topo["objects"]["land"]["geometries"] for a in anillos(g)]

# Fronteras: los arcos que usan DOS paises. Los que usa uno solo son costa.
usos = {}
for g in topo["objects"]["countries"]["geometries"]:
    for anillo in anillos(g):
        for i in anillo:
            usos[base(i)] = usos.get(base(i), 0) + 1
fronteras = sorted(i for i, n in usos.items() if n >= 2)

# Solo los arcos que se dibujan, renumerados.
usados = sorted({base(i) for anillo in tierra for i in anillo} | set(fronteras))
nuevo = {viejo: n for n, viejo in enumerate(usados)}


def renumera(i):
    return nuevo[i] if i >= 0 else ~nuevo[~i]


arcos = []
total = 0
for viejo in usados:
    pts = puntos(topo["arcs"][viejo])
    total += len(pts)
    plano = [pts[0][0], pts[0][1]]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        plano += [x1 - x0, y1 - y0]
    arcos.append(plano)

salida = {
    "fuente": "Natural Earth 1:50m (dominio publico), via world-atlas 2.0.2. "
              "Generado con scripts/mkmapa.py.",
    "q": Q,
    "arcos": arcos,
    "tierra": [[renumera(i) for i in anillo] for anillo in tierra],
    "fronteras": [nuevo[i] for i in fronteras],
}
with io.open(DEST, "w", encoding="utf-8", newline="\n") as f:
    f.write(json.dumps(salida, separators=(",", ":")))

print("arcos: %d (%d de frontera) · puntos: %d · anillos de tierra: %d"
      % (len(arcos), len(fronteras), total, len(salida["tierra"])))
print("guardado en %s (%d KB)" % (DEST, os.path.getsize(DEST) // 1024))
