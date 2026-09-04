# scripts/

Utilidades que NO corren en el robot: se usan desde el laptop cuando hay que
regenerar algo del frontend.

## `mkicons.py`

Genera `frontend/vendor/mech-icons.css` con **solo los iconos que usa el
panel** (42 de los 4962 del paquete Tabler): 2 KB en vez de 200 KB.

Corrélo **si añadís un icono nuevo** a `index.html` o `library.html`. Necesita
`frontend/vendor/tabler-icons.min.css` (el CSS completo del CDN, que no se
commitea). Si no está, bajalo:

```bash
curl -L -o frontend/vendor/tabler-icons.min.css \
  https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@2.47.0/tabler-icons.min.css
```

Si el script avisa de un icono **NO encontrado**, ese nombre no existe en
Tabler y en el panel se ve vacío — cambialo por uno que exista.

## `mkfonts.py`

Descarga Sora y Space Mono de Google Fonts (subsets latin y latin-ext) a
`frontend/vendor/fonts/` y genera `mech-fonts.css`. Solo hay que volver a
correrlo si se cambian las fuentes del panel.

## Por qué está todo en local

En la competencia **no se puede depender del wifi del recinto**. Antes los
iconos venían de un CDN y las fuentes de Google Fonts: sin internet, varios
botones del panel (los que son solo icono) se quedaban **en blanco**.
Comprobalo con `python -m backend.preflight`.
