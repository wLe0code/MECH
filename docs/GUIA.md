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
                       ┌─────────────────┐
                       │ ARDUINO         │
                       │  - HC-SR04      │  ◄── evita obstáculos
                       │  - servos       │  ◄── cabeza + brazos
                       │  - 4 motores DC │  ◄── ruedas omni
                       └─────────────────┘
```

**División de responsabilidades:**

| Componente | Hace |
|---|---|
| Raspberry Pi 5 | Audio, IA (Claude/Gemini/ElevenLabs), orquestación |
| Arduino | Control de motores y servos, evasión de obstáculos en tiempo real |
| Proyector(es) | Muestra imágenes generadas por NanoBanana |
| Micrófono USB | Entrada de voz del usuario |
| Parlante USB / Bluetooth | Salida de voz del robot |

**Por qué dividirlo así:** el Arduino es ideal para control en tiempo real (ms) de motores y sensores; la Pi 5 maneja la parte "inteligente" donde Python + APIs es más práctico. Se hablan por USB serial — un solo cable.

## 1. Hardware

### Lista de componentes

- **Raspberry Pi 5 (4 GB)** + microSD 64 GB clase 10+
- **Arduino** del kit "robo robo" (UNO o Mega) — Mega recomendado por número de pines
- **Driver de motores** L298N o similar (2 unidades si usas 4 motores)
- **4 motores DC** con ruedas omnidireccionales (mecanum)
- **4 servos** (SG90 o MG996R): cabeza pan, cabeza tilt, brazo izq, brazo der
- **1 sensor ultrasónico HC-SR04** — ver sección 1.2
- **Micrófono USB** (cualquiera con buen ruido de fondo; el ReSpeaker es excelente pero opcional)
- **Parlante** USB o conectado al jack 3.5mm de la Pi
- **1 o 2 proyectores** (HDMI desde la Pi)
- **Fuente de poder** independiente para los motores (NO los alimentes desde la Pi)
- Cables jumper, protoboard, capacitores de 100µF en las líneas de motores

### 1.2 Cámara vs sensor ultrasónico — recomendación

**Recomendación: empieza con HC-SR04 solo, y opcionalmente añade cámara después.**

Razones:
- **Para evasión de obstáculos**, el HC-SR04 es muchísimo más simple y confiable. Latencia <30ms, sin procesamiento, sin librerías. La Pi 5 con 4GB no tiene mucho margen para correr Whisper + CV simultáneamente.
- **La cámara aporta valor** si quieres detectar al usuario (presencia, posición, gestos). Pero para una primera versión funcional, no es necesario: el robot puede asumir que el usuario está al frente cuando empiece a hablar (el VAD detecta esto).
- **Si quieres reconocimiento facial o seguir al usuario con la mirada**, ahí sí necesitas cámara (un módulo Pi Camera v3, no USB — la latencia es menor).

**Plan sugerido:**
1. **Fase 1 (esta guía):** HC-SR04 + voz. Funciona completo.
2. **Fase 2 (opcional):** añade Pi Camera v3 + MediaPipe para detectar al usuario y girar la cabeza hacia él. No requiere cambios en este código, solo un nuevo módulo `vision.py`.

Si tienes que elegir uno solo y de verdad uno solo: **HC-SR04**.

### 1.3 Cableado básico

```
HC-SR04:
  VCC  → 5V
  GND  → GND
  TRIG → Arduino pin 7
  ECHO → Arduino pin 8 (con divisor de tensión 5V→3.3V si tu Arduino es de 3.3V)

Servos (señal):
  Cabeza Pan   → pin 9
  Cabeza Tilt  → pin 10
  Brazo Izq    → pin 11
  Brazo Der    → pin 12
  Alimenta los servos con 5V externos, NO desde el Arduino. GND común.

Motores (L298N):
  Cada L298N maneja 2 motores. Necesitas 2 drivers para 4 motores.
  Conecta IN1/IN2/ENA (PWM) según constantes en mech_controller.ino.
  Alimenta los motores con una fuente independiente (7–12V según motor).
  GND común con el Arduino.

Arduino ↔ Raspberry Pi:
  USB. Aparece en la Pi como /dev/ttyACM0 (UNO) o /dev/ttyUSB0 (clones).
```

Ajusta los pines en `arduino/mech_controller/mech_controller.ino` (sección "CONFIGURACIÓN DE PINES").

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

Si el micrófono USB no es el default, edita `~/.asoundrc` o usa `pavucontrol` (`sudo apt install pavucontrol`) para fijarlo.

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
~/bin/arduino-cli compile --fqbn arduino:avr:mega .
~/bin/arduino-cli upload  --fqbn arduino:avr:mega --port /dev/ttyACM0 .
```

Cambia `mega` por `uno` si usas Arduino UNO. Si usas UNO, vas a tener que reasignar pines IN1/IN2 en el .ino — el UNO no tiene 22-29.

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
- **Cámara Pi v3 + MediaPipe**: detectar al usuario y girar la cabeza hacia él durante LISTEN.
- **Memoria entre días**: persistir conversaciones en SQLite para que el robot reconozca visitantes recurrentes (con su consentimiento).
- **Skills de Claude API**: meter el contenido cultural (obras completas, contexto histórico) como Skills en vez del system prompt — escala mejor a más obras.
