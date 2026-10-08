# Cómo se usa MECH

Guía del **operador del stand**: qué decirle a MECH, qué hace con cada cosa y
qué hacer cuando no responde. No hace falta saber programar ni tocar la
terminal.

Para montarlo y configurarlo, ver [`GUIA.md`](GUIA.md). Para el panel de
control por dentro, [`FRONTEND.md`](FRONTEND.md).

---

## 1. Encender

En el escritorio de la Raspberry Pi hay **tres iconos**. Se usan en este
orden:

| Icono | Qué hace |
|---|---|
| 🟢 **Iniciar MECH** | Descarga lo último de GitHub, arranca el servidor y abre el panel de control. Arranca igual si no hay internet. |
| 📽️ **Proyectar MECH** | Abre la proyección a pantalla completa. |
| 🔴 **Apagar MECH** | Cierra todo con cuidado. |

Cuando MECH está listo suena un **tono corto**. A partir de ahí ya escucha.

> Si los iconos no están, se instalan **una sola vez** con doble click en
> `pi/instalar-accesos.sh`. Ver [`../pi/README.md`](../pi/README.md).

### Desde una laptop Windows

**La app «MECH».** Se instala **una sola vez** en cada laptop, sin instalar
nada más (ni Python ni programas): en la carpeta `windows` del proyecto,
doble clic en **`Instalar MECH.bat`**. Deja un icono **MECH** en el
Escritorio y en el menú Inicio.

Al abrir ese icono:

1. Sale una ventana propia que **busca al robot sola** («Buscando a MECH…»).
2. Cuando lo encuentra, entra al panel de control. La siguiente vez va
   directo: recuerda dónde estaba.
3. Si no lo encuentra, lo dice y enseña qué revisar: que MECH esté encendido
   (icono «Iniciar MECH» en la Pi), que la laptop y el robot estén en la
   **misma wifi**, y un campo para escribir la dirección a mano (por ejemplo
   `192.168.1.42`). **Sigue buscando sola**: se puede abrir la app primero y
   encender el robot después.

Dentro del panel, el menú de la izquierda tiene además **Biblioteca** (subir
los videos, §7) y **Proyección** (por si se proyecta desde la laptop); las
dos se abren en otra ventana. Abajo del todo, **Atajos y frases**.

Si se pierde la conexión con el robot sale un aviso abajo («Sin conexión con
MECH») con el botón **Buscar de nuevo**, que vuelve a la pantalla de búsqueda.

Para quitarla: `Quitar MECH.bat`, en la misma carpeta. Más detalles (y la
versión antigua, `MECH Panel.exe`) en
[`../windows/README.md`](../windows/README.md).

---

## 2. Lo básico: despertarlo y dormirlo

MECH está siempre escuchando, pero **en reposo no responde a nada** salvo a
su frase de despertar. Así no gasta créditos ni se mete en conversaciones
ajenas.

```
«ok MECH»               → despierta (responde: «Hola, ya te escucho»)
                          … suena un tono: ahí es cuando hay que hablar …
«para de escuchar»      → vuelve a reposo («De acuerdo, hasta luego»)
```

**El idioma lo decide la frase con la que se le despierta**, y se queda en
ese idioma hasta que se duerma:

| Frase | Idioma |
|---|---|
| «ok MECH» · «despierta MECH» | 🇪🇸 español |
| «wake up MECH» | 🇬🇧 inglés |
| «bonjour MECH» · «salut MECH» · «réveille MECH» | 🇫🇷 francés |
| «bom dia MECH» · «boa tarde MECH» · «acorda MECH» | 🇵🇹 portugués |
| «guten Tag MECH» · «guten Morgen MECH» · «wach auf MECH» | 🇩🇪 alemán |
| «ciao MECH» · «buongiorno MECH» · «svegliati MECH» | 🇮🇹 italiano |
| «こんにちは MECH» (*konnichiwa*) · «起きて MECH» (*okite*) | 🇯🇵 japonés |
| «привет MECH» (*privet*) · «проснись MECH» (*prosnís*) | 🇷🇺 ruso |
| «你好 MECH» (*nǐ hǎo*) · «醒醒 MECH» (*xǐng xing*) | 🇨🇳 mandarín |
| «안녕 MECH» (*annyeong*) · «일어나 MECH» (*ireona*) | 🇰🇷 coreano |

Al dormirse **vuelve solo a español**, listo para el siguiente visitante.

> ⚠️ Esto es a propósito: si alguien le habla en francés a un MECH despierto
> en español, MECH entiende mal. Hay que **dormirlo y despertarlo** en el
> otro idioma: despierto, la frase de despertar de otro idioma ya **no** lo
> cambia (antes sí).
> Para probar sin hablar: panel → vista **Voz** → botón **IDIOMA** (muestra
> el idioma en el que está MECH; al pulsarlo salen los diez, cada uno con la
> frase que lo despierta). Al lado se ven siempre las dos frases del idioma
> activo: la que lo despierta y la que lo corta.

### Cada comando, en el idioma en que despertó

Desde octubre de 2026 los comandos **solo funcionan en el idioma con el que
se despertó a MECH**. Despierto con «wake up MECH», «oye MECH» no hace nada:
hay que decir «hey MECH». Y al revés.

| Despertó con | Cortarlo al narrar | Dormirlo | Girar | Volver |
|---|---|---|---|---|
| 🇪🇸 «ok MECH» | «oye MECH» | «para de escuchar» | «mira hacia afuera» | «regresa a proyectar» |
| 🇬🇧 «wake up MECH» | «hey MECH» | «stop listening» | «look outside» | «back to projecting» |
| 🇫🇷 «bonjour MECH» | «pardon MECH» | «au revoir MECH» | «regarde dehors» | «retourne projeter» |
| 🇵🇹 «bom dia MECH» | «escuta MECH» | «boa noite MECH» | «olha para fora» | «volta a projetar» |
| 🇩🇪 «guten Tag MECH» | «warte MECH» | «gute Nacht MECH» | «schau raus» | «zurück zur Projektion» |
| 🇮🇹 «ciao MECH» | «scusa MECH» | «buonanotte MECH» | «guarda fuori» | «torna a proiettare» |
| 🇯🇵 «こんにちは MECH» | «ねえ MECH» (*nee*) | «おやすみ MECH» (*oyasumi*) | «外を見て» (*soto o mite*) | «投影に戻って» (*tōei ni modotte*) |
| 🇷🇺 «привет MECH» | «эй MECH» (*ey*) | «спокойной ночи MECH» (*spokóynoy nochi*) | «посмотри наружу» (*posmotrí narúzhu*) | «вернись к проекции» (*vernís k proyéktsii*) |
| 🇨🇳 «你好 MECH» | «嘿 MECH» (*hēi*) | «晚安 MECH» (*wǎn'ān*) | «向外看» (*xiàng wài kàn*) | «回去投影» (*huíqù tóuyǐng*) |
| 🇰🇷 «안녕 MECH» | «저기 MECH» (*jeogi*) | «잘 자 MECH» (*jal ja*) | «밖을 봐» (*bakkeul bwa*) | «투영으로 돌아가» (*tuyeong-euro doraga*) |

| Despertó en | Marketing | Traducir | Trivia |
|---|---|---|---|
| 🇪🇸 español | «proyecta marketing» | «traduce MECH» | «juguemos una trivia» |
| 🇬🇧 inglés | «play marketing» | «translate MECH» | «quiz me» |
| 🇫🇷 francés | «lance le marketing» | «traduis MECH» | «jouons au quiz» |
| 🇵🇹 portugués | «toca marketing» | «traduz MECH» | «vamos jogar o quiz» |
| 🇩🇪 alemán | «zeig Marketing» | «übersetze MECH» | «Quiz spielen» |
| 🇮🇹 italiano | «mostra marketing» | «traduci MECH» | «facciamo un quiz» |
| 🇯🇵 japonés | «マーケティングを再生して» | «翻訳して MECH» | «クイズをしよう» |
| 🇷🇺 ruso | «покажи маркетинг» | «переведи MECH» | «сыграем в викторину» |
| 🇨🇳 mandarín | «播放宣传片» | «翻译 MECH» | «玩问答» |
| 🇰🇷 coreano | «마케팅 재생» (*maketing jaesaeng*) | «번역해 MECH» (*beonyeokhae*) | «퀴즈 하자» (*kwijeu haja*) |

Vale también para el «sí» / «no» de la trivia. Las listas completas (hay
varias formas de decir cada cosa) están en `backend/config.py`
(`VOICE_*_PHRASES`, con un sufijo por idioma: `_EN`, `_FR`, `_PT`, `_DE`,
`_IT`, `_JA`, `_RU`, `_ZH`, `_KO`).

> Hay palabras casi iguales entre idiomas que siguen valiendo en los dos:
> «ok», «no», «avanza» / «avance» / «avança», «traduce» / «traduz» /
> «traduci», «perdón» / «pardon». Es el mismo sonido; no es un fallo.

> Si MECH despertó en un idioma por error y nadie sabe dormirlo en ese
> idioma: panel → vista **Voz** → botón **IDIOMA** → **Español**. Queda en
> español y ya se le puede decir «para de escuchar».
> Para volver a lo de antes (todos los idiomas a la vez): Ajustes →
> **«Idioma de los comandos»**, apagado.

### Para dormirlo

«para de escuchar», «deja de escuchar», «duérmete MECH», «descansa MECH»,
«modo reposo». Despierto en otro idioma, con la frase de ese idioma (tabla
de arriba).

En los demás idiomas: «gute Nacht MECH» (alemán), «buonanotte MECH»
(italiano), «おやすみ MECH» (*oyasumi*, japonés), «спокойной ночи MECH»
(*spokóynoy nochi*, ruso), «晚安 MECH» (*wǎn'ān*, mandarín), «잘 자 MECH»
(*jal ja*, coreano). Y siempre vale apagarlo desde el panel.

### Alemán, italiano, japonés, ruso, mandarín y coreano: lo que hay que saber

Se añadieron en octubre de 2026 (el coreano, el décimo, el día 6) y
**todavía no se han probado con el micrófono de verdad** (sí con texto, ver
abajo). Tres cosas que no pasan con los otros idiomas:

1. **En alemán NO es «hallo MECH».** Suena casi igual que «hello MECH», y un
   visitante que saludara en inglés despertaría a MECH en alemán. Se usa
   «guten Tag MECH».
2. **En japonés, ruso, chino y coreano, MECH puede no reconocer su nombre.**
   El programa que transcribe la voz lo escribe como le suena («メック»,
   «мек», «麦克», «멕»…) y no siempre igual. Si le hablan en uno de esos idiomas y
   no despierta, el panel lo dice: *«Oí en japonés: '…' (no es una frase de
   despertar)»*. Mira cómo salió escrito el nombre y añádelo en
   `backend/.env`, en la línea `VOICE_NAME_ALIASES` (ver `.env.example`).
   También ayuda poner `WHISPER_MODEL=small` en Ajustes: entiende bastante
   mejor estos idiomas, a cambio de tardar más.
3. **La letra del japonés, el chino y el coreano ya viene incluida.** La
   Raspberry Pi no trae letra para esas escrituras (salían cuadritos vacíos
   en el panel, los subtítulos y la trivia). Desde octubre de 2026 esas
   letras van dentro del propio programa: **no hay que instalar nada**, basta
   con actualizar («Iniciar MECH»). `python -m backend.preflight` avisa si
   faltara algún archivo.

Si en el evento no vais a usar alguno, apagadlo en `backend/.env`
(`WAKE_GERMAN_ENABLED=false`, `WAKE_JAPANESE_ENABLED=false`…): cada idioma
encendido es una lista más de frases contra la que se compara todo lo que
MECH oye en reposo.

Para comprobar las frases de todos los idiomas sin micrófono (la segunda
además juega una trivia entera, usa el traductor y pide marketing en cada
idioma, y mira que todo lo que MECH dice salga en ese idioma):

```bash
python scripts/probar_idiomas.py
```

```bash
python scripts/probar_comandos_idioma.py
```

> Si se despide con una frase larga **pero sigue escuchando**, no reconoció
> la orden como tal. Repítela con **«para de escuchar»**, que es la más
> segura.

---

## 3. Pedirle una obra

Despierto, se le pide cualquier cosa en lenguaje normal:

```
«Háblame de Don Quijote»
«Cuéntame la historia de Malpaís»
«¿Quién fue Isaac Newton?»
«Explícame la teoría de la relatividad»
«¿Qué es CRISPR?»
«¿Qué eres tú?»  /  «¿Quién te construyó?»
```

MECH narra, proyecta y mueve los brazos a la vez. Los **subtítulos** salen
abajo de la proyección, en el idioma activo.

Si la obra tiene sus videos subidos (§7), proyecta esos videos. Si no, genera
imágenes en el momento — no se rompe nada, solo se ve distinto.

### Cortarlo a media narración

```
«oye MECH»                      → para todo y pregunta de qué quiere hablar
«oye MECH, cuéntame otra cosa»  → para y atiende eso enseguida, sin preguntar
```

Mientras narra, MECH **solo** escucha esa frase. Todo lo demás lo ignora
(casi siempre es el eco de su propio parlante). Si despertó en inglés es
«hey MECH» — ahí «oye MECH» **no** lo corta (ver la tabla de §2).

### La trivia al terminar

Cuando MECH **termina de contar una obra entera**, pregunta él solo:

> «¿Te gustaría realizar una trivia para comprobar tu conocimiento?»

(en el idioma en que lo despertaron). Se contesta **«sí»** o **«no»**. Con un
sí, prepara tres preguntas sobre lo que acaba de contar y las **proyecta**,
estilo Kahoot: la pregunta arriba y una ficha de color por opción.

```
¿Cómo se llama el escudero de don Quijote?
  ▲ A  Rocinante     ◆ B  Sancho Panza     ● C  Dulcinea
```

El visitante contesta **hablando**, como le salga:

| Se le dice | Vale |
|---|---|
| «la A» · «be» · «opción C» | Por la letra |
| «la primera» · «la segunda» | Por el orden |
| «Sancho Panza» | Diciendo la opción |

- **Si acierta**, la ficha salta, cae confeti y MECH dice «¡Correcto!».
- **Si falla**, MECH dice «No has acertado. La respuesta correcta es la B:
  Sancho Panza» y la pantalla marca la buena en verde.
- **Si dice «no sé»** (o no se le entiende dos veces), MECH le da la
  respuesta y sigue con la siguiente.
- Al final proyecta el marcador: **2/3**, con confeti si acertó.

También se pide en cualquier momento con **«juguemos una trivia»** (sobre lo
último que contó; si no ha contado nada, sobre MECH) y se sale con **«deja la
trivia»**. Si en vez de contestar al «¿te gustaría…?» piden otra cosa, MECH
deja el juego y atiende eso.

Para probarla **sin micrófono**: panel → vista **Voz** → tarjeta TRIVIA
(«Empezar trivia» y un botón por opción). Si por ahí funciona y hablando no,
el problema es de audio, no del juego. Se apaga o se cambia el número de
preguntas en Ajustes → TRIVIA.

---

## 4. Modo traductor

MECH hace de intérprete entre dos personas que no hablan el mismo idioma.
Traduce **una frase por comando** y se calla — así nunca se traduce a sí
mismo.

```
«traduce MECH»
MECH: «Modo traductor. ¿De qué idioma a qué idioma traduzco?»  ← solo la 1.ª vez
«de español a francés»
MECH: «Listo, traduzco entre español y francés. ¿Qué quieres que traduzca?»
«Buenos días, ¿cómo está?»
MECH: «Bonjour, comment allez-vous ?»                ← y SE CALLA
```

Para la siguiente frase se repite **«traduce MECH»**. El par de idiomas **se
recuerda**, así que a partir de la segunda vez va directo:

```
«traduce MECH»
MECH: «¿Qué quieres que traduzca?»
«Très bien, merci»          (el otro, en francés)
MECH: «Muy bien, gracias.»
```

- **Funciona en los dos sentidos.** MECH detecta en cuál de los dos idiomas
  se dijo la frase y la pasa al otro.
- **Se puede nombrar el par en el propio comando** y se salta la pregunta:
  «traduce MECH del inglés al portugués», «traduce MECH al francés».
- **«deja de traducir»** olvida el par, en cualquier momento (a mitad de un
  turno o cuando ya terminó de traducir). También se olvida al dormir a MECH y
  con el paro de emergencia.
- La traducción sale también como **subtítulo** en la proyección.
- Desde el panel: vista **Voz** → tarjeta TRADUCTOR (los dos idiomas y los
  botones «Traducir una» / «Olvidar»).

> Si traduce su propia pregunta («¿Qué quieres que traduzca?»), es el eco del
> parlante: sube **«Umbral ruido»** en Ajustes o aleja el parlante del
> micrófono.

---

## 5. Moverlo

### Con la voz

Estas órdenes son **directas**: MECH obedece al instante, sin consultar a la
nube.

```
«mira hacia afuera»        → gira 180° y saluda al público
«regresa a proyectar»      → deshace el giro exacto
«avanza diez segundos»     → avanza (el número es opcional)
«retrocede cinco segundos» → hacia atrás
«proyecta marketing»       → los videos promocionales, enteros y con su audio
```

> El giro **se mide por tiempo** (el robot no tiene encoders). Si se queda a
> medias o se pasa, no es un fallo: hay que calibrarlo en
> Panel → Ajustes → **Giro de 180° — Calibración** → «Media vuelta», y
> rehacerlo si cambia el suelo, la batería o las ruedas.

### Con el panel (vista Arduino)

Se **mantiene presionado** el botón para moverlo; al soltar, se detiene.

| Botón | Qué hace |
|---|---|
| **↑ AVANZAR** / **↓ ATRÁS** | Adelante / atrás |
| **← LATERAL** / **→ LATERAL** | Se desliza de lado, sin girar |
| **⟲ GIRO IZQ** / **⟳ GIRO DER** | Gira sobre sí mismo (es el mismo movimiento de la media vuelta) |
| **■ ALTO** | Para las ruedas |

Todo va a potencia máxima: con estos motores, a menos solo zumban.

**Si un control va al revés:**

| Lo que pasa | Qué tocar |
|---|---|
| AVANZAR va hacia atrás | Ajustes → **«Adelante/atrás invertido»**. Arregla a la vez los botones, «avanza diez segundos» y el acercarse al visitante. |
| La media vuelta gira hacia el lado contrario | Ajustes → **«Girar hacia el otro lado»**. |
| «Regresa a proyectar» dice «ya estoy en posición» y no gira | MECH cree que ya mira a la proyección. Si lo giraste con el panel (GIRO, LATERAL o «PROBAR MEDIA VUELTA»), ya lo sabe y obedece; si lo moviste empujándolo a mano, gíralo con los botones GIRO. En el panel, «Ahora mira a» dice lo que MECH cree. |
| LATERAL o GIRO salen espejados (izquierda ↔ derecha) | Avisar para cambiarlo en el código (es una línea). |

Se aplican en vivo, sin reiniciar nada.

---

## 6. Cuando alguien se acerca: el saludo

Con la cámara encendida y **MECH en reposo**, saluda solo a quien llega:
sube el **brazo derecho** hacia adelante, llega arriba **3 veces** y dice,
**en español**, «¡Hola! Soy MECH. Un gusto verte hoy aquí».

> El saludo va en español (desde octubre de 2026; antes iba en inglés): es
> el idioma de MECH en reposo. Se cambia en Ajustes → «Idioma del saludo».
> **No cambia el idioma de MECH** — eso lo decide la frase con que se le
> despierta.

- **Solo saluda en reposo.** Despierto está atendiendo a alguien.
- **Nunca saluda mientras presenta algo** (narrando o con el marketing), ni
  aunque en ese momento parezca estar en reposo.
- Saluda **una vez por visitante**: para volver a hacerlo, la cámara tiene
  que quedarse vacía un rato (Ajustes → «Visitante nuevo»).
- La cara tiene que **mantenerse cerca de un segundo** en la cámara antes
  de que MECH salude (Ajustes → «Confirmar cara»): así no saluda a un
  reflejo o a una sombra que la cámara confunde un instante.
- Para probarlo: panel → vista **Arduino** → **👋 SALUDAR AHORA**. Se salta
  la espera, pero MECH tiene que estar **en reposo**; si no, el panel dice
  por qué no saluda.

Se ajusta en Panel → Ajustes:

| Ajuste | Qué hace |
|---|---|
| **Saludo rotaciones** | Cuántas veces llega arriba el brazo (3) |
| **Saludo brazos** | Apagado = solo el derecho. Encendido = los dos |
| **Sentido brazos** | Si el brazo saluda hacia **atrás** en vez de hacia adelante, se cambia aquí |
| **Saludo** (interruptor) | Exigir que esté en reposo para saludar |
| **Idioma del saludo** | En qué idioma saluda (español) |
| **Saludo lento** / **Saludo alto** / **Saludo amplitud** | Velocidad y tamaño del arco |

> ⚠️ **«Guardar y aplicar» guarda TODOS los ajustes de esa pantalla.** Si
> alguien dejó un valor viejo guardado, ese valor manda. Antes del evento,
> revisa que «Saludo rotaciones» diga 3 e «Idioma del saludo» diga ESPAÑOL.
> (Si MECH sigue saludando en inglés después de actualizar, es justo esto:
> el valor INGLÉS quedó guardado. Ponlo en ESPAÑOL y «Guardar y aplicar».)

---

## 7. Subir videos a la biblioteca

Cada obra se proyecta con sus propios videos, uno por tramo de la narración.
Se suben en la **biblioteca**:

- Desde el panel (en la Pi o en la app de la laptop): menú de la izquierda →
  **Biblioteca**.
- Desde cualquier navegador en la misma wifi: `http://mech:8000/library`.

Hay una tarjeta por obra, con un botón por segmento. Se arrastra el mp4 al
segmento que le toca. **El orden importa**: MECH narra el tramo 1 sobre el
video 1, el 2 sobre el 2…

| Obra | Segmentos | Guiones para generar los videos |
|---|---|---|
| Don Quijote, Campaña de 1856, Jiménez Deredia, Malpaís, Isidro Con Wong | 4 cada una | — |
| Isaac Newton | 5 | [`GUIONES_NEWTON.md`](GUIONES_NEWTON.md) |
| La teoría de la relatividad | 7 | [`GUIONES_RELATIVIDAD.md`](GUIONES_RELATIVIDAD.md) |
| CRISPR y Cas9: las tijeras genéticas | 5 | [`GUIONES_CRISPR.md`](GUIONES_CRISPR.md) |
| Marketing | hasta 12 (ninguno obligatorio) | — |

**La relatividad recorta sola** (los segmentos con ✂ en su tarjeta): se sube
el video completo y la Pi se queda con los **últimos 10 s** del 3 al 7, los
primeros 20 s del 1 y los primeros 10 s del 2. El original no
se pierde: queda guardado aparte. Tarda unos segundos más en subir.

Una obra se proyecta con sus videos solo cuando están **todos** sus
segmentos. **Después de subirlos, reinicia el servidor** (Apagar MECH →
Iniciar MECH): la lista de obras con video se arma al arrancar.

---

## 7 bis. El mapa de sismos

Panel → **Sismos** (menú de la izquierda). Es un mapa del mundo con los
sismos de los últimos 7 días, que se actualiza solo cada minuto.

> **Qué es y qué no.** Muestra lo que **ya tembló**, en cuanto las redes
> sísmicas lo publican: entre 2 y 10 minutos después. **No predice sismos y
> no es una alerta**: cuando el punto aparece, la sacudida ya pasó. Ante una
> emergencia se sigue a las autoridades, no al panel.

- **Colores**: rojo = última hora · ámbar = últimas 24 horas · gris = esta
  semana. **Tamaño** = magnitud. Los que acaban de pasar laten.
- **Arriba**: el periodo (1 hora / 24 horas / 7 días) y la magnitud mínima.
- **Repasar**: vuelve a pasar el periodo en unos segundos; cada sismo aparece
  a su hora. Sirve para enseñarlo aunque en ese momento no esté temblando.
- **Mundo / Mi zona / + / −**: mover el mapa. Con el ratón también se
  arrastra y se acerca con la rueda.
- **Tocar un punto** (o un renglón de la lista): sale su ficha —
  profundidad, a cuántos km de tu zona, quién lo reportó— y se dibujan sus
  dos ondas en cámara rápida: la **P** (rápida y suave) y la **S** (más
  lenta, la que sacude). La ficha dice cuánto tardó cada una en llegar.
- **Mi zona** (tarjeta de abajo): dónde está MECH y de qué radio es el
  círculo. Dentro del círculo salen también los sismos pequeños (desde 2,5);
  del resto del mundo, desde 4. Se guarda con **Guardar** y se aplica al
  momento. Ahí mismo se **apaga** la consulta si no se quiere gastar datos.
- Si llega un sismo dentro de tu zona y estás en otra vista, sale un **punto
  ámbar** junto a «Sismos» en el menú, y una línea en el registro.

Los datos vienen de **EMSC** (reúne las redes de cada país; los de Costa Rica
llegan del OVSICORI-UNA) y del **USGS**. Las dos son públicas y sin clave.
Necesita internet en la Raspberry Pi; sin internet el mapa se queda con lo
último que bajó y lo avisa arriba a la izquierda.

---

## 8. Cuando algo no funciona

**Lo primero, siempre: mirar el panel.** MECH escribe ahí todo lo que oye y
todo lo que hace. La mayoría de las veces el problema se ve de una.

| Lo que pasa | Qué mirar |
|---|---|
| **Le hablan en japonés, ruso o chino y no despierta** | Mira el panel: sale *«Oí en japonés: '…'»* con lo que entendió. Si el nombre está escrito de otra forma, añádelo a `VOICE_NAME_ALIASES` (§2). |
| **El japonés, el chino o el coreano salen como cuadritos** (en el panel, los subtítulos o la trivia) | Esas letras vienen incluidas desde octubre de 2026: actualiza con «Iniciar MECH» y vuelve a abrir el panel y la proyección. Si sigue igual, `python -m backend.preflight` dice si falta algún archivo. |
| **No despierta con «ok MECH»** | ¿Se mueven las barras del micrófono en el panel? Si no, es el micrófono: revisa que el receptor USB del Steren esté puesto y el micrófono de solapa encendido. Si sí se mueven, baja **«Umbral ruido»** en Ajustes. |
| **Se despierta solo / graba fantasmas** | Sube **«Umbral ruido»**. |
| **No se duerme** | Dile **«para de escuchar»** (§2). |
| **No se deja interrumpir** | Prueba el botón **«Interrumpir narración»** de la vista Voz. Si por ahí SÍ corta, el problema es de audio: baja **«Umbral al narrar»**. |
| **Se corta solo a media narración** | Es su propio eco. Sube **«Umbral al narrar»**, o apaga **«Interrumpir»**. |
| **No saluda a nadie** | ¿Está despierto? Solo saluda en reposo (§6). ¿Está encendida la cámara? |
| **Saluda solo, sin nadie delante** | La cámara confunde algo con una cara: sube **«Confirmar cara»**. Si lo que hace es REPETIR el saludo, sube **«Visitante nuevo»**. |
| **El brazo saluda hacia atrás** | Ajustes → **«Sentido brazos»**. |
| **Un botón de movimiento va al revés** | §5, «Si un control va al revés». |
| **No se oye** | Que el parlante esté encendido, conectado y con volumen. |
| **Los videos de marketing se ven pero no se oyen** | La proyección se abrió sin el permiso de autoplay. Ciérrala y ábrela con el icono **Proyectar MECH** (ese ya lo lleva). |
| **La proyección de marketing dura un segundo** | Es el formato de los videos. El panel dice cuáles fallaron y da el comando para reconvertirlos. |
| **Las ruedas no se mueven** | Prueba `MOVE:0:0:100` desde el panel (vista Arduino → comando crudo) con el bucle de voz apagado. |
| **El mapa de sismos dice «sin conexión con las fuentes»** | La Raspberry Pi no tiene internet (o el wifi del recinto bloquea esas páginas). El mapa sigue con lo último que bajó. Con el hotspot del celular vuelve solo en un minuto. |
| **No veo la Pi desde Windows** | La wifi del recinto puede estar aislando los equipos entre sí. Usa el hotspot del celular para los dos. |

### El chequeo antes del evento

Con el servidor **apagado**, en la Pi:

```bash
python -m backend.preflight
```

Revisa de una vez: dependencias, que Whisper funcione sin internet, las
claves de API, el micrófono (lo abre de verdad), el Arduino, los videos y
sus formatos, que el panel no dependa de internet, y que el `.env` de la Pi
no tape los valores por defecto (incluido el saludo).

---

## 9. Paro de emergencia

Botón rojo del panel, o la **barra espaciadora**. Para motores, voz,
proyección y el bucle de voz de golpe.

Después de un paro, MECH **no sabe dónde quedó**: hay que recolocarlo a mano
en su sitio de proyección. También olvida el par de idiomas del traductor.

---

## 10. Resumen de todo lo que entiende

Las frases de esta tabla son las de **español** (despierto con «ok MECH»).
Despierto en otro idioma, valen las de ese idioma y **no** estas (§2).

| Se le dice | Hace |
|---|---|
| «ok MECH» / «wake up MECH» / «bonjour MECH» / «bom dia MECH» / «guten Tag MECH» / «ciao MECH» / «こんにちは MECH» / «привет MECH» / «你好 MECH» / «안녕 MECH» | Despierta en ese idioma |
| «para de escuchar» / «duérmete MECH» | Vuelve a reposo |
| «háblame de …» / «cuéntame …» / «¿quién fue …?» | Narra y proyecta |
| «oye MECH» | Corta la narración |
| «traduce MECH» | Traduce UNA frase |
| «deja de traducir» | Olvida el par de idiomas |
| «mira hacia afuera» / «regresa a proyectar» | Gira 180° y vuelve |
| «avanza N segundos» / «retrocede N segundos» | Se desplaza |
| «sí» / «no» (tras terminar una obra) | Juega o no la trivia |
| «juguemos una trivia» | Empieza el juego de preguntas |
| «la A» / «la segunda» / «Sancho Panza» | Responde la pregunta en pantalla |
| «deja la trivia» | Sale del juego |
| «proyecta marketing» | Los videos promocionales, con su audio |
