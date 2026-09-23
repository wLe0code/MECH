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

Abre **`MECH Panel.exe`**: busca la Pi sola en la red y, cuando el punto se
pone verde, se habilitan los botones:

| Botón | Qué abre |
|---|---|
| **ABRIR EL PANEL** | El panel de control, en una ventana propia. |
| **Abrir la proyección** | La proyección, por si se proyecta desde la laptop. |
| **Panel a pantalla completa** | El panel en modo kiosko (se sale con `Alt + F4`). |
| **Biblioteca de videos (en el navegador)** | La página para subir los videos de las obras (§7). |

Si no encuentra la Pi, escribe su dirección en el campo (por ejemplo
`192.168.1.42` o `mech.local`) y pulsa **Probar**. Más detalles en
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

Al dormirse **vuelve solo a español**, listo para el siguiente visitante.

> ⚠️ Esto es a propósito: si alguien le habla en francés a un MECH despierto
> en español, MECH entiende mal. Hay que dormirlo y despertarlo en el otro
> idioma (o decir la frase de despertar de ese idioma estando despierto).
> Para probar sin hablar: panel → vista **Voz** → chips ES / EN / FR / PT.

### Para dormirlo

«para de escuchar», «deja de escuchar», «duérmete MECH», «descansa MECH»,
«modo reposo». En inglés «stop listening» o «go to sleep».

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
(casi siempre es el eco de su propio parlante). En inglés es «hey MECH».

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
- **«deja de traducir»** olvida el par. También se olvida al dormir a MECH y
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
| LATERAL o GIRO salen espejados (izquierda ↔ derecha) | Avisar para cambiarlo en el código (es una línea). |

Se aplican en vivo, sin reiniciar nada.

---

## 6. Cuando alguien se acerca: el saludo

Con la cámara encendida y **MECH en reposo**, saluda solo a quien llega:
sube el **brazo derecho** hacia adelante, llega arriba **3 veces** y dice,
**en inglés**, «Hello! I am MECH. It's a pleasure to see you here today».

> El saludo va en inglés a propósito: es lo primero que se oye en el stand y
> así lo entiende cualquiera. **No cambia el idioma de MECH** — si le hablas
> con «ok MECH» te responde en español, como siempre.

- **Solo saluda en reposo.** Despierto está atendiendo a alguien.
- **Nunca saluda mientras presenta algo** (narrando o con el marketing), ni
  aunque en ese momento parezca estar en reposo.
- Saluda **una vez por visitante**: para volver a hacerlo, la cámara tiene
  que quedarse vacía un rato (Ajustes → «Visitante nuevo»).
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
| **Idioma del saludo** | En qué idioma saluda (inglés) |
| **Saludo lento** / **Saludo alto** / **Saludo amplitud** | Velocidad y tamaño del arco |

> ⚠️ **«Guardar y aplicar» guarda TODOS los ajustes de esa pantalla.** Si
> alguien dejó un valor viejo guardado, ese valor manda. Antes del evento,
> revisa que «Saludo rotaciones» diga 3 e «Idioma del saludo» diga INGLÉS.

---

## 7. Subir videos a la biblioteca

Cada obra se proyecta con sus propios videos, uno por tramo de la narración.
Se suben en la **biblioteca**:

- Desde la laptop: `MECH Panel.exe` → **Biblioteca de videos**.
- Desde cualquier navegador en la misma wifi: `http://mech:8000/library`.

Hay una tarjeta por obra, con un botón por segmento. Se arrastra el mp4 al
segmento que le toca. **El orden importa**: MECH narra el tramo 1 sobre el
video 1, el 2 sobre el 2…

| Obra | Segmentos | Guiones para generar los videos |
|---|---|---|
| Don Quijote, Campaña de 1856, Jiménez Deredia, Malpaís, Isidro Con Wong | 4 cada una | — |
| Isaac Newton | 5 | [`GUIONES_NEWTON.md`](GUIONES_NEWTON.md) |
| La teoría de la relatividad | 8 | [`GUIONES_RELATIVIDAD.md`](GUIONES_RELATIVIDAD.md) |
| Marketing | hasta 12 (ninguno obligatorio) | — |

**La relatividad recorta sola** (los segmentos con ✂ en su tarjeta): se sube
el video completo y la Pi se queda con los **últimos 10 s** del 3 al 7, los
primeros 20 s del 1 y los primeros 10 s del 2. El 8 va entero. El original no
se pierde: queda guardado aparte. Tarda unos segundos más en subir.

Una obra se proyecta con sus videos solo cuando están **todos** sus
segmentos. **Después de subirlos, reinicia el servidor** (Apagar MECH →
Iniciar MECH): la lista de obras con video se arma al arrancar.

> También hay guiones listos para **CRISPR y Cas9** (5 segmentos) en
> [`GUIONES_CRISPR.md`](GUIONES_CRISPR.md), pero esa obra **todavía no está
> en la biblioteca**: hay que añadirla antes de poder subir sus videos.

---

## 8. Cuando algo no funciona

**Lo primero, siempre: mirar el panel.** MECH escribe ahí todo lo que oye y
todo lo que hace. La mayoría de las veces el problema se ve de una.

| Lo que pasa | Qué mirar |
|---|---|
| **No despierta con «ok MECH»** | ¿Se mueven las barras del micrófono en el panel? Si no, es el micrófono: revisa que el receptor USB del Steren esté puesto y el micrófono de solapa encendido. Si sí se mueven, baja **«Umbral ruido»** en Ajustes. |
| **Se despierta solo / graba fantasmas** | Sube **«Umbral ruido»**. |
| **No se duerme** | Dile **«para de escuchar»** (§2). |
| **No se deja interrumpir** | Prueba el botón **«Interrumpir narración»** de la vista Voz. Si por ahí SÍ corta, el problema es de audio: baja **«Umbral al narrar»**. |
| **Se corta solo a media narración** | Es su propio eco. Sube **«Umbral al narrar»**, o apaga **«Interrumpir»**. |
| **No saluda a nadie** | ¿Está despierto? Solo saluda en reposo (§6). ¿Está encendida la cámara? |
| **Saluda solo, sin nadie delante** | El detector parpadea: sube **«Visitante nuevo»**. |
| **El brazo saluda hacia atrás** | Ajustes → **«Sentido brazos»**. |
| **Un botón de movimiento va al revés** | §5, «Si un control va al revés». |
| **No se oye** | Que el parlante esté encendido, conectado y con volumen. |
| **Los videos de marketing se ven pero no se oyen** | La proyección se abrió sin el permiso de autoplay. Ciérrala y ábrela con el icono **Proyectar MECH** (ese ya lo lleva). |
| **La proyección de marketing dura un segundo** | Es el formato de los videos. El panel dice cuáles fallaron y da el comando para reconvertirlos. |
| **Las ruedas no se mueven** | Prueba `MOVE:0:0:100` desde el panel (vista Arduino → comando crudo) con el bucle de voz apagado. |
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

| Se le dice | Hace |
|---|---|
| «ok MECH» / «wake up MECH» / «bonjour MECH» / «bom dia MECH» | Despierta en ese idioma |
| «para de escuchar» / «duérmete MECH» | Vuelve a reposo |
| «háblame de …» / «cuéntame …» / «¿quién fue …?» | Narra y proyecta |
| «oye MECH» | Corta la narración |
| «traduce MECH» | Traduce UNA frase |
| «deja de traducir» | Olvida el par de idiomas |
| «mira hacia afuera» / «regresa a proyectar» | Gira 180° y vuelve |
| «avanza N segundos» / «retrocede N segundos» | Se desplaza |
| «proyecta marketing» | Los videos promocionales, con su audio |
