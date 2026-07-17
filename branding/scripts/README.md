# Scripts de los diagramas (branding/)

Generan las figuras PNG de `branding/` a 300 dpi para el trabajo escrito
(formato IEEE: 1050 px = ancho de columna de 3.5", 2150 px = dos columnas).

## Regenerar

```bash
pip install pillow
cd branding/scripts
python diag_arquitectura.py   # → ../diagrama-arquitectura.png
python diag_flujos.py         # → ../diagrama-flujo-hardware.png y -software.png
python diag_casouso.py        # → ../diagrama-caso-uso.png
```

- `diag_base.py` — helpers compartidos: lienzo con supersampling (bordes
  suaves), cajas, flechas, chips, texto con la fuente Sora, y `draw_robot()`
  (el render de MECH-1 portado del SVG del sitio web a PIL).
- `Sora.ttf` — fuente variable oficial del proyecto (OFL, de google/fonts).
- OJO: los scripts guardan directo en `branding/` con ruta absoluta
  (`OUT = ...`). Si el repo se mueve de carpeta, actualizar esa ruta.
