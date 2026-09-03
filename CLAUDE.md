# CLAUDE.md — contexto para futuras sesiones de Claude Code

Este archivo es tu primer punto de referencia al abrir una sesión nueva en este repo. Léelo COMPLETO antes de hacer cualquier cambio o sugerencia. Está escrito para ti (Claude), no para el usuario.

---

## Qué es MECH

Robot interactivo para la **WRO 2026 — Robots and Culture**. Misión: en un stand de exhibición, narrar obras culturales (Romeo y Julieta, Shrek, La Odisea, Don Quijote, etc.) con **voz + proyección inmersiva + movimiento físico**, reaccionando a usuarios que se acercan y le hablan.

El usuario es un estudiante (no programador profesional). Comunica en **español**. Las explicaciones siempre en español, paso a paso, asumiendo poco conocimiento previo. No asumas familiaridad con git, terminal, Python, etc. salvo evidencia contraria.

---

## Arquitectura — qué hace cada pieza

Esquema mental basado en los diagramas originales del usuario (capas física + flujo de software + flujo de interacción):

### Capas físicas del robot

| Capa | Componentes |
|---|---|
| **Superior** | Motor de cabeza (servos pan/tilt), proyectores HDMI |
| **Central** | Raspberry Pi 5 (8GB), fuente de poder, parlante, **Logitech C930e** (cámara USB — solo video), **receptor del mic inalámbrico Steren MIC-9010** (USB) |
| **Mecánica** | **Arduino Uno R3** + 2× driver L298N, 4 motores DC con ruedas omnidireccionales (mecanum), 2 servos MG996R (brazos) |

### Flujo del software (de arriba a abajo)

```
Usuario habla
   │
   ▼ audio
[STT local] faster-whisper en la Pi          ← backend/stt.py
   │ texto
   ▼
[LLM] Claude Opus 4.7 (UN solo request)      ← backend/llm.py
   │ system prompt incluye lista DINÁMICA de
   │ obras con video pre-renderizado disponible.
   │ devuelve Plan estructurado (Pydantic):
   │   { mode, title,
   │     segments[{narration,
   │               image_prompt?,
   │               video_slug?, video_segment?,
   │               gesture}] }
   ▼
[Orquestador] mech_app.execute_plan()         ← backend/mech_app.py
   │ por cada segmento decide visual:
   │   1) video_slug+video_segment presentes Y archivo existe
   │      → reproduce video de biblioteca   ← backend/video_library.py
   │   2) image_prompt presente
   │      → genera con Gemini Image          ← backend/image_gen.py
   │   3) ninguno → mantiene visual anterior
   ├─→ Arduino (servos + ruedas)              ← backend/arduino_link.py
   └─→ ElevenLabs TTS                         ← backend/tts.py
```

### Flujo de interacción usuario

```
Usuario → Selección por voz → [Stand info] o
                              [Espacio inmersivo] (con Función + Movimiento + Q&A)
                                                          ↓
                                                       Bot MECH
                                                          ↓
                                              Supervisión firmware (panel web)
```

### Por qué structured outputs y NO tool use

Para narrar Romeo y Julieta en 5 escenas, tool use serían ~10 round trips a Claude (5x imagen + 5x texto). Structured outputs es UN solo round trip que devuelve el guión completo. Más rápido, más barato, más predecible. Si más adelante se necesita reactividad (Claude decide el flujo en vivo), se puede migrar — pero **no lo cambies sin que el usuario lo pida explícitamente**.

### Por qué video pre-renderizado y NO generación en vivo (Opción B)

El usuario quiere video real, no solo imagen. Pero generar video en vivo (Kling, Veo 3, Runway) tarda **30 s – 2 min** por clip y cuesta dólares por historia. Eso rompe el formato de stand interactivo (el usuario se aburre y se va).

**Estrategia adoptada (Opción B):**
- Los videos de obras conocidas (Romeo, Shrek, Odisea, Quijote, ...) se generan **una sola vez** antes del evento, en otra máquina, con el modelo de video que prefiera el equipo.
- Se guardan como `.mp4` en `backend/video_library/<slug>/seg{NN:02d}.mp4`.
- MECH los reproduce en bucle mientras narra (la narración dura ~20–30 s, el video 5–15 s → loop natural).
- Si el usuario pide una obra **no** pre-renderizada, el robot cae automáticamente al flujo viejo de NanoBanana (imagen generada en vivo). Esto preserva improvisación.

**Manifest** de obras: [`backend/video_library.py`](backend/video_library.py). El system prompt de Claude se compone **dinámicamente** al arranque del servidor — solo aparecen las obras con TODOS sus segmentos físicamente presentes en disco. Si falta un segmento, esa obra no se ofrece a Claude y se usa el fallback.

**UI de subida:** `http://<pi>:8000/library` (`frontend/library.html`) — un card por obra, botón por segmento, drag-and-drop de mp4. Endpoints REST: `POST /api/library/{slug}/{seg}` y `DELETE` análogo.

**No vuelvas a proponer generación de video en vivo** salvo que el usuario lo pida explícitamente.

---

## Decisiones de hardware ya tomadas

No las cuestiones a menos que el usuario las cuestione primero:

| Componente | Decisión | Por qué |
|---|---|---|
| Cómputo principal | Raspberry Pi 5 **8 GB** | Holgura para Whisper + Chromium + CV |
| Storage | microSD 64 GB | Suficiente |
| Microcontrolador | **Arduino Uno R3** (ATmega328P) + **2× L298N** | El RoboKit RS de Roborobo se descartó (no acepta control en vivo de la Pi; corre programas Rogic cerrados). El Arduino se controla por USB serial — es la arquitectura que el proyecto espera (`arduino_link.py` + `mech_controller.ino`). |
| Motores | DC con ruedas omnidireccionales (mecanum) | Movimiento en cualquier dirección |
| Servos | **2 MG996R** (brazo L, brazo R) | Solo brazos para gestos. La cabeza se descartó (la expresividad direccional la dan las ruedas). Los servos se alimentan con 5–6V externos desde la protoboard (NO desde el Arduino), GND común. |
| Presencia / visión | **Logitech C930e** (USB UVC, 1080p, FOV 90°) — **solo video** | FOV ancho detecta usuarios que se acercan por los lados; H.264 por hardware libera CPU de la Pi. **El mic de la C930e ya NO se usa.** |
| Audio in | **Steren MIC-9010** — micrófono inalámbrico de solapa con receptor USB | Inalámbrico (~20–35m de alcance), batería recargable. El receptor se enchufa por USB a la Pi y aparece como dispositivo de captura. Se selecciona con `AUDIO_INPUT_DEVICE` en `.env` (ej. `Steren`). |
| Audio out | Parlante USB o jack 3.5mm | |
| Visualización | Proyector **YG300** (HDMI desde la Pi) + Chromium kiosko a `/projector` | Se cambió del HY300 al **YG300 por el voltaje** (el YG300 va con 5V) |
| Energía | Batería + **interruptor general** | El interruptor corta la alimentación de potencia (batería → drivers/servos) sin desenchufar |

### Sin HC-SR04 (cambio de plan)

El plan original tenía HC-SR04 **+** cámara para roles distintos: HC-SR04 evasión rápida, cámara detección de usuarios. **El usuario decidió quitar el HC-SR04** y usar solo la cámara C930e para todo.

**Trade-off conocido:** la cámara con MediaPipe corre a ~10 fps; no es buena para frenar antes de chocar en movimiento. Si más adelante el robot se golpea contra paredes/personas, considerar:
- Volver a meter un HC-SR04 (es barato y se conecta a 2 pines del Arduino).
- O añadir detección de obstáculos por visión (mucho más complejo).

No empujes esto si el usuario no lo trae. Por ahora se asume operación en stand con poco movimiento autónomo.

### Pin mapping del Arduino Uno (firmware actual)

El firmware [`arduino/mech_controller/mech_controller.ino`](arduino/mech_controller/mech_controller.ino) ya está mapeado para el **Arduino Uno R3**:

- **Servos (brazos):** ARM_L = pin **9**, ARM_R = pin **10** (la librería Servo usa el Timer1 = pines 9/10).
- **Motores (4× DC vía 2× L298N):** PWM/ENA en **3, 5, 6, 11**; direcciones IN1/IN2 en **2, 4, 7, 8, 12, 13, A0, A1**. (No se usan 9/10 para PWM porque los ocupa el Servo.)
- **Aro de LEDs (WS2812/NeoPixel 12 LEDs, estilo Alexa):** ⏸️ **EN PAUSA (jul 2026): el equipo decidió NO usar el aro por el momento — `#define MECH_LEDS 0` en el .ino** (compila sin la librería; los `LED:` responden ACK y no hacen nada; el backend los sigue mandando y es inofensivo). Si se retoma: `MECH_LEDS 1`, DIN = pin **A2** (con ~330 Ω en serie), VCC al **5V del Arduino** (brillo limitado a 60/255 — NO a la fuente de 6V de los servos), GND común, librería **Adafruit NeoPixel**.
- **Sin cabeza:** el comando `HEAD` se reconoce pero es un no-op (no rompe el lado de la Pi; los gestos siguen con los brazos).

Subir con `arduino:avr:uno`. Servos alimentados con 5–6V externos (protoboard), GND común.

**Sentido de giro por motor:** constantes `DIR_FL/DIR_FR/DIR_BL/DIR_BR` en el .ino (1 = normal, −1 = invertido). Calibración CONFIRMADA en el robot real (jul 2026): **FR y BL van en −1** (cableadas con polaridad opuesta); con esos signos AVANZAR va hacia adelante. Si una rueda gira al revés, se cambia su signo ahí y se reflashea — NO recablear. Para calibrar sin adivinar: comando `WHEEL:<id>:<vel>` (una sola rueda; chips en el panel → Arduino → comando crudo).

**Cinemática ADAPTADA a las ruedas reales (jul 2026) — NO "corregirla" al estándar de libro:** por cómo están montadas las mecanum del robot (el usuario decidió NO remontarlas), los patrones se calibraron empíricamente en el suelo: 4 iguales = avanza (vx) ✓; patrón DIAGONAL (FL+BR vs FR+BL) = GIRO sobre sí mismo (w) ✓; patrón de LADOS (izq vs der) = las fuerzas se anulan y NO se mueve (no se usa); patrón DELANTERO/TRASERO (2 de adelante vs 2 de atrás) = desplazamiento LATERAL (vy). `driveOmni()`: `fl=vx+vy+w · fr=vx+vy−w · bl=vx−vy−w · br=vx−vy+w`. El giro a 2 ruedas (solo FL+BR sin las otras) se descartó: se sentía "trabado". Si un sentido sale espejado (giro der ↔ izq o lateral der ↔ izq), se voltea el signo de `w` o `vy` en esta fórmula, nada más.

**Movimiento AUTÓNOMO = SOLO adelante/atrás (decisión jul 2026):** en la práctica el robot solo se desplaza bien hacia adelante y atrás; girar se hace MANUAL desde el panel "estilo carro" (atrás, girar un poco, atrás, girar un poco). Por eso los comportamientos automáticos (visión al acercarse, gestos con ruedas) SOLO usan `vx` — nada de `w` ni `vy`. Además `arduino_link.py` lleva un **odómetro** adelante/atrás (integra vx·tiempo) y `mech_app.return_to_start()` revierte el desplazamiento neto ANTES de cada plan, para que el proyector vuelva a apuntar a donde estaba calibrado (la proyección no se desfasa). El odómetro se resetea con el paro de emergencia (posición ya no confiable).

---

## Stack de APIs externas

| Servicio | Para qué | Archivo | Variable .env |
|---|---|---|---|
| **Anthropic Claude API** (Opus 4.7) | Cerebro — devuelve plan estructurado | `backend/llm.py` | `ANTHROPIC_API_KEY` |
| **ElevenLabs** | TTS en español (multilingual_v2) | `backend/tts.py` | `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` |
| **Google Gemini** | NanoBanana = `gemini-2.5-flash-image` — **solo fallback** cuando la obra no está en la biblioteca de videos | `backend/image_gen.py` | `GOOGLE_API_KEY` |

**Claude no llama directamente a ElevenLabs ni a Gemini.** El usuario tuvo esta confusión. Si vuelve a preguntar, recuérdale: Claude devuelve un Plan JSON; Python ejecuta el plan llamando cada API en orden.

**STT NO usa API.** Es `faster-whisper` corriendo local en la Pi (modelo `base` o `small`). Cero costo, sin red. Configurable en `WHISPER_MODEL`.

---

## Mapa de archivos

```
backend/
  server.py           ← ENTRY POINT principal. FastAPI + WebSocket.
  main.py             ← Modo standalone sin servidor (testing puro).
                        NO correr junto con server.py.
                        NO proyecta videos de biblioteca (solo imágenes).
  mech_app.py         ← Singleton de estado + event bus.
                        Aquí vive emergency_stop() y execute_plan().
                        _render_segment_visual() decide video vs imagen.
  llm.py              ← Cliente Claude. System prompt + schema Pydantic del Plan.
                        Inyecta dinámicamente la lista de obras disponibles
                        desde video_library.
  lang.py             ← Idioma activo (es/en). Español por defecto; inglés
                        SOLO si despiertan a MECH con "wake up MECH". Guarda
                        las frases fijas de los dos idiomas y la instrucción
                        de idioma que se le añade a Claude.
  stt.py              ← faster-whisper local + VAD (webrtcvad). Transcribe en
                        el idioma activo (lang.whisper_language()).
  subtitles.py        ← Parte el guion en líneas y calcula EN QUÉ SEGUNDO va
                        cada una, con las marcas de tiempo por carácter que
                        devuelve ElevenLabs (o proporcional si no las hay).
  tts.py              ← ElevenLabs streaming.
  image_gen.py        ← Gemini / NanoBanana. Fallback de visual cuando
                        no hay video pre-renderizado.
  video_library.py    ← Manifest de obras + helpers para resolver paths/URLs
                        y componer la sección dinámica del system prompt.
  video_library/      ← Carpeta con los .mp4 (gitignored). Estructura:
                        <slug>/seg01.mp4, seg02.mp4, ...
  arduino_link.py     ← Serial al Arduino. Protocolo de texto líneas \n.
                        Auto-reconexión + autodetección de puerto + LED:.
  interrupt_listener.py ← Hilo que escucha SOLO "oye MECH"/"hey MECH"
                        mientras MECH narra, para poder cortarlo.
  gestures.py         ← Coreografías reales de gestos (wave, excited...)
                        con interpolación suave; modos full/subtle/off;
                        opcionalmente mueve ruedas (GESTURE_WHEELS).
                        perform() = coreografía completa (saludo, panel);
                        perform_talking() = versión SIMPLE de un solo brazo
                        para MIENTRAS proyecta.
  maneuvers.py        ← "mira hacia afuera" / "regresa a proyectar": giro de
                        180° (lateral + rotación) y su vuelta exacta. Guarda
                        hacia dónde mira en state["facing"].
  vision.py           ← C930e + MediaPipe: presencia, posición y distancia
                        del usuario; seguir/acercarse; gate de proyección.
  projector.py        ← Visor tkinter ALTERNATIVO (solo para main.py standalone).
                        En operación normal se usa el visor browser-based.
  config.py           ← Lee .env.
  requirements.txt
  .env.example

frontend/
  index.html          ← Panel de control web.
  app.js              ← Lógica + WebSocket. Detecta file:// para modo demo.
                        Maneja eventos image y video.
  styles.css
  projector.html      ← Página fullscreen para Chromium kiosko en la Pi.
                        Maneja eventos image y video, con loop en video, y
                        pinta los SUBTÍTULOS de la narración abajo.
  subtitles.js        ← Subtítulos estilo cine compartidos por /projector y
                        /projector/vr. Es un pintor TONTO: muestra la línea
                        que manda el backend. El reparto y el ritmo los
                        decide backend/subtitles.py (ver más abajo).
                        Se sirve en /static/subtitles.js.
  cardboard.html      ← Vista estéreo lado a lado (Google Cardboard) en
                        /projector/vr. Misma fuente WS que projector.html,
                        duplicada por ojo; se abre en el teléfono.
  library.html        ← UI sencilla en /library para subir videos
                        pre-renderizados (Opción B).
  manifest.json       ← PWA instalable.
  sw.js               ← Service worker.
  icon.svg

arduino/mech_controller/
  mech_controller.ino ← Firmware. Modos: AUTO/IDLE/LISTEN/SPEAK/STOP.
                        Comandos: MODE, HEAD, ARM, MOVE (omnidireccional), STOP.

branding/             ← Identidad y figuras para el trabajo escrito (IEEE).
                        logo-mech.jpg/pdf (alta calidad, réplica del SVG del
                        sitio) + diagramas a 300 dpi generados con PIL+Sora:
                        diagrama-arquitectura.png (capas DENTRO del render del
                        robot, 1050px = columna IEEE), diagrama-flujo-hardware/
                        software.png (1050px) y diagrama-caso-uso.png (2150px,
                        figura de dos columnas, con el render como actor).
                        Scripts regenerables en branding/scripts/ (diag_*.py
                        + Sora.ttf; ver su README).

web/                  ← Sitio de PRESENTACIÓN del proyecto (NO es el panel).
  index.html          ← One-page en 2 capítulos: 01·empresa (lateral sticky) y
                        02·robot (banner MECH-1, showcase scroll estilo Apple,
                        pipeline, hardware, obras y construcción en tiras).
  styles.css          ← Estética heredada del panel (mismo dark + acentos).
  app.js              ← Scroll showcase + typing + reveals. Sin dependencias;
                        funciona abriendo index.html con doble click (file://).
  assets/             ← Logo oficial, favicon, fotos del PDF del trabajo
                        escrito. El showcase busca robot-01.jpg/robot-02.jpg
                        (fotos del robot terminado); si faltan usa un render SVG.
  README.md           ← Cómo verla y cómo publicar en GitHub Pages.

windows/              ← Control desde laptop Windows
  MECH Control.bat    ← Doble click → Edge --app, ventana sin barras.
  MECH Kiosko.bat     ← Pantalla completa kiosko.
  MECH Proyector.bat  ← Página de proyector en kiosko.
  config.txt          ← URL del servidor (el usuario edita la IP de la Pi aquí).
  README.md

docs/
  GUIA.md             ← Hardware y montaje en la Pi.
  FRONTEND.md         ← Servidor, panel, control desde Windows.

Demos/                ← Versión standalone solo HTML+JS+CSS para probar
                        la UI sin backend (file://).
```

---

## Reglas de operación (modos mutuamente excluyentes)

Dos formas de correr el backend, **nunca a la vez** (pelearían por Arduino + micrófono):

1. **`python -m backend.server`** → modo normal. Sirve frontend + WS + bucle de voz (controlable desde el panel).
2. **`python -m backend.main`** → modo headless de testing. Solo voz + STT + Claude + TTS. Sin web.

Para producción, **siempre server.py**.

---

## Comandos comunes

Quick-reference. Asume que estás en la raíz del repo.

```bash
# Setup en la Pi (una sola vez)
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env       # rellenar API keys

# Operación normal (backend + panel + WS, todo en uno)
python -m backend.server

# Visor de proyección en la misma Pi (Chromium kiosko)
chromium --kiosk http://localhost:8000/projector
# En Bookworm el binario también está como chromium-browser; ambos funcionan.

# Testing headless (sin web, sin panel — solo voz → Claude → TTS)
python -m backend.main

# Subir firmware al Arduino (desde Arduino IDE o arduino-cli)
arduino-cli compile --fqbn arduino:avr:uno arduino/mech_controller
arduino-cli upload  --fqbn arduino:avr:uno -p <PUERTO> arduino/mech_controller
# PUERTO en Linux suele ser /dev/ttyUSB0 o /dev/ttyACM0; en Windows COM3, COM4...
```

### Versión de Python

Desarrollado y probado con **Python 3.11** (el que trae Raspberry Pi OS Bookworm por defecto). `requirements.txt` no fija versión mínima — si surgen incompatibilidades de paquetes, sospechar primero de versión de intérprete.

### Tests y lint

Este repo **no tiene suite de tests ni linter configurado**. La validación es manual extremo-a-extremo: voz → STT → Plan de Claude → imagen → proyección → comandos Arduino. No inventes `pytest`/`ruff`/`black` — si crees que hace falta uno, propónselo al usuario antes de añadirlo.

---

## Convenciones de código

### Idiomas

- **Strings al usuario (UI, voz, logs)** → siempre español neutro. Las frases
  que MECH DICE (saludo, despedida, error) tienen su par en inglés en
  `backend/lang.py`: si añades una, añade las dos.
- **`image_prompt` para NanoBanana** → siempre inglés (Gemini rinde mejor).
- **Comentarios y nombres de variables** → español está bien, ya lo usa el repo.
- **Commits** → español también, sigue el estilo existente.

### Logs

`mech_app.log(message, level)` con niveles `ok | info | warn | err`. Se difunde por WebSocket al panel. Úsalo en vez de `print()` cuando sea desde un módulo que toca eventos del robot.

### Schema del Plan de Claude

```python
Segment:
  narration: str
  image_prompt: str | None      # fallback (NanoBanana)
  video_slug: str | None        # biblioteca pre-renderizada
  video_segment: int | None     # 1-indexed
  gesture: Literal[...]
```

Prioridad de visual: `video_slug + video_segment` (si el archivo existe) > `image_prompt` > nada. Si Claude pide un video que no está en disco se loguea warning y se intenta el `image_prompt` del mismo segmento si lo trae.

### Idioma (español / inglés)

MECH **siempre arranca en español**. El **inglés se activa si y solo si** se
le despierta con **«wake up MECH»**; con «ok MECH» / «despierta MECH» sigue en
español. En inglés van: lo que Whisper transcribe (`language="en"`), lo que
Claude narra (bloque de idioma en el system prompt), las frases fijas (saludo,
despedida, error) y los subtítulos. **Al dormirse vuelve solo a español.**

- Idioma activo y textos fijos: [`backend/lang.py`](backend/lang.py).
- Frases de despertar/reposo en inglés: `VOICE_WAKE_PHRASES_EN` /
  `VOICE_SLEEP_PHRASES_EN` (`.env`), detección en `voice_phrases.wake_language()`.
- En reposo, si la transcripción en español no coincide con ningún wake, el
  bucle **re-transcribe el MISMO audio en inglés** (clip corto, ≤4 s) para
  reconocer «wake up MECH» aunque Whisper lo hubiera deformado.
- Se puede forzar desde el panel (chips ES/EN en la vista Voz →
  `POST /api/language/{es|en}`), útil para probar sin micrófono.
- Apagar el modo inglés: `WAKE_ENGLISH_ENABLED=false`.

### Interrumpir a MECH mientras narra ("oye MECH" / "hey MECH")

Durante TODO el plan (narración y también las pausas en que genera imágenes),
`backend/interrupt_listener.py` corre un hilo que escucha con una regla muy
estricta: **solo** las frases de `VOICE_INTERRUPT_PHRASES` /
`VOICE_INTERRUPT_PHRASES_EN`. Cualquier otra cosa que oiga se descarta sin
mirarla — durante la narración, lo que más se oye es el propio parlante.

Al oírla: `mech_app._on_interrupt()` llama a **`stop_presentation()`**, que
para TODO lo de la presentación de golpe — voz (`tts.request_stop()`), música
de fondo, subtítulos, **lo que se está proyectando** (`clear_visual()`) y las
ruedas — marca `_narration_interrupted`, y el bucle de `execute_plan` deja de
recorrer segmentos (y deja los brazos en reposo).

Detalles que importan para que el audio no suene sucio (ago 2026):

- `_on_interrupt` es **idempotente**: si el listener dispara dos veces
  seguidas, la segunda no hace nada. Sin eso, el segundo corte mataba la
  pregunta a media palabra.
- Antes de preguntar hay una pausa de 0.4 s: el parlante (sobre todo por
  Bluetooth) todavía tiene dentro el final de la narración, y hablar encima
  se oye sucio.
- `background_audio.stop()` también mata el proceso si no muere en 250 ms
  (antes solo pedía `terminate()` y la música seguía sonando por debajo).
- **Lo que de verdad quitó el lag**: que MECH dejara de transcribirse a sí
  mismo. Mientras narra, `record_until_silence` se llama con
  `floor_average=True` + `INTERRUPT_ENERGY_FACTOR` (4.0): el piso de ruido se
  PONE al nivel del parlante en vez de quedarse en los silencios, así los
  picos de su propia voz ya no lo superan y solo dispara quien hable
  claramente por encima (el mic es de solapa: el visitante entra 5× más
  fuerte). Antes disparaba con cada frase suya y la Pi transcribía sin
  parar → audio entrecortado, panel a tirones y la interrupción llegando
  tarde. Medido en simulación con audio continuo: de 5 transcripciones a 2
  en 15 s, sin perder al visitante. **No vuelvas al piso normal aquí.**
  - El piso se calibra durante ~1 s al abrir el micrófono (ahí NO puede
    disparar) y luego ignora los picos, para que la voz del visitante no
    suba el listón y se quede sin oírlo.
  - Queda una transcripción "de más" cada vez que MECH pasa de callado a
    hablar (aún no conoce su nivel). Es el precio, y es barato.
  - Ajustable en vivo: Ajustes → **"Umbral al narrar"**
    (`INTERRUPT_ENERGY_FACTOR`). Súbelo si se transcribe a sí mismo; bájalo
    si no te oye al interrumpirlo.
- El listener transcribe con un **modelo de Whisper aparte limitado a
  `WHISPER_INTERRUPT_THREADS` (2) hilos de CPU** (`stt.get_interrupt_model()`,
  precargado al arrancar), para dejarle aire al reproductor de audio.
  `WHISPER_INTERRUPT_MODEL` vacío = el mismo modelo de siempre (no descarga
  nada); "tiny" es aún más ligero si se descarga una vez.
- Clips de menos de `INTERRUPT_MIN_CLIP` (0.35 s) no se transcriben: son
  golpes o sílabas sueltas.
- El listener **NO emite el nivel del micrófono** al panel: durante toda la
  narración eran ~8 eventos/s por WebSocket y el panel iba a tirones. Para
  diagnosticar está el log "Oí mientras narraba: ...".

Después hay dos caminos:

- **"oye MECH" a secas** → MECH **pregunta** «Claro, ¿de qué quieres que
  hable?» y deja `chime_pending`, así que suena el **chime de "puedes
  hablar"** (el mismo de después de "ok MECH") justo antes de abrir el
  micrófono. El banner del panel pasa a "PUEDES HABLAR".
- **"oye MECH, cuéntame otra cosa"** → `voice_phrases.strip_interrupt()` se
  queda con la petición (`mech_app.pending_command`) y el bucle de voz la
  atiende enseguida (`take_pending_command()`), **sin preguntar ni sonar el
  chime**: ya se sabe qué quiere y no hay que hacerlo esperar.

Por qué no se interrumpe solo con su propio eco:

- El umbral del VAD es relativo al **ruido ambiente medido en vivo**: con el
  parlante sonando, el piso sube y hace falta una voz claramente más fuerte
  (el mic es de solapa e inalámbrico, así que el visitante entra mucho más
  fuerte que el parlante).
- La frase pide DOS palabras juntas ("oye" + "mech"); las narraciones dicen
  "MECH" a menudo, pero casi nunca "oye".
- Si el guion que va a narrar contiene la frase, el listener **no se arranca**
  (`guard_text` en `InterruptListener.start()`).
- Y si aun así molesta en el evento: Ajustes → "Interrumpir"
  (`VOICE_INTERRUPT_ENABLED`, en vivo).

**Cómo está hecho para que reaccione rápido** (ago 2026, tras probarlo en el
robot: "lo detecta pero le cuesta, y tarda en callarse"):

- El listener **graba y transcribe en hilos separados** (cola de 1 clip, se
  queda con el más reciente). Antes hacía las dos cosas seguidas y el
  micrófono quedaba CERRADO 1-2 s en cada transcripción — justo ahí se
  perdían los "oye MECH". **No volver a hacerlo secuencial.**
- Mientras narra usa un silencio de fin de frase más corto
  (`INTERRUPT_SILENCE_TIMEOUT`, 0.6 s, contra 1.2 s del bucle normal): eso
  recorta el retardo Y hace que dispare antes (el disparo pide media
  ventana de voz). Bájalo si tarda; súbelo si corta a media frase.
- `tts.request_stop()` no se conforma con `terminate()`: espera 250 ms y si
  el reproductor sigue vivo lo mata. Devuelve cuánto tardó y el panel lo
  registra ("Voz cortada en N ms"). El rastro de voz que a veces queda
  DESPUÉS es el buffer del parlante Bluetooth (ya tiene ese audio dentro);
  eso no se puede cortar por software.

Al interrumpir, el panel registra **"Corto la narración (X s desde que
terminaste de hablar)"**: ese número es el retardo real de detección y es lo
que hay que mirar para tunear.

Si NO reacciona, el panel lo dice todo: el listener loguea **cada frase que
oye mientras narra** (`Oí mientras narraba: '...'`), así se distingue entre
"el micrófono no capta" y "Whisper entiende otra cosa". Las barras de nivel
del micrófono también se mueven durante la narración. Y el botón
**«Interrumpir narración»** de la vista Voz (`POST /api/voice/interrupt`)
dispara el corte sin micrófono: si por ahí SÍ corta, el mecanismo está bien y
el problema es de audio.

**El bucle de voz cede el micrófono mientras MECH narra**
(`mech_app.mic_release`): si no, cuando la narración se lanza desde el PANEL
el bucle sigue con el micrófono abierto esperando y el listener no puede
abrirlo. Con voz no pasaba (ese hilo está ocupado ejecutando el plan), pero
desde el panel sí.

### Subtítulos de la proyección

El guion se ve abajo de la pantalla, estilo cine, en `/projector` y en la
vista VR `/projector/vr` (uno por ojo, con la misma separación de
calibración). Se muestran haya video, imagen o pantalla vacía, y salen en el
idioma activo (son el texto que Claude acaba de escribir).

**El TIEMPO lo manda el backend, no el navegador** (ago 2026 — antes el
navegador los paceaba a ~15 car/s y se adelantaban en cada pausa de MECH):

1. `tts.speak()` pide el audio con `convert_with_timestamps` y obtiene el
   **segundo exacto de cada carácter** (`alignment`). Si el SDK o la API no lo
   soportan, cae a `convert` y avisa por consola.
2. Al arrancar la reproducción llama `on_playback({duration, lead, char_times})`.
   Ese instante es el t=0 real de la voz (ya generado el audio, y con el
   silencio inicial `AUDIO_LEAD_SILENCE` contado aparte).
3. `mech_app.start_subtitles()` lo convierte en "cues"
   (`backend/subtitles.build_cues`) y un hilo publica cada línea a su hora:
   `set_subtitle()` → evento WS `subtitle` + `state["current_subtitle"]`. Sin
   marcas de tiempo, reparte proporcional a la duración REAL (menos fino, pero
   sin acumular error).
4. Al callar (`tts.speak` retorna) → `stop_subtitles()` limpia la pantalla.

Por eso **NO devuelvas el pacing al navegador**: la página no sabe cuánto dura
el audio ni dónde respira MECH. Interruptor: `SUBTITLES_ENABLED`
(Ajustes → "Subtítulos", en vivo).

### Gestos disponibles

Definidos en `backend/gestures.py` y referenciados en el system prompt de `llm.py`:
`neutral`, `excited`, `thoughtful`, `wave`, `point`, `arms_open`.
Si añades uno nuevo, **modifica ambos archivos** y el `Literal[...]` del schema en `llm.py`.

### Dos "tamaños" de gesto (ago 2026) — NO los mezcles

El equipo pidió que MIENTRAS PROYECTA los brazos se muevan **muy poco**
("que simplemente mueva un brazo, para que no gaste casi energía"), pero que
el SALUDO siga siendo el arco amplio del video. Por eso hay dos entradas:

| Función | Cuándo | Qué hace |
|---|---|---|
| `gestures.perform(link, g)` | Saludo por cámara, giro hacia afuera, planes `mode="movement"` ("saluda al público"), botones del panel | Coreografía **completa** (`_FULL_GESTURES`): dos brazos, arco hasta 170°, a veces ruedas. |
| `gestures.perform_talking(link, g)` | Cada segmento de `execute_plan` (o sea, narrando/proyectando) | Versión **simple** (`_TALK_GESTURES`): UN brazo, máx. 115° (reposo 90), lento, **sin ruedas**, y `neutral` no manda nada. |

`NARRATION_GESTURE_MODE=full` (Ajustes → "Al narrar") devuelve las
coreografías completas también al narrar. `ARM_GESTURE_MODE` (full/subtle/off)
sigue mandando por encima de las dos.

**El saludo es lento y AMPLIO a propósito** (todo ajustable en vivo):
`ARM_WAVE_SECONDS` (2.2 s) es lo que tarda en subir y bajar; `ARM_WAVE_HIGH`
(180°) hasta dónde llega; `ARM_WAVE_SWING` (65°) y `ARM_WAVE_REPEATS` (3) las
agitadas de arriba. Antes era 170° con UN vaivén de 20° y el equipo dijo que
"casi no se notaba" (sep 2026).
**El brazo solo sube (90 → 180). Por debajo de 90 choca con el cuerpo** — el
código lo topa ahí; no bajes ese límite sin verlo en el robot.

### "Mira hacia afuera" / "Regresa a proyectar" (giro de 180°)

`backend/maneuvers.py`. En el stand MECH mira a la superficie donde proyecta;
con estas dos órdenes se pone de cara al público y vuelve.

- **Se atienden SIN pasar por Claude**: `mech_app.handle_movement_command()`
  las intercepta al principio de `handle_text_command`, así que responden al
  instante y no gastan crédito de API. Frases en `config.VOICE_OUTWARD_PHRASES`
  / `VOICE_PROJECT_PHRASES` (+ `_EN`), detección en `voice_phrases`.
- **La maniobra**: primero un tramo **lateral** (`vy`, para apartarse de la
  mesa/pared antes de rotar) y luego el **giro** (`w`). La vuelta hace lo
  mismo al revés y con el signo cambiado, así que termina donde empezó.
  Nunca usa `vx` (eso lo lleva el odómetro de `return_to_start`).
- ⚠️ **`MODE:LISTEN` FRENA LOS MOTORES.** En el firmware, `applyMode()` llama
  a `stopAllMotors()` para LISTEN/SPEAK/STOP. El bucle de voz mandaba
  `MODE:LISTEN` en CADA vuelta (cada 0.3 s mientras narra), así que cualquier
  movimiento de ruedas moría a los ~300 ms: el giro de 180° "no se movía" y
  `return_to_start()` tampoco funcionaba con el bucle de voz activo.
  Arreglado (sep 2026) en tres capas — **no deshagas ninguna**:
  1. `arduino_link.set_mode()` **no reenvía el modo que ya está puesto**
     (`force=True` solo para la reconexión, donde el Arduino se reseteó).
  2. En `server._voice_loop_worker`, el `set_mode("LISTEN")` va **justo antes
     de grabar**, no al principio de la vuelta.
  3. `mech_app.wheels_busy` (Event): mientras una maniobra mueve las ruedas,
     el bucle de voz no toca el Arduino. Lo toman `maneuvers._WheelsHeld` y
     `return_to_start()`. `_WheelsHeld` además pone el modo en **AUTO**, que
     es el único que no frena los motores.
- **POTENCIA AL MÁXIMO por defecto.** `TURN_180_SPEED`/`TURN_LATERAL_SPEED`
  valían 55/45 y no movían nada: en el firmware la velocidad se escala a PWM
  (`v * 255 / 100`), así que 55 → 140/255. Con motores de mal material y el
  L298N comiéndose ~2 V, eso no rompe la fricción estática (peor girando: las
  mecanum arrastran los rodillos de lado). Ahora el default es **100** (PWM
  255). Si el giro sale brusco, baja **los segundos**, no la velocidad.
  Además `MOTOR_KICK_SECONDS` (0.15 s) arranca cada tramo a fondo antes de
  bajar a la velocidad pedida — el truco clásico para "zumba pero no arranca".
- **Los tramos van SEPARADOS (lateral, luego giro) a propósito.** Si se
  mandan mezclados (`MOVE:0:100:100`), la normalización de `driveOmni` reparte
  y deja ruedas a 0. Mezclar = menos fuerza justo donde hace falta.
- **SIN encoders: el giro se mide POR TIEMPO.** `TURN_180_SECONDS` HAY QUE
  CALIBRARLO en el robot real — Ajustes → "Giro de 180° — Calibración"
  (en vivo, sin reiniciar). Junto con `TURN_180_SPEED`,
  `TURN_LATERAL_SECONDS`, `TURN_LATERAL_SPEED`.
- **Estado**: `state["facing"]` = `"projection"` | `"outward"`, evento WS
  `facing`, visible en la vista Arduino del panel. Un `look_outward` estando
  ya afuera no gira otra vez (un giro doble a ciegas sería irrecuperable).
- **`execute_plan` se da vuelta solo**: si le piden una historia estando de
  espaldas, vuelve a la posición de proyección antes de narrar.
- **Paro de emergencia** = `maneuvers.assume_projection()`: tras un paro no
  sabemos hacia dónde quedó, así que se asume "projection" y el operador lo
  recoloca a mano (igual que el reset del odómetro).
- Botones en el panel (vista Arduino) y endpoints `POST /api/move/outward`,
  `/api/move/projection`, `/api/move/greet`.

### Protocolo Arduino (líneas terminadas en `\n` a 115200 baud)

```
MODE:{AUTO|IDLE|LISTEN|SPEAK|STOP}
HEAD:<pan>:<tilt>          # 0-180 cada uno
ARM:{L|R}:<angle>          # 0-180
MOVE:<vx>:<vy>:<w>         # -100..100 cada uno
STOP
WHEEL:{FL|FR|BL|BR}:<vel>  # debug/calibración: UNA rueda, -100..100
LED:{OFF|IDLE|WAKE|LISTEN|THINK|SPEAK|ERR}   # aro NeoPixel estilo Alexa
```

Cinemática mecanum en `driveOmni()` del .ino. NO cambiar la fórmula sin pedir contexto al usuario.

---

## Estado actual del proyecto (actualiza esto cuando avances)

### ✅ Implementado y funcional

- Backend completo (server.py, mech_app.py, llm, stt, tts, image_gen, arduino_link, gestures).
- Firmware Arduino completo para **Arduino Uno** (4 motores DC vía 2× L298N + 2 servos de brazos; pines ya mapeados).
- Frontend completo (panel + projector + PWA).
  - **Banner de fase de voz** siempre visible: off → waiting ("PUEDES HABLAR",
    señal para decirle al juez que hable) → listening → transcribing → thinking
    → speaking. Lo alimenta `mech_app.set_voice_phase()` vía el callback
    `on_phase` de `stt.listen_once()`. Estado en `state["voice_phase"]`.
  - **Vista Ajustes** (sidebar del panel): tunea en vivo VAD, timeout de
    silencio, silencio inicial del parlante y espera máxima (`POST /api/config`,
    sin reiniciar); guarda en `.env` micrófono, sample rate, modelo Whisper y
    voice_id (requieren reiniciar). Prueba de TTS (`POST /api/tts/test`) y
    lista de micrófonos (`GET /api/audio/devices`).
- **Control de voz por palabra clave** (server.py `_voice_loop_worker`): el
  bucle tiene dos estados (`state["voice_awake"]`). En reposo el micrófono
  sigue abierto pero solo reacciona a las frases de despertar
  (`VOICE_WAKE_PHRASES`, ej. "ok MECH" / "despierta MECH") — no llama a Claude ni gasta
  créditos. Despierto, una frase de reposo (`VOICE_SLEEP_PHRASES`, ej. "para
  de escuchar") lo duerme. Con `VOICE_AUTOSTART=true` el server arranca el
  bucle en reposo, así MECH espera "ok MECH" sin tocar el panel. El
  botón del panel sigue siendo el apagado/encendido TOTAL (suelta el mic).
  Fase nueva del banner: `dormant`. Métodos `mech_app.go_awake/go_dormant`.
  Detección de frases en `backend/voice_phrases.py` (match por palabras en
  cualquier orden, sin acentos). El reposo/despertar solo se evalúa ENTRE
  turnos; MIENTRAS narra solo se escucha la frase de interrupción
  ("oye MECH", ver más abajo), nada más.
  El mensaje de `go_dormant` NO contiene la palabra "despierta" (si no, el
  mic captaría el eco del parlante y MECH se despertaría solo). Tras
  go_dormant/go_awake hay un `time.sleep(0.8)` para drenar el parlante.
  `tts.request_stop()/clear_stop()` permiten cortar la voz en curso (lo usa
  el paro de emergencia); `tts._play_audio` usa `subprocess.Popen` para ser
  interrumpible.
- **Voces dinámicas por personaje** (`backend/voices.py`): catálogo con
  `voice_id` por personaje, campo `voice` en el `Segment`, `tts.speak()` acepta
  `voice_id`. Rellenar los `voice_id` en `voices.py` para activarlas (ej. voz
  del Hidalgo para Don Quijote). Fallback a la voz default si está vacío.
- Launchers Windows.
- Documentación (GUIA.md, FRONTEND.md, PRUEBAS_HARDWARE.md, windows/README.md).
- **Biblioteca de videos pre-renderizados (Opción B)** — manifest, schema, dispatch
  en execute_plan, fallback a NanoBanana, UI `/library` para subir mp4s,
  endpoints REST `GET/POST/DELETE /api/library/...`. Obras actuales:
  `don_quijote`, `campana_1856`, `jimenez_deredia`, `malpais`,
  `isidro_con_wong` (4 segmentos c/u).
- **Música de fondo bajo la narración** (`backend/background_audio.py`): obras
  marcadas con `music: True` en `WORKS` (solo `malpais`) admiten un sample
  `video_library/<slug>/music.<ext>` que suena en bucle a bajo volumen
  (`ffplay`, `BACKGROUND_MUSIC_VOLUME`) mientras MECH narra; el TTS sale por
  encima (lo mezcla PipeWire). Claude lo activa con el campo `Plan.background_music`
  (slug). Se sube en `/library` (slot extra) y se sirve por `POST/DELETE
  /api/library/{slug}/music`. Requiere `ffplay` (paquete ffmpeg) en la Pi.
- **Wake word "ok MECH"** — es el comando principal (variantes "okay/okey/ok
  mek/oye mech" en `VOICE_WAKE_PHRASES`). `voice_phrases.py` además tolera
  1 letra de error (levenshtein ≤1 en palabras de 4+ letras). OJO: si el
  `.env` de la Pi define `VOICE_WAKE_PHRASES` viejo, tapa el default — borrar
  la línea o añadir "ok mech".
- **Detección de voz híbrida anti-ruido** (`stt.record_until_silence`): mide
  el piso de ruido ambiente (RMS adaptativo: baja rápido, sube lento, y NO se
  actualiza mientras graba) y solo dispara si webrtcvad dice voz Y la
  amplitud supera `piso × VAD_ENERGY_FACTOR` (live, slider "Umbral ruido").
  El fin de frase = la amplitud cae cerca del piso (la "caída de onda"). En
  reposo cada grabación se corta a `WAKE_MAX_UTTERANCE` (4 s) para revisar el
  wake rápido. `on_level` emite `mic_level` por WS (barras reales en panel).
  Esto se hizo porque en la olimpiada el ruido impedía que MECH despertara.
- **Aro de LEDs estilo Alexa Echo** (NeoPixel 12 en A2 del Arduino): firmware
  con animaciones no bloqueantes (`LED:` OFF/IDLE/WAKE/LISTEN/THINK/SPEAK/ERR).
  `mech_app.set_voice_phase()` lo sincroniza solo: reposo=respiración tenue,
  "ok MECH"=barrido WAKE, puedes hablar=cometa girando, pensando=pulso,
  narrando=fijo (fijo a propósito: show() repetidos hacen temblar los servos).
  Paro de emergencia = ERR (rojo). Ver docs/PRUEBAS_HARDWARE.md §6.
- **Gestos reales con movimiento suave** (`gestures.py` reescrito): modo
  `full` (default) con coreografía por gesto (wave oscila el brazo derecho,
  excited brazos arriba con rebote + balanceo de ruedas, point/arms_open/
  thoughtful sostienen pose) interpolando en pasos de 30 ms (nada de saltos).
  `GESTURE_WHEELS` (live) habilita los movimientos cortos de ruedas; si la
  visión sabe dónde está el usuario, MECH gira hacia él antes del gesto.
  Modos `subtle`/`off` siguen disponibles (selector en Ajustes).
- **Arduino robusto**: `arduino_link.py` autodetecta el puerto (busca
  "Arduino"/"CH340"/ACM en los puertos serie) y reintenta conectar cada 4 s
  en segundo plano (server puede arrancar sin Arduino, o sobrevivir a un
  desenchufe). `on_status` actualiza `state["arduino_connected"]` en vivo y
  al reconectar re-manda el MODE y el patrón de LED vigentes.
  `POST /api/arduino/reconnect` + botón en la vista Firmware.
- **Visión completa** (`backend/vision.py`): C930e por OpenCV (MJPG forzado,
  640×360 @10fps) + MediaPipe Face Detection (full-range). Estima distancia
  por el ancho de la cara (~16 cm, focal ≈320 px para FOV 90°). Publica
  `state["vision"]` + evento WS `vision` (panel: Sensores → Cámara y tarjeta
  en Ajustes). Comportamientos: saludo al detectar usuario
  (`mech_app.on_user_detected`), girar para seguirlo (`VISION_FOLLOW`),
  acercarse hasta `VISION_MIN_DISTANCE` (`VISION_APPROACH`; solo en fases
  waiting/dormant/off, nunca narrando; siempre STOP al perderlo) y **gate de
  proyección** (`VISION_PROJECT_GATE`: sin usuario dentro de la distancia
  mínima, narra sin proyectar — se evalúa una vez por plan en
  `execute_plan`). Imports de cv2/mediapipe perezosos: sin instalar, el
  server corre igual. On/off con `POST /api/vision/{on|off}` (persiste
  `VISION_ENABLED` en .env) o toggle en Ajustes; el resto de claves
  `VISION_*` son live.
- **Nombre del robot: MECH-1** (el usuario lo dejó así "por el momento",
  4 jul 2026). PHOTON se propuso y se DESCARTÓ. Si el usuario retoma el
  renombre, hay candidatos ya validados contra `voice_phrases.py` (cero
  colisiones con palabras comunes): TÓTEM, ORFEO, CÓDICE, MORFEO. NO proponer
  nombres a 1 edición de palabras comunes (la tolerancia lev≤1 del matcher los
  dispararía solos: musa→mesa, mito→moto, domo→como, faro→paro, fotón→foto…).
- **Sitio web de presentación (`web/`)**: one-page estático en español con la
  estética del proyecto (dark `#0e0e12`, Sora/Space Mono, logo oficial en SVG).
  FUENTE DE CONTENIDO: el trabajo escrito nuevo `Documentación/Proyecto
  MECH.pdf` (IEEE, jul 2026), que amplió la misión de solo cultura a
  **generar interés en cultura, educación, salud, economía e historia**
  (eslogan «si es inmersivo, es MECH»). Estructurado en DOS capítulos:
  **01·LA EMPRESA** (columna lateral sticky con logo+eslogan+índice; qué es
  M.E.C.H en 2×2, "un robot muchos mundos" con las 5+ aplicaciones,
  problemática, ventaja competitiva vs Alexa en formato "versus", impacto
  RESPALDADO por 3 estudios reales —Fuentes-Moraleda +40%, Magdin, Zhang—,
  BMC, y equipo con FOTOS reales de estudio —`assets/team-{leo,ale,jimmy}.jpg`,
  recortadas de `branding/{Leo,Ale,Jimmy}.png`— y roles nuevos: Mecatrónica /
  Mecánica / Circuitos, Colegio Científico de Alajuela) y **02·EL ROBOT**
  (banner horizontal MECH-1 con stats y render, showcase con scroll estilo
  Apple de 4 tomas, pipeline, hardware+construcción con dims reales
  —PVC 52×66 cm, coroplast—, **timeline de evolución MECH-1→MECH-2→MECH-3**
  —MECH-2 añade lentes VR y autonomía—, obras en tira deslizable, bitácora de
  construcción). Hero con typing "ok MECH" y aro LED CSS. Sin build ni
  dependencias: doble click a `web/index.html`. El showcase y el banner buscan
  `assets/robot-01.jpg`/`robot-02.jpg`; si faltan, render SVG (`robotRenderTpl`).
  El usuario preguntó por React y se decidió NO usarlo (sin beneficio).
  **Motion pulido con las skills de Emil Kowalski** (`.agents/skills/`, tras
  `npx skills add emilkowalski/skill`): curvas propias `--ease-out`/
  `--ease-in-out`, feedback `:active{scale(.97)}` en botones, hover SOLO bajo
  `@media (hover:hover) and (pointer:fine)`, stagger real (contenedor `.stagger`
  → cascada en hijos vía app.js), reduced-motion = cross-fade, nav translúcido.
- **Logo en alta calidad (`branding/`)**: `logo-mech.jpg` (4500×2000, fondo
  `#0e0e12`) y `logo-mech.pdf` (300 dpi) — la versión del sitio (marco
  redondeado con skew 8° + "MECH" en Sora ExtraBold con itálica sintética),
  generados con PIL + fuente Sora variable descargada de google/fonts.
- **Base «Información nuestra» (`backend/informacion_nuestra.py`)**: datos
  OFICIALES sobre MECH/el equipo/el proyecto (identidad, equipo, problemática,
  impacto, hardware, software, innovaciones, desafíos, contacto), inyectados
  al system prompt con regla de exactitud (responder SOLO con esos datos; si
  falta algo, decirlo en vez de inventar). FUENTE: trabajo escrito del equipo
  (volcado vía web/index.html) + bitácora del repo. Si MECH dice algo falso
  sobre el proyecto → añadir el dato correcto ahí (igual que los `facts` de
  las obras). Se concatena en `llm.plan_response()`.
- **`facts` + `sources` completos para las 5 obras** (`video_library.py`):
  datos verificados por búsqueda web (jul 2026) con URLs de respaldo en el
  campo `sources` (solo documentación para humanos; NO se inyecta al prompt).
  Claves: Fidel Gamboa (1961–2011, músico), Isidro Con Wong FALLECIÓ el
  1 set 2024, Deredia primer escultor latinoamericano en la Basílica de San
  Pedro (2000), Batalla de Rivas 11 abr 1856, Quijote 1605/1615.
- **Proyección en Google Cardboard** (`/projector/vr` o `/proyector/vr` →
  `frontend/cardboard.html`): vista estéreo lado a lado con lo mismo que
  `/projector`. Se abre EN EL TELÉFONO (misma wifi que la Pi); tocar el centro
  = fullscreen + lock landscape + mantener pantalla encendida (Wake Lock si hay
  HTTPS; si no, truco de video invisible con canvas.captureStream). Se mete al
  visor. Detalles clave:
  - **Una sola decodificación**: la imagen/video se decodifica UNA vez y se
    pinta a los dos ojos con `<canvas>` + `requestAnimationFrame`. Antes había
    dos `<video>` del mismo archivo y el ojo derecho PARPADEABA (los teléfonos
    suelen tener un único decodificador de video por hardware). NO volver a
    duplicar el elemento de video.
  - **Calibración SEPARACIÓN + ZOOM** (botón "AJUSTAR VR", guardada en
    `localStorage`): si en el visor se ve "doble", la separación entre las dos
    imágenes no coincide con la distancia interocular; se ajusta a mano una vez.
    Por eso NO hace falta el QR del visor (ese solo lo usan apps con SDK de
    Cardboard; para estéreo plano la separación ajustable lo resuelve). WebXR
    se descartó porque exige HTTPS.
  - Estéreo "plano" (sin corrección de distorsión de lente). Aviso de girar el
    teléfono en portrait.
- **Vista Arduino del panel actualizada**: se quitó la tarjeta CABEZA (el
  robot no tiene cabeza móvil; `API.headLive` eliminado de app.js), tarjeta
  nueva de ARO DE LEDS (botones LED:WAKE/LISTEN/…) y COMANDO CRUDO con chips
  de plantillas (`API.rawPreset`) + referencia del protocolo y mapa de pines
  real (giro solo FL+BR, servos 9/10, aro A2). Verificado en preview estático.
- **Movimiento autónomo solo adelante/atrás + odómetro (jul 2026)**: la
  visión ya no gira hacia el usuario (toggle "Seguir" eliminado del panel;
  `VISION_FOLLOW` queda sin efecto) y los gestos solo balancean adelante/
  atrás. `arduino_link` integra vx·tiempo (odómetro `net_forward()`/
  `reset_odometer()`); `mech_app.return_to_start()` revierte el
  desplazamiento (tope 6 s) al inicio de CADA `execute_plan`, para que el
  proyector vuelva a su punto calibrado. Paro de emergencia = reset del
  odómetro. Girar es manual desde el panel (estilo carro).
- **Saludo al detectar usuario (calibrado con videos del equipo, jul 2026)**:
  al ver a alguien, MECH dice «¡Hola! Soy MECH. Un gusto verte hoy aquí»
  (`mech_app.GREETING_TEXT`, cooldown 60 s, no interrumpe narraciones) y hace
  el **protocolo de saludo**: UN arco amplio y lento del brazo derecho
  (90→170, vaivén arriba, baja) — video 1 del equipo. El bucle de voz ignora
  transcripciones mientras dura el saludo (`mech_app.greeting_until`) para no
  procesar su propio eco. Los gestos AL HABLAR son pequeños (máx ~125°,
  `_TALK_MAX` en gestures.py): no girar todo el brazo — video 2 del equipo.

- **Modo inglés bajo demanda (ago 2026)** — `backend/lang.py` guarda el idioma
  activo. «wake up MECH» despierta en INGLÉS (Whisper en `en`, narración de
  Claude en inglés, frases fijas y subtítulos en inglés); «ok MECH» /
  «despierta MECH» sigue en español. Al dormirse vuelve a español solo. En
  reposo se re-transcribe el audio en el otro idioma si el primero no dio
  wake, para no perder «wake up MECH» por un error de Whisper. Chips ES/EN en
  la vista Voz del panel (`POST /api/language/{es|en}`) para probar sin voz.
  Claves nuevas: `WAKE_ENGLISH_ENABLED`, `VOICE_WAKE_PHRASES_EN`,
  `VOICE_SLEEP_PHRASES_EN`.
- **Subtítulos en la proyección (ago 2026)** — `frontend/subtitles.js` (compartido
  por `/projector` y `/projector/vr`) muestra el guion abajo, estilo cine, haya
  video, imagen o nada. Lo alimenta `mech_app.set_subtitle()` (evento WS
  `subtitle` + `state["current_subtitle"]`, para que la VR los reciba también
  por el sondeo HTTP, ahora cada 0.9 s). Idioma = el activo. Toggle en Ajustes
  (`SUBTITLES_ENABLED`, en vivo).
- **Subtítulos sincronizados con la voz real (ago 2026)** — el ritmo lo lleva
  el backend con las marcas de tiempo por carácter de ElevenLabs
  (`tts._synthesize` → `on_playback` → `mech_app.start_subtitles` →
  `backend/subtitles.build_cues`). Antes se estimaban en el navegador a
  ~15 car/s y se adelantaban en cada pausa de MECH. Respaldo automático
  (reparto proporcional) si la API no devuelve las marcas.

- **Movilidad al día (ago/sep 2026)** — cuatro cosas:
  1. **Giro de 180°** con `maneuvers.py`: «mira hacia afuera» gira (lateral +
     rotación), saluda al público y lo anuncia; «regresa a proyectar» deshace
     el giro exacto. Sin pasar por Claude. `state["facing"]` en el panel.
     ⚠️ `TURN_180_SECONDS` se calibra en el robot (Ajustes, en vivo).
  2. **Saludo por cámara arreglado**: el brazo y la voz van JUNTOS y bajo el
     MISMO cooldown (`GREETING_COOLDOWN`, 45 s). Antes el brazo se disparaba
     en CADA detección, también dentro del cooldown — y como la visión se
     pausa mientras narra, al terminar cada narración "redetectaba" y el
     brazo se movía solo, sin decir nada. Botón «SALUDAR AHORA» en el panel
     (`POST /api/move/greet`) para probarlo sin usar la cámara.
  3. **Saludo más lento**: `ARM_WAVE_SECONDS` (2.2 s, antes 1.3 fijos).
  4. **Gestos mínimos al proyectar**: `perform_talking()` mueve UN solo brazo,
     máx. 115°, sin ruedas (`NARRATION_GESTURE_MODE=simple`). Los planes
     `mode="movement"` ("saluda al público") siguen con el gesto completo.
- **Interrupción por voz mientras narra (ago 2026)** — "oye MECH" (es) /
  "hey MECH" (en) corta la presentación en cualquier momento:
  `backend/interrupt_listener.py` + `mech_app._on_interrupt()`. Si la frase
  trae petición pegada ("oye MECH, háblame de Malpaís"), se atiende enseguida
  sin repetirla. Guarda anti-eco (umbral relativo al ruido, dos palabras,
  `guard_text`) y switch en Ajustes (`VOICE_INTERRUPT_ENABLED`).

### 🚧 Pendiente

- **Copiar las fotos reales del robot terminado** a `web/assets/robot-01.jpg`
  (frontal, la de la sala con la banda de píxeles) y `web/assets/robot-02.jpg`
  (tres cuartos) para que el showcase de la web use fotos en vez del render SVG.
- **Generar los videos pre-renderizados** para cada obra (Kling/Veo/Runway en otra máquina) y subirlos vía `/library`. Hasta que estén, MECH cae a NanoBanana para esas obras automáticamente.
- **Cablear y probar el Arduino Uno** — firmware ya mapeado (`mech_controller.ino`, fqbn `arduino:avr:uno`). Falta: conseguir 2× L298N, cablear motores + servos (servos con 5–6V de protoboard), flashear y probar por serial.
- **Aro NeoPixel: EN PAUSA** (decisión jul 2026, no se usa por el momento; `#define MECH_LEDS 0`). Si el equipo lo retoma: DIN→A2, 5V del Arduino, GND común, librería Adafruit NeoPixel, `MECH_LEDS 1`.
- **Probar la visión en la Pi real**: `pip install opencv-python-headless` basta (la visión cae al detector Haar de OpenCV, que corre en cualquier Python incl. 3.13). Para el modo full-range instalar además `mediapipe` (solo Python 3.11/3.12; ver `backend/requirements-vision.txt`). `vision.py` elige el mejor detector disponible y loguea cuál (`mediapipe` u `opencv-haar`). Enchufar la C930e, encender visión desde Ajustes. Calibrar `VISION_MIN_DISTANCE` y la constante `FACE_WIDTH_M`/`FOCAL_PX` de `vision.py` si la distancia estimada sale corrida (medir con cinta métrica a 1 m y comparar con lo que muestra el panel).
- **Probar el despertar con ruido**: ajustar el slider "Umbral ruido" (VAD_ENERGY_FACTOR) en el lugar del evento. Si MECH no despierta: bajarlo; si graba fantasmas: subirlo.
- **Selección de dispositivo de audio**: ✅ resuelto. `stt.py` usa `config.AUDIO_INPUT_DEVICE` (de `.env`) para elegir el mic. El mic del proyecto es el **Steren MIC-9010** (receptor USB); la C930e queda solo para video. Si hay varios dispositivos de captura, poner en `.env` `AUDIO_INPUT_DEVICE=Steren` (o el índice que muestre `sounddevice`).

---

## Gotchas frecuentes

1. **OneDrive sync** puede impedir `git worktree move` y otros renombrados. Si una operación de archivo falla con "Permission denied" en Windows, sospechar de OneDrive.
2. **Whisper descarga el modelo en la primera ejecución** (~150 MB para `base`). Tarda ~30s sin red feedback. No es un freeze.
3. **El Arduino se resetea cuando se abre el puerto serial.** El `arduino_link.connect()` espera 2s después de abrir. No reducir ese sleep.
4. **`temperature`/`top_p`/`top_k`/`budget_tokens` no van con Claude Opus 4.7.** Devuelven 400. El código actual ya está alineado (usa `thinking: {type: "adaptive"}`).
5. **Modelo Claude**: siempre `claude-opus-4-7` (alias correcto; no añadir sufijo de fecha).
6. **Microcontrolador = Arduino Uno R3** (ATmega328P). El RoboKit RS de Roborobo se descartó: no acepta control en vivo desde la Pi (corre programas Rogic cerrados, sin recibir serial). El Arduino se controla por USB con `arduino_link.py`. Subir firmware con `arduino:avr:uno`.
7. **`python -m backend.projector`** (tkinter) y el visor browser-based en `/projector` son alternativas. Para producción usar el browser.
8. **El paquete Chromium en Raspberry Pi OS Bookworm es `chromium`**, no `chromium-browser` (aunque el binario sigue existiendo bajo ambos nombres).
9. **La red wifi del evento puede tener client isolation** (común en colegios/eventos). Si Windows no ve la Pi por IP aunque estén en la misma red, ese es el problema. Hotspot del celular como respaldo.
10. **Modo standalone (`python -m backend.main`) NO muestra videos pre-renderizados.** El visor tkinter solo sabe de imágenes. Para ver videos hace falta `python -m backend.server` + `/projector` en navegador. `main.py` loguea el slug/segmento del video y sigue con la narración/gesto.
11. **Slug del video_library debe coincidir con el subdirectorio.** Si añades una obra al manifest pero la carpeta se llama distinto, `available_works()` la reporta como incompleta y no aparece a Claude.
11b. **Datos erróneos en la narración = alucinación del modelo.** Si MECH dice un dato falso de una obra (fecha, biografía, profesión), NO es un bug de código: el modelo lo inventó porque no se lo dimos. Solución: añade el dato correcto al campo `facts: [...]` de esa obra en `video_library.py`. Esos "Datos verificados" se inyectan al system prompt con una regla anti-invención. Sonnet alucina más que Opus en esto; por eso los `facts` importan más si se usa Sonnet. (Ej. ya corregido: Fidel Gamboa de Malpaís murió en 2011 y fue músico, no médico.)
12. **Sample rate del micrófono ≠ el que usa Whisper.** Muchos mics USB baratos (Steren MIC-9010 / "WXMH mini") NO abren a 16000 Hz y dan `Invalid sample rate [PaErrorCode -9997]`. Por eso `AUDIO_SAMPLE_RATE=48000` (captura). **faster-whisper exige arrays a 16000 Hz y NO resamplea solo**: `stt.py` captura a 48000 (para VAD) y **resamplea a 16000** (`WHISPER_SAMPLE_RATE`) antes de transcribir. Si se pasa audio a otra tasa, Whisper lo "oye" 3× más rápido, transcribe basura y **alucina** el contenido del `initial_prompt`. Por eso ese prompt ya NO lista títulos de obras.
13. **El `.env` del panel.** La vista Ajustes escribe `backend/.env` con `config.update_env_file()`. Solo las claves en `_LIVE_KEYS` (server.py) se aplican sin reiniciar (VAD, umbral de ruido, silencios, idioma, visión, gestos); las demás (mic, sample rate, modelo, voice_id) necesitan reiniciar el server.
14. **`VOICE_WAKE_PHRASES` en el `.env` de la Pi tapa el default.** Si "ok mech" no despierta a MECH, revisar si el `.env` tiene esa clave con la lista vieja ("despierta mech,...") y borrarla o añadirle "ok mech".
15. **NeoPixel + servos**: `ring.show()` bloquea interrupciones un instante; por eso el patrón SPEAK es fijo (se pinta una vez) y las animaciones solo corren cuando los brazos están quietos. No añadir animaciones al estado SPEAK.
16. **El idioma se decide en el DESPERTAR, no en medio de la conversación.**
    Si alguien le habla en inglés a un MECH despierto en español, Whisper
    transcribe con el modelo español y sale basura: hay que dormirlo y
    despertarlo con «wake up MECH» (o decir «wake up MECH» estando despierto,
    que cambia el idioma). Es a propósito: así el stand no cambia de idioma
    por accidente.
17. **`VOICE_WAKE_PHRASES_EN` en el `.env` de la Pi tapa el default**, igual
    que la lista en español. Si «wake up MECH» no funciona, revisar esa clave.
18. **Si MECH se corta solo a media narración**, es el eco de su parlante
    disparando la frase de interrupción: subí el "Umbral ruido" en Ajustes o
    apagá "Interrumpir" (`VOICE_INTERRUPT_ENABLED=false`). Y si NO se deja
    interrumpir, revisá que el `.env` de la Pi no tenga
    `VOICE_INTERRUPT_PHRASES` con otra lista.
19. **Si las ruedas "no se mueven", sospecha de `MODE:LISTEN` ANTES que del
    código de movimiento.** En el firmware ese comando llama a
    `stopAllMotors()`. Comprobación rápida: `MOVE:0:0:100` desde el panel
    (vista Arduino → comando crudo) con el bucle de voz APAGADO. Si ahí se
    mueve y con el bucle encendido no, es esto. Ver la sección del giro.
20. **Velocidad ≠ potencia.** El firmware escala `v * 255 / 100`: velocidad
    50 son 127/255 de PWM, y con estos motores + L298N eso normalmente solo
    zumba. Para probar movimiento SIEMPRE usa 100.
21. **El giro de 180° no tiene encoders: se mide por TIEMPO.** Si MECH se
    queda a 90° o se pasa, NO es un bug — hay que calibrar `TURN_180_SECONDS`
    en Ajustes (en vivo). Cambiar de batería, de suelo o de ruedas obliga a
    recalibrarlo. Si el giro sale al revés (gira hacia el lado equivocado),
    voltear el signo de `w` en `driveOmni()` del .ino, no en `maneuvers.py`.
22. **`VOICE_OUTWARD_PHRASES` / `VOICE_PROJECT_PHRASES` en el `.env` de la Pi
    tapan el default**, igual que las de wake/sleep/interrupt.
23. **cv2/mediapipe son opcionales**: `vision.py` los importa perezosamente; si faltan, `start()` loguea el aviso y el server sigue. No mover esos imports al nivel de módulo.

---

## Cómo trabajar con este usuario

- **Pasos pequeños y concretos.** "Pega esto, dime qué sale." No abrumes con explicación teórica.
- **Cuando algo falla en su consola**, pídele el mensaje EXACTO antes de adivinar.
- **No empujes Tauri / Electron / refactors grandes** salvo que pregunte. El stack actual (FastAPI + Edge --app + PWA) ya cubre lo que necesita.
- **Confirma el alcance antes de tocar muchos archivos.** El usuario prefiere cambios chicos y revisables.
- **Antes de instalar dependencias nuevas**, mira si ya hay algo equivalente en `requirements.txt`.
- **Después de cualquier cambio relevante**, actualiza la sección "Estado actual" arriba.

---

## Recursos de referencia

- Anthropic Claude API docs: https://platform.claude.com/docs
- Gemini Image API: https://ai.google.dev/gemini-api/docs/image-generation
- ElevenLabs Python SDK: https://github.com/elevenlabs/elevenlabs-python
- faster-whisper: https://github.com/SYSTRAN/faster-whisper
- OpenCV VideoCapture (V4L2): https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html
- Logitech C930e datasheet: https://www.logitech.com/en-us/products/webcams/c930e-business-webcam.html
- MediaPipe Face Detection: https://developers.google.com/mediapipe/solutions/vision/face_detector

---

**Si actualizas algo significativo en el código, actualiza también este archivo. La siguiente sesión depende de que esto refleje la realidad.**
