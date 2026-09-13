# Ficha de usos EN INGLES, version simple: titulo corto y seis usos en dos
# columnas (punto de color + nombre + una linea). Mucho aire, sin iconos ni
# numeros. Sin MECH al centro. Fondo negro del stand. -> branding/stand/ficha-usos-en.png
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'stand', 'ficha-usos-en.png')
W, H = 2400, 3000
BG = (8, 8, 11); TEXT = (240, 238, 255); MUTED = (155, 155, 173); DIM = (90, 90, 106)
RED = (226, 75, 74); PURM = (127, 119, 221); AMB = (239, 159, 39); TEAL = (29, 158, 117)

def sora(size, wt):
    f = ImageFont.truetype(os.path.join(HERE, 'Sora.ttf'), size); f.set_variation_by_axes([wt]); return f
def mono(size):
    return ImageFont.truetype(os.path.join(HERE, 'SpaceMono-Bold.ttf'), size)

img = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(img)

def grad_text(xy, txt, font, stops):
    m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).text(xy, txt, font=font, fill=255)
    x0, _, x1, _ = m.getbbox()
    t = np.clip((np.arange(W) - x0) / (x1 - x0), 0, 1)
    cols = np.zeros((W, 3))
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        sel = (t >= p0) & (t <= p1)
        k = ((t[sel] - p0) / (p1 - p0))[:, None]
        cols[sel] = np.array(c0) * (1 - k) + np.array(c1) * k
    img.paste(Image.fromarray(np.repeat(cols[None], H, 0).astype(np.uint8)), (0, 0), m)

L = 260

d.text((L, 330), 'USE CASES', font=mono(42), fill=PURM)
d.text((L, 440), 'One robot.', font=sora(170, 700), fill=TEXT)
grad_text((L, 640), 'Many rooms.', sora(170, 700), [(0, RED), (.58, PURM), (1, TEAL)])

USES = [
    (RED, 'Classrooms', 'A teaching assistant for\nsingle-teacher schools.'),
    (AMB, 'Museums', 'Exhibits that answer\nvisitors’ questions.'),
    (TEAL, 'Healthcare', 'Clear explanations in\nwaiting rooms.'),
    (PURM, 'Tech launches', 'A presenter that\ndraws the crowd.'),
    (RED, 'Medical devices', 'Demos instead of\nmanuals.'),
    (AMB, 'Artists', 'A stage that speaks\nfor their work.'),
]

top, colw, rowh = 1150, 1000, 480
for i, (col, title, desc) in enumerate(USES):
    x = L + (i % 2) * colw
    y = top + (i // 2) * rowh
    d.ellipse([x, y + 30, x + 26, y + 56], fill=col)
    d.text((x + 56, y), title, font=sora(76, 700), fill=TEXT)
    d.multiline_text((x + 56, y + 120), desc, font=sora(46, 400), fill=MUTED, spacing=18)

d.line([L, H - 400, W - L, H - 400], fill=(34, 34, 44), width=2)
d.text((L, H - 300), '« if it’s immersive, it’s MECH »', font=mono(44), fill=DIM)

img.save(OUT, 'PNG', optimize=True)
print('ok')
