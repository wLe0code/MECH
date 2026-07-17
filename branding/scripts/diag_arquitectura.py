# Diagrama de arquitectura: las tres capas físicas DENTRO del cuerpo de
# MECH-1 (render del sitio). Ancho de columna IEEE: 3.5 in @ 300 dpi = 1050 px.

from diag_base import *

W, H = 1050, 900
c = Canvas(W, H)

# ── Título ──────────────────────────────────────────────────────────────
c.text((40, 34), 'DIAGRAMA DE ARQUITECTURA', size=13, weight=700,
       fill=ROJO)
c.text((40, 56), 'MECH-1 · Distribución física por capas', size=24,
       weight=800, fill=TINTA)

# ── Robot a la izquierda ────────────────────────────────────────────────
s = 0.78
ox, oy = 30, 130
draw_robot(c, ox, oy, s)

def RX(v): return ox + v * s
def RY(v): return oy + v * s

# Zonas (viewBox y): superior 140-305, central 306-560, mecánica 561-755
zx0, zx1 = RX(96), RX(504)
zonas = [
    ('CAPA SUPERIOR', MORADO, RY(138), RY(300),
     ['Webcam C930e', 'Proyector HD']),
    ('CAPA CENTRAL', ROJO, RY(306), RY(560),
     ['Brazos (servos)', 'Raspberry Pi 5', 'Micrófono', 'JBL Charge 3', 'Fuente de poder']),
    ('CAPA MECÁNICA', AZUL, RY(566), RY(752),
     ['Arduino Uno', 'Ruedas mecanum', 'Motores DC', 'Drivers L298N']),
]

# ── Paneles a la derecha ────────────────────────────────────────────────
px0, px1 = 545, W - 35
panel_h = {0: 150, 1: 240, 2: 200}
gap = 28
total = sum(panel_h.values()) + gap * 2
py = 145

for i, (nombre, color, zy0, zy1, comps) in enumerate(zonas):
    ph = panel_h[i]
    py1 = py + ph

    # zona punteada sobre el robot
    c.dashed_rbox(zx0, zy0, zx1, zy1, r=14, color=color, width=2.2,
                  dash=9, gap=6)
    # etiqueta pequeña de zona (número)
    c.ellipse(zx0 - 14, (zy0+zy1)/2 - 14, zx0 + 14, (zy0+zy1)/2 + 14,
              fill=color)
    c.text((zx0, (zy0+zy1)/2 - 1), str(i+1), size=14, weight=800,
           fill=BLANCO, anchor='mm')

    # conector zona → panel
    zy_mid = (zy0 + zy1) / 2
    py_mid = py + ph / 2
    c.line([(zx1 + 2, zy_mid), (px0 - 24, zy_mid), (px0 - 24, py_mid),
            (px0 - 6, py_mid)], fill=color, width=2.2)
    c.ellipse(px0 - 10, py_mid - 4, px0 - 2, py_mid + 4, fill=color)

    # panel
    c.rbox(px0, py, px1, py1, r=14, fill=(252, 252, 253),
           outline=BORDE, width=1.6)
    c.rbox(px0, py, px0 + 6, py1, r=3, fill=color)
    c.ellipse(px0 + 22, py + 16, px0 + 46, py + 40, fill=color)
    c.text((px0 + 34, py + 27), str(i+1), size=13, weight=800,
           fill=BLANCO, anchor='mm')
    c.text((px0 + 58, py + 28), nombre, size=15.5, weight=800,
           fill=shade(color, 0.8), anchor='lm')

    # chips de componentes (2 por fila)
    cw = (px1 - px0 - 60) / 2
    cx_l = px0 + 30 + cw / 2
    cx_r = px0 + 30 + cw + 14 + cw / 2 - 7
    cy0 = py + 70
    for j, comp in enumerate(comps):
        col = j % 2
        row = j // 2
        cx = cx_l if col == 0 else cx_r
        cy = cy0 + row * 44
        # chip centrado en su celda con ancho de celda fijo
        x0, y0 = cx - cw/2 + 4, cy - 17
        x1, y1 = cx + cw/2 - 4, cy + 17
        c.rbox(x0, y0, x1, y1, r=8, fill=tint(color, 0.09),
               outline=tint(color, 0.5), width=1.5)
        c.text((cx, cy - 1), comp, size=12.5, weight=600,
               fill=shade(color, 0.7), anchor='mm')

    py = py1 + gap

# ── Nota de comunicación al pie ─────────────────────────────────────────
ny = H - 62
c.rbox(35, ny, W - 35, ny + 40, r=10, fill=(248, 248, 250),
       outline=BORDE, width=1.4)
c.text((W/2, ny + 20),
       'Raspberry Pi 5 – Arduino Uno vía USB serial  ·  HDMI al proyector  ·  USB a cámara y micrófono',
       size=11.5, weight=600, fill=GRIS, anchor='mm')

import os
OUT = r'C:\Users\almon\OneDrive\Documentos\GitHub\MECH\branding'
os.makedirs(OUT, exist_ok=True)
c.save(os.path.join(OUT, 'diagrama-arquitectura.png'))
