# Ficha "La misma tecnología, infinidad de usos" — sección de aplicaciones
# del sitio (Cultura, Educación, Salud, Empresas, Historia, …y más).
# Fondo NEGRO, formato 4:5 (2400×3000) para Instagram, alta calidad.

import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SS = 2
W, H = 2400, 3000
CW, CH = W * SS, H * SS
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
EMOJI_FONT = r'C:\Windows\Fonts\seguiemj.ttf'

BG      = (0, 0, 0)
SURFACE = (20, 20, 27)
TEXT    = (240, 238, 255)
MUTED   = (155, 155, 173)
DIM     = (110, 110, 128)
RED     = (226, 75, 74)
PURPLE  = (127, 119, 221)
PURPLE2 = (83, 74, 183)
TEAL    = (29, 158, 117)
AMBER   = (239, 159, 39)
BORDER  = (46, 46, 58)

_fc = {}
def font(size, weight=400):
    k = (size, weight)
    if k not in _fc:
        f = ImageFont.truetype('Sora.ttf', int(size * SS))
        try: f.set_variation_by_axes([weight])
        except Exception: pass
        _fc[k] = f
    return _fc[k]

def tint(color, f=0.12):
    return tuple(int(c * f + 0 * (1 - f)) for c in color)  # sobre negro
def mix(color, f):
    return tuple(int(c * f) for c in color)

img = Image.new('RGB', (CW, CH), BG)
d = ImageDraw.Draw(img)

def text(cx, cy, s, f, fill=TEXT, anchor='mm', spacing=None):
    if spacing is None:
        d.text((cx * SS, cy * SS), s, font=f, fill=fill, anchor=anchor)
    else:
        d.multiline_text((cx * SS, cy * SS), s, font=f, fill=fill, anchor=anchor,
                         align='center', spacing=spacing * SS)

def measure(s, f):
    b = d.textbbox((0, 0), s, font=f); return (b[2]-b[0])/SS, (b[3]-b[1])/SS

def wrap(s, f, maxw):
    words = s.split(); lines=[]; cur=''
    for w in words:
        t=(cur+' '+w).strip()
        if measure(t,f)[0] <= maxw or not cur: cur=t
        else: lines.append(cur); cur=w
    lines.append(cur); return lines

def rbox(x0, y0, x1, y1, r, **kw):
    d.rounded_rectangle([x0*SS, y0*SS, x1*SS, y1*SS], radius=r*SS, **kw)

def pixel_band(y, flip=False, alpha=30):
    dd = ImageDraw.Draw(img, 'RGBA'); tile=220*SS
    rects=[(6,8,13),(26,18,9),(44,6,11),(60,22,14),(82,9,9),(97,20,12),
           (116,7,14),(138,19,9),(154,8,11),(172,21,12),(192,9,9),(206,19,10)]
    band=46*SS; x0=0
    while x0<CW:
        for rx,ry,rw in rects:
            X=x0+rx*SS; Y=y+(band-ry*SS if flip else ry*SS)
            dd.rectangle([X,Y,X+rw*SS,Y+rw*SS*0.9], fill=(240,238,255,alpha))
        x0+=tile

def emoji(char, size):
    strike = 109
    f = ImageFont.truetype(EMOJI_FONT, strike)
    tmp = Image.new('RGBA', (strike*2, strike*2), (0,0,0,0))
    ImageDraw.Draw(tmp).text((strike, strike), char, font=f, embedded_color=True, anchor='mm')
    bb = tmp.getbbox(); tmp = tmp.crop(bb)
    px = int(size*SS)
    tmp.thumbnail((px, px), Image.LANCZOS)
    return tmp

def logo(cx, cy, scale, color=TEXT):
    layer = Image.new('RGBA', (CW, CH), (0,0,0,0)); dl=ImageDraw.Draw(layer)
    rw, rh = 264*scale*SS, 96*scale*SS
    dl.rounded_rectangle([cx*SS-rw/2, cy*SS-rh/2, cx*SS+rw/2, cy*SS+rh/2],
                         radius=22*scale*SS, outline=color, width=max(int(9*scale*SS),2))
    t=math.tan(math.radians(-8))
    layer=layer.transform((CW,CH),Image.AFFINE,(1,t,-t*cy*SS,0,1,0),resample=Image.BICUBIC)
    img.paste(layer,(0,0),layer)
    tl=Image.new('RGBA',(CW,CH),(0,0,0,0)); dt=ImageDraw.Draw(tl)
    dt.text((cx*SS,cy*SS),'MECH',font=font(56*scale,800),fill=color,anchor='mm')
    t2=math.tan(math.radians(12))
    tl=tl.transform((CW,CH),Image.AFFINE,(1,t2,-t2*cy*SS,0,1,0),resample=Image.BICUBIC)
    img.paste(tl,(0,0),tl)

# ── Cabecera ────────────────────────────────────────────────────────────
pixel_band(int(46*SS))
cx = W/2
logo(cx, 230, 0.44)
text(cx, 350, 'UN ROBOT, MUCHOS MUNDOS', font(30, 700), fill=RED)
text(cx, 430, 'La misma tecnología,', font(78, 800), fill=TEXT)
# segunda línea con degradado — la hacemos vía máscara
def grad_line(cx, cy, s, f, stops):
    layer=Image.new('RGBA',(CW,CH),(0,0,0,0))
    ImageDraw.Draw(layer).text((cx*SS,cy*SS),s,font=f,fill=(255,255,255,255),anchor='mm')
    a=layer.split()[3]; bb=a.getbbox()
    w=bb[2]-bb[0]; xs=np.linspace(0,1,w); pts=[p[0] for p in stops]; cols=[np.array(p[1],np.float32) for p in stops]
    row=np.zeros((1,w,3),np.float32)
    for i in range(w):
        x=xs[i]
        for j in range(len(pts)-1):
            if pts[j]<=x<=pts[j+1]:
                fr=(x-pts[j])/(pts[j+1]-pts[j]+1e-9); row[0,i]=cols[j]*(1-fr)+cols[j+1]*fr; break
        else: row[0,i]=cols[-1]
    g=Image.fromarray(np.repeat(row.astype(np.uint8),bb[3]-bb[1],0),'RGB')
    fill=Image.new('RGB',(CW,CH),stops[0][1]); fill.paste(g,(bb[0],bb[1]))
    img.paste(fill,(0,0),a)
grad_line(cx, 528, 'infinidad de usos.', font(78, 800),
          [(0.0,RED),(0.55,PURPLE),(1.0,TEAL)])

lead = ('MECH no se limita a un tema. Es una plataforma versátil: allí donde el '
        'interés de las personas se apaga, un espacio inmersivo puede volver a encenderlo.')
ll = wrap(lead, font(30, 300), 1560)
ly = 640
for line in ll:
    text(cx, ly, line, font(30, 300), fill=MUTED); ly += 46

# ── Tarjetas (2 col × 3 filas) ──────────────────────────────────────────
cards = [
    ('🎭', 'Cultura', RED, 'Expone obras y artistas locales dando el contexto que un cartel no alcanza a transmitir. Es su demo actual.'),
    ('📚', 'Educación', PURPLE, 'Un profesor de apoyo en casa que refuerza lo aprendido en clase, con paciencia infinita.'),
    ('🩺', 'Salud', TEAL, 'Explica tratamientos o medicamentos básicos de forma clara y cercana a quien lo necesita.'),
    ('📈', 'Empresas', AMBER, 'Publicidad viva: presenta productos y servicios de una manera que la gente sí quiere ver.'),
    ('🏛️', 'Historia', PURPLE2, 'Convierte fechas y hechos en relatos inmersivos que se recuerdan porque se sienten.'),
    ('✦', '…y más', DIM, 'Entretenimiento, museos, ferias. Donde haga falta captar la atención, MECH encaja.'),
]
mx = 150; gap = 44
cw = (W - 2*mx - gap) / 2
ch = 560
top = 840
for i, (emo, title, col, body) in enumerate(cards):
    r, ccol = divmod(i, 2)
    x0 = mx + ccol*(cw+gap); y0 = top + r*(ch+gap)
    x1, y1 = x0+cw, y0+ch
    last = (i == len(cards)-1)
    # tarjeta
    rbox(x0, y0, x1, y1, 26, fill=SURFACE, outline=BORDER, width=int(1.6*SS))
    # barra de acento superior
    if not last:
        rbox(x0, y0, x1, y0+7, 3, fill=col)
    # tile de emoji
    tile = 108
    tx0, ty0 = x0+44, y0+52
    rbox(tx0, ty0, tx0+tile, ty0+tile, 22, fill=mix(col,0.16) if not last else SURFACE,
         outline=mix(col,0.55), width=int(1.6*SS))
    if emo == '✦':  # sin emoji de color: dibujamos un "+" con la fuente del sitio
        text(tx0+tile/2, ty0+tile/2-2, '+', font(56, 700), fill=MUTED, anchor='mm')
    else:
        em = emoji(emo, tile-40)
        img.paste(em, (int((tx0+tile/2)*SS - em.width/2), int((ty0+tile/2)*SS - em.height/2)), em)
    # título
    text(x0+44, y0+205, title, font(44, 800), fill=TEXT if not last else MUTED, anchor='lm')
    # cuerpo
    by = y0+270
    for line in wrap(body, font(29, 300), cw-88):
        text(x0+44, by, line, font(29, 300), fill=MUTED, anchor='lm'); by += 44
    # etiqueta demo para Cultura
    if title == 'Cultura':
        tag='DEMO ACTUAL'; tw,_=measure(tag,font(20,700))
        rbox(x0+44, y1-70, x0+44+tw+36, y1-24, 8, fill=mix(col,0.14), outline=mix(col,0.5), width=int(1.4*SS))
        text(x0+44+18+tw/2, y1-47, tag, font(20,700), fill=col, anchor='mm')

# ── Pie ─────────────────────────────────────────────────────────────────
text(cx, H-150, '« si es inmersivo, es MECH »', font(34, 400), fill=DIM)
pixel_band(CH-int(84*SS), flip=True)

img.resize((W, H), Image.LANCZOS).save(os.path.join(OUT, 'ficha-usos.png'))
print('OK ficha-usos.png', (W, H))
