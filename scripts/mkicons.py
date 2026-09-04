"""Genera un CSS de iconos MINIMO con solo los que usa el panel.

El CSS del CDN son 200 KB con 4962 iconos; el panel usa 42. Extraemos solo
esos, y apuntamos la fuente al .woff2 local para que todo funcione SIN
INTERNET (en la competencia no se puede depender del wifi del recinto).
"""
import io, os, re, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
full = io.open(os.path.join(ROOT, "frontend/vendor/tabler-icons.min.css"),
               encoding="utf-8").read()

# Qué iconos usa realmente el frontend (HTML + JS).
usados = set()
for f in glob.glob(os.path.join(ROOT, "frontend", "*.html")) + \
         glob.glob(os.path.join(ROOT, "frontend", "*.js")):
    usados |= set(re.findall(r"ti ti-([a-z0-9-]+)", io.open(f, encoding="utf-8").read()))

reglas, faltan = [], []
for nombre in sorted(usados):
    m = re.search(r"\.ti-" + re.escape(nombre) + r":before\{[^}]*\}", full)
    if m:
        reglas.append(m.group(0))
    else:
        faltan.append(nombre)

base = re.search(r"\.ti\s*\{[^}]*\}", full).group(0)

salida = [
    "/* Iconos del panel de MECH - subconjunto de Tabler Icons 2.47.0 (MIT).",
    " *",
    " * SE SIRVE EN LOCAL A PROPOSITO: antes esto venia de un CDN y sin",
    " * internet los botones se quedaban SIN ICONO (varios son solo icono, o",
    " * sea botones en blanco). En la competencia no se puede depender del",
    " * wifi del recinto.",
    " *",
    " * Generado con scripts/mkicons.py a partir del CSS oficial: solo",
    f" * los {len(reglas)} iconos que usa el frontend, no los 4962 del paquete.",
    " * Si anadis un icono nuevo al panel, volve a correr el script.",
    " */",
    '@font-face{font-family:"tabler-icons";font-style:normal;font-weight:400;'
    'src:url("./fonts/tabler-icons.woff2") format("woff2");font-display:block}',
    base,
]
salida += reglas
css = "\n".join(salida) + "\n"
dest = os.path.join(ROOT, "frontend/vendor/mech-icons.css")
io.open(dest, "w", encoding="utf-8").write(css)

print(f"iconos usados por el frontend: {len(usados)}")
print(f"reglas generadas:              {len(reglas)}")
print(f"NO encontrados en Tabler:      {faltan or 'ninguno'}")
print(f"tamano: {len(css)} bytes (el CSS completo eran {len(full)})")
