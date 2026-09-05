# Sitio web de MECH

Sitio de presentación del proyecto — **multipágina, estático, sin build**.
No confundir con `frontend/`, que es el panel de control operativo del robot.

## Estructura

```
web/
  index.html          ← Inicio (hero + barra de patrocinadores)
  empresa.html        ← 01 · La empresa, equipo y colaboradores
  problema.html       ← 02 · El problema (crisis educativa, estudios)
  robot.html          ← 03 · El robot (cómo funciona, hardware, construcción)
  evolucion.html      ← 04 · MECH-1 → MECH-4
  aplicaciones.html   ← 05 · Aplicaciones y modelo de negocio
  contacto.html       ← 06 · Contacto y patrocinadores
  404.html            ← Página de error (Vercel la sirve automáticamente)
  css/styles.css      ← Toda la hoja de estilos
  js/main.js          ← Nav, menú móvil, animaciones de entrada, typing
  js/i18n.js          ← Interruptor de idioma ES/EN + diccionario completo
  site.webmanifest    ← Para instalarlo como app en el celular
  assets/             ← Imágenes
    logos/            ← Logos de patrocinadores (generados, ver abajo)
    equipo/           ← Retratos del equipo (generados, ver abajo)
    figuras/          ← Figuras del trabajo escrito (generadas, ver abajo)
  vercel.json         ← Configuración de despliegue
```

## Idioma (ES / EN)

El sitio se escribe **en español**; el inglés vive en `js/i18n.js`. El botón
`ES | EN` de la barra superior cambia todo el sitio y **recuerda la elección**
(se guarda en el navegador), así que se mantiene al pasar de página.

Para **cambiar o añadir un texto**: edita el HTML en español como siempre y
luego actualiza su pareja en el diccionario de `js/i18n.js`. La clave es el
texto en español **sin etiquetas**; el valor es el HTML en inglés (así se
conservan las negritas). Si una frase no está en el diccionario simplemente se
queda en español — nunca se rompe nada.

## Ver el sitio en local

Doble click a `index.html` funciona, pero es mejor servirlo para que las rutas
se comporten igual que en producción:

```bash
python -m http.server 8734 --directory web
```

Luego abrir <http://localhost:8734>.

## Publicar en Vercel

1. Entra a [vercel.com](https://vercel.com) e inicia sesión con GitHub.
2. **Add New → Project** y elige el repositorio `wLe0code/MECH`.
3. En la configuración del proyecto:
   - **Framework Preset:** `Other`
   - **Root Directory:** `web`  ← ⚠️ importante, si no desplegará todo el repo
   - Build Command y Output Directory: **déjalos vacíos** (es HTML estático).
4. **Deploy**. Cada `git push` a `main` vuelve a desplegar solo.

`vercel.json` ya activa `cleanUrls`, así que las direcciones quedan como
`/empresa` en vez de `/empresa.html` (los enlaces internos usan `.html` para
que también funcionen en local; Vercel los redirige a la versión limpia).

## Logos de patrocinadores

Los originales viven en `branding/patrocinadores/`. Para regenerarlos
(recorta el fondo blanco y normaliza la altura):

```bash
cd branding/scripts
python prep_logos.py
```

Eso escribe `web/assets/logos/*.png`. Para **añadir un patrocinador nuevo**:
pon su logo en `branding/patrocinadores/`, añádelo al diccionario `NAMES` del
script, ejecútalo, y agrega su `<li>` en la barra de `index.html` y
`contacto.html` (recuerda: la barra tiene **dos filas idénticas** para que el
bucle sea continuo — hay que añadirlo en las dos).

## Que se vea bien en el celular

Esto **no se configura en Vercel** — lo controla el propio sitio, y ya está
resuelto:

- La etiqueta `viewport` de cada página (con `viewport-fit=cover` para los
  celulares con notch).
- El CSS es responsive: a partir de 1024 px y de 760 px las rejillas se van
  reacomodando hasta quedar en una sola columna, y el menú pasa a hamburguesa.
- `theme-color` pinta la barra del navegador del color de la marca, y
  `site.webmanifest` permite instalarlo como app.

Verificado sin desbordes horizontales a **390 px y 360 px** en las 8 páginas.
Si en el futuro añades una tabla o una imagen ancha, mételas dentro de un
contenedor con `overflow-x:auto` (como `.table-wrap`) para no romper esto.

## Detalles de diseño

- **Barra de patrocinadores**: marquesina infinita en CSS puro
  (`animation: marquee 38s linear infinite` sobre dos filas duplicadas).
  Fondo claro a propósito, porque los logos son de tinta oscura. Se pausa al
  pasar el mouse y se detiene con `prefers-reduced-motion`.
- **Motion** siguiendo las skills de Emil Kowalski / Apple: curvas de easing
  propias, `:active { scale(.97) }` en botones, hover solo bajo
  `@media (hover:hover) and (pointer:fine)`, cascada (stagger) al entrar y
  transiciones entre páginas con la View Transitions API.
- **Accesibilidad**: enlace de "saltar al contenido", `aria-current` en la
  página activa, `aria-expanded` en el menú móvil y foco visible.
