# Guiones de video — Isaac Newton

Prompts listos para pegar en **Gemini (Veo)** y generar los 5 clips de la obra
`isaac_newton` de la biblioteca.

## Antes de empezar — cómo funcionan estos videos

Estos NO son como los del slot de marketing. Son videos de una **obra
cultural**, así que:

- **Van MUDOS.** El proyector los silencia por código: encima habla MECH. No
  pierdas tiempo con el audio del clip.
- **Se reproducen en BUCLE** mientras MECH narra ese segmento. La narración
  dura ~20-30 s y el clip ~8 s, así que se va a repetir 3 o 4 veces.
  → Por eso los prompts piden **movimiento lento y continuo**, sin cortes:
  un clip con un corte brusco canta muchísimo al repetirse.
- **Sin texto en pantalla.** La IA escribe letras deformes, y además el
  idioma lo pone MECH con la voz y los subtítulos.
- **Formato:** 16:9 horizontal, 1080p. Es una proyección.

## Ajustes en Gemini

| Ajuste | Valor |
|---|---|
| Relación de aspecto | **16:9** |
| Duración | la que ofrezca (~8 s está bien) |
| Personas | permitir generación de personas (hay figuras humanas) |

## Estilo común

Pega este bloque **al final de cada prompt** para que los cinco clips parezcan
del mismo documental y no cinco cosas distintas:

```
Cinematic 17th-century period film look, warm candlelight and cold window
light, deep shadows, fine dust and smoke drifting in the air, shallow depth
of field, slow continuous camera movement, no cuts, no text, no captions,
no modern objects, 16:9.
```

---

## Segmento 1 — Contexto: la era de la razón

**Qué narra MECH:** la Inglaterra del siglo XVII, la revolución científica, un
mundo que empieza a medir en vez de suponer.

```
A candlelit 17th-century study at night. Astronomical instruments, a brass
armillary sphere, open leather-bound books, quill pens and hand-drawn star
charts spread across a heavy oak table. The camera drifts very slowly across
the table as candle flames flicker and dust floats through a shaft of
moonlight from a tall leaded window. Nobody in frame.
```
*(+ bloque de estilo común)*

---

## Segmento 2 — Vida: el niño de Woolsthorpe

**Qué narra MECH:** nace en una granja de Lincolnshire, huérfano de padre antes
de nacer, criado por su abuela; un niño solitario que construye artefactos.

```
A stone farmhouse in the English countryside at dawn, low mist over green
fields and bare winter trees. Slow push-in toward a small upstairs window
with warm light inside. Cut-free. Then, inside, a boy's hands assembling a
small wooden model windmill and a sundial on a workbench by the window.
Quiet, lonely, tender mood.
```
*(+ bloque de estilo común)*

---

## Segmento 3 — El año maravilloso: la peste, la manzana, el prisma

**Qué narra MECH:** 1665, la peste cierra Cambridge, vuelve a casa y en ese
retiro forzado nacen el cálculo, la óptica y la idea de la gravitación.

```
An orchard behind a stone manor in late summer, golden afternoon light
through apple trees. A single ripe apple detaches from a branch and falls in
slow motion to the grass; the camera follows it down and holds. Then a slow
dissolve to a dim room where a glass prism on a windowsill splits a narrow
beam of sunlight into a clean rainbow spectrum across a white wall. Slow,
contemplative, no people's faces.
```
*(+ bloque de estilo común)*

---

## Segmento 4 — Los logros: los *Principia*

**Qué narra MECH:** 1687, las tres leyes del movimiento y la gravitación
universal; las mismas leyes para la manzana y para la Luna.

```
Close-up of a large open antique book on a desk, pages dense with
hand-written geometric diagrams, circles, ellipses and orbital curves drawn
in ink. The camera slowly rises from the page and the diagrams dissolve into
a vast starfield where planets trace glowing elliptical orbits around a
distant sun, seen from the darkness of space. Majestic, awe-struck,
continuous motion.
```
*(+ bloque de estilo común)*

---

## Segmento 5 — Legado: Sir Isaac Newton

**Qué narra MECH:** la Casa de la Moneda, la Royal Society, el título de
caballero, la tumba en Westminster y una física que sigue viva hoy.

```
The vast stone interior of a gothic English abbey, columns rising into
darkness, coloured light falling from a rose window onto a marble monument.
The camera glides forward very slowly down the nave toward the monument.
Silver coins catch the light on a ledge in the foreground. Solemn, reverent,
timeless.
```
*(+ bloque de estilo común)*

---

## Cómo subirlos

1. `http://mech:8000/library` (o la IP de la Pi).
2. Tarjeta **Isaac Newton** → casilla `seg01` … `seg05` en el mismo orden de
   arriba. **El orden importa**: MECH narra el segmento 1 con el video 1.
3. La obra solo se le ofrece a Claude cuando estén los **cinco**. Mientras
   falte alguno, MECH la cuenta igual pero generando imágenes con NanoBanana
   en vivo — no se rompe nada, solo se ve distinto.
4. Reiniciá el servidor después de subirlos: la lista de obras con video se
   arma al arrancar.

Si Gemini te da `.webm` o algo raro, convertilo a mp4 H.264 (estos van mudos,
así que `-an` está bien):

```bash
ffmpeg -i original.webm -c:v libx264 -crf 23 -preset slow -an seg01.mp4
```

## Si querés cambiar el guion

Los datos que MECH usa para narrar están en el campo `facts` de
`isaac_newton` en [`backend/video_library.py`](../backend/video_library.py).
Ahí hay 17 datos verificados (fechas, la disputa con Leibniz, la manzana que
**no** le cayó en la cabeza…). Si MECH dice algo falso sobre Newton, se
corrige añadiendo el dato ahí — no es un bug de código, es que el modelo no
lo tenía.
