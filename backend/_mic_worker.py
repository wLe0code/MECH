"""Hijo aislado que abre el micrófono y manda los bytes por un pipe.

Por qué existe
--------------
PortAudio/ALSA tiene un bug serio: si el dispositivo USB desaparece (se
desenchufa el receptor, se cae la corriente del bus) EN EL MOMENTO de abrir
un stream, el código C de ALSA dispara una aserción
(`pa_linux_alsa.c: PaAlsaStream_Initialize`) y el proceso entero muere con
SIGABRT — sin ninguna posibilidad de capturarlo desde Python. Era el
"El servidor de MECH se detuvo" con el crash de ALSA en pantalla.

La solución: el stream del micrófono vive en ESTE proceso. Si el bug de
ALSA lo mata, muere solo este hijo; el server se entera (el pipe se cierra),
lo registra y reabre. El micrófono puede caerse todas las veces que quiera,
que el server nunca se cae por esa vía.

Protocolo
---------
    python -m backend._mic_worker <fd> <spec-json>

- `<fd>`: descriptor de un pipe de escritura heredado del padre (pasado con
  `pass_fds`). Por aquí se mandan los bloques int16 tal cual salen del
  callback de PortAudio.
- `<spec-json>`: `{"device": ..., "samplerate": ..., "blocksize": ...}`,
  donde `device` puede ser un índice (int), un nombre (str) o null (el
  dispositivo por defecto del sistema).

El hijo normalmente vive hasta que el padre cierra el pipe (la próxima
escritura del callback falla con EPIPE y el hijo termina solo) o hasta que
el padre lo mata. `import sounddevice` se hace DESPUÉS de parsear argv a
propósito: si el entorno del hijo falla, muere con código de salida 1 y el
padre lo ve como un fallo limpio, no como un crash.
"""

from __future__ import annotations

import json
import os
import sys
import time


def main() -> int:
    if len(sys.argv) < 3:
        print("[mic_worker] faltan argumentos: <fd> <spec-json>", file=sys.stderr, flush=True)
        return 2
    try:
        fd = int(sys.argv[1])
        spec = json.loads(sys.argv[2])
    except (ValueError, json.JSONDecodeError) as e:
        print(f"[mic_worker] argv inválido: {e}", file=sys.stderr, flush=True)
        return 2

    device = spec.get("device")
    sample_rate = int(spec.get("samplerate", 48000))
    blocksize = int(spec.get("blocksize", 1440))

    # Nada de buffering: cada callback escribe y se va.
    try:
        out = os.fdopen(fd, "wb", buffering=0)
    except OSError as e:
        print(f"[mic_worker] no pude usar el pipe: {e}", file=sys.stderr, flush=True)
        return 2

    try:
        import sounddevice as sd
    except Exception as e:
        print(f"[mic_worker] no pude importar sounddevice: {e}", file=sys.stderr, flush=True)
        return 1

    def callback(indata, frames, time_info, status):
        if status:
            print(f"[STT] sounddevice: {status}", file=sys.stderr, flush=True)
        try:
            out.write(indata.tobytes())
        except OSError:
            # El padre cerró el pipe (terminó la escucha o se cayó): salimos.
            raise SystemExit(0)

    try:
        with sd.RawInputStream(
            samplerate=sample_rate,
            blocksize=blocksize,
            dtype="int16",
            channels=1,
            device=device,
            callback=callback,
        ):
            # Vivimos hasta que el padre corte el pipe o nos mate. El callback
            # es el que escribe; aquí solo se espera.
            while True:
                time.sleep(3600)
    except Exception as e:
        print(f"[mic_worker] no pude abrir el micrófono: {e}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())