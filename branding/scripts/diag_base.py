# Base de dibujo para los diagramas de MECH (formato IEEE, 300 dpi).
# Todo se dibuja a escala SS (supersampling) y se reduce con LANCZOS
# para tener bordes suaves (PIL no antialiasa formas).

import math
from PIL import Image, ImageDraw, ImageFont

SS = 3  # factor de supersampling

# Paleta (de los diagramas del equipo + panel del proyecto)
MORADO = (139, 92, 246)    # capa superior
ROJO   = (224, 32, 32)     # capa central
AZUL   = (34, 32, 154)     # capa mecánica
AMBAR  = (239, 159, 39)    # supervisión
TINTA  = (26, 26, 34)      # texto principal
GRIS   = (108, 108, 122)   # texto secundario
LINEA  = (150, 150, 160)   # conectores
BORDE  = (208, 208, 216)   # bordes suaves
BLANCO = (255, 255, 255)

_font_cache = {}

def font(size, weight=400):
    key = (size, weight)
    if key not in _font_cache:
        f = ImageFont.truetype('Sora.ttf', int(size * SS))
        f.set_variation_by_axes([weight])
        _font_cache[key] = f
    return _font_cache[key]

def tint(color, factor=0.12):
    """Mezcla el color con blanco (fondo suave)."""
    return tuple(int(255 - (255 - c) * factor) for c in color)

def shade(color, factor=0.75):
    return tuple(int(c * factor) for c in color)

class Canvas:
    def __init__(self, w, h, bg=BLANCO):
        self.w, self.h = w, h
        self.img = Image.new('RGB', (w * SS, h * SS), bg)
        self.d = ImageDraw.Draw(self.img)

    # ── primitivas (coordenadas en px finales, se multiplican por SS) ──
    def rbox(self, x0, y0, x1, y1, r=10, fill=None, outline=None, width=2):
        self.d.rounded_rectangle(
            [x0 * SS, y0 * SS, x1 * SS, y1 * SS], radius=r * SS,
            fill=fill, outline=outline, width=int(width * SS))

    def ellipse(self, x0, y0, x1, y1, fill=None, outline=None, width=2):
        self.d.ellipse([x0 * SS, y0 * SS, x1 * SS, y1 * SS],
                       fill=fill, outline=outline, width=int(width * SS))

    def line(self, pts, fill=LINEA, width=2):
        self.d.line([(x * SS, y * SS) for x, y in pts],
                    fill=fill, width=int(width * SS), joint='curve')

    def dashed(self, p0, p1, fill=LINEA, width=2, dash=7, gap=5):
        x0, y0 = p0; x1, y1 = p1
        dist = math.hypot(x1 - x0, y1 - y0)
        if dist == 0: return
        ux, uy = (x1 - x0) / dist, (y1 - y0) / dist
        t = 0
        while t < dist:
            e = min(t + dash, dist)
            self.line([(x0 + ux * t, y0 + uy * t), (x0 + ux * e, y0 + uy * e)],
                      fill=fill, width=width)
            t += dash + gap

    def dashed_rbox(self, x0, y0, x1, y1, r=12, color=LINEA, width=2, dash=8, gap=6):
        # lados
        self.dashed((x0 + r, y0), (x1 - r, y0), color, width, dash, gap)
        self.dashed((x0 + r, y1), (x1 - r, y1), color, width, dash, gap)
        self.dashed((x0, y0 + r), (x0, y1 - r), color, width, dash, gap)
        self.dashed((x1, y0 + r), (x1, y1 - r), color, width, dash, gap)
        # esquinas (arcos)
        for cx, cy, a0, a1 in [(x0+r, y0+r, 180, 270), (x1-r, y0+r, 270, 360),
                               (x1-r, y1-r, 0, 90), (x0+r, y1-r, 90, 180)]:
            self.d.arc([(cx-r)*SS, (cy-r)*SS, (cx+r)*SS, (cy+r)*SS],
                       a0, a1, fill=color, width=int(width * SS))

    def text(self, xy, s, size=14, weight=400, fill=TINTA, anchor='la',
             align='left', max_w=None, line_h=1.35):
        """Texto con envoltura opcional. anchor tipo PIL ('mm' centrado...)."""
        f = font(size, weight)
        if max_w:
            s = self._wrap(s, f, max_w * SS)
        x, y = xy[0] * SS, xy[1] * SS
        if '\n' in s:
            self.d.multiline_text((x, y), s, font=f, fill=fill, anchor=anchor,
                                  align=align, spacing=int(size * SS * (line_h - 1)))
        else:
            self.d.text((x, y), s, font=f, fill=fill, anchor=anchor)
        return s

    def _wrap(self, s, f, max_w):
        words = s.split()
        lines, cur = [], ''
        for w in words:
            trial = (cur + ' ' + w).strip()
            if self.d.textlength(trial, font=f) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur); cur = w
        lines.append(cur)
        return '\n'.join(lines)

    def text_size(self, s, size=14, weight=400, max_w=None, line_h=1.35):
        f = font(size, weight)
        if max_w:
            s = self._wrap(s, f, max_w * SS)
        bbox = self.d.multiline_textbbox((0, 0), s, font=f,
                                         spacing=int(size * SS * (line_h - 1)))
        return (bbox[2] - bbox[0]) / SS, (bbox[3] - bbox[1]) / SS

    def arrow(self, pts, color=LINEA, width=2.2, head=9):
        """Polilínea con punta de flecha en el último tramo."""
        self.line(pts, fill=color, width=width)
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        ang = math.atan2(y1 - y0, x1 - x0)
        h = head
        p1 = (x1 - h * math.cos(ang - 0.45), y1 - h * math.sin(ang - 0.45))
        p2 = (x1 - h * math.cos(ang + 0.45), y1 - h * math.sin(ang + 0.45))
        self.d.polygon([(x1 * SS, y1 * SS), (p1[0] * SS, p1[1] * SS),
                        (p2[0] * SS, p2[1] * SS)], fill=color)

    # ── nodos de diagrama ──────────────────────────────────────────────
    def node(self, cx, cy, w, h, title, accent=ROJO, sub=None, r=12,
             size=15, weight=700, fill=None, text_fill=None, border_w=2.5):
        x0, y0, x1, y1 = cx - w/2, cy - h/2, cx + w/2, cy + h/2
        self.rbox(x0, y0, x1, y1, r=r, fill=fill or BLANCO,
                  outline=accent, width=border_w)
        tf = text_fill or TINTA
        if sub:
            self.text((cx, cy - h*0.14), title, size=size, weight=weight,
                      fill=tf, anchor='mm', align='center', max_w=w - 20)
            self.text((cx, cy + h*0.22), sub, size=size-4, weight=400,
                      fill=GRIS, anchor='mm', align='center', max_w=w - 20)
        else:
            self.text((cx, cy), title, size=size, weight=weight, fill=tf,
                      anchor='mm', align='center', max_w=w - 20)
        return (x0, y0, x1, y1)

    def pill(self, cx, cy, w, h, title, color=TINTA, size=14):
        self.rbox(cx - w/2, cy - h/2, cx + w/2, cy + h/2, r=h/2,
                  fill=color, outline=None, width=0)
        self.text((cx, cy), title, size=size, weight=700, fill=BLANCO,
                  anchor='mm', align='center')

    def chip(self, cx, cy, text, color, size=12.5, pad_x=12, pad_y=7, weight=600):
        w, h = self.text_size(text, size=size, weight=weight)
        x0, y0 = cx - w/2 - pad_x, cy - h/2 - pad_y
        x1, y1 = cx + w/2 + pad_x, cy + h/2 + pad_y
        self.rbox(x0, y0, x1, y1, r=7, fill=tint(color, 0.10),
                  outline=tint(color, 0.55), width=1.6)
        self.text((cx, cy - 1), text, size=size, weight=weight,
                  fill=shade(color, 0.72), anchor='mm')
        return (x0, y0, x1, y1)

    def save(self, path):
        out = self.img.resize((self.w, self.h), Image.LANCZOS)
        out.save(path, 'PNG')
        print('OK', path, out.size)


# ── Render del robot MECH-1 (portado del SVG del sitio, fondo claro) ────
def draw_robot(c, ox, oy, s, outline=True):
    """Dibuja el robot con origen (ox,oy) = esquina sup-izq del viewBox
    600x780 escalado por s. Pensado para fondo blanco."""
    def X(v): return ox + v * s
    def Y(v): return oy + v * s

    CUERPO = (23, 23, 30)
    NEGRO = (10, 10, 14)
    BORDE_R = (52, 52, 62)
    CLARO = (242, 241, 244)

    # sombra
    c.ellipse(X(130), Y(702), X(470), Y(742), fill=(225, 225, 231))
    # discos laterales
    c.ellipse(X(126), Y(400), X(178), Y(640), fill=NEGRO, outline=BORDE_R, width=max(2*s, 1))
    c.ellipse(X(422), Y(400), X(474), Y(640), fill=NEGRO, outline=BORDE_R, width=max(2*s, 1))
    # cuerpo: rect + elipse inferior
    c.d.rectangle([X(168)*SS, Y(340)*SS, X(432)*SS, Y(670)*SS], fill=CUERPO)
    c.ellipse(X(168), Y(644), X(432), Y(696), fill=CUERPO)
    # tapa superior blanca
    c.ellipse(X(168), Y(314), X(432), Y(366), fill=CLARO, outline=NEGRO, width=max(3*s, 1))
    # franja de píxeles
    px = [(188,382,20),(214,396,14),(236,378,16),(258,398,22),(288,380,14),
          (308,400,18),(334,382,22),(362,398,14),(384,380,16),(196,418,12),
          (246,422,14),(298,424,12),(348,420,14),(396,416,12)]
    for x, y, w in px:
        c.d.rectangle([X(x)*SS, Y(y)*SS, X(x+w)*SS, Y(y+w*0.9)*SS], fill=CLARO)
    # tornillos
    for x, y in [(252, 648), (300, 654), (348, 648)]:
        c.ellipse(X(x-5), Y(y-5), X(x+5), Y(y+5), fill=CLARO)
    # ruedas
    c.ellipse(X(214), Y(700), X(266), Y(732), fill=NEGRO)
    c.ellipse(X(334), Y(700), X(386), Y(732), fill=NEGRO)
    # cuello
    c.rbox(X(278), Y(286), X(322), Y(346), r=8*s, fill=NEGRO)
    # cabeza (banda blanca superior + frente oscuro)
    c.rbox(X(134), Y(152), X(466), Y(232), r=16*s, fill=CLARO, outline=NEGRO, width=max(3*s, 1))
    c.rbox(X(134), Y(176), X(466), Y(292), r=16*s, fill=(16, 16, 20), outline=BORDE_R, width=max(2*s, 1))
    # lente del proyector
    c.ellipse(X(192), Y(180), X(284), Y(272), fill=(10, 10, 13), outline=CLARO, width=5*s)
    c.ellipse(X(208), Y(196), X(268), Y(256), fill=(17, 19, 28))
    c.ellipse(X(221), Y(209), X(255), Y(243), fill=(27, 32, 51))
    c.ellipse(X(222), Y(210), X(234), Y(222), fill=(143, 151, 196))
    # cámara
    c.rbox(X(352), Y(210), X(418), Y(244), r=8*s, fill=(35, 35, 41), outline=(58, 58, 68), width=max(2*s, 1))
    c.ellipse(X(376), Y(218), X(394), Y(236), fill=(11, 11, 15), outline=(86, 86, 100), width=max(3*s, 1))
    c.ellipse(X(381.5), Y(223.5), X(388.5), Y(230.5), fill=(61, 69, 104))
