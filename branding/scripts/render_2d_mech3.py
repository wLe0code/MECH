# Render 2D (ilustracion plana) de MECH-3, basado en el render 3D del equipo:
# cuerpo negro, plataforma y brazos blanco-menta, cabeza con cara (ojo grande,
# guino con la webcam, sonrisa), panuelo rojo, botones, logo MECH y la franja
# de la bandera de Costa Rica. FONDO TRANSPARENTE.
# El negro lleva un borde de luz tenue para que no desaparezca sobre fondo negro.
import os, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'stand'))
SS = 3
W, H = 1600, 2050
def S(v): return int(round(v * SS))

BLACK = (12, 12, 16); BLACK2 = (28, 28, 35)
MINT = (226, 238, 236); MINT_D = (178, 200, 197); MINT_L = (244, 250, 249)
WHITE = (238, 238, 242)
RED = (196, 32, 38); RED_D = (120, 16, 22)
NAVY = (22, 30, 92); CR_RED = (206, 38, 44)
RIM = (255, 255, 255, 46)

cv = Image.new('RGBA', (S(W), S(H)), (0, 0, 0, 0))
d = ImageDraw.Draw(cv)

def rect(x0, y0, x1, y1, fill, r=0, outline=None, w=0):
    d.rounded_rectangle([S(x0), S(y0), S(x1), S(y1)], radius=S(r), fill=fill,
                        outline=outline, width=S(w) if w else 0)
def poly(pts, fill):
    d.polygon([(S(x), S(y)) for x, y in pts], fill=fill)
def ell(cx, cy, rx, ry, fill):
    d.ellipse([S(cx - rx), S(cy - ry), S(cx + rx), S(cy + ry)], fill=fill)

# sombra en el suelo
sh = Image.new('RGBA', cv.size, (0, 0, 0, 0))
ImageDraw.Draw(sh).ellipse([S(430), S(1935), S(1230), S(2010)], fill=(0, 0, 0, 110))
cv.alpha_composite(sh.filter(ImageFilter.GaussianBlur(S(22))))

# ruedas
for cx in (620, 1040):
    rect(cx - 95, 1860, cx + 95, 1968, BLACK, r=46, outline=RIM, w=2)

# brazo izquierdo (colgando, mano escalonada)
poly([(392, 740), (340, 740), (340, 1090), (316, 1090), (316, 1300), (392, 1300)], MINT)
poly([(340, 740), (352, 740), (352, 1090), (340, 1090)], MINT_L)
poly([(316, 1090), (330, 1090), (330, 1300), (316, 1300)], MINT_D)

# brazo derecho (saludando: bloque vertical + mano hacia afuera)
poly([(1255, 745), (1318, 745), (1318, 1290), (1255, 1290)], MINT)
poly([(1300, 745), (1318, 745), (1318, 1290), (1300, 1290)], MINT_D)
poly([(1292, 790), (1420, 790), (1420, 1065), (1356, 1065), (1356, 1015), (1292, 1015)], MINT)
poly([(1404, 790), (1420, 790), (1420, 1065), (1404, 1065)], MINT_D)
poly([(1292, 790), (1420, 790), (1420, 802), (1292, 802)], MINT_L)

# cuerpo (degradado vertical sutil)
ys = np.linspace(0, 1, S(1890 - 612))[:, None]
g = (np.array(BLACK2) * (1 - ys) + np.array(BLACK) * ys)
g = np.repeat(g[:, None, :], S(1258 - 386), axis=1).astype(np.uint8)
cv.paste(Image.fromarray(g, 'RGB'), (S(386), S(612)))
d = ImageDraw.Draw(cv)
rect(386, 612, 1258, 1890, None, outline=RIM, w=2)

# franja bandera de Costa Rica (azul, blanco, rojo, blanco, azul)
y = 1800
for h_, col in [(10, NAVY), (14, WHITE), (26, CR_RED), (14, WHITE), (12, NAVY)]:
    rect(386, y, 1258, y + h_, col); y += h_

# plataforma de hombros
poly([(430, 540), (1214, 540), (1270, 612), (374, 612)], MINT)
rect(374, 604, 1270, 622, MINT_D)
poly([(430, 540), (1214, 540), (1226, 556), (418, 556)], MINT_L)

# cuello
rect(676, 426, 986, 575, MINT)
rect(676, 426, 700, 575, MINT_L)

# cabeza
rect(386, 44, 1274, 434, BLACK, r=6, outline=RIM, w=2)
rect(390, 44, 1270, 52, (70, 74, 80))

# ojo grande: anillo blanco con el borde de abajo recto (como en el 3D)
ex, ey = 590, 245
eye = Image.new('L', cv.size, 0)
ed = ImageDraw.Draw(eye)
ed.ellipse([S(ex - 132), S(ey - 124), S(ex + 132), S(ey + 124)], fill=255)
ed.rectangle([S(ex - 140), S(ey + 92), S(ex + 140), S(ey + 130)], fill=0)
ed.ellipse([S(ex - 62), S(ey - 62), S(ex + 54), S(ey + 54)], fill=0)
cv.paste(Image.new('RGBA', cv.size, WHITE + (255,)), (0, 0), eye)
d = ImageDraw.Draw(cv)
# ceja izquierda (media luna inclinada)
cej = Image.new('RGBA', cv.size, (0, 0, 0, 0))
cd = ImageDraw.Draw(cej)
cd.ellipse([S(478), S(84), S(650), S(150)], fill=WHITE)
cd.ellipse([S(486), S(104), S(652), S(166)], fill=(0, 0, 0, 0))
cej = cej.rotate(14, center=(S(564), S(120)), resample=Image.BICUBIC)
m_ = np.array(cej.getchannel('A'))
hole = Image.new('L', cv.size, 0)
ImageDraw.Draw(hole).ellipse([S(486), S(104), S(652), S(166)], fill=255)
hole = np.array(hole.rotate(14, center=(S(564), S(120)), resample=Image.BICUBIC))
cej.putalpha(Image.fromarray(np.clip(m_.astype(int) - hole.astype(int), 0, 255).astype(np.uint8)))
cv.alpha_composite(cej)
d = ImageDraw.Draw(cv)
# ceja derecha (guino)
d.chord([S(1005), S(98), S(1172), S(160)], start=180, end=360, fill=WHITE)
ell(1088, 131, 84, 9, BLACK)
# webcam
rect(986, 170, 1202, 268, (20, 20, 24), r=22, outline=(90, 90, 100), w=3)
rect(996, 180, 1192, 258, (8, 8, 10), r=16)
ell(1092, 219, 34, 34, (40, 40, 46)); ell(1092, 219, 22, 22, (10, 12, 18))
ell(1084, 212, 6, 6, (120, 130, 170))
fm = ImageFont.truetype('Sora.ttf', S(15)); fm.set_variation_by_axes([600])
d.text((S(1162), S(219)), 'logitech', font=fm, fill=(210, 210, 220), anchor='mm')
# sonrisa
d.chord([S(772), S(292), S(892), S(408)], start=0, end=180, fill=WHITE)

# panuelo rojo con estampado
band = Image.new('RGBA', cv.size, (0, 0, 0, 0))
bd = ImageDraw.Draw(band)
left = [(612, 616), (736, 616), (784, 690), (604, 930), (566, 920)]
right = [(896, 616), (1022, 616), (1068, 920), (1030, 930), (846, 690)]
knot = [(736, 616), (896, 616), (846, 690), (784, 690)]
for pts in (left, right, knot):
    bd.polygon([(S(x), S(y)) for x, y in pts], fill=RED)
m = np.array(band.getchannel('A'))
pat = Image.new('RGBA', cv.size, (0, 0, 0, 0))
pd = ImageDraw.Draw(pat)
random.seed(7)
for _ in range(260):
    x, y = random.uniform(560, 1075), random.uniform(612, 935)
    r = random.choice([4, 5, 7, 9])
    if random.random() < .55:
        pd.ellipse([S(x - r), S(y - r), S(x + r), S(y + r)], outline=(255, 214, 214, 150), width=S(2))
    else:
        a0 = random.uniform(0, 360)
        pd.arc([S(x - r * 2), S(y - r * 2), S(x + r * 2), S(y + r * 2)],
               start=a0, end=a0 + 150, fill=(255, 214, 214, 120), width=S(2))
pat.putalpha(Image.fromarray(np.minimum(np.array(pat.getchannel('A')), m)))
band.alpha_composite(pat)
edge_a = Image.fromarray(((m > 0) * 255).astype(np.uint8)).filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(S(3)))
edge = Image.new('RGBA', cv.size, RED_D + (0,))
edge.putalpha(edge_a)
band.alpha_composite(edge)
cv.alpha_composite(band)
d = ImageDraw.Draw(cv)

# botones
ell(835, 712, 30, 30, WHITE)
ell(835, 797, 30, 30, WHITE)

# logo MECH (marco inclinado + texto en italica sintetica)
lx, ly, lw, lh = 975, 1692, 258, 90
cy0 = S(ly + lh / 2)
logo = Image.new('RGBA', cv.size, (0, 0, 0, 0))
ImageDraw.Draw(logo).rounded_rectangle([S(lx), S(ly), S(lx + lw), S(ly + lh)],
                                       radius=S(24), outline=WHITE, width=S(8))
t = math.tan(math.radians(-8))
cv.alpha_composite(logo.transform(logo.size, Image.AFFINE, (1, t, -t * cy0, 0, 1, 0), resample=Image.BICUBIC))
tl = Image.new('RGBA', cv.size, (0, 0, 0, 0))
fl = ImageFont.truetype('Sora.ttf', S(52)); fl.set_variation_by_axes([800])
ImageDraw.Draw(tl).text((S(lx + lw / 2), S(ly + lh / 2 + 2)), 'MECH', font=fl, fill=WHITE, anchor='mm')
t2 = math.tan(math.radians(12))
cv.alpha_composite(tl.transform(tl.size, Image.AFFINE, (1, t2, -t2 * cy0, 0, 1, 0), resample=Image.BICUBIC))

out = cv.resize((W, H), Image.LANCZOS)
out = out.crop(out.getbbox())
p = os.path.join(OUT, 'render-2d-mech3.png')
out.save(p, 'PNG', optimize=True)
print('render-2d-mech3.png', out.size)
