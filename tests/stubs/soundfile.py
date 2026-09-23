# Stub de soundfile: escribe/lee sin disco (las pruebas no necesitan wav reales).
import numpy as np


def write(path, data, samplerate):
    return None


def read(path, dtype="float32", always_2d=False):
    return np.zeros(44100, dtype=np.float32), 44100