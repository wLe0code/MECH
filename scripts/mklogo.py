"""Genera los iconos de MECH a partir del LOGO OFICIAL.

    python scripts/mklogo.py

Deja tres archivos:

- `frontend/icon.svg`       Icono del panel (PWA), de los tres accesos del
                            escritorio de la Pi («Iniciar MECH»…) y la imagen
                            con que la app de Windows reconoce al robot.
                            Es VECTOR de verdad: las letras van como trazos
                            (sacados de Sora ExtraBold), así se ve igual en
                            la Pi aunque no tenga la fuente instalada.
- `windows/mech.ico`        Icono de la app «MECH» de Windows. Los tamaños
                            grandes (48-256) llevan el logo ENTERO; los
                            pequeños (16-32) solo la «M» con su marco, porque
                            la palabra completa a 16 px es una raya.
- `windows/app/logo-mech.png`  El logo, transparente, para la pantalla que
                            busca al robot.

El logo es el de `branding/` (marco redondeado inclinado 8° + «MECH» en Sora
ExtraBold con la inclinación que el navegador le da a la itálica, ~14°). Los
PNG salen directamente de `branding/MECH true black.png`, sin redibujar nada.
`branding/` NO se modifica.

Necesita Pillow y fontTools (`pip install pillow fonttools`). Solo hace falta
en la máquina de desarrollo; la Pi no lo usa.
"""

from __future__ import annotations

import io
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
LOGO_PNG = RAIZ / "branding" / "MECH true black.png"   # logo claro sobre negro
SORA = RAIZ / "branding" / "scripts" / "Sora.ttf"

SVG_SALIDA = RAIZ / "frontend" / "icon.svg"
ICO_SALIDA = RAIZ / "windows" / "mech.ico"
PNG_SALIDA = RAIZ / "windows" / "app" / "logo-mech.png"

FONDO = (14, 14, 18)          # #0e0e12, el fondo del logo oficial
TINTA = (240, 238, 255)       # #f0eeff, el blanco lavanda del logo
TINTA_HEX = "#f0eeff"
FONDO_HEX = "#0e0e12"

INCLINA_MARCO = math.tan(math.radians(8))   # skewX(-8) del marco
CUERPO = 60.0                               # tamaño de «MECH» dentro del marco
INCLINA_LETRA = 0.25                        # itálica sintética del navegador (~14°)


# ---------------------------------------------------------------- vector

def _trazos_mech() -> tuple[str, float]:
    """Trazo SVG de «MECH» (Sora 800, inclinada), centrado en (0, 0).

    Proporciones medidas sobre el logo oficial de branding/: cuerpo 60,
    espaciado 2, dentro del marco de 264×96. Devuelve (path d, ancho)."""
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont

    fuente = instantiateVariableFont(TTFont(SORA), {"wght": 800})
    upm = fuente["head"].unitsPerEm
    cmap = fuente.getBestCmap()
    glifos = fuente.getGlyphSet()
    cuerpo, espacio = CUERPO, 2.0
    s = cuerpo / upm
    nombres = [cmap[ord(c)] for c in "MECH"]
    anchos = [glifos[n].width * s for n in nombres]
    total = sum(anchos) + espacio * (len(nombres) - 1)
    alto_mayus = fuente["OS/2"].sCapHeight * s

    pen = SVGPathPen(glifos, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
    x = -total / 2
    base = alto_mayus / 2          # mayúsculas centradas en y = 0
    for nombre, ancho in zip(nombres, anchos):
        # Fuente -> SVG: escala, voltea Y e inclina (x' = s·x + k·s·y + x0).
        # La inclinación gira alrededor de la línea base; hacer_svg() lo
        # compensa para que quede centrada en las mayúsculas.
        k = INCLINA_LETRA
        glifos[nombre].draw(TransformPen(pen, (s, 0, k * s, -s, x, base)))
        x += ancho + espacio
    d = pen.getCommands()
    return d, total


def hacer_svg() -> None:
    d, _ = _trazos_mech()
    k = INCLINA_LETRA
    # Las letras se inclinaron alrededor de su línea base (y = alto/2): se
    # corren a la izquierda la mitad de esa inclinación para que el centro
    # óptico quede en el centro del marco, como en el logo oficial.
    from fontTools.ttLib import TTFont
    alto = TTFont(SORA)["OS/2"].sCapHeight * CUERPO / TTFont(SORA)["head"].unitsPerEm
    corre = -k * alto / 2
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <!-- Logo oficial de MECH. Generado con scripts/mklogo.py: no editar a mano. -->
  <rect width="512" height="512" rx="104" fill="{FONDO_HEX}"/>
  <g transform="translate(256,256) scale(1.62)">
    <g transform="skewX(-8)">
      <rect x="-132" y="-48" width="264" height="96" rx="22" fill="none" stroke="{TINTA_HEX}" stroke-width="11"/>
    </g>
    <path transform="translate({corre:.2f},0)" fill="{TINTA_HEX}" d="{d}"/>
  </g>
</svg>
"""
    SVG_SALIDA.write_text(svg, encoding="utf-8", newline="\n")
    print(f"{SVG_SALIDA.relative_to(RAIZ)}  ({len(svg) // 1024} KB)")


# ---------------------------------------------------------------- raster

def _logo_recortado() -> Image.Image:
    """El logo oficial como máscara (L): blanco = tinta. Recortado al borde."""
    gris = Image.open(LOGO_PNG).convert("L")
    caja = gris.point(lambda v: 255 if v > 60 else 0).getbbox()
    return gris.crop(caja)


def _sobre_fondo(mascara: Image.Image, lado: int, ancho_rel: float) -> Image.Image:
    """Pone la máscara centrada sobre un cuadrado redondeado oscuro."""
    grande = lado * 4                      # se dibuja grande y se reduce: bordes limpios
    lienzo = Image.new("RGBA", (grande, grande), (0, 0, 0, 0))
    ImageDraw.Draw(lienzo).rounded_rectangle(
        (0, 0, grande - 1, grande - 1), radius=int(grande * 0.2), fill=FONDO + (255,))
    w = int(grande * ancho_rel)
    h = round(mascara.height * w / mascara.width)
    m = mascara.resize((w, h), Image.LANCZOS)
    tinta = Image.new("RGBA", m.size, TINTA + (255,))
    lienzo.paste(tinta, ((grande - w) // 2, (grande - h) // 2), m)
    return lienzo.resize((lado, lado), Image.LANCZOS)


def _monograma() -> Image.Image:
    """La «M» con su marco inclinado, como el favicon del sitio (máscara L)."""
    lado = 1024
    capa = Image.new("L", (lado, lado), 0)
    dib = ImageDraw.Draw(capa)
    mw, mh, grosor = 740, 540, 92
    caja = ((lado - mw) // 2, (lado - mh) // 2, (lado + mw) // 2, (lado + mh) // 2)
    dib.rounded_rectangle(caja, radius=130, outline=255, width=grosor)
    # Marco inclinado 8° alrededor del centro.
    k = INCLINA_MARCO
    capa = capa.transform(capa.size, Image.AFFINE, (1, k, -k * lado / 2, 0, 1, 0),
                          resample=Image.BICUBIC)
    letra = Image.new("L", (lado, lado), 0)
    fuente = ImageFont.truetype(str(SORA), 430)
    fuente.set_variation_by_axes([800])
    ImageDraw.Draw(letra).text((lado / 2, lado / 2 + 6), "M", font=fuente, fill=255, anchor="mm")
    letra = letra.transform(letra.size, Image.AFFINE, (1, INCLINA_LETRA, -INCLINA_LETRA * lado / 2, 0, 1, 0),
                            resample=Image.BICUBIC)
    return ImageChops.lighter(capa, letra).crop(ImageChops.lighter(capa, letra).getbbox())


def hacer_png_y_ico() -> None:
    logo = _logo_recortado()

    # Logo transparente para la pantalla de búsqueda (se ve a ~200 px de ancho;
    # 3x para pantallas de alta densidad).
    w = 640
    h = round(logo.height * w / logo.width)
    m = logo.resize((w, h), Image.LANCZOS)
    png = Image.new("RGBA", m.size, TINTA + (0,))
    png.putalpha(m)
    png.save(PNG_SALIDA, optimize=True)
    print(f"{PNG_SALIDA.relative_to(RAIZ)}  ({w}x{h})")

    mono = _monograma()
    tamanos = [256, 128, 64, 48, 32, 24, 16]
    marcos = []
    for t in tamanos:
        if t >= 48:
            marcos.append(_sobre_fondo(logo, t, 0.86))
        else:
            marcos.append(_sobre_fondo(mono, t, 0.92))
    buf = io.BytesIO()
    marcos[0].save(buf, format="ICO", sizes=[(t, t) for t in tamanos], append_images=marcos[1:])
    ICO_SALIDA.write_bytes(buf.getvalue())
    print(f"{ICO_SALIDA.relative_to(RAIZ)}  ({', '.join(str(t) for t in tamanos)} px)")


def main() -> int:
    for p in (LOGO_PNG, SORA):
        if not p.exists():
            print(f"No encuentro {p}")
            return 1
    hacer_svg()
    hacer_png_y_ico()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
