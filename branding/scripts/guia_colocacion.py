# Guia visual: como queda la columna derecha del stand con los assets nuevos.
import os
from PIL import Image, ImageDraw, ImageFont

S = os.path.abspath(os.path.join('..', 'stand'))
B = os.path.abspath('..')
W, H = 1000, 2080
BG = (0, 0, 0)
TEXT = (240, 238, 255); MUTED = (155, 155, 173); DIM = (106, 106, 124)
RED=(226,75,74); PURPLE=(127,119,221); TEAL=(29,158,117); AMBER=(239,159,39)

cv = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(cv, 'RGBA')

def sora(sz, w=800):
    f = ImageFont.truetype('Sora.ttf', sz)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
def mono(sz, bold=True):
    return ImageFont.truetype('SpaceMono-Bold.ttf' if bold else 'SpaceMono-Regular.ttf', sz)

def place(name, y, width=None, cx=W//2):
    im = Image.open(os.path.join(S, name)).convert('RGBA')
    w = width or int(W * 0.9)
    im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    cv.paste(im, (cx - w//2, y), im)
    return y + im.height

# ── Tarjetas M E C H (aproximacion de lo que ya tienes) ────────────────
cards = [('M','Multisensory',RED), ('E','Engineering',PURPLE),
         ('C','Cyberphysical',TEAL), ('H','Humanized',AMBER)]
cw, gap, ch = 214, 16, 200
x0 = (W - (cw*4 + gap*3)) // 2
for i,(L,lab,col) in enumerate(cards):
    x = x0 + i*(cw+gap); y = 60
    d.rounded_rectangle([x, y, x+cw, y+ch], radius=22,
                        fill=(22,22,29,255), outline=col+(90,), width=2)
    d.text((x+cw//2, y+78), L, font=sora(76,800), fill=col, anchor='mm')
    d.text((x+cw//2, y+150), lab, font=mono(19), fill=col+(210,), anchor='mm')

d.text((W//2, 330), '<< If it\u2019s immersive, it is MECH. >>',
       font=mono(25), fill=TEXT, anchor='mm')

# ── AQUI van los assets nuevos ─────────────────────────────────────────
y = place('frase-en.png', 400, width=int(W*0.94))
y = place('divisor.png', y + 46, width=int(W*0.86))
y = place('datos-en.png', y + 44, width=int(W*0.92))

# ── Robot (el render que ya existe) ────────────────────────────────────
rb = Image.open(os.path.join(B, 'render-mech-transparent.png')).convert('RGBA')
rw = int(W*0.72); rb = rb.resize((rw, round(rb.height*rw/rb.width)), Image.LANCZOS)
cv.paste(rb, (W//2 - rw//2, y + 40), rb)

# ── Anotaciones de la guia ─────────────────────────────────────────────
def nota(y0, y1, txt, col=(120,200,255)):
    x = 24
    d.line([(x, y0), (x, y1)], fill=col+(170,), width=3)
    d.line([(x, y0), (x+16, y0)], fill=col+(170,), width=3)
    d.line([(x, y1), (x+16, y1)], fill=col+(170,), width=3)
    d.text((x+26, (y0+y1)//2), txt, font=mono(17), fill=col+(230,), anchor='lm')

nota(400, 400+int(W*0.94*799/3600), 'frase-en.png')
d.text((W//2, H-34), 'GUIA DE COLOCACION \u00b7 columna derecha del stand',
       font=mono(19), fill=DIM, anchor='mm')

cv.save(os.path.join(S, 'guia-colocacion.png'))
print('guia-colocacion.png', cv.size)
