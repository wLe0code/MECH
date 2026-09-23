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
| 🟢 **Iniciar MECH** | Actualiza el código, arranca el servidor y abre el panel de control. |
| 📽️ **Proyectar MECH** | Abre la proyección a pantalla completa. |
| 🔴 **Apagar MECH** | Cierra todo con cuidado. |

Cuando MECH esté listo suena un **tono corto**. A partir de ahí ya escucha.

> Si los iconos no están, se instalan **una sola vez** con doble click en
> `pi/instalar-accesos.sh`.

**Desde una laptop Windows**, abre `MECH Panel.exe`: busca la Pi sola y abre
el panel. Ver [`../windows/README.md`](../windows/README.md).

---

## 2. Lo básico: despertarlo y dormirlo

MECH está siempre escuchando, pero **en reposo no responde a nada** salvo a
su palabra de despertar. Así no gasta créditos ni se mete en conversaciones
ajenas.

```
«ok MECH»               → despierta (responde: «Hola, ya te escucho»)
                          … suena un tono: ahí es cuando hay que hablar …
«duérmete MECH»         → vuelve a reposo
```

**El idioma lo decide la frase con la que se le despierta**, y se queda en
ese idioma hasta que se duerma:

| Frase | Idioma |
|---|---|
| «ok MECH» · «despierta MECH» | 🇪🇸 español |
| «wake up MECH» | 🇬🇧 inglés |
| «bonjour MECH» · «salut MECH» | 🇫🇷 francés |
| «bom dia MECH» · «boa tarde MECH» | 🇵🇹 portugués |

Al dormirse **vuelve solo a español**, listo para el siguiente visitante.

> ⚠️ Esto es a propósito: si alguien le habla en francés a un MECH despierto
> en español, MECH entiende mal. Hay que dormirlo y despertarlo en el otro
> idioma (o decir la frase de despertar de ese idioma estando despierto).

### Para dormirlo valen muchas formas

«duérmete MECH», «MECH, duérmete», «a dormir MECH», «ponte a dormir MECH»,
«para de escuchar», «modo reposo», «adiós MECH», «buenas noches MECH»…

> **Si alguna vez se despide con una frase larga pero sigue escuchando**, es
> que no entendió la orden como tal. Está arreglado en tres capas (sep 2026),
> pero si vuelve a pasar: dilo más claro, con la palabra «MECH» al lado, o
> úsalo desde el panel. Ver §8.

---

## 3. Pedirle una obra

Despierto, se le pide cualquier cosa en lenguaje normal:

```
«Háblame de Don Quijote»
«Cuéntame la historia de Malpaís»
«¿Quién fue Isaac Newton?»
«¿Qué eres tú?»  /  «¿Quién te construyó?»
```

MECH narra, proyecta y mueve los brazos a la vez. Los **subtítulos** salen
abajo de la proyección, en el idioma activo.

### Cortarlo a media narración

```
«oye MECH»                      → para todo y pregunta de qué quiere hablar
«oye MECH, cuéntame otra cosa»  → para y atiende eso enseguida, sin preguntar
```

Mientras narra, MECH **solo** escucha esa frase. Todo lo demás lo ignora
(casi siempre es el eco de su propio parlante).

---

## 3bis. La trivia (sep 2026)

Cuando MECH **termina de contar una obra**, pregunta él solo:

> «¿Te animas a una trivia sobre lo que acabo de contarte?»

Se contesta **«sí»** o **«no»**. Con un sí, escribe tres preguntas sobre lo
que acaba de narrar y las **proyecta**, cada una con tres opciones:

```
¿En qué año se publicó la primera parte del Quijote?
   A   1605
   B   1700
   C   1492
```

El visitante contesta **hablando**, como le salga:

| Se le dice | Vale |
|---|---|
| «la A» · «be» · «opción C» | Por la letra |
| «la primera» · «la segunda» · «la 3» | Por el orden |
| «1605» · «Sancho Panza» | Diciendo la opción |

- **Si acierta**, la pantalla lo celebra (la opción se pone verde y cae
  confeti) y MECH dice «¡Correcto!».
- **Si falla**, MECH dice «No acertaste, la respuesta correcta es la A:
  1605» y la pantalla marca en rojo la que eligió y en verde la buena.
- **Si dice «no sé»** (o no se le entiende dos veces), MECH le regala esa y
  pasa a la siguiente: nadie se queda atascado.
- Al final proyecta el marcador: **2/3**, con confeti si acertó todas.

También se puede pedir en cualquier momento:

```
«juguemos una trivia»    → empieza (sobre lo último que contó)
«deja la trivia»         → sale
```

Si todavía no ha contado nada, las preguntas van sobre **MECH y el proyecto**.

### Lo que hay que saber

- **Las preguntas salen de lo que acaba de narrar**, no de internet: se
  escriben en el momento con el guion y los datos verificados de esa obra.
  Tardan unos segundos, y MECH avisa («dame un momento»).
- Se ofrece **solo al terminar una obra**, no después de una respuesta
  suelta ni de una orden de movimiento.
- Si alguien contesta otra cosa («cuéntame de Malpaís»), MECH **deja el
  juego y atiende eso**: nadie se queda encerrado en la trivia.
- Para probarla **sin micrófono**: panel → vista Voz → tarjeta TRIVIA, con el
  botón «Empezar trivia» y los botones de cada opción. Si por ahí funciona y
  hablando no, el problema es de audio, no del juego.
- Se apaga entera en Ajustes → «Trivia», y ahí mismo se cambia cuántas
  preguntas tiene cada partida.

---

## 4. Modo traductor

MECH hace de intérprete entre dos personas que no hablan el mismo idioma.
Hay **dos formas**, y la diferencia es cuántas frases traduce antes de
callarse.

### Una sola frase

```
«traduce MECH»
MECH: «¿De qué idioma a qué idioma traduzco?»        ← solo la primera vez
«de español a francés»
MECH: «Listo, traduzco entre español y francés. ¿Qué quieres que traduzca?»
«Buenos días, ¿cómo está?»
MECH: «Bonjour, comment allez-vous ?»                ← y SE CALLA
```

Para la siguiente frase hay que repetir «traduce MECH». **El par de idiomas
se recuerda**, así que a partir de la segunda vez va directo al grano.

### Modo continuo (sep 2026)

Para una conversación de verdad, donde repetir el comando cada frase es
insufrible:

```
«activa modo traductor»
MECH: «¿De qué idioma a qué idioma traduzco?»
«de español a francés»
MECH: «Modo traductor activado. Traduzco entre español y francés hasta
       que me digas que lo desactive.»
«Buenos días»                 →  MECH: «Bonjour»
«Merci beaucoup»              →  MECH: «Muchas gracias»    ← y sigue
«¿Dónde está la salida?»      →  MECH: «Où est la sortie ?»
«desactiva el modo traductor»
MECH: «Listo, dejo de traducir.»
```

Suena un **tono** después de cada traducción: ahí le toca hablar al
siguiente.

### Lo que hay que saber

- **Funciona en los dos sentidos.** MECH detecta en cuál de los dos idiomas
  se dijo cada frase y la pasa al otro. No hay que decirle quién habla.
- **Se puede nombrar el par en el propio comando**, y se salta la pregunta:
  «activa modo traductor del inglés al portugués», «traduce MECH al francés».
- **Dentro del traductor NO obedece órdenes**, las traduce. Es lo correcto:
  un intérprete no ejecuta lo que está traduciendo. Solo hacen excepción
  «desactiva el modo traductor» y dormirlo.
- **Se olvida el par** al desactivarlo, al dormir a MECH y con el paro de
  emergencia.
- También se maneja desde el panel: vista **Voz** → tarjeta TRADUCTOR, con
  los dos idiomas y los botones «Traducir una» / «Modo continuo» /
  «Desactivar».

### ⚠️ Si empieza a traducir su propia voz

Es el eco del parlante: MECH habla, el micrófono lo capta y traduce lo que
él mismo acaba de decir. Pasa sobre todo con parlantes Bluetooth, que
arrastran retardo.

MECH ya se defiende solo (descarta lo que reconoce como propio, **y cuando
lo descarta no dice nada**, así que no puede entrar en bucle). Si aun así
molesta, por orden:

1. Panel → **Ajustes** → **TRADUCTOR** → sube **«Espera continuo»**
   (de 1,2 s a 2 s, por ejemplo). Es la perilla principal.
2. Panel → **Ajustes** → sube **«Umbral ruido»**.
3. Aleja el parlante del micrófono.

El panel avisa cuando esto está pasando: «Llevo N ecos seguidos: me estoy
oyendo a mí mismo».

---



## 6. Moverlo

Todas estas órdenes son **directas**: MECH obedece al instante, sin consultar
a la nube.

```
«mira hacia afuera»        → gira 180° y saluda al público
«regresa a proyectar»      → deshace el giro exacto
«avanza diez segundos»     → avanza (el número es opcional)
«retrocede cinco segundos» → hacia atrás
«proyecta marketing»       → los videos promocionales, enteros y con su audio
```

> El giro **se mide por tiempo** (el robot no tiene encoders). Si se queda a
> medias o se pasa, no es un fallo: hay que calibrarlo en
> Panel → Ajustes → **Giro de 180°**, y hay que rehacerlo si cambia el suelo,
> la batería o las ruedas.

---

## 7. Cuando alguien se acerca

Con la cámara encendida, MECH **saluda solo** a quien llega: levanta el
**brazo derecho**, lo agita **4 veces** y dice, **en inglés**,
«Hello! I am MECH. It's a pleasure to see you here today».

> El saludo va en inglés a propósito: es lo primero que se oye en el stand y
> así lo entiende cualquiera. **No cambia el idioma de MECH** — si le hablas
> con «ok MECH» te responde en español, como siempre. Se cambia en
> Ajustes → «Idioma del saludo».

- **Solo saluda en reposo.** Despierto está atendiendo a alguien y saludar
  encima le cortaría la experiencia. Esto vale para TODOS los caminos,
  incluido el botón del panel.
- Saluda **una vez por visitante**: para volver a hacerlo, la cámara tiene
  que quedarse vacía un rato.
- Para probarlo: Panel → vista **Arduino** → **👋 SALUDAR AHORA** (se salta
  la espera, pero MECH tiene que estar **dormido**; si está despierto te lo
  dirá).

Se ajusta en Panel → Ajustes:

| Ajuste | Qué hace |
|---|---|
| **Saludo rotaciones** | Cuántas veces sube el brazo (por defecto 4) |
| **Saludo brazos** | Apagado = solo el derecho. Encendido = los dos |
| **Idioma del saludo** | En qué idioma saluda (inglés por defecto) |
| **Sentido brazos** | Hacia qué lado se mueven. Si un brazo va al revés, es esto |
| **Saludo** (interruptor) | Si se exige que esté en reposo para saludar |
| **Saludo lento** / **Saludo alto** / **Saludo amplitud** | Velocidad y tamaño del arco |

---

## 8. Cuando algo no funciona

**Lo primero, siempre: mirar el panel.** MECH escribe ahí todo lo que oye y
todo lo que hace. La mayoría de las veces el problema se ve de una.

| Lo que pasa | Qué mirar |
|---|---|
| **No despierta con «ok MECH»** | ¿Se mueven las barras del micrófono en el panel? Si no, es el micrófono. Si sí, baja **Umbral ruido** en Ajustes. |
| **Se despierta solo / graba fantasmas** | Sube **Umbral ruido**. |
| **No se duerme y suelta una despedida larga** | Dilo con «MECH» al lado («duérmete MECH»). Si sigue, míralo en el panel: si ahí aparece «Comando: …» y luego un plan de Claude, la frase no se reconoció. Ver §2. |
| **No se deja interrumpir** | Prueba el botón **«Interrumpir narración»** del panel. Si por ahí SÍ corta, el mecanismo está bien y el problema es de audio: baja **«Umbral al narrar»**. |
| **Se corta solo a media narración** | Es su propio eco. Sube **«Umbral al narrar»**, o apaga **Interrumpir**. |
| **Traduce su propia voz** | §4, «Si empieza a traducir su propia voz». |
| **No se oye** | Revisa los **3 botones del parlante Logitech S150** (`−`, mute, `+`, en el frente del derecho) — que no esté en mute. Después, Ajustes → **Volumen voz**. |
| **Los videos de marketing se ven pero no se oyen** | La proyección se abrió sin el permiso de autoplay. Ciérrala y ábrela con el icono **Proyectar MECH** (ese ya lo lleva). |
| **La proyección de marketing dura un segundo** | Es el formato de los videos. El panel dice cuáles fallaron; hay que reconvertirlos (el panel da el comando). |
| **Banner rojo «Sin micrófono — reintentando…»** | El receptor USB del Steren no está o el sistema no lo ve. Enchúfalo: **se recupera solo** en unos segundos, no hace falta reiniciar. Si no vuelve: `arecord -l` en la Pi dice si lo ve. Apagar solo el micrófono de solapa NO causa esto (da silencio, no error). |
| **La cámara se enciende y se apaga** | Mira el panel: dice cuántos segundos aguantó cada vez. Si siempre es lo mismo, es **corriente**: `dmesg \| tail -20` y un hub USB con alimentación propia. Ahora se reabre sola hasta 5 veces antes de rendirse. |
| **Las ruedas no se mueven** | Prueba `MOVE:0:0:100` desde el panel (vista Arduino → comando crudo) con el bucle de voz apagado. |
| **No veo la Pi desde Windows** | La wifi del recinto puede estar aislando los equipos entre sí. Usa el hotspot del móvil para los dos. |

### El chequeo antes del evento

Con el servidor **apagado**, en la Pi:

```bash
python -m backend.preflight
```

Revisa de una vez: dependencias, que Whisper funcione sin internet, las
claves de API, el micrófono (lo abre de verdad), el Arduino, los videos, los
formatos de video, que el panel no dependa de internet y **que los comandos
de voz se sigan reconociendo con el `.env` que tiene la Pi puesto**.

---

## 9. Paro de emergencia

Botón rojo del panel, o la **barra espaciadora**. Para motores, voz,
proyección y el bucle de voz de golpe.

Después de un paro, MECH **no sabe dónde quedó**: hay que recolocarlo a mano
en su sitio de proyección. También olvida el par de idiomas del traductor.

---

## 10. Resumen de todo lo que entiende

| Se le dice | Hace |
|---|---|
| «ok MECH» / «wake up MECH» / «bonjour MECH» / «bom dia MECH» | Despierta en ese idioma |
| «duérmete MECH» | Vuelve a reposo |
| «háblame de …» / «cuéntame …» / «¿quién fue …?» | Narra y proyecta |
| «oye MECH» | Corta la narración |
| «traduce MECH» | Traduce UNA frase |
| «activa modo traductor» | Se queda traduciendo |
| «desactiva el modo traductor» | Sale del traductor |
| «mira hacia afuera» / «regresa a proyectar» | Gira 180° y vuelve |
| «avanza N segundos» / «retrocede N segundos» | Se desplaza |
| «juguemos una trivia» | Empieza el juego de preguntas |
| «la A» / «la segunda» / «1605» | Responde la pregunta en pantalla |
| «deja la trivia» | Sale del juego |
| «proyecta marketing» | Los videos promocionales, con su audio |
