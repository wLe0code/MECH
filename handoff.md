# HANDOFF — MECH

Documento de traspaso entre sesiones de Claude Code. **Léelo completo** antes
de tocar nada. Contexto de fondo (arquitectura/hardware/decisiones): **CLAUDE.md**
en la raíz — este handoff no lo reemplaza, lo complementa con el estado *vivo*.
CLAUDE.md está muy actualizado; si hay conflicto, gana CLAUDE.md.

> ✅ **Estado (20 sep 2026):** el robot FUNCIONA casi entero en la Pi — audio
> (mic Steren → Whisper local → Claude → voz por parlante Bluetooth),
> movimiento (Arduino Uno + 2× L298N + 4 motores mecanum), proyección, visión
> (cámara C930e) y proyección VR para Google Cardboard. La web de presentación
> está en `web/`.
>
> **Lo último (22 sep 2026, §3.septendecies): lo que salió de probarlo en el
> robot** — el arranque de voz (MECH parecía sordo al encender el server y el
> panel no lo decía), el micrófono que ahora se MIDE solo al arrancar, el
> saludo (4 rotaciones, un brazo, solo en reposo, en inglés), el **sentido de
> giro por brazo** y la **cámara que se perdía al cambiarla de puerto USB**
> (el índice ahora se busca solo). Más los guiones de la relatividad.
>
> Antes (20 sep 2026, §3.quindecies): cuatro cosas, **ninguna probada
> todavía en la Pi** pero todas medidas en la laptop con scripts que quedan en
> el repo. **(1) Gesto "67"**: MECH lo imita cuando alguien lo hace ante la
> cámara — se reconoce por movimiento en ANTIFASE, no por la cara (con las
> manos delante, Haar ve la cara en 1 de cada 45 fotogramas). **(2) Traductor
> continuo**: «activa modo traductor» se queda traduciendo hasta «desactiva el
> modo traductor»; «traduce MECH» sigue siendo una frase. **(3) El reposo que
> no dormía** — la causa era que la frase acababa en Claude, que improvisa una
> despedida pero no puede dormir al robot; ahora hay tres redes. **(4)
> `MECH Panel.exe`**: app de Windows que encuentra la Pi sola (construida y
> probada de verdad, 10,5 MB). Más **`docs/USO.md`**, la guía del operador.
>
> Antes (§3.terdecies) **Tres botones en el escritorio de
> la Pi** — iniciar+panel, proyectar y apagar, sin tocar la terminal.
> (§3.duodecies) **Volumen** para los parlantes Logitech S150, que son
> flojitos: el sistema se pone a tope solo en cada arranque y la voz se puede
> empujar +6 dB con limitador. (§3.undecies) **El matcher perdona errores de
> Whisper**: «trasluce mech» ya activa el traductor, y a la vez se quitaron
> los falsos positivos («el pr-oye-cto» ya no interrumpe). ⚠️ Sigue SIN
> resolver el cambio de Whisper que hizo un compañero — ver §3.quaterdecies.
>
> Antes (sep 2026, §3.decies): **cadena de audio** — MECH entiende mejor
> (se arregló un defecto real de aliasing en el remuestreo y un offset que lo
> dejaba sordo para el «ok MECH»). Antes (§3.nonies): el **saludo por cámara
> solo va en reposo**, para que no corte presentaciones ni conversaciones.
> Antes
> (§3.octies): **modo TRADUCTOR** — «traduce MECH» y
> MECH hace de intérprete entre dos personas en cualquiera de los cuatro
> idiomas, **una frase por comando** (así no se traduce a sí mismo). Sin probar en la Pi. Antes (§3.septies): **francés y portugués**
> — MECH ya habla cuatro idiomas y el que manda lo decide la frase con que
> lo despiertan. Antes (§3.sexies): **giro recalibrado a 4.5 s**,
> **chequeo previo** (`python -m backend.preflight`) y el **panel ya no
> depende de internet**. Antes (§3.quinquies): el **giro es solo lateral** (se quitó la
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

- **Rama:** `main`. Lo de §3.quindecies (gesto 67, traductor continuo, reposo,
  app de Windows y las guías) está **commiteado pero puede estar SIN PUSHEAR**
  — comprobalo con `git log origin/main..main`. Hasta que no esté pusheado, la
  Pi no lo recoge.
  El último commit pusheado antes de esta sesión era `0216cdf` (controles del
  S150).

  **La Pi se actualiza desde GitHub, no desde la carpeta local de nadie.**
  El icono «Iniciar MECH» hace `git pull --ff-only` de `origin/main`. O sea:
  para que un cambio llegue al robot tiene que estar **pusheado**. Cualquiera
  del equipo con permiso de escritura en el repo puede pushear desde su
  computadora y la Pi lo recogerá en el siguiente arranque.
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

**1. El giro se quedaba corto.** Calibrado en tres pasadas sobre el robot:
2.0 s daba ~80° ("un poquito menos de la mitad"), 4.5 s daba 165-170°, y el
default quedó en **4.8 s**. El slider llega a 14 s.
La regla para reajustarlo: si con S segundos gira X grados, los que necesitás
son **S × 180 / X**. Botón nuevo **«PROBAR MEDIA VUELTA»** en la vista Arduino: repite el
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

**4. «Proyecta marketing» terminaba en menos de un segundo.** No era el
backend: el `<video>` de la pantalla dispara `error` con los archivos que no
sabe decodificar y se salta al siguiente — con todos fallando, la playlist
acaba en milisegundos. **Chromium no lee H.265/HEVC**, aunque el archivo se
vea perfecto en VLC o en el móvil.

Ahora la pantalla **reporta qué archivos falló** (`played` y `failed` en
`/api/playlist/ended`) y el panel lo dice con nombre y motivo, más el comando
de ffmpeg para reconvertir. También avisa si termina en menos de 3 s aunque
no haya reportes. Y `python -m backend.preflight` lo detecta ANTES, con
ffprobe: marca cualquier video de la biblioteca cuyo codec no lea el
navegador.

Reconversión:
```bash
ffmpeg -i original.mp4 -c:v libx264 -crf 23 -c:a aac -b:a 192k seg01.mp4
```

**5. Todo valor de movimiento es CONFIGURACIÓN** (pedido explícito). Nada
hardcodeado: clave en `config.py` + `_LIVE_KEYS` + slider en Ajustes, para
poder recalibrar EN EL EVENTO sin tocar código ni reiniciar. Lo último que
entró así: **«avanza diez segundos» / «retrocede cinco segundos»**
(`maneuvers.advance`), con el número hablado opcional — sin él usa Ajustes →
"Avanzar", y siempre topa en `ADVANCE_MAX_SECONDS`.

Valores actuales tras calibrar en el robot: giro **4.8 s**, brazos **2**
subidas (saludo y giro hacia afuera comparten esa perilla), avanzar **10 s**.

### Qué se cae si no hay wifi (lo dice el preflight)

**Sigue funcionando:** micrófono y Whisper (local), «ok MECH», «mira hacia
afuera», «proyecta marketing» y los videos de biblioteca **con su audio**,
saludo por cámara, motores, panel, proyector y VR.

**No funciona:** narrar una obra (el guion lo escribe Claude) y hablar (la voz
la genera ElevenLabs). No hay sustituto local. **Plan B: hotspot del celular.**
Si tampoco hay datos, lo que queda en pie es la proyección de marketing y los
videos de biblioteca, que son archivos locales.

---

## 3.septies Francés y portugués (sep 2026) — sin probar en la Pi

Pedido del equipo: los mismos idiomas que ya tenía en inglés, ahora también en
**francés** y **portugués**. Mecanismo idéntico al del inglés (§3), solo que
generalizado de 2 a 4 idiomas.

**El idioma lo decide la frase con que se le despierta**, igual que antes:

| Frase | Idioma |
|---|---|
| «ok MECH» · «despierta MECH» | español |
| «wake up MECH» | inglés |
| «bonjour MECH» · «salut MECH» · «réveille MECH» | francés |
| «bom dia MECH» · «boa tarde MECH» · «acorda MECH» | portugués |

Al dormirse **vuelve solo a español**, como siempre. En el panel (vista Voz)
hay ahora cuatro chips ES / EN / FR / PT para probarlo sin micrófono.

Qué se tradujo a los cuatro idiomas:
- las frases fijas de `backend/lang.py` (saludo, despedida, bienvenida, error,
  interrupción, playlist vacía, cambio de idioma),
- las frases del giro (`maneuvers._SAY`),
- las órdenes de movimiento, la de marketing y las de interrumpir/dormir
  (`VOICE_*_PHRASES_FR` / `_PT` en `config.py`) — **se aceptan todas siempre**,
  sin mirar el idioma activo,
- el `initial_prompt` de Whisper y la directiva de idioma que se le manda a
  Claude.

### Dos decisiones que importan

**1. El reintento del despertar ya NO va idioma por idioma.** Antes, si la
transcripción en español no daba wake, se re-transcribía el mismo audio en
inglés. Con cuatro idiomas eso serían 3 pasadas de Whisper por CADA ruido que
entre: la Pi quedaría ~10 s sin escuchar. Ahora se re-transcribe **una sola
vez con detección automática de idioma** (`stt.transcribe_any`) y el texto se
compara contra las listas de los cuatro. Mismo costo que antes.
**No lo vuelvas a hacer idioma por idioma.**

**2. Las frases se eligieron para NO chocar entre idiomas.** El matcher de
`voice_phrases` tolera UNA letra de error en palabras de 4+ letras y hace
substring en las cortas, así que:
- ❌ «desperta MECH» (pt) — cae en «despierta MECH» (es), despertaría en el
  idioma equivocado. Por eso el portugués usa **«acorda»** y **«bom dia»**.
- ❌ «olá MECH» (pt) — «ola» está dentro de «hola», así que «hola MECH»
  despertaría en portugués.
- ❌ «dors MECH» (fr, dormir) — «dors» está a una letra de «dos», y
  «avanza dos segundos, MECH» habría dormido al robot. El francés usa
  «au revoir», «bonne nuit», «arrête d'écouter».

Si vas a añadir una frase, pruébala contra las listas de los otros tres.

### Cómo comprobar que la Pi corre esto

Al arrancar, el server loguea una línea nueva:

```
Idiomas: español · inglés · francés · portugués — «ok MECH» (es) · ...
```

Si esa línea no sale (o solo dice «español · inglés»), hicieron `git pull`
pero **no reiniciaron el server** — o alguien apagó un idioma en el `.env`
(`WAKE_FRENCH_ENABLED` / `WAKE_PORTUGUESE_ENABLED`).

### Qué falta probar

1. Despertar en los cuatro idiomas y comprobar que narra, subtitula y
   responde en el idioma correcto.
2. Que «ok MECH» y «hola MECH» **no** despierten en portugués, y que
   «avanza dos segundos MECH» **no** lo duerma (son las colisiones que se
   cerraron a mano; en simulación pasan, falta el micrófono real).
3. Cuánto tarda el reintento con detección automática en la Pi. Si se nota
   lento al despertar, la palanca es `WHISPER_MODEL` (o apagar los idiomas
   que no se vayan a usar en el evento).
4. Que las voces de ElevenLabs suenen bien en francés y portugués
   (`eleven_multilingual_v2` los cubre, pero la voz configurada tiene acento
   español y puede sonar raro).

Validado en simulación: ~100 comprobaciones sin hardware (despertar en los 4
idiomas, no-despertar con frases del stand, reposo, interrupción, las 5
órdenes de movimiento en los 4 idiomas, números hablados, tablas de `lang.py`
y de `maneuvers._SAY`). El panel se verificó en el navegador: los 4 chips
caben en una línea y el cambio de idioma marca el chip correcto.

---

## 3.octies Modo TRADUCTOR (sep 2026) — sin probar en la Pi

Pedido del equipo: que MECH sirva para que dos personas que no hablan el mismo
idioma se entiendan en el stand. Aprovecha los cuatro idiomas de §3.septies.

**Funciona POR TURNOS: un «traduce MECH» = UNA frase traducida.**

```
«ok MECH»                → despierta
«traduce MECH»           → arranca un turno
MECH: «¿De qué idioma a qué idioma traduzco?»          (+ chime)
«de español a francés»
MECH: «Listo, traduzco entre español y francés. ¿Qué quieres que traduzca?»
«Buenos días, ¿cómo está?»
MECH: «Bonjour, comment allez-vous ?»    → y SE CALLA

«traduce MECH»           → otro turno; ya sabe el par, va al grano
MECH: «¿Qué quieres que traduzca?»                     (+ chime)
«Très bien, merci»       (el otro, en francés)
MECH: «Muy bien, gracias.»               → y se calla otra vez

«deja de traducir»       → olvida el par
```

Módulo nuevo: [`backend/translator.py`](backend/translator.py) (solo el
estado) + `llm.translate()` + la rama del bucle de voz en `server.py`.

### Por qué por turnos (esto es lo importante)

La **primera versión escuchaba en bucle** y tenía un problema grave: MECH
habla en cada frase, el micrófono capta su propio parlante, traduce su
traducción, y la de esa — **sin fin**. Se intentó tapar con una espera y una
guarda de texto, pero el equipo propuso lo que de verdad lo resuelve: que
MECH escuche **solo cuando acaba de preguntar**, traduzca UNA frase y se
calle. Así el micrófono nunca está abierto justo después de que él hable.

⚠️ **No lo vuelvas a hacer continuo** sin resolver el eco de otra manera.

Queda **un** hueco de eco: entre la pregunta de MECH y la frase del
visitante. Lo tapan `TRANSLATOR_DRAIN_SECONDS` (0.8 s tras hablar, por el
buffer del parlante Bluetooth) y `translator.looks_like_own_echo()`. Y si aun
así entra, MECH **no pierde el turno**: vuelve a pedir la frase.

### Otras decisiones

**1. El par de idiomas se RECUERDA** entre turnos — repetirlo en cada frase
sería insufrible. Se cambia nombrándolo en el propio comando («traduce MECH
del inglés al portugués», «traduce MECH al francés» → origen = el idioma
activo de MECH) y se olvida con «deja de traducir», al dormirlo o con el paro.

**2. Traduce en los DOS sentidos.** Whisper detecta en cuál de los dos
idiomas del par se dijo la frase (`stt.transcribe_any`, el mismo de
§3.septies) y MECH la pasa al otro. Si detecta un idioma que no es del par,
re-transcribe forzando el de ORIGEN. Se puede fijar el sentido con
`TRANSLATOR_AUTO_DETECT=false` — recomendable **si el par es
español/portugués**, que Whisper confunde en frases muy cortas.

**3. No pasa por el prompt grande de MECH.** `llm.translate()` es una llamada
corta (system de ~700 caracteres, sin caché ni structured output). Con el
prompt de siempre (obras, gestos, biblioteca) cada frase tardaría de más, y
en una conversación la latencia es todo. Si en el evento se nota lento,
`CLAUDE_TRANSLATE_MODEL` permite poner un modelo más rápido sin tocar nada.

**4. Dentro de un turno no se obedecen órdenes.** Solo «deja de traducir»,
dormirlo y repetir «traduce MECH». Es a propósito: un intérprete no ejecuta
lo que está traduciendo (si no, traducir la frase «mira hacia afuera»
giraría el robot).

**5. Si la traducción falla** (API caída, respuesta vacía), tampoco pierde el
turno: lo dice y vuelve a pedir la frase.

### En el panel

Tarjeta TRADUCTOR nueva en la vista Voz: dos selectores de idioma, «Traducir
una» (un turno con ese par, sin preguntar idiomas) y «Olvidar». El badge
muestra la etapa:

| Badge | Qué significa |
|---|---|
| `APAGADO` | nada en curso, sin par recordado |
| `ESPERANDO IDIOMAS` | preguntó de qué idioma a qué idioma |
| `ESCUCHANDO · ESPAÑOL ↔ FRANCÉS` | esperando LA frase a traducir |
| `LISTO · ESPAÑOL ↔ FRANCÉS` | callado, con el par recordado |

La flecha dice el modo: `↔` bidireccional, `→` sentido fijo.
Endpoints: `POST /api/translate/start?src=&dst=` y `POST /api/translate/stop`.

### Qué falta probar

1. El ciclo entero: «traduce MECH» → par → frase → traducción → **se calla** →
   «traduce MECH» otra vez y que NO vuelva a preguntar los idiomas.
2. **Que no traduzca su propia pregunta.** Es lo que más puede fallar. Si
   pasa, subí `TRANSLATOR_DRAIN_SECONDS` y el "Umbral ruido" de Ajustes.
3. El sentido automático con dos personas de verdad. Si se equivoca mucho,
   `TRANSLATOR_AUTO_DETECT=false`.
4. Cuánto tarda cada traducción en la Pi (Whisper + Claude + ElevenLabs). Si
   se hace pesado, la palanca es `CLAUDE_TRANSLATE_MODEL`.
5. Que «traduce MECH» no se dispare con preguntas normales del stand (las
   frases piden dos palabras justo por eso) y que «¿cómo se traduce Quijote
   al francés?» siga yendo a Claude.
6. Los subtítulos de la traducción en `/projector` y en la VR.

Validado en simulación: 10 bloques con micrófono, Whisper, ElevenLabs y
Claude simulados — los dos turnos seguidos, par recordado, par dicho en el
comando, par a medias, guarda anti-eco, fallo de traducción, «deja de
traducir», dormirse, paro y el estado del panel en cada etapa. El panel se
verificó en el navegador con las cinco etapas del badge.

---

## 3.nonies Saludo por cámara SOLO en reposo (sep 2026)

Pedido del equipo: el saludo de la cámara interrumpía presentaciones y
conversaciones. Ahora **solo se dispara con MECH en reposo**.

| MECH está… | ¿Saluda al ver a alguien? |
|---|---|
| en reposo (esperando «ok MECH») | **sí** — es justo lo que se quiere |
| despierto, esperando comando | no |
| grabando / transcribiendo / pensando / narrando | no |
| traduciendo | no (está despierto) |

### Y además: saluda UNA VEZ por visitante

El equipo reportó que MECH **repetía el saludo cada minuto aunque ya no
hubiera nadie**. La causa: `vision.LOST_AFTER_S` son 1.5 s, así que cualquier
parpadeo del detector (una cabeza que gira, un falso positivo con la luz de
la proyección) contaba como "se fue y volvió" = llegada nueva. Lo único que
lo frenaba era el cooldown de 45 s — de ahí la periodicidad.

Ahora hace falta una **ausencia de verdad**: la cámara tiene que quedarse sin
nadie `GREETING_REARM_SECONDS` (20 s) **seguidos**. El reloj se REINICIA en
cada pérdida, así que un detector que parpadea no lo completa nunca.
Verificado en simulación: 10 min de parpadeo continuo -> 1 solo saludo;
cámara vacía 25 s y llega otro -> sí saluda.

⚠️ Efecto secundario a saber: si la cámara tiene un falso positivo
PERMANENTE (un póster, un reflejo), MECH creerá que nunca se fue nadie y no
volverá a saludar. Ahí el problema es la cámara.

- Clave: **`GREETING_ONLY_DORMANT`** (default true), **en vivo** desde
  Ajustes → «Saludar por cámara solo en reposo». Poniéndola en false vuelve
  el comportamiento viejo, pero **ni así habla encima de una narración**.
- El botón **«SALUDAR AHORA»** (vista Arduino) se salta la regla Y el
  cooldown: es para probar el saludo sin tener que dormir a MECH. Lo único
  que respeta es no hablar encima de una narración o de una grabación.
- El aviso del panel («No saludo: MECH está despierto») sale **como mucho una
  vez por minuto**: la visión detecta a ~10 fps y si no lo llenaría de logs
  iguales.
- También se añadió `listening` a las fases que bloquean el saludo: antes
  MECH podía saludar **encima de alguien a quien estaba grabando**.

Código: `mech_app.on_user_detected()` (la puerta), `_perform_greeting()` (el
saludo en sí) y `greet_now()` (el botón). Validado en simulación: 6 bloques
(reposo, las 5 fases despierto, throttle del aviso, regla apagada, cooldown y
el botón del panel).

---

## 3.decies Cadena de audio: que MECH entienda mejor (sep 2026)

Pregunta del equipo: *"¿por qué Google o Siri entienden tan bien y MECH no?
Los micrófonos son buenos."* La investigación completa está en
**[`docs/AUDIO.md`](docs/AUDIO.md)**; aquí va el resumen.

**No es el micrófono.** El de MECH es de solapa: va a 15 cm de la boca, que
es mejor punto de partida que un teléfono a un metro. Lo que hace un teléfono
es **procesar el audio antes de reconocerlo** (pasa-altos, cancelación de
eco, supresión de ruido, AGC, remuestreo limpio, VAD neuronal). MECH hacía
casi nada de eso.

### Lo que se implementó (sin dependencias nuevas)

`stt.prepare_for_whisper()`: pasa-altos → remuestreo a 16 kHz **con
anti-aliasing** → nivel objetivo.

⚠️ **Había un defecto real en el remuestreo.** Bajaba de 48 kHz a 16 kHz
promediando bloques de 3 muestras, que es un filtro pobrísimo: los agudos de
8-16 kHz **se pliegan** dentro de la banda de la voz. Medido con tonos puros:

| Entrada | Reaparece a | antes | ahora |
|---|---|---|---|
| 8.5 kHz | 7.5 kHz | −7 dB | −18 dB |
| 10 kHz | 6 kHz | −9 dB | **−48 dB** |
| 12 kHz | 4 kHz | −13 dB | **−52 dB** |

Con ruido realista de banda alta (fuente conmutada, proyector, siseo de
sala): **16 a 47 dB menos de basura** dentro de la banda útil. Y de paso
conserva mejor las consonantes (a 6 kHz: −1.9 dB antes, 0 dB ahora).

⚠️ **Solo aplica si se captura por encima de 16 kHz.** Si el `.env` de la Pi
tiene `AUDIO_SAMPLE_RATE=16000`, no hay remuestreo y esto no hace nada.
**Hay que confirmar que en la Pi esté en 48000** (el del laptop está en
16000, por eso el script de prueba lo fija a mano).

**Y otro arreglo que puede importar más todavía:** `_frame_rms()` ahora resta
la continua antes de medir. Si el receptor USB mete offset de continua, ese
offset contaba como "ruido ambiente", el piso subía y MECH se quedaba sordo
para el "ok MECH" — que es justo el problema que el equipo peleó a mano en la
olimpiada subiendo el umbral. Medido: una continua pura pasa de marcar
RMS 0.092 a marcar 0.00000, y la voz real sigue marcando igual.

También: **nivel automático** (el "AGC" del teléfono, `-16 dBFS`, con tope de
ganancia ×8 y sin saturar nunca) y **`WHISPER_BEAM_SIZE=5`** en vez de 1 (el
de las interrupciones sigue en 1: ahí manda el retardo).

Tres sliders nuevos en Ajustes, en vivo: **Quita retumbe**, **Nivel de voz**
y **Precisión STT**.

### Lo que NO se hizo (hace falta decisión del equipo)

Ordenado por impacto esperado; el detalle y los costes están en `docs/AUDIO.md`:

1. **Silero VAD** en lugar de webrtcvad (de 2011, se dispara con cualquier
   ruido de banda ancha). Es lo más prometedor. Necesita `onnxruntime` y toca
   el bucle de grabación, que es la parte más delicada del proyecto.
2. **`WHISPER_MODEL=small`** en vez de `base`: el mayor salto de precisión
   posible y **sin dependencias**, pero ~2.5× más lento. **Hay que medirlo en
   la Pi.**
3. **Cancelación de eco (AEC)**: la solución "de teléfono" al eco del
   parlante. Con parlante Bluetooth (retardo variable) es muy difícil; no
   vale la pena para el evento.
4. **Supresión de ruido**: ojo, la documentación de Whisper avisa de que
   sobre-procesar audio limpio **empeora** la transcripción. Con micrófono de
   solapa puede restar en vez de sumar.

### Qué probar

1. **Confirmar `AUDIO_SAMPLE_RATE=48000`** en el `.env` de la Pi.
2. Diez frases variadas (cerca, lejos, bajito, con ruido) y comparar.
3. ¿El «ok MECH» despierta más fácil? Si ahora dispara solo, subir el
   "Umbral ruido".
4. Cronometrar el retardo con `WHISPER_BEAM_SIZE=5` y con 1.

Validado en simulación: 9 bloques con señales sintéticas (aliasing medido en
tres tipos de ruido, que la voz no se toque, pasa-altos, AGC en tres niveles,
que no amplifique el silencio, cadena completa, captura ya a 16 kHz, RMS sin
continua y que todo se pueda apagar desde config).

---

## 3.undecies Que entienda mal una palabra ya no rompe el comando (sep 2026)

El equipo reportó que Whisper escribía «**trasluce** mech» en vez de «traduce
mech» y el traductor no arrancaba. Pasaba también con «oye mech». No es un
problema de Whisper: es del **matcher** de `backend/voice_phrases.py`, que
comparaba demasiado literal.

Y a la vez era demasiado LAXO en el otro extremo: hacía substring libre, así
que «oye» coincidía dentro de «pr-**oye**-cto» y decir «el proyecto se llama
mech» disparaba la interrupción.

`_word_matches()` prueba ahora cuatro cosas, de más barata a más cara:

1. **Igual.**
2. **Suena igual** — `_fonetica()`, una reducción rápida del español:
   `ll`=`y`, `qu`=`k`, `sh`=`ch`, `h` muda, seseo (`c`/`z`/`s`), `b`=`v`,
   `g`+`e/i`=`j`, letras dobles a simple. Eso solo ya arregla «olle»/«oye»,
   «mesh»/«mech», «traduse»/«traduce», «marqueting»/«marketing».
3. **Casi la misma palabra**: el token empieza igual y trae como mucho UNA
   letra de más («mech»→«mecha», «va»→«vai»). Esto sustituye al substring
   libre y es lo que mató los falsos positivos.
4. **Distancia de edición**: 1 error en palabras de 4-6 letras y **2 en las
   de 7+ siempre que empiecen igual**. Los 2 errores son lo que pilla
   «trasluce»; el «empiecen igual» es lo que evita que «produce mucha
   energía» active el traductor.

**Medido** contra 37 transcripciones deformadas reales y 40 frases normales de
stand: **37/37 comandos detectados y 0 falsos positivos** (antes: 34/37 y 1
falso positivo).

⚠️ Si alguien toca estos umbrales, **hay que volver a medir las DOS listas**.
Aflojar para pillar un caso rompe el otro lado enseguida — el corpus de prueba
está descrito en CLAUDE.md, sección «Cómo compara el matcher».

---

## 3.duodecies Volumen: parlantes Logitech S150 (sep 2026)

El equipo cambió el JBL Charge 5 (~30 W) por unos **Logitech S150** (1,2 W por
canal) y MECH sonaba demasiado bajo. Se atacó en las tres capas que existen.

### 1. Volumen del sistema — `pi/volumen-max.sh`, y ya es automático

El audio pasa por varias etapas antes del parlante (sink de PipeWire + uno o
varios mezcladores de ALSA). Basta con que UNA esté al 40 % para que todo
suene flojo, y **no hay un sitio único donde mirarlo**. El script las
**enumera** (no adivina nombres de control) y las pone a tope.

`iniciar-mech.sh` lo llama con `--silencioso` en **cada arranque**: es
ganancia gratis y nadie se acuerda de hacerlo a mano. En el log sale
`Volumen del sistema al máximo...`. Para verlo en detalle, doble click en
`pi/volumen-max.sh` — lista cada etapa que encontró y cómo estaba.

**NO sube del 100 % a propósito**: por encima sería ganancia digital sin
limitador y la voz saldría rota. Para eso está la capa 2.

### 2. Volumen de la voz — `tts._subir_volumen()`

Se aplica a la voz Y al chime, antes de escribir el WAV, así que vale para
`pw-play`, `paplay` y `ffplay` por igual.

| Clave | Default | Qué hace | Medido |
|---|---|---|---|
| `TTS_NORMALIZE` | `true` | deja cada frase pegada al máximo | **+8,1 dB, 0 % de distorsión** |
| `TTS_GAIN_DB` | `0` | empuja más, con **limitador suave** (`tanh` por encima de 0.70) | +6 dB → **+13,2 dB totales, 1 % de distorsión** |

Por encima de +12 dB la voz suena apretada y se gana poco. Los dos son
**en vivo** desde Ajustes («Volumen voz» / «Nivelar voz»). Tabla completa en
[`docs/AUDIO.md`](docs/AUDIO.md) §4.bis.

### 3. El parlante

Los S150 **no tienen rueda de volumen**: llevan **3 botones digitales** en el
frente del parlante derecho — `−`, **mute**, `+`. (Yo afirmé que tenían rueda;
el equipo lo corrigió. Está arreglado en `pi/README.md`, `pi/volumen-max.sh`,
`docs/AUDIO.md` y CLAUDE.md.)

⚠️ Al ser **digitales y no un potenciómetro**, es probable que manden teclas de
volumen al SISTEMA — o sea, la misma etapa que `volumen-max.sh` ya pone al
100 %. En ese caso pulsar `+` no añade nada, pero **el mute sí importa**. La
forma de salir de dudas es doble click en `pi/volumen-max.sh` y mirar qué
etapas lista.

**Orden recomendado si suena bajo:** (1) que no esté en mute, (2) ya lo hace
«Iniciar MECH» solo, (3) Ajustes → «Volumen voz» a +6 dB, (4) si aún no
alcanza es el parlante — uno amplificado de 10-20 W lo resuelve de verdad.

---

## 3.terdecies Tres botones en el escritorio de la Pi (sep 2026)

Pedido del equipo: usar MECH sin pasar por la terminal. Carpeta **`pi/`**.
Se instalan UNA vez con doble click en `pi/instalar-accesos.sh` (también
**borra** los iconos de versiones anteriores, para no dejar botones sueltos).

| Icono | Script | Qué hace |
|---|---|---|
| 🟢 **Iniciar MECH** | `iniciar-mech.sh` | `git pull` → cierra un server anterior → venv → volumen al máximo → arranca el server → **abre el panel solo** cuando responde |
| 📽️ **Proyectar MECH** | `proyector-mech.sh` | Chromium kiosko en `/projector` **con el flag de autoplay** |
| 🔴 **Apagar MECH** | `apagar-mech.sh` | para el server con margen para cerrar bien; `-9` solo si no cierra; cierra también la proyección (SOLO esa) |

Sin icono, a propósito (el equipo quiere solo 3): `panel-mech.sh` (lo llama
`iniciar-mech.sh`), `volumen-max.sh` y `autoarranque.sh` (arranque al encender
la Pi, con `--sin-actualizar --sin-panel`). Se lanzan con doble click desde el
explorador de archivos.

Detalles que importan:

- **Arranca aunque no haya internet.** Si el `git pull` falla, avisa y sigue
  con el código local. Quedarse sin robot por el wifi del recinto sería lo peor
  que podría pasar en un evento.
- **`.gitattributes` con `*.sh text eol=lf`** — sin eso, Git en Windows los
  commitea con CRLF y en la Pi salen con `bad interpreter: /bin/bash^M`.
- El flag `--autoplay-policy=no-user-gesture-required` del proyector **no es
  opcional**: sin él los videos de marketing se ven MUDOS.

Ver [`pi/README.md`](pi/README.md) para la tabla de «si algo no funciona».

---

## 3.quaterdecies ⚠️ Pendiente sin resolver: el cambio de Whisper del compañero

El equipo dijo: «mi compañero hizo un cambio en el modelo de whisper, que nos
está desbeneficiando». **No se llegó a resolver** — pedí la salida de este
comando en la Pi y la conversación siguió por otro lado:

```bash
grep -E "WHISPER|AUDIO_SAMPLE_RATE" ~/MECH/backend/.env
```

Sospechas, por orden: `WHISPER_MODEL=tiny` (transcribe peor) o `small`/`medium`
(la Pi tarda demasiado). El default sano es **`base`**. Y de paso confirmar
`AUDIO_SAMPLE_RATE=48000`: con 16000 toda la mejora del remuestreo (§3.decies)
no hace nada.

Recordar que el `.env` de la Pi **tapa los defaults del código**, así que un
`git pull` no deshace ese cambio: hay que editar el `.env` o cambiarlo desde
Ajustes en el panel.

---

## 3.quindecies Gesto "67", traductor continuo, reposo y app de Windows (sep 2026)

Cuatro cosas pedidas por el equipo. **Nada probado en la Pi todavía**, pero
todo medido en la laptop con scripts que quedan en el repo.

### 🙌 El gesto del "67"

El equipo pasó **dos videos**: en el primero un visitante hace el "67" con las
**manos** a la altura de la cara; en el segundo, cómo tiene que hacerlo MECH —
con los **brazos enteros**, uno arriba y el otro abajo, alternando.

Lo que define al gesto no es la forma de la mano: son **dos cosas moviéndose
en vertical, una a cada lado, en ANTIFASE**, repitiéndose. Eso es todo lo que
mide `backend/gesture_detect.py`.

**Por qué NO se ancla en la cara.** Fue el primer intento (dos zonas de
búsqueda a los lados del rostro) y se descartó con un dato: pasando el video
real del equipo por el detector Haar de OpenCV, **con las manos delante la
cara aparece en 1 de cada 45 fotogramas**. Anclarse ahí no habría detectado
nada. MediaPipe Pose tampoco vale (la Pi corre Python 3.13, sin wheels).

Cómo funciona, a 320×180 y en gris: diferencia entre fotogramas → el centro
horizontal del movimiento parte la escena en dos mitades → se sigue la ALTURA
media del movimiento de cada lado → sobre 1,6 s se exige amplitud,
**correlación negativa** y varias alternancias.

| Filtro | Qué descarta |
|---|---|
| Correlación ≤ −0,30 | levantar las dos manos A LA VEZ (correlación positiva) |
| Equilibrio entre lados | saludar con UNA sola mano |
| Alternancias ≥ 3 | un cruce suelto |
| Amplitud mínima | alguien quieto, un temblor |

⚠️ **Los huecos NO borran la ventana** (`_MAX_GAP_S`). En cada extremo del
gesto la mano se frena un instante y ese fotograma cae por debajo del mínimo
de movimiento; la primera versión limpiaba el historial ahí y nunca llegaba a
juntar muestras. Se descubrió porque el positivo sintético no disparaba.

**Medido, no estimado** — `python scripts/probar_gesto67.py <video1> <video2>`:

```
ok   REAL WIN_...26_Pro.mp4  (debe disparar)   -> [0.66, 1.19, 1.79]
ok   REAL WIN_...34_Pro.mp4  (debe disparar)   -> [2.06, 2.99, 4.19, 5.52]
ok   antifase (el gesto)     (debe disparar)   -> [1.07, 2.07, ...]
ok   quieto                  (NO debe)         -> ninguno
ok   saluda con UNA mano     (NO debe)         -> ninguno
ok   dos manos EN FASE       (NO debe)         -> ninguno
ok   manos en horizontal     (NO debe)         -> ninguno
ok   alguien camina          (NO debe)         -> ninguno
```

Los negativos se generan solos con OpenCV, así que el script corre en
cualquier máquina sin cargar videos al repo. **Si tocás un umbral, volvé a
correrlo.**

Lo demás: `gestures.sixty_seven()` (único gesto con los dos brazos en
antifase), `mech_app.on_gesture_67()`, botón «🙌 HACER EL 67» en la vista
Arduino (`POST /api/move/67`) y toda la calibración en vivo en Ajustes →
GESTO "67". Frase «¡Seis... siete!» en los cuatro idiomas.

### 💬 Traductor continuo

Ahora hay DOS formas, con listas de frases separadas:

| Se le dice | Qué hace |
|---|---|
| «traduce MECH» | UNA frase y se calla (**igual que antes, sin cambios**) |
| «activa modo traductor» | se queda traduciendo frase tras frase |
| «desactiva el modo traductor» | sale |

⚠️ **«desactiva el modo traductor» contiene «modo traductor»** y el matcher
compara por palabras en cualquier orden, así que las listas se pisan por
fuerza. Lo resuelve `voice_phrases.is_translate_on()`, que devuelve False si
la frase también casa con las de salir.

⚠️ **El continuo reabre a propósito el problema del eco** que los turnos
habían resuelto en jul 2026 (MECH traducía su propia traducción, sin fin).
Volvió por pedido explícito del equipo. Lo que impide el bucle ahora son TRES
cosas — **no quites ninguna**:

1. `TRANSLATOR_CONTINUOUS_DRAIN_SECONDS` (1,2 s, más que en el modo de una
   frase): el micrófono no se abre hasta que el parlante drena.
2. La guarda compara contra las **últimas 3** cosas que MECH dijo, no solo la
   última — con buffer Bluetooth, lo que entra tarde puede ser de dos frases
   atrás. Y ahora se recuerda también **la traducción**, no solo la pregunta
   (antes solo la pregunta, que en el continuo es justo lo que menos importa).
3. Lo decisivo: **cuando la guarda salta, MECH no dice nada**. Sin voz nueva
   no hay nada que realimentar, así que el bucle no puede existir aunque la
   guarda falle a ratos.

El panel avisa con «Llevo N ecos seguidos: me estoy oyendo a mí mismo» y dice
qué perilla subir.

### 😴 El reposo que no dormía

El equipo: *«a veces le digo "duérmete MECH" y dice una frase más larga
diciendo que se va a modo reposo, pero vuelve a abrir el módulo de voz»*.

**La causa**: la frase no casaba con `VOICE_SLEEP_PHRASES`, el texto seguía
hasta Claude, y Claude improvisaba una despedida bonita — pero **dormirse no
es algo que un plan pueda hacer**, así que al terminar volvía a `waiting`. La
"frase más larga" era literalmente Claude hablando.

Tres redes, de la más barata a la más general:

1. **Lista ampliada**: «dormite», «vete a dormir», «a dormir», «ponte a
   dormir», «buenas noches mech», «adiós mech»…
2. **Intercept en `mech_app.handle_text_command()`**, lo primero de todo. Así
   vale para cualquier camino (voz, panel, petición pendiente tras «oye
   MECH»), no solo para el bucle de voz.
3. **Modo `sleep` en el Plan de Claude** (`llm.py`). Si Whisper deformó tanto
   la frase que no casa con ninguna lista, Claude sí entiende la intención y
   MECH se duerme **sin narrar** el plan.

⚠️ **Efecto secundario que hubo que corregir**: al ampliar la lista,
«¿los robots duermen?» empezó a dormir a MECH. El matcher perdona 2 letras en
palabras de 7+ que empiecen igual, y «duermete» casa con «duermen». Por eso
las formas cortas de dormir **piden «mech» al lado**. Está medido.

**`scripts/probar_frases.py`** (nuevo) pasa las dos listas juntas: 47 comandos
que deben reconocerse y 18 frases normales de stand que no. 65/65.

### 🪟 `MECH Panel.exe` para Windows

Hasta ahora, usar el panel desde una laptop pedía saberse la IP de la Pi y
editar `config.txt` a mano — y esa IP cambia al cambiar de wifi.

`windows/mech_panel.py` **encuentra la Pi sola**: prueba la última dirección
que funcionó, `mech.local`, `mech`, y si no barre la red local en paralelo
buscando quién responde en el 8000 **con `/api/state`** (no basta con que el
puerto esté abierto: así no confunde la Pi con otra cosa). Después abre el
panel con Edge/Chrome en `--app`, con el flag de autoplay puesto.

**Solo librería estándar, a propósito**: eso es lo que hace que el .exe pese
10 MB y se construya en un minuto. Tauri/Electron meterían un navegador entero
dentro del ejecutable para mostrar la misma página que Edge ya muestra.

**Construido y probado de verdad en esta sesión**: `MECH Panel.exe` (10,5 MB)
arranca, detecta un servidor de prueba, guarda la dirección y habilita los
botones. Instalador opcional con Inno Setup (`windows/MECH-Panel.iss`): menú
inicio, desinstalador, sin permisos de administrador.

⚠️ Gotcha encontrado al probarlo: el **Python de la Microsoft Store virtualiza
`%APPDATA%`**, así que correr el script con ese intérprete guarda la dirección
en otro sitio que el .exe. No rompe nada, pero despista.

### 📖 Guía de USO

**[`docs/USO.md`](docs/USO.md)** (nuevo): qué decirle a MECH, qué hace cada
comando y qué tocar cuando algo falla, escrito para quien no programa. Es la
que hay que darle al equipo en el evento. Incluye la tabla de todos los
comandos y una de «lo que pasa → qué mirar».

También actualizados: `docs/GUIA.md`, `docs/FRONTEND.md`, `windows/README.md`,
`README.md`, `CLAUDE.md` y `backend/.env.example`.

### El preflight ahora comprueba los comandos

`python -m backend.preflight` §9 ya no solo lista las claves del `.env` que
tapan los defaults: **prueba los comandos principales con el `.env` puesto** y
falla si alguno dejó de reconocerse o si apagar el traductor lo enciende. Es
la comprobación que habría pillado el fallo del reposo antes del evento.

---

## 3.septendecies Arranque de voz, saludo, brazos y cámara (22 sep 2026)

Todo lo que salió de probar MECH en el robot y reportar fallos. **Nada de
esto está probado en la Pi todavía**; está medido en la laptop con scripts
que quedan en el repo.

### 🔇 «Al encender el server no oye "ok MECH", pero con el botón sí»

Reportado dos veces, y NO era el micrófono.

**Causa (primera pasada):** al arrancar, el hilo de voz carga **dos modelos
de Whisper** antes de abrir el micrófono. En la Pi eso tarda de segundos a
casi un minuto, y durante toda esa espera el panel mostraba la fase
`dormant`, que es el estado NORMAL de MECH escuchando. O sea: **parecía
listo cuando el micrófono seguía cerrado**. El botón "arreglaba" el problema
solo porque para cuando se pulsaba los modelos ya estaban en memoria.

Arreglos:

1. **Fase nueva `loading`**: el banner dice «⏳ Cargando Whisper… MECH
   TODAVÍA NO ESCUCHA» en vez de fingir reposo. El aro de LEDs pulsa como
   "pensando".
2. El panel loguea la carga y **cuánto tardó** («Whisper cargado en N s»).
   Ese número es el que hay que mirar: si es alto, la palanca es
   `WHISPER_INTERRUPT_MODEL=tiny`.
3. ⚠️ **El arranque del hilo NO tenía try/except.** Un fallo antes del bucle
   (Arduino, audio, modelo) mataba el hilo **en silencio** y dejaba
   `voice_loop_active` en True: el panel mostraba la voz encendida, el
   micrófono nunca se abría, y como el botón es un toggle hacía falta
   apagar y encender. Ahora el `finally` deja el estado en False y el error
   se ve en el panel.
4. `start_voice_loop()` comprueba que el hilo esté **VIVO**, no solo la
   bandera: si se cayó, arranca otro y lo avisa.

**Segunda pasada — el equipo dijo que seguía sordo.** Ahí dejé de adivinar:

- **`stt.probe_microphone()`** abre el micrófono un segundo al arrancar y
  **mide** lo que entra. `server._reportar_microfono()` escribe el veredicto
  en el panel en CADA arranque y distingue los cuatro casos, que desde fuera
  se ven idénticos:

  | Mensaje | Qué significa |
  |---|---|
  | `Micrófono OK: capta señal` | funciona → si no despierta, es el **umbral** |
  | `NO pude abrir el micrófono (…)` | el dispositivo del `.env` no existe o está ocupado |
  | `se abrió pero NO llegó audio` | desenchufado o apagado |
  | `NO capta nada (silencio digital)` | dispositivo equivocado, sin batería o silenciado |

  También dice **qué dispositivo abrió de verdad** y el nivel medido. Si el
  nombre no es el Steren, ahí está el problema.

- ⚠️ **`VOICE_AUTOSTART=false` ya no es silencio absoluto.** Es la causa más
  probable de todo esto y el arranque no la mencionaba en ningún sitio: con
  esa clave apagada el bucle no arranca solo, MECH parece sordo, y el botón
  del panel lo "arregla" porque es lo único que lo enciende. Ahora se avisa.

**Sigue SIN confirmar cuál de las dos era.** Falta que el equipo pegue las
líneas del panel desde «Bucle de voz iniciado» hasta «Voz lista».

### 👋 El saludo: 4 rotaciones, un brazo y solo en reposo

Tres cosas que pidió el equipo:

1. **`ARM_WAVE_REPEATS` pasa de 2 a 4** (mínimo 2). Cuenta **las veces que
   el brazo llega ARRIBA**, incluida la subida inicial — que es lo que se
   cuenta mirando el robot.
   ⚠️ Al hacerlo intenté que el número contara "solo las agitadas" y el
   script nuevo demostró que estaba mal: **la subida inicial también se ve
   como una**, así que el brazo llegaba arriba una vez MÁS de lo que decía
   el panel. No lo vuelvas a cambiar sin medirlo.
2. **`ARM_WAVE_BOTH` pasa a false**: saluda solo el brazo DERECHO. Con los
   dos se leía más como "manos arriba" que como un saludo, y gasta el doble
   en el gesto que más se repite en el stand.
3. **La regla de "solo en reposo" ya no tiene excepciones.** El botón
   «SALUDAR AHORA» se la saltaba a propósito, y por ahí MECH saludaba
   despierto — justo lo que se quería evitar. Ahora se niega y explica por
   qué. Para probarlo despierto se apaga la regla en Ajustes.

**`scripts/probar_saludo.py`** (nuevo) cuenta las órdenes que el saludo
manda de verdad al Arduino. Es el que pilló el error del punto 1.

### 🦾 Sentido de giro por brazo

El equipo reportó que el brazo derecho saluda **hacia el lado contrario**.
Es de MONTAJE: si la bocina del servo está puesta del otro lado, el brazo
sube al BAJAR el ángulo y **todos** los gestos salen al revés.

Se resuelve como ya se hacía con las ruedas (`DIR_FL/FR/BL/BR` en el .ino):
`gestures._fisico()` traduce el ángulo LÓGICO (90 = reposo, más = levantado)
al que ve el servo. **`ARM_INVERT_R` viene en true** y `ARM_INVERT_L` en
false; los dos en vivo desde Ajustes → «Sentido brazos». El reposo son 90 en
los dos sentidos, así que cambiarlo no obliga a recalibrar nada más.

### 🇬🇧 El saludo por cámara, en inglés

`GREETING_LANGUAGE` (default `en`): el saludo que MECH suelta al ver llegar
a alguien sale en inglés, porque es lo primero que se oye en un stand
internacional. **NO cambia el idioma de MECH** — eso lo sigue decidiendo la
frase con la que se le despierta, y en reposo vuelve siempre a español.
Una clave vacía o mal escrita cae al idioma activo, así que una errata no
deja a MECH mudo. Selector en Ajustes → «Idioma del saludo».

### 📷 La cámara deja de funcionar al cambiarla de puerto USB

Reportado al final de la sesión. **`VISION_CAMERA_INDEX` era un número
FIJO**, y en Linux el número de `/dev/videoN` depende del ORDEN en que se
enchufan los dispositivos: al cambiar de puerto USB (o al reiniciar con el
receptor del micrófono puesto), la cámara pasa de `video0` a `video2` y el
índice guardado apunta a otra cosa.

Es exactamente el mismo problema que ya tenía el Arduino con su puerto
serie, y se resuelve igual:

- **`vision._buscar_camara()`** prueba primero el índice configurado y, si no
  da imagen, **barre los índices 0 a 9**. Dice en el panel cuál encontró y
  sugiere guardarlo.
- ⚠️ **`isOpened()` NO basta**: en Linux una misma webcam expone VARIOS
  `/dev/videoN` (el primero es imagen, los demás metadatos). OpenCV "abre"
  esos nodos sin protestar y luego no entrega un fotograma — por fuera se ve
  igual que una cámara rota. Por eso `_abrir()` pide un fotograma de verdad
  antes de dar el índice por bueno.
- **`VISION_CAMERA_INDEX` ahora es una clave en vivo** (Ajustes → «Cámara
  nº»). Hay que apagar y encender la visión para que valga.
- **El preflight tiene un chequeo nuevo (§10)**: lista los `/dev/video*`,
  prueba qué índices entregan imagen de verdad y avisa si el configurado no
  es uno de ellos. Distingue "la Pi no ve la cámara" (cable/puerto/corriente)
  de "la ve pero no da imagen" (corriente o programa que la tiene abierta).

⚠️ **Lo que esto NO arregla**: si la Pi no ve ningún `/dev/video*`, el
problema es eléctrico o de cable, no del programa. La C930e a 1080p pide
bastante corriente y la Pi 5 la reparte entre los cuatro puertos: con el
receptor del micrófono, el Arduino y la cámara colgando, un hub USB **con
alimentación propia** puede ser la diferencia. Ver §4 para qué pedirle al
equipo.

### 🌌 Relatividad: guion + obra en la biblioteca

- **`docs/GUIONES_RELATIVIDAD.md`**: ocho escenas con narración y prompt de
  Veo. El **segmento 4 (transformaciones de Lorentz) es el único con
  FÓRMULAS en pantalla**, a pedido del equipo; el resto va sin texto porque
  la IA escribe letras deformes. La sección explica cómo conseguir que
  salgan (pizarra y tiza, `sqrt(...)` en vez de √, tres líneas máximo) y el
  plan B: generar la pizarra vacía y poner las fórmulas en la edición.
- **Obra `relatividad` en la biblioteca, con DOS segmentos, no ocho**:
  Gemini junta las escenas en un solo video y el equipo las generó en dos
  cuentas. `seg01` = escenas 1-4 (la relatividad especial), `seg02` =
  escenas 5-8. El corte cae donde termina la especial.
  ⚠️ El **primer `fact`** de la obra le dice a Claude que puede usar el
  mismo `video_segment` en varios tramos de narración. Sin eso intentaría
  contar toda la historia en dos segmentos de 25 s.
  22 `facts` verificados, incluidas las trampas: el Nobel de 1921 fue por el
  efecto fotoeléctrico y **no** por la relatividad, y el papel de Mileva
  Marić es un debate que MECH no debe afirmar ni negar.

### 🪟 `MECH Panel.exe` — dónde está

El .exe construido está en **`windows/dist/MECH Panel.exe`** (10,5 MB).
Esa carpeta está en `.gitignore`, así que **NO viaja en el repo**: cada
máquina lo construye con `windows\construir_exe.ps1`, o alguien lo pasa por
USB. Si el equipo prefiere que viaje en git, hay que sacar `windows/dist/`
del `.gitignore`.

### Dos sesiones a la vez — ojo con los commits

Esta sesión y otra (la de la TRIVIA) estuvieron tocando el repo **al mismo
tiempo**, y las dos editaron `CLAUDE.md`, `handoff.md`, `config.py`,
`voice_phrases.py` y `.env.example`.

⚠️ **No uses `git add -A`.** Yo lo hice una vez y me llevé `trivia.py` a un
commit que no era suyo; hubo que deshacerlo con `git reset --soft`. Si hay
otra sesión abierta:

- commitea **por rutas concretas**;
- si un archivo está mezclado, extraé tus hunks con
  `git diff <archivo> > x.patch`, filtralos y `git apply --cached`;
- y comprobá con `git show --stat` que no se coló nada ajeno.

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
2. **Idiomas**: «wake up MECH» → inglés, «bonjour MECH» → francés,
   «bom dia MECH» → portugués (log: "MECH despierto (<idioma>)"). Debe
   narrar y subtitular en ese idioma y volver a español al dormirse. Ver
   §3.septies para las trampas que hay que descartar.
3. **Subtítulos**: verlos en el proyector y en el visor VR (en el teléfono,
   recargar con caché limpia).
3b. **Traductor (§3.octies, recién hecho)**: «traduce MECH» → «de español a
   inglés» → decirle una frase → debe repetirla en inglés y **callarse**.
   Repetir «traduce MECH»: NO debe volver a preguntar los idiomas. Lo que
   más puede fallar es que traduzca su propia PREGUNTA (eco del parlante):
   si pasa, subí `TRANSLATOR_DRAIN_SECONDS`.
4. **Movilidad (§3.bis, recién hecho)**:
   - Calibrar el giro de 180° (arriba). Es lo que más tiempo lleva.
   - Encender la visión y pasar por delante **con MECH EN REPOSO**: ¿saluda
     con brazo **y** voz a la vez? Y pasar por delante **despierto**: NO
     debe saludar (§3.nonies). ¿Deja de agitar el brazo solo entre
     narraciones?
   - Poner a narrar algo: los brazos deben moverse **poco** y solo uno.
5. **Marketing (§3.ter, recién hecho)**: subir un par de videos en `/library`
   → «Proyectar ahora» → ¿se ven enteros, uno tras otro, **y se oyen**? Si se
   ven mudos, es el flag de autoplay de Chromium.
6. **VR sincronizada (§3.quater y §3.quinquies)**: poner marketing a
   proyectar, esperar, ENTRAR al visor (tiene que aparecer por donde va el
   audio), SALIR de la página y VOLVER — no debe empezar de nuevo.
   El estado de abajo del visor dice a qué segundo se enganchó.
6b. **Audio (§3.decies, recién hecho)**: confirmar
   `AUDIO_SAMPLE_RATE=48000` en el `.env` de la Pi (con 16000 la mejora del
   remuestreo no hace nada), y comparar diez frases variadas con lo de antes.
   ¿Despierta más fácil con «ok MECH»? Si ahora dispara solo, subir el
   "Umbral ruido".
6c. **Los tres botones (§3.terdecies, recién hecho)**: `git pull` en la Pi y
   doble click en `pi/instalar-accesos.sh`. Después, probar los tres iconos.
   Si sale `bad interpreter: /bin/bash^M`, es CRLF: `dos2unix ~/MECH/pi/*.sh`.
6d. **Volumen (§3.duodecies, recién hecho)**: doble click en
   `pi/volumen-max.sh` y **pegar la salida** — dice qué etapas de volumen
   encontró y en qué nivel estaban. Con eso se sabe si los 3 botones del S150
   tocan una etapa aparte o la misma. Y revisar que no esté en **mute**.
6e. **Comandos mal entendidos (§3.undecies, recién hecho)**: decirle «traduce
   mech» varias veces con ruido y ver si arranca el traductor aunque Whisper
   escriba otra cosa (el panel loguea lo que oyó). Y comprobar que MECH **no**
   se interrumpe solo cuando la narración dice «proyecto».
6f. ⚠️ **El `.env` de la Pi (§3.quaterdecies)**: pegar la salida de
   `grep -E "WHISPER|AUDIO_SAMPLE_RATE" ~/MECH/backend/.env`. Es lo que falta
   para cerrar lo del cambio de modelo de Whisper.
6g. **Gesto "67" (§3.quindecies, recién hecho)**: encender la visión y
   ponerse delante haciendo el gesto — MECH debe imitarlo con los brazos y
   decir «¡Seis... siete!». Probar ANTES el botón «🙌 HACER EL 67» de la
   vista Arduino, para separar "la coreografía no va" de "la cámara no lo
   reconoce". Después, los falsos positivos: saludar con una mano, levantar
   las dos a la vez y pasar caminando **no** deben dispararlo. Si hay que
   exagerar mucho, bajar «Amplitud mínima» en Ajustes; si dispara de más,
   subirla. ⚠️ Ojo con la luz de la proyección moviéndose: en teoría no
   afecta (la visión se pausa al narrar) pero es lo primero a mirar si
   dispara solo.
6h. **Traductor continuo (§3.quindecies)**: «activa modo traductor» → par de
   idiomas → tres o cuatro frases seguidas **sin repetir el comando** →
   «desactiva el modo traductor». Lo que más puede fallar sigue siendo el
   eco: si empieza a traducir su propia traducción, subir «Espera continuo»
   en Ajustes. Comprobar también que **«traduce MECH» sigue traduciendo UNA
   sola** y callándose.
6i. **Reposo (§3.quindecies)**: decirle «duérmete MECH» varias veces, de
   formas distintas y con ruido. Debe decir solo «De acuerdo, hasta luego» y
   quedarse en reposo. Si vuelve a soltar una despedida larga, mirar el panel:
   si ahí sale un plan de Claude, la frase no se reconoció — **y lo primero a
   revisar es si el `.env` de la Pi tiene `VOICE_SLEEP_PHRASES` con la lista
   vieja** (el preflight lo avisa ahora).
6j. **El `.env` de la Pi, de una vez**: `python -m backend.preflight` con el
   server apagado. El §9 ahora PRUEBA los comandos con el `.env` puesto y
   falla si alguno dejó de reconocerse. Es el chequeo que cierra §3.quaterdecies.
6k. **LA CÁMARA (§3.septendecies) — es lo más urgente.** El equipo la
   cambió de puerto USB y dejó de funcionar. Con el server APAGADO, en la Pi:

   ```bash
   ls /dev/video*
   v4l2-ctl --list-devices
   python -m backend.preflight      # el chequeo 10 es el de la cámara
   ```

   Y con eso ya se sabe de qué lado está el problema:
   - **No sale ningún `/dev/video*`** → la Pi no la ve: es CABLE, PUERTO o
     CORRIENTE, no el programa. Probar otro puerto, otro cable, y `dmesg |
     tail -20` justo al enchufarla. La C930e a 1080p pide bastante: con el
     receptor del micrófono y el Arduino colgando, un **hub USB con
     alimentación propia** puede ser la diferencia.
   - **Salen nodos pero ningún índice da imagen** → está conectada pero no
     entrega video: casi siempre corriente, o que el server estaba abierto
     (este chequeo va con el server APAGADO).
   - **El preflight dice que el índice que funciona NO es el del `.env`** →
     era eso. Ya no rompe nada (MECH lo busca solo al arrancar), pero conviene
     guardarlo en Ajustes → «Cámara nº».

   Después, encender la visión y comprobar el saludo y el gesto del 67.

6l. **Arranque de voz (§3.septendecies)**: reiniciar el server y **pegar las
   líneas del panel desde «Bucle de voz iniciado» hasta «Voz lista»**. Ahí
   está la respuesta a lo del micrófono: el dispositivo que abrió de verdad,
   el nivel medido y cuánto tardó Whisper. Si NO aparece «Bucle de voz
   iniciado», es `VOICE_AUTOSTART=false` en el `.env`.

6m. **Saludo (§3.septendecies)**: dormir a MECH y pasar por delante. Tiene que
   levantar **solo el brazo derecho**, agitarlo **4 veces** y decirlo **en
   inglés**. Si el brazo va hacia el lado contrario, Ajustes → «Sentido
   brazos» → invertir el derecho. Y despierto NO debe saludar, ni siquiera
   con el botón «SALUDAR AHORA».
   ⚠️ Si sigue saludando con los dos brazos, es el `.env`:
   `grep -E "ARM_WAVE|GREETING" ~/MECH/backend/.env` — esas claves tapan los
   defaults nuevos. El preflight ahora las vigila.

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
  backend/frontend. Desde sep 2026 hay un icono **«Iniciar MECH»** en el
  escritorio de la Pi que hace las dos cosas (ver `pi/README.md`); se
  instala una sola vez con `bash ~/MECH/pi/instalar-accesos.sh`.
  El frontend NO necesita reinicio (el server lo sirve del disco), pero sí
  **Ctrl+Shift+R** en el navegador o se queda el `app.js` cacheado. El firmware se flashea aparte. El `.bat` de Windows es solo
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
