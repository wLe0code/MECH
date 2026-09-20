"""Genera `windows/mech.ico` a partir del logo oficial de branding/.

Un .ico de Windows lleva VARIOS tamaños dentro (16, 24, 32, 48, 64, 128, 256)
y el sistema elige el que le toca: 16 en la barra de tareas, 256 en el
escritorio con iconos grandes. Si solo se mete uno, Windows lo reescala él y
se ve sucio.

El logo de branding es apaisado (4500x2000) y un icono es cuadrado, así que
aquí se recorta la parte de la marca y se centra sobre el fondo oscuro del
proyecto.

    python windows/hacer_icono.py

Solo hace falta Pillow (ya está en el entorno de desarrollo; la Pi no
necesita esto para nada).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
ORIGEN = RAIZ / "branding" / "logo-mech.jpg"
DESTINO = Path(__file__).resolve().parent / "mech.ico"

# El fondo del proyecto (mismo que el panel y el sitio).
FONDO = (14, 14, 18)
# Tamaños que Windows pide según el contexto.
TAMANOS = [16, 24, 32, 48, 64, 128, 256]


def main() -> int:
    if not ORIGEN.exists():
        print(f"No encuentro {ORIGEN}")
        return 1

    logo = Image.open(ORIGEN).convert("RGB")
    w, h = logo.size

    # Recorte cuadrado centrado: la marca vive en el centro del banner.
    lado = min(w, h)
    izq = (w - lado) // 2
    arriba = (h - lado) // 2
    cuadrado = logo.crop((izq, arriba, izq + lado, arriba + lado))

    # Un poco de aire alrededor: pegado al borde, en 16x16 el icono se
    # convierte en una mancha.
    lienzo = Image.new("RGB", (512, 512), FONDO)
    marca = cuadrado.resize((400, 400), Image.LANCZOS)
    lienzo.paste(marca, (56, 56))

    lienzo.save(DESTINO, format="ICO", sizes=[(s, s) for s in TAMANOS])
    print(f"{DESTINO}  ({', '.join(f'{s}x{s}' for s in TAMANOS)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
