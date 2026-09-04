# HANDOFF — MECH

Documento de traspaso entre sesiones de Claude Code. **Léelo completo** antes
de tocar nada. Contexto de fondo (arquitectura/hardware/decisiones): **CLAUDE.md**
en la raíz — este handoff no lo reemplaza, lo complementa con el estado *vivo*.
CLAUDE.md está muy actualizado; si hay conflicto, gana CLAUDE.md.

> ✅ **Estado (3 sep 2026):** el robot FUNCIONA casi entero en la Pi — audio
> (mic Steren → Whisper local → Claude → voz por parlante Bluetooth),
> movimiento (Arduino Uno + 2× L298N + 4 motores mecanum), proyección, visión
> (cámara C930e) y proyección VR para Google Cardboard. La web de presentación
> está en `web/`.
>
> Lo último (sep 2026, §3.sexies): **giro recalibrado a 4.5 s**, **chequeo
> previo** (`python -m backend.preflight`) y el **panel ya no depende de
> internet**. Antes (§3.quinquies): el **giro es solo lateral** (se quitó la
> rotación, que hacía un movimiento raro), la **VR ya no reinicia el video** al
> salir y volver de la página, y los **brazos al girar afuera van a medio gas**. Antes de eso (§3.ter), el **slot de MARKETING**: videos promocionales
> que se proyectan enteros y con su propio audio con «proyecta marketing».
> Sin probar en la Pi; ojo con el flag de autoplay de Chromium (§3.ter).
>
> Antes (sep 2026, §3.bis), **movilidad**: giro de 180° con «mira hacia
> afuera» / «regresa a proyectar», el saludo por cámara arreglado, saludo más
> amplio y brazos mínimos al proyectar. En la primera prueba en el robot las
> ruedas NO se movían: eran `MODE:LISTEN` frenando los motores + media
> potencia; las dos cosas están arregladas pero **falta volver a probarlo**.
> El giro HAY QUE CALIBRARLO (§3.bis).
>
> Antes de eso (ago 2026, §3) fueron tres cosas nuevas: **modo inglés**,
> **subtítulos** e **interrupción por voz**. Las tres están implementadas y
> pusheadas; la interrupción se probó cuatro veces en el robot real y se fue
> corrigiendo, pero **la última corrección (el lag) todavía NO se ha probado
> en la Pi** — ver §4. El frente abierto de hardware sigue siendo el cambio de
> motores/ruedas (§5).

---

## 1. Objetivo del proyecto (MECH)

Robot interactivo para la **WRO 2026 — Robots and Culture**. En un stand, narra
obras culturales (Don Quijote, Campaña de 1856, Jiménez Deredia, Malpaís, Isidro
Con Wong) con **voz + proyección inmersiva + movimiento físico**, reaccionando a
usuarios que se acercan y le hablan. Claude devuelve un Plan estructurado; Python
lo ejecuta (STT local, TTS ElevenLabs, videos pre-renderizados o imágenes Gemini,
Arduino para motores/servos). El nombre del robot es **MECH-1**.

---

## 2. Estado del repo

- **Rama:** `main`, **todo pusheado** a `origin/main` (incluido este handoff).
  Último commit: `6f432ec` (quitar el lag de la interrupción).
- Remoto: `https://github.com/wLe0code/MECH.git`
- Sin trackear y **NO se commitean**: `.agents/`, `skills-lock.json`. Tampoco
  `windows/config.txt` (tiene la IP local del usuario).
- Dev en **Windows 11** (OneDrive sincroniza el repo); el robot corre en
  **Raspberry Pi 5** (hostname `mech`, ej. `http://mech:8000`). El Arduino se
  flashea desde el laptop.
- **Python de la Pi: 3.13** (¡no 3.11!). Importa para dependencias — ver §6.
- **No hay tests ni linter.** Validación manual E2E. Chequeo rápido sin
  hardware: `python -m py_compile backend/*.py` y `node --check frontend/app.js`.
  Para lógica sin hardware se han usado scripts con stubs (`unittest.mock`) que
  simulan micrófono/voz/APIs — funcionan bien y valen la pena antes de pedirle
  al usuario que pruebe en el robot.

---

## 3. Lo último que se hizo (ago 2026, todo pusheado)

### 🇬🇧 Modo inglés bajo demanda
- Módulo **`backend/lang.py`**: idioma activo (`es` por defecto), frases fijas
  de los dos idiomas y la instrucción de idioma que se le añade a Claude.
- **Se activa SOLO con «wake up MECH»**; con «ok MECH» / «despierta MECH»
  sigue en español. Al dormirse **vuelve a español solo**. Estando despierto,
  decir la frase del otro idioma cambia el idioma.
- Cambian: Whisper (`language="en"`), la narración de Claude (bloque de idioma
  APARTE en el system prompt para no romper el caché), las frases fijas y los
  subtítulos. El TTS ya era multilingüe.
- **Truco**: en reposo se escucha en español, así que «wake up MECH» puede
  salir deformado → si la transcripción no da wake, se **re-transcribe el mismo
  audio en inglés** antes de descartarlo. Hay variantes fonéticas en la lista.
- Chips **ES / EN** en la vista Voz (`POST /api/language/{es|en}`) para probar
  sin micrófono. `.env`: `WAKE_ENGLISH_ENABLED`, `VOICE_WAKE_PHRASES_EN`,
  `VOICE_SLEEP_PHRASES_EN`.

### 💬 Subtítulos en la proyección
- Estilo cine, abajo, en `/projector` y en `/projector/vr` (uno por ojo, con la
  separación de la calibración VR). Haya video, imagen o pantalla vacía, y en
  el idioma activo.
- **El ritmo lo manda el BACKEND**, no el navegador: `tts` pide el audio a
  ElevenLabs **con marcas de tiempo por carácter** y `backend/subtitles.py`
  calcula en qué segundo va cada línea; un hilo las publica a su hora. Antes se
  estimaban en el navegador a ~15 car/s y se adelantaban en cada pausa.
  `frontend/subtitles.js` quedó como pintor tonto — **no devolver el pacing al
  navegador**. Sin marcas de tiempo, cae a reparto proporcional a la duración
  real del audio.
- `mech_app.set_subtitle()` emite el evento WS `subtitle` **y** deja
  `state["current_subtitle"]`: eso último es lo que hace que se vean en el
  teléfono (que se alimenta del sondeo HTTP). Toggle: Ajustes → "Subtítulos".

### ✋ Interrupción por voz mientras narra ("oye MECH" / "hey MECH")
Lo más iterado de la sesión: se probó 4 veces en el robot y cada prueba destapó
una causa distinta. Estado final:

- `backend/interrupt_listener.py`: hilo que escucha durante TODO el plan y
  **solo** reacciona a `VOICE_INTERRUPT_PHRASES(_EN)`. Graba y transcribe **en
  paralelo** (cola de 1 clip, se queda con el más reciente) — antes el
  micrófono se cerraba 1-2 s en cada transcripción y ahí se perdían las frases.
  **No volver a hacerlo secuencial.**
- Al oírla, `mech_app.stop_presentation()` para TODO: voz, música, subtítulos,
  **la proyección** y las ruedas (brazos a reposo). Luego **pregunta** «Claro,
  ¿de qué quieres que hable?» y suena el **chime** de "puedes hablar".
- «oye MECH, cuéntame de Malpaís» → guarda la petición en
  `mech_app.pending_command` y el bucle de voz la atiende enseguida, sin
  preguntar ni chime.

**Las cuatro causas encontradas** (por si algo vuelve a fallar):

1. *No respondía*: si la narración se lanzaba desde el PANEL, el bucle de voz
   tenía el micrófono abierto y el listener no podía abrirlo → ahora el bucle
   lo cede (`mech_app.mic_release`).
2. *"Le cuesta y tarda en callarse"*: grabar y transcribir en serie + silencio
   de fin de frase de 1.2 s. Ahora van en paralelo,
   `INTERRUPT_SILENCE_TIMEOUT=0.6` y `tts.request_stop()` mata el reproductor
   si no muere en 250 ms.
3. *"Se buguea el audio"*: `_on_interrupt` no era idempotente (un segundo
   disparo cortaba la pregunta a media palabra), se hablaba encima del rastro
   del parlante (ahora 0.4 s de pausa) y la música no se mataba de verdad.
4. *"Va muy lagueado, todo descoordinado"*: **MECH se transcribía a sí mismo
   sin parar** y la Pi no daba abasto. El piso de ruido normal baja rápido y se
   queda en los silencios, así que los picos de su propia voz lo superaban
   siempre (subir el umbral NO bastaba — comprobado simulando el micrófono).
   Ahora, solo al narrar, `stt.record_until_silence(floor_average=True)` pone
   el piso **al nivel del parlante** (calibra ~1 s sin poder disparar y luego
   ignora los picos) con `INTERRUPT_ENERGY_FACTOR=4.0`. En simulación con audio
   continuo: de 5 transcripciones a 2 en 15 s, sin perder al visitante.
   Además el listener ya no manda el nivel del mic al panel (eran ~8 eventos/s
   por WS) y usa un Whisper aparte con 2 hilos de CPU.

**Diagnóstico que quedó montado** (útil en el evento):
- El panel loguea **todo lo que oye mientras narra**: `Oí mientras narraba: '...'`.
- Al cortar registra **"Corto la narración (X s desde que terminaste de
  hablar)"** y **"Voz cortada en N ms"**. Con esos dos números se sabe si falta
  afinar la detección o si lo que queda es el buffer del parlante Bluetooth.
- Botón **«Interrumpir narración»** en la vista Voz (`POST /api/voice/interrupt`):
  corta sin micrófono. Si por ahí SÍ corta, el mecanismo está bien y el
  problema es de audio.

**Ajustes en vivo para el evento** (Ajustes del panel):
| Ajuste | Clave | Cuándo tocarlo |
|---|---|---|
| Umbral ruido | `VAD_ENERGY_FACTOR` | No despierta / graba fantasmas |
| **Umbral al narrar** | `INTERRUPT_ENERGY_FACTOR` | Se transcribe a sí mismo (subir) / no te oye al interrumpir (bajar) |
| Interrumpir | `VOICE_INTERRUPT_ENABLED` | Si se corta solo en el evento |
| Subtítulos | `SUBTITLES_ENABLED` | — |

---

## 3.bis Movilidad (sep 2026) — lo último, SIN probar en el robot

El usuario notó que MECH había perdido movimiento («como que le quitaste esas
capacidades cuando logramos el VR, por ejemplo el saludo cuando pasa en la
cámara») y pidió tres cosas más. Todo implementado y validado en simulación
(scripts con stubs, ~70 comprobaciones), **nada probado en el robot todavía**.

### El saludo por cámara: qué estaba mal de verdad

No se había borrado. `on_user_detected` movía el brazo **antes** del cooldown,
así que:
- el brazo se disparaba en CADA detección (también dentro del cooldown),
- la voz solo cada 60 s,
- y como la visión se **pausa** mientras narra (commit `c446563`, del tiempo
  del VR), al terminar cada narración "redetectaba" a la misma persona y el
  brazo se movía **solo, en silencio**.

Ahora gesto y voz van juntos bajo el mismo cooldown (`GREETING_COOLDOWN`,
45 s, ajustable). Y hay un botón **«SALUDAR AHORA»** en la vista Arduino
(`POST /api/move/greet`) para probarlo sin depender de la cámara.

### Lo nuevo

1. **«mira hacia afuera» / «regresa a proyectar»** → `backend/maneuvers.py`.
   Giro de 180° = tramo **lateral** (apartarse de la mesa) + **rotación**; la
   vuelta es el mismo recorrido invertido, así que termina donde empezó.
   No pasa por Claude (instantáneo, sin gastar API). Al girar hacia afuera
   saluda con el brazo y lo dice. `state["facing"]` se ve en el panel, y
   `execute_plan` se da vuelta solo si le piden una historia estando de
   espaldas.
2. **Saludo más lento** — `ARM_WAVE_SECONDS` (2.2 s de subida y de bajada,
   antes 1.3 fijos).
3. **Brazos mínimos al proyectar** — `gestures.perform_talking()`: UN solo
   brazo, máx. 115° (reposo 90), lento, **sin ruedas**; `neutral` no manda
   nada. Los planes `mode="movement"` («saluda al público») conservan el
   gesto completo. Se revierte con `NARRATION_GESTURE_MODE=full`.

### Segunda pasada (probado en el robot: "no se mueve")

Se probó en el robot y **las ruedas no se movían**. Dos causas, las dos reales:

1. **`MODE:LISTEN` frena los motores.** En el firmware, `applyMode()` llama a
   `stopAllMotors()` para LISTEN/SPEAK/STOP — y el bucle de voz mandaba
   `MODE:LISTEN` en CADA vuelta (cada 0.3 s mientras narra). Cualquier
   movimiento moría a los ~300 ms. **Esto afectaba también a
   `return_to_start()`, que probablemente nunca funcionó con el bucle de voz
   encendido.** Arreglado en tres capas: `set_mode` ya no reenvía el modo que
   ya está puesto, el `MODE:LISTEN` del bucle se movió a justo antes de
   grabar, y `mech_app.wheels_busy` bloquea al bucle mientras las ruedas se
   mueven (y pone el Arduino en AUTO, el único modo que no frena).
2. **Iba a media potencia.** `TURN_180_SPEED` era 55, y el firmware escala
   `v * 255 / 100` → PWM 140/255. Con estos motores y el L298N eso zumba y no
   arranca. Ahora el default es **100** (PWM 255) y cada tramo empieza con un
   pulso a fondo (`MOTOR_KICK_SECONDS`).

La **distribución de ruedas sí era la correcta**: el giro usa el patrón
diagonal y el lateral el delantero/trasero, que es justo lo que el equipo
calibró en julio. Se comprobó reproduciendo `driveOmni()` en la simulación.

**El saludo también se agrandó**: llegaba a 170° con UN vaivén de 20°; ahora
llega a 180° y agita 65° tres veces (`ARM_WAVE_HIGH`/`SWING`/`REPEATS`).

### Tercera pasada: "solo sale ACK:ARM"

El equipo probó y **la orden no producía ningún comando de ruedas, solo
`ACK:ARM`**. Ese síntoma es exactamente lo que hace el CÓDIGO VIEJO: sin el
intercept de `handle_movement_command`, «mira hacia afuera» se la come Claude
como un plan `mode="movement"` → gesto `wave` → solo comandos `ARM`. Se
comprobó que el matcher reconoce todas las variantes reales de Whisper
("Mira/Mire/Mirá hacia afuera/fuera", con y sin "MECH" delante), y que por la
ruta real la maniobra emite `MOVE:0:100:0 · STOP · MOVE:0:0:100 · STOP` ANTES
del `ARM`. O sea: la Pi tenía `git pull` pero **sin reiniciar el server**.

Para que no vuelva a pasar a ciegas:
- El server loguea al arrancar **`Movilidad v2 (sep 2026): ...`** con los
  parámetros del giro. Si esa línea no sale, está corriendo código viejo.
  (`MOVILIDAD_VERSION` en server.py — subirla al tocar movimiento.)
- Cada tramo loguea **`Ruedas: MOVE:x:y:z durante N s`** en el panel, y avisa
  con `warn` si un tramo quedó en 0 s.

También en esta pasada:
- **Potencia 100 en TODO lo que mueve ruedas** (antes solo el giro): visión
  al acercarse, `return_to_start`, balanceo de gestos y los botones del
  panel. Los brazos siguen suaves.
- **El saludo usa los DOS brazos** (`ARM_WAVE_BOTH`) y **ya no lo encoge un
  `.env` con `ARM_GESTURE_MODE=subtle`** — eso dejaba el saludo de bienvenida
  en un vaivén de 12°, que es probablemente por qué "movía muy poco los
  brazos al ver a alguien". **Vale la pena revisar esa clave en el `.env` de
  la Pi.**
- `mech_app.log()` ya no puede tumbar una maniobra: un carácter que la
  consola no sepa pintar reventaba el `print` y se perdía el movimiento
  entero (pasa en Windows/cp1252, no en la Pi).

### ⚠️ Lo que HAY QUE CALIBRAR en el robot

**El giro se mide por TIEMPO (no hay encoders).** Con el robot en el suelo
donde vaya a trabajar:

0. **Primero, sin el bucle de voz**: apagá la voz desde el panel y probá
   `MOVE:0:0:100` en Arduino → comando crudo. Si ahí gira y con la voz
   encendida no, quedó algún resto del bug de `MODE:LISTEN`.
1. Panel → **Arduino** → «MIRA HACIA AFUERA». Ahora es un tramo lateral
   sostenido; si gira al revés, activá «Sentido» en Ajustes.
2. Panel → **Ajustes** → «GIRO DE 180° — CALIBRACIÓN» → subir/bajar **Giro**
   (segundos) hasta que quede justo de espaldas. Se aplica en vivo.
3. **Lateral** = cuánto se aparta antes de rotar. Ponlo en 0 s si no hace
   falta o si el espacio es justo.
4. Si gira hacia el lado equivocado, se voltea el signo de `w` en
   `driveOmni()` del `.ino` — **no** en `maneuvers.py`.

Ajustes nuevos, todos en vivo: `TURN_180_SECONDS`, `TURN_180_SPEED`,
`TURN_LATERAL_SECONDS`, `TURN_LATERAL_SPEED`, `MOTOR_KICK_SECONDS`,
`ARM_WAVE_SECONDS`, `ARM_WAVE_HIGH`, `ARM_WAVE_SWING`, `ARM_WAVE_REPEATS`,
`GREETING_COOLDOWN`, `NARRATION_GESTURE_MODE`.

**Si aun así no se mueve, es eléctrico** (§5: los motores y ruedas son de mal
material y hay un cambio de compra pendiente). A potencia 100 y con el bucle
de voz apagado, si `MOVE:0:0:100` no mueve nada, el problema ya no está en
este código: batería, L298N o los propios motores.

> Recordatorio del §5: los **servos de los brazos** todavía no se habían
> movido en el robot (respondían `ACK:ARM` pero quietos) — eso es eléctrico.
> Si el saludo no se ve, revisar primero la alimentación de 5–6 V y la tierra
> común, no este código.

---

## 3.ter Slot de MARKETING (sep 2026) — sin probar en la Pi

Pedido del equipo: un slot de videos promocionales que **proyecte aunque no
tenga los 5**, se dispare con «proyecta marketing» y **conserve su audio**.

Está en `WORKS` como `marketing` con la marca **`promo: True`**, que es lo que
lo hace comportarse al revés que una obra cultural:

| | Obra cultural | Slot `marketing` |
|---|---|---|
| Cómo se pide | lo decide Claude | «proyecta marketing» (orden directa, sin Claude) |
| Reproducción | clip corto en bucle bajo la narración | video **entero**, uno tras otro |
| Audio | **mudo** (MECH narra encima) | **su propio audio** — MECH se calla |
| Si faltan archivos | la obra no se ofrece | **proyecta con los que haya** |

- **12 espacios, ninguno obligatorio.** Con uno solo ya proyecta, y los huecos
  del medio se saltan (si están el 1, el 3 y el 7, reproduce esos tres).
- **No se le ofrece a Claude** (`system_prompt_section` filtra los promo): si
  lo viera, lo narraría como una obra y taparía el audio del video.
- Se corta con «oye MECH», con el botón «Cortar» de `/library` o con el paro.
- **El final lo marca la PANTALLA, no el backend.** Python no sabe cuánto dura
  cada mp4: `projector.html` avanza con el evento `ended` de cada `<video>` y
  avisa con `POST /api/playlist/ended`. `MARKETING_MAX_SECONDS` es solo el
  tope por si no hay ninguna pantalla abierta.
- Subida en `/library`: la tarjeta de Marketing tiene su propio aviso y los
  botones «Proyectar ahora» / «Cortar».

### ⚠️ Para que se OIGA hay que abrir Chromium distinto

Los navegadores no dejan reproducir con sonido sin un gesto del usuario:

```bash
chromium --kiosk --autoplay-policy=no-user-gesture-required http://localhost:8000/projector
```

Sin esa opción el video **se ve pero mudo**, y la pantalla muestra «Toca la
pantalla para activar el sonido» (un toque lo activa y reinicia el video en
curso). Conviene actualizar el lanzador de la Pi con ese flag. En el visor VR
los videos van siempre mudos a propósito: el sonido sale por el parlante.

Y al convertir los mp4, **NO uses `-an`** (eso quita el audio):

```bash
ffmpeg -i original.mov -c:v libx264 -crf 23 -c:a aac -b:a 192k seg01.mp4
```

---

## 3.quater Sincronía de la VR y saludo más corto (sep 2026)

Dos arreglos pedidos tras probar el robot (ya se mueve bien):

**1. El video de la VR no iba sincronizado con el audio.** El audio sale por
el parlante de la Pi, al ritmo de `/projector`; el visor del teléfono
empezaba el video DESDE CERO cada vez que se entraba. Ahora `/projector`
reporta por qué segundo va (`POST /api/playback`, cada 2 s y al cambiar de
archivo) y el visor salta a ese punto.

Detalle que importa: se manda la posición **+ la antigüedad del dato**
(`age`), NO una hora absoluta — el reloj del teléfono no tiene por qué
coincidir con el de la Pi. El visor solo suma `position + age`. `/api/state`
recalcula `age` al responder, que es de donde se alimenta el sondeo del
móvil. Tolerancia de 0.6 s y máximo un salto cada 1.5 s, porque buscar
posición en un móvil parpadea. Con clips en bucle se usa el módulo de la
duración. En la playlist promo el visor sigue además el `index` que reporta
la pantalla, en vez de asumir que va por el primer archivo.

Si vuelve a salir descuadrado: revisar que `/projector` esté abierto (es
quien reporta) y que `state["playback"]` traiga datos. Sin reporte el visor
no se rompe, solo pierde la sincronía.

**2. El saludo daba demasiadas vueltas.** `ARM_WAVE_REPEATS` ahora cuenta las
subidas TOTALES (contando la inicial), que es lo que uno ve: antes el valor 3
producía 4 subidas. Con el default 3 hace "sube, agita, agita, baja". Mínimo
2, tanto en el código como en el slider del panel.

---

## 3.quinquies Segunda pasada del giro y de la VR (sep 2026)

Tras probarlo en el robot:

**1. El giro hacía "un movimiento raro y muy corto".** Ahora la media vuelta
es **UN SOLO tramo LATERAL** — literalmente el mismo movimiento del botón
«LATERAL» del panel — sostenido hasta que queda de espaldas. **Se quitó el
tramo de rotación (`w`)**: con estas ruedas ese patrón no gira bien. Encaja
con lo que ya sabíamos: la cinemática de este robot está calibrada a mano y
no coincide con la mecanum de libro.
- Solo hay que calibrar **una** cosa: los segundos (Ajustes → «Media vuelta»).
- Si gira hacia el lado contrario: **`TURN_180_INVERT`**, en vivo, sin tocar
  el firmware.
- Los sliders «Lateral» y «Vel. lateral» desaparecieron del panel (ya no
  existe ese tramo); las claves siguen en config para no romper `.env`.

**2. Los brazos al girar hacia afuera van a medio gas.** `gestures.wave_outward()`:
145°, vaivén de 30°, UN brazo. Quedan tres tamaños bien diferenciados:
bienvenida por cámara (180°, 65°, dos brazos) > girar hacia afuera (145°, 30°,
un brazo) > al narrar (115°, un brazo).

**3. La VR se sincronizaba solo al entrar.** Al salir de la página el móvil
PAUSA el video, y al volver arrancaba desde cero (se notaba sobre todo en
marketing: videos largos y sin bucle). Tres arreglos:
- **Corrección continua**: un tic cada segundo, no solo al cargar el video.
- **`visibilitychange` / `pageshow` / `focus`** fuerzan un reenganche
  inmediato saltándose el antirrebote.
- El reporte se guarda **con la hora local en que llegó**, y el objetivo se
  recalcula como `position + age + (ahora − llegada)`. Sin eso, reusar el
  mismo reporte apuntaba a un punto cada vez más viejo.

⚠️ Y un detalle que es fácil volver a romper: **`play()` sobre un video
TERMINADO lo reinicia desde cero**. Todos los `play()` de reanudación llevan
`if (v.paused && !v.ended)`. Si alguien "arregla" que el video se quede
pausado sin esa guarda, vuelve el bug del video que empieza de nuevo.

---

## 3.sexies Listo para la competencia (sep 2026)

**1. El giro se quedaba corto.** Con 2.0 s giraba "un poquito menos de la
mitad" (~80°), así que el default pasó a **4.5 s** y el slider llega ahora a
14 s. Botón nuevo **«PROBAR MEDIA VUELTA»** en la vista Arduino: repite el
tramo *sin* cambiar la orientación guardada, para poder calibrar pulsando
varias veces seguidas (con «mira hacia afuera» había que alternar con
«regresa a proyectar» y se acumulaba el error de los dos tramos).

**2. Chequeo previo:** `python -m backend.preflight` (o `--sin-red`).
Verifica de una pasada dependencias, Whisper cargando **del disco**, claves,
micrófono (lo abre de verdad), reproductores de audio, Arduino, biblioteca,
frontend offline y las claves del `.env` que tapan defaults. **Correrlo con
el server apagado.**

**3. El panel ya no depende de internet.** Los iconos venían de un CDN y las
fuentes de Google Fonts: sin wifi, los botones que son **solo icono** (subir
video, borrar) salían **EN BLANCO**. Ahora todo en `frontend/vendor/`.
De paso: `ti-brand-arduino` no existe en Tabler, así que esos tres iconos ya
estaban rotos incluso con internet.

### Qué se cae si no hay wifi (lo dice el preflight)

**Sigue funcionando:** micrófono y Whisper (local), «ok MECH», «mira hacia
afuera», «proyecta marketing» y los videos de biblioteca **con su audio**,
saludo por cámara, motores, panel, proyector y VR.

**No funciona:** narrar una obra (el guion lo escribe Claude) y hablar (la voz
la genera ElevenLabs). No hay sustituto local. **Plan B: hotspot del celular.**
Si tampoco hay datos, lo que queda en pie es la proyección de marketing y los
videos de biblioteca, que son archivos locales.

---

## 4. ⚠️ Lo PRIMERO que hay que hacer: probar en la Pi

La última corrección (el lag) **no se ha probado todavía**. En la Pi:
`git pull` + reiniciar el server, y después:

1. **Interrumpir**: ponerlo a narrar algo largo y decirle «oye MECH».
   - ¿El audio sale limpio ahora, sin entrecortarse?
   - ¿Cuánto marca el log en «Corto la narración (X s…)» y «Voz cortada en N ms»?
   - Si en el log aparece `Oí mientras narraba:` con texto de su PROPIA
     narración → subir "Umbral al narrar".
   - Si no reacciona → bajarlo, y probar el botón «Interrumpir narración» para
     descartar que sea el micrófono.
2. **Modo inglés**: «wake up MECH» → debe despertar en inglés (log:
   "MECH despierto (inglés)"), narrar y subtitular en inglés, y volver a
   español al dormirse.
3. **Subtítulos**: verlos en el proyector y en el visor VR (en el teléfono,
   recargar con caché limpia).
4. **Movilidad (§3.bis, recién hecho)**:
   - Calibrar el giro de 180° (arriba). Es lo que más tiempo lleva.
   - Encender la visión y pasar por delante: ¿saluda con brazo **y** voz a la
     vez? ¿Deja de agitar el brazo solo entre narraciones?
   - Poner a narrar algo: los brazos deben moverse **poco** y solo uno.
5. **Marketing (§3.ter, recién hecho)**: subir un par de videos en `/library`
   → «Proyectar ahora» → ¿se ven enteros, uno tras otro, **y se oyen**? Si se
   ven mudos, es el flag de autoplay de Chromium.
6. **VR sincronizada (§3.quater y §3.quinquies)**: poner marketing a
   proyectar, esperar, ENTRAR al visor (tiene que aparecer por donde va el
   audio), SALIR de la página y VOLVER — no debe empezar de nuevo.
   El estado de abajo del visor dice a qué segundo se enganchó.
7. Vigilar la **CPU de la Pi** mientras narra (`htop`): si sigue alta, la
   siguiente palanca es `WHISPER_INTERRUPT_MODEL=tiny` (hay que descargarlo una
   vez con `WHISPER_OFFLINE=false`; si falta, el sistema avisa y sigue con el
   normal).

---

## 5. Frentes ABIERTOS

### A) Cambio de motores y ruedas (decisión de compra en curso)
Los motores y ruedas mecanum actuales son de **mal material** y el robot no se
mueve bien. Lo conversado:
- **Motor recomendado: JGB37-520** (caja 37mm, engranajes de METAL, eje D 6mm).
  Existe en **6V y 12V** — elegir el que coincida con la batería del robot
  (**dato que falta confirmar: ¿6V? ¿7.4V? ¿12V?** — preguntarlo). RPM usable
  **~150–300** (NO worm/sinfín, NO <100 RPM, NO N20 3mm).
- **Ruedas:** las mecanum Yahboom (acople hex 6mm) calzan en el eje de 6mm.
  Para cero sorpresas, comprar un **kit de un solo vendedor** (Moebius/OSOYOO
  4WD mecanum) o motor+rueda+acople emparejados.
- **Driver:** el L298N "come" ~2V; a 12V pasa, a 6V queda flojo → si van a bajo
  voltaje, considerar **TB6612FNG**. No comprar aún; probar con el L298N.
- **Encoder:** opcional, **NO conectarlo** (el Uno no tiene pines de
  interrupción libres para 4 y el código no lo usa).
- **Firmware cuando lleguen:** si se montan bien (rodillos en X), recalibrar
  `driveOmni` a la mecanum estándar (o a diferencial "tipo carro" si pasan a
  ruedas normales). Cambio chico, hacerlo con las ruedas ya montadas.

### B) Pendientes menores heredados
- **Fotos reales del robot** a `web/assets/robot-01.jpg` / `robot-02.jpg`
  (mientras no existan, la web usa un render SVG).
- **Generar y subir los videos pre-renderizados** por obra (UI en `/library`).
  Sin ellos, MECH cae a imágenes Gemini para esas obras.
- **Servos de los brazos**: en un test respondían `ACK:ARM` pero no se movían
  → es ELÉCTRICO (alimentación 5–6V externa / tierra común / interruptor), no
  código. El firmware manda bien la orden.

---

## 6. Gotchas que cuestan tiempo si no se saben

- **Dependencias de la Pi con Python 3.13:** `pip install -r backend/requirements.txt`.
  Visión: `pip install "opencv-python-headless<5"` (NO la 5, NO mediapipe en
  3.13; corre con el detector Haar). Ver `backend/requirements-vision.txt`.
- **El `.env` de la Pi TAPA los defaults del código.** Ha pasado ya con
  `VOICE_WAKE_PHRASES`. Si una frase nueva no funciona, revisar si esa clave
  está escrita a mano en el `.env`.
- **`git pull` en la Pi + reiniciar el server** para aplicar cambios de
  backend/frontend. El firmware se flashea aparte. El `.bat` de Windows es solo
  un lanzador del navegador.
- **VR en el teléfono:** recargar con caché limpia; la pantalla de carga
  muestra el estado de conexión para diagnosticar. El sondeo HTTP (no el WS) es
  lo que la hace funcionar en el móvil — **no quitarlo**, y **no volver al
  canvas** (no pintaba en el móvil del equipo).
- **El parlante es Bluetooth**: tiene buffer propio. Un rastro de voz de
  décimas DESPUÉS de cortar no se puede arreglar por software.
- **`git push` solo cuando el usuario lo pida.** Commits en español,
  `Co-Authored-By: Claude ...`. Si el usuario tiene trabajo sin commitear,
  commitear por pathspec para no pisarlo.
- **Este `handoff.md` no se venía commiteando** (estuvo modificado en local
  desde julio). El 3 sep 2026 el usuario pidió commitearlo. Si vuelve a
  quedarse fuera de los commits, preguntarle.

---

## 7. Cómo trabajar con este usuario

- Estudiante, **no** programador pro, en **español**. Explicaciones paso a paso,
  cambios chicos y revisables.
- Cuando algo falla en su consola/hardware, pedir el mensaje u observación
  **exacta** antes de adivinar. En esta sesión, tres de las cuatro causas del
  problema de interrupción aparecieron solo tras preguntar qué veía.
- **Antes de dar por bueno un arreglo de audio/micrófono, simularlo.** El
  intento de subir el umbral parecía correcto y la simulación demostró que no
  cambiaba nada; sin eso se habría ido otra prueba en el robot.
- **Hardware pieza por pieza** (flashear → 1 motor → …). Muchos problemas
  fueron eléctricos (batería débil, tierra común, voltaje), no de código.
- Al terminar cambios grandes, **actualizar este `handoff.md` y/o `CLAUDE.md`**.
