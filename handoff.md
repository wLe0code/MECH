# HANDOFF — MECH

Documento de traspaso entre sesiones de Claude Code. **Léelo completo** antes
de tocar nada.

> ✅ **ACTUALIZACIÓN (2 jul 2026): el sitio web ya se construyó.** Vive en
> `web/` (ver `web/README.md`). Es un one-page estático (HTML/CSS/JS, sin
> build) con: hero con typing "ok MECH" + aro LED CSS, qué es M.E.C.H,
> problemática, **showcase con scroll estilo Apple** (4 tomas del robot),
> pipeline, hardware por capas, 5 obras, bitácora de construcción con fotos
> extraídas de `MECH.pdf`, impacto + BMC, equipo y footer. Detalle importante:
> el showcase busca `web/assets/robot-01.jpg` y `robot-02.jpg` (fotos del
> robot terminado que el usuario tiene en su teléfono); mientras no existan,
> muestra un render SVG de respaldo. Falta que el usuario copie esas 2 fotos.
> Hosting sugerido: GitHub Pages (instrucciones en `web/README.md`).
>
> **Nombre del robot: PHOTON** (la empresa sigue siendo MECH). La web ya lo
> usa; el backend aún despierta con "ok MECH" — el cambio de wake word a
> "ok photon" quedó como pendiente en CLAUDE.md (el usuario aceptó el riesgo
> de colisión "foto"/"botón" con la tolerancia lev≤1 del matcher).

Esta sesión anterior (la que escribió el handoff original) hizo
cambios de código en el backend/firmware.

> Contexto de fondo del repo: leer **CLAUDE.md** en la raíz. Es la fuente de
> verdad de arquitectura, hardware y decisiones. Este handoff NO lo reemplaza,
> lo complementa con el estado *vivo* de ahora mismo.

---

## 1. Objetivo

### Objetivo del proyecto (MECH)
Robot interactivo para la **WRO 2026 — Robots and Culture**. En un stand,
narra obras culturales (Don Quijote, Campaña Nacional de 1856, Jiménez
Deredia, Malpaís, Isidro Con Wong…) con **voz + proyección + movimiento
físico**, reaccionando a usuarios que se acercan y le hablan. Cerebro: Claude
devuelve un Plan estructurado; Python lo ejecuta (STT local, TTS ElevenLabs,
imágenes Gemini o videos pre-renderizados, Arduino para motores/servos/LEDs).

### Objetivo de la PRÓXIMA sesión (web del proyecto)
Crear un **sitio web de presentación de MECH** (para mostrar el proyecto:
qué es, cómo funciona, hardware, equipo, demo, etc.). Es un entregable
**nuevo y separado** del código del robot. Puntos a decidir con el usuario
al arrancar:
- ¿Sitio estático (HTML/CSS/JS) o framework (Astro, Next, Vite)? El usuario
  **no es programador profesional**; prefiere cosas simples y revisables.
  Recomendación: empezar estático o Astro, sin build pesado.
- ¿Dónde se hospeda? (GitHub Pages es lo natural dado que el repo ya está en
  `github.com/wLe0code/MECH`).
- ¿Idioma? Todo el proyecto es en **español** — la web también.
- ¿Dónde vive en el repo? Sugerencia: carpeta nueva `web/` o `site/` en la
  raíz, para NO mezclarla con `frontend/` (que es el panel de control del
  robot, cosa distinta).

⚠️ **No confundir** `frontend/` (panel de control operativo del robot, ya
existe) con la web de presentación (lo nuevo a construir). Son dos cosas.

---

## 2. Estado actual del repo

- **Rama:** `main`. Limpio, sin cambios sin commitear.
- **Último commit (ya pusheado a `origin/main`):**
  `d3976bf — Voz robusta con ruido, visión de usuarios, aro de LEDs y gestos reales`
- Remoto: `https://github.com/wLe0code/MECH.git`
- Entorno de desarrollo: **Windows 11 + PowerShell** (el robot corre en
  Raspberry Pi 5, pero se edita desde Windows). OneDrive sincroniza el repo
  (ojo con locks de archivos: si un rename/move falla con "Permission
  denied", es OneDrive).
- **No hay tests ni linter** configurados. La validación es manual E2E.
  Para chequear rápido sin hardware: `python -m py_compile <archivos>` y
  `node --check frontend/app.js`.

### Dependencias / imports que NO están instalados en la laptop de dev
(esto es normal, corren en la Pi): `sounddevice`, `webrtcvad`,
`faster_whisper`, `cv2`, `mediapipe`, `serial`. Por eso `stt.py`,
`vision.py`, etc. no se pueden *ejecutar* aquí, solo compilar. Los módulos
que dependen de cámara/mic importan esas libs **de forma perezosa** a
propósito, así el server arranca aunque falten.

---

## 3. Qué se cambió en esta sesión (commit d3976bf)

Todo esto ya está en `main` y pusheado. Contexto por si la web quiere
describir features reales del robot:

1. **Wake word "ok MECH"** — comando principal de despertar (antes era
   "despierta MECH"). Variantes: okay/okey/ok mek/oye mech. Tolerancia a 1
   letra de error en la transcripción.
2. **Detección de voz anti-ruido** — mide el piso de ruido del ambiente y
   solo graba si la voz lo supera; corta la frase cuando la amplitud cae.
   Resuelve que en la olimpiada costaba despertarlo por el ruido.
3. **Aro de LEDs estilo Alexa Echo** — NeoPixel 12 LEDs en el pin A2 del
   Arduino, sincronizado con la fase de voz (barrido al oír "ok MECH", etc.).
4. **Gestos reales** — coreografías por gesto (saludar, señalar, brazos
   arriba…) con movimiento suave, opcionalmente mueve las ruedas.
5. **Visión** — `backend/vision.py` nuevo: detecta usuarios con la cámara
   C930e, estima distancia, saluda, sigue y se acerca; si no hay usuario
   cerca, narra sin proyectar.
6. **Arduino robusto** — autodetección de puerto y reconexión automática.

---

## 4. Archivos relevantes (mapa para la web)

Para la web probablemente quieras **leer** estos, no editarlos:

| Archivo | Para qué te sirve al hacer la web |
|---|---|
| `CLAUDE.md` | Arquitectura completa, hardware, decisiones. Fuente #1 de contenido. |
| `README` (si existe) / `docs/GUIA.md` | Montaje del hardware en la Pi. |
| `docs/FRONTEND.md` | Cómo se opera el panel de control. |
| `docs/PRUEBAS_HARDWARE.md` | Detalle de mic, cámara, LEDs (secciones 5 y 6 nuevas). |
| `frontend/styles.css` | **Paleta de colores y estética** ya definida del panel (morados/teal/ámbar sobre fondo oscuro `#0e0e12`). Reúsala para que la web combine. |
| `frontend/icon.svg` | Ícono/logo de MECH. |
| `backend/video_library.py` | Lista de obras culturales que MECH presenta (buen contenido para la web). |

Código del robot que se tocó esta sesión (referencia, **no** para la web):
`backend/{config,stt,voice_phrases,arduino_link,gestures,vision,mech_app,server}.py`,
`arduino/mech_controller/mech_controller.ino`,
`frontend/{index.html,app.js}`, `backend/.env.example`, `requirements.txt`.

### Estética existente a reutilizar (del panel)
- Fondo oscuro `#0e0e12`, tipografía mono para acentos técnicos.
- Acentos: morado, teal (`--teal`), ámbar, rojo (paro). Ver variables CSS en
  `frontend/styles.css`.
- Estilo "sistema de control / sci-fi sobrio". La web puede seguir esa línea.

---

## 5. Qué funcionó / qué falló / qué falta

### ✅ Funcionó (verificado esta sesión)
- Todo el backend **compila** (`py_compile` OK en los 9 módulos tocados).
- `frontend/app.js` pasa `node --check`.
- Test del matcher de wake word: "Ok, Mech.", "okay mech", "OK Mec",
  "ok mek", "Okey Meche", "oye mech" → despiertan; frases normales no.

### ⚠️ No se pudo probar aquí (falta hardware / Pi)
- Firmware del Arduino: **no hay `arduino-cli`** en esta máquina. El .ino no
  se compiló; hay que flashearlo y probarlo en la Pi/Arduino real.
- Visión, micrófono y TTS reales: necesitan la Pi con cámara/mic enchufados
  y las libs instaladas (`pip install opencv-python-headless mediapipe`).

### 🚧 Pendiente del robot (no bloquea la web)
- Comprar/cablear el aro NeoPixel (o dejar `#define MECH_LEDS 0`).
- Generar y subir los videos pre-renderizados de cada obra.
- Cablear y probar el Arduino Uno (2× L298N + servos).
- Calibrar visión (`VISION_MIN_DISTANCE`, `FACE_WIDTH_M`) en la Pi.
- Ajustar el slider "Umbral ruido" en el lugar del evento.

---

## 6. Cómo trabajar (recordatorios para la próxima sesión)

- **Usuario:** estudiante, **no** programador pro, se comunica en **español**.
  Explicaciones en español, paso a paso, cambios chicos y revisables.
  Confirmar alcance antes de tocar muchos archivos.
- **Git:** el usuario pidió trabajar en `main` directamente (no crear branch)
  y hace `git push` cuando lo dice explícitamente. No pushear sin que lo pida.
- **Commits en español**, siguiendo el estilo del historial.
- **Windows/PowerShell** para comandos; hay también Bash disponible.
- Actualiza este `handoff.md` y/o `CLAUDE.md` al terminar cambios grandes.

---

## 7. Arranque sugerido para la sesión de la web

1. Leer `CLAUDE.md` (arquitectura/contenido) y `frontend/styles.css` (estética).
2. Preguntar al usuario: stack (estático vs Astro), hosting (GitHub Pages?),
   y confirmar carpeta destino (`web/` propuesta).
3. Estructurar contenido: Hero (qué es MECH) → Cómo funciona (el flujo
   voz→Claude→proyección→movimiento) → Hardware → Obras culturales → Equipo →
   Demo/Contacto.
4. Reusar paleta y logo existentes para coherencia visual.
