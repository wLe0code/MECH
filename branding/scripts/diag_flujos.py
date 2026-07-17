# Diagramas de flujo mejorados (hardware y software).
# Ancho de columna IEEE: 3.5 in @ 300 dpi = 1050 px, verticales.

from diag_base import *
import os

OUT = r'C:\Users\almon\OneDrive\Documentos\GitHub\MECH\branding'

# ════════════════════════════════════════════════════════════════════════
# FLUJO 1 · HARDWARE (encendido e inicialización)
# ════════════════════════════════════════════════════════════════════════
W, H = 1050, 1150
c = Canvas(W, H)

c.text((40, 34), 'DIAGRAMA DE FLUJO · 1 DE 2', size=13, weight=700, fill=AZUL)
c.text((40, 56), 'Encendido e inicialización del hardware', size=24,
       weight=800, fill=TINTA)

SPINE = 300          # eje vertical principal
BR = 770             # centro de las ramas derechas
NW, NH = 400, 74     # nodo estándar
BW, BH = 380, 70     # nodo de rama

y = 160
c.pill(SPINE, y, 340, 56, 'Se enciende el equipo', color=TINTA, size=15)

y2 = y + 110
c.arrow([(SPINE, y + 28), (SPINE, y2 - 37)], width=2.4)
c.node(SPINE, y2, NW, NH, 'Inicializar firmware', accent=AZUL,
       sub='Arduino Uno + Raspberry Pi', size=16)

y3 = y2 + 130
c.arrow([(SPINE, y2 + 37), (SPINE, y3 - 37)], width=2.4)
c.node(SPINE, y3, NW, NH, 'Arranque del hardware', accent=AZUL, size=16)

# rama: proyectores
c.arrow([(SPINE + NW/2, y3), (BR - BW/2 - 4, y3)], width=2.4)
c.node(BR, y3, BW, BH, 'Proyectores se encienden', accent=MORADO, size=15)

# sensores
y4 = y3 + 140
c.arrow([(SPINE, y3 + 37), (SPINE, y4 - 37)], width=2.4)
c.node(SPINE, y4, NW, NH, 'Activación de sensores', accent=AZUL, size=16)

c.arrow([(SPINE + NW/2, y4), (BR - BW/2 - 4, y4 - 34)], width=2.4)
c.node(BR, y4 - 42, BW, 62, 'Cámara  ·  visión de usuarios',
       accent=MORADO, size=14)
c.arrow([(SPINE + NW/2, y4), (BR - BW/2 - 4, y4 + 34)], width=2.4)
c.node(BR, y4 + 42, BW, 62, 'Micrófono  ·  escucha activa',
       accent=MORADO, size=14)

# movilidad
y5 = y4 + 160
c.arrow([(SPINE, y4 + 37), (SPINE, y5 - 37)], width=2.4)
c.node(SPINE, y5, NW, NH, 'Sistema de movilidad se inicia',
       accent=AZUL, size=16)

y6 = y5 + 130
c.arrow([(SPINE, y5 + 37), (SPINE, y6 - 37)], width=2.4)
c.node(SPINE, y6, NW, NH, 'Detección de obstáculos', accent=AZUL,
       sub='cámara + supervisión del panel', size=16)

y7 = y6 + 120
c.arrow([(SPINE, y6 + 37), (SPINE, y7 - 30)], width=2.4)
c.pill(SPINE, y7, 460, 58, 'El robot evita obstáculos y opera', color=shade(AZUL, 1.0), size=14)

# leyenda
ly = H - 70
c.rbox(40, ly, W - 40, ly + 44, r=10, fill=(248, 248, 250), outline=BORDE, width=1.4)
c.ellipse(64, ly + 15, 78, ly + 29, fill=AZUL)
c.text((90, ly + 21), 'Secuencia principal', size=11.5, weight=600, fill=GRIS, anchor='lm')
c.ellipse(320, ly + 15, 334, ly + 29, fill=MORADO)
c.text((346, ly + 21), 'Subsistemas que se activan en paralelo', size=11.5,
       weight=600, fill=GRIS, anchor='lm')

c.save(os.path.join(OUT, 'diagrama-flujo-hardware.png'))

# ════════════════════════════════════════════════════════════════════════
# FLUJO 2 · SOFTWARE (interacción por voz)
# ════════════════════════════════════════════════════════════════════════
W, H = 1050, 1150
c = Canvas(W, H)

c.text((40, 34), 'DIAGRAMA DE FLUJO · 2 DE 2', size=13, weight=700, fill=ROJO)
c.text((40, 56), 'Interacción por voz y proyección', size=24,
       weight=800, fill=TINTA)

SPINE = 300
BR = 770

y = 160
c.pill(SPINE, y, 340, 56, 'Firmware inicializado', color=TINTA, size=15)

y2 = y + 110
c.arrow([(SPINE, y + 28), (SPINE, y2 - 37)], width=2.4)
c.node(SPINE, y2, 400, 74, 'Software', accent=ROJO,
       sub='backend en la Raspberry Pi 5', size=16)

y3 = y2 + 140
c.arrow([(SPINE, y2 + 37), (SPINE, y3 - 40)], width=2.4)
c.node(SPINE, y3, 400, 80, 'Selección por voz', accent=ROJO,
       sub='wake word «ok MECH» + petición', size=16)

# rama: stand
c.arrow([(SPINE + 200, y3), (BR - 190 - 4, y3)], width=2.4)
c.node(BR, y3, 380, 74, 'Proyección de stand', accent=MORADO,
       sub='información del proyecto', size=15)

# espacio inmersivo
y4 = y3 + 150
c.arrow([(SPINE, y3 + 40), (SPINE, y4 - 37)], width=2.4)
c.node(SPINE, y4, 400, 74, 'Espacio inmersivo', accent=ROJO,
       sub='narración + proyección de la obra', size=16)

c.arrow([(SPINE + 200, y4), (BR - 190 - 4, y4)], width=2.4)
c.node(BR, y4, 380, 74, 'Se proyecta la «función»', accent=MORADO,
       sub='video o imagen por escena', size=15)

# movimiento
y5 = y4 + 150
c.arrow([(SPINE, y4 + 37), (SPINE, y5 - 37)], width=2.4)
c.node(SPINE, y5, 400, 74, 'Movimiento', accent=ROJO,
       sub='gestos y giros durante el relato', size=16)

c.arrow([(SPINE + 200, y5), (BR - 190 - 4, y5)], width=2.4)
c.node(BR, y5, 380, 74, 'Recorrido pasivo', accent=MORADO,
       sub='código de la Pi / Arduino', size=15)

# preguntas y fin
y6 = y5 + 150
c.arrow([(SPINE, y5 + 37), (SPINE, y6 - 37)], width=2.4)
c.node(SPINE, y6, 400, 74, 'Preguntas del público', accent=ROJO,
       sub='respuestas con IA en vivo', size=16)

y7 = y6 + 120
c.arrow([(SPINE, y6 + 37), (SPINE, y7 - 30)], width=2.4)
c.pill(SPINE, y7, 460, 58, 'Vuelve a escuchar («ok MECH»)',
       color=shade(ROJO, 0.85), size=14)

ly = H - 70
c.rbox(40, ly, W - 40, ly + 44, r=10, fill=(248, 248, 250), outline=BORDE, width=1.4)
c.ellipse(64, ly + 15, 78, ly + 29, fill=ROJO)
c.text((90, ly + 21), 'Flujo principal de interacción', size=11.5, weight=600,
       fill=GRIS, anchor='lm')
c.ellipse(400, ly + 15, 414, ly + 29, fill=MORADO)
c.text((426, ly + 21), 'Salidas proyectadas / acciones derivadas', size=11.5,
       weight=600, fill=GRIS, anchor='lm')

c.save(os.path.join(OUT, 'diagrama-flujo-software.png'))
