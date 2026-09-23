# Pruebas de conexión — MECH

Suite que verifica el comportamiento "a prueba de todo" de cámara, micrófono,
Arduino y del arranque. Se puede correr en CUALQUIER máquina (sin la Pi, sin
micrófono, sin cámara, sin Arduino): los dispositivos se SIMULAN.

## Cómo correrla

```bash
python3 -m venv --system-site-packages .venv-tests
.venv-tests/bin/pip install pytest
cd <repo>
.venv-tests/bin/python -m pytest tests/ -x -q
```

(o simplemente `python3 -m pytest tests/` si ya tenés pytest).

## Qué cubre

| Archivo | Qué verifica |
|---|---|
| `test_mic_worker.py` | El protocolo del subproceso del micrófono con hijos REALES: argv inválido, hijo sin sounddevice (muerte limpia y detección por EOF), fallo al abrir ("No such device"), flujo feliz con datos reales por el pipe y cierre limpio por EPIPE. |
| `test_stt.py` | Framing de 30 ms, vigilia del hijo (caída silenciosa ≠ cuelgue), clasificación de errores de dispositivo, resolución del mic (por índice/nombre/nunca la webcam), rescan ALSA solo cuando cambia, probe (OK / mudo / fallo), y el flujo completo `record_until_silence` con VAD simulado (detección de voz, corte, timeout, cancelación). |
| `test_tts.py` | Orden de reproductores (pw-play → paplay → ffplay → `wav_play`), último recurso en proceso aparte, fallo total sin excepción, stop_event, y `backend/wav_play.py` (argumentos, reproduce, no puede leer, salida fallida). |
| `test_vision.py` | La cámara NUNCA se rinde: se inyecta una cámara que muere 60 lecturas y vuelve; el hilo se recupera solo, no dice "dejo de intentarlo" y avisa de corriente/cable UNA sola vez. También el caso "no hay ninguna cámara" (el loop termina sin reventar). |
| `test_arduino.py` | El hilo de reconexión no muere ni con fallos repetidos; reconecta solo cuando el Arduino vuelve; los comandos se escriben de verdad; la desconexión en caliente se refleja y se recupera. |
| `test_interrupt.py` | Un corte del micrófono a mitad de narración se reabre a los 3 s y la escucha de "oye MECH" continúa (antes moría hasta la próxima narración). |
| `test_preflight.py` | El chequeo previo nunca revienta: mic sano → OK, mic mudo → FALLA clara, crash del hijo aislado → FALLA con motivo (no un crash del preflight). |
| `test_shell_iniciar.py` | `pi/iniciar-mech.sh`: un crash se reinicia solo (hasta 5 veces) y después deja la ventana abierta con el motivo; Ctrl+C y salida limpia NO se reinician. |

## Cómo funciona

- `tests/stubs/` simula el hardware: `sounddevice` (con amplitud controlable,
  fallo al abrir, contador de reinicializaciones), `webrtcvad`, pyserial
  (puerto que se enchufa/desenchufa), cv2 (cámara que muere y vuelve), etc.
- El código bajo prueba es el REAL de `backend/` (se importa desde
  `../fix/backend`... en realidad desde el árbol del repo donde corras pytest).
- Los tests de subproceso (`test_mic_worker.py`) lanzan `python -m
  backend._mic_worker` de verdad, con sounddevice simulado vía `PYTHONPATH`.

## Nota

Ningún test toca la red, ni el hardware, ni gasta créditos.