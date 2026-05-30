# MECH
Proyecto de WRO 2026 (Robots and Culture) enfocado en inmersiones y experiencias involucrando ingeniería y firmware. Encargados de la construcción de ART (A Real Immersion). Somos Multisensory Engineering Cyberphysical Humanized, somos MECH.

## Estructura del proyecto

```
backend/                  Python — corre en Raspberry Pi 5
  server.py               Servidor FastAPI + WebSocket (entry point principal)
  main.py                 Modo standalone sin servidor (testing)
  mech_app.py             Estado compartido + event bus
  stt.py                  Speech-to-Text local (faster-whisper)
  llm.py                  Claude API (Opus 4.7) — devuelve plan estructurado
  tts.py                  ElevenLabs (voz)
  image_gen.py            NanoBanana / Gemini 2.5 Flash Image (fallback de visual)
  arduino_link.py         Serial al Arduino
  gestures.py             Mapea gestos abstractos → comandos del Arduino
  projector.py            Visor tkinter alternativo (modo standalone)
  video_library.py        Manifest de videos pre-renderizados (Opción B)
  video_library/          Los .mp4 por obra (gitignored): <slug>/seg01.mp4...
  config.py               Lee .env
  requirements.txt
  .env.example

frontend/                 Panel de control web para supervisión con caracter de emergencia (servido por backend/server.py)
  index.html              Panel principal
  app.js                  Lógica (WebSocket + REST)
  styles.css
  projector.html          Página fullscreen para el proyector
  library.html            UI para subir videos pre-renderizados (/library)
  manifest.json           PWA — instalable como app
  sw.js                   Service worker
  icon.svg

arduino/                  Control de sistemas móviles: movilidad terrestre y de servomotores (brazos y cabeza)
  mech_controller/
    mech_controller.ino   Firmware: motores omni, servos

windows/                  Operación desde Windows
  MECH Control.bat        Doble click → abre panel en Edge --app
  MECH Kiosko.bat         Doble click → pantalla completa kiosko
  MECH Proyector.bat      Doble click → página de proyector kiosko
  config.txt              URL del servidor (editar con la IP de la Pi)
  README.md               Guía detallada

docs/
  GUIA.md                 Guía de montaje y hardware
  FRONTEND.md             Guía del servidor + panel + control desde Windows
```

## Inicio rápido

Lee [`docs/GUIA.md`](docs/GUIA.md) (hardware) y [`docs/FRONTEND.md`](docs/FRONTEND.md) (servidor + panel). Resumen:

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
   chromium-browser --kiosk http://localhost:8000/projector
   ```
6. Desde Windows: edita `windows/config.txt` con la IP de la Pi y doble click en `windows/MECH Control.bat`.

