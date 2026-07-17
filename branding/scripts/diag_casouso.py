# Diagrama de caso de uso: Usuario / MECH-1 (render) / Equipo MECH.
# Figura ancha para las dos columnas IEEE: 7.16 in @ 300 dpi ≈ 2150 px.

from diag_base import *
import os

OUT = r'C:\Users\almon\OneDrive\Documentos\GitHub\MECH\branding'

W, H = 2150, 1250
c = Canvas(W, H)

c.text((50, 40), 'DIAGRAMA DE CASO DE USO', size=15, weight=700, fill=ROJO)
c.text((50, 66), 'MECH-1 · Exposición interactiva en el stand', size=28,
       weight=800, fill=TINTA)

# ── Frontera del sistema ────────────────────────────────────────────────
SX0, SY0, SX1, SY1 = 470, 170, 1660, 1170
c.rbox(SX0, SY0, SX1, SY1, r=22, fill=(250, 250, 252), outline=BORDE, width=2)
c.text((SX0 + 28, SY0 + 26), 'SISTEMA MECH-1', size=13, weight=700,
       fill=GRIS)

# ── Actores ─────────────────────────────────────────────────────────────
def persona(cx, cy, escala=1.0, color=TINTA):
    r = 24 * escala
    c.ellipse(cx - r, cy - 58 * escala, cx + r, cy - 58 * escala + 2 * r,
              fill=color)
    c.rbox(cx - 40 * escala, cy, cx + 40 * escala, cy + 62 * escala,
           r=28 * escala, fill=color)

# Usuario (izquierda)
UX, UY = 235, 470
persona(UX, UY)
c.text((UX, UY + 92), 'Usuario', size=17, weight=700, fill=TINTA, anchor='mm')
c.text((UX, UY + 118), 'visitante del stand', size=12, weight=400,
       fill=GRIS, anchor='mm')

# Equipo MECH (abajo-izquierda)
EX, EY = 235, 930
persona(EX - 30, EY, 0.82)
persona(EX + 30, EY, 0.82, color=(70, 70, 82))
c.text((EX, EY + 84), 'Equipo MECH', size=17, weight=700, fill=TINTA, anchor='mm')
c.text((EX, EY + 110), 'supervisión técnica', size=12, weight=400,
       fill=GRIS, anchor='mm')

# MECH-1 (derecha, render del robot)
rs = 0.55
ROX, ROY = 1730, 250
draw_robot(c, ROX, ROY, rs)
rcx = ROX + 300 * rs
c.text((rcx, ROY + 780 * rs + 34), 'MECH-1', size=19, weight=800,
       fill=TINTA, anchor='mm')
c.text((rcx, ROY + 780 * rs + 62), 'robot expositor', size=12, weight=400,
       fill=GRIS, anchor='mm')

# ── Casos de uso ────────────────────────────────────────────────────────
# núcleo
UC1 = (720, 470)
c.node(*UC1, 340, 86, 'Selección por voz', accent=ROJO,
       sub='wake word «ok MECH»', size=17)

UC_STAND = (720, 265)
c.node(*UC_STAND, 340, 74, 'Proyección de stand', accent=MORADO,
       sub='información del proyecto', size=15)

UC_INM = (1110, 470)
c.node(*UC_INM, 300, 86, 'Espacio inmersivo', accent=ROJO,
       sub='narración de la obra', size=17)

# derivados del espacio inmersivo
UC_FUN = (1480, 300)
c.node(*UC_FUN, 300, 70, 'Función proyectada', accent=MORADO,
       sub='video / imagen', size=14)
UC_MOV = (1480, 470)
c.node(*UC_MOV, 300, 70, 'Movimiento', accent=MORADO,
       sub='gestos y giros', size=14)
UC_QA = (1480, 640)
c.node(*UC_QA, 300, 70, 'Preguntas y respuestas', accent=MORADO,
       sub='IA en vivo', size=14)

# supervisión
UC_SUP = (830, 930)
c.node(*UC_SUP, 400, 86, 'Supervisión de firmware', accent=AMBAR,
       sub='panel web de control', size=17)
UC_GIT = (1300, 860)
c.node(*UC_GIT, 320, 70, 'Repositorio en GitHub', accent=AMBAR,
       sub='código abierto', size=14)
UC_OBS = (1300, 1020)
c.node(*UC_OBS, 320, 70, 'Revisión de obstáculos', accent=AMBAR,
       sub='y movimiento', size=14)

# ── Conexiones ──────────────────────────────────────────────────────────
# Usuario → selección por voz
c.arrow([(UX + 52, UY + 10), (UC1[0] - 174, UC1[1])], color=(90, 90, 104),
        width=2.6, head=11)
# selección → stand (arriba)
c.arrow([(UC1[0], UC1[1] - 43), (UC1[0], UC_STAND[1] + 41)], width=2.4)
# selección → espacio inmersivo
c.arrow([(UC1[0] + 170, UC1[1]), (UC_INM[0] - 154, UC_INM[1])], width=2.4)
# espacio inmersivo → derivados (codos limpios)
inm_r = UC_INM[0] + 150
mid_x = (inm_r + UC_FUN[0] - 150) / 2
for (ucx, ucy) in [UC_FUN, UC_MOV, UC_QA]:
    if ucy == UC_INM[1]:
        c.arrow([(inm_r, UC_INM[1]), (ucx - 154, ucy)], width=2.2)
    else:
        c.arrow([(inm_r, UC_INM[1]), (mid_x, UC_INM[1]), (mid_x, ucy),
                 (ucx - 154, ucy)], width=2.2)
# selección → supervisión
c.arrow([(UC1[0] - 60, UC1[1] + 43), (UC1[0] - 60, UC_SUP[1] - 47)], width=2.2)
# supervisión → github / obstáculos
c.arrow([(UC_SUP[0] + 200, UC_SUP[1] - 12), (UC_GIT[0] - 164, UC_GIT[1] + 6)], width=2.2)
c.arrow([(UC_SUP[0] + 200, UC_SUP[1] + 12), (UC_OBS[0] - 164, UC_OBS[1] - 6)], width=2.2)
# Equipo MECH → supervisión
c.arrow([(EX + 62, EY + 16), (UC_SUP[0] - 204, UC_SUP[1])],
        color=shade(AMBAR, 0.9), width=2.6, head=11)

# MECH-1 ejecuta los derivados (líneas que convergen hacia el robot)
rob_edge = ROX + 92 * rs   # borde izquierdo del robot
punto = (rob_edge - 8, 470)
for (ucx, ucy) in [UC_FUN, UC_MOV, UC_QA]:
    c.line([(ucx + 154, ucy), punto], fill=tint(ROJO, 0.45), width=2.4)
# etiqueta sobre la línea central
ej_x, ej_y = (UC_MOV[0] + 154 + punto[0]) / 2, 448
c.rbox(ej_x - 44, ej_y - 13, ej_x + 44, ej_y + 13, r=8, fill=BLANCO,
       outline=tint(ROJO, 0.45), width=1.4)
c.text((ej_x, ej_y - 1), 'ejecuta', size=12, weight=700,
       fill=shade(ROJO, 0.85), anchor='mm')

# ── Leyenda ─────────────────────────────────────────────────────────────
ly = H - 58
c.rbox(50, ly, W - 50, ly + 42, r=10, fill=(248, 248, 250), outline=BORDE, width=1.4)
items = [(ROJO, 'Interacción por voz'), (MORADO, 'Salidas del espacio inmersivo'),
         (AMBAR, 'Supervisión del equipo'), ((90, 90, 104), 'Actores externos')]
lx = 84
for col, lab in items:
    c.ellipse(lx, ly + 14, lx + 14, ly + 28, fill=col)
    c.text((lx + 26, ly + 20), lab, size=12, weight=600, fill=GRIS, anchor='lm')
    lx += 26 + c.text_size(lab, size=12, weight=600)[0] + 60

c.save(os.path.join(OUT, 'diagrama-caso-uso.png'))
