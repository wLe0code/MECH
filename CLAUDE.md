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
| Visualización | Proyector HDMI desde la Pi + Chromium kiosko a `/projector` | |

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
- **Aro de LEDs (WS2812/NeoPixel 12 LEDs, estilo Alexa):** DIN = pin **A2** (con ~330 Ω en serie), VCC al **5V del Arduino** (brillo limitado a 60/255 — NO a la fuente de 6V de los servos), GND común. Requiere librería **Adafruit NeoPixel**; sin aro, poner `#define MECH_LEDS 0` en el .ino y compila sin ella. El backend sincroniza el aro con la fase de voz (`mech_app.set_voice_phase` → `LED:<patrón>`).
- **Sin cabeza:** el comando `HEAD` se reconoce pero es un no-op (no rompe el lado de la Pi; los gestos siguen con los brazos).

Subir con `arduino:avr:uno`. Servos alimentados con 5–6V externos (protoboard), GND común. Si una rueda gira al revés, intercambia sus 2 cables o sus pines IN1/IN2.

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
  stt.py              ← faster-whisper local + VAD (webrtcvad).
  tts.py              ← ElevenLabs streaming.
  image_gen.py        ← Gemini / NanoBanana. Fallback de visual cuando
                        no hay video pre-renderizado.
  video_library.py    ← Manifest de obras + helpers para resolver paths/URLs
                        y componer la sección dinámica del system prompt.
  video_library/      ← Carpeta con los .mp4 (gitignored). Estructura:
                        <slug>/seg01.mp4, seg02.mp4, ...
  arduino_link.py     ← Serial al Arduino. Protocolo de texto líneas \n.
                        Auto-reconexión + autodetección de puerto + LED:.
  gestures.py         ← Coreografías reales de gestos (wave, excited...)
                        con interpolación suave; modos full/subtle/off;
                        opcionalmente mueve ruedas (GESTURE_WHEELS).
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
                        Maneja eventos image y video, con loop en video.
  library.html        ← UI sencilla en /library para subir videos
                        pre-renderizados (Opción B).
  manifest.json       ← PWA instalable.
  sw.js               ← Service worker.
  icon.svg

arduino/mech_controller/
  mech_controller.ino ← Firmware. Modos: AUTO/IDLE/LISTEN/SPEAK/STOP.
                        Comandos: MODE, HEAD, ARM, MOVE (omnidireccional), STOP.

web/                  ← Sitio de PRESENTACIÓN del proyecto (NO es el panel).
  index.html          ← One-page: hero, qué es, showcase scroll estilo Apple,
                        cómo funciona, hardware, obras, construcción, equipo.
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

- **Strings al usuario (UI, voz, logs)** → siempre español neutro.
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

### Gestos disponibles

Definidos en `backend/gestures.py` y referenciados en el system prompt de `llm.py`:
`neutral`, `excited`, `thoughtful`, `wave`, `point`, `arms_open`.
Si añades uno nuevo, **modifica ambos archivos** y el `Literal[...]` del schema en `llm.py`.

### Protocolo Arduino (líneas terminadas en `\n` a 115200 baud)

```
MODE:{AUTO|IDLE|LISTEN|SPEAK|STOP}
HEAD:<pan>:<tilt>          # 0-180 cada uno
ARM:{L|R}:<angle>          # 0-180
MOVE:<vx>:<vy>:<w>         # -100..100 cada uno
STOP
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
  turnos (MECH no escucha mientras narra, por decisión del usuario).
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
- **Sitio web de presentación (`web/`)**: one-page estático en español con la
  estética del proyecto (dark `#0e0e12`, Sora/Space Mono, logo oficial del
  trabajo escrito recreado en SVG). Secciones: hero con typing "ok MECH" y aro
  LED animado en CSS, qué es M.E.C.H, problemática, showcase con scroll estilo
  Apple (4 tomas del robot con captions; sticky + crossfade), pipeline de cómo
  funciona, hardware por capas (con el diagrama del PDF), las 5 obras de la
  biblioteca, bitácora de construcción (7 fotos extraídas de
  `Documentación/MECH.pdf` con pypdf), impacto social + Business Model Canvas,
  equipo y footer con contactos (GitHub, IG @wr0mech, wromech@gmail.com).
  Sin build ni dependencias: doble click a `web/index.html`. El showcase busca
  `assets/robot-01.jpg` (frontal) y `assets/robot-02.jpg` (tres cuartos); si
  faltan, muestra un render SVG del robot (template `robotRenderTpl`).

### 🚧 Pendiente

- **Copiar las fotos reales del robot terminado** a `web/assets/robot-01.jpg`
  (frontal, la de la sala con la banda de píxeles) y `web/assets/robot-02.jpg`
  (tres cuartos) para que el showcase de la web use fotos en vez del render SVG.
- **Generar los videos pre-renderizados** para cada obra (Kling/Veo/Runway en otra máquina) y subirlos vía `/library`. Hasta que estén, MECH cae a NanoBanana para esas obras automáticamente.
- **Cablear y probar el Arduino Uno** — firmware ya mapeado (`mech_controller.ino`, fqbn `arduino:avr:uno`). Falta: conseguir 2× L298N, cablear motores + servos (servos con 5–6V de protoboard), flashear y probar por serial.
- **Comprar/cablear el aro NeoPixel de 12 LEDs** (DIN→A2, 5V del Arduino, GND común) e instalar la librería Adafruit NeoPixel. Hasta entonces: `#define MECH_LEDS 0`.
- **Probar la visión en la Pi real**: `pip install opencv-python-headless mediapipe`, enchufar la C930e, encender visión desde Ajustes. Calibrar `VISION_MIN_DISTANCE` y la constante `FACE_WIDTH_M`/`FOCAL_PX` de `vision.py` si la distancia estimada sale corrida (medir con cinta métrica a 1 m y comparar con lo que muestra el panel).
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
12. **Sample rate del micrófono ≠ el que usa Whisper.** Muchos mics USB baratos (Steren MIC-9010 / "WXMH mini") NO abren a 16000 Hz y dan `Invalid sample rate [PaErrorCode -9997]`. Por eso `AUDIO_SAMPLE_RATE=48000` (captura). **faster-whisper exige arrays a 16000 Hz y NO resamplea solo**: `stt.py` captura a 48000 (para VAD) y **resamplea a 16000** (`WHISPER_SAMPLE_RATE`) antes de transcribir. Si se pasa audio a otra tasa, Whisper lo "oye" 3× más rápido, transcribe basura y **alucina** el contenido del `initial_prompt`. Por eso ese prompt ya NO lista títulos de obras.
13. **El `.env` del panel.** La vista Ajustes escribe `backend/.env` con `config.update_env_file()`. Solo las claves en `_LIVE_KEYS` (server.py) se aplican sin reiniciar (VAD, umbral de ruido, silencios, idioma, visión, gestos); las demás (mic, sample rate, modelo, voice_id) necesitan reiniciar el server.
14. **`VOICE_WAKE_PHRASES` en el `.env` de la Pi tapa el default.** Si "ok mech" no despierta a MECH, revisar si el `.env` tiene esa clave con la lista vieja ("despierta mech,...") y borrarla o añadirle "ok mech".
15. **NeoPixel + servos**: `ring.show()` bloquea interrupciones un instante; por eso el patrón SPEAK es fijo (se pinta una vez) y las animaciones solo corren cuando los brazos están quietos. No añadir animaciones al estado SPEAK.
16. **cv2/mediapipe son opcionales**: `vision.py` los importa perezosamente; si faltan, `start()` loguea el aviso y el server sigue. No mover esos imports al nivel de módulo.

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
