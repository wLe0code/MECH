# Guiones de video — La teoría de la relatividad

Ocho escenas que cuentan la relatividad **en el orden en que se descubrió**:
primero el problema que nadie sabía resolver, después las ideas de Einstein
(con las fórmulas de Lorentz), y al final cómo se comprobó y dónde la usamos
hoy.

Cada escena trae dos cosas:

- **Narración** — el texto que dice MECH (o la voz en off, si hacen el video
  por separado). Unas 65-75 palabras ≈ 25 segundos de voz.
- **Prompt de video** — listo para pegar en **Gemini (Veo)** y generar el clip.

| # | Título | Época | Archivo |
|---|---|---|---|
| 1 | El misterio de la luz | 1865 – 1887 | **seg01** |
| 2 | El empleado de patentes | 1895 – 1905 | **seg01** |
| 3 | El tiempo no es igual para todos | 1905 | **seg01** |
| 4 | Las transformaciones de Lorentz | 1892 – 1905 | **seg01** |
| 5 | E = mc² | 1905 | **seg02** |
| 6 | La gravedad es espacio curvo | 1907 – 1915 | **seg02** |
| 7 | El eclipse que lo cambió todo | 1919 | **seg02** |
| 8 | La relatividad hoy | 2015 – hoy | **seg02** |

## ⚠️ Son OCHO escenas pero solo DOS archivos

Gemini ahora **junta las escenas en un solo video**, y el equipo generó unas
en una cuenta y otras en otra. Así que de las ocho escenas salen **dos
archivos**:

| Archivo | Escenas | De qué va |
|---|---|---|
| `seg01.mp4` | 1 a 4 | El problema y la relatividad **especial** |
| `seg02.mp4` | 5 a 8 | **E = mc²**, la general, la prueba y el hoy |

Eso es lo que hay en la biblioteca: la obra `relatividad` tiene **2
segmentos**, no ocho. MECH narra varios tramos seguidos sobre el mismo
video, que va en bucle por debajo — exactamente lo que ya hace con las demás
obras, solo que el clip es más largo.

El corte va entre la escena 4 y la 5 a propósito: ahí termina la relatividad
**especial** (la del tiempo y el espacio) y empieza todo lo demás. Si se
reparte de otra forma, hay que cambiar el reparto en
[`backend/video_library.py`](../backend/video_library.py) también.

> **Por qué ocho escenas y no menos.** La relatividad son DOS teorías (la
> especial, de 1905, y la general, de 1915) y cada una necesita su "idea
> clave" y su "prueba". Juntarlas en cuatro obliga a narraciones de un
> minuto, y en un stand la gente no se queda un minuto mirando lo mismo.
> Ocho es justo el máximo de segmentos que admite un plan de Claude.

---

## Antes de empezar — cómo funcionan estos videos

Igual que los de [Isaac Newton](GUIONES_NEWTON.md):

- **Van MUDOS.** Encima habla MECH. No pierdas tiempo con el audio del clip.
- **Se reproducen en BUCLE** mientras MECH narra. El clip dura ~8 s y la
  narración ~25 s, así que se repite 3 veces → los prompts piden
  **movimiento lento y continuo**, sin cortes bruscos.
- **Sin texto en pantalla**, con UNA excepción: el **segmento 4** (las
  transformaciones de Lorentz), donde el equipo quiere ver las fórmulas.
  En todos los demás, ni siquiera E = mc²: la IA escribe letras y números
  deformes, y la fórmula ya la dice MECH y sale en los subtítulos.
- **Sin la cara de Einstein** (ni de ningún científico real). Gemini suele
  bloquear personas reales, y cuando no, las deforma. Los prompts lo muestran
  **de espaldas, en silueta o solo sus manos** — se entiende igual y queda
  más cinematográfico.
- **Formato:** 16:9 horizontal, 1080p. Es una proyección.

## Ajustes en Gemini

| Ajuste | Valor |
|---|---|
| Relación de aspecto | **16:9** |
| Duración | la que ofrezca (~8 s está bien) |
| Personas | permitir (hay figuras humanas, sin rostro reconocible) |

## Estilo común

Pega este bloque **al final de cada prompt** para que los ocho clips parezcan
del mismo documental:

```
Cinematic science documentary look, deep blacks, soft volumetric light,
fine glowing particles drifting in the air, shallow depth of field, slow
continuous camera movement, no cuts, no text, no letters, no numbers, no
equations, no captions, no recognizable faces, 16:9.
```

---

## Segmento 1 — El misterio de la luz (1865 – 1887)

**Narración:**

> A mediados del siglo diecinueve, James Clerk Maxwell descubrió que la luz
> es una onda electromagnética que viaja a unos trescientos mil kilómetros
> por segundo. Pero toda onda necesita algo que ondule, y los físicos
> imaginaron un medio invisible que llenaba el universo: el éter. En 1887,
> Albert Michelson y Edward Morley construyeron un aparato finísimo para
> detectarlo. No encontraron nada. La luz viajaba igual de rápido en todas
> las direcciones.

**Prompt de video:**

```
A dim 19th-century laboratory basement. A heavy square stone slab holds a
precise arrangement of brass mirrors and glass plates. A single thin beam
of warm lamplight enters, splits in two at a glass plate, travels to two
distant mirrors at right angles and returns, and where the beams meet they
form soft glowing light-and-dark interference bands. The camera circles
the apparatus very slowly. No people in frame.
```
*(+ bloque de estilo común)*

---

## Segmento 2 — El empleado de patentes (1895 – 1905)

**Narración:**

> A los dieciséis años, un estudiante llamado Albert Einstein se preguntó qué
> vería si pudiera viajar montado en un rayo de luz. Años después, sin
> conseguir trabajo en ninguna universidad, revisaba inventos en la oficina
> de patentes de Berna, en Suiza. Y en 1905, con veintiséis años y en sus
> ratos libres, publicó cuatro artículos que cambiaron la física para
> siempre. A ese año se le llama su año milagroso.

**Prompt de video:**

```
A modest office in Bern, Switzerland, in 1905. Tall window with morning
light over old city rooftops and a distant clock tower. A wooden desk
covered with technical patent drawings and handwritten pages. A young man
with dark curly hair, seen only from behind, sits writing by the window.
The camera drifts slowly past his shoulder toward the window, where the
sunlight turns into a single bright beam of light streaking across the
sky. Quiet, dreamy mood.
```
*(+ bloque de estilo común)*

---

## Segmento 3 — El tiempo no es igual para todos (1905)

**Narración:**

> Einstein partió de dos ideas. Primera: las leyes de la física son iguales
> para todos los que se mueven a velocidad constante. Segunda: la luz siempre
> viaja a la misma velocidad, la mida quien la mida. Para que las dos sean
> verdad, algo tiene que ceder, y ese algo es el tiempo. Un reloj en
> movimiento avanza más despacio, y los objetos se acortan en la dirección
> en que viajan. No es una ilusión: el tiempo mismo se estira.

**Prompt de video:**

```
An old steam-era passenger train glides at night past an empty station
platform, rendered as if time itself were slowing down. Inside a glass
carriage, a glowing pulse of light bounces up and down between two small
mirrors, leaving a luminous zigzag trail as the train moves forward. On
the platform a large antique station clock with no numbers has its
second hand moving slowly. Smooth tracking shot alongside the train.
```
*(+ bloque de estilo común)*

---

## Segmento 4 — Las transformaciones de Lorentz (1892 – 1905)

**Esta es la escena de las FÓRMULAS.** Es la única del guion en la que sí
queremos texto en pantalla.

**Narración:**

> ¿Cuánto se estira el tiempo? Lo dicen las transformaciones de Lorentz. Todo
> depende de un número, gamma, que vale uno partido por la raíz de uno menos
> ve al cuadrado sobre ce al cuadrado. A las velocidades de todos los días,
> gamma vale prácticamente uno y no se nota nada. Pero al acercarse a la
> velocidad de la luz se dispara, y el tiempo y el espacio se deforman de
> verdad. La física de siempre era solo un caso particular.

**Prompt de video:**

```
A dark green chalkboard fills the frame, lit by a warm lamp from the left,
chalk dust floating in the beam. A hand holding white chalk writes these
three lines slowly, one under the other, in clean handwriting:

gamma = 1 / sqrt(1 - v^2/c^2)

t' = gamma (t - vx/c^2)

x' = gamma (x - vt)

The camera pushes in very slowly on the finished equations as the chalk
dust drifts. Nothing else in frame.
```
*(+ bloque de estilo común, pero **QUITANDO** `no text, no letters, no
numbers, no equations` — aquí sí las queremos)*

### ⚠️ Cómo conseguir que las fórmulas salgan bien

Los modelos de video **escriben fatal**: letras torcidas, símbolos
inventados, líneas repetidas. Con un poco de cuidado sale, pero hay que
contar con varios intentos.

- **Genera varias veces y quédate con la mejor.** Es normal descartar 3 o 4.
- **Pizarra y tiza, no pantalla.** La escritura a mano perdona los defectos;
  un texto "digital" torcido canta muchísimo.
- **Nada de símbolos raros en el prompt.** Pide `sqrt(...)`, `v^2/c^2` y la
  palabra `gamma` en vez de √, ² o γ: los modelos los dibujan mucho mejor
  que los símbolos reales.
- **Tres líneas como mucho.** Cuantos más caracteres, más errores.
- **Plan B, y es el que yo recomiendo:** genera el clip de la pizarra
  **vacía** (o con la mano escribiendo garabatos) y **pon las fórmulas
  encima en la edición**, con un editor de video. Cinco minutos de trabajo y
  salen perfectas siempre. Es lo que hacen los canales de divulgación.

> Si las fórmulas salen mal y no da tiempo a rehacerlas, **no pasa nada
> grave**: la narración las dice en voz alta y salen en los subtítulos. El
> video es el acompañamiento, no la explicación.

---

## Segmento 5 — E = mc² (1905)

**Narración:**

> Pocos meses después, Einstein sacó una consecuencia asombrosa: la masa y
> la energía son lo mismo. Lo escribió en la ecuación más famosa de la
> historia: E igual a m por c al cuadrado. Como la velocidad de la luz es
> enorme, un poquito de masa guarda una energía gigantesca. Así brilla el
> Sol: cada segundo convierte unos cuatro millones de toneladas de su masa
> en luz y calor.

**Prompt de video:**

```
Extreme close-up of the surface of the Sun: boiling golden plasma,
granulation cells and slow looping solar prominences arcing into space.
The camera pulls back very slowly until the whole Sun glows against the
black of space, radiating light outward in every direction. Majestic,
powerful, continuous motion.
```
*(+ bloque de estilo común)*

---

## Segmento 6 — La gravedad es espacio curvo (1907 – 1915)

**Narración:**

> Pero su teoría no incluía la gravedad. En 1907 tuvo lo que llamó el
> pensamiento más feliz de su vida: alguien que cae libremente no siente su
> propio peso. Le llevó ocho años de trabajo, y la ayuda de su amigo
> matemático Marcel Grossmann, llegar a la conclusión: la gravedad no es una
> fuerza que tira de las cosas. Es la curvatura del espacio y del tiempo.
> La presentó en noviembre de 1915: la relatividad general.

**Prompt de video:**

```
Deep space visualized as a vast, faintly glowing blue grid stretching to
the horizon. A massive radiant golden sphere slowly sinks into the grid,
bending it into a deep smooth well. Smaller glowing spheres roll along
the curved grid and fall into graceful orbits around it. The camera
glides slowly over the curved grid. Elegant, calm, hypnotic.
```
*(+ bloque de estilo común)*

---

## Segmento 7 — El eclipse que lo cambió todo (1919)

**Narración:**

> Si el espacio se curva, la luz de las estrellas debería torcerse al pasar
> junto al Sol. Solo se podía comprobar durante un eclipse total. El
> veintinueve de mayo de 1919, dos expediciones británicas, una en la isla de
> Príncipe, en África, y otra en Sobral, en Brasil, fotografiaron las
> estrellas alrededor del Sol eclipsado. La desviación coincidía con lo que
> Einstein había calculado. De la noche a la mañana, se volvió el científico
> más famoso del mundo.

**Prompt de video:**

```
A total solar eclipse over a tropical island in 1919: the black disk of
the Moon surrounded by the white glowing corona, a few stars visible in
the darkened sky, palm trees silhouetted below. In the foreground, an
early 20th-century brass telescope on a wooden mount points at the
eclipse, and a figure in period clothes, seen from behind, slides a glass
photographic plate into it. Slow push-in toward the corona. Awe-struck,
historic mood.
```
*(+ bloque de estilo común)*

---

## Segmento 8 — La relatividad hoy (2015 – hoy)

**Narración:**

> Hoy la relatividad está en tu bolsillo. Los relojes de los satélites GPS se
> adelantan unos treinta y ocho microsegundos al día; sin corregirlo, el mapa
> de tu teléfono se equivocaría varios kilómetros cada día. En 2015
> detectamos por primera vez las ondas gravitacionales que Einstein predijo,
> y en 2019 vimos la primera imagen de un agujero negro. Más de un siglo
> después, su idea sigue superando cada prueba.

**Prompt de video:**

```
The night side of planet Earth seen from orbit, city lights glowing, with
several small satellites drifting in slow orbit and faint signal pulses
reaching down to the surface. The camera drifts away from Earth into deep
space, where two black holes spiral around each other and send gentle
glowing ripples through space, and a glowing orange ring of light
surrounds a dark center. Slow, continuous, awe-inspiring.
```
*(+ bloque de estilo común)*

---

## Datos verificados

Si se añade la obra a la biblioteca de MECH, estos van al campo `facts` en
[`backend/video_library.py`](../backend/video_library.py), igual que los de
Newton. Así MECH no inventa fechas ni atribuye cosas a quien no toca.

1. **James Clerk Maxwell** publicó su teoría del campo electromagnético en
   1865; de ella se deduce que la luz es una onda electromagnética que viaja
   a unos 300 000 km/s.
2. El **experimento de Michelson y Morley** (1887, Cleveland, Estados Unidos)
   buscaba el movimiento de la Tierra a través del éter y no lo encontró: es
   el "resultado nulo" más famoso de la historia de la física.
3. **Hendrik Lorentz** y **Henri Poincaré** ya habían desarrollado parte de
   las matemáticas de la relatividad especial (las transformaciones de
   Lorentz). Lo nuevo de Einstein fue la interpretación: el tiempo y el
   espacio mismos son relativos, y el éter sobra.
3.bis Las **transformaciones de Lorentz** relacionan lo que miden dos
   observadores que se mueven uno respecto al otro. Todo gira alrededor del
   **factor de Lorentz**, gamma = 1 / raíz(1 − v²/c²). A velocidades
   normales gamma es prácticamente 1 (por eso no notamos nada); cuando v se
   acerca a c, gamma se dispara. Lorentz las publicó en su forma moderna en
   1904, y Einstein las dedujo en 1905 partiendo de sus dos postulados en
   vez de suponer el éter. El nombre "transformación de Lorentz" se lo puso
   **Poincaré**.
3.ter De gamma salen las dos consecuencias famosas: la **dilatación del
   tiempo** (un reloj en movimiento va más lento, t = gamma·t₀) y la
   **contracción de la longitud** (un objeto en movimiento se acorta en la
   dirección del viaje, L = L₀/gamma). Las ecuaciones de Newton son el caso
   particular de estas cuando v es mucho menor que c.
4. **Albert Einstein** nació el 14 de marzo de 1879 en Ulm, Alemania, y murió
   el 18 de abril de 1955 en Princeton, Estados Unidos.
5. La pregunta de **perseguir un rayo de luz** se la hizo hacia los 16 años,
   estudiando en Aarau, Suiza. Él mismo la contó después.
6. Trabajó en la **Oficina de Patentes de Berna** desde 1902 como experto
   técnico de tercera clase. Allí escribió los artículos de 1905.
7. **1905, su "año milagroso"**: cuatro artículos — el efecto fotoeléctrico,
   el movimiento browniano, la relatividad especial ("Sobre la
   electrodinámica de los cuerpos en movimiento") y el de la equivalencia
   entre masa y energía, de donde sale **E = mc²**.
8. El **Premio Nobel de Física de 1921** (entregado en 1922) se lo dieron por
   el efecto fotoeléctrico, **no por la relatividad**.
9. **Hermann Minkowski**, que había sido profesor de Einstein, propuso en 1908
   unir espacio y tiempo en una sola cosa: el **espacio-tiempo**.
10. El **"pensamiento más feliz de su vida"** (1907): una persona en caída
    libre no siente su propio peso. De ahí sale el principio de equivalencia
    entre gravedad y aceleración.
11. Su amigo el matemático **Marcel Grossmann** le enseñó la geometría de
    Riemann, la herramienta que necesitaba para describir espacio curvo.
    Publicaron juntos un primer intento en 1913.
12. Las ecuaciones finales de la **relatividad general** las presentó ante la
    Academia Prusiana de Ciencias en **noviembre de 1915**. El matemático
    **David Hilbert** trabajaba en lo mismo al mismo tiempo.
13. Con la relatividad general explicó por fin una anomalía en la órbita de
    **Mercurio** que Newton no podía explicar (un desvío de unos 43 segundos
    de arco por siglo).
14. En 1916, **Karl Schwarzschild**, mientras servía en el frente de la
    Primera Guerra Mundial, encontró la primera solución exacta de las
    ecuaciones: la que describe lo que hoy llamamos un agujero negro.
15. **Eclipse del 29 de mayo de 1919**: una expedición dirigida por **Arthur
    Eddington** fue a la isla de Príncipe (frente a África) y otra a Sobral
    (Brasil). Los resultados se anunciaron en Londres el 6 de noviembre de
    1919 y convirtieron a Einstein en una celebridad mundial.
16. **GPS**: los relojes de los satélites se adelantan unos 38 microsegundos
    al día respecto a los de la Tierra (la relatividad general los adelanta
    y la especial los atrasa un poco). Sin corregirlo, el error de posición
    crecería varios kilómetros por día.
17. **Ondas gravitacionales**: Einstein las predijo en 1916. El
    observatorio **LIGO** las detectó por primera vez el 14 de septiembre de
    2015 (se anunció en febrero de 2016), producidas por la fusión de dos
    agujeros negros. Premio Nobel de Física 2017.
18. **Primera imagen de un agujero negro**: el del centro de la galaxia M87,
    publicada el 10 de abril de 2019 por el Event Horizon Telescope.
19. ⚠️ **Mileva Marić**, compañera de estudios y primera esposa de Einstein,
    se menciona a veces como coautora de la relatividad. Es un debate
    histórico **sin pruebas concluyentes**: si alguien pregunta, MECH debe
    decir que se discute, no afirmarlo ni negarlo.

## Cómo subirlos

La obra `relatividad` **ya está en la biblioteca** con sus **dos** espacios.

1. `http://mech:8000/library` (o la IP de la Pi).
2. Tarjeta **La teoría de la relatividad** → dos casillas:
   - **`seg01`** = el video con las escenas **1 a 4** (el problema y la
     relatividad especial, incluidas las fórmulas de Lorentz).
   - **`seg02`** = el video con las escenas **5 a 8** (E = mc², la general,
     el eclipse y el hoy).
   **El orden importa**: MECH narra la primera mitad sobre `seg01`.
3. La obra se le ofrece a Claude solo cuando estén **los dos**. Mientras
   falte uno, MECH la cuenta igual pero generando imágenes en vivo — no se
   rompe nada, solo se ve distinto.
4. Reinicia el servidor después de subirlos: la lista de obras con video se
   arma al arrancar.

Si Gemini da `.webm` o algo raro, conviértelo a mp4 H.264 (van mudos, así que
`-an` está bien):

```bash
ffmpeg -i original.webm -c:v libx264 -crf 23 -preset slow -an seg01.mp4
```

## Si hacen el video por separado (fuera de MECH)

Las ocho narraciones leídas seguidas son un video de ~3 minutos y medio, u
ocho cortos de ~25 s para redes. En ese caso sí conviene **extender cada clip** a
la duración de su narración (o encadenar dos generaciones del mismo prompt)
en vez de dejarlo en bucle, y ahí se pueden añadir las fórmulas como
texto en la edición — con un editor, no pidiéndosela a la IA.
