# Banners 16:9 en 4K (3840x2160) con la estética del sitio web de MECH:
# fondo #0e0e12, glows de color, rejilla tenue, franja de píxeles, logo MECH
# (marco skew + itálica) y degradado rojo→morado→teal en el texto enfatizado.
#
# Salidas en branding/:
#   banner-frase.png   ← la frase de la línea 67 (para el mosaico de Instagram)
#   banner-mech.png    ← banner de marca (logo + eslogan)
#   banner-robot.png   ← robot + tagline
#
# Todo se dibuja a 2x y se reduce con LANCZOS para bordes nítidos.

import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SS = 2
W, H = 3840, 2160
CW, CH = W * SS, H * SS

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Paleta del sitio
BG      = (14, 14, 18)
TEXT    = (240, 238, 255)
MUTED   = (155, 155, 173)
DIM     = (106, 106, 124)
RED     = (226, 75, 74)
PURPLE  = (127, 119, 221)
TEAL    = (29, 158, 117)
AMBER   = (239, 159, 39)

_fc = {}
def font(size, weight=400, italic=False):
    key = (size, weight, italic)
    if key not in _fc:
        f = ImageFont.truetype('Sora.ttf', int(size * SS))
        try: f.set_variation_by_axes([weight])
        except Exception: pass
        _fc[key] = f
    return _fc[key]

# ── Fondo con glows radiales (numpy a baja res, luego escalado) ─────────
def make_background():
    gw, gh = 480, 270
    ys, xs = np.mgrid[0:gh, 0:gw].astype(np.float32)
    xs /= gw; ys /= gh
    acc = np.zeros((gh, gw, 3), np.float32)
    # (cx, cy, rx, ry, color, intensidad) — como los radial-gradient del hero
    glows = [
        (0.50, 0.30, 0.55, 0.45, RED,    0.16),
        (0.22, 0.72, 0.50, 0.42, PURPLE, 0.22),
        (0.80, 0.68, 0.46, 0.42, TEAL,   0.12),
        (0.50, 0.50, 0.75, 0.65, PURPLE, 0.05),
    ]
    for cx, cy, rx, ry, col, inten in glows:
        d = ((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2
        falloff = np.clip(1 - d, 0, 1) ** 1.6
        for i in range(3):
            acc[:, :, i] += falloff * (col[i] / 255.0) * inten
    base = np.array(BG, np.float32) / 255.0
    img = np.clip(base[None, None, :] + acc, 0, 1)
    arr = (img * 255).astype(np.uint8)
    glow = Image.fromarray(arr, 'RGB').resize((CW, CH), Image.BICUBIC)
    return glow

def add_grid(img):
    # rejilla tenue con desvanecido radial hacia los bordes (como .hero-grid)
    layer = Image.new('L', (CW, CH), 0)
    d = ImageDraw.Draw(layer)
    step = 150 * SS
    for x in range(0, CW, step):
        d.line([(x, 0), (x, CH)], fill=12, width=SS)
    for y in range(0, CH, step):
        d.line([(0, y), (CW, y)], fill=12, width=SS)
    # máscara radial (visible al centro, se apaga a los bordes)
    my, mx = np.mgrid[0:CH, 0:CW].astype(np.float32)
    mx = (mx / CW - 0.5) / 0.5; my = (my / CH - 0.42) / 0.42
    dd = np.clip(1 - (mx ** 2 + my ** 2), 0, 1) ** 1.4
    mask = Image.fromarray((dd * 255).astype(np.uint8), 'L')
    grid = Image.composite(layer, Image.new('L', (CW, CH), 0), mask)
    tinted = Image.new('RGB', (CW, CH), TEXT)
    img.paste(tinted, (0, 0), grid)
    return img

# ── Franja de píxeles (firma visual) ───────────────────────────────────
def pixel_band(img, y, flip=False, alpha=34):
    d = ImageDraw.Draw(img, 'RGBA')
    band_h = 46 * SS
    tile = 220 * SS
    rects = [(6,8,13),(26,18,9),(44,6,11),(60,22,14),(82,9,9),(97,20,12),
             (116,7,14),(138,19,9),(154,8,11),(172,21,12),(192,9,9),(206,19,10)]
    x0 = 0
    while x0 < CW:
        for rx, ry, rw in rects:
            X = x0 + rx * SS
            Y = y + (band_h - ry * SS if flip else ry * SS)
            d.rectangle([X, Y, X + rw * SS, Y + rw * SS * 0.9],
                        fill=(240, 238, 255, alpha))
        x0 += tile
    return img

# ── Logo MECH (marco skew -8° + "MECH" itálica) ────────────────────────
def draw_logo(img, cx, cy, scale, color=TEXT, stroke=None):
    # viewBox 300x120; rect 264x96 rx22 stroke; texto MECH 56 italic 800
    stroke = stroke if stroke is not None else max(int(9 * scale * SS), 2)
    layer = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rw, rh = 264 * scale * SS, 96 * scale * SS
    x0, y0 = cx - rw / 2, cy - rh / 2
    d.rounded_rectangle([x0, y0, x0 + rw, y0 + rh], radius=22 * scale * SS,
                        outline=color, width=stroke)
    # skew -8° alrededor del centro
    t = math.tan(math.radians(-8))
    layer = layer.transform((CW, CH), Image.AFFINE,
                            (1, t, -t * cy, 0, 1, 0), resample=Image.BICUBIC)
    img.paste(layer, (0, 0), layer)
    # texto MECH con itálica sintética
    tl = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
    td = ImageDraw.Draw(tl)
    f = font(56 * scale, 800)
    td.text((cx, cy), 'MECH', font=f, fill=color, anchor='mm')
    t2 = math.tan(math.radians(12))
    tl = tl.transform((CW, CH), Image.AFFINE,
                      (1, t2, -t2 * cy, 0, 1, 0), resample=Image.BICUBIC)
    img.paste(tl, (0, 0), tl)

# ── Texto con degradado horizontal (rojo→morado→teal) ──────────────────
def gradient_image(w, h, stops):
    grad = np.zeros((1, w, 3), np.float32)
    xs = np.linspace(0, 1, w)
    pts = [s[0] for s in stops]
    cols = [np.array(s[1], np.float32) for s in stops]
    for i in range(w):
        x = xs[i]
        for j in range(len(pts) - 1):
            if pts[j] <= x <= pts[j + 1]:
                f = (x - pts[j]) / (pts[j + 1] - pts[j] + 1e-9)
                grad[0, i] = cols[j] * (1 - f) + cols[j + 1] * f
                break
        else:
            grad[0, i] = cols[-1] if x > pts[-1] else cols[0]
    return Image.fromarray(np.repeat(grad.astype(np.uint8), h, axis=0), 'RGB')

def text_line(d, s, f):
    b = d.textbbox((0, 0), s, font=f)
    return b[2] - b[0], b[3] - b[1], b

def draw_text(img, cx, cy, s, f, fill=TEXT, gradient=None, italic=False):
    layer = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text((cx, cy), s, font=f, fill=(255, 255, 255, 255), anchor='mm')
    if italic:
        t = math.tan(math.radians(11))
        layer = layer.transform((CW, CH), Image.AFFINE,
                                (1, t, -t * cy, 0, 1, 0), resample=Image.BICUBIC)
    alpha = layer.split()[3]
    if gradient is not None:
        bbox = alpha.getbbox()
        grad = gradient_image(bbox[2] - bbox[0], bbox[3] - bbox[1], gradient)
        fillimg = Image.new('RGB', (CW, CH), gradient[0][1])
        fillimg.paste(grad, (bbox[0], bbox[1]))
        img.paste(fillimg, (0, 0), alpha)
    else:
        solid = Image.new('RGB', (CW, CH), fill)
        img.paste(solid, (0, 0), alpha)

def measure(s, f):
    tmp = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    b = tmp.textbbox((0, 0), s, font=f)
    return b[2] - b[0], b[3] - b[1]

GRAD = [(0.0, RED), (0.55, PURPLE), (1.0, TEAL)]

def new_canvas():
    img = make_background()
    add_grid(img)
    pixel_band(img, int(38 * SS))
    pixel_band(img, CH - int(84 * SS), flip=True)
    return img

def save(img, name):
    out = img.resize((W, H), Image.LANCZOS)
    out.save(os.path.join(OUT, name), 'PNG')
    print('OK', name, out.size)

# ═══════════════════════════════════════════════════════════════════════
# 1) BANNER FRASE (línea 67) — para el mosaico
# ═══════════════════════════════════════════════════════════════════════
def banner_frase():
    img = new_canvas()
    cx = CW / 2
    # kicker
    fk = font(30, 600)
    draw_text(img, cx, CH * 0.20, 'WRO 2026 · ROBOTS AND CULTURE · COSTA RICA',
              font(28, 600, ), fill=MUTED)
    # título en dos líneas: línea 1 sólida, línea 2 con degradado itálico
    f1 = font(118, 800)
    draw_text(img, cx, CH * 0.42, 'Despertamos el interés', f1, fill=TEXT)
    f2 = font(118, 800)
    draw_text(img, cx, CH * 0.56, 'en lo que de verdad importa.', f2,
              gradient=GRAD, italic=True)
    # logo pequeño arriba
    draw_logo(img, cx, CH * 0.30, 0.42)
    # eslogan abajo
    draw_text(img, cx, CH * 0.76, '« si es inmersivo, es MECH »',
              font(34, 400), fill=DIM)
    save(img, 'banner-frase.png')

# ═══════════════════════════════════════════════════════════════════════
# 2) BANNER DE MARCA — logo grande + acrónimo + eslogan
# ═══════════════════════════════════════════════════════════════════════
def banner_mech():
    img = new_canvas()
    cx = CW / 2
    draw_logo(img, cx, CH * 0.44, 1.35)
    # acrónimo M·E·C·H con letras de color
    parts = [('M', RED, 'ultisensory'), ('E', PURPLE, 'ngineering'),
             ('C', TEAL, 'yberphysical'), ('H', AMBER, 'umanized')]
    fmono = font(34, 700)
    # medir ancho total
    seps = '   ·   '
    total = 0
    pieces = []
    for i, (L, col, rest) in enumerate(parts):
        w1, _ = measure(L, fmono)
        w2, _ = measure(rest, font(34, 400))
        pieces.append((L, col, rest, w1, w2))
        total += w1 + w2
        if i < 3:
            total += measure(seps, font(34, 400))[0]
    x = cx - total / 2
    y = CH * 0.62
    layer = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    frest = font(34, 400)
    for i, (L, col, rest, w1, w2) in enumerate(pieces):
        d.text((x, y), L, font=fmono, fill=col, anchor='lm'); x += w1
        d.text((x, y), rest, font=frest, fill=MUTED, anchor='lm'); x += w2
        if i < 3:
            d.text((x, y), seps, font=frest, fill=DIM, anchor='lm')
            x += measure(seps, frest)[0]
    img.paste(layer, (0, 0), layer)
    draw_text(img, cx, CH * 0.72, '« si es inmersivo, es MECH »',
              font(38, 400), fill=TEXT)
    draw_text(img, cx, CH * 0.85, 'WRO 2026 · ROBOTS AND CULTURE · COSTA RICA',
              font(26, 600), fill=DIM)
    save(img, 'banner-mech.png')

# ═══════════════════════════════════════════════════════════════════════
# 3) BANNER ROBOT — render del robot + tagline
# ═══════════════════════════════════════════════════════════════════════
def banner_robot():
    from diag_base import draw_robot, Canvas
    img = new_canvas()
    # render del robot a la derecha usando el helper de diag_base sobre un
    # Canvas temporal transparente, luego compuesto.
    rc = Canvas(W, H, bg=BG)  # su propio SS interno (=3)
    # dibujamos el robot y lo recortamos por luminancia sobre nuestro fondo
    s = 1.15
    ox, oy = int(W * 0.60), int(H * 0.16)
    draw_robot(rc, ox, oy, s)
    robot = rc.img.resize((W, H), Image.LANCZOS).convert('RGB')
    robot2x = robot.resize((CW, CH), Image.LANCZOS)
    # máscara: donde el robot difiere del fondo liso
    ra = np.asarray(robot2x, np.int16)
    bg = np.array(BG, np.int16)
    diff = np.abs(ra - bg[None, None, :]).sum(2)
    m = np.clip((diff - 8) * 6, 0, 255).astype(np.uint8)
    mask = Image.fromarray(m, 'L').filter(ImageFilter.GaussianBlur(SS))
    img.paste(robot2x, (0, 0), mask)
    # texto a la izquierda
    lx = int(CW * 0.06)
    draw_text(img, lx + measure('WRO 2026 · COSTA RICA', font(28,600))[0]/2, CH*0.30,
              'WRO 2026 · COSTA RICA', font(28, 600), fill=MUTED)
    # título grande alineado a la izquierda (dibujo por líneas ancladas 'lm')
    def left(s, f, y, **kw):
        w, _ = measure(s, f)
        draw_text(img, lx + w/2, y, s, f, **kw)
    left('El robot que', font(108, 800), CH*0.44, fill=TEXT)
    left('despierta el interés.', font(108, 800), CH*0.57, gradient=GRAD, italic=True)
    left('« si es inmersivo, es MECH »', font(34, 400), CH*0.70, fill=DIM)
    draw_logo(img, lx + 130 * SS, CH*0.83, 0.55)
    save(img, 'banner-robot.png')

if __name__ == '__main__':
    banner_frase()
    banner_mech()
    banner_robot()
