# Extrae las figuras del anexo del trabajo escrito (MECH-3 Final.pdf) y las
# deja listas para la web en web/assets/figuras/.
#
# El mapeo pagina_indice -> figura se hizo revisando el PDF a mano; las
# figuras 1 y 2 (arquitectura y caso de uso) se omiten porque ya tenemos
# los originales en alta calidad en branding/.

import io, os
from pypdf import PdfReader
from PIL import Image

PDF = (r'C:\Users\almon\OneDrive\Documentos\Científico\WRO\Documentación'
       r'\MECH\MECH Nacional\MECH-3 Final.pdf')
DST = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..',
                                   'web', 'assets', 'figuras'))
os.makedirs(DST, exist_ok=True)

# (pagina, indice_de_imagen_en_la_pagina) -> (nombre, ancho_max)
MAPA = {
    (12, 1): ('fig03-modelado-3d', 1100),
    (12, 2): ('fig04-primera-estructura', 1200),
    (12, 3): ('fig05-estructura-movilidad', 1200),
    (12, 4): ('fig06-ensamblaje-pvc', 1200),
    (13, 2): ('fig07-estructura-con-movimiento', 1200),
    (13, 4): ('fig08-recubierto-coroplast', 1400),
    (13, 6): ('fig09-estructura-interna', 1400),
    (13, 1): ('fig10-montaje-cabeza', 1400),
    (13, 3): ('fig11-sistema-ventilacion', 1400),
    (13, 5): ('fig12-acoplamiento-sistemas', 1000),
    (14, 1): ('fig13-boceto-decoracion', 1000),
    (14, 3): ('fig14-mech1-completo', 1200),
    (14, 2): ('fig15-optimizacion-movilidad', 1200),
    (14, 4): ('fig16-cableado-trenzado', 1200),
    (15, 2): ('fig17-componentes-electronicos', 1200),
    (15, 4): ('fig18-lentes-vr', 1100),
    (15, 3): ('fig19-movilidad-finalizada', 1200),
    (15, 1): ('fig20-mech2-completo', 1200),
    (16, 1): ('fig21-3d-base-inferior', 1000),
    (16, 2): ('fig22-3d-coraza', 1000),
    (16, 4): ('fig23-3d-parte-superior', 1000),
    (16, 3): ('fig24-3d-estructura-interna', 1000),
    (17, 1): ('fig25-3d-soporte-cabeza', 1000),
    (17, 2): ('fig26-miembros', 1800),
    (18, 1): ('bmc', 2048),          # Business Model Canvas actualizado
}

reader = PdfReader(PDF)
for (pagina, idx), (nombre, ancho) in sorted(MAPA.items(), key=lambda k: k[1][0]):
    imgs = reader.pages[pagina - 1].images
    im = Image.open(io.BytesIO(imgs[idx].data)).convert('RGB')
    if im.width > ancho:
        im = im.resize((ancho, round(im.height * ancho / im.width)), Image.LANCZOS)
    out = os.path.join(DST, nombre + '.jpg')
    im.save(out, 'JPEG', quality=84, optimize=True, progressive=True)
    print(f'{nombre:34s} {im.size}  {os.path.getsize(out)//1024} KB')
