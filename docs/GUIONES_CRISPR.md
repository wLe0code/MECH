# Guiones de video — CRISPR y Cas9

Cinco escenas que cuentan CRISPR **en el orden en que se descubrió**: primero
un misterio en el ADN de unas bacterias, después la herramienta que salió de
ahí, cómo funciona, qué ya se cura con ella y la gran pregunta ética que
abre.

Cada escena trae dos cosas:

- **Narración** — el texto que dice MECH (o la voz en off, si hacen el video
  por separado). Unas 65-75 palabras ≈ 25 segundos de voz.
- **Prompt de video** — listo para pegar en **Gemini (Veo)** y generar el clip.

| # | Título | Época | Archivo |
|---|---|---|---|
| 1 | Un misterio en el ADN de las bacterias | 1987 – 2007 | `seg01.mp4` |
| 2 | Las tijeras genéticas | 2011 – 2012 | `seg02.mp4` |
| 3 | Cómo funciona | — | `seg03.mp4` |
| 4 | Del laboratorio al hospital | 2013 – 2023 | `seg04.mp4` |
| 5 | Reescribir la vida: la gran pregunta | 2018 – hoy | `seg05.mp4` |

> ⚠️ **Todavía NO hay espacio `crispr` en la biblioteca de videos.** Cuando
> estén los clips, hay que añadir la obra a `backend/video_library.py` (con 5
> segmentos y los datos verificados de abajo) para que aparezca su tarjeta en
> `/library`.

---

## Antes de empezar — cómo funcionan estos videos

Igual que los de [Isaac Newton](GUIONES_NEWTON.md) y los de la
[relatividad](GUIONES_RELATIVIDAD.md):

- **Van MUDOS.** Encima habla MECH. No pierdas tiempo con el audio del clip.
- **Se reproducen en BUCLE** mientras MECH narra. El clip dura ~8 s y la
  narración ~25 s, así que se repite 3 veces → los prompts piden
  **movimiento lento y continuo**, sin cortes bruscos.
- **Sin texto en pantalla**, y tampoco letras sobre el ADN (A, T, C, G): la
  IA las escribe deformes. Las "letras" las dice MECH y salen en los
  subtítulos.
- **Sin caras de científicos reales** (ni Doudna, ni Charpentier, ni nadie).
  Gemini suele bloquear personas reales, y cuando no, las deforma. Los
  prompts muestran **manos, siluetas o gente de espaldas**.
- **Nada de sangre ni de agujas en primer plano** (escena 4): en un stand hay
  niños. El hospital se cuenta con luz y esperanza, no con quirófano.
- **Formato:** 16:9 horizontal, 1080p. Es una proyección.

## Ajustes en Gemini

| Ajuste | Valor |
|---|---|
| Relación de aspecto | **16:9** |
| Duración | la que ofrezca (~8 s está bien) |
| Personas | permitir (hay figuras humanas, sin rostro reconocible) |

## Estilo común

Pega este bloque **al final de cada prompt** para que los cinco clips parezcan
del mismo documental:

```
Cinematic science documentary look, microscopic world rendered as a vast
glowing landscape, deep blues and teals with warm amber highlights, soft
volumetric light, fine floating particles, shallow depth of field, slow
continuous camera movement, no cuts, no text, no letters, no numbers, no
captions, no recognizable faces, 16:9.
```

---

## Segmento 1 — Un misterio en el ADN de las bacterias (1987 – 2007)

**Narración:**

> En 1987, un grupo de científicos japoneses encontró algo raro en el ADN de
> una bacteria: el mismo trocito repetido una y otra vez, con pedazos
> distintos en medio. Nadie sabía para qué servía. En España, Francisco
> Mojica estudió esas repeticiones durante años en microbios de unas salinas
> de Alicante, y en 2005 descubrió el secreto: los pedazos del medio eran
> restos de virus. Las bacterias guardaban una memoria de sus enemigos. Era
> un sistema inmune.

**Prompt de video:**

```
Inside the microscopic world of a single rod-shaped bacterium drifting in
dark water. The camera glides slowly through its translucent membrane into
the interior, where a long glowing strand of DNA coils gently. Along the
strand, identical short segments light up one after another in a regular
repeating pattern, with differently colored segments between them, like a
string of beads. Small spiky virus particles float silently outside the
cell. Mysterious, patient, discovery mood.
```
*(+ bloque de estilo común)*

---

## Segmento 2 — Las tijeras genéticas (2011 – 2012)

**Narración:**

> Esa memoria funciona con una proteína llamada Cas nueve: cuando un virus
> vuelve, la bacteria reconoce su ADN y lo corta. En 2011, la francesa
> Emmanuelle Charpentier y la estadounidense Jennifer Doudna se conocieron en
> un congreso en Puerto Rico y decidieron trabajar juntas. En 2012 publicaron
> la idea que lo cambió todo: si le cambias la guía a Cas nueve, puede
> cortar el ADN exactamente donde tú quieras. Habían convertido una defensa
> de bacterias en unas tijeras genéticas.

**Prompt de video:**

```
A quiet modern research laboratory at night, lit by the cool glow of a
microscope screen. Two scientists in white lab coats, seen only from
behind as silhouettes, lean together over the screen. The camera slowly
pushes past their shoulders into the screen, and the image becomes a
microscopic scene: a large translucent protein shaped like a clamp, glowing
soft amber, holding a short luminous thread and closing gently around a
long DNA double helix, which parts cleanly in two. Awe, breakthrough mood.
```
*(+ bloque de estilo común)*

---

## Segmento 3 — Cómo funciona

**Narración:**

> Funciona como buscar una palabra en un libro gigante. Cas nueve lleva
> consigo una guía: una pequeña cadena de unas veinte letras genéticas.
> Recorre el ADN hasta encontrar la secuencia que encaja exactamente con
> esa guía, y ahí corta las dos hebras. Luego la célula repara el corte. A
> veces, al repararlo, el gen queda apagado. Y si le damos una copia
> corregida, la célula puede usarla como molde para arreglar el error.

**Prompt de video:**

```
An enormous DNA double helix stretches like a glowing bridge through dark
space. A small translucent amber protein carrying a short glowing thread
travels slowly along the helix, scanning it. It stops at one exact spot
where the thread matches and locks in place with a soft pulse of light,
the two strands separate cleanly, and then tiny particles of light gently
knit the helix back together, repaired and seamless. Smooth, precise,
calm, continuous motion.
```
*(+ bloque de estilo común)*

---

## Segmento 4 — Del laboratorio al hospital (2013 – 2023)

**Narración:**

> En 2013 ya se estaban editando células humanas en el laboratorio. En 2019,
> Victoria Gray, una mujer de Mississippi con anemia falciforme, fue la
> primera paciente de Estados Unidos tratada con CRISPR, y su enfermedad
> dejó de darle crisis. En 2020, Charpentier y Doudna ganaron el Premio
> Nobel de Química. Y a finales de 2023, el Reino Unido y Estados Unidos
> aprobaron el primer tratamiento con CRISPR para esa anemia. La tijera ya
> estaba curando.

**Prompt de video:**

```
Microscopic view of red blood cells flowing through a blood vessel. At
first some cells are stiff, crescent-shaped and tangled, blocking the flow.
Slowly, a warm golden light spreads through the stream and the cells
become round, smooth disc shapes that glide freely and evenly. The camera
then rises out of the vessel and dissolves into a bright hospital window
at sunrise, soft warm light pouring into a calm empty room with a plant on
the sill. Hopeful, gentle, healing mood. No needles, no blood outside the
vessel, no faces.
```
*(+ bloque de estilo común)*

---

## Segmento 5 — Reescribir la vida: la gran pregunta (2018 – hoy)

**Narración:**

> Pero una herramienta tan poderosa también asusta. En 2018, un científico
> en China anunció el nacimiento de dos gemelas con el ADN editado antes de
> nacer. El mundo entero lo condenó y terminó en prisión, porque esos
> cambios pasarían a sus hijos y a sus nietos. Hoy CRISPR se usa para curar
> enfermedades, crear cultivos más resistentes y entender la vida. La gran
> pregunta ya no es si podemos reescribir el ADN, sino cuándo debemos
> hacerlo.

**Prompt de video:**

```
A vast dark space with a single giant DNA double helix slowly rotating,
glowing softly. As the camera circles it, the helix branches into a
luminous tree of many smaller helices spreading outward like generations
of a family tree, some glowing warm gold and others cool blue. The camera
pulls back slowly until the whole tree of light is seen floating in the
darkness, delicate and immense. Reflective, thoughtful, slightly uneasy
but hopeful mood.
```
*(+ bloque de estilo común)*

---

## Datos verificados

Para el campo `facts` de la obra cuando se añada a la biblioteca. Son los
que MECH puede afirmar sin miedo — y las trampas que NO debe decir.

1. **CRISPR** son las siglas en inglés de *Clustered Regularly Interspaced
   Short Palindromic Repeats*: repeticiones palindrómicas cortas agrupadas y
   regularmente espaciadas. **Cas** significa "asociada a CRISPR" (*CRISPR
   associated*): son las proteínas que trabajan con esas repeticiones.
2. **1987**: el equipo de **Yoshizumi Ishino**, en la Universidad de Osaka
   (Japón), describió por primera vez esas repeticiones raras en el ADN de la
   bacteria *Escherichia coli*. No supieron para qué servían.
3. **Francisco Mojica**, de la **Universidad de Alicante** (España), estudió
   esas repeticiones desde 1993 en arqueas (*Haloferax mediterranei*) de las
   **salinas de Santa Pola**. El nombre CRISPR lo acordaron Mojica y el
   holandés Ruud Jansen, y se publicó por primera vez en **2002**.
4. **2005**: Mojica publicó que los fragmentos entre las repeticiones
   (los "espaciadores") coinciden con ADN de virus, y propuso que son una
   **memoria inmunitaria** de las bacterias. Otros dos grupos llegaron a la
   misma idea ese año.
5. **2007**: **Rodolphe Barrangou** y **Philippe Horvath**, de la empresa
   Danisco, demostraron con *Streptococcus thermophilus* —la bacteria que se
   usa para hacer yogur y queso— que CRISPR la protege de verdad contra los
   virus.
6. **2011**: el grupo de **Emmanuelle Charpentier** (francesa) describió el
   ARN llamado tracrRNA, una pieza clave del sistema. Ese mismo año
   Charpentier y **Jennifer Doudna** (estadounidense, Universidad de
   California en Berkeley) se conocieron en un congreso en **Puerto Rico**.
7. **Junio de 2012**: Doudna, Charpentier y su equipo (primer autor: Martin
   Jinek) publicaron en la revista *Science* que **Cas9 se puede programar**
   con un ARN guía para cortar el ADN en el sitio que uno elija, y que los
   dos ARN naturales se pueden unir en una sola guía.
8. La Cas9 más usada viene de la bacteria ***Streptococcus pyogenes***. La
   guía lleva unas **20 letras** (nucleótidos) que buscan su pareja en el
   ADN. Cas9 además necesita una señal corta al lado del objetivo (llamada
   PAM) y **corta las dos hebras** del ADN.
9. Después del corte, la célula repara el ADN. Si lo repara "a lo rápido",
   suele meter pequeños errores y **el gen queda apagado**. Si se le da una
   **copia corregida como molde**, puede usarla para **arreglar** el gen.
10. **Enero de 2013**: los equipos de **Feng Zhang** (Instituto Broad) y
    **George Church** (Harvard) publicaron edición con CRISPR en **células
    humanas**. Hubo una larga disputa de patentes entre la Universidad de
    California y el Instituto Broad.
11. **7 de octubre de 2020**: **Premio Nobel de Química** para Emmanuelle
    Charpentier y Jennifer Doudna "por el desarrollo de un método para la
    edición del genoma". Fue la **primera vez que dos mujeres compartían,
    solas, un Nobel de ciencias**. El comité lo llamó "las tijeras genéticas".
12. **Julio de 2019**: **Victoria Gray**, de Mississippi, fue la **primera
    persona de Estados Unidos** tratada con CRISPR para la **anemia
    falciforme**, dentro de un ensayo clínico.
13. **Casgevy** (exa-cel, de Vertex y CRISPR Therapeutics) es el **primer
    tratamiento con CRISPR aprobado**: el Reino Unido lo autorizó el **16 de
    noviembre de 2023** y la FDA de Estados Unidos el **8 de diciembre de
    2023**, para la anemia falciforme (y después también para la
    beta-talasemia). Se extraen células madre de la sangre del paciente, se
    editan en el laboratorio y se le devuelven.
14. **Noviembre de 2018**: el científico chino **He Jiankui** anunció el
    nacimiento de dos gemelas con el gen CCR5 editado antes de nacer, para
    intentar protegerlas del VIH. Lo condenó la comunidad científica
    mundial, y en **diciembre de 2019** un tribunal chino lo sentenció a
    **tres años de cárcel**.
15. La diferencia clave de la ética: editar células del **cuerpo** de un
    paciente (no se hereda) **no es lo mismo** que editar **embriones** o
    células reproductoras (se hereda a los hijos). Lo segundo está prohibido
    o muy restringido en muchos países.
16. Después de Cas9 llegaron versiones más finas creadas en el laboratorio
    de **David Liu** (Instituto Broad): la **edición de bases** (2016), que
    cambia una sola letra sin cortar las dos hebras, y la **edición prime**
    (2019).
17. ⚠️ **No decir** que Mojica ganó el Nobel (no lo ganó, aunque su trabajo
    fue fundamental) ni que CRISPR "cura cualquier enfermedad genética": hoy
    hay un tratamiento aprobado y muchos ensayos en marcha.
18. ⚠️ **No decir** que Doudna y Charpentier "inventaron CRISPR": CRISPR
    existe en las bacterias desde hace miles de millones de años. Lo que
    ellas hicieron fue convertirlo en una **herramienta programable**.

**Fuentes:**

- https://www.nobelprize.org/prizes/chemistry/2020/press-release/
- https://www.science.org/doi/10.1126/science.1225829 (Jinek et al., 2012)
- https://www.science.org/doi/10.1126/science.1138140 (Barrangou et al., 2007)
- https://en.wikipedia.org/wiki/Francisco_Mojica
- https://en.wikipedia.org/wiki/CRISPR
- https://www.fda.gov/news-events/press-announcements/fda-approves-first-gene-therapies-treat-patients-sickle-cell-disease
- https://www.gov.uk/government/news/mhra-authorises-world-first-gene-therapy-that-aims-to-cure-sickle-cell-disease-and-transfusion-dependent-thalassemia
- https://en.wikipedia.org/wiki/He_Jiankui_affair

## Cómo subirlos

1. Primero hay que **añadir la obra `crispr`** a la biblioteca (ver el aviso
   del principio). Hasta entonces no hay dónde subirlos.
2. `http://mech:8000/library` (o la IP de la Pi, o el botón «Biblioteca de
   videos» de la app de Windows).
3. Tarjeta **CRISPR y Cas9** → la escena 1 en **`seg01`**, la 2 en
   **`seg02`**... hasta la 5 en **`seg05`**. **El orden importa**: MECH narra
   el tramo N sobre el video N.
4. La obra se le ofrece a Claude con video solo cuando estén **los cinco**.
   Mientras falte uno, MECH la cuenta igual pero generando imágenes en vivo.
5. Reinicia el servidor después de subirlos: la lista de obras con video se
   arma al arrancar.

Si Gemini da `.webm` o algo raro, conviértelo a mp4 H.264 (van mudos, así que
`-an` está bien):

```bash
ffmpeg -i original.webm -c:v libx264 -crf 23 -preset slow -an seg01.mp4
```

## Si hacen el video por separado (fuera de MECH)

Las cinco narraciones leídas seguidas son un video de ~2 minutos, o cinco
cortos de ~25 s para redes. En ese caso sí conviene **extender cada clip** a
la duración de su narración (o encadenar dos generaciones del mismo prompt)
en vez de dejarlo en bucle, y los nombres y fechas se pueden poner como texto
en la edición — con un editor, no pidiéndoselos a la IA.
