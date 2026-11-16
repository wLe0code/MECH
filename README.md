# MECH
Proyecto de WRO 2026 | Futuros Innovadores (Robots and Culture) enfocado en inmersiones y experiencias involucrando ingeniería y firmware. Encargados de la construcción de MECH. Somos Multisensory Engineering Cyberphysical Humanized, y si es inmersivo, es MECH.

## Estructura del proyecto

```
backend/                  Python — corre en la Raspberry Pi 5
  server.py               Servidor FastAPI + WebSocket + bucle de voz (el ÚNICO punto de entrada)
  mech_app.py             Estado compartido + event bus (narrar, trivia, traductor, saludo…)
  stt.py                  Speech-to-Text local (faster-whisper)
  llm.py                  Claude API — devuelve un plan estructurado
  tts.py                  ElevenLabs (voz)
  lang.py                 Los diez idiomas (el despertar decide cuál)
  image_gen.py            Gemini (respaldo cuando una obra no tiene videos)
  video_library.py        Biblioteca de videos pre-renderizados
  arduino_link.py         Serial al Arduino
  gestures.py, maneuvers.py  Brazos y movimiento (saludo, giro de 180°…)
  vision.py               Cámara: detectar visitantes
  sismos.py               Sismos recientes para el panel
  preflight.py            Chequeo antes del evento
  config.py               Lee .env
  requirements.txt, .env.example

frontend/                 Panel de control web (servido por backend/server.py)
  index.html, app.js, styles.css   Panel
  projector.html          Página de proyección (Chromium kiosko)
  cardboard.html          Proyección estéreo para Google Cardboard (/projector/vr)
  library.html            Subir los videos de cada obra (/library)
  vendor/                 Iconos, fuentes y mapa en local (sin internet)

arduino/mech_controller/  Firmware del Arduino Uno: ruedas mecanum y servos de los brazos
pi/                       Iconos de escritorio de la Pi (Iniciar / Proyectar / Apagar MECH)
windows/                  App «MECH» para la laptop (Instalar MECH.bat)
scripts/                  Pruebas sin hardware y generadores de iconos/fuentes/mapa
web/                      Sitio de presentación (Vercel)
branding/                 Logo, diagramas y material del stand
docs/
  USO.md                  Guía del operador del stand (qué decirle, qué tocar)
  GUIA.md                 Guía de montaje y hardware
  FRONTEND.md             Servidor + panel + control desde Windows
```

## Inicio rápido

Para **usar** MECH en el stand: [`docs/USO.md`](docs/USO.md) — qué decirle y qué hace cada botón.

Para **montarlo**: [`docs/GUIA.md`](docs/GUIA.md) (hardware) y [`docs/FRONTEND.md`](docs/FRONTEND.md) (servidor + panel). Resumen:

1. Cablea el hardware según `docs/GUIA.md` §1.
2. Sube `arduino/mech_controller/mech_controller.ino` al Arduino.
3. En la Raspberry Pi 5:
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r backend/requirements.txt
   cp backend/.env.example backend/.env   # rellena tus API keys
   ```
4. Lanza el servidor (todo en uno):
   ```bash
   python -m backend.server
   ```
5. En la misma Pi, abre el proyector en kiosko:
   ```bash
   chromium --kiosk --autoplay-policy=no-user-gesture-required http://localhost:8000/projector
   ```
6. Desde Windows: doble clic una vez en `windows/Instalar MECH.bat` y abre el icono «MECH» del Escritorio (busca al robot solo).

