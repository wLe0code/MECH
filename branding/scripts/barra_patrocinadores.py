# Barra de patrocinadores para el STAND: misma estetica que la marquesina de
# la web (pastilla clara, logos en fila, bordes que se desvanecen), pero en
# alta resolucion y con FONDO TRANSPARENTE fuera de la barra.
#
# Salida: branding/stand/
#   patrocinadores-azul.png    ← fondo claro azulado + glow tenue (recomendada)
#   patrocinadores-blanco.png  ← fondo claro neutro, igual que la web
#   patrocinadores-azul-sin-fade.png ← pastilla completa, sin desvanecer bordes

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'patrocinadores'))
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'stand'))
os.makedirs(OUT, exist_ok=True)

# mismo orden que en la web
ORDEN = ['CCAL.png', 'Admisión CR.png', 'Team Steam.jpeg',
         '360 Health & Value.png', 'Sr y Sra Ese.jpg', 'Luvá.png']

SS = 2
W, H = 6000, 600          # barra (sin el margen del glow)
PAD = 90                  # margen transparente alrededor (para el glow)
LOGO_H = 390
GAP = 300
FADE = 0.075              # fraccion del ancho que se desvanece en cada borde
SENTINEL = (255, 0, 254)

def cargar_logo(nombre):
    """Quita el fondo blanco SOLO desde los bordes (flood fill: no perfora
    los blancos interiores) y recorta al contenido. Resolucion nativa."""
    im = Image.open(os.path.join(SRC, nombre))
    rgba = None
    if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
        rgba = im.convert('RGBA')
        if rgba.getchannel('A').getextrema()[0] == 255:
            rgba = None
    if rgba is None:
        rgb = im.convert('RGB')
        w, h = rgb.size
        for c in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
            if sum(rgb.getpixel(c)) / 3 > 200:
                ImageDraw.floodfill(rgb, c, SENTINEL, thresh=42)
        a = np.array(rgb)
        mask = np.all(a == SENTINEL, axis=2)
        alpha = np.where(mask, 0, 255).astype(np.uint8)
        a[mask] = 255
        rgba = Image.fromarray(np.dstack([a, alpha]), 'RGBA')
    bb = rgba.getbbox()
    return rgba.crop(bb) if bb else rgba

def escalar(im, h):
    return im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)

def construir(nombre, fondo, borde, glow=None, fade=True, fondo2=None):
    cw, ch = (W + 2 * PAD) * SS, (H + 2 * PAD) * SS
    cv = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    x0, y0, x1, y1 = PAD * SS, PAD * SS, (PAD + W) * SS, (PAD + H) * SS
    radio = int(H * 0.30 * SS)

    # glow exterior tenue (se funde con el negro del stand)
    if glow:
        g = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
        ImageDraw.Draw(g).rounded_rectangle([x0, y0, x1, y1], radius=radio,
                                            fill=glow + (120,))
        g = g.filter(ImageFilter.GaussianBlur(34 * SS))
        cv.alpha_composite(g)

    # la pastilla (con degradado vertical muy suave si hay fondo2)
    bar = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    if fondo2:
        ys = np.linspace(0, 1, y1 - y0)[:, None]
        c1, c2 = np.array(fondo, np.float32), np.array(fondo2, np.float32)
        grad = (c1 * (1 - ys[..., None]) + c2 * ys[..., None]).astype(np.uint8)
        grad = np.repeat(grad, x1 - x0, axis=1)
        tile = Image.fromarray(grad, 'RGB').convert('RGBA')
        mask = Image.new('L', (cw, ch), 0)
        ImageDraw.Draw(mask).rounded_rectangle([x0, y0, x1, y1], radius=radio, fill=255)
        full = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
        full.paste(tile, (x0, y0))
        full.putalpha(mask)
        bar.alpha_composite(full)
    else:
        ImageDraw.Draw(bar).rounded_rectangle([x0, y0, x1, y1], radius=radio,
                                              fill=fondo + (255,))
    ImageDraw.Draw(bar).rounded_rectangle([x0, y0, x1, y1], radius=radio,
                                          outline=borde + (255,), width=3 * SS)
    cv.alpha_composite(bar)

    # logos: los 6 UNA sola vez, repartidos con el mismo aire entre todos
    # ("space-around") y fuera de la franja que se desvanece. En una pieza
    # impresa, repetir logos o dejarlos cortados en el borde parece un error.
    logos = [escalar(L, LOGO_H * SS) for L in LOGOS]
    borde_seguro = int(W * SS * (FADE + 0.01)) if fade else int(H * 0.28 * SS)
    ini, fin = x0 + borde_seguro, x1 - borde_seguro
    libre = (fin - ini) - sum(L.width for L in logos)
    hueco = libre / len(logos)
    ly = y0 + ((y1 - y0) - LOGO_H * SS) // 2
    capa = Image.new('RGBA', (cw, ch), (0, 0, 0, 0))
    x = ini + hueco / 2
    for L in logos:
        capa.alpha_composite(L, (int(x), ly))
        x += L.width + hueco
    # recortar los logos a la forma de la pastilla
    forma = Image.new('L', (cw, ch), 0)
    ImageDraw.Draw(forma).rounded_rectangle([x0 + 6 * SS, y0, x1 - 6 * SS, y1],
                                            radius=radio, fill=255)
    capa.putalpha(Image.fromarray(np.minimum(np.array(capa.getchannel('A')),
                                             np.array(forma))))
    cv.alpha_composite(capa)

    # desvanecer los extremos (la mascara de la web)
    if fade:
        xs = np.arange(cw, dtype=np.float32)
        a0, b0 = x0, x0 + W * SS * FADE
        a1, b1 = x1 - W * SS * FADE, x1
        ramp = np.clip(np.minimum((xs - a0 + PAD * SS * 0.6) / (b0 - a0 + PAD * SS * 0.6),
                                  (b1 + PAD * SS * 0.6 - xs) / (b1 - a1 + PAD * SS * 0.6)), 0, 1)
        ramp = ramp ** 1.4
        A = np.array(cv.getchannel('A')).astype(np.float32) * ramp[None, :]
        cv.putalpha(Image.fromarray(A.astype(np.uint8)))

    out = cv.resize((cw // SS, ch // SS), Image.LANCZOS)
    bb = out.getbbox()
    out = out.crop(bb)
    p = os.path.join(OUT, nombre)
    out.save(p, 'PNG', optimize=True)
    print(f'{nombre:34s} {out.size[0]}x{out.size[1]}  {os.path.getsize(p)//1024} KB')

LOGOS = [cargar_logo(n) for n in ORDEN]
for n, L in zip(ORDEN, LOGOS):
    print(f'  {n:24s} nativo {L.size}')

AZUL1, AZUL2 = (236, 240, 252), (218, 225, 245)   # claro azulado, degradado sutil
construir('patrocinadores-azul.png', AZUL1, (170, 182, 228),
          glow=(99, 110, 214), fondo2=AZUL2)
construir('patrocinadores-blanco.png', (238, 237, 243), (205, 204, 214))
construir('patrocinadores-azul-sin-fade.png', AZUL1, (170, 182, 228),
          glow=(99, 110, 214), fondo2=AZUL2, fade=False)
