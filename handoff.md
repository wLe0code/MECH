# HANDOFF — MECH

Documento de traspaso entre sesiones de Claude Code. **Léelo completo** antes
de tocar nada. Contexto de fondo (arquitectura/hardware/decisiones): **CLAUDE.md**
en la raíz — este handoff no lo reemplaza, lo complementa con el estado *vivo*.

> ✅ **Estado (jul 2026):** el **audio funciona en la Pi** (mic Steren → Whisper →
> Claude → voz por el parlante Bluetooth) y el **movimiento ya gira** (Arduino Uno
> + 2× L298N con 4 motores mecanum). La **web de presentación** ya está construida
> en `web/`. Detalles abajo.

---

## 1. Objetivo del proyecto (MECH)

Robot interactivo para la **WRO 2026 — Robots and Culture**. En un stand, narra
obras culturales (Don Quijote, Campaña de 1856, Jiménez Deredia, Malpaís, Isidro
Con Wong…) con **voz + proyección + movimiento físico**, reaccionando a usuarios
que se acercan y le hablan. Claude devuelve un Plan estructurado; Python lo
ejecuta (STT local, TTS ElevenLabs, videos pre-renderizados o imágenes Gemini,
Arduino para motores/servos).

---

## 2. Estado actual del repo

- **Rama:** `main`. Último commit pusheado: `12c59eb` (cableado §1.3 más claro).
- Remoto: `https://github.com/wLe0code/MECH.git`
- Dev en **Windows 11** (OneDrive sincroniza el repo); el robot corre en
  **Raspberry Pi 5**. El usuario flashea el Arduino desde el laptop (Arduino IDE).
- **No hay tests ni linter.** Validación manual E2E. Chequeo rápido sin hardware:
  `python -c "import ast; ast.parse(open('archivo', encoding='utf-8').read())"`.
- Ojo: `windows/config.txt` tiene la URL local del usuario (ej. `http://mech:8000`)
  — es cambio local suyo, **no** lo commitees.

---

## 3. Cambios de esta sesión (audio + hardware/movimiento)

Todo pusheado a `main`. **Nota de git:** el usuario tenía trabajo propio en
staging (voces, panel de ajustes, resample STT); se commiteó cada cambio de
Claude **por archivo** (pathspec) para no pisarlo.

### 🎤🔊 Audio — YA FUNCIONA en la Pi
- **Mic = Steren MIC-9010** (receptor USB inalámbrico). La **C930e queda SOLO
  para video**. Se elige con `AUDIO_INPUT_DEVICE` en `.env` (`stt.py` lo usa).
- **STT:** captura a **48000 Hz** (el Steren no abre a 16k) y **resamplea a 16000**
  antes de Whisper (Whisper no resamplea solo → si no, alucina). `initial_prompt`
  breve para reconocer el nombre **"MECH"**.
- **TTS por PipeWire:** `tts.py` reproduce con **pw-play/paplay** (no sounddevice,
  que apunta al HDMI) para que la voz salga por el **parlante Bluetooth (JBL)**.
  Se antepone un **silencio inicial** (`AUDIO_LEAD_SILENCE`, ~0.7–1.0s) porque el
  BT tarda en "despertar" y se come las primeras palabras.
- **Voces dinámicas por personaje** (`backend/voices.py`; `tts.speak(voice_id=…)`).
- **Server arranca sin `PYTHONPATH`** (se añadió `sys.path.insert` en `server.py`
  y `main.py`). **Proyección de video** funciona (los videos van **muteados** a
  propósito; el audio lo pone el TTS).

### 🔌 Movimiento — Arduino Uno (el RoboKit se descartó)
- **Microcontrolador definitivo: Arduino Uno R3** + **2× L298N** (4 motores DC
  mecanum) + **2 servos MG996R** (brazos; **sin cabeza**).
- **RoboKit RS de Roborobo DESCARTADO** tras explorarlo a fondo: corre programas
  cerrados de **Rogic**, **no recibe serial en vivo**, solo se controla por su
  dongle/Bluetooth propietario. Existe `backend/robokit_link.py` (método de "bus
  de pines GPIO" que se probó) pero **se abandonó** en favor del Arduino. Los
  bloques de Rogic **sí** leen pines pero **no** hay bloque de "recibir serial".
- **Firmware `mech_controller.ino` reescrito para el Uno.** Mapa de pines final:
  - **Servos:** brazo izq = **9**, brazo der = **10** (Timer1 bloquea PWM en 9/10).
  - **L298N #1** (M1=FL, M2=FR): ENA **3**, IN1 **4**, IN2 **2**, IN3 **7**, IN4 **8**, ENB **5**.
  - **L298N #2** (M3=BL, M4=BR): ENA **6**, IN1 **12**, IN2 **13**, IN3 **A0**, IN4 **A1**, ENB **11**.
  - `HEAD` = **no-op** (sin cabeza física). `MOVE`/`ARM`/`MODE`/`STOP` funcionan.
  - **Giro con SOLO 2 ruedas en diagonal (FL+BR)**, por pedido del equipo (el `w`
    solo afecta esas 2; adelante/atrás/lateral usan las 4).
- **Probado:** los motores giran; adelante/atrás/lateral OK. Se sube con
  `arduino:avr:uno`; probar por Serial Monitor (115200, Newline) → `READY:MECH`,
  `ACK:MOVE`, etc.
- **Cableado** documentado claro en `docs/GUIA.md §1.3` (3 fuentes independientes,
  tierra común, jumpers **ENA/ENB QUITADOS**, jumper de **5V PUESTO**, +5V sin
  conectar). **No** conectar 5V del Arduino al +5V del L298N con el jumper puesto
  (quema). **Batería:** el bloque de 9V **no sirve** (poca corriente aunque tenga
  mAh) → pack ≥7V con buena corriente (o el de 6V, con menos fuerza).

---

## 4. Pendiente

- **Copiar fotos reales del robot** a `web/assets/robot-01.jpg` y `robot-02.jpg`
  (mientras no existan, la web usa un render SVG).
- **Cablear y probar los 2 servos MG996R** (fuente de 5–6V con varios amperios;
  señal a pines 9/10). Mandar `ARM:L:30`, `ARM:R:120`.
- **Segundo L298N + los otros 2 motores** si aún faltan (probar `MOVE:50:0:0` con 4).
- **Generar y subir los videos pre-renderizados** por obra (UI en `/library`).
- **Probar la visión** en la Pi (`vision.py`; la C930e = solo video).
- **Integrar el movimiento al software** (por ahora `arduino_link.py` habla el
  protocolo; falta conectar voz/cámara → movimiento cuando el usuario lo pida).
- Aro NeoPixel (o `#define MECH_LEDS 0`).

---

## 5. Cómo trabajar (recordatorios)

- **Usuario:** estudiante, **no** programador pro, se comunica en **español**.
  Explicaciones en español, paso a paso, cambios chicos y revisables. Confirmar
  alcance antes de tocar muchos archivos. Cuando algo falla en su consola, pedir
  el mensaje **exacto** antes de adivinar.
- **Hardware:** ir **pieza por pieza** (flashear → Serial Monitor → 1 motor → …),
  no todo de una. Muchos problemas fueron eléctricos (batería débil, tierra
  común, jumpers), no de código.
- **Git:** trabajar en `main`; `git push` solo cuando el usuario lo pida.
  Commitear los cambios de Claude **por archivo** si el usuario tiene trabajo
  propio sin commitear (para no incluirlo por error). Commits en **español**.
  Terminar los mensajes con `Co-Authored-By: Claude Opus 4.8 …`.
- **Actualiza este `handoff.md` y/o `CLAUDE.md`** al terminar cambios grandes.
