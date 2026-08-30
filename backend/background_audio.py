"""Música de fondo bajo la narración (Opción Malpaís).

Para ciertas exposiciones (las marcadas con ``music: True`` en
``video_library.WORKS``) se puede subir un sample de audio que suene SUAVE
de fondo mientras MECH narra. El audio se reproduce en bucle a bajo volumen
con ``ffplay``; el TTS de ElevenLabs sale por el mismo dispositivo y el
sistema de audio (PipeWire/PulseAudio) los mezcla — así la voz queda
"encima" de la música.

Solo hay UNA pista de fondo a la vez. ``start()`` detiene la anterior.
Si ``ffplay`` no está instalado, no rompe nada: simplemente no hay música.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import config

_proc: subprocess.Popen | None = None


def start(path: Path, volume: int | None = None) -> bool:
    """Empieza a reproducir `path` en bucle a bajo volumen. Devuelve True
    si arrancó. Detiene cualquier pista previa."""
    global _proc
    stop()
    vol = config.BACKGROUND_MUSIC_VOLUME if volume is None else volume
    try:
        _proc = subprocess.Popen(
            [
                "ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
                "-volume", str(max(0, min(100, vol))),
                "-loop", "0",  # bucle infinito
                str(path),
            ],
            stdin=subprocess.DEVNULL,
        )
        return True
    except FileNotFoundError:
        # ffplay no está instalado (sudo apt install ffmpeg). Sin música.
        _proc = None
        return False
    except Exception:
        _proc = None
        return False


def stop() -> None:
    """Detiene la música de fondo si está sonando.

    Igual que la voz: si `terminate()` no basta en un cuarto de segundo, se
    mata. Si no, al interrumpir a MECH la música seguía sonando un rato por
    debajo de lo que dice después.
    """
    global _proc
    proc, _proc = _proc, None
    if proc is None:
        return
    try:
        proc.terminate()
    except Exception:
        return
    t0 = time.monotonic()
    while proc.poll() is None and time.monotonic() - t0 < 0.25:
        time.sleep(0.02)
    if proc.poll() is None:
        try:
            proc.kill()
        except Exception:
            pass


def is_playing() -> bool:
    return _proc is not None and _proc.poll() is None
