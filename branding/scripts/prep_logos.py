# Prepara los logos de patrocinadores para la barra transportadora de la web.
# - Quita el fondo blanco SOLO desde los bordes (flood fill), así no perfora
#   los blancos interiores del logo.
# - Recorta el margen sobrante y normaliza la altura.
# Salida: web/assets/logos/*.png

import os, glob
from PIL import Image, ImageDraw

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'patrocinadores'))
DST = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..',
                                  'web', 'assets', 'logos'))
os.makedirs(DST, exist_ok=True)

H = 220          # altura normalizada (se muestra a ~44px → 5x para retina)
SENTINEL = (255, 0, 254)

# nombre de archivo destino por logo
NAMES = {
    '360 Health & Value': '360-health-value',
    'Admisión CR': 'admision-cr',
    'CCAL': 'ccal',
    'Luvá': 'steam-luva',
    'Sr y Sra Ese': 'sr-y-sra-ese',
    'Team Steam': 'team-steam',
}

for path in sorted(glob.glob(os.path.join(SRC, '*'))):
    base = os.path.splitext(os.path.basename(path))[0]
    im = Image.open(path)

    # si ya trae alfa, la respetamos; si no, quitamos el blanco del borde
    if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
        rgba = im.convert('RGBA')
        if rgba.getchannel('A').getextrema()[0] == 255:   # alfa opaca => tratar como sin alfa
            rgba = None
    else:
        rgba = None

    if rgba is None:
        rgb = im.convert('RGB')
        w, h = rgb.size
        d = ImageDraw.Draw(rgb)
        for corner in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
            px = rgb.getpixel(corner)
            if sum(px) / 3 > 200:            # solo si la esquina es clara
                ImageDraw.floodfill(rgb, corner, SENTINEL, thresh=42)
        rgba = rgb.convert('RGBA')
        px = rgba.load()
        for y in range(h):
            for x in range(w):
                if px[x, y][:3] == SENTINEL:
                    px[x, y] = (255, 255, 255, 0)

    bbox = rgba.getbbox()
    if bbox:
        rgba = rgba.crop(bbox)
    ratio = H / rgba.height
    rgba = rgba.resize((max(int(rgba.width * ratio), 1), H), Image.LANCZOS)

    out = os.path.join(DST, NAMES.get(base, base.lower().replace(' ', '-')) + '.png')
    rgba.save(out, 'PNG', optimize=True)
    print(f'{base:22s} -> {os.path.basename(out):22s} {rgba.size}')
