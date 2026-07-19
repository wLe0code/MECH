# Guía MECH — montaje y operación

Esta guía cubre, en orden de ejecución, todo lo necesario para que MECH funcione: arquitectura, hardware, instalación de software en la Raspberry Pi 5, configuración de APIs y operación.

## 0. Arquitectura del sistema

```
                       ┌─────────────────────────────────────┐
                       │           USUARIO HABLA             │
                       └───────────────┬─────────────────────┘
                                       │ audio
                                       ▼
┌──────────────────────────────────────────────────────────────────┐
│ RASPBERRY PI 5 (cerebro)                                         │
│                                                                  │
│   micrófono ──► STT local (faster-whisper) ──► texto             │
│                                                  │               │
│                                                  ▼               │
│            ┌───────────────────────────────────────────────┐    │
│            │  Claude API (Opus 4.7) — devuelve un PLAN     │    │
│            │   segmentos = [{narración, imagen, gesto}]    │    │
│            └────────────┬──────────────────────────────────┘    │
│                         │                                        │
│         ┌───────────────┼───────────────┐                       │
│         ▼               ▼               ▼                        │
│   ElevenLabs       Gemini 2.5         Serial                    │
│     (TTS)        Flash Image          a Arduino                 │
│         │            │                    │                     │
│         ▼            ▼                    ▼                     │
│      parlante     proyector          Arduino + motores          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                            │
                            ▼ USB serial
                       ┌──────────────────────┐
                       │ ARDUINO (Uno R3)     │
                       │  - servos            │  ◄── cabeza + brazos
                       │  - 4 motores DC      │  ◄── ruedas omni
                       └──────────────────────┘

   La cámara Logitech C930e va por USB directo a la Pi (solo video):
   detecta al usuario. El micrófono es el receptor USB del Steren MIC-9010.
```

**División de responsabilidades:**

| Componente | Hace |
|---|---|
| Raspberry Pi 5 (8 GB) | Audio, visión, IA (Claude/Gemini/ElevenLabs), orquestación |
| Arduino Uno + 2× L298N | Control de motores (4 ruedas) y 2 servos de brazos en tiempo real |
| Cámara Logitech C930e (USB) | Detección de usuario (**solo video**) |
| Micrófono Steren MIC-9010 (receptor USB) | Entrada de voz (inalámbrico) |
| Proyector(es) | Muestra videos pre-renderizados (biblioteca) o imágenes de NanoBanana |
| Parlante USB / jack 3.5mm | Salida de voz del robot |

**Por qué dividirlo así:** el Arduino es ideal para control en tiempo real (ms) de motores y servos; la Pi 5 maneja la parte "inteligente" (audio, visión, APIs) donde Python es más práctico. Se hablan por USB serial — un solo cable.

> **Nota sobre obstáculos:** el plan original tenía un sensor ultrasónico HC-SR04 para evasión. **Se eliminó** — ahora solo se usa la cámara C930e para detectar usuarios. En operación de stand (poco movimiento autónomo) no hace falta evasión rápida. Si más adelante el robot choca, se puede volver a añadir un HC-SR04 (2 pines del Arduino).

## 1. Hardware

### Lista de componentes

- **Raspberry Pi 5 (8 GB)** + microSD 64 GB clase 10+
- **Arduino Uno R3** — el cerebro de movimiento, por USB a la Pi
- **2× driver de motores L298N** — para las 4 ruedas DC (cada L298N maneja 2 motores)
- **Fuente de 5–6V para los servos** (protoboard / módulo de alimentación) con buena corriente para los 2 MG996R
- **4 motores DC** con ruedas omnidireccionales (mecanum)
- **2 servos MG996R**: brazo izq, brazo der (el robot no tiene cabeza móvil)
- **Cámara Logitech C930e** (USB UVC, 1080p, FOV 90°) — **solo video** (detección de usuario)
- **Micrófono inalámbrico Steren MIC-9010** (de solapa, receptor USB) — entrada de voz
- **Parlante** (la Pi 5 no tiene jack 3.5mm: usa parlante USB, Bluetooth, o un dongle USB→3.5mm)
- **Proyector YG300** (HDMI desde la Pi). ⚠️ Antes se usaba un HY300, pero se
  cambió al **YG300 por el voltaje** — el YG300 se alimenta con 5V, compatible
  con la energía disponible en el robot.
- **Interruptor general de energía** — corta la alimentación de potencia del
  robot (batería → drivers/servos) sin desenchufar nada. Apagarlo ANTES de
  tocar el cableado.
- **Fuente de poder** independiente para los motores (NO los alimentes desde la Pi)
- Cables jumper, capacitores de 100µF en las líneas de motores

### 1.2 Visión y audio — cámara C930e (video) + mic inalámbrico Steren

- **Visión (Logitech C930e):** la cámara USB se usa **solo para video**. Su FOV de 90° detecta a gente que se acerca por los lados. Con OpenCV + MediaPipe (módulo `vision.py`, pendiente) el robot sabrá cuándo hay alguien al frente para activar el modo de escucha y seguirlo. **El micrófono de la C930e ya no se usa.**
- **Micrófono (Steren MIC-9010):** un micrófono **inalámbrico de solapa** con receptor recargable. El receptor se enchufa por **USB a la Pi** y aparece como dispositivo de captura. Es inalámbrico (~20–35 m), así que el visitante u operador puede hablar sin cable. En el código se elige con `AUDIO_INPUT_DEVICE` en `.env` (ver §3.3).

> **Sin sensor ultrasónico:** el plan original combinaba HC-SR04 (evasión rápida) + cámara (detección de usuario). Se **eliminó el HC-SR04**; la cámara cubre todo. Trade-off conocido: la cámara + MediaPipe corre a ~10 fps, suficiente para detectar presencia pero no para frenar antes de chocar en movimiento. En un stand con poco movimiento autónomo no es problema. Si hace falta, un HC-SR04 se reconecta en 2 pines del Arduino.

**Conexión:** la C930e va por **USB directo a la Pi**, no al Arduino. Para verificar que la Pi la ve:
```bash
v4l2-ctl --list-devices          # debe aparecer como /dev/videoN
ffmpeg -f v4l2 -i /dev/video0 -frames 1 test.jpg   # captura un frame de prueba
```

### 1.3 Cableado básico

Los pines ya están en `mech_controller.ino` (Arduino Uno R3); esto es solo la
referencia para cablear.

**Hay 3 fuentes de alimentación independientes.** Solo comparten la **tierra
(GND)**; los positivos NUNCA se mezclan (por eso no se quema nada):

| Fuente | Alimenta |
|---|---|
| **USB de la Pi** | Lógica del Arduino |
| **Batería de motores** (≥7V ideal; con 6V funciona con menos fuerza) | Los 4 motores (vía L298N) + la lógica de los L298N |
| **Fuente de 5–6V** (protoboard) | Los 2 servos MG996R |

#### Servos (2× MG996R — brazos)
| Cable del servo | Va a |
|---|---|
| Señal Brazo Izq | pin **9** del Uno |
| Señal Brazo Der | pin **10** del Uno |
| **+** (rojo) | riel **+** de la protoboard (fuente de 5–6V) |
| **−** (café) | riel **−** (tierra común) |

*(Los servos NO usan driver: el Uno les da la señal directo.)*

#### Driver L298N #1 (motores M1=FL, M2=FR)
| L298N | → Uno | | L298N | → Uno |
|---|---|---|---|---|
| ENA | **3** | | ENB | **5** |
| IN1 | **4** | | IN3 | **7** |
| IN2 | **2** | | IN4 | **8** |

- **OUT1/OUT2** → motor M1 · **OUT3/OUT4** → motor M2
- **+12V (VMS)** → **+** de la batería · **GND** → tierra común · **+5V** → SIN conectar

#### Driver L298N #2 (motores M3=BL, M4=BR)
| L298N | → Uno | | L298N | → Uno |
|---|---|---|---|---|
| ENA | **6** | | ENB | **11** |
| IN1 | **12** | | IN3 | **A0** |
| IN2 | **13** | | IN4 | **A1** |

- **OUT1/OUT2** → motor M3 · **OUT3/OUT4** → motor M4
- **+12V (VMS)** → **+** de la batería · **GND** → tierra común · **+5V** → SIN conectar

#### Batería de motores
- **+** → +12V (VMS) de **ambos** L298N.
- **−** → tierra común, con **cable directo y grueso** (no por un rielito fino,
  para no ahogar la corriente de los motores).

#### Tierra común (riel − de la protoboard)
Unir aquí **todos** los negativos: GND de los 2 L298N, GND del Arduino, **−** de
la fuente de servos, **−** de la batería de motores. Sin esto nada funciona bien.

#### Periféricos de la Pi (USB directo, NO al Arduino)
- **Cámara Logitech C930e** → USB de la Pi (solo video, `/dev/videoN`).
- **Receptor del mic Steren MIC-9010** → USB de la Pi.
- **Arduino Uno** → USB de la Pi (`/dev/ttyACM0` o `/dev/ttyUSB0`).

#### Jumpers de cada L298N
- **ENA y ENB:** QUITADOS (para controlar velocidad por PWM).
- **Jumper de 5V:** PUESTO — la placa saca su lógica de la batería de motores.
  El terminal **+5V se deja SIN conectar**.

> 🚨 **Seguridad (no quemar nada):**
> - Los positivos NO se mezclan; cada voltaje por su lado. Solo el GND es común.
> - **NUNCA** conectes el 5V del Arduino al **+5V** del L298N con el jumper de 5V
>   puesto (dos fuentes de 5V peleando → se quema). Con esta config no hace falta.
> - Revisa la **polaridad** de la batería (+ al +12V, − al GND) antes de encender.
> - La fuente de servos debe dar **varios amperios** a 5–6V (2 MG996R piden harto).
>
> 💡 Si una rueda gira al revés, intercambia sus 2 cables de motor (OUT) o sus IN.

**Mapa de pines del Arduino de un vistazo:**
```
Pin 2  -> L298N#1 IN2      Pin 9  -> Servo Brazo IZQ
Pin 3  -> L298N#1 ENA      Pin 10 -> Servo Brazo DER
Pin 4  -> L298N#1 IN1      Pin 11 -> L298N#2 ENB
Pin 5  -> L298N#1 ENB      Pin 12 -> L298N#2 IN1
Pin 6  -> L298N#2 ENA      Pin 13 -> L298N#2 IN2
Pin 7  -> L298N#1 IN3      Pin A0 -> L298N#2 IN3
Pin 8  -> L298N#1 IN4      Pin A1 -> L298N#2 IN4
```

## 2. Cuentas y API keys

Necesitas tres servicios. Coste estimado para una demo de 1 día:

| Servicio | Para qué | Coste estimado |
|---|---|---|
| **Anthropic Claude API** | Cerebro del robot (decide qué responder, narra) | ~USD 5–15 / día de demo |
| **ElevenLabs** | Voz natural en español | Plan Starter $5/mes alcanza para una demo |
| **Google AI Studio** | NanoBanana (imágenes para el espacio inmersivo) | Tier gratuito generoso |

### 2.1 Anthropic
1. Crea cuenta en https://console.anthropic.com
2. Settings → API Keys → Create Key.
3. Guarda el valor (empieza con `sk-ant-...`).
4. Añade crédito mínimo ($5 USD).

### 2.2 ElevenLabs
1. Crea cuenta en https://elevenlabs.io
2. Profile → API Keys.
3. Voces recomendadas en español:
   - `EXAVITQu4vr4xnSDxMaL` (Bella, cálida)
   - O navega Voice Library y elige otra; copia su `voice_id`.

### 2.3 Google AI (NanoBanana)
1. Ve a https://aistudio.google.com/apikey
2. Create API Key.
3. Modelo a usar: `gemini-2.5-flash-image`.

Pon las tres en `backend/.env` (basado en `.env.example`).

## 3. Configurar la Raspberry Pi 5

### 3.1 Sistema operativo

- Instala **Raspberry Pi OS (64-bit, Bookworm)** con Raspberry Pi Imager.
- Configura SSH y wifi antes del primer boot (asistente del Imager).
- Primer login → `sudo apt update && sudo apt full-upgrade -y`.

### 3.2 Dependencias del sistema

```bash
sudo apt install -y \
    python3-pip python3-venv python3-tk \
    portaudio19-dev libsndfile1 \
    arduino \
    git
```

### 3.3 Audio: que el micrófono USB y el parlante funcionen

```bash
# Lista dispositivos de audio:
arecord -l   # entrada (micrófono)
aplay   -l   # salida (parlante)

# Prueba grabar 3 segundos y reproducir:
arecord -d 3 -f cd test.wav
aplay test.wav
```

**Elegir el micrófono Steren MIC-9010.** Al conectar su receptor USB aparecerá
como un dispositivo de captura más (junto al de la C930e, que ya no usamos para
audio). Lista los dispositivos que ve el código y pon el Steren en `.env`:
```bash
# Muestra todos los dispositivos con su índice y nombre:
python -c "import sounddevice as sd; print(sd.query_devices())"
```
Luego en `backend/.env`:
```
AUDIO_INPUT_DEVICE=Steren     # parte del nombre, o el índice (ej. 3)
```
`stt.py` usará ese micrófono. Si lo dejas vacío, usa el dispositivo por defecto
del sistema (que podría ser el de la C930e — por eso conviene fijarlo).

### 3.4 Clonar e instalar el backend

```bash
cd ~
git clone <tu repo MECH>
cd MECH

python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

> **Nota:** `faster-whisper` en Pi 5 tarda ~30s en cargar el modelo `base` la primera vez (lo descarga). Después es instantáneo.

### 3.5 Configurar variables de entorno

```bash
cp backend/.env.example backend/.env
nano backend/.env
```

Rellena las tres API keys y verifica `ARDUINO_PORT` (corre `ls /dev/ttyACM* /dev/ttyUSB*` con el Arduino conectado para ver cuál es).

### 3.6 Permisos para el puerto serial

```bash
sudo usermod -a -G dialout $USER
# Cierra sesión y vuelve a entrar para que aplique.
```

## 4. Subir el firmware al Arduino

### Opción A — desde la Pi con arduino-cli

```bash
# Instala arduino-cli si no lo tienes (la Pi ya tiene Arduino IDE clásico):
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
./bin/arduino-cli core update-index
./bin/arduino-cli core install arduino:avr

# Compila y sube
cd arduino/mech_controller
~/bin/arduino-cli compile --fqbn arduino:avr:uno .
~/bin/arduino-cli upload  --fqbn arduino:avr:uno --port /dev/ttyACM0 .
```

El **Arduino Uno R3** usa el ATmega328P, por eso el `fqbn` es `arduino:avr:uno`. Los pines del .ino ya están mapeados para el Uno (ver §1.3); solo cablea según esa tabla.

### Opción B — desde tu computadora con Arduino IDE

1. Abre `arduino/mech_controller/mech_controller.ino` en Arduino IDE.
2. Tools → Board → tu modelo.
3. Tools → Port → tu puerto.
4. Sketch → Upload.

### Verificar que el Arduino responde

```bash
# Desde la Pi:
python3 -c "
import serial, time
s = serial.Serial('/dev/ttyACM0', 115200, timeout=2); time.sleep(2)
print(s.readline())          # debe imprimir 'READY:MECH'
s.write(b'MODE:IDLE\n')
print(s.readline())          # 'ACK:MODE:IDLE'
"
```

## 5. Probar componentes uno por uno

Antes del bucle completo, valida pieza por pieza:

```bash
cd ~/MECH
source .venv/bin/activate

# 5.1 STT — di algo y debería transcribirlo:
python3 -c "from backend import stt; print(stt.listen_once())"

# 5.2 TTS — debe sonar por el parlante:
python3 -c "from backend import tts; tts.speak('Hola, soy MECH.')"

# 5.3 Imagen — genera un PNG en backend/generated_images/
python3 -c "
from backend.image_gen import generate_image
print(generate_image('A friendly white robot in a futuristic exhibition hall'))
"

# 5.4 Arduino — el robot debe mover el brazo:
python3 -c "
from backend.arduino_link import get_link
import time
link = get_link()
link.arm('R', 30); time.sleep(1); link.arm('R', 150); time.sleep(1); link.arm('R', 90)
"

# 5.5 Claude (sin audio) — un solo turno desde texto:
python3 -m backend.main --once "Cuéntame sobre Romeo y Julieta"
```

Si los 5 pasan, el bucle completo va a funcionar.

## 6. Operación normal

**Recomendado:** usa el servidor completo (`backend/server.py`) que sirve también el panel de control web. Lee [`FRONTEND.md`](FRONTEND.md) para la operación completa con frontend y control desde Windows.

### Modo recomendado — servidor + panel web

```bash
# Terminal 1 — servidor (en la Pi)
cd ~/MECH && source .venv/bin/activate
python -m backend.server
```

```bash
# Terminal 2 — proyector kiosko (en la Pi)
chromium-browser --kiosk http://localhost:8000/projector
```

```
# Desde Windows: edita windows\config.txt con la IP de la Pi
# y doble click en windows\MECH Control.bat
```

El panel da control sobre voz, proyectores, Arduino, y un botón de **PARO DE EMERGENCIA** siempre visible (también con barra espaciadora).

### Biblioteca de videos pre-renderizados (Opción B)

Para las obras conocidas (Romeo y Julieta, Shrek, La Odisea, Don Quijote...) MECH
reproduce **videos generados antes del evento** en vez de imágenes en vivo. Se generan
una sola vez en otra máquina (Kling/Veo/Runway) y se suben a MECH desde:

```
http://<IP-de-la-pi>:8000/library
```

Un card por obra, un botón por segmento, arrastra el `.mp4`. Mientras una obra **no**
tenga todos sus segmentos subidos, MECH cae automáticamente a generar imágenes con
NanoBanana para esa obra (no se rompe nada). Detalles y convención de archivos en
[`backend/video_library/README.md`](../backend/video_library/README.md).

### Modo standalone — sin frontend

Para depurar la cadena STT → Claude → TTS aislada:

```bash
# Terminal 1 — visor tkinter (alternativa al proyector kiosko)
python -m backend.projector

# Terminal 2 — bucle de voz sin servidor
python -m backend.main
```

El robot:
1. Dice un saludo y se queda en modo IDLE.
2. Cuando detecta voz (VAD), graba hasta silencio.
3. Transcribe → pide plan a Claude → ejecuta segmentos (imagen + gesto + narración).
4. Vuelve a IDLE.

**Para apagar:** Ctrl+C en la terminal del backend.

> ⚠️ **No corras `server.py` y `main.py` a la vez** — pelearían por el Arduino y el micrófono.

## 7. Flujo de una interacción típica

Usuario: *"Cuéntame sobre Romeo y Julieta."*

1. `stt.listen_once()` graba (~3s) y transcribe en ~1s.
2. `llm.plan_response(...)` llama a Claude Opus 4.7. Devuelve algo como:
   ```json
   {
     "mode": "immersive",
     "title": "Romeo y Julieta",
     "segments": [
       {
         "narration": "En la bella Verona, dos familias rivales...",
         "image_prompt": "Renaissance Verona, sunny piazza...",
         "gesture": "arms_open"
       },
       {
         "narration": "Romeo, hijo de los Montesco, conoce a Julieta...",
         "image_prompt": "Renaissance ballroom, masked dance...",
         "gesture": "thoughtful"
       },
       ...
     ]
   }
   ```
3. Por cada segmento:
   - `image_gen.generate_image(...)` (~3–5s con NanoBanana)
   - `projector.show(path)` actualiza la imagen proyectada
   - `gestures.perform(link, "thoughtful")` mueve servos en paralelo
   - `tts.speak(narration)` reproduce voz por el parlante (bloquea hasta terminar)
4. Vuelve a escuchar — el usuario puede preguntar follow-ups dentro del contexto.

## 8. Costos y rendimiento

**Latencia perceptible (estimada en Pi 5):**

| Paso | Tiempo |
|---|---|
| STT (Whisper base, frase de 5s) | ~1.5s |
| Claude Opus 4.7 (plan completo) | ~3–6s |
| NanoBanana (por imagen) | ~3–5s |
| ElevenLabs TTS (primer audio) | <1s con streaming |

**Total entre pregunta y primera frase:** ~8–12s. La primera imagen tarda, pero las siguientes corren en paralelo con la narración previa si las paralelizas (mejora opcional).

**Costos por interacción típica (3 segmentos):**
- Claude: ~$0.05 con prompt cache activo
- ElevenLabs: ~$0.02
- NanoBanana: ~$0.10 (3 imágenes)
- **Total: ~$0.17 por historia.**

## 9. Problemas comunes

| Síntoma | Causa probable | Solución |
|---|---|---|
| `serial.SerialException: could not open port` | Permisos o puerto incorrecto | `sudo usermod -a -G dialout $USER`, reloguea. Verifica con `ls /dev/ttyACM*`. |
| VAD no detecta voz | Micrófono no es el default | `pavucontrol`, fija el micrófono USB como default. |
| Whisper transcribe inglés | `WHISPER_LANGUAGE` no es `es` | Revisa `.env`. |
| TTS no suena | Parlante no es el default | `aplay -l` y `~/.asoundrc`. |
| Las imágenes no se proyectan | El visor `projector.py` no está corriendo | Lánzalo en otra terminal. |
| Arduino se resetea cada vez | Normal — al abrir el serial Arduino se resetea. El backend espera 2s. |
| Motores no responden, servos sí | Falta fuente externa para motores | Conecta VIN del L298N a fuente 7–12V, GND común con Arduino. |
| El robot tira muy fuerte | Velocidad PWM alta | Baja `AUTO_FORWARD_SPEED` en el .ino. |

## 10. Mejoras posibles (siguientes pasos)

- **Wake word** ("Hey MECH"): usa `openwakeword` o `Porcupine` para que el robot no transcriba todo lo que oye, solo después de la palabra clave.
- **Streaming TTS verdadero**: empieza a reproducir mientras ElevenLabs sigue generando (ya hay infraestructura).
- **Paralelizar imagen + narración**: mientras narra el segmento N, genera la imagen del N+1.
- **Visión con la C930e + MediaPipe** (`vision.py`, pendiente): detectar al usuario por USB UVC (OpenCV + V4L2, no picamera2) y girar la cabeza hacia él durante LISTEN. Activaría el bucle de voz automáticamente cuando alguien se acerca.
- **Memoria entre días**: persistir conversaciones en SQLite para que el robot reconozca visitantes recurrentes (con su consentimiento).
- **Skills de Claude API**: meter el contenido cultural (obras completas, contexto histórico) como Skills en vez del system prompt — escala mejor a más obras.
