# Frontend y servidor de control

Esta guía complementa [`GUIA.md`](GUIA.md) — cubre cómo correr el panel de control web y operar MECH desde Windows.

## Arquitectura

```
            ┌────────────────────────────────────┐
            │  RASPBERRY PI 5                    │
            │                                    │
            │   ┌──────────────────────────┐     │
            │   │ backend/server.py        │     │
            │   │  - FastAPI               │     │
            │   │  - WebSocket /ws         │     │
            │   │  - Bucle de voz          │     │
            │   │  - Sirve frontend        │     │
            │   └─────────┬────────────────┘     │
            │             │ control               │
            │             ▼                       │
            │   Arduino · TTS · Imagen · STT     │
            └──────┬──────────────────┬───────────┘
                   │ HTTP/WS         │ HDMI
                   ▼                  ▼
        ┌──────────────────┐   ┌─────────────────┐
        │  Windows laptop  │   │  Proyector(es)  │
        │  (panel)         │   │  (Chromium en   │
        │                  │   │   modo kiosko   │
        │   Edge --app     │   │   apuntando a   │
        │   o PWA          │   │   /projector)   │
        └──────────────────┘   └─────────────────┘
```

**Dos procesos en la Pi:**
- `backend/server.py` — el principal. FastAPI sirve todo (panel, proyector, REST, WS) y corre el bucle de voz.
- Un Chromium en modo kiosko mostrando `http://localhost:8000/projector` para alimentar el proyector físico.

**En Windows:** un Edge en modo `--app` o PWA apuntando a `http://<IP-pi>:8000`.

## Correr el servidor en la Pi

Sustituye al `python -m backend.main` de la guía original. **No corras ambos a la vez** — pelearían por el Arduino y el micrófono.

```bash
cd ~/MECH
source .venv/bin/activate
pip install -r backend/requirements.txt   # añade fastapi, uvicorn

python -m backend.server
```

Verás:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Prueba desde la misma Pi:
```bash
curl http://localhost:8000/api/state
```

## Lanzar el proyector (Pi)

En otra terminal de la Pi:

```bash
chromium-browser --kiosk --noerrdialogs --disable-infobars \
                 http://localhost:8000/projector
```

Si tienes dos proyectores como pantallas separadas:
```bash
# Pantalla 1
DISPLAY=:0.0 chromium-browser --kiosk http://localhost:8000/projector &
# Pantalla 2 — si quieres un contenido diferente puedes apuntar a la
# misma URL (se sincroniza vía WS) o crear /projector2 si necesitas
# fuentes distintas.
```

Para arrancarlo al boot de la Pi, añade un archivo `.desktop` a `~/.config/autostart/`:

```ini
# ~/.config/autostart/mech-projector.desktop
[Desktop Entry]
Type=Application
Name=MECH Projector
Exec=chromium-browser --kiosk --noerrdialogs --disable-infobars http://localhost:8000/projector
```

Y un servicio systemd para el servidor (lo arranca al boot, lo reinicia si crashea):

```ini
# /etc/systemd/system/mech-server.service
[Unit]
Description=MECH backend server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/MECH
ExecStart=/home/pi/MECH/.venv/bin/python -m backend.server
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable mech-server
sudo systemctl start mech-server
journalctl -u mech-server -f   # ver logs
```

## Operar desde Windows

Lee [`windows/README.md`](../windows/README.md) — cubre los tres modos (.bat app, .bat kiosko, PWA instalada).

Resumen ultra rápido:
1. Edita `windows/config.txt` con la URL: `http://192.168.1.42:8000` (la IP de tu Pi).
2. Doble click a `windows/MECH Control.bat`.

## Lo que hace el panel

| Vista | Para qué |
|---|---|
| **Voz / Comandos** | Activar el bucle de voz (botón rojo), enviar comandos por texto, ver transcripción y respuestas de MECH en vivo. Botones rápidos para Romeo y Julieta, Shrek, La Odisea, etc. |
| **Proyección Stand** | Sube imágenes/videos a los proyectores 1 y 2 del stand. Encender/apagar cada uno independientemente. |
| **Espacio Inmersivo** | Vista previa del contenido inmersivo. Durante una narración aparecen aquí en vivo los **videos pre-renderizados** de la biblioteca (si la obra está completa) o, en su defecto, las imágenes generadas por NanoBanana. |
| **Firmware** | Estado del servidor, modelo de Claude, estado del Arduino, modo actual del robot. |
| **Sensores** | Resumen del estado de mic, parlante, proyectores, Arduino, cámara, WebSocket. |

Además, en `/library` (página aparte, **Biblioteca de videos**) subes los `.mp4`
pre-renderizados de cada obra. Ver [`GUIA.md`](GUIA.md) §6 y
[`backend/video_library/README.md`](../backend/video_library/README.md).
| **Arduino** | Control directo: modos (IDLE/LISTEN/SPEAK/AUTO/STOP), movimiento omnidireccional con botones pulsables, sliders para cabeza/brazos, comando crudo para debug. |

## PARO DE EMERGENCIA

El botón rojo del header (siempre visible) y la **barra espaciadora** disparan el paro:

1. `MODE:STOP` al Arduino → motores apagados, servos congelados.
2. `sounddevice.stop()` → corta cualquier TTS en curso.
3. Apaga el bucle de voz si estaba activo.
4. Limpia la proyección AI.
5. Marca todos los proyectores como apagados.

El backend implementa esto en `MechApp.emergency_stop()`. Llega vía `POST /api/emergency/stop`.

## API REST (para integraciones externas)

| Endpoint | Body | Acción |
|---|---|---|
| `POST /api/voice/text` | `{"text": "..."}` | Procesa un comando de texto como si fuera voz |
| `POST /api/voice/loop/on` | — | Arranca el bucle de voz |
| `POST /api/voice/loop/off` | — | Para el bucle de voz |
| `POST /api/projector/{s1\|s2\|imm}/upload` | multipart `file` | Sube imagen/video |
| `POST /api/projector/{id}/on` | — | Enciende proyector |
| `POST /api/projector/{id}/off` | — | Apaga proyector |
| `POST /api/arduino/raw` | `{"cmd": "MODE:AUTO"}` | Envía línea cruda al Arduino |
| `POST /api/arduino/move` | `{"vx": 60, "vy": 0, "w": 0}` | Movimiento omnidireccional |
| `POST /api/arduino/head` | `{"pan": 90, "tilt": 90}` | Posición de cabeza |
| `POST /api/arduino/arm` | `{"side": "L", "angle": 30}` | Posición de brazo |
| `POST /api/arduino/mode/{MODE}` | — | AUTO / IDLE / LISTEN / SPEAK / STOP |
| `POST /api/emergency/stop` | — | PARO DE EMERGENCIA |
| `GET  /api/state` | — | Estado completo (JSON) |
| `GET  /api/library` | — | Lista de obras y cuántos segmentos están subidos |
| `POST /api/library/{slug}/{segment}` | multipart `file` | Sube el `.mp4` de un segmento |
| `DELETE /api/library/{slug}/{segment}` | — | Borra el `.mp4` de un segmento |

## Protocolo WebSocket

Conecta a `ws://<pi>:8000/ws`. Recibirás un primer mensaje con el estado completo y luego eventos en tiempo real.

**Server → Cliente:**

```json
{"type": "state",       "state": { ... }}                    // estado completo
{"type": "log",         "message": "...", "level": "ok"}     // entrada de log
{"type": "transcript",  "text": "Cuéntame Romeo y Julieta"}  // STT detectó voz
{"type": "ai_response", "text": "...", "segment": 1, "total": 5}  // respuesta de Claude
{"type": "projector",   "id": "s1", "on": true, "file": "/uploads/..."}
{"type": "image",       "url": "/generated/Romeo_1.png"}     // imagen AI nueva (fallback)
{"type": "video",       "url": "/videos/romeo_julieta/seg01.mp4"}  // video pre-renderizado (biblioteca)
```

**Cliente → Server:**

```json
{"type": "ping"}   // → recibes {"type": "pong"}
```

El resto de control es vía REST (más simple para llamadas puntuales). El WS es solo lectura de estado.

## Modos de operación

Para distintos escenarios:

| Escenario | Cómo |
|---|---|
| **Demo completa con público** | Servidor + proyector kiosko + Windows con `MECH Control.bat` para que el operador supervise. Bucle de voz ON. |
| **Pruebas headless** | `python -m backend.main` (sin servidor). Solo voz local. Sin frontend. Útil para depurar la cadena STT→Claude→TTS sin web. |
| **Demo sin voz (manual)** | Servidor con bucle de voz OFF. Operador usa botones del panel (texto + comandos rápidos). Útil si el micrófono falla. |
| **Solo proyector** | Servidor + proyector kiosko + subir archivos vía panel. No usa Claude ni voz. Para mostrar contenido estático del stand. |
| **Paro de emergencia remoto** | Cualquier dispositivo en la red con la URL puede dispararlo (no hay auth — restringe la red wifi). |

## Notas de seguridad

El servidor escucha en `0.0.0.0:8000` **sin autenticación**. Esto es intencional para que el panel de control sea fácil de abrir desde cualquier laptop del equipo durante la exhibición. **No expongas el servidor a internet** — corre en la wifi del stand. Si necesitas auth, añade un middleware FastAPI con HTTP Basic o un token compartido.
