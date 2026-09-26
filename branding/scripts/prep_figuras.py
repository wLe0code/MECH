# Extrae las figuras del anexo del trabajo escrito y las deja listas para la
# web en web/assets/figuras/.
#
# Dos fuentes:
#   1) MECH-3 Final.pdf (Nacional, sep 2026)  -> figuras 3-25 y el BMC.
#   2) MECH California.docx (sep 2026)         -> figuras 26-45 (las nuevas).
#      Del Word y no del PDF porque el Word guarda las fotos a mayor
#      resolucion (p. ej. 900x1600 contra 635x1129).
#
# Los mapeos se hicieron revisando las imagenes a mano contra los pies de
# foto: el orden de las imagenes dentro de la pagina (o del .docx) NO es el
# orden de las figuras. Las figuras 1 y 2 (arquitectura y caso de uso) se
# omiten porque ya tenemos los originales en alta calidad en branding/.
#
# OJO con la cache: vercel.json sirve /assets con "immutable" (1 anio). Si
# una figura cambia de contenido, dale un NOMBRE nuevo; no pises el archivo.

import io, os, zipfile
from pypdf import PdfReader
from PIL import Image, ImageOps

DOCS = r'C:\Users\almon\OneDrive\Documentos\Científico\WRO\Documentación\MECH'
PDF = os.path.join(DOCS, 'MECH Nacional', 'MECH-3 Final.pdf')
DOCX = os.path.join(DOCS, 'MECH California.docx')
DST = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..',
                                   'web', 'assets', 'figuras'))
os.makedirs(DST, exist_ok=True)

# (pagina, indice_de_imagen_en_la_pagina) -> (nombre, ancho_max)
MAPA_PDF = {
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
    # en el Nacional era la figura 26; en California pasó a ser la 44
    (17, 2): ('fig44-miembros', 1800),
    (18, 1): ('bmc', 2048),          # Business Model Canvas actualizado
}

# word/media/<archivo> -> (nombre, ancho_max)
MAPA_DOCX = {
    'image31.jpeg': ('fig26-mech2-desarmado', 1000),
    'image32.jpeg': ('fig27-3d-nueva-version', 1200),
    'image33.jpeg': ('fig28-movilidad-mech3', 1000),
    'image34.jpeg': ('fig29-circuito-mech3', 1000),
    'image35.jpeg': ('fig30-rediseno-cara', 1200),
    'image37.jpeg': ('fig31-frente-mech3', 1000),
    'image38.jpeg': ('fig32-cuerpo-mech3', 1000),
    'image36.jpeg': ('fig33-construccion-cabeza', 1000),
    'image39.jpeg': ('fig34-cabeza-montada', 1000),
    'image40.jpeg': ('fig35-render-mech3', 1000),
    'image41.jpeg': ('fig36-vista-superior', 1000),
    'image43.jpeg': ('fig37-mech3-completo', 1000),
    'image42.jpeg': ('fig38-evolucion', 1400),
    'image44.jpeg': ('fig39-regional-alajuela', 1400),
    'image45.jpeg': ('fig40-regional-guanacaste', 1000),
    'image46.jpeg': ('fig41-final-nacional', 1000),
    'image47.jpeg': ('fig42-cargador', 1000),
    'image48.jpeg': ('fig43-mech3-desarmado', 1600),
    'image50.jpeg': ('fig45-premios', 1200),
}


# recortes (izq, arriba, der, abajo) antes de escalar
RECORTES = {
    # el original trae una franja gris de 14 px en el borde derecho
    'fig38-evolucion': (0, 0, 1066, 649),
}


def guardar(im, nombre, ancho):
    im = ImageOps.exif_transpose(im).convert('RGB')
    if nombre in RECORTES:
        im = im.crop(RECORTES[nombre])
    if im.width > ancho:
        im = im.resize((ancho, round(im.height * ancho / im.width)), Image.LANCZOS)
    out = os.path.join(DST, nombre + '.jpg')
    im.save(out, 'JPEG', quality=84, optimize=True, progressive=True)
    print(f'{nombre:34s} {im.size}  {os.path.getsize(out)//1024} KB')


reader = PdfReader(PDF)
for (pagina, idx), (nombre, ancho) in sorted(MAPA_PDF.items(), key=lambda k: k[1][0]):
    imgs = reader.pages[pagina - 1].images
    guardar(Image.open(io.BytesIO(imgs[idx].data)), nombre, ancho)

with zipfile.ZipFile(DOCX) as z:
    for archivo, (nombre, ancho) in sorted(MAPA_DOCX.items(), key=lambda k: k[1][0]):
        guardar(Image.open(io.BytesIO(z.read('word/media/' + archivo))), nombre, ancho)
