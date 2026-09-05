# Prepara los retratos del equipo con la estética de la plantilla de perfil:
# recorte a cabeza+torso centrado en el rostro, desaturado, oscurecido y con
# viñeta radial que funde el fondo a negro.
#
# Salida: web/assets/equipo/{leo,ale,jimmy}.jpg  (1200x1200)
#         web/assets/equipo/grupo.jpg            (foto grupal, 1600x1067)

import os
import numpy as np
import cv2
from PIL import Image, ImageOps, ImageEnhance

SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'equipo'))
DST = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..',
                                   'web', 'assets', 'equipo'))
os.makedirs(DST, exist_ok=True)

OUT = 1200            # lado del retrato cuadrado
CASCADE = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# foto elegida por persona
PICKS = {
    'leo':   os.path.join(SRC, 'Leo',   'IMG_0336.jpg'),
    'ale':   os.path.join(SRC, 'Ale',   'IMG_0318.jpg'),
    'jimmy': os.path.join(SRC, 'Jimmy', 'IMG_0327.jpg'),
}


def find_face(pil_img):
    """Devuelve (cx, cy, w) del rostro más grande, o None."""
    arr = np.array(pil_img.convert('RGB'))
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    # escala reducida para acelerar
    scale = 900 / max(gray.shape)
    small = cv2.resize(gray, None, fx=scale, fy=scale)
    faces = CASCADE.detectMultiScale(small, 1.1, 6, minSize=(40, 40))
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    return (int((x + w / 2) / scale), int((y + h / 2) / scale), int(w / scale))


def vignette(pil_img, strength=1.0):
    """Funde los bordes a negro con una viñeta radial suave."""
    w, h = pil_img.size
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    nx = (xs / w - 0.5) / 0.5
    ny = (ys / h - 0.46) / 0.5
    d = np.sqrt(nx ** 2 + ny ** 2)
    # 1 en el centro, 0 pasado el radio
    mask = np.clip(1.15 - d * 1.02, 0, 1) ** (1.5 * strength)
    arr = np.array(pil_img).astype(np.float32)
    arr *= mask[:, :, None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def portrait(path, out_name):
    im = ImageOps.exif_transpose(Image.open(path)).convert('RGB')
    W, H = im.size
    face = find_face(im)
    if face:
        cx, cy, fw = face
        # encuadre: el rostro ocupa ~26% del alto → cabeza y torso
        side = int(fw / 0.26)
        top = int(cy - side * 0.30)      # deja aire sobre la cabeza
    else:                                 # respaldo si no detecta
        side = int(W * 0.85)
        cx, top = W // 2, int(H * 0.24)
    left = int(cx - side / 2)
    # mantener el recorte dentro de la imagen
    left = max(0, min(left, W - side)) if side <= W else 0
    top = max(0, min(top, H - side)) if side <= H else 0
    side = min(side, W, H)
    im = im.crop((left, top, left + side, top + side)).resize((OUT, OUT), Image.LANCZOS)

    im = ImageEnhance.Color(im).enhance(0.45)       # casi monocromo
    im = ImageEnhance.Brightness(im).enhance(0.80)  # más oscuro
    im = ImageEnhance.Contrast(im).enhance(1.18)
    im = vignette(im)
    im.save(os.path.join(DST, out_name), 'JPEG', quality=88, optimize=True)
    print(f'{out_name:12s} rostro={"sí" if face else "no"}  {im.size}')


for name, path in PICKS.items():
    portrait(path, f'{name}.jpg')

# ── Foto grupal ────────────────────────────────────────────────────────
g = ImageOps.exif_transpose(Image.open(os.path.join(SRC, 'IMG_0302.jpg'))).convert('RGB')
gw, gh = g.size
# recorte apaisado centrado en las personas (tercio central vertical)
ch = int(gw * 0.62)
top = int(gh * 0.30)
g = g.crop((0, top, gw, min(top + ch, gh)))
g.thumbnail((1600, 1600), Image.LANCZOS)
g = ImageEnhance.Color(g).enhance(0.55)
g = ImageEnhance.Brightness(g).enhance(0.86)
g.save(os.path.join(DST, 'grupo.jpg'), 'JPEG', quality=86, optimize=True)
print('grupo.jpg   ', g.size)
