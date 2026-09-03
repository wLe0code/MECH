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
> Lo último (ago 2026, §3) fueron tres cosas nuevas: **modo inglés**,
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
4. Vigilar la **CPU de la Pi** mientras narra (`htop`): si sigue alta, la
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
