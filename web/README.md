# Web de presentación de MECH

Sitio estático de presentación del proyecto (NO confundir con `frontend/`,
que es el panel de control del robot). No necesita servidor ni instalación:

## Ver el sitio

Doble click a `index.html` — se abre en el navegador y funciona completo
(animaciones, scroll estilo Apple, galería).

Si prefieres servirlo (opcional):

```bash
# desde la raíz del repo
python -m http.server 8080 --directory web
# → http://localhost:8080
```

## Fotos del robot (showcase con scroll)

La sección "El robot" (scroll estilo Apple) busca estas fotos:

| Archivo esperado | Qué es |
|---|---|
| `assets/robot-01.jpg` | Foto FRONTAL del robot terminado (fondo de sala, franja de píxeles visible) |
| `assets/robot-02.jpg` | Foto en TRES CUARTOS / lateral del robot terminado |
| `assets/robot-final.jpg` | Ya incluida (extraída del trabajo escrito) |

**Si `robot-01.jpg` o `robot-02.jpg` no existen, no se rompe nada**: el sitio
muestra automáticamente un render SVG del robot en su lugar. Para usar las
fotos reales, solo cópialas a `web/assets/` con esos nombres exactos.

## Publicar en GitHub Pages

1. En GitHub: repo → **Settings → Pages**.
2. En "Build and deployment", Source: **Deploy from a branch**.
3. Branch: `main`, Folder: `/ (root)`. Guardar.
4. El sitio quedará en `https://wle0code.github.io/MECH/web/`.

(Si se quiere la URL sin `/web/` al final, se puede añadir más adelante un
workflow de Actions que publique solo esta carpeta — pedirlo en una próxima
sesión.)

## Estructura

```
web/
  index.html      ← todo el contenido (una sola página)
  styles.css      ← estética (paleta heredada del panel de control)
  app.js          ← animaciones: scroll showcase, typing, reveals
  assets/         ← logo, favicon, fotos de construcción (del PDF), diagrama
```
