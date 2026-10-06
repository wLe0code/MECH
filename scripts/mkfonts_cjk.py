"""Descarga las letras para COREANO, JAPONES y CHINO y las deja EN LOCAL.

Sora y Space Mono (las fuentes del panel) solo traen el alfabeto latino. Para
las demas escrituras el navegador tira de lo que tenga instalado el aparato...
y la Raspberry Pi no trae letra coreana: en el panel, en los subtitulos y en
la trivia salian CUADRITOS en vez de texto. Antes habia que instalar
`fonts-noto-cjk` a mano en cada Pi; con esto las letras viajan con el repo.

Son las Noto Sans KR / JP / SC de Google Fonts (SIL Open Font License), peso
400. Google reparte cada familia en un centenar de trozos (`unicode-range`) y
el navegador solo carga los trozos cuyos caracteres aparecen en pantalla, asi
que tenerlas no hace mas lento el panel: en espanol no se carga ninguno.

Solo se guardan los trozos NUMERADOS (hangul, kana, ideogramas y su
puntuacion). Los de latin / cirilico / vietnamita se dejan fuera, y a los
numerados se les recorta el `unicode-range` a los bloques de `SOLO` (traen
tambien las letras A-Z, los numeros, flechas, figuras y algun emoji). Es a
proposito: asi estas fuentes NUNCA dibujan otra cosa que coreano, japones o
chino, y el resto del panel y de la proyeccion se ve exactamente como antes.

El CSS acaba con la variable `--cjk`: el orden en que se prueban las tres
familias. Chino y japones comparten miles de caracteres que cada pais dibuja
un poco distinto, asi que con `lang="ja"` va primero la japonesa y con
`lang="zh"` la china. Las paginas la usan asi:
    font-family: 'Sora', var(--cjk, sans-serif), sans-serif;

Uso (hace falta internet; pesa unos 7 MB):
    python scripts/mkfonts_cjk.py            # baja lo que falte
    python scripts/mkfonts_cjk.py --todo     # vuelve a bajarlo todo
"""
import io, os, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VEN = os.path.join(ROOT, "frontend", "vendor")
DEST = os.path.join(VEN, "fonts", "cjk")
os.makedirs(DEST, exist_ok=True)

# (familia en Google Fonts, prefijo de los archivos)
FAMILIAS = [("Noto Sans KR", "kr"), ("Noto Sans JP", "jp"), ("Noto Sans SC", "sc")]
# Sin un navegador moderno como User-Agent, Google devuelve .ttf en vez de .woff2.
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
TODO = "--todo" in sys.argv


def pedir(url):
    ultimo = None
    for _ in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=40).read()
        except Exception as e:  # red floja: se reintenta
            ultimo = e
    raise ultimo


# Lo UNICO que estas fuentes pueden dibujar. Fuera queda todo lo demas que
# traen: letras latinas, numeros, flechas, figuras geometricas, emojis...
# El panel usa muchos de esos simbolos en sus botones, y sin este filtro
# cambiaban de aspecto (las flechas de una fuente china son mas anchas).
SOLO = [
    (0x1100, 0x11FF),    # hangul: piezas sueltas (jamo)
    (0x2E80, 0x9FFF),    # radicales, puntuacion CJK, kana, ideogramas
    (0xA960, 0xA97F),    # hangul: jamo extendido A
    (0xAC00, 0xD7FF),    # hangul: silabas
    (0xF900, 0xFAFF),    # ideogramas de compatibilidad
    (0xFE30, 0xFE4F),    # formas CJK de compatibilidad
    (0xFF00, 0xFFEF),    # ancho completo y katakana de medio ancho
    (0x20000, 0x3FFFF),  # ideogramas raros (extensiones B en adelante)
]


def solo_cjk(rango):
    """Recorta un `unicode-range` a los bloques de SOLO."""
    partes = []
    for trozo in rango.split(","):
        a, _, b = trozo.strip()[2:].partition("-")
        lo, hi = int(a, 16), int(b or a, 16)
        for desde, hasta in SOLO:
            x, y = max(lo, desde), min(hi, hasta)
            if x <= y:
                partes.append("U+%x" % x if x == y else "U+%x-%x" % (x, y))
    return ",".join(partes)


def bajar(tarea):
    url, destino = tarea
    if TODO or not os.path.exists(destino) or os.path.getsize(destino) == 0:
        datos = pedir(url)
        with open(destino, "wb") as f:
            f.write(datos)
    return os.path.getsize(destino)


reglas, tareas, resumen = [], [], []
for familia, pre in FAMILIAS:
    css = pedir("https://fonts.googleapis.com/css2?family=%s:wght@400&display=swap"
                % familia.replace(" ", "+")).decode("utf-8")
    n = 0
    for bloque in re.findall(r"@font-face\s*\{[^}]*\}", css):
        url = re.search(r"url\((https://[^)]+\.woff2)\)", bloque)
        rango = re.search(r"unicode-range:\s*([^;]+);", bloque)
        # Los trozos numerados acaban en ".<n>.woff2"; los de latin, cirilico
        # y vietnamita no llevan numero.
        num = url and re.search(r"\.(\d+)\.woff2$", url.group(1))
        if not (num and rango):
            continue
        limpio = solo_cjk(rango.group(1))
        if not limpio:
            continue  # un trozo que solo traia simbolos o letras latinas
        nombre = "%s-%03d.woff2" % (pre, int(num.group(1)))
        tareas.append((url.group(1), os.path.join(DEST, nombre)))
        reglas.append(
            "@font-face{font-family:'%s';font-style:normal;font-weight:400;"
            "font-display:swap;src:url(./fonts/cjk/%s) format('woff2');"
            "unicode-range:%s}" % (familia, nombre, limpio))
        n += 1
    resumen.append((familia, pre, n))

with ThreadPoolExecutor(max_workers=8) as pool:
    tamanos = list(pool.map(bajar, tareas))

# Fuera lo que ya no pide el CSS (trozos de una version anterior).
vigentes = {os.path.basename(d) for _, d in tareas}
for f in os.listdir(DEST):
    if f.endswith(".woff2") and f not in vigentes:
        os.remove(os.path.join(DEST, f))

texto = (
    "/* Letras para coreano, japones y chino - Noto Sans KR / JP / SC\n"
    " * (SIL Open Font License), peso 400.\n"
    " *\n"
    " * SE SIRVEN EN LOCAL A PROPOSITO: la Raspberry Pi no trae letra coreana\n"
    " * y el texto salia como cuadritos. Cada familia va en trozos\n"
    " * (unicode-range): el navegador solo carga los que hacen falta, asi que\n"
    " * en espanol no se carga ninguno.\n"
    " *\n"
    " * Generado con scripts/mkfonts_cjk.py. Solo hangul, kana e ideogramas:\n"
    " * ni letras latinas, ni flechas, ni emojis, para que estas fuentes no\n"
    " * le cambien el aspecto a nada mas. NO editar a mano.\n"
    " */\n" + "\n".join(reglas) + "\n"
    "/* En que orden se prueban (ver la cabecera de scripts/mkfonts_cjk.py).\n"
    " * Uso: font-family: 'Sora', var(--cjk, sans-serif), sans-serif; */\n"
    ":root{--cjk:'Noto Sans KR','Noto Sans JP','Noto Sans SC'}\n"
    ":lang(ja){--cjk:'Noto Sans JP','Noto Sans KR','Noto Sans SC'}\n"
    ":lang(zh){--cjk:'Noto Sans SC','Noto Sans JP','Noto Sans KR'}\n"
)
io.open(os.path.join(VEN, "mech-fonts-cjk.css"), "w", encoding="utf-8", newline="\n").write(texto)

for familia, pre, n in resumen:
    peso = sum(t for (u, d), t in zip(tareas, tamanos)
               if os.path.basename(d).startswith(pre + "-"))
    print("%-13s %3d trozos  %6.2f MB" % (familia, n, peso / 1e6))
print("total: %d archivos, %.2f MB en frontend/vendor/fonts/cjk/" % (len(tareas), sum(tamanos) / 1e6))
print("CSS: frontend/vendor/mech-fonts-cjk.css  (%d KB, %d reglas)" % (len(texto) // 1024, len(reglas)))
