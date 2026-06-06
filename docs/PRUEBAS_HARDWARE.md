# Pruebas de hardware — Micrófono Steren MIC-9010 + Cámara Logitech C930e

Esta guía es para verificar, en la Raspberry Pi 5, que el **micrófono
inalámbrico Steren MIC-9010** y la **webcam Logitech C930e** funcionan
antes de meterlos al pipeline de MECH.

> Hacelas en este orden: primero mic, después cámara. Si el mic falla,
> el STT no va a oír nada y vas a perder tiempo debuggeando lo que no es.

---

## 0. Antes de empezar

1. Encendé la Pi y conectate a ella (monitor + teclado, o por SSH).
2. Abrí una terminal.
3. Enchufá los dos dispositivos por USB **antes** de cualquier prueba:
   - El **receptor** del Steren MIC-9010 (no el micrófono — el receptor
     es la cajita con la antena que va a la Pi).
   - La **Logitech C930e**.
4. Encendé el transmisor de solapa del Steren (el que te clipas a la
   ropa). Verificá que su LED esté encendido.

Listá rápido qué USB ve la Pi:

```bash
lsusb
```

Deberías ver dos líneas nuevas, una con algo tipo "C-Media" / "Generic
USB Audio" (el receptor Steren — los inalámbricos baratos suelen
mostrarse como genéricos) y una con "Logitech, Inc. Webcam C930e".

---

## 1. Micrófono Steren MIC-9010

### 1.1 ¿La Pi lo reconoce como entrada de audio?

```bash
arecord -l
```

Esperás ver una `card` que no sea `bcm2835` (la Pi interna) ni
`Webcam` (la C930e). El nombre suele ser "USB PnP Sound Device",
"USB Audio Device" o similar. Anotate **el número de card** (ej. `card 2`).

Otra forma desde Python (que es lo que usa MECH):

```bash
cd ~/MECH  # o donde tengas el repo clonado
source .venv/bin/activate
python -c "import sounddevice as sd; print(sd.query_devices())"
```

En la lista que imprime, fijate cuáles tienen `inputs > 0`. El Steren
debería aparecer con `2 in, 0 out` (estéreo) o `1 in, 0 out` (mono).
Anotate **el índice** (el número entre corchetes al principio de la
línea) o **el nombre exacto**.

### 1.2 Grabar 5 segundos y reproducirlos

Probá grabación + reproducción con `arecord`. Reemplazá `2` por tu
número de card:

```bash
arecord -D plughw:2,0 -f S16_LE -r 16000 -c 1 -d 5 prueba_mic.wav
aplay prueba_mic.wav
```

Mientras grabás, **hablale al transmisor** desde 1–2 metros de
distancia. Si al reproducir escuchás tu voz limpia, el mic funciona.

Si no escuchás nada o solo silencio/ruido blanco:
- Verificá que el transmisor esté **encendido** (LED) y con batería.
- Verificá que el transmisor y el receptor estén **emparejados** en el
  mismo canal (la mayoría de los Steren ya vienen así de fábrica).
- Probá ajustar el volumen de captura: `alsamixer`, F4 (capture),
  seleccioná el dispositivo USB con F6, subí el nivel.

### 1.3 Configurar MECH para usar este mic

Editá `backend/.env`:

```env
AUDIO_INPUT_DEVICE=Steren
```

(O si "Steren" no aparece en el nombre, usá un fragmento del nombre
que sí salió en `sd.query_devices()`, ej. `USB PnP` o `USB Audio`.
También podés usar el número de índice directamente: `AUDIO_INPUT_DEVICE=3`.)

### 1.4 Probar el pipeline completo de voz

Con el venv activo y el `.env` ya editado:

```bash
python -m backend.main
```

Esperá a que diga "Escuchando…" y hablale: "MECH, contame Romeo y
Julieta". Si en consola aparece la transcripción del STT y después
Claude responde, el mic está integrado correctamente.

> Si el STT transcribe pero salen palabras raras o cortadas, probá
> subir `WHISPER_MODEL=small` en `.env` (más preciso, más lento) o
> bajar `VAD_AGGRESSIVENESS=1` (más tolerante con silencios).

---

## 2. Cámara Logitech C930e

### 2.1 ¿La Pi la reconoce como cámara V4L2?

```bash
v4l2-ctl --list-devices
```

Esperás un bloque parecido a:

```
HD Webcam C930e (usb-xhci-hcd.0-1):
        /dev/video0
        /dev/video1
```

(La C930e suele exponer 2 nodos: uno para video y otro para metadata.
El que importa es el `video0`, o el menor de los dos.)

Si no aparece, probá otro puerto USB (preferí los USB 3.0 azules de la
Pi 5) y volvé a ejecutar el comando.

### 2.2 Ver las resoluciones que soporta

```bash
v4l2-ctl -d /dev/video0 --list-formats-ext
```

Para MECH alcanza con 640x360 o 1280x720 @ 30fps en MJPG. La C930e
también da 1080p, pero no lo necesitamos y consume más CPU.

### 2.3 Capturar un frame de prueba

Con `ffmpeg` (ya viene en Raspberry Pi OS):

```bash
ffmpeg -y -f v4l2 -video_size 1280x720 -i /dev/video0 -frames 1 prueba_cam.jpg
```

Abrí `prueba_cam.jpg` con `xdg-open prueba_cam.jpg` o copialo a tu
laptop con `scp` para verlo. Tiene que ser una foto nítida de lo que
estaba delante de la cámara.

Si la imagen sale negra:
- Tapá y destapá la cámara con la mano para asegurarte de que está
  capturando (no solo cacheando).
- Probá `-video_size 640x360` (algunos drivers piden bajar resolución
  para inicializar).

### 2.4 Stream en vivo (opcional, para validar fps)

```bash
ffplay -f v4l2 -video_size 640x360 -framerate 30 -i /dev/video0
```

Necesitás monitor conectado a la Pi para verlo. Si va fluido a 30 fps
sin tearing, ya está lista para MediaPipe.

### 2.5 Confirmar que el mic de la C930e NO se está usando

La C930e también tiene mic integrado, pero queremos que MECH use SOLO
el Steren. Volvé a correr:

```bash
python -c "import sounddevice as sd; print(sd.query_devices())"
```

Y revisá el índice/nombre que muestre la línea con "C930e" o
"Logitech". Asegurate de que `AUDIO_INPUT_DEVICE` en `.env` apunte al
Steren y NO a este. Si los dos quedan con el mismo nombre genérico,
usá el número de índice del Steren explícitamente.

---

## 3. Checklist final

- [ ] `arecord -l` muestra el Steren como card USB.
- [ ] Grabación de prueba `prueba_mic.wav` se escucha limpia.
- [ ] `.env` tiene `AUDIO_INPUT_DEVICE` apuntando al Steren.
- [ ] `python -m backend.main` transcribe la voz correctamente.
- [ ] `v4l2-ctl --list-devices` muestra la C930e en `/dev/video0`.
- [ ] `prueba_cam.jpg` salió nítida.
- [ ] El mic de la C930e NO es el dispositivo de captura activo.

Cuando los 7 estén tildados, podemos pasar a escribir `backend/vision.py`
(MediaPipe Face Detection + seguimiento) sin sorpresas de hardware.

---

## 4. Troubleshooting frecuente

**"No such file or directory: /dev/video0"** → la C930e no se conectó
bien o quedó en otro puerto. Probá `lsusb` y reconectá.

**"Device or resource busy" al grabar** → otro proceso (probablemente
PulseAudio/PipeWire) tiene el mic. Cerrá el navegador y cualquier app
de audio, o usá `fuser -v /dev/snd/*` para ver qué lo retiene.

**Steren entra y sale (ruido intermitente)** → el transmisor tiene la
batería baja, o estás fuera del rango (>20 m). Recargá y acercate.

**La C930e funciona pero a 5 fps** → la Pi está negociando YUYV en vez
de MJPG. Forzá MJPG en MediaPipe / OpenCV cuando hagamos `vision.py`
(`cv2.VideoCapture(0)` + `cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))`).
