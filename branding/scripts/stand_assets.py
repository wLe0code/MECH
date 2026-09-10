# Assets para el STAND de MECH — PNG con FONDO TRANSPARENTE, alta resolucion.
# Pensados para colocarse DEBAJO de las tarjetas M / E / C / H.
#
# Salida: branding/stand/
#   frase-en.png / frase-es.png          ← el lema en dos lineas (principal)
#   frase-en-1linea.png                  ← variante para espacios anchos
#   divisor.png                          ← franja de pixeles (separador)
#   datos-en.png / datos-es.png          ← tres cifras clave, aireadas
#
# Todo se dibuja a 2x y se reduce con LANCZOS; luego se recorta al contenido
# para que el PNG no traiga transparencia sobrante y sea facil de colocar.

import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SS = 2                       # supersampling
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'stand'))
os.makedirs(OUT, exist_ok=True)

# Paleta del sitio
TEXT   = (240, 238, 255)
MUTED  = (155, 155, 173)
DIM    = (106, 106, 124)
RED    = (226, 75, 74)
PURPLE = (127, 119, 221)
TEAL   = (29, 158, 117)
GRAD   = [(0.0, RED), (0.58, PURPLE), (1.0, TEAL)]

_fc = {}
def sora(size, weight=800):
    k = ('sora', size, weight)
    if k not in _fc:
        f = ImageFont.truetype('Sora.ttf', int(size * SS))
        try: f.set_variation_by_axes([weight])
        except Exception: pass
        _fc[k] = f
    return _fc[k]

def mono(size, bold=True):
    k = ('mono', size, bold)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(
            'SpaceMono-Bold.ttf' if bold else 'SpaceMono-Regular.ttf', int(size * SS))
    return _fc[k]

def canvas(w, h):
    return Image.new('RGBA', (int(w * SS), int(h * SS)), (0, 0, 0, 0))

def skew(layer, deg):
    """Italica sintetica / inclinacion, alrededor del centro vertical."""
    t = math.tan(math.radians(deg))
    cy = layer.height / 2
    return layer.transform(layer.size, Image.AFFINE, (1, t, -t * cy, 0, 1, 0),
                           resample=Image.BICUBIC)

def _mask(size, xy, text, f, anchor, italic):
    m = Image.new('L', size, 0)
    ImageDraw.Draw(m).text((xy[0] * SS, xy[1] * SS), text, font=f, fill=255, anchor=anchor)
    return skew(m, italic) if italic else m

def solid(cv, xy, text, f, color, anchor='mm', italic=0):
    m = _mask(cv.size, xy, text, f, anchor, italic)
    layer = Image.new('RGBA', cv.size, color + (0,))
    layer.putalpha(m)
    cv.alpha_composite(layer)

def gradient_strip(w, h, stops):
    xs = np.linspace(0, 1, max(w, 2))
    pts = [s[0] for s in stops]
    cols = [np.array(s[1], np.float32) for s in stops]
    row = np.zeros((1, max(w, 2), 3), np.float32)
    for i, x in enumerate(xs):
        for j in range(len(pts) - 1):
            if pts[j] <= x <= pts[j + 1]:
                fr = (x - pts[j]) / (pts[j + 1] - pts[j] + 1e-9)
                row[0, i] = cols[j] * (1 - fr) + cols[j + 1] * fr
                break
        else:
            row[0, i] = cols[-1] if x > pts[-1] else cols[0]
    return Image.fromarray(np.repeat(row.astype(np.uint8), max(h, 2), axis=0), 'RGB')

def grad(cv, xy, text, f, anchor='mm', italic=0, stops=GRAD):
    m = _mask(cv.size, xy, text, f, anchor, italic)
    bb = m.getbbox()
    if not bb:
        return
    g = gradient_strip(bb[2] - bb[0], bb[3] - bb[1], stops)
    full = Image.new('RGB', cv.size, stops[0][1])
    full.paste(g, (bb[0], bb[1]))
    rgba = full.convert('RGBA')
    rgba.putalpha(m)
    cv.alpha_composite(rgba)

def save(cv, name, margin=26, target_w=None):
    """Recorta al contenido, deja un margen y guarda."""
    bb = cv.getbbox()
    if bb:
        m = int(margin * SS)
        bb = (max(0, bb[0] - m), max(0, bb[1] - m),
              min(cv.width, bb[2] + m), min(cv.height, bb[3] + m))
        cv = cv.crop(bb)
    w = target_w or cv.width // SS
    h = round(cv.height * w / cv.width)
    cv = cv.resize((w, h), Image.LANCZOS)
    p = os.path.join(OUT, name)
    cv.save(p, 'PNG', optimize=True)
    print(f'{name:26s} {cv.size[0]}x{cv.size[1]}  {os.path.getsize(p)//1024} KB')

# ═══════════════════════════════════════════════════════════════════════
# 1) EL LEMA — dos lineas, centrado (el principal)
# ═══════════════════════════════════════════════════════════════════════
def frase(l1, l2, name, size=200, italic2=11):
    cv = canvas(3400, 900)
    cx = 1700
    solid(cv, (cx, 300), l1, sora(size, 800), TEXT, anchor='mm')
    grad(cv, (cx, 300 + size * 1.06), l2, sora(size, 800), anchor='mm', italic=italic2)
    save(cv, name, margin=30, target_w=3600)

frase('We spark interest in', 'what truly matters.', 'frase-en.png')
frase('Despertamos el interés', 'en lo que de verdad importa.',
      'frase-es.png', size=178)

# Variante de UNA linea (para espacios anchos)
def frase_1linea(a, b, name, size=170):
    cv = canvas(6000, 500)
    d = ImageDraw.Draw(cv)
    fa, fb = sora(size, 800), sora(size, 800)
    wa = d.textlength(a + ' ', font=fa) / SS
    wb = d.textlength(b, font=fb) / SS
    total = wa + wb
    x0 = 3000 - total / 2
    solid(cv, (x0, 250), a + ' ', fa, TEXT, anchor='lm')
    grad(cv, (x0 + wa, 250), b, fb, anchor='lm', italic=11)
    save(cv, name, margin=30, target_w=4200)

frase_1linea('We spark interest in', 'what truly matters.', 'frase-en-1linea.png')

# ═══════════════════════════════════════════════════════════════════════
# 2) DIVISOR — la franja de pixeles de la marca (separa sin ruido)
# ═══════════════════════════════════════════════════════════════════════
def divisor(name='divisor.png', w=3000, alpha=58):
    cv = canvas(w, 46)
    d = ImageDraw.Draw(cv)
    rects = [(6,8,13),(26,18,9),(44,6,11),(60,22,14),(82,9,9),(97,20,12),
             (116,7,14),(138,19,9),(154,8,11),(172,21,12),(192,9,9),(206,19,10)]
    x0 = 0
    while x0 < w:
        for rx, ry, rw in rects:
            X, Y = (x0 + rx) * SS, ry * SS
            d.rectangle([X, Y, X + rw * SS, Y + rw * 0.9 * SS],
                        fill=TEXT + (alpha,))
        x0 += 220
    save(cv, name, margin=0, target_w=3000)

divisor()

# ═══════════════════════════════════════════════════════════════════════
# 3) TRES CIFRAS CLAVE — aireadas, sin cajas ni fondos
# ═══════════════════════════════════════════════════════════════════════
def datos(items, name, num=130, lab=30):
    """Las cifras comparten UN degradado que recorre toda la fila: asi cada
    numero toma un tramo (rojo -> morado -> teal) y se leen como un sistema,
    en vez de meter el arcoiris entero dentro de cada numero corto."""
    cv = canvas(3400, 460)
    n = len(items)
    step = 3400 / n

    # 1) una sola mascara con las TRES cifras
    figs = Image.new('L', cv.size, 0)
    df = ImageDraw.Draw(figs)
    for i, (fig, _, _) in enumerate(items):
        df.text((step * (i + 0.5) * SS, 150 * SS), fig,
                font=sora(num, 800), fill=255, anchor='mm')
    bb = figs.getbbox()
    g = gradient_strip(bb[2] - bb[0], bb[3] - bb[1], GRAD)
    full = Image.new('RGB', cv.size, GRAD[0][1])
    full.paste(g, (bb[0], bb[1]))
    rgba = full.convert('RGBA')
    rgba.putalpha(figs)
    cv.alpha_composite(rgba)

    # 2) etiquetas y separadores
    for i, (_, l1, l2) in enumerate(items):
        cx = step * (i + 0.5)
        solid(cv, (cx, 268), l1, mono(lab), MUTED, anchor='mm')
        if l2:
            solid(cv, (cx, 268 + lab * 1.9), l2, mono(lab), DIM, anchor='mm')
        if i < n - 1:
            x = step * (i + 1)
            ImageDraw.Draw(cv).line([(x * SS, 78 * SS), (x * SS, 300 * SS)],
                                    fill=TEXT + (34,), width=int(1.6 * SS))
    save(cv, name, margin=30, target_w=3400)

datos([('+40%', 'MORE INTEREST', 'RETENTION'),
       ('8 h', 'OF BATTERY', 'A FULL SCHOOL DAY'),
       ('100%', 'ON-DEVICE VOICE', 'NO INTERNET NEEDED')], 'datos-en.png')

datos([('+40%', 'MÁS RETENCIÓN', 'DEL INTERÉS'),
       ('8 h', 'DE AUTONOMÍA', 'UN DÍA ESCOLAR'),
       ('100%', 'VOZ PROCESADA', 'EN EL PROPIO ROBOT')], 'datos-es.png')
