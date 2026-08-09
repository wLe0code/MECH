# Render de MECH-1 centrado, alta calidad. Genera:
#   branding/render-mech.png             ← sobre fondo de marca con glow
#   branding/render-mech-transparent.png ← recorte con canal alfa (sombra suave)
#
# El robot se porta del SVG del sitio (mismos colores y proporciones), dibujado
# en RGBA a 2x con sombra oscura suave (sirve en fondo oscuro y transparente).

import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SS = 2
W, H = 2200, 2600
CW, CH = W * SS, H * SS
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

BG     = (0, 0, 0)
RED    = (226, 75, 74)
PURPLE = (127, 119, 221)
TEAL   = (29, 158, 117)

CUERPO = (23, 23, 30)
NEGRO  = (10, 10, 14)
BORDE  = (52, 52, 62)
CLARO  = (242, 241, 244)

def draw_robot_rgba(ox, oy, s):
    """Dibuja el robot en una capa RGBA (CW×CH) y la devuelve."""
    layer = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    X = lambda v: (ox + v * s) * SS
    Y = lambda v: (oy + v * s) * SS
    def rbox(x0, y0, x1, y1, r, **kw): d.rounded_rectangle([X(x0), Y(y0), X(x1), Y(y1)], radius=r * s * SS, **kw)
    def ell(x0, y0, x1, y1, **kw): d.ellipse([X(x0), Y(y0), X(x1), Y(y1)], **kw)
    W2 = lambda w: max(int(w * s * SS), 1)

    # discos laterales
    ell(126, 400, 178, 640, fill=NEGRO, outline=BORDE, width=W2(2))
    ell(422, 400, 474, 640, fill=NEGRO, outline=BORDE, width=W2(2))
    # cuerpo
    d.rectangle([X(168), Y(340), X(432), Y(670)], fill=CUERPO)
    ell(168, 644, 432, 696, fill=CUERPO)
    # tapa superior
    ell(168, 314, 432, 366, fill=CLARO, outline=NEGRO, width=W2(3))
    # franja de píxeles
    px = [(188,382,20),(214,396,14),(236,378,16),(258,398,22),(288,380,14),
          (308,400,18),(334,382,22),(362,398,14),(384,380,16),(196,418,12),
          (246,422,14),(298,424,12),(348,420,14),(396,416,12)]
    for x, y, w in px:
        d.rectangle([X(x), Y(y), X(x + w), Y(y + w * 0.9)], fill=CLARO)
    for x, y in [(252,648),(300,654),(348,648)]:
        ell(x-5, y-5, x+5, y+5, fill=CLARO)
    # ruedas
    ell(214, 700, 266, 732, fill=NEGRO)
    ell(334, 700, 386, 732, fill=NEGRO)
    # cuello
    rbox(278, 286, 322, 346, 8, fill=NEGRO)
    # cabeza
    rbox(134, 152, 466, 232, 16, fill=CLARO, outline=NEGRO, width=W2(3))
    rbox(134, 176, 466, 292, 16, fill=(16, 16, 20), outline=BORDE, width=W2(2))
    # lente del proyector
    ell(192, 180, 284, 272, fill=(10, 10, 13), outline=CLARO, width=W2(5))
    ell(208, 196, 268, 256, fill=(17, 19, 28))
    ell(221, 209, 255, 243, fill=(27, 32, 51))
    ell(222, 210, 234, 222, fill=(143, 151, 196))
    # cámara
    rbox(352, 210, 418, 244, 8, fill=(35, 35, 41), outline=(58, 58, 68), width=W2(2))
    ell(376, 218, 394, 236, fill=(11, 11, 15), outline=(86, 86, 100), width=W2(2))
    ell(381.5, 223.5, 388.5, 230.5, fill=(61, 69, 104))
    return layer

def soft_shadow(ox, oy, s):
    """Sombra oscura suave bajo el robot (capa RGBA)."""
    layer = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx = (ox + 300 * s) * SS
    cy = (oy + 730 * s) * SS
    rx, ry = 175 * s * SS, 34 * s * SS
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(0, 0, 0, 150))
    return layer.filter(ImageFilter.GaussianBlur(26 * SS))

def glow_background():
    gw, gh = 440, 520
    ys, xs = np.mgrid[0:gh, 0:gw].astype(np.float32)
    xs /= gw; ys /= gh
    acc = np.zeros((gh, gw, 3), np.float32)
    glows = [(0.50, 0.44, 0.52, 0.50, RED, 0.18),
             (0.34, 0.66, 0.46, 0.44, PURPLE, 0.20),
             (0.68, 0.60, 0.44, 0.44, TEAL, 0.12)]
    for cx, cy, rx, ry, col, inten in glows:
        dd = ((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2
        fall = np.clip(1 - dd, 0, 1) ** 1.6
        for i in range(3):
            acc[:, :, i] += fall * (col[i] / 255.0) * inten
    base = np.array(BG, np.float32) / 255.0
    arr = (np.clip(base[None, None, :] + acc, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(arr, 'RGB').resize((CW, CH), Image.BICUBIC)

# Coloca el robot centrado: centro del viewBox (300,390) al centro del lienzo
s = 2.62
ox = W / 2 / 1 - 300 * s
oy = H / 2 / 1 - 396 * s

robot = draw_robot_rgba(ox, oy, s)
shadow = soft_shadow(ox, oy, s)

# 1) sobre fondo NEGRO plano (solo el render)
bg = Image.new('RGBA', (CW, CH), (0, 0, 0, 255))
bg.alpha_composite(robot)
bg.convert('RGB').resize((W, H), Image.LANCZOS).save(os.path.join(OUT, 'render-mech.png'))
print('OK render-mech.png', (W, H))

# 2) transparente (sombra + robot)
trans = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
trans.alpha_composite(shadow)
trans.alpha_composite(robot)
trans.resize((W, H), Image.LANCZOS).save(os.path.join(OUT, 'render-mech-transparent.png'))
print('OK render-mech-transparent.png', (W, H))
