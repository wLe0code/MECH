"""Stub controlable de webrtcvad (VAD_RESULT puede ser bool o callable)."""
from __future__ import annotations

VAD_RESULT = False


def reset_state():
    global VAD_RESULT
    VAD_RESULT = False


class Vad:
    def __init__(self, *a, **k):
        pass

    def is_speech(self, frame, rate):
        f = VAD_RESULT
        return f() if callable(f) else bool(f)