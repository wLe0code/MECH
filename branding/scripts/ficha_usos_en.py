# Ficha de usos EN INGLES (distinta de ficha_usos.py): lista editorial numerada,
# un uso por fila con numero grande en contorno, icono de linea y descripcion.
# Sin MECH al centro. Fondo negro del stand. -> branding/stand/ficha-usos-en.png
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'stand', 'ficha-usos-en.png')
W, H = 2400, 3000
BG = (8, 8, 11); TEXT = (240, 238, 255); MUTED = (155, 155, 173); DIM = (106, 106, 124)
RED = (226, 75, 74); PUR = (83, 74, 183); PURM = (127, 119, 221); AMB = (239, 159, 39); TEAL = (29, 158, 117)

def sora(size, wt):
    f = ImageFont.truetype(os.path.join(HERE, 'Sora.ttf'), size); f.set_variation_by_axes([wt]); return f
def mono(size, bold=True):
    return ImageFont.truetype(os.path.join(HERE, 'SpaceMono-Bold.ttf' if bold else 'SpaceMono-Regular.ttf'), size)

img = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(img)

def grad_text(xy, txt, font, stops, anchor='la'):
    m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).text(xy, txt, font=font, fill=255, anchor=anchor)
    box = m.getbbox()
    if not box: return
    x0, x1 = box[0], box[2]
    t = np.clip((np.arange(W) - x0) / max(1, x1 - x0), 0, 1)
    cols = np.zeros((W, 3))
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]; p1, c1 = stops[i + 1]
        sel = (t >= p0) & (t <= p1)
        k = ((t[sel] - p0) / (p1 - p0))[:, None]
        cols[sel] = np.array(c0) * (1 - k) + np.array(c1) * k
    layer = Image.fromarray(np.repeat(cols[None], H, axis=0).astype(np.uint8), 'RGB')
    img.paste(layer, (0, 0), m)

STOPS = [(0, RED), (.58, PURM), (1, TEAL)]
L = 200; R = W - 200

# halo tenue arriba a la derecha
glow = Image.new('RGB', (W, H), (0, 0, 0))
ImageDraw.Draw(glow).ellipse([1500, -500, 2900, 700], fill=(40, 30, 90))
img = Image.fromarray(np.clip(np.array(img, int) + np.array(glow.filter(ImageFilter.GaussianBlur(260)), int), 0, 255).astype(np.uint8))
d = ImageDraw.Draw(img)

# cabecera
d.text((L, 230), 'WHERE MECH WORKS', font=mono(40), fill=PURM)
d.text((R, 230), 'USE CASES · 2026', font=mono(40, False), fill=DIM, anchor='ra')
d.text((L, 340), 'Built for any room', font=sora(128, 700), fill=TEXT)
grad_text((L, 490), 'where attention matters.', sora(128, 700), STOPS)
d.text((L, 690), 'Voice, immersive projection and movement in one robot — the same', font=sora(46, 400), fill=MUTED)
d.text((L, 755), 'technology adapts to every audience that needs to be reached.', font=sora(46, 400), fill=MUTED)

# iconos de linea (en caja de 110 px centrada en cx, cy)
def icon(kind, cx, cy, col):
    w = 7
    if kind == 'class':
        d.rounded_rectangle([cx - 50, cy - 38, cx + 50, cy + 26], 8, outline=col, width=w)
        d.line([cx - 30, cy + 26, cx - 42, cy + 50], fill=col, width=w)
        d.line([cx + 30, cy + 26, cx + 42, cy + 50], fill=col, width=w)
        d.line([cx - 28, cy - 12, cx + 10, cy - 12], fill=col, width=w)
        d.line([cx - 28, cy + 4, cx + 26, cy + 4], fill=col, width=w)
    elif kind == 'museum':
        d.polygon([(cx - 56, cy - 22), (cx, cy - 54), (cx + 56, cy - 22)], outline=col, width=w)
        for x in (-34, -11, 12, 35):
            d.line([cx + x, cy - 12, cx + x, cy + 34], fill=col, width=w)
        d.line([cx - 58, cy + 46, cx + 58, cy + 46], fill=col, width=w)
    elif kind == 'health':
        d.rounded_rectangle([cx - 50, cy - 50, cx + 50, cy + 50], 22, outline=col, width=w)
        d.line([cx, cy - 26, cx, cy + 26], fill=col, width=w + 3)
        d.line([cx - 26, cy, cx + 26, cy], fill=col, width=w + 3)
    elif kind == 'launch':
        d.polygon([(cx, cy - 58), (cx + 24, cy - 16), (cx + 24, cy + 28), (cx - 24, cy + 28), (cx - 24, cy - 16)], outline=col, width=w)
        d.ellipse([cx - 9, cy - 16, cx + 9, cy + 2], outline=col, width=5)
        d.polygon([(cx - 24, cy + 4), (cx - 46, cy + 36), (cx - 24, cy + 28)], outline=col, width=w)
        d.polygon([(cx + 24, cy + 4), (cx + 46, cy + 36), (cx + 24, cy + 28)], outline=col, width=w)
        d.line([cx, cy + 38, cx, cy + 58], fill=col, width=w)
    elif kind == 'device':
        pts = [(cx - 58, cy + 4), (cx - 26, cy + 4), (cx - 12, cy - 36), (cx + 6, cy + 42), (cx + 20, cy + 4), (cx + 58, cy + 4)]
        d.line(pts, fill=col, width=w, joint='curve')
        d.rounded_rectangle([cx - 58, cy - 54, cx + 58, cy + 54], 16, outline=col, width=5)
    elif kind == 'art':
        d.line([cx - 16, cy + 30, cx - 16, cy - 44], fill=col, width=w)
        d.line([cx + 34, cy + 16, cx + 34, cy - 56], fill=col, width=w)
        d.line([cx - 16, cy - 44, cx + 34, cy - 56], fill=col, width=w + 4)
        d.ellipse([cx - 46, cy + 16, cx - 12, cy + 44], fill=col)
        d.ellipse([cx + 4, cy + 2, cx + 38, cy + 30], fill=col)

ROWS = [
    ('class', RED, 'Classrooms', 'A tireless teaching assistant for single-teacher schools —', 'eight hours of battery, a full school day.'),
    ('museum', AMB, 'Museums & culture', 'Turns exhibits into stories visitors can ask questions to,', 'in Spanish or English.'),
    ('health', TEAL, 'Healthcare & pharma', 'Explains treatments and prevention in waiting rooms and', 'events, with our partner 360 Health & Value.'),
    ('launch', PURM, 'Tech launches', 'A presenter that draws the crowd, demos the product', 'and answers on the spot.'),
    ('device', RED, 'Medical devices', 'Shows how a device works with projection instead of', 'a manual nobody reads.'),
    ('art', AMB, 'Independent artists', 'Narrates and projects a creator’s work, giving small', 'artists a stage that speaks for them.'),
]

y0, rowh = 900, 262
nfont = mono(150)
for i, (kind, col, title, l1, l2) in enumerate(ROWS):
    y = y0 + i * rowh
    d.line([L, y, R, y], fill=(38, 38, 48), width=2)
    cy = y + rowh // 2
    # numero en contorno
    d.text((L, cy), f'{i + 1:02d}', font=nfont, fill=BG, anchor='lm', stroke_width=3, stroke_fill=col)
    # icono en circulo fino con glow
    icx = L + 440
    g = Image.new('RGB', (W, H), (0, 0, 0))
    ImageDraw.Draw(g).ellipse([icx - 92, cy - 92, icx + 92, cy + 92], outline=col, width=10)
    g = g.filter(ImageFilter.GaussianBlur(18))
    img = Image.fromarray(np.clip(np.array(img, int) + (np.array(g, int) * .5).astype(int), 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    d.ellipse([icx - 90, cy - 90, icx + 90, cy + 90], outline=tuple(int(c * .75) for c in col), width=3)
    icon(kind, icx, cy, col)
    tx = L + 600
    d.text((tx, cy - 58), title, font=sora(70, 700), fill=TEXT, anchor='ls')
    d.text((tx, cy + 12), l1, font=sora(40, 400), fill=MUTED, anchor='ls')
    d.text((tx, cy + 66), l2, font=sora(40, 400), fill=MUTED, anchor='ls')
d.line([L, y0 + 6 * rowh, R, y0 + 6 * rowh], fill=(38, 38, 48), width=2)

# pie: dato + eslogan
fy = y0 + 6 * rowh + 95
grad_text((L, fy), '+40%', sora(150, 800), STOPS)
d.text((L + 480, fy + 40), 'interest retention when content is delivered', font=sora(44, 500), fill=TEXT)
d.text((L + 480, fy + 102), 'by a humanoid robot — Fuentes-Moraleda et al., 2021', font=sora(38, 400), fill=DIM)
d.text((W // 2, H - 120), '« if it’s immersive, it’s MECH »', font=mono(46), fill=PURM, anchor='mm')

img.save(OUT, 'PNG', optimize=True)
print('ok', OUT)
