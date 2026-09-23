# Arreglos de conexión — MECH (sep 2026)

Parche que arregla **de raíz** los cortes de cámara, micrófono y Arduino: ya
no hace falta "recuperar los sistemas" porque **el servidor ya no se puede
caer por un problema de hardware**, y todo lo que se caiga se rearma solo.

## Qué estaba pasando (en simple)

| Síntoma en pantalla | Causa real | Por qué no se recuperaba solo |
|---|---|---|
| `Assertion ... pa_linux_alsa.c:2178 failed` y "El servidor de MECH se detuvo" | Cuando el receptor USB se desenchufa (o la corriente del bus cae un instante) **en el momento exacto** en que se abre el micrófono, ALSA aborta **todo el proceso** con un crash de C. | Ese abort **no se puede capturar desde Python** con try/except: era un muerte súbita del server. |
| "No puedo abrir el micrófono: ... 'No such device' [ALSA error -19]" | El número/`hw:2,0` guardado apunta a un dispositivo que ya no existe (los índices USB cambian al mover cosas de puerto). | PortAudio cachea la lista de dispositivos y no se entera de re-enchufes. |
| "La cámara dejó de dar imagen tras 7 s/56 s" + reintentos | Bajones de corriente o reinicios del USB compartido (cámara + mic + Arduino en el mismo bus). | La visión se rendía después de 5 intentos y pedía "apagá y encendé la visión" a mano. |
| "Arduino desconectado (reintentando)" | El Arduino se cae con el mismo bajón de bus. | La reconexión funcionaba, pero un solo fallo raro podía matar el hilo que reconecta (y entonces nunca más). |

## Qué cambia este parche

### 1. El micrófono ya NO puede tumbar el servidor (`backend/_mic_worker.py` NUEVO + `backend/stt.py`)
El stream del micrófono corre en un **proceso hijo aparte**. Si ALSA aborta,
muere solo el hijo; el servidor ve el pipe cerrado, lo registra como error de
dispositivo y **reabre solo**. Antes esa misma situación mataba el server y
había que ir a la Pi a reiniciar.

- El hijo se lanza por vuelta de escucha (~0.3 s), no pesa: solo importa
  sounddevice.
- La escucha también detecta "micrófono abierto pero mudo" (sin bytes en 8 s):
  antes eso colgaba la escucha para siempre silenciosamente.
- `record_until_silence`, `probe_microphone` y el chequeo del preflight usan
  el hijo. Los mensajes del panel siguen igual de claros.

### 2. Índices de audio frescos (`backend/stt.py`)
Antes de cada apertura se compara `/proc/asound/cards`: si cambió (re-enchufe,
re-enumeración USB), se re-inicializa PortAudio. Así el `.env` con nombre
("WXMH mini: USB Audio") o índice nunca apunta a un `hw` muerto.

### 2b. "Se abre pero no llega audio": ahora se DIAGNOSTICA solo (`backend/stt.py` + `backend/server.py`)
Si el micrófono se abre pero no entrega ni un byte (8 s sin datos, con 3 s de
gracia inicial tras un bajón del USB), ya no se muestra el mensaje de "receptor
desenchufado" (que era engañoso en ese caso). Ahora el panel dice la verdad:

1. Revisá que el TRANSMISOR de solapa esté encendido y con batería (el
   receptor puede estar enchufado pero SIN señal inalámbrica);
2. que AUDIO_INPUT_DEVICE apunte al receptor y no al micrófono de la cámara;
3. que no esté silenciado (alsamixer).

Y de vez en cuando lista los micrófonos que ve PortAudio (`[0] WXMH mini...
[2] Steren...`) para que el dispositivo equivocado se vea de una.

### 3. La voz de salida tampoco puede tumbar el server (`backend/wav_play.py` NUEVO + `backend/tts.py`)
El último recurso de reproducción (sounddevice directo) tenía el mismo riesgo
de abort. Ahora se reproduce con `python -m backend.wav_play` (proceso aparte);
si el parlante desaparece, se pierde un intento de audio, no el server.

### 4. La cámara NUNCA más se rinde (`backend/vision.py`)
Antes, 5 caídas seguidas → se apagaba y había que ir a "apagá y encendé la
visión". Ahora **sigue reintentando sola para siempre**, con esperas que crecen
(hasta 30 s) y un solo aviso de "esto huele a corriente/cable". Cuando la
cámara vuelve, retoma sola. Si la cámara estuvo bien 30 s seguidos, el
contador se resetea (como antes).

### 5. El hilo de reconexión del Arduino no puede morir (`backend/arduino_link.py`)
Cualquier excepción (no solo las tres previstas) se captura y se sigue
reintentando: el hilo que reconecta el Arduino en segundo plano es indestructible.

### 6. Las interrupciones sobreviven a un corte del micrófono (`backend/interrupt_listener.py`)
Si el micrófono se cae a mitad de una narración, se reabre a los 3 s y la
escucha de "oye MECH" continúa (antes moría hasta la próxima narración).

### 7. Auto-reinicio del server en la Pi (`pi/iniciar-mech.sh`)
Si aun así el server llegara a caerse (bug del programa, corte de luz en la
Pi...), `Iniciar MECH` ahora lo **levanta solo** (hasta 5 veces, con 4 s de
espera). Ctrl+C o apagado pedido no se reinician, como corresponde.

## Cómo instalarlo

### Opción A — la Pi con el repo (recomendado)
En la Pi, con MECH parado:

```bash
cd ~/MECH
git pull                          # baja estos cambios
source .venv/bin/activate
python -m backend.preflight       # opcional: chequeo rápido
./pi/iniciar-mech.sh --sin-actualizar
```

### Opción B — aplicar el parche a mano (si no querés esperar el push)
```bash
cd ~/MECH
git apply parche-conexiones.patch
# o: patch -p1 < parche-conexiones.patch
```

### Opción C — copiar los archivos
Los archivos modificados están en `MECH-fixed/` con su ruta dentro del repo.
Copialos encima (los dos NUEVOS son `backend/_mic_worker.py` y
`backend/wav_play.py`).

## Qué revisar después del primer arranque

1. El .env: `AUDIO_INPUT_DEVICE` puede quedar con el NOMBRE del mic
   ("WXMH mini: USB Audio") o vacío; con el parche los dos se re-resuelven
   solos. Lo ideal es el nombre, no el índice.
2. Los mensajes naranjas de cámara/Arduino pueden seguir saliendo si el bus
   USB está inestable, **pero ya no piden intervención**: se rearman solos.
   Si salen seguido, es CORRIENTE: mirá `dmesg | tail -20` (si dice
   `over-current` o `disconnect`, un hub USB con alimentación propia arregla
   la raíz física).
3. "El proceso del micrófono murió (código ...)" en el log es la marca del
   sistema nuevo funcionando: el server siguió vivo y reabrió solo.

## Archivos tocados

```
backend/_mic_worker.py        NUEVO  — hijo aislado del micrófono
backend/wav_play.py           NUEVO  — hijo aislado de la salida de voz
backend/stt.py                       — mic en proceso aparte + ALSA fresco
backend/tts.py                       — salida de voz en proceso aparte
backend/vision.py                    — la cámara se rearma sola para siempre
backend/arduino_link.py              — reconexión a prueba de todo
backend/interrupt_listener.py        — el corte de mic no mata la interrupción
backend/preflight.py                 — chequeo del mic a prueba de crashes
backend/server.py                    — diagnóstico "abre pero no llega audio"
pi/iniciar-mech.sh                   — auto-reinicio del server
```

## Pruebas (57, todas automáticas)

```bash
python3 -m venv --system-site-packages .venv-tests
.venv-tests/bin/pip install pytest
.venv-tests/bin/python -m pytest tests/ -q    # 57 passed
```

Cubren: el protocolo del subproceso del micrófono con hijos REALES (muerte por
EOF, cierre limpio por EPIPE, fallo al abrir), el flujo de voz con VAD
simulado, el orden de reproductores del TTS, la cámara que se cae y vuelve
(nunca se rinde), la reconexión del Arduino, las interrupciones que
sobreviven a un corte del mic, el preflight indestructible y el auto-reinicio
del script de arranque. Ningún test toca hardware ni red. Ver `tests/README.md`.