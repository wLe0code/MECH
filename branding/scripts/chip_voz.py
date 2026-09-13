# Chip de voz del sitio (aro LED + prompt + texto + cursor) en alta resolucion,
# con FONDO TRANSPARENTE fuera de la pastilla. Replica .voice-chip de la web.
#
# Salida: branding/stand/voz-wake-up-mech.png  (y voz-ok-mech.png)

import math, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'stand'))
S = 16            # escala respecto a los px CSS del sitio
SS = 2            # supersampling
K = S * SS

SURFACE = (22, 22, 29)
BORDER = (255, 255, 255, 30)
TEXT = (240, 238, 255)
RED = (226, 75, 74)
TEAL = (29, 158, 117)

def chip(texto, nombre):
    f = ImageFont.truetype('SpaceMono-Regular.ttf', int(15 * K))
    tmp = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    w_prompt = tmp.textlength('› ', font=f) / K
    w_txt = tmp.textlength(texto, font=f) / K
    # medidas CSS del .voice-chip
    pad_l, pad_r, ring, gap = 13, 30, 42, 16
    caret_w, caret_h, caret_gap = 9, 17, 3
    h = 64
    w = pad_l + ring + gap + w_prompt + w_txt + caret_gap + caret_w + pad_r
    m = 34                                   # margen para el glow
    cw, ch = int((w + 2 * m) * K), int((h + 2 * m) * K)
    cv = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    x0, y0, x1, y1 = m * K, m * K, (m + w) * K, (m + h) * K

    # glow rojo muy tenue (box-shadow 0 0 40px rgba(226,75,74,.08))
    g = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    ImageDraw.Draw(g).rounded_rectangle([x0, y0, x1, y1], radius=h / 2 * K,
                                        fill=RED + (60,))
    cv.alpha_composite(g.filter(ImageFilter.GaussianBlur(18 * K)))

    d = ImageDraw.Draw(cv)
    d.rounded_rectangle([x0, y0, x1, y1], radius=h / 2 * K, fill=SURFACE + (255,))
    d.rounded_rectangle([x0, y0, x1, y1], radius=h / 2 * K, outline=BORDER,
                        width=max(1, int(1.2 * K)))

    # aro LED: 12 puntos, cometa congelado (cabeza brillante + estela)
    cx, cy = x0 + (pad_l + ring / 2) * K, y0 + h / 2 * K
    head = 1                                  # posicion de la cabeza
    estela = [1.0, 0.72, 0.52, 0.38, 0.30]
    leds = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    glow = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    dl, dg = ImageDraw.Draw(leds), ImageDraw.Draw(glow)
    for i in range(12):
        ang = math.radians(i * 30 - 90)
        px, py = cx + 17 * K * math.cos(ang), cy + 17 * K * math.sin(ang)
        atras = (head - i) % 12
        a = estela[atras] if atras < len(estela) else 0.25
        r = 2.5 * K
        dl.ellipse([px - r, py - r, px + r, py + r], fill=TEAL + (int(255 * a),))
        if atras == 0:
            rg = 6 * K
            dg.ellipse([px - rg, py - rg, px + rg, py + rg], fill=TEAL + (200,))
    cv.alpha_composite(glow.filter(ImageFilter.GaussianBlur(4 * K)))
    cv.alpha_composite(leds)

    # prompt + texto + cursor
    tx = x0 + (pad_l + ring + gap) * K
    ty = cy
    d.text((tx, ty), '›', font=ImageFont.truetype('SpaceMono-Bold.ttf', int(15 * K)),
           fill=RED, anchor='lm')
    tx += w_prompt * K
    d.text((tx, ty), texto, font=f, fill=TEXT, anchor='lm')
    tx += (w_txt + caret_gap) * K
    d.rectangle([tx, cy - caret_h / 2 * K, tx + caret_w * K, cy + caret_h / 2 * K],
                fill=TEXT)

    out = cv.resize((cw // SS, ch // SS), Image.LANCZOS)
    out = out.crop(out.getbbox())
    p = os.path.join(OUT, nombre)
    out.save(p, 'PNG', optimize=True)
    print(f'{nombre:24s} {out.size[0]}x{out.size[1]}')

chip('«wake up MECH»', 'voz-wake-up-mech.png')
chip('«ok MECH»', 'voz-ok-mech.png')
