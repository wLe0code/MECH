"""Reproduce un .wav con sounddevice, en un proceso aparte.

Por qué existe
--------------
El TTS usa pw-play/paplay/ffplay (procesos externos, ya aislados) y de último
recurso sounddevice. Pero sounddevice abre el hardware ALSA directamente, y
ALSA puede ABORTAR todo el proceso con una aserción en C si el dispositivo de
salida desaparece en pleno open (el mismo bug de `pa_linux_alsa.c` que mataba
al server con el micrófono). Al correr acá, el abort mata solo a este hijo:
el server sigue vivo y la voz simplemente no se emitió en ese intento.

    python -m backend.wav_play <archivo.wav>

Código de salida: 0 = se reprodujo, 1 = no se pudo (archivo o dispositivo).
"""

from __future__ import annotations

import sys
import time

import sounddevice as sd
import soundfile as sf


def main() -> int:
    if len(sys.argv) < 2:
        print("[wav_play] falta el archivo .wav", file=sys.stderr, flush=True)
        return 1
    try:
        data, sr = sf.read(sys.argv[1], dtype="float32")
    except Exception as e:
        print(f"[wav_play] no pude leer {sys.argv[1]}: {e}", file=sys.stderr, flush=True)
        return 1
    try:
        sd.play(data, sr)
        try:
            stream = sd.get_stream()
            while stream is not None and stream.active:
                sd.sleep(50)
        except Exception:
            sd.stop()
    except Exception as e:
        print(f"[wav_play] no pude reproducir: {e}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())