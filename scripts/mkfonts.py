"""Descarga las fuentes del panel para servirlas EN LOCAL (sin internet).

Antes styles.css hacia @import a Google Fonts: sin red, el panel caia a las
fuentes del sistema. No es fatal, pero en la competencia no queremos que
nada dependa del wifi del recinto.
"""
import io, os, re, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VEN = os.path.join(ROOT, "frontend", "vendor")
FON = os.path.join(VEN, "fonts")
os.makedirs(FON, exist_ok=True)

css = io.open(os.path.join(VEN, "_gf.css"), encoding="utf-8").read()

# Nos quedamos SOLO con los bloques latin/latin-ext: el resto (cirilico,
# griego, vietnamita...) son megas que no vamos a usar nunca.
bloques = re.findall(r"/\*\s*([\w\-\[\]0-9]+)\s*\*/\s*(@font-face\s*\{[^}]*\})", css)
salida, bajados = [], {}
for subset, bloque in bloques:
    if subset not in ("latin", "latin-ext"):
        continue
    url = re.search(r"url\((https://[^)]+\.woff2)\)", bloque)
    if not url:
        continue
    url = url.group(1)
    nombre = url.rsplit("/", 1)[-1]
    destino = os.path.join(FON, nombre)
    if nombre not in bajados:
        urllib.request.urlretrieve(url, destino)
        bajados[nombre] = os.path.getsize(destino)
    salida.append(bloque.replace(url, "./fonts/" + nombre))

texto = (
    "/* Fuentes del panel de MECH - Sora y Space Mono (SIL Open Font License).\n"
    " *\n"
    " * SE SIRVEN EN LOCAL A PROPOSITO: antes styles.css hacia @import a\n"
    " * Google Fonts y sin internet el panel caia a las fuentes del sistema.\n"
    " * En la competencia no puede depender del wifi del recinto.\n"
    " *\n"
    " * Generado con scripts/mkfonts.py. Solo los subsets latin y latin-ext.\n"
    " */\n" + "\n".join(salida) + "\n"
)
io.open(os.path.join(VEN, "mech-fonts.css"), "w", encoding="utf-8").write(texto)
os.remove(os.path.join(VEN, "_gf.css"))

total = sum(bajados.values())
print(f"archivos de fuente: {len(bajados)}  ({total/1024:.0f} KB en total)")
for n, s in sorted(bajados.items()):
    print(f"   {n:42} {s/1024:6.1f} KB")
print(f"CSS generado: {len(texto)} bytes, {len(salida)} bloques @font-face")
