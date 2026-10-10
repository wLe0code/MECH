# CLAUDE.md — contexto para futuras sesiones de Claude Code

Este archivo es tu primer punto de referencia al abrir una sesión nueva en este repo. Léelo COMPLETO antes de hacer cualquier cambio o sugerencia. Está escrito para ti (Claude), no para el usuario.

> ⚠️ **REVERSIÓN (23 sep 2026) — léelo antes de proponer nada.** El equipo
> pidió volver al código del commit `c0e0310` («trasluce mech»), que era el
> que funcionaba bien. **Se quitó a propósito** todo lo que vino después:
> la subida de volumen para los parlantes alámbricos Logitech S150
> (`TTS_GAIN_DB`, `TTS_NORMALIZE`, `pi/volumen-max.sh` — **ya no se usan esos
> parlantes**), el gesto "67" por cámara, el traductor continuo, la trivia
> (⚠️ **recuperada el 25 sep a pedido del equipo**, estilo Kahoot — ver su
> sección),
> el arreglo del reposo con redes extra, la medición del micrófono al
> arrancar, la fase `loading`, los reintentos de cámara/micrófono,
> `docs/USO.md`, y los 4 commits de la noche del 22 sep («Conexiones a prueba
> de todo»: el micrófono en un proceso aparte `_mic_worker.py`, `wav_play.py`,
> la detección de "8 s sin datos", la carpeta `tests/` y `LEEME-ARREGLOS.md`).
> **No los vuelvas a meter salvo que el equipo lo pida
> explícitamente** — siguen en el historial de git si hacen falta.
> Lo ÚNICO que se conservó de esa época: la app **`MECH Panel.exe`**
> (`windows/`, solo control remoto, no toca el audio). Encima de la
> reversión se hizo: el saludo nuevo (3 rotaciones del brazo derecho hacia
> adelante, solo en reposo; en inglés hasta oct 2026, **ahora en español** —
> ver «Saludo» en Estado actual) y la
> obra `relatividad` (hoy con **7 segmentos**). Después (23 sep): `docs/USO.md`
> **reescrita desde cero** con lo que SÍ hay ahora, los controles de
> movimiento del panel corregidos, el botón de la biblioteca en la app y los
> guiones de CRISPR.

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

**⚠️ Actualización sep 2026 (tras cambiar motores/ruedas) — lo que se ve HOY en el suelo:** el botón AVANZAR (`vx`+) iba **hacia atrás**, y el patrón `vy` (delantero vs trasero) **GIRA** el robot (la media vuelta ya lo usaba así). En vez de reflashear:
- **`DRIVE_INVERT_FORWARD`** (default **true**, en vivo desde Ajustes → «Adelante/atrás invertido»): `arduino_link.move()` manda `-vx` al Arduino. Vale para TODO (botones, «avanza», visión, gestos, `return_to_start`); el odómetro guarda el `vx` lógico. El **comando crudo** del panel NO pasa por ahí.
- **Panel**: los botones **GIRO** mandan `vy` y los **LATERAL** mandan `w` (antes al revés). Es solo el mapeo de botones en `frontend/index.html`: el código de maniobras ya usaba `vy` para girar. Que `w` desplace de lado de verdad está **pendiente de confirmar en el robot**; si salen espejados, se cambia el signo en el botón.

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
  trivia.py           ← Modo TRIVIA: el juego de preguntas que se proyecta
                        al terminar una obra. Solo el ESTADO (etapa,
                        preguntas, marcador, historial, guarda anti-eco);
                        quien habla, proyecta y llama a Claude es mech_app.
  translator.py       ← Modo TRADUCTOR: MECH de intérprete entre dos
                        personas. Solo el ESTADO (activo, par de idiomas,
                        guarda anti-eco); quien habla y pide la traducción
                        es mech_app. Se dispara con «traduce MECH».
  sismos.py           ← Sismos recientes para la vista «Sismos» del panel.
                        Un hilo consulta EMSC y USGS (públicas, sin clave),
                        junta el mismo sismo contado por las dos, y guarda 7
                        días: el mundo desde magnitud 4 y «mi zona» desde
                        2,5. Solo librería estándar. NO predice ni alerta.
  lang.py             ← Idioma activo: español + nueve más (en/fr/pt y,
                        desde oct 2026, de/it/ja/ru/zh/ko). Español por defecto;
                        los demás SOLO si despiertan a MECH en ese idioma
                        ("wake up MECH", "bonjour MECH", "こんにちは MECH"…).
                        Guarda las frases fijas de los diez idiomas y la
                        instrucción de idioma que se le añade a Claude.
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
  styles.css          ← TODA la estética del panel (y la base de
                        library.html). Rehecha dos veces en oct 2026: tema
                        oscuro de mucho contraste, armazón fijo de app y un
                        solo acento cian. Ver «Estética del panel» más abajo
                        antes de tocar colores, tamaños o animaciones.
  projector.html      ← Página fullscreen para Chromium kiosko en la Pi.
                        Maneja eventos image y video, con loop en video, y
                        pinta los SUBTÍTULOS de la narración abajo.
                        Cuando no hay nada que proyectar NO se queda en
                        negro (9 oct 2026): salen las «bolitas» de la vista
                        Inmersivo del panel y su rótulo. Lienzo pequeño
                        (720 px) estirado, a propósito: se ve suave y la Pi
                        casi no trabaja. Se para en cuanto entra algo.
  trivia.js           ← La PANTALLA del juego, estilo Kahoot (se sirve en
                        /static/trivia.js). Pintor tonto: muestra el
                        estado que manda el servidor. Trae su CSS dentro.
  sismos.js           ← El MAPA de la vista «Sismos» (se sirve en
                        /static/sismos.js, cargado ANTES que app.js). Pintor:
                        los datos los baja el servidor. Dos lienzos (mapa
                        abajo, sismos arriba). El contorno de los países
                        sale de vendor/mech-mapa.json, en local.
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

branding/stand/       ← Assets para el STAND físico (PNG TRANSPARENTES, alta
                        resolución, para montar sobre el fondo negro): el lema
                        "We spark interest in what truly matters" en ES/EN
                        (frase-*.png), la franja de píxeles como divisor
                        (divisor.png), tres cifras clave (datos-*.png) y una
                        guía de colocación. Se regeneran con
                        branding/scripts/stand_assets.py (Sora + Space Mono).
                        Ver branding/stand/README.md.

web/                  ← Sitio de PRESENTACIÓN del proyecto (NO es el panel).
                        MULTIPÁGINA (sep 2026): un .html por sección, pensado
                        para desplegar en Vercel con Root Directory = web.
  index.html          ← Inicio: hero + patrocinadores + SALÓN DE TROFEOS +
                        cifras clave.
  empresa.html        ← 01 · M.E.C.H, propuesta de valor, equipo, colaboradores.
  problema.html       ← 02 · Indiferencia, crisis educativa de CR, escuelas
                        unidocentes, neurociencia de la atención + referencias.
  robot.html          ← 03 · Cómo funciona, hardware por capas, construcción,
                        mecanismo, código, retos y bitácora de fotos.
  evolucion.html      ← 04 · MECH-1 → MECH-2 → MECH-3 (campeón nacional) →
                        MECH-4 (4.º en WRO Las Américas) → MECH-5 (actual).
  aplicaciones.html   ← 05 · Áreas de uso + modelo de negocio (costos/ingresos).
  contacto.html       ← 06 · Contacto + patrocinadores (rejilla + marquesina).
  404.html            ← Página de error (Vercel la sirve sola).
  css/styles.css      ← Toda la hoja de estilos (una sola, compartida).
  js/main.js          ← Nav, menú móvil, reveals con stagger, typing.
  assets/             ← Imágenes; assets/logos/ = patrocinadores procesados.
  vercel.json         ← cleanUrls + cache headers.
  README.md           ← Cómo verlo en local y cómo desplegar en Vercel.

pi/                   ← TRES accesos de ESCRITORIO en la Raspberry Pi,
                        para usar MECH sin terminal. `instalar-accesos.sh`
                        se corre UNA vez (doble click desde el explorador) y
                        deja los tres; también BORRA los de versiones
                        anteriores para no dejar botones sueltos.
  iniciar-mech.sh     ← "Iniciar MECH": git pull + arranca el server + ABRE
                        EL PANEL solo (en segundo plano, cuando el server
                        responde). Cierra el server anterior si lo había, y
                        **arranca igual si no hay internet** (avisa y sigue
                        con el código local). Banderas: `--sin-actualizar`
                        (salta el pull) y `--sin-panel`.
  proyector-mech.sh   ← "Proyectar MECH": Chromium kiosko en /projector CON
                        el flag de autoplay (sin él los videos van MUDOS).
                        Si ya hay un Chromium abierto SIN ese flag, lo dice
                        y se ofrece a cerrarlo y abrirlo bien (el porqué,
                        en «Modo MÚSICA — QUITADO»).
  apagar-mech.sh      ← "Apagar MECH": para el servidor con margen para que
                        cierre bien, y solo lo fuerza si no cierra. Cierra
                        también la proyección en kiosko (SOLO esa).
  panel-mech.sh       ← Abre el panel de control. NO tiene icono propio: lo
                        llama `iniciar-mech.sh` con `--silencioso`. ⚠️ Lleva
                        TAMBIÉN el flag de autoplay aunque no reproduzca
                        nada: es el primer Chromium que se abre y de él
                        hereda la proyección. No se lo quites.
  autoarranque.sh     ← Arranque automático al encender la Pi (crea/borra
                        ~/.config/autostart/mech.desktop). SIN icono a
                        propósito (el equipo quiere solo 3): se lanza con
                        doble click desde el explorador. Usa
                        `--sin-actualizar --sin-panel`.
  instalar-accesos.sh ← Genera los .desktop con la ruta real del repo.

windows/              ← Control desde laptop Windows
  Instalar MECH.bat   ← **LA APP (oct 2026), sin construir nada.** Doble
                        clic: deja el icono «MECH» en el Escritorio y el
                        menú Inicio. Llama a instalar_app.ps1.
  Quitar MECH.bat     ← La desinstala (mismo script, con -Quitar).
  instalar_app.ps1    ← Copia app/ a %APPDATA%\MECH\app y crea el acceso
                        directo a Edge/Chrome en modo --app. SIN TILDES a
                        propósito (PowerShell 5 lee los .ps1 como ANSI).
  app/index.html      ← La pantalla que BUSCA AL ROBOT y entra a su panel
                        (http://<robot>:8000/?app=1). Un solo archivo, sin
                        nada externo. El panel se sigue cargando del robot.
  mech_panel.py       ← **La app antigua** (sep 2026): hay que construirla
                        y en la laptop del equipo no hay Python. ENCUENTRA LA PI
                        SOLA (mech.local, mech, la última dirección, y si no
                        barre la red buscando el puerto 8000 + /api/state) y
                        abre el panel con Edge/Chrome en modo --app. Solo
                        librería estándar, a propósito: así el .exe pesa
                        10 MB y se construye en un minuto. Es SOLO control
                        remoto: no toca nada del audio ni del robot. Botones:
                        panel, proyección, kiosko y **biblioteca de videos**
                        (`/library` en el navegador de siempre, pestaña
                        normal, para arrastrar los mp4).
  construir_exe.ps1   ← Construye "MECH Panel.exe" con PyInstaller en un
                        venv aparte (desde el Python de diario se colarían
                        numpy/opencv y el .exe pasaría a cientos de MB).
  MECH-Panel.iss      ← Instalador Inno Setup (menú inicio + desinstalador,
                        sin pedir permisos de administrador). Opcional.
  hacer_icono.py      ← Genera mech.ico desde branding/logo-mech.jpg.
  MECH Control.bat    ← Doble click → Edge --app, ventana sin barras.
  MECH Kiosko.bat     ← Pantalla completa kiosko.
  MECH Proyector.bat  ← Página de proyector en kiosko.
  config.txt          ← URL del servidor (solo lo usan los .bat).
  README.md

docs/
  AUDIO.md            ← Cómo oye MECH: qué hacen los teléfonos con el
                        micrófono, qué de eso hace MECH y qué falta.
  GUIA.md             ← Hardware y montaje en la Pi.
  FRONTEND.md         ← Servidor, panel, control desde Windows.
  USO.md              ← **Guía del OPERADOR del stand**: qué decirle a MECH,
                        qué hace cada botón y qué tocar cuando algo falla.
                        Para quien no programa. Si añadís un comando o un
                        botón, va aquí también (y SOLO lo que existe: se
                        reescribió el 23 sep tras la reversión).
  GUIONES_NEWTON.md   ← Guiones (narración + prompt de video) de Newton.
  GUIONES_RELATIVIDAD.md ← Los 7 guiones de la relatividad, uno por segmento.
  GUIONES_CRISPR.md   ← 5 guiones de CRISPR y Cas9 + datos verificados
                        (los mismos que van en `facts` de la obra `crispr`).

scripts/
  probar_trivia.py    ← Cómo entiende las RESPUESTAS de la trivia (letra,
                        orden, texto) y lo que NO debe adivinar («no sé»,
                        una palabra que vale para dos opciones). 50/50.
                        Correrlo al tocar parse_answer().
  probar_idiomas.py   ← Los DIEZ idiomas sin micrófono: que cada frase
                        despierte en SU idioma, que las órdenes no se pisen
                        entre idiomas (ni con lo que se dice en el stand), el
                        par del traductor, la trivia, los subtítulos en
                        japonés/chino y que las tablas estén completas.
                        Correrlo al tocar las listas VOICE_*_PHRASES_*,
                        lang.py o el matcher. Mide con TODAS las listas
                        juntas (apaga VOICE_STRICT_LANGUAGE a propósito).
  probar_comandos_idioma.py ← La regla de oct 2026: cada comando solo en el
                        idioma del despertar. Las frases de cada idioma en
                        el suyo, una frase de bandera por comando contra las
                        de los otros nueve, el idioma fijo estando despierto,
                        el saludo en español y el bucle de voz REAL con
                        micrófono/Whisper/voz de mentira. Y las funciones
                        extra jugadas ENTERAS en cada idioma (una trivia, un
                        turno del traductor, marketing vacío): cada frase que
                        MECH dice, lo que proyecta y lo que le pide a Claude
                        tienen que ir en el idioma del despertar. Correrlo
                        junto con el anterior.
  probar_sismos.py    ← La pieza que consulta los sismos, con fuentes de
                        mentira: fichas, lugar en español, el mismo sismo en
                        las dos fuentes, qué cuenta como «nuevo», sin
                        internet, cambio de zona. Con `--red` consulta EMSC
                        y USGS de verdad. Correrlo al tocar backend/sismos.py.
  probar_llegada.py   ← Cuándo la cámara da por LLEGADA a una persona:
                        fotogramas falsos sueltos, parpadeos y ruido NO son
                        una llegada; una cara que se mantiene sí. Sin cámara
                        ni OpenCV. Correrlo al tocar vision._Llegada.
  probar_saludo.py    ← Cuenta las órdenes que el SALUDO manda al Arduino:
                        cuántas veces llega arriba el brazo (tienen que ser
                        3), que el izquierdo no se mueva y que nunca baje de
                        90. Sin hardware. Correrlo al tocar ARM_WAVE_*.

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

# ...o desde el escritorio de la Pi, sin terminal: icono «Iniciar MECH»
# (se instala UNA vez con `bash ~/MECH/pi/instalar-accesos.sh`). Ver pi/README.md.

# Visor de proyección en la misma Pi (Chromium kiosko)
chromium --kiosk --autoplay-policy=no-user-gesture-required          http://localhost:8000/projector
# El flag de autoplay es OBLIGATORIO para que suene el audio de los videos del
# slot de marketing; sin él el navegador los deja MUDOS.
# ⚠️ Solo cuenta si es el PRIMER Chromium que se abre: con otro ya abierto,
# la ventana nueva se mete en ese y el flag se ignora.
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

### Chequeo previo al evento

```bash
python -m backend.preflight            # todo
python -m backend.preflight --sin-red  # simulando que NO hay internet
```

Revisa en un solo paso: dependencias, que **Whisper cargue del disco sin
red**, claves de API, qué servicios se caen sin wifi (y qué sigue en pie),
micrófono (lo abre de verdad al sample rate configurado), reproductores de
audio, Arduino, biblioteca de videos, que el panel no cargue **nada** de
internet, y las claves del `.env` que tapan los defaults. Sale 1 si hay
fallos. **Correrlo con el server apagado** (usa el micrófono y el Arduino).

### El frontend NO carga nada de internet — mantenelo así

Los iconos venían de un CDN y las fuentes de Google Fonts. Sin wifi, los
botones del panel que son **solo icono** salían **en blanco** (subir video,
borrar…). Ahora todo está en `frontend/vendor/`, servido en `/vendor` y
referenciado con ruta **relativa** (así funciona igual servido que abriendo
el HTML con doble click).

- `mech-icons.css` = solo los 42 iconos que usa el panel (2 KB en vez de los
  200 KB del paquete completo), regenerable con `python scripts/mkicons.py`.
  **Si añadís un icono nuevo, hay que regenerarlo** o ese botón sale vacío —
  el preflight lo detecta.
- `mech-fonts.css` + `vendor/fonts/` = Sora y Space Mono (subsets latin),
  regenerable con `python scripts/mkfonts.py`.
- `mech-fonts-cjk.css` + `vendor/fonts/cjk/` = las letras de **coreano,
  japonés y chino** (Noto Sans KR/JP/SC, 322 trozos, 7 MB), regenerable con
  `python scripts/mkfonts_cjk.py`. Las cargan el panel, `/projector` y
  `/projector/vr`. Ver «La letra de coreano, japonés y chino va incluida».
- `mech-mapa.json` = el contorno de los países para la vista «Sismos»
  (Natural Earth 1:50m, 500 KB), regenerable con `python scripts/mkmapa.py`.
  Nada de mapas de internet (los de cuadritos que se bajan al moverse): sin
  wifi la vista quedaría en negro. El preflight (§8) avisa si falta.
- `ti-brand-arduino` **no existe en Tabler**: esos tres iconos ya estaban
  rotos incluso con internet. Se cambiaron por `ti-cpu-2`.

### Tests y lint

Este repo **no tiene suite de tests ni linter configurado**. La validación es manual extremo-a-extremo: voz → STT → Plan de Claude → imagen → proyección → comandos Arduino. No inventes `pytest`/`ruff`/`black` — si crees que hace falta uno, propónselo al usuario antes de añadirlo.

---

## Convenciones de código

### Idiomas

- **Strings al usuario (UI, voz, logs)** → siempre español neutro. Las frases
  que MECH DICE (saludo, despedida, error) tienen su versión en los DIEZ
  idiomas en `backend/lang.py`: si añades una, añade las diez
  (es/en/fr/pt/de/it/ja/ru/zh/ko). ⚠️ También lo que se PROYECTA: el título
  de la trivia sobre MECH iba fijo en español («MECH y su equipo») y salía
  así aunque se jugara en japonés; ahora es `trivia_about_us`. Lo mismo con
  `_SAY` de `backend/maneuvers.py`
  y con `T` de `frontend/trivia.js`. `scripts/probar_idiomas.py` avisa si
  falta alguna.
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

### Idiomas (español + inglés, francés, portugués, alemán, italiano, japonés, ruso, mandarín, coreano)

MECH **siempre arranca en español**. Los otros nueve **se activan si y solo si**
se le despierta EN ese idioma. **Lo decide el despertar, no la conversación**:

| Frase de despertar | Idioma |
|---|---|
| «ok MECH» · «despierta MECH» | español (`es`) |
| «wake up MECH» | inglés (`en`) |
| «bonjour MECH» · «salut MECH» · «réveille MECH» | francés (`fr`) |
| «bom dia MECH» · «boa tarde MECH» · «acorda MECH» | portugués (`pt`) |
| «guten Tag MECH» · «guten Morgen MECH» · «wach auf MECH» | alemán (`de`) |
| «ciao MECH» · «buongiorno MECH» · «svegliati MECH» | italiano (`it`) |
| «こんにちは MECH» · «起きて MECH» | japonés (`ja`) |
| «привет MECH» · «проснись MECH» | ruso (`ru`) |
| «你好 MECH» · «醒醒 MECH» | mandarín (`zh`) |
| «안녕 MECH» · «일어나 MECH» | coreano (`ko`) |

Los seis últimos son de **oct 2026** (pedido del equipo; el coreano, el
décimo, el día 6). Entran porque están dentro de lo que habla la voz
(`eleven_multilingual_v2`) y de lo que entiende Whisper. **Sin probar en la
Pi**: ver la subsección «Idiomas que no usan letras latinas».

En el idioma activo van: lo que Whisper transcribe (`language=<código>`), lo
que Claude narra (bloque de idioma en el system prompt), las frases fijas
(saludo, despedida, error, giro) y los subtítulos. El TTS de ElevenLabs ya era
multilingüe. **Al dormirse vuelve solo a español.**

- Idioma activo y textos fijos: [`backend/lang.py`](backend/lang.py). Para
  añadir un idioma nuevo, la cabecera del módulo lista los pasos (4, y 2 más
  si no se escribe con letras latinas).
- Frases de despertar/reposo: `VOICE_WAKE_PHRASES_<XX>` /
  `VOICE_SLEEP_PHRASES_<XX>` (`.env`; `XX` = EN, FR, PT, DE, IT, JA, RU, ZH, KO),
  detección en `voice_phrases.wake_language()` (los idiomas extra se
  comprueban ANTES que el español, que tiene frases muy cortas).
- En `config.py`, las listas de EN/FR/PT van repartidas tema por tema; las de
  DE/IT/JA/RU/ZH van **todas juntas, agrupadas por idioma**, en la sección
  «Idiomas añadidos en oct 2026» (son 14 listas por idioma: así se revisa un
  idioma entero de un vistazo).
- **Cada comando, solo en el idioma del despertar (6 oct 2026, pedido del
  equipo).** Las frases de mando existen en los diez idiomas
  (`VOICE_*_PHRASES_<XX>`), pero `voice_phrases._frases_activas()` solo mira
  la lista del idioma ACTIVO: despierto con «wake up MECH» lo corta «hey
  MECH» y **no** «oye MECH»; despierto con «ok MECH», al revés. Vale para
  todo lo que se reconoce por frase (interrumpir, dormir, moverse, marketing,
  traductor, trivia, sí/no). Las de DESPERTAR son la excepción: en reposo se
  miran las diez, porque son las que eligen el idioma. (Hasta el 5 oct se
  aceptaban todas siempre, sin mirar el idioma activo.)
  - **El idioma queda fijo hasta que se duerme.** Antes, decir la frase de
    despertar de otro idioma estando despierto lo cambiaba; ya no
    (`voice_phrases.wake_language_awake()`). Tenía un fallo real: «OK MECH,
    tell me about…» dicho en inglés casaba con el «ok MECH» español y lo
    pasaba a español a media charla. Ahora esa frase sigue hacia Claude como
    cualquier otra.
  - Se apaga con **`VOICE_STRICT_LANGUAGE=false`** (en vivo: Ajustes →
    «Idioma de los comandos»), y vuelve todo lo de antes: todas las listas a
    la vez y el cambio de idioma estando despierto.
  - ⚠️ La separación es **por lista**, no perfecta: el matcher sigue
    perdonando una letra, así que palabras casi iguales entre idiomas valen
    en los dos («avanza»/«avance»/«avança», «traduce»/«traduz»,
    «perdón»/«pardon»). No es un fallo, es el mismo sonido.
  - Al quedar cada idioma con SU lista, cada una tiene que valerse sola: por
    eso «ok» está ahora en las diez listas de `VOICE_YES_PHRASES*`. Si
    añades un idioma o una frase, revisa que no dependa de otra lista.
  - No se tocó lo que no es un comando: las respuestas de la trivia
    (`parse_answer`: letras y ordinales), los números de «avanza diez
    segundos» y los nombres de idioma del traductor siguen mezclando todos
    los idiomas.
  - Dos simulaciones, sin hardware:
    **`python scripts/probar_comandos_idioma.py`** mide ESTA regla (cada
    idioma con sus comandos y sin los ajenos, + el bucle de voz real con
    micrófono/Whisper/voz de mentira); `scripts/probar_idiomas.py` sigue
    midiendo las colisiones con TODAS las listas juntas (apaga la regla a
    propósito: es el peor caso, y el que vale si alguien la apaga).
- En reposo, si la transcripción en español no coincide con ningún wake, el
  bucle **re-transcribe el MISMO audio UNA vez con detección automática de
  idioma** (`stt.transcribe_any`) y vuelve a comparar contra todas las listas.
  ⚠️ **NO lo cambies a reintentar idioma por idioma**: con diez idiomas
  serían 9 pasadas de Whisper por cada ruido, y la Pi tardaría medio minuto
  en volver a escuchar. Por eso añadir idiomas NO cuesta tiempo de escucha.
- Se puede forzar desde el panel (botón **IDIOMA** de la vista Voz: un menú
  con los diez → `POST /api/language/<código>`), útil para probar sin
  micrófono. Hasta el 6 oct eran diez chips en fila.
- Apagar un idioma: `WAKE_ENGLISH_ENABLED`, `WAKE_FRENCH_ENABLED`,
  `WAKE_PORTUGUESE_ENABLED`, `WAKE_GERMAN_ENABLED`, `WAKE_ITALIAN_ENABLED`,
  `WAKE_JAPANESE_ENABLED`, `WAKE_RUSSIAN_ENABLED`, `WAKE_CHINESE_ENABLED`,
  `WAKE_KOREAN_ENABLED` = `false`. Conviene apagar los que no se vayan a usar en el evento.

⚠️ **Al inventar frases nuevas, ojo con las colisiones entre idiomas.** El
matcher de `voice_phrases` perdona errores de letra, así que palabras
parecidas se pisan. Casos reales que ya se evitaron: el portugués «desperta»
caía en el español «despierta»; «olá MECH» caía en «hola MECH»; el francés
«dors» cae en «dos», así que «avanza dos segundos, MECH» habría dormido al
robot.

### Idiomas que no usan letras latinas (japonés, ruso, mandarín, coreano) — oct 2026

Añadir alemán e italiano fue copiar listas. Estos tres obligaron a tocar el
matcher, los subtítulos y la trivia. **Para texto en letras latinas el
matcher no cambió** (medido contra el de antes: `normalize` y `_word_matches`
dan lo mismo en 181 476 pares de palabras, y 334 guiones dan los mismos
subtítulos). Lo único distinto en 1463 frases de prueba, con las listas
nuevas vacías: «sei» ya cuenta como número (seis, en italiano).

- **Japonés y chino van SIN ESPACIOS.** No hay palabras que comparar, así que
  cada trozo de una frase de `config` se busca DENTRO de lo que se oyó
  (`voice_phrases._contiene`). En las listas, un espacio separa trozos que
  tienen que aparecer los dos: «マーケティング 再生» casa con
  «マーケティングを再生して». `normalize()` pasa el katakana a hiragana, las
  letras de ancho completo a normales y mete un espacio donde cambia la
  escritura («こんにちはMECH» → «こんにちは mech»).
- **El nombre «MECH» no sale siempre en letras latinas.** Whisper lo escribe
  como le suena: «メック», «мек», «麦克». Cualquier frase que lleve la palabra
  `mech` acepta también las formas de `config.VOICE_NAME_ALIASES` (en vivo
  desde el `.env`). Ninguna usa letras latinas, así que no le abre la puerta
  a nada en los idiomas de siempre. ⚠️ Esto es lo que MÁS puede fallar con el
  micrófono real. Diagnóstico ya montado: si en reposo le hablan en otro
  idioma y no es una frase de despertar, el panel dice **«Oí en japonés:
  '…'»** (como mucho cada 10 s) — ahí se ve cómo escribió el nombre.
- **El chino llega en simplificado o en tradicional**, sin avisar. Donde
  cambian van las dos formas en las listas (醒来 / 醒來). El `initial_prompt`
  de Whisper y la directiva para Claude van en simplificado a propósito.
- **Un comando de UN solo carácter** («好» sí, «不» no) solo cuenta si la
  respuesta es corta y EMPIEZA por él: si no, «你好» (hola) sería un sí.
- **Subtítulos**: `subtitles.py` mide el ANCHO (un carácter chino o japonés
  vale 2), parte por caracteres en vez de por palabras, prefiere cortar en
  una coma (、，) y no deja que una línea empiece por «。» o «っ».
- **Trivia**: `parse_answer()` entiende «Bです», «二番目», «我选B», «第二个»,
  la «А» cirílica y el texto de la opción dicho sin los signos
  («桑丘潘沙» por «桑丘·潘沙»). «不知道» / «わかりません» / «не знаю» son
  "no sé", no una opción.
- **La letra para LEERLOS va incluida en el repo** (desde el 6 oct 2026; antes
  había que hacer `sudo apt install fonts-noto-cjk` en la Pi). Ver la
  subsección siguiente. El preflight (§11) comprueba que no falte ningún trozo.

#### La letra de coreano, japonés y chino va incluida (6 oct 2026)

El equipo reportó que en el chat del panel el coreano salía con «un símbolo
raro, como si no tuviera el idioma». **No era el código ni los datos** (el
texto viaja bien por el WebSocket): el panel se veía **en la Raspberry Pi**,
y la Pi no trae letra coreana. Sora y Space Mono solo traen el alfabeto
latino; para lo demás el navegador usa lo que tenga instalado el aparato.

- Ahora las letras viajan con el repo: `frontend/vendor/fonts/cjk/` (Noto
  Sans KR / JP / SC, peso 400, 322 archivos `.woff2`, 7 MB) +
  `frontend/vendor/mech-fonts-cjk.css`. Se generan con
  `python scripts/mkfonts_cjk.py` (necesita internet).
- Van en **trozos** (`unicode-range`): el navegador solo baja los que hacen
  falta. Un subtítulo en español no carga ninguno. El panel sí carga una
  docena al abrir, porque el menú de idioma escribe «한국어», «日本語»…
- ⚠️ **El script RECORTA las fuentes a solo coreano, japonés y chino** (lista
  `SOLO`). Tal como las da Google también traen letras latinas, números,
  flechas, figuras y algún emoji; sin el recorte le cambiaban el aspecto a
  las flechas de los botones del Arduino y, en la Pi, a la letra de los
  subtítulos en español. **No quites ese recorte.** Medido: el ancho de un
  texto en español es idéntico con y sin las fuentes nuevas.
- **Orden de las familias = variable `--cjk`**, definida al final de
  `mech-fonts-cjk.css`: por defecto KR · JP · SC; con `lang="ja"` va primero
  la japonesa y con `lang="zh"` la china (comparten miles de caracteres que
  cada país dibuja algo distinto). Se usa así:
  `font-family: 'Sora', var(--cjk, sans-serif), sans-serif`.
  ⚠️ En `styles.css`, `--font-main` y `--font-mono` se vuelven a componer en
  `:lang(ja), :lang(zh)`: una variable ya resuelta en `:root` no se entera de
  que `--cjk` cambió más abajo.
- Quién pone el `lang`: en el panel, `escritura()` de `app.js` mira qué
  escritura trae cada texto (chat, transcripción, respuesta, log, trivia); en
  la proyección ya lo ponía `subtitles.js`, y `trivia.js` se lo pone ahora a
  su capa.
- Solo hay peso 400: las negritas (subtítulos, trivia) las engorda el
  navegador. Bajar también el 700 serían otros 7 MB.
- `library.html` no carga estas fuentes (no muestra texto en esos idiomas);
  por eso todos los usos llevan el respaldo `var(--cjk, sans-serif)`.
- **Si se añade un idioma con otra escritura** (árabe, hindi, tailandés…)
  hace falta su fuente: otra familia en `FAMILIAS` y otro bloque en `SOLO`.

**Coreano (6 oct 2026) — el décimo idioma.** Se escribe con otra letra
(hangul) como los tres de arriba, pero tiene sus propias reglas. Sin probar
con micrófono.

- **Lleva espacios, pero pega las terminaciones a la palabra** («번역해줘»,
  «번역해 주세요») y Whisper junta o separa a su antojo. Por eso se compara
  como el japonés y el chino: `_es_cjk()` incluye el hangul y cada trozo se
  busca DENTRO de lo oído.
- ⚠️ **Una sílaba suelta dentro de una orden de varias tiene que ser la
  palabra ENTERA** (`_contiene`, rama `_es_hangul`). «앞으로 가» ("ve hacia
  adelante") lleva «가», que es además la partícula más común del idioma:
  buscándola dentro, «앞으로 … 가져올 변화» ("los cambios que traerá en el
  futuro") hacía AVANZAR al robot. Por eso las listas llevan también las
  formas con la terminación pegada («앞으로 가줘», «잘자 mech»).
- ⚠️ **El nombre de UNA sílaba** («멕», «맥», que es lo que más probablemente
  escriba Whisper) solo vale suelto o con la partícula con que se llama a
  alguien («멕아», «맥씨»): dentro de otra palabra no (`_nombre_en`,
  `_TRAS_NOMBRE_KO`). Si no, «멕시코» (México) y «맥주» (cerveza) serían MECH.
- **Nada de «안녕히 주무세요 MECH»** ("buenas noches") para dormirlo: lleva
  dentro «안녕», que es la frase de despertar. Se duerme con «잘 자 MECH».
  Y el saludo dice «환영합니다», no «안녕하세요», por lo mismo.
- **Segundos**: «10초», «십 초», «이십오 초» (`_SEGUNDOS_KO`). El número no
  puede ir pegado a otra palabra: en «로봇이 초록색» el «이» es una partícula,
  no un dos.
- **Trivia**: «B요», «비» / «에이» (la letra dicha en hangul, solo si es la
  respuesta entera), «2번», «두 번째» / «두번째» (se busca sin espacios;
  ⚠️ nada de «이번» por "número dos": es también "esta vez"), «모르겠어요».
- **Subtítulos**: las letras son anchas como las chinas (valen 2), pero las
  líneas se cortan ENTRE palabras, nunca por la mitad (`subtitles._se_corta`).
- Todos los nombres de idioma en coreano acaban en «어»: es lo que permite
  decir «{src}와 {dst}» en `translate_ready` sin mirar la última letra. Si
  añades un idioma cuyo nombre coreano acabe en consonante, hay que tocarlo.

Colisiones que YA se evitaron (están medidas en `scripts/probar_idiomas.py`;
si añades frases, córrelo):

| Tentación | Por qué no |
|---|---|
| «hallo MECH» (alemán) | `hallo` queda a una letra de `hello`: «hello MECH» despertaba en alemán. Se usa «guten Tag MECH». |
| «voltati» (italiano, "date la vuelta") | cae en el español `voltea`: «voltea hacia la proyección» hacía girar hacia AFUERA. |
| «buona notte MECH» en dos palabras | «buena nota, MECH» lo dormía. Va «buonanotte» junto. |
| «включи / выключи переводчик» (ruso) | "enciende" y "apaga" están a una letra. No está ninguna de las dos. |
| «secondo» como ordinal (italiano) | «secondo me» = "en mi opinión": «secondo me la C» se leía como la segunda. |
| Frases de `_SAY` que contienen su propia orden | Tras decirlas se abre el micrófono y MECH se obedecería a sí mismo («…schau nach außen»). Las de los idiomas nuevos se escribieron evitándolo. |

Lo que cambia al estar encendidos (y conviene saber): «cierto» cuenta como un
sí (por el italiano «certo»), «un momento, MECH» y «acepta, MECH» interrumpen
la narración (por el alemán «moment MECH» y el italiano «aspetta MECH») y
«já sei» en portugués cuenta como un sí (por el alemán «ja»). Son
inofensivos; en esas 1463 frases no hay NINGÚN cambio en despertar, dormir
ni moverse.

### Cómo compara el matcher (sep 2026) — por qué «trasluce» ya funciona

El equipo reportó que Whisper escribía «**trasluce** mech» en vez de
«traduce mech» y el comando no se ejecutaba. El matcher era a la vez
**demasiado estricto** (1 sola letra de error) y **demasiado laxo**
(substring libre: «oye» coincidía DENTRO de «pr-**oye**-cto», así que «el
proyecto se llama mech» disparaba la interrupción). `_word_matches` prueba
ahora, de más barato a más caro:

1. **Igual.**
2. **Suena igual** (`_fonetica`): reducción rápida del español —
   `ll`=`y`, `qu`=`k`, `sh`=`ch`, `h` muda, seseo (`c`/`z`/`s`), `b`=`v`,
   `g`+`e/i`=`j`, letras dobles a simple. Arregla solo «olle»/«oye»,
   «marqueting»/«marketing», «asia»/«hacia», «mesh»/«mech», «traduse».
3. **Casi la misma palabra**: el token empieza igual y trae como mucho UNA
   letra de más («mech»→«mecha», «va»→«vai»). Antes era substring libre, y
   de ahí salían los falsos positivos.
4. **Distancia de edición**: 1 error en palabras de 4-6 letras, **2 en las
   de 7+ siempre que empiecen igual**. Lo de los 2 errores es lo que pilla
   «trasluce»; el «empiecen igual» es lo que evita que «produce» active el
   traductor.

Medido contra un corpus de 37 transcripciones deformadas reales y 40 frases
normales del stand: **37/37 comandos y 0 falsos positivos** (antes: 34/37 y
1 falso positivo). ⚠️ Si tocás estos umbrales, **volvé a medir las dos
listas**: aflojar para pillar un caso rompe el otro lado enseguida.

### Modo TRADUCTOR — MECH de intérprete («traduce MECH»)

Pedido del equipo (sep 2026): que MECH sirva para que dos personas que no
hablan el mismo idioma se entiendan en el stand.

**Va por TURNOS: un «traduce MECH» = UNA frase traducida.**

```
«ok MECH»               → despierta
«traduce MECH»          → arranca un turno (NO pasa por Claude)
MECH: «¿De qué idioma a qué idioma traduzco?»          (+ chime)
«de español a francés»
MECH: «Listo, traduzco entre español y francés. ¿Qué quieres que traduzca?»
«Buenos días, ¿cómo está?»
MECH: «Bonjour, comment allez-vous ?»   → y SE CALLA

«traduce MECH»          → otro turno; ya sabe el par, va al grano
MECH: «¿Qué quieres que traduzca?»                     (+ chime)
«Très bien, merci»      (el otro, en francés)
MECH: «Muy bien, gracias.»              → y se calla otra vez

«deja de traducir»      → olvida el par (dormirlo o el paro, también)
```

- ⚠️ **Un turno por comando es LA solución al eco, no una limitación.** La
  primera versión escuchaba en bucle y MECH acababa traduciendo su propia
  traducción, y la de esa, sin fin. Con turnos el micrófono nunca está
  abierto justo después de que él hable. **No lo vuelvas a hacer continuo**
  sin resolver el eco de otra manera.
- **El par de idiomas se RECUERDA** entre turnos (`translator.finish()` lo
  conserva; `translator.reset()` lo borra). Repetirlo en cada frase sería
  insufrible. Se cambia nombrándolo en el propio comando («traduce MECH del
  inglés al portugués», «traduce MECH al francés» → origen = idioma activo);
  se olvida con «deja de traducir», al dormirse y con el paro.
- **Va en los DOS SENTIDOS** (`TRANSLATOR_AUTO_DETECT`, default sí): Whisper
  detecta en cuál de los dos idiomas del par se dijo la frase
  (`stt.transcribe_any`) y MECH la pasa al otro. Si detecta un idioma que no
  es del par, re-transcribe forzando el de ORIGEN. Ponerlo en `false` fija el
  sentido — útil con el par español/portugués, que Whisper confunde en
  frases cortas.
- **No pasa por el prompt grande.** `llm.translate()` es una llamada corta
  (`messages.create`, system de ~700 caracteres, sin caché ni structured
  output): en una conversación lo que importa es la latencia. Modelo en
  `CLAUDE_TRANSLATE_MODEL` (vacío = `CLAUDE_MODEL`).
- **Dentro de un turno NO se obedecen órdenes**, solo salir, dormirse y
  repetir el comando. Es lo correcto: un intérprete no ejecuta lo que está
  traduciendo (si no, «mira hacia afuera» giraría el robot).
- **«Deja de traducir» funciona también con el turno YA terminado** (arreglo
  del 5 oct 2026). Antes solo se miraba en medio de un turno
  (`server._voice_loop_worker`); dicha después, se iba a Claude como una
  pregunta cualquiera y el par no se olvidaba nunca. Ahora
  `mech_app.handle_text_command()` la mira **antes** que «traduce MECH».
  ⚠️ **No cambies ese orden**: «deja de traducir, MECH» lleva dentro las
  palabras de «traduce MECH» y arrancaba OTRO turno en vez de salir (mismo
  criterio que la trivia: salir se mira antes que entrar).
- **Si no hay nada que olvidar, MECH se calla** (lo apunta en el panel y no
  llama a Claude). Es a propósito: la confirmación «Listo, dejo de traducir»
  casa con la orden en los diez idiomas, así que cuando MECH se oye a sí
  mismo el eco cae ahí y muere en silencio. Si contestara, se oiría y
  volvería a contestarse. `scripts/probar_idiomas.py` comprueba que la
  confirmación siga casando con la orden — no la reescribas sin correrlo.
- La traducción se **dice y se pinta como subtítulo** en la proyección
  (`set_subtitle(texto, idioma_destino)`), y el subtítulo **se queda** al
  terminar el turno para que dé tiempo a leerlo.
- ⚠️ **Sigue habiendo un hueco de eco**: entre la PREGUNTA de MECH y la frase
  del visitante el micrófono sí está abierto. Lo tapan
  `TRANSLATOR_DRAIN_SECONDS` (0.8 s tras hablar, por el buffer del parlante
  Bluetooth) y `translator.looks_like_own_echo()`, que descarta lo que oye si
  es casi lo último que dijo. Si el eco entra igual, MECH **no pierde el
  turno**: vuelve a pedir la frase.
- Si la traducción falla (API caída, respuesta vacía), tampoco pierde el
  turno: lo dice y vuelve a pedir la frase.
- Panel: tarjeta TRADUCTOR en la vista Voz con los dos selectores,
  «Traducir una» (un turno con ese par) y «Olvidar». El badge muestra la
  etapa: `APAGADO` · `ESPERANDO IDIOMAS` · `ESCUCHANDO · ES ↔ FR` ·
  `LISTO · ES ↔ FR` (callado, con el par recordado). Endpoints
  `POST /api/translate/start?src=&dst=` y `/api/translate/stop`.
- Claves: `TRANSLATOR_ENABLED`, `TRANSLATOR_AUTO_DETECT`,
  `TRANSLATOR_DRAIN_SECONDS`, `CLAUDE_TRANSLATE_MODEL`,
  `VOICE_TRANSLATE_PHRASES{,_EN,_FR,_PT}`,
  `VOICE_TRANSLATE_STOP_PHRASES{,_EN,_FR,_PT}`.

### Modo TRIVIA — el juego de preguntas (sep 2026, recuperado el 25 sep)

⚠️ Se quitó con la reversión a `c0e0310` y el equipo lo pidió de vuelta el
25 sep: es el MISMO juego (ya medido), portado al código actual, con la
pantalla rehecha **estilo Kahoot** y las frases que pidió el equipo.

Pedido del equipo: al terminar de contar una obra, MECH ofrece una trivia
sobre lo que acaba de narrar, la **proyecta** y el visitante contesta
hablando.

**El juego corre ENTERO en el servidor** ([`backend/trivia.py`](backend/trivia.py)
= estado, `mech_app` = voz y proyección). La pantalla
([`frontend/trivia.js`](frontend/trivia.js)) solo pinta lo que le mandan, por
evento WS `trivia` **y** por `state["trivia"]`: una pantalla que se recargue a
media partida vuelve sola a la pregunta correcta.

Etapas: `offer` (¿jugamos?) → `loading` (Claude escribe las preguntas) →
`question` → `result` (celebra o revela) → `final` (marcador).

- **La pantalla es estilo KAHOOT** (pedido del equipo): fondo morado, la
  pregunta en una banda blanca y una ficha de color por opción con su
  figura (triángulo rojo, rombo azul, círculo amarillo, cuadrado verde) y
  la LETRA bien grande (se contesta hablando). Al acertar: ficha que salta,
  ✓, banda verde «¡Correcto!» y confeti. Al fallar: ✕ en la elegida,
  ✓ en la buena y banda roja «No has acertado — la respuesta correcta es la
  B: …», que MECH también dice en voz alta. Todo en el idioma activo
  (`snap["lang"]`; los textos fijos de la pantalla viven en `T` de
  `trivia.js`). Las bolitas de progreso salen de `history`.
- ⚠️ **Al revelar NO se repite la animación de entrada** (`.mt-wrap.reveal`):
  su último fotograma (opacidad 1) se queda pegado y las fichas que no
  eran dejarían de atenuarse. Y la banda del veredicto va EN el flujo, no
  encima: si no, tapa el texto de las fichas.
- **La pregunta del ofrecimiento** es la que pidió el equipo, en todos los
  idiomas: «¿Te gustaría realizar una trivia para comprobar tu
  conocimiento?» (`lang.py` → `trivia_offer`).
- **TODO va en el idioma del despertar** (revisado el 6 oct 2026, pedido del
  equipo): lo que MECH dice, los textos fijos de la pantalla (`T` de
  `trivia.js`), las preguntas (`llm.make_quiz` recibe el idioma y la MISMA
  indicación de estilo que la narración, `lang.writing_style()`: japonés
  cortés, chino simplificado…) y el **título** que se proyecta («Sobre: …»).
  Dos fugas que se cerraron: el título de la partida sobre MECH iba fijo en
  español (ahora `lang.say("trivia_about_us")`), y a Claude no se le decía
  en qué idioma escribir el `title` del plan, que la trivia proyecta (ahora
  va en la directiva de idioma). `scripts/probar_comandos_idioma.py` juega
  una partida entera en cada idioma y compara frase por frase.
  ⚠️ Lo que escribe Claude de verdad (título y preguntas) solo se ve con la
  API real: en la simulación Claude es de mentira.
- **Solo se ofrece si la presentación llegó al FINAL**, sin interrupción y
  tras un plan `immersive` (`should_offer_trivia(plan, completa)`).
- Mientras hay partida, MECH **no saluda** (`_greeting_blocked`).
- Sin trivia en la vista VR del teléfono (`/projector/vr`), a propósito.

- **Opción múltiple A/B/C, no respuesta libre** — y es una decisión, no una
  simplificación: esto se juega hablándole a un robot en un stand ruidoso.
  Con tres opciones leídas en voz alta el visitante solo dice una letra;
  interpretar una respuesta libre costaría otra llamada a la API y fallaría
  a cada rato.
- `voice_phrases.parse_answer()` acepta las tres formas naturales: **la
  letra** («la A»), **el orden** («la segunda») y **el texto** («1605»,
  «Sancho Panza», incluso a medias: «Dulcinea» por «Dulcinea del Toboso»).
  ⚠️ **El orden de comprobación importa** y está medido en
  `scripts/probar_trivia.py`:
  1. Primero el TEXTO, porque dentro de una opción dicha entera puede haber
     un «se» o un «de» que se confundiría con una letra.
  2. Luego el ORDINAL, porque en español y portugués el artículo que
     acompaña al ordinal ES una letra de opción («a terceira» era la A).
  3. Y por último la LETRA, que solo cuenta si la frase es corta o si
     delante va un marcador («la», «opción», «letra»).
- ⚠️ **«No sé» NO es la opción C.** En español lleva dentro un «se» que suena
  igual que esa letra; sin `is_dont_know()`, rendirse contaría como
  responder. A la SEGUNDA respuesta que no se entiende, MECH revela la buena
  y pasa a la siguiente: insistir con «decí A, B o C» a alguien que no te
  entiende es la peor experiencia posible en un stand.
- **Las preguntas las escribe Claude en el momento** (`llm.make_quiz`, salida
  estructurada, prompt corto y aparte del grande) con DOS fuentes: el guion
  que acaba de narrar y los **datos verificados** (`facts`) de esa obra. Si
  todavía no ha narrado nada, la partida va sobre `informacion_nuestra`.
  Solo se usa lo que el visitante **llegó a oír**: si lo interrumpieron a la
  mitad, los segmentos que no sonaron no entran.
- **Se ofrece solo tras un plan `immersive`** y sin interrupción. Tras una
  respuesta suelta o una orden de movimiento, ofrecer un juego queda fuera
  de lugar.
- Si en el ofrecimiento contestan otra cosa, `handle_trivia_offer()` devuelve
  **False** y el bucle de voz procesa el texto como un comando normal: nadie
  se queda encerrado en el juego.
- Guarda anti-eco propia (`trivia.remember_spoken` + `sounds_like_same`), por
  lo mismo que el traductor: el micrófono se abre justo detrás de la voz de
  MECH.
- Panel: tarjeta TRIVIA en la vista Voz con «Empezar trivia», «Salir» y un
  botón por opción para responder **sin micrófono** — es lo que separa «el
  juego falla» de «no te entendió al hablar»
  (`POST /api/trivia/answer/{a|b|c}`). El icono de la tarjeta es `ti-bulb`
  porque `ti-help-circle` NO está en el subconjunto local de iconos.
- Claves: `TRIVIA_ENABLED`, `TRIVIA_QUESTIONS` (3), `TRIVIA_OFFER_AFTER_PLAN`,
  `TRIVIA_DRAIN_SECONDS`, `TRIVIA_FINAL_SECONDS`, `CLAUDE_TRIVIA_MODEL`,
  `VOICE_TRIVIA_PHRASES{,_EN,_FR,_PT}`, `VOICE_TRIVIA_STOP_PHRASES{...}`,
  `VOICE_YES_PHRASES{...}`, `VOICE_NO_PHRASES{...}`. Las tres primeras son
  **live** desde Ajustes.

### Interrumpir a MECH mientras narra ("oye MECH" / "hey MECH")

Durante TODO el plan (narración y también las pausas en que genera imágenes),
`backend/interrupt_listener.py` corre un hilo que escucha con una regla muy
estricta: **solo** las frases de `VOICE_INTERRUPT_PHRASES` **del idioma en
que MECH despertó** («oye MECH» en español, «hey MECH» en inglés, «pardon
MECH» en francés, «escuta MECH» en portugués; desde oct 2026 las de otro
idioma no lo cortan). Cualquier otra cosa que oiga se descarta sin
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

### Slot de MARKETING — proyección directa con audio (sep 2026)

`marketing` en `WORKS` **no es una obra cultural**: lleva `promo: True` y se
comporta al revés que las demás en cuatro cosas.

| | Obra cultural | Slot `marketing` |
|---|---|---|
| Cómo se pide | lo decide Claude | «**proyecta marketing**» — orden directa, **sin pasar por Claude** |
| Reproducción | clip corto **en bucle** bajo la narración | video **entero**, uno tras otro |
| Audio | **mudo** (MECH narra encima) | **su propio audio** — MECH se calla |
| Si faltan archivos | la obra no se ofrece a Claude | **proyecta con los que haya**; los huecos se saltan |

- 12 espacios, ninguno obligatorio: con UNO ya proyecta (`work_is_complete()`
  usa `any()` en lugar de `all()` para los promo). Los videos son largos
  (~90 s) y se ven completos.
- `video_library.playlist(slug)` devuelve los presentes en orden.
- **Se excluye del system prompt** (`system_prompt_section` filtra los promo):
  si Claude lo viera, lo contaría como una obra y hablaría encima.
- `mech_app.play_playlist()` emite el evento WS `playlist` con la lista y
  `audio: True`, pone la fase en `speaking` (el bucle de voz no abre el
  micrófono) y **espera**. Se corta con «oye MECH», con
  `POST /api/marketing/stop` o con el paro de emergencia.
- **Quién marca el final: la PANTALLA, no el backend.** Python no sabe cuánto
  dura cada mp4, así que `frontend/projector.html` avanza con el evento
  `ended` de cada `<video>` y avisa con `POST /api/playlist/ended` al acabar
  el último. `MARKETING_MAX_SECONDS` (1500) es solo el tope por si NO hay
  ninguna pantalla abierta.
- ⚠️ **El audio necesita la política de autoplay relajada en la Pi**:
  `chromium --kiosk --autoplay-policy=no-user-gesture-required
  http://localhost:8000/projector`. Sin eso el video se ve pero MUDO, y la
  página muestra «Toca la pantalla para activar el sonido» (un toque lo
  activa y reinicia el video en curso). En `/projector/vr` van siempre mudos
  a propósito: el sonido sale por el parlante de la Pi, no por el teléfono.
- ⚠️ **Si la proyección "termina" en menos de un segundo, es el CODEC.** El
  `<video>` dispara `error` con un archivo que no sabe decodificar y se salta
  al siguiente; con todos fallando, la playlist acaba en milisegundos.
  Chromium NO lee **H.265/HEVC**, aunque el archivo se vea perfecto en VLC o
  en el móvil. La pantalla ahora **reporta qué archivos fallaron** en
  `/api/playlist/ended` y el panel lo dice con el comando de ffmpeg para
  reconvertir. `python -m backend.preflight` lo detecta antes con ffprobe.
- Endpoints: `POST /api/marketing/play`, `/api/marketing/stop`,
  `/api/playlist/ended`. Botones «Proyectar ahora» / «Cortar» en `/library`.
- Para añadir OTRO slot así: una entrada con `promo: True` y su `segments`
  (máximo de espacios), y una lista de frases en `config` para dispararlo.

### Modo MÚSICA — QUITADO (10 oct 2026)

El equipo pidió quitarlo, tal cual: **«quita el modo música, no sé por qué no
funcionó. No se reproduce nada»**. Se había hecho el 8 oct («modo música
MECH» → pregunta canción y artista → pone su video de YouTube en la
proyección) y se le arreglaron dos cosas el 9 oct (la lectura de la clave y
el permiso de sonido del navegador), pero en el robot siguió sin sonar y
**nunca se llegó a saber por qué** (no se vio la Pi fallando).

- **Ya no existe nada del modo**: `backend/music.py`,
  `backend/youtube_music.py`, `frontend/music.js`, `scripts/probar_musica.py`,
  `llm.interpret_song`, los métodos `*music*` de `mech_app`, los endpoints
  `/api/music/*`, las 30 listas `VOICE_MUSIC_*` y las 14 frases `music_*`, la
  tarjeta y los ajustes del panel, las claves `MUSIC_*`, `YOUTUBE_API_KEY` y
  `CLAUDE_MUSIC_MODEL`. Una línea `YOUTUBE_API_KEY=…` que quede en el `.env`
  de la Pi no hace nada (y no molesta).
- ⚠️ **No lo vuelvas a meter salvo que lo pidan.** Si lo piden, está entero
  en el historial: el último commit que lo tiene es `74ab082`
  (`git show 74ab082:backend/music.py`, etc.). Antes de rescatarlo, **ver el
  fallo en la Pi** (la línea del registro del panel): rehacerlo a ciegas
  repetiría lo mismo. Lo que se sabía que podía fallar y no se confirmó: el
  permiso de sonido del Chromium de la Pi, que la red del colegio bloquee
  youtube.com, y los videos que no se dejan incrustar.
- **NO confundir con la música de FONDO** de las obras (`background_audio.py`,
  `Plan.background_music`, `BACKGROUND_MUSIC_VOLUME`, el hueco «música» de
  `/library`): esa es otra función y **sigue igual**.
- **Lo que se quedó de esos días, porque sirve para el marketing:**
  - **El permiso de sonido de la proyección.** Chromium es UN solo programa:
    el flag `--autoplay-policy=no-user-gesture-required` solo cuenta en el
    PRIMER Chromium que se abre, y las ventanas siguientes se meten en él
    ignorando sus propias banderas. El primero es el PANEL (lo abre «Iniciar
    MECH»), así que `pi/panel-mech.sh` lleva el flag, y `pi/proyector-mech.sh`
    mira si hay un Chromium principal abierto sin él (`pgrep` +
    `/proc/<pid>/cmdline`, sin los procesos `--type=`) y se ofrece a cerrarlo
    y reabrirlo (Enter o 15 s = sí). ⚠️ Ese trozo de bash **no se ha corrido
    en la Pi** (se simuló con un `/proc` de mentira).
  - **La proyección comprueba el sonido AL ABRIRSE** (`comprobarSonido()` en
    `projector.html`: intenta reproducir una décima de silencio). Si el
    navegador se niega, deja puesto «Toca la pantalla para activar el
    sonido» y avisa por `POST /api/projection/sound`; el panel dice
    «Proyección abierta, con permiso de sonido» o «OJO: la proyección se
    abrió SIN permiso de sonido». La repite cada vez que el servidor vuelve.
  - **Las «bolitas» de reposo** de la proyección (ver `projector.html` en el
    mapa de archivos).

### Sismos recientes — el mapa del panel (8 oct 2026)

Pedido del equipo: «un mapa dentro del panel de control, como un apartado
extra, y que el mapa animado muestre sismos recientes apenas sean públicos».
Es la vista **Sismos** del menú lateral. `backend/sismos.py` baja los datos,
`frontend/sismos.js` los pinta.

⚠️ **Qué es y qué NO es — no lo vendas como otra cosa.** Muestra lo que YA
tembló, tal como lo publican las redes: EMSC tarda 5-10 minutos, USGS 1-3 en
Estados Unidos. **No predice y no es una alerta temprana**: cuando el punto
aparece, la sacudida ya pasó. La vista lo dice arriba, en negrita. Una alerta
de verdad (segundos de ventaja) necesita acuerdo con el OVSICORI o el USGS;
ver handoff.md.

- **Fuentes** (gratis, sin clave): **EMSC** (`seismicportal.eu`, servicio
  FDSN) y **USGS** (los GeoJSON de `earthquake.usgs.gov`). EMSC es la que
  trae Centroamérica: los sismos de Costa Rica llegan firmados `UNA`
  (= OVSICORI-UNA, comprobado en la tabla de contribuyentes de EMSC), los de
  Panamá `IGC`, los de Nicaragua `INET`. Medido el 8 oct: en una semana, 62
  sismos a menos de 5° de Costa Rica en EMSC y **4** en USGS. Por eso van
  las dos.
- **El mismo sismo sale en las dos fuentes** (163 de 320 en la prueba):
  `sismos._mismo()` los junta si coinciden en 40 s y 150 km. Se queda la
  ficha que llegó primero y se anota la otra fuente.
- **Qué se guarda**: 7 días. Del mundo, magnitud ≥ `SISMOS_MIN_MAG_WORLD`
  (4.0); dentro de «mi zona» (círculo de `SISMOS_ZONE_RADIUS_KM` alrededor
  de `SISMOS_ZONE_LAT/LON`), desde `SISMOS_MIN_MAG_ZONE` (2.5). La zona, el
  radio y el encendido se cambian EN VIVO en la tarjeta «Mi zona» de la
  propia vista (escribe el `.env` por `/api/config`, como Ajustes); los
  sitios del desplegable están en `ZONAS` de `sismos.js`.
- **La lista NO va en `state`** (ese viaja entero por WebSocket en cada
  cambio de fase, y son cientos de fichas): el panel la pide por
  `GET /api/sismos`; los NUEVOS llegan por el evento WS `sismos`. Mientras
  la vista está abierta también vuelve a pedir la lista cada minuto (trae
  las magnitudes que las redes corrigen después).
- **«Nuevo» = apareció después de la primera carga de ESA fuente** y ocurrió
  hace menos de 2 h. Lo primero que trae cada fuente es historia y no se
  anuncia. Un sismo nuevo dentro de la zona se apunta en el registro (nivel
  `warn`) y pone un punto ámbar en el menú si no se está mirando la vista.
- **Datos que gasta**: ~15 MB al día (las dos fuentes comprimen con gzip:
  8 KB por minuto + la semana entera cada media hora). Vale para el hotspot.
- **Los relojes no tienen por qué coincidir**: cada respuesta lleva `ahora`
  (hora del servidor) y el panel calcula el desfase, igual que la VR.
- **El mapa** (`sismos.js`): Mercator, dibujado a mano en un `<canvas>`.
  - Dos lienzos. El de abajo (80 000 puntos) **no se repinta en cada
    fotograma**: mientras la vista se mueve se estira la última imagen
    nítida y al parar (140 ms) se pinta bien. Sin eso, acercar el mapa
    tardaba 85 ms por fotograma en la laptop; en la Pi iría a tirones.
  - El de arriba se pinta ~30 veces por segundo si algo se mueve y 2 si no.
    Nada corre con la vista cerrada (`Sismos.mostrar(false)`).
  - ⚠️ Lo que cruza el borde del mapa (Chukotka, Fiyi, la Antártida pasan
    de 180° a −180°) se dibuja «desenrollado» y otra vez una vuelta más
    allá (`trazo()`). Sin eso salen rayas de lado a lado del mapa.
  - ⚠️ Los nombres de los lugares vienen de fuera: **siempre `textContent`**,
    nunca `innerHTML`.
  - Con el dedo NO se arrastra el mapa (el gesto es para desplazar la
    página); en el teléfono se mueve con los botones.
- **Las ondas P y S al tocar un sismo** son una animación en cámara rápida
  con velocidades típicas (6,5 y 3,7 km/s): sirven para explicar por qué
  existe la alerta temprana. Son aproximadas y la ficha lo dice («unos»).
- **El lugar se traduce a medias** (`sismos.lugar_es`): los patrones
  («18 km NNE of…», «NEAR COAST OF…») y una veintena de países. Lo que no
  encaja se queda en inglés. No es un fallo.
- **Marca de tsunami**: es el campo `tsunami` del USGS, que significa
  «revisar el aviso», NO que haya tsunami. La ficha lo dice así.
- Sin dependencias nuevas (`urllib` + `gzip`). El hilo arranca siempre con
  el servidor; apagado (`SISMOS_ENABLED=false`) se queda sin consultar nada.
- Claves: `SISMOS_ENABLED`, `SISMOS_POLL_SECONDS`, `SISMOS_ZONE_NAME`,
  `SISMOS_ZONE_LAT`, `SISMOS_ZONE_LON`, `SISMOS_ZONE_RADIUS_KM`,
  `SISMOS_MIN_MAG_WORLD`, `SISMOS_MIN_MAG_ZONE`. Todas en `_LIVE_KEYS`.
- Línea de arranque: `Sismos: mapa en el panel (vista «Sismos») · zona …`.

**MECH contesta sobre sismos (9 oct 2026)** — pedido del equipo: «dale a
MECH acceso a los datos de los sismos». «MECH, ¿ha temblado hoy?», «¿cuál fue
el último sismo?», «¿hubo alguno fuerte en el mundo?» se contestan con los
MISMOS datos del mapa, en el idioma del despertar.

- `sismos.para_claude()` arma un resumen corto (~3000 letras): los 8 más
  recientes de «mi zona» (cuándo, magnitud, lugar, km hasta MECH,
  profundidad, quién lo reportó), el más fuerte de la semana en la zona, los
  5 más fuertes del mundo y el más reciente. `llm.plan_response()` lo mete
  como un bloque de `system` **después del bloque cacheado** (cambia cada
  minuto: dentro invalidaría el caché en cada petición) y antes del idioma.
- **Va en TODAS las peticiones**, no solo cuando se pregunta por sismos: así
  vale en los diez idiomas y como lo escriba Whisper, sin listas de palabras.
  Las reglas del propio bloque le dicen a Claude que lo use solo si
  preguntan, en modo `qa`, un segmento, sin imagen.
- ⚠️ **Las reglas del bloque importan tanto como los datos**: son sismos que
  YA ocurrieron; MECH no predice ni alerta; no inventa; no tiene avisos de
  tsunami, daños ni réplicas (la marca `tsunami` del USGS **no se le pasa**).
  No las quites.
- Sin datos (apagado en el panel, o sin internet desde el arranque) el bloque
  dice justo eso, para que MECH conteste «ahora no tengo esos datos» en vez
  de inventar. Con más de 15 min sin conexión avisa de que puede faltar lo
  último.
- Interruptor: `SISMOS_ANSWERS_ENABLED` (default true, en `_LIVE_KEYS`; sin
  control en el panel). En `python -m backend.main` no hay hilo de sismos y
  no se pasa nada.
- `scripts/probar_sismos.py` mide el resumen y que viaja en la petición.
  **Sin probar con Claude de verdad**: cómo lo cuenta solo se oye en la Pi.

Lo que NO se hizo, y **no hay que hacerlo salvo pedido**: que MECH lo **diga
por su cuenta** cuando tiembla o lo **proyecte**, la tarjeta «qué hacer si
tiembla» y el simulacro. Se le propusieron al equipo y contestó que la
función de seguridad es el propio mapa y que eso ya lo tienen cubierto
(8 oct). Están apuntadas en handoff.md.

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

**Las repeticiones son las MISMAS para el saludo y para el giro hacia
afuera** (`ARM_WAVE_REPEATS`, default **3**): una sola perilla en el panel,
porque el equipo pidió el mismo criterio para los dos. Lo que cambia entre
ellos es la amplitud del arco, no el número.
⚠️ El número cuenta **las veces que el brazo llega ARRIBA**, incluida la
subida inicial — que es lo que se cuenta mirando el robot («3 rotaciones»
= sube, agita 2 veces más y baja). `scripts/probar_saludo.py` lo mide.

**El saludo es lento y AMPLIO a propósito** (todo ajustable en vivo):
`ARM_WAVE_SECONDS` (2.2 s) es lo que tarda en subir y bajar; `ARM_WAVE_HIGH`
(180°) hasta dónde llega; `ARM_WAVE_SWING` (65°) cuánto agita arriba. Antes era 170° con UN vaivén de 20° y el equipo dijo que
"casi no se notaba" (sep 2026).
**El brazo solo sube (90 → 180). Por debajo de 90 choca con el cuerpo** — el
código lo topa ahí; no bajes ese límite sin verlo en el robot.
El saludo mueve **SOLO el brazo DERECHO** (`ARM_WAVE_BOTH`, default
**false** desde sep 2026, pedido del equipo); en true el izquierdo sube a
acompañar. **"Hacia adelante"** depende del montaje del servo:
`ARM_INVERT_R` (default **true**: el equipo reportó que el derecho saludaba
hacia el lado contrario) / `ARM_INVERT_L` (false) dan la vuelta al recorrido
en `gestures._fisico()`, igual que `DIR_FL/FR/BL/BR` con las ruedas. El
reposo son 90 en los dos sentidos. En vivo desde Ajustes → «Sentido brazos».
Y **`ARM_GESTURE_MODE=subtle` ya
no encoge el saludo** — solo `off` lo desactiva. Antes, un `.env` con
`subtle` dejaba el saludo de bienvenida en un vaivén de 12° que no se veía.

### "Mira hacia afuera" / "Regresa a proyectar" (giro de 180°)

`backend/maneuvers.py`. En el stand MECH mira a la superficie donde proyecta;
con estas dos órdenes se pone de cara al público y vuelve.

- **Se atienden SIN pasar por Claude**: `mech_app.handle_movement_command()`
  las intercepta al principio de `handle_text_command`, así que responden al
  instante y no gastan crédito de API. Frases en `config.VOICE_OUTWARD_PHRASES`
  / `VOICE_PROJECT_PHRASES` (+ `_EN`), detección en `voice_phrases`.
- **La maniobra es UN SOLO tramo LATERAL** (`vy`), el mismo movimiento del
  botón «LATERAL» del panel, sostenido hasta quedar de espaldas. La vuelta es
  ese tramo con el signo cambiado, así que termina donde empezó. Nunca usa
  `vx` (eso lo lleva el odómetro de `return_to_start`).
  ⚠️ **NO se usa `w` (rotación) — a propósito** (sep 2026). Con estas ruedas
  el patrón de rotación hacía "un movimiento raro y muy corto"; el que gira
  de verdad es el lateral. Es coherente con el resto del proyecto: la
  cinemática está calibrada a mano y no coincide con la mecanum de libro. Si
  alguien vuelve a meter `w` aquí, repite el mismo problema.
- **Sentido**: `TURN_180_INVERT` (en vivo desde Ajustes) lo cambia de lado
  sin tocar el firmware ni recablear.
- **Los brazos al girar hacia afuera van a MEDIO gas**: `gestures.wave_outward()`
  (145°, 30° de vaivén, UN brazo), entre el saludo de bienvenida (180°, 65°,
  dos brazos) y el gesto de narrar (115°). El equipo pidió que se notara pero
  "no tanto" como la bienvenida.
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
- **TODO lo que mueve ruedas va a POTENCIA 100** (sep 2026, pedido del
  equipo): giro, lateral, `VISION_MAX_SPEED` (acercarse), `RETURN_SPEED`
  (`return_to_start`), `GESTURE_WHEEL_SPEED` (balanceo de gestos) y los
  botones del panel. **Los BRAZOS son la excepción**: van lentos y suaves.
  El balanceo de gestos, al ir a 100, dura muy poco (`GESTURE_WHEEL_SECONDS`,
  0.18 s) para que sea un acento y no un desplazamiento.
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
- **Estado**: `state["facing"]` = `"projection"` | `"outward"` | **`"manual"`**,
  evento WS `facing`, visible en la vista Arduino del panel. Un `look_outward`
  estando ya afuera no gira otra vez, ni un `back_to_projection` estando ya en
  la proyección (así una orden repetida no lo da vuelta de nuevo).
  ⚠️ **`"manual"` = NO LO SABE** (26 sep 2026). El equipo reportó que
  «regresa a proyectar» no giraba: lo habían dado vuelta con el panel
  (botones GIRO/LATERAL, comando crudo con giro o «PROBAR MEDIA VUELTA»), MECH
  seguía creyendo que miraba a la proyección y contestaba «ya estoy en
  posición». Ahora esos movimientos llaman a `maneuvers.mark_manual()`, y en
  "manual" las dos órdenes EXPLÍCITAS obedecen siempre (quien las da ve el
  robot; un giro de 180° acaba en la misma orientación por cualquier lado).
  Lo AUTOMÁTICO (volver solo antes de narrar) NO gira en "manual": solo con
  `"outward"`. Avanzar/retroceder no cambia la orientación.
- **`execute_plan` se da vuelta solo**: si le piden una historia estando de
  espaldas, vuelve a la posición de proyección antes de narrar.
- **Paro de emergencia** = `maneuvers.assume_projection()`: tras un paro no
  sabemos hacia dónde quedó, así que se asume "projection" y el operador lo
  recoloca a mano (igual que el reset del odómetro).
- Botones en el panel (vista Arduino) y endpoints `POST /api/move/outward`,
  `/api/move/projection`, `/api/move/greet`, `/api/move/testturn`.

### "Avanza diez segundos" / "retrocede cinco segundos"

`maneuvers.advance()`. Orden directa, sin pasar por Claude, igual que el giro.

- El número es **opcional**: sin él usa `ADVANCE_SECONDS` (Ajustes →
  "Avanzar"). Con él, manda lo que digan —
  `voice_phrases.extract_seconds()` entiende dígitos y letra ("diez"),
  que es como lo transcribe Whisper.
- Topa en `ADVANCE_MAX_SECONDS` (30 s): en un stand, un robot lanzado varios
  metros es un problema, y una orden mal entendida no debería provocarlo.
- **Resetea el odómetro al terminar.** Si alguien pide expresamente mover el
  robot, esa pasa a ser su posición de trabajo; si no, `return_to_start()`
  desharía el movimiento antes de la siguiente narración, que es justo lo
  contrario de lo que se pidió.

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
- **App de Windows `MECH Panel.exe` (sep 2026)** — lanzador de escritorio que
  **encuentra la Pi sola** (mech.local, mech, la última dirección, y si no
  barre la red buscando `/api/state`) y abre el panel en ventana de
  aplicación. Solo control remoto. Solo librería estándar → .exe de 10 MB
  con PyInstaller (`windows/construir_exe.ps1`) e instalador opcional con
  Inno Setup (`windows/MECH-Panel.iss`). Es lo único que se conservó al
  revertir a `c0e0310` (ver el aviso de arriba). Desde el 23 sep tiene un
  cuarto botón, **«Biblioteca de videos (en el navegador)»**.
- **«Regresa a proyectar» que no giraba, arreglado (26 sep 2026)** — tres
  causas: girarlo a mano desde el panel no le decía a MECH que ya no miraba a
  la proyección (estado nuevo `"manual"`), «vuelve a la proyección» no se
  entendía (frases nuevas en `VOICE_PROJECT_PHRASES`) y en inglés «go back to
  projecting» lo hacía RETROCEDER (el giro se comprueba ahora antes). Medido
  en simulación con el código real. Movilidad **v4**.
- **Controles de movimiento del panel corregidos (23 sep 2026)** — AVANZAR
  iba hacia atrás y los LATERAL giraban. Ver la actualización de la
  cinemática (arriba): `DRIVE_INVERT_FORWARD` + botones GIRO = `vy`,
  LATERAL = `w`.
- **Guía de uso `docs/USO.md` (23 sep 2026)** — reescrita al día: encender,
  despertar/dormir, obras, traductor de una frase, moverlo (voz y panel),
  saludo, biblioteca, problemas y resumen de comandos.
- **Recorte automático al subir (23 sep 2026)** — campo `trim` de `WORKS`
  (`{segmento: ("inicio"|"final", segundos)}`). La relatividad lo usa a
  pedido del equipo: seg 1 → primeros 20 s, seg 2 → primeros 10 s,
  **seg 3-7 → ÚLTIMOS 10 s**. Lo hace
  `video_library.trim_uploaded()` con ffmpeg justo después de
  `POST /api/library/{slug}/{seg}` (en `asyncio.to_thread`, re-codificando a
  H.264: copiando solo se puede cortar en fotogramas clave). El original
  queda en `<slug>/originales/`; si no hay ffmpeg o falla, **se usa el video
  entero** y el panel avisa — nunca se pierde lo subido. `/library` marca con
  ✂ los segmentos que recortan. Solo afecta a lo que se suba DESPUÉS del
  cambio. Probado con ffmpeg simulado (en la laptop no hay ffmpeg).
- **Modo TRIVIA recuperado, estilo Kahoot (25 sep 2026)** — al terminar
  una obra, MECH pregunta «¿Te gustaría realizar una trivia para comprobar
  tu conocimiento?» (en el idioma activo), proyecta cada pregunta con
  fichas de colores A/B/C, celebra el acierto con confeti y, al fallar,
  dice «No has acertado. La respuesta correcta es la B: …». Verificado:
  `probar_trivia.py` 50/50, 0 choques con otras órdenes, una partida
  completa simulada con el código real y las 6 pantallas vistas en el
  navegador a 1280×720. Sin probar en la Pi.
- **CRISPR y Cas9** — guiones en [`docs/GUIONES_CRISPR.md`](docs/GUIONES_CRISPR.md)
  (5 escenas + datos verificados con fuentes) y, desde el 26 sep, la obra
  `crispr` en la biblioteca con **5 segmentos** y 18 `facts` (el primero le
  dice a Claude qué escena va en cada video; los dos últimos son trampas que
  NO debe decir). Sin recorte automático.
- Documentación (GUIA.md, FRONTEND.md, PRUEBAS_HARDWARE.md, windows/README.md).
- **Biblioteca de videos pre-renderizados (Opción B)** — manifest, schema, dispatch
  en execute_plan, fallback a NanoBanana, UI `/library` para subir mp4s,
  endpoints REST `GET/POST/DELETE /api/library/...`. Obras actuales:
  `don_quijote`, `campana_1856`, `jimenez_deredia`, `malpais`,
  `isidro_con_wong` (4 segmentos c/u), `isaac_newton` (5 segmentos:
  contexto, vida, annus mirabilis, Principia, legado; 17 `facts`
  verificados), `relatividad` (**7 segmentos**, uno por escena del guion,
  22 `facts`; el 8, «la relatividad hoy», se quitó el 26 sep a pedido del
  equipo, pero sus datos siguen en los `facts`) y `crispr` (**5 segmentos**, 18 `facts`). Guiones para generar
  sus videos en [`docs/GUIONES_NEWTON.md`](docs/GUIONES_NEWTON.md),
  [`docs/GUIONES_RELATIVIDAD.md`](docs/GUIONES_RELATIVIDAD.md) y
  [`docs/GUIONES_CRISPR.md`](docs/GUIONES_CRISPR.md). El primer
  `fact` de la relatividad le dice a Claude qué escena va en cada video, y
  el segmento 4 (transformaciones de Lorentz) es el único con fórmulas en
  pantalla. Ocho es el máximo de segmentos de un plan (`max_length=8`).
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
- **Cadena de audio antes de Whisper (sep 2026)** — `stt.prepare_for_whisper()`:
  pasa-altos (quita continua y retumbe) → remuestreo a 16 kHz **con filtro
  anti-aliasing de verdad** → nivel objetivo ("AGC"). Es la versión mínima de
  lo que hace un teléfono; ver [`docs/AUDIO.md`](docs/AUDIO.md), que explica
  el porqué de cada etapa y lo que falta.
  ⚠️ **El remuestreo tenía un defecto real**: promediaba bloques de 3
  muestras, y eso deja pasar los agudos de 8-16 kHz *plegados* dentro de la
  banda de la voz (a 10 kHz solo los atenuaba 9 dB; ahora 48 dB). Solo aplica
  si `AUDIO_SAMPLE_RATE` > 16000 — en la Pi debe ser **48000**.
  `_frame_rms()` también resta la continua: un offset del receptor USB
  inflaba el piso de ruido y dejaba a MECH sordo para el "ok MECH".
  Claves en vivo (Ajustes): `AUDIO_HIGHPASS_HZ`, `AUDIO_TARGET_DBFS`,
  `WHISPER_BEAM_SIZE` (5; el de interrupciones sigue en 1, ahí manda el
  retardo).
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
- **Sitio web MULTIPÁGINA para Vercel (sep 2026)** — se rehízo por completo:
  7 páginas HTML independientes (ver mapa de archivos), CSS y JS compartidos en
  `web/css/` y `web/js/`, `vercel.json` con `cleanUrls`. **Para desplegar:
  Vercel → Root Directory = `web`, framework "Other", sin build command.**
  FUENTE DE CONTENIDO: `Documentación/MECH/MECH Nacional/MECH-3 Final.pdf`
  (IEEE, sep 2026) + `branding/Business Model Canvas MECH.pdf`. Novedades que
  trajo ese documento y que YA están en la web: **MECH-3 en desarrollo** y
  MECH-4 planeado (antes el último era MECH-2); batería de **8 h**; toda la
  **crisis educativa de Costa Rica** (PIB 5,3%→4,9%, PISA 2022, 96% en mates
  insuficiente, 63%→¼ en lectura); **escuelas unidocentes** (35% de las
  públicas, mitad con <10 alumnos, inglés 89% vs 26%, 1 de cada 3 deserta) y el
  caso Flor de Islita; estudios nuevos (DCMS 60% vs 73%, Karolinska/Todorov
  sobre novedad y dopamina); el partner **360 Health & Value**; y el modelo de
  negocio (costo $756,91 · venta $1000 · servicio $50).
  **Barra de patrocinadores**: marquesina infinita en CSS (dos filas
  duplicadas + `translateX(-50%)`, 38 s lineal), **fondo CLARO a propósito**
  porque los logos son de tinta oscura. Los logos se generan con
  `branding/scripts/prep_logos.py` desde `branding/patrocinadores/` →
  `web/assets/logos/`. Si se añade uno, hay que meterlo en LAS DOS filas.
  **Perfiles del equipo** (`empresa.html`): estilo editorial pedido por el
  equipo — nombre enorme en **Playfair Display** (serif) con un punto del color
  de acento, rol en mono itálico y foto circular difuminada al fondo, con el
  lado alternando por persona. ⚠️ Las reglas van anidadas como
  `.profile .profile-name` porque si no `.section h3` (más específica) impone
  20 px. Retratos generados con `branding/scripts/prep_equipo.py` desde
  `branding/equipo/{Leo,Ale,Jimmy}/` (detecta el rostro con OpenCV, encuadra
  cabeza+torso, desatura, oscurece y aplica viñeta) → `web/assets/equipo/`.
  **NO hay sección de colaboradores** (el equipo pidió quitar esos nombres).
  **NADA de barras de color arriba de las tarjetas**: se ven poco
  profesionales. El acento es `.card-accent` = borde fino del color del tint
  rodeando la tarjeta + glow tenue (`box-shadow`).
  **Diagramas**: se usan los de `branding/` (arquitectura, caso de uso y los
  dos de flujo, generados con `branding/scripts/diag_*.py`), NO el
  `diagrama-capas.png` viejo que salía del PDF — ese ya se borró.
  **Figuras del anexo** (`web/assets/figuras/`): las 24 imágenes reales del
  trabajo escrito (figuras 3–26 + el BMC actualizado), extraídas con
  `branding/scripts/prep_figuras.py`, que lleva el mapeo
  `(página, índice) → figura` verificado a mano contra los pies de foto.
  Se usan en la bitácora de `robot.html` (figs 3–14), en las galerías de
  MECH-2 (15–20) y los diseños 3D de MECH-3 (21–25) en `evolucion.html`,
  el retrato oficial (26) en `empresa.html` y el BMC en `aplicaciones.html`.
  Sustituyeron a los `build-0*.jpg`/`robot-final.jpg`/`canvas-negocio.png`
  del PDF viejo, que ya se borraron.
  **Actualización con `MECH California.docx` (26 sep 2026)** — el trabajo
  escrito nuevo (en inglés) añade las figuras **26–45**; salen del `.docx`
  (más resolución que el PDF) con el mismo `prep_figuras.py` (`MAPA_DOCX`,
  mapeo `imageNN.jpeg → figura` verificado a mano). La numeración cambió: el
  retrato del equipo pasó de figura 26 a **44** (`fig44-miembros.jpg`) y la
  26 es ahora MECH-2 desarmado. En `robot.html` los pies siguen al documento
  (Fig. 1 arquitectura, **Fig. 2 caso de uso**; los flujos van como
  «DIAGRAMA ·», porque no están en el documento).
  ⚠️ `vercel.json` sirve `/assets` como `immutable` (1 año): si una figura
  cambia de contenido, **nombre nuevo**, nunca pisar el archivo.
  **Salón de trofeos** (`index.html#trofeos`, pedido del equipo) — SOLO
  estos tres títulos, todos primer lugar: **campeones nacionales WRO 2026
  Future Innovators** (con MECH-3), **campeones regionales de Guanacaste
  WRO 2026 Future Innovators** (con MECH-2) y **campeones del Torneo STEAM
  Luvá – Electrotec** (con **TitoBot**, otro robot del equipo, no MECH).
  La regional de Alajuela (MECH-1, 7.º lugar según el documento) aparece en
  Evolución como «debut», **sin el puesto** — a propósito; no lo pongas sin
  preguntar. Distintivo «CAMPEONES NACIONALES · WRO FUTURE INNOVATORS» en
  el hero que enlaza al salón.
  **Debajo de los tres títulos va el resultado internacional (10 oct 2026,
  pedido del equipo): «4.º lugar en WRO Las Américas», con MECH-4.** No es
  un título, así que no cuenta entre los tres («Tres torneos. Tres títulos.»
  sigue igual): es una tarjeta aparte, a lo ancho y en verde
  (`.trophy-intl` en `web/css/styles.css`). La misma tarjeta sale en
  `evolucion.html#competencias`. ⚠️ El equipo solo dijo «quedamos de 4to
  lugar con MECH-4 en WRO Las Américas»: **no hay foto, ni sede, ni fecha,
  ni categoría**. No las inventes; si las dan, se añaden.
  **`evolucion.html` = cinco generaciones, las cinco LANZADAS (10 oct
  2026)**: MECH-1, MECH-2 (campeón regional), MECH-3 (campeón nacional),
  MECH-4 (4 idiomas, trivia, traductor, «Hey MECH», parlante alámbrico,
  cargador el doble de rápido, diseño más moderno; **4.º lugar en WRO Las
  Américas**) y **MECH-5 = EL MODELO ACTUAL**: seis idiomas nuevos (diez en
  total), panel de control rediseñado y modo sismos (el modo música figuró
  un día y se quitó de la web el 10 oct, a la vez que del robot). Secciones:
  comparación (fig. 38), línea de tiempo, en competencia (39–41 + la tarjeta
  de Las Américas), MECH-2, MECH-3 (seis mejoras, render vs. real,
  desarmable/cargador/circuito, bitácora 26–34, diseño 3D 21–25), MECH-4 y
  MECH-5 (`#mech5`, tres tarjetas). ⚠️ El modo sismos se describe como lo
  que es («informa de lo que ya ocurrió: no predice»); no lo cambies a
  «alerta» ni «predicción». La figura 38 solo compara MECH-1/2/3: no hay
  imágenes de MECH-4 ni de MECH-5 todavía.
  **Interruptor de idioma ES/EN** (`web/js/i18n.js`): el sitio se escribe en
  español y el inglés vive en un diccionario `{texto español: HTML inglés}`.
  El botón va en la barra de navegación (inyectado por JS, así aparece en las
  8 páginas) y la elección se guarda en `localStorage`; también cambia
  `<html lang>` y el `<title>`. Al añadir texto nuevo hay que meter su pareja
  en el diccionario; si falta, esa frase se queda en español (no rompe).
  ⚠️ La clave se calcula quitando etiquetas **por un espacio** (si no, un
  `<br>` pega las palabras: "interésen"), decodificando entidades (`&amp;` →
  `&`) y volviendo a pegar la puntuación (`<b>x</b>.` dejaría " ."). Si una
  cadena "no traduce", casi siempre es una de esas tres cosas.
  **Móvil**: no se configura en Vercel — es el `viewport` + el CSS responsive.
  Verificado sin desbordes a 390 px y 360 px en las 8 páginas; hay
  `theme-color`, `viewport-fit=cover` y `site.webmanifest`. Ojo: los hijos de
  `.grid` llevan `min-width:0` porque si no una tabla ancha desborda la
  pantalla.
- **Sitio web de presentación (`web/`) — historial**: antes era one-page con la
  estética del proyecto (dark `#0e0e12`, Sora/Space Mono, logo oficial en SVG).
  FUENTE DE CONTENIDO previa: el trabajo escrito `Documentación/Proyecto
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
  - **SINCRONIZADO con la pantalla principal, y de forma CONTINUA** (sep 2026). Antes, al entrar al
    visor el video empezaba DESDE CERO mientras el audio (que sale por el
    parlante de la Pi, al ritmo de `/projector`) ya iba por la mitad: se veía
    descuadrado siempre. Ahora `/projector` reporta por qué segundo va
    (`POST /api/playback` cada 2 s y al cambiar de archivo) y el visor salta
    a ese punto. **Se manda la posición + la ANTIGÜEDAD del dato (`age`), no
    una hora absoluta**: el reloj del teléfono no tiene por qué coincidir con
    el de la Pi, así que el visor solo suma `position + age`. `/api/state`
    recalcula `age` al responder (`mech_app.refresh_playback()`), que es de
    donde se alimenta el sondeo del móvil. Con un clip en bucle se usa el
    módulo de la duración. Tolerancia de 0.6 s y como mucho un salto cada
    1.5 s: buscar posición en un móvil parpadea, y no vale la pena por unas
    décimas.
  - **La corrección es continua, no de una sola vez.** Sincronizar solo al
    cargar el video no bastaba: el móvil PAUSA el video al salir de la
    página, y al volver arrancaba desde cero (se notaba sobre todo en la
    playlist de marketing, donde los videos son largos y no van en bucle).
    Ahora hay un tic cada segundo, y `visibilitychange` / `pageshow` /
    `focus` fuerzan un reenganche inmediato saltándose el antirrebote.
  - El reporte se guarda **con la hora local en que llegó**
    (`playbackAt`), y el objetivo se recalcula como
    `position + age + (ahora − playbackAt)`. Sin eso, reusar el mismo
    reporte apuntaba a un punto cada vez más viejo.
  - ⚠️ **`play()` sobre un video terminado lo REINICIA desde cero.** Por eso
    todos los `play()` de reanudación van con `if (v.paused && !v.ended)`.
    Es fácil volver a meter este bug al "arreglar" que el video se quede
    pausado.
  - En la playlist promo el visor sigue el `index` que reporta la pantalla
    (no asume que va por el primero) y NO pone `loop` (esos videos se ven
    enteros).
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
- **Saludo UNA VEZ por visitante (sep 2026)**: MECH saluda a quien llega y
  **no vuelve a saludar hasta que la cámara se queda vacía
  `GREETING_REARM_SECONDS` seguidos** (20 s, en vivo desde Ajustes →
  «Visitante nuevo»).
  ⚠️ **Por qué hacía falta**: `vision.LOST_AFTER_S` son 1.5 s, así que
  cualquier parpadeo del detector (una cabeza que gira, un falso positivo con
  la luz de la proyección) contaba como "se fue y volvió" → llegada nueva.
  Lo único que lo frenaba era el cooldown, así que MECH **repetía el saludo
  cada 45 s aunque no hubiera nadie delante**. El reloj de ausencia se
  REINICIA en cada pérdida (`on_user_lost`), de modo que un detector que
  parpadea nunca lo completa. `_greeting_rearmed()` en mech_app.
- **La cara tiene que MANTENERSE para contar como una llegada (8 oct
  2026)**: el equipo reportó que MECH «a veces saluda incluso cuando no hay
  personas al frente». Causa: a `vision.py` le bastaba **UN fotograma** con
  cara para llamar a `on_user_detected()`, así que un reflejo o una sombra
  que el detector confundía un instante (en la Pi corre el Haar, que da
  falsos positivos sueltos) ya era un visitante. La regla de «visitante
  nuevo» no lo frenaba: con la cámara vacía de verdad, el reloj de ausencia
  SÍ se completa, y el siguiente fotograma falso saludaba.
  Ahora decide `vision._Llegada`: cada fotograma con cara suma su duración
  y cada uno sin cara **descuenta la mitad**; solo al llegar a
  `GREETING_CONFIRM_SECONDS` (1.0 s, en vivo desde Ajustes → «Confirmar
  cara»; 0 = lo de antes) se avisa a `mech_app`. Un falso positivo suelto, o
  uno que parpadea menos de un tercio del tiempo, no llega nunca; una cara
  real que el detector pierde a ratos sí (~2 s viéndola el 70 %).
  ⚠️ Solo cambia CUÁNDO se avisa de la llegada (y por tanto el saludo):
  `present` / `state["vision"]["user_present"]`, el acercarse y el gate de
  proyección siguen reaccionando al primer fotograma, como antes. Y una
  presencia que no llegó a confirmarse **no** cuenta como «se fue alguien»
  (no reinicia el reloj de ausencia). Medido con
  `python scripts/probar_llegada.py`. **Sin probar en la Pi.**
- **Saludo SOLO EN REPOSO (sep 2026)**: el saludo por cámara se dispara
  únicamente con MECH **en reposo** (`GREETING_ONLY_DORMANT`, default true,
  en vivo desde Ajustes → «Saludar por cámara solo en reposo»). Despierto
  está narrando, conversando o traduciendo, y soltar «¡Hola! Soy MECH»
  encima de eso le corta la experiencia al visitante que ya está atendiendo.
  **Y NUNCA mientras presenta algo**, aunque se apague esa regla: mientras
  corre `execute_plan` o `play_playlist` hay un contador
  (`mech_app._presentation()`) que bloquea el saludo pase lo que pase con
  la fase de voz, además de las fases ocupadas. Las dos reglas viven en
  `mech_app._greeting_blocked()` y valen igual para la cámara y para el
  botón **«SALUDAR AHORA»** (que solo se salta el cooldown).
  El aviso «No saludo…» sale como mucho **una vez por
  minuto** — la visión detecta a ~10 fps y si no llenaría el panel.
- **Saludo de 3 rotaciones, en ESPAÑOL (sep 2026; el idioma cambió en oct
  2026)**: el brazo DERECHO sube hacia adelante y llega arriba **exactamente
  3 veces** (`ARM_WAVE_REPEATS=3`, `ARM_WAVE_BOTH=false`,
  `ARM_INVERT_R=true`) y la frase sale en **español** («¡Hola! Soy MECH. Un
  gusto verte hoy aquí», `GREETING_LANGUAGE=es`). En septiembre el equipo lo
  pidió en inglés y en octubre lo devolvió a español — **no lo vuelvas a
  poner en inglés por tu cuenta**. ⚠️ `GREETING_LANGUAGE` **NO cambia el
  idioma de MECH**: eso lo sigue decidiendo la frase con que se le
  despierta. El subtítulo del saludo va etiquetado en ese idioma
  (`start_subtitles(code=)`).
  ⚠️ **El `.env` de la Pi casi seguro tiene `GREETING_LANGUAGE=en`
  guardado** (el panel escribe todas sus perillas): si tras actualizar sigue
  saludando en inglés, es eso — Ajustes → «Idioma del saludo» → ESPAÑOL →
  «Guardar y aplicar». El arranque lo delata: loguea «… · saludo en inglés».
  ⚠️ **Eco del saludo**: en español la frase lleva un «MECH», así que su eco
  no puede colarse como un despertar. La guarda (`mech_app.greeting_until`)
  se compara ahora con el momento en que se GRABÓ el audio
  (`inicio_audio` en el bucle de `server.py`), no con la hora de después de
  transcribir: Whisper tarda 1-2 s en la Pi y la ventana ya estaba cerrada.
  ⚠️ **«Guardar y aplicar» del panel escribe TODAS las perillas en el
  `.env`**, así que un `ARM_WAVE_REPEATS=2` viejo en el `.env` de la Pi tapa
  el default. El preflight (§9) avisa si el saludo no está como se pidió.
- **Saludo al detectar usuario (calibrado con videos del equipo, jul 2026)**:
  al ver a alguien, MECH dice «¡Hola! Soy MECH. Un gusto verte hoy aquí»
  (`mech_app.GREETING_TEXT`, cooldown 60 s, no interrumpe narraciones) y hace
  el **protocolo de saludo**: UN arco amplio y lento del brazo derecho
  (90→170, vaivén arriba, baja) — video 1 del equipo. El bucle de voz ignora
  transcripciones mientras dura el saludo (`mech_app.greeting_until`) para no
  procesar su propio eco. Los gestos AL HABLAR son pequeños (máx ~125°,
  `_TALK_MAX` en gestures.py): no girar todo el brazo — video 2 del equipo.

- **Cinco idiomas más: alemán, italiano, japonés, ruso y mandarín (5 oct
  2026)** — mismo mecanismo de siempre (el despertar decide el idioma), con
  todo traducido: frases fijas, giro, órdenes de movimiento, marketing,
  traductor, trivia (voz y pantalla), `initial_prompt` de Whisper y directiva
  para Claude. Chips nuevos en el panel y opciones en los desplegables del
  traductor y del saludo. Verificado SIN hardware: `scripts/probar_idiomas.py`
  (todo bien), el matcher de antes contra el de ahora en texto latino (sin
  diferencias) y una simulación con `mech_app` y el bucle de voz reales
  (despertar, dormir, moverse, traducir y jugar en los cinco). **Sin probar
  con el micrófono**: ver «Idiomas que no usan letras latinas».
- **Estética nueva del panel (5 oct 2026)** — pedido del equipo: «que el
  fondo no sea ese violeta». Mismos controles, otra piel: ver «Estética del
  panel».
- **Panel menos saturado y con menús animados (6 oct 2026)** — los diez
  idiomas caben en un botón con menú, los desplegables son menús propios, el
  resaltado del menú lateral se desliza y las vistas entran en cascada al
  cambiar con el ratón. De paso: el chat ya no repite burbujas y el
  desplegable del micrófono ya no puede borrar el micrófono configurado. Ver
  «Menús animados y los diez idiomas en uno». Verificado en el navegador con
  un servidor de mentira (escritorio y tamaño de teléfono). **Sin probar en
  la Pi.**
- **Coreano, japonés y chino legibles en cualquier aparato (6 oct 2026)** —
  el coreano salía con cuadritos en el chat porque la Pi no trae esa letra.
  Ahora las fuentes van en el repo (7 MB) y las usan el panel, los subtítulos
  y la trivia; ya no hace falta `fonts-noto-cjk`. Ver «La letra de coreano,
  japonés y chino va incluida». Verificado en Windows midiendo qué fuente se
  usa de verdad (la incluida, no la del sistema) y que el español no cambia.
  **Sin probar en la Pi**, que es donde fallaba.
- **Rediseño «de app» del panel (8 oct 2026)** — tema oscuro con mucho más
  contraste, armazón fijo de app, la vista Voz en tarjetas, el micrófono que
  cambia de color con la fase, iconos en vez de emojis, deslizadores
  rellenos, Ajustes en grupos y accesos a Biblioteca / Proyección / Atajos
  en el menú. Ver «Rediseño "de app"». Verificado en el navegador con el
  servidor de mentira (las siete vistas, las seis fases, escritorio ancho,
  ventana de 900 px y tamaño de teléfono) y con el preflight §8 (los 42
  iconos tienen glifo). **Sin probar en la Pi.**
- **App de Windows sin construir nada (8 oct 2026)** — `Instalar MECH.bat`
  deja un icono «MECH» que busca al robot y abre el panel en su ventana. Ver
  «App de Windows sin construir nada». Probado: el instalador y el
  desinstalador en una carpeta temporal (acceso directo leído de vuelta) y
  la pantalla de búsqueda en el navegador (no encontrado, dirección a mano,
  encontrado, volver desde el panel). **Sin probar con el robot ni abriendo
  el icono de verdad**: el equipo tiene que instalarla y probarla.
- **Mapa de sismos recientes en el panel (8 oct 2026)** — vista «Sismos»:
  mapa animado con los sismos de los últimos 7 días (EMSC + USGS, sin
  clave), lista, ficha con las ondas P y S, repaso animado del periodo y
  «mi zona» configurable en vivo. Informa de lo que ya tembló; **no predice
  ni alerta**. Ver «Sismos recientes — el mapa del panel». Verificado:
  `scripts/probar_sismos.py` (48 comprobaciones + las fuentes reales) y la
  vista en el navegador con un servidor de mentira que corre
  `backend/sismos.py` de verdad (datos reales, llegada en vivo, cambio de
  zona, apagar/encender, escritorio ancho, 1440 px y teléfono). **Sin probar
  en la Pi.**
- **Modo música: hecho el 8 oct y QUITADO el 10 oct 2026**, a pedido del
  equipo («no sé por qué no funcionó. No se reproduce nada»). Ver «Modo
  MÚSICA — QUITADO»: qué se borró, dónde está en el historial y lo que se
  quedó porque le sirve al marketing (el permiso de sonido de la
  proyección). Verificado tras quitarlo: `probar_idiomas`,
  `probar_comandos_idioma` (el bucle de voz real), `probar_trivia` 50/50,
  `probar_saludo`, `probar_sismos`, `probar_llegada`, el preflight, y el
  panel y la proyección en el navegador. **Sin probar en la Pi.**
- **Modo inglés bajo demanda (ago 2026)** — `backend/lang.py` guarda el idioma
  activo. «wake up MECH» despierta en INGLÉS (Whisper en `en`, narración de
  Claude en inglés, frases fijas y subtítulos en inglés); «ok MECH» /
  «despierta MECH» sigue en español. Al dormirse vuelve a español solo. En
  reposo se re-transcribe el audio si el primero no dio wake, para no perder
  «wake up MECH» por un error de Whisper. Chips en la vista Voz del panel
  (`POST /api/language/{código}`) para probar sin voz.
  Claves: `WAKE_ENGLISH_ENABLED`, `VOICE_WAKE_PHRASES_EN`,
  `VOICE_SLEEP_PHRASES_EN`.
- **Francés y portugués (sep 2026)** — mismo mecanismo que el inglés, ahora
  generalizado a CUATRO idiomas: «bonjour MECH» / «salut MECH» /
  «réveille MECH» despiertan en FRANCÉS y «bom dia MECH» / «boa tarde MECH» /
  «acorda MECH» en PORTUGUÉS. Tienen su juego completo de frases fijas,
  frases de las maniobras (`maneuvers._SAY`), órdenes de movimiento, frases de
  interrupción y de reposo, `initial_prompt` de Whisper y directiva de idioma
  para Claude. Chips FR/PT en la vista Voz. Al arrancar, el server loguea
  **«Idiomas: español · inglés · francés · portugués»** — si esa línea no
  sale, la Pi está corriendo código viejo.
  El reintento de despertar ya NO prueba idioma por idioma (serían 3 pasadas
  de Whisper por cada ruido): re-transcribe UNA vez con **detección
  automática** (`stt.transcribe_any`) y compara contra todas las listas.
  Claves nuevas: `WAKE_FRENCH_ENABLED`, `WAKE_PORTUGUESE_ENABLED`,
  `VOICE_*_PHRASES_FR`, `VOICE_*_PHRASES_PT`.
- **Modo TRADUCTOR (sep 2026)** — «traduce MECH» convierte a MECH en
  intérprete entre dos personas. Va **por turnos**: pregunta qué traducir,
  escucha UNA frase, la dice en el otro idioma (con subtítulo) y se calla;
  para la siguiente hay que repetir el comando. El par de idiomas se
  recuerda entre turnos. Bidireccional (Whisper detecta en qué idioma se
  dijo la frase). No pasa por Claude salvo una llamada corta de traducción
  (`llm.translate`). Se olvida con «deja de traducir», durmiéndolo o con el
  paro. Tarjeta nueva en el panel (vista Voz) para elegir el par a mano.
  Módulo: [`backend/translator.py`](backend/translator.py).
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

- **Slot de MARKETING con audio propio (sep 2026)** — «proyecta marketing»
  reproduce los videos del slot `promo` ENTEROS, en fila y con su propio
  audio, sin que MECH narre encima. Proyecta aunque falten videos (12
  espacios, ninguno obligatorio) y se salta los huecos. No pasa por Claude.
  El fin de cada video lo marca la pantalla (`POST /api/playlist/ended`).
  ⚠️ Chromium necesita `--autoplay-policy=no-user-gesture-required` para que
  se oiga.
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
15b. **Si le hablan en japonés, ruso o chino y no despierta**, casi seguro
    es el NOMBRE: Whisper escribió «MECH» de una forma que no está en
    `VOICE_NAME_ALIASES`. El panel lo enseña («Oí en japonés: '…'»). Se añade
    en el `.env`, sin tocar código. `WHISPER_MODEL=small` ayuda bastante con
    estos tres idiomas (y cuesta ~2.5× de tiempo).
15c. **Coreano, japonés o chino con CUADRITOS** (panel, subtítulos o trivia)
    = el navegador no tiene con qué dibujar esos caracteres. Desde el 6 oct
    2026 la letra va incluida (`frontend/vendor/fonts/cjk/`), así que si
    pasa es que la Pi no ha hecho `git pull`, que el navegador tiene la
    página vieja guardada, o que falta algún archivo (lo dice el preflight,
    §8 y §11). MECH habla bien igual: es solo la pantalla.
16. **El idioma se decide en el DESPERTAR, no en medio de la conversación.**
    Si alguien le habla en francés a un MECH despierto en español, Whisper
    transcribe con el modelo español y sale basura: hay que dormirlo y
    despertarlo con la frase de ese idioma. Desde oct 2026 decirla estando
    despierto **ya no** cambia el idioma, y los comandos solo valen en el
    idioma activo (`VOICE_STRICT_LANGUAGE`, ver «Idiomas»). Es a propósito:
    así el stand no cambia de idioma por accidente. Si quedó en un idioma
    equivocado y nadie sabe dormirlo en ese idioma: botón **IDIOMA** de la
    vista Voz del panel → Español.
17. **`VOICE_WAKE_PHRASES_{EN,FR,PT}` en el `.env` de la Pi tapan el
    default**, igual que la lista en español. Si «wake up MECH» /
    «bonjour MECH» / «bom dia MECH» no funcionan, revisar esas claves.
17e. **Si MECH saluda solo, sin nadie delante**, la cámara confunde algo
    con una cara: subí `GREETING_CONFIRM_SECONDS` (Ajustes → «Confirmar
    cara»). Si lo que hace es REPETIR el saludo a quien sigue ahí, subí
    `GREETING_REARM_SECONDS` (Ajustes → «Visitante nuevo»). Y si NO saluda
    a un visitante nuevo, bajá ese último (o «Confirmar cara», si es que
    tarda). Ojo: si la cámara
    tiene un falso positivo PERMANENTE (un póster, un reflejo), MECH creerá
    que nunca se fue nadie y no volverá a saludar — ahí el problema es la
    cámara, no esto.
17d. **Si MECH no saluda a nadie por cámara, mirá si está DESPIERTO.**
    Desde sep 2026 el saludo por cámara solo va en reposo
    (`GREETING_ONLY_DORMANT`). El panel lo dice una vez por minuto («No
    saludo…»). El botón «SALUDAR AHORA» respeta la MISMA regla (solo se
    salta el cooldown): para probarlo despierto hay que apagarla en Ajustes.
    Si el brazo saluda hacia ATRÁS, es `ARM_INVERT_R` (Ajustes → «Sentido
    brazos»), no un bug.
17c. **Si el traductor traduce la PREGUNTA de MECH** («¿Qué quieres que
    traduzca?»), es el eco del parlante en el único hueco que queda abierto:
    subí `TRANSLATOR_DRAIN_SECONDS` (el Bluetooth tiene buffer propio) y/o
    el "Umbral ruido" de Ajustes. La guarda de texto
    (`translator.looks_like_own_echo`) solo pilla el eco que se transcribe
    parecido a lo que dijo; si el parlante lo deforma mucho, no lo salva.
    El bucle infinito de la primera versión ya no puede pasar: el modo va
    por turnos y el micrófono no se abre justo después de que MECH hable.
17b. **Frases nuevas: cuidado con las colisiones entre idiomas.** El matcher
    tolera 1 letra de error en palabras de 4+ letras y hace substring en las
    cortas. Ya pasó con «desperta» (pt) vs «despierta» (es), «olá» vs «hola»
    y «dors» (fr) vs «dos». Antes de añadir una frase, probarla contra las
    listas de los otros tres idiomas.
18. **Si MECH se corta solo a media narración**, es el eco de su parlante
    disparando la frase de interrupción: subí el "Umbral ruido" en Ajustes o
    apagá "Interrumpir" (`VOICE_INTERRUPT_ENABLED=false`). Y si NO se deja
    interrumpir, revisá que el `.env` de la Pi no tenga
    `VOICE_INTERRUPT_PHRASES` con otra lista.
19. **Si «mira hacia afuera» solo produce `ACK:ARM` y ningún `ACK:MOVE`, la
    Pi está corriendo el CÓDIGO VIEJO.** Sin el intercept de
    `handle_movement_command`, la frase se la come Claude como un plan
    `mode="movement"` → gesto `wave` → solo comandos `ARM`. Se verifica en el
    arranque del server: si NO sale la línea `Movilidad v4 (sep 2026): ...`,
    hicieron `git pull` pero no reiniciaron. Ver `MOVILIDAD_VERSION` en
    server.py — **súbela cuando cambies algo de movimiento**.
    Además, cada tramo de la maniobra loguea `Ruedas: MOVE:x:y:z durante N s`
    en el panel, y avisa con `warn` si un tramo quedó en 0 s.
20. **Si las ruedas "no se mueven", sospecha de `MODE:LISTEN` ANTES que del
    código de movimiento.** En el firmware ese comando llama a
    `stopAllMotors()`. Comprobación rápida: `MOVE:0:0:100` desde el panel
    (vista Arduino → comando crudo) con el bucle de voz APAGADO. Si ahí se
    mueve y con el bucle encendido no, es esto. Ver la sección del giro.
20b. **Si AVANZAR va hacia atrás, es `DRIVE_INVERT_FORWARD`** (Ajustes →
    «Adelante/atrás invertido»), no un bug de maniobras: se aplica en
    `arduino_link.move()` a TODO. El comando crudo no la usa, así que
    `MOVE:100:0:0` a mano puede ir al revés que el botón AVANZAR.
21. **Velocidad ≠ potencia.** El firmware escala `v * 255 / 100`: velocidad
    50 son 127/255 de PWM, y con estos motores + L298N eso normalmente solo
    zumba. Para probar movimiento SIEMPRE usa 100.
22. **El giro de 180° no tiene encoders: se mide por TIEMPO.** Si MECH se
    queda a 90° o se pasa, NO es un bug — hay que calibrar `TURN_180_SECONDS`
    en Ajustes (en vivo). Cambiar de batería, de suelo o de ruedas obliga a
    recalibrarlo. Si el giro sale al revés (gira hacia el lado equivocado),
    voltear el signo de `w` en `driveOmni()` del .ino, no en `maneuvers.py`.
22b. **Si «regresa a proyectar» dice «ya estoy en posición» y no gira**,
    MECH cree que ya mira a la proyección. Desde el 26 sep, girarlo a mano
    desde el panel lo pone en "no sé" y entonces sí obedece; si aun así pasa,
    es que lo movieron sin el panel (a mano de verdad) o tras un paro de
    emergencia (`assume_projection`). ⚠️ En `handle_movement_command` el
    GIRO se comprueba ANTES que avanzar/retroceder: «go BACK to projecting»
    casaba con «go back» y MECH retrocedía. No cambies ese orden.
23. **`VOICE_OUTWARD_PHRASES` / `VOICE_PROJECT_PHRASES` en el `.env` de la Pi
    tapan el default**, igual que las de wake/sleep/interrupt.
24. **El slot `marketing` NO va al system prompt, y es a propósito.**
    `system_prompt_section()` filtra los `promo`. Si lo metés, Claude lo
    tratará como una obra: narrará encima de los videos y se perderá el audio
    original. Se dispara solo por la orden directa.
25. **Si «proyecta marketing» termina al instante, NO es el backend: son
    los archivos.** El navegador salta los que no puede decodificar (H.265 es
    el caso típico) y la playlist acaba en milisegundos. Mirá el panel: ahora
    nombra los archivos que fallaron. Prevención: `python -m backend.preflight`.
26. **Si el video de marketing se ve pero no se oye**, es la política de
    autoplay del navegador, no el código: abrí Chromium con
    `--autoplay-policy=no-user-gesture-required`, o tocá la pantalla cuando
    salga el aviso. Los mp4 también tienen que traer pista de audio (al
    convertir con ffmpeg, NO uses `-an`).
26. **El visor VR no lleva su propio reloj: se engancha al de `/projector`.**
    Si el video de la VR vuelve a salir descuadrado, mirá que `/projector`
    esté abierto (es quien reporta la posición) y que `state["playback"]`
    tenga datos. Sin reporte, el visor simplemente reproduce desde el
    principio — no se rompe, solo pierde la sincronía.
27. **cv2/mediapipe son opcionales**: `vision.py` los importa perezosamente; si faltan, `start()` loguea el aviso y el server sigue. No mover esos imports al nivel de módulo.
27b. **En la trivia, entender mal una respuesta NO da un error: da un
    resultado FALSO.** El visitante dice «la A», MECH apunta la C y le dice
    que falló. Por eso `parse_answer()` prefiere devolver None (y volver a
    preguntar) antes que adivinar, y por eso `scripts/probar_trivia.py` mide
    las dos caras. Si aflojás el matcher para pillar un caso, corré ese
    script.
27f. **Si el marketing se VE pero NO SUENA**, es el permiso de sonido del
    navegador, no el código ni el parlante. Sale «Toca la pantalla para
    activar el sonido» y el panel lo dice («OJO: la proyección se abrió SIN
    permiso de sonido»). Un clic en la proyección lo arregla al momento; en
    la Pi, volver a abrir «Proyectar MECH» y dar Enter. ⚠️ **Chromium es UN
    solo programa**: el flag de autoplay de «Proyectar MECH» no sirve de
    nada si ya había un Chromium abierto sin él. Ver «Modo MÚSICA —
    QUITADO».
27c. **Si la trivia no arranca**, mirá el arranque del server: tiene que
    salir la línea «Trivia: 3 preguntas por partida…». Si no sale, la Pi
    corre código viejo (git pull sin reiniciar) o está apagada en Ajustes.
    Y si MECH ofrece jugar pero no entiende el «sí», revisá
    `VOICE_YES_PHRASES` en el `.env` de la Pi (tapa el default, como todas).
28. **El .exe de Windows se construye en un venv aparte.** Desde el Python de
    diario, PyInstaller mete lo que encuentre (numpy, opencv...) y el .exe
    pasa de 10 MB a cientos. Por eso `mech_panel.py` no usa nada fuera de la
    librería estándar: es lo que hace que eso se pueda garantizar.
29. **El Python de la Microsoft Store virtualiza `%APPDATA%`.** Correr
    `python windows\mech_panel.py` con ese intérprete guarda la dirección en
    `...LocalCache\Roaming\MECH\` y el .exe la busca en la real. No rompe
    nada (cada uno es coherente), pero explica que "se olvide" la dirección
    al pasar del script al .exe.

---

## Estética del panel (oct 2026)

El equipo pidió cambiar el aspecto del panel **sin tocar los controles**: «que
el fondo no sea ese color violeta, algo más chiva». Se rehízo
`frontend/styles.css` entera con la skill de diseño que instaló el equipo
(`emil-design-eng`); el HTML y el JS no cambiaron salvo colores sueltos.

> ⚠️ **El 8 oct 2026 se volvió a rehacer** (pedido: «moderno y avanzado, con
> buen contraste, que parezca una app hecha para el usuario»). Lo de esta
> lista sigue valiendo salvo donde se indica; lo nuevo está en «Rediseño "de
> app"», más abajo.

- **Fondo oscuro y NEUTRO**, nada de tintes violeta. Desde el 8 oct:
  `--bg: #0a0c10` y cuatro escalones que se distinguen a simple vista
  (`--surface` → `--surface4`), con borde SÓLIDO (`--border: #252d37`; antes
  era un blanco al 7 % que casi no se veía). Ya no hay rejilla de puntos.
- **Un solo acento, cian** (`--accent`, hoy `#22d3ee`), para lo que es "MECH"
  o la acción principal. Sustituye al morado. Los nombres viejos
  (`--purple-mid`, `.btn-purple`) siguen existiendo como alias porque los
  usan estilos en línea del HTML: **no significan morado**.
- **Los demás colores significan algo** y no se usan de adorno: rojo = paro
  de emergencia, error (y la marca: el aro del logo) · verde = bien, «puedes
  hablar» · ámbar = trabajando, Arduino, aviso · cian = MECH. ⚠️ El
  micrófono **ya no es rojo fijo**: desde el 8 oct toma el color de la fase.
- `library.html` hereda la misma paleta. **No se tocaron** la proyección, la
  trivia (va en morado a propósito: es el estilo Kahoot que pidió el equipo)
  ni la app de Windows (`windows/mech_panel.py` tiene sus propios colores y
  habría que reconstruir el .exe).

Tres reglas de movimiento que salen de esa skill — **no las rompas al añadir
un control**:

1. Solo se animan `transform` y `opacity`. (El halo del paro de emergencia
   animaba el `box-shadow`: obligaba a repintar el botón en cada fotograma
   mientras el panel estaba abierto. Ahora es una capa aparte.)
2. Los `:hover` van TODOS juntos al final, dentro de
   `@media (hover: hover) and (pointer: fine)`: en el teléfono el hover se
   queda pegado tras el toque.
3. Nada de `transition: all`; todo lo que se pulsa responde con
   `scale(.97)`; y **lo que se dispara con el TECLADO es inmediato**:
   cambiar de vista con las teclas 1/2/3 no se anima. Con el ratón sí (desde
   el 6 oct, ver abajo): `UI.showView(nombre, navEl)` solo recibe `navEl`
   cuando se pulsa el menú, y de eso depende que haya animación.

### Rediseño «de app» (8 oct 2026)

Pedido del equipo: «que se vea moderno y avanzado con un buen contraste de
colores, que parezca una app realmente hecha para el usuario». Se les
preguntó el tema y eligieron **oscuro con más contraste** (no claro, no los
dos). Mismos controles y mismos `id`; `styles.css` reescrita entera y el HTML
reordenado.

- **Armazón de app**: `.app` mide la ventana justa (`100dvh`) y NO se
  desplaza; la cabecera, la barra de fase, el menú y el panel derecho se
  quedan quietos y solo se desplaza `.view`. ⚠️ Va en `.app`, no en `body`:
  `library.html` comparte la hoja y su página sí tiene que bajar. En el
  teléfono (≤ 700 px) vuelve a desplazarse la página entera.
- **Contraste**: texto secundario `--text-muted` a 7,9:1 sobre una tarjeta
  (antes ~4:1) y casi todo en **Sora a 13-14 px**. Space Mono queda solo
  para datos (valores de los deslizadores, comandos, registro). Si añades
  un texto de ayuda, usa `.note`; un título de tarjeta, `.card-title`
  (`.tone-green` / `.tone-amber`); un rótulo pequeño, `.kicker`. **No
  vuelvas a escribir estilos en línea** para eso (se quitaron ~20).
- **Botones**: teñidos por defecto (`.btn-purple`, `.btn-green`…) y
  **rellenos** con `.btn-solid`, que es para LA acción principal de su
  tarjeta (Enviar, Guardar y aplicar, Probar voz). No lo pongas en todos.
- **Vista Voz en tarjetas**: `.voice-top` (micrófono `.voice-hero` +
  conversación `.voice-talk`), `.voice-tools` (trivia + traductor) y
  `.voice-quick` (comandos rápidos). Se parten en dos columnas con una
  **container query** sobre `.content` (`@container contenido (min-width:
  760px)`): depende del ancho que queda de verdad, haya o no panel derecho.
- **El micrófono cambia de color con la fase**: `updateVoicePhase()` pone
  `document.body.dataset.phase` y el CSS define `--orb` por fase (gris
  apagado · azul grisáceo reposo · verde «puedes hablar» · cian grabando y
  hablando · ámbar pensando). El icono de dentro y el de la barra también
  cambian (`PHASES[...].icon`).
- **Sin emojis**: las fases y los botones del Arduino usan iconos de la
  fuente local. En la Pi los emojis pueden salir como cuadritos (no trae
  fuente de emojis), igual que pasaba con el coreano. ⚠️ **No hay icono de
  flecha hacia abajo** en el subconjunto local: se usa
  `<i class="ti ti-arrow-up ti-down">` (`.ti-down` lo gira 180°). No se
  añadió ningún icono nuevo, así que `mech-icons.css` no cambió.
- **Deslizadores rellenos** hasta la perilla: el navegador no lo hace solo;
  `pintarRango()` pone `--p` en cada `<input type="range">` (al cargar, al
  moverlo y en `setSlider()`). Si creas un deslizador por código, llámala.
- **Ajustes en grupos**: la tarjeta de ~40 filas lleva rótulos `.set-group`
  (Micrófono y escucha · Voz, interrupción y subtítulos · Brazos y gestos ·
  Saludo por cámara).
- **Menú lateral**: sección «Abrir» con **Biblioteca** (`/library`) y
  **Proyección** (`/projector`), en ventana aparte, y al pie **«Atajos y
  frases»** (un desplegable de `Menus`). Los atajos ya no ocupan un tercio
  del panel derecho, que queda para Conversación y Registro.
- **Aviso de conexión perdida**: `.net-toast`, visible con
  `body.sin-servidor` (lo ponen `ws.onclose` / `ws.onopen`). Con `?app=1` en
  la dirección (así lo abre la app de Windows) trae «Buscar de nuevo», que
  hace `history.back()` a la pantalla de búsqueda.
- `index.html` pide ahora `styles.css?v=13` y `app.js?v=13` (y `sismos.js?v=13`).

### App de Windows sin construir nada (8 oct 2026)

Pedido: «que el panel también funcione como una app que pueda correr
abriéndolo en mi computadora». Se le preguntó qué quería decir y eligió **un
icono que abre el panel** (no un modo demostración sin robot, no MECH entero
en la PC). `MECH Panel.exe` ya hacía eso, pero **en la laptop del equipo no
está construido ni se puede** (no hay Python instalable a mano).

- **`windows/Instalar MECH.bat`** → `instalar_app.ps1`: copia
  `windows/app/` + `mech.ico` a `%APPDATA%\MECH\app` y crea el acceso
  directo **MECH** (Escritorio y menú Inicio) a Edge/Chrome con
  `--app="file:///…/index.html"`, perfil propio y el flag de autoplay.
  `Quitar MECH.bat` lo deshace. Parámetros `-Destino`, `-Escritorio` y
  `-SinMenuInicio` para probarlo sin tocar el equipo.
- **`windows/app/index.html`** es la pantalla que busca al robot (un solo
  archivo, sin nada externo): última dirección + `mech.local` / `mech`; si
  no, barre la red de la última vez; si no, pantalla de ayuda con campo
  manual y reintento cada 4 s. Al encontrarlo navega a
  `http://<robot>:8000/?app=1`.
- ⚠️ **El panel se sigue cargando DESDE EL ROBOT, a propósito.** Una copia
  local del panel se desincronizaría del backend en cuanto alguien
  actualizara solo uno de los dos. No lo cambies por «que abra aunque el
  robot esté apagado»: para eso está la pantalla de búsqueda.
- Cómo comprueba que es MECH sin poder leer la respuesta (CORS): `fetch`
  con `mode: 'no-cors'` (¿contestó alguien?) + cargar `/static/icon.svg`
  como imagen (¿es MECH?). **No hizo falta tocar el backend** ni abrir CORS.
- ⚠️ No barre la red actual a ciegas: una página no puede saber la IP de la
  laptop. El botón «Buscar en redes habituales» prueba las típicas; es
  manual a propósito (son ~1800 conexiones: no para lanzarlas solas en la
  red de un colegio).
- ⚠️ `.ps1` y `.bat` van **sin tildes**: PowerShell 5 lee los `.ps1` sin BOM
  como ANSI.
- Si cambia `windows/app/index.html`, hay que volver a correr el instalador
  en cada laptop (se usa la copia de `%APPDATA%`).
- `mech_panel.py` y lo del `.exe` no se tocaron (siguen con su paleta
  vieja).

### Menús animados y los diez idiomas en uno (6 oct 2026)

Pedido del equipo: el panel «se ve muy saturado por los 10 idiomas» y «más
animaciones en los menús». Mismos controles y mismos `id`; cambió cómo se
presentan.

- **Idioma**: los diez chips en fila y su pista de cinco líneas son ahora UN
  botón (`#lang-btn`) con el idioma activo, que abre un menú de dos columnas
  (nombre, nombre nativo y frase que lo despierta). Al lado queda una sola
  línea con las dos frases del idioma ACTIVO (despertar y cortar). Las
  opciones las pinta `pintarMenuIdiomas()` desde la tabla `LANGS` de
  `app.js` y conservan los `id` `lang-es`, `lang-en`…: **`LANGS` es la única
  lista de idiomas del panel** (antes estaban repetidos en el HTML).
- **Desplegables**: `mejorarSelect()` convierte cada `<select>` en un menú
  propio. ⚠️ El `<select>` **sigue en la página, escondido, y es quien guarda
  el valor**: todo el código que hace `$('tr-src').value` funciona igual. El
  botón se entera de los cambios por tres vías — el evento `change`, un
  envoltorio de la propiedad `value` (asignarla por código no avisa con
  ningún evento) y un `MutationObserver` (la lista de micrófonos se rehace).
  Los que solo tienen idiomas se pintan en dos columnas. **En pantallas
  táctiles no se convierten** (`pointer: fine`): el selector nativo del
  teléfono es mejor.
- **`Menus`** (en `app.js`) es el único controlador: un menú abierto a la
  vez; el desplegable cuelga de `<body>` con `position: fixed` (así no lo
  recorta ninguna tarjeta con `overflow`), se abre hacia ARRIBA si abajo no
  cabe, y se cierra con Escape, al pulsar fuera, al hacer scroll o al cambiar
  de vista. Flechas/Inicio/Fin mueven el foco. ⚠️ La barra espaciadora sigue
  siendo el PARO DE EMERGENCIA también con un menú abierto: no la uses para
  elegir.
- **Menú lateral**: el resaltado es una sola pieza (`.nav-glider`) que se
  desliza de un botón a otro (`moverGlider()`); solo en pantallas de más de
  700 px. Los botones entran en cascada al cargar.
- **Cambio de vista con el ratón**: `.view.entra` hace entrar las tarjetas en
  cascada (300 ms). Las burbujas del chat salen de la esquina de quien habla.
- ⚠️ Las animaciones que corren una vez usan `backwards`, **no `both`**: con
  `both` el `transform` final se queda puesto y tapa el `scale(.97)` del
  `:active`.
- **El chat ya no repite la misma burbuja.** El backend manda el estado
  entero en CADA cambio de fase, con la última frase dentro, y el panel la
  volvía a pintar cada vez. Ahora solo si es otra (`state.ultimoTranscript` /
  `state.ultimaRespuesta`); los eventos `transcript` / `ai_response` siguen
  pintando siempre.
- **Micrófono en Ajustes**: si lo configurado es un trozo del nombre
  (`AUDIO_INPUT_DEVICE=Steren`) no coincidía con ninguna opción, el
  desplegable quedaba en blanco y «Guardar en .env» **borraba el micrófono**.
  Ahora se añade como opción («Steren (lo configurado ahora)»).
- **`?v=N` en `index.html`** (en `styles.css` y `app.js`; hoy `?v=13`): para
  que tras un `git pull` el navegador no mezcle el HTML nuevo con el CSS/JS
  viejos que tenía guardados. **Al tocar cualquiera de los dos, súbele el
  número.**
- Iconos: no se añadió ninguno (la flecha y la palomita de los menús están
  dibujadas con bordes de CSS), así que no hubo que regenerar
  `mech-icons.css`.

Para verlo sin la Pi (en la laptop no hay FastAPI): hace falta un servidor
estático que sirva `frontend/` con las rutas del server real (`/static/…`).
La vista previa de Claude Code lo tiene como `panel-estatico` en
`.claude/launch.json` (apunta a un script del scratchpad de la sesión: si ya
no existe, hay que rehacerlo — el del 6 oct eran 250 líneas de `http.server`
con un WebSocket de verdad y un `POST /__push` para simular eventos del
robot). ⚠️ Con el panel de vista previa escondido, las capturas salen
atrasadas: esperar 1-2 s antes de cada una, y fiarse más de medir con
JavaScript que de la imagen.

---

## Cómo trabajar con este usuario

- **Todo valor de movimiento va como CONFIGURACIÓN, nunca hardcodeado**
  (pedido explícito del equipo, sep 2026). Cuando pidan "que avance diez
  segundos", "que gire 4.8", "que agite el brazo dos veces": clave en
  `config.py` con default sensato, entrada en `_LIVE_KEYS` y en `/api/config`
  de `server.py`, y un slider en la vista Ajustes del panel. Así se recalibra
  EN EL EVENTO, en vivo, sin tocar código ni reiniciar — que es lo único que
  sirve cuando el suelo, la batería o las ruedas cambian.
  Y si la orden admite un número hablado ("avanza CINCO segundos"), ese número
  manda sobre el default: ver `voice_phrases.extract_seconds()`.

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
