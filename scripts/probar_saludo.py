"""Mide lo que el saludo manda de VERDAD al Arduino, brazo por brazo.

Por que existe: los angulos del saludo salen de varias claves que se
multiplican entre si, y es facil creer que un cambio hizo una cosa cuando
hizo otra. Aqui se cuenta sobre las ordenes reales que recibiria el Arduino.

Ya pillo un error de verdad: al pasar ARM_WAVE_REPEATS a "solo las
agitadas", el brazo llegaba arriba una vez MAS de lo que decia el panel
(la subida inicial tambien se ve como una). Por eso el numero cuenta las
veces que llega arriba, no las agitadas.

    python scripts/probar_saludo.py

Sale 1 si algo falla. No necesita hardware ni claves de API.
"""
import sys, types, os, time
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))
for k in ("ANTHROPIC_API_KEY", "ELEVENLABS_API_KEY", "GOOGLE_API_KEY"):
    os.environ.setdefault(k, "x")

def _stub(n, **a):
    m = types.ModuleType(n)
    for k, v in a.items(): setattr(m, k, v)
    sys.modules[n] = m
_stub("sounddevice", query_devices=lambda *a, **k: [], default=types.SimpleNamespace(device=None))
_stub("soundfile"); _stub("webrtcvad", Vad=lambda *a, **k: None)
class _Any:
    def __init__(s,*a,**k): pass
    def __getattr__(s,n): return _Any()
    def __call__(s,*a,**k): return _Any()
def _falta(n):
    try: __import__(n); return False
    except Exception: return True
for _m in ("elevenlabs","anthropic","faster_whisper","serial","serial.tools",
           "serial.tools.list_ports"):
    if _falta(_m):
        mod=types.ModuleType(_m); mod.__path__=[]
        mod.__getattr__=lambda n:_Any(); sys.modules[_m]=mod
if "elevenlabs.client" not in sys.modules:
    c=types.ModuleType("elevenlabs.client"); c.ElevenLabs=_Any
    sys.modules["elevenlabs.client"]=c
try: from google import genai
except Exception:
    g=sys.modules.get("google") or types.ModuleType("google")
    g.__path__=getattr(g,"__path__",[])
    gen=types.ModuleType("google.genai"); gen.Client=_Any; gen.types=_Any()
    g.genai=gen; sys.modules["google"]=g; sys.modules["google.genai"]=gen

import config, gestures

fallos=[]
def check(c,m):
    print(("ok   " if c else "FALLA"), m)
    if not c: fallos.append(m)

class LinkFalso:
    def __init__(self): self.ordenes=[]
    def arm(self, lado, ang): self.ordenes.append((lado,int(ang)))
    def move(self,*a,**k): pass
    def stop_motors(self): pass

def picos(seq):
    """Cuantas veces el brazo LLEGA ARRIBA (maximos locales).

    Es lo que se cuenta mirando el robot: la subida inicial ya es una.
    """
    n=0
    for i in range(1,len(seq)-1):
        if seq[i] > seq[i-1] and seq[i] >= seq[i+1]: n+=1
    return n

def correr():
    link=LinkFalso()
    gestures._current["L"]=gestures._current["R"]=90
    gestures._g_wave(link)
    der=[a for l,a in link.ordenes if l=="R"]
    izq=[a for l,a in link.ordenes if l=="L"]
    return der, izq

# La coreografia se mide con los brazos SIN invertir: asi el angulo que
# recibe el Arduino es el mismo que el logico (90 reposo, mas = arriba) y
# las comprobaciones se leen solas. La inversion tiene su propia seccion.
config.ARM_INVERT_R = config.ARM_INVERT_L = False

print("=== Defaults que pidió el equipo (sep 2026) ===")
print(f"    ARM_WAVE_REPEATS = {config.ARM_WAVE_REPEATS}   (veces arriba)")
print(f"    ARM_WAVE_BOTH    = {config.ARM_WAVE_BOTH}  (dos brazos)")
check(config.ARM_WAVE_REPEATS == 3, "las rotaciones por defecto son exactamente 3")
check(config.ARM_WAVE_BOTH is False, "por defecto NO saluda con los dos brazos")

print("\n=== Lo que llega al Arduino con los defaults ===")
der, izq = correr()
subidas = picos(der)
print(f"    brazo DERECHO: {len(der)} ordenes, de {min(der)} a {max(der)}, llega arriba {subidas} vez/veces")
print(f"    brazo IZQUIERDO: de {min(izq)} a {max(izq)}")
check(max(izq) == 90 and min(izq) == 90, "el brazo IZQUIERDO no se mueve (queda en reposo 90)")
check(max(der) >= 170, "el DERECHO sube arriba del todo")
check(min(der) >= 90, "y nunca baja de 90 (no choca con el cuerpo)")
check(subidas == config.ARM_WAVE_REPEATS,
      f"llega arriba exactamente {config.ARM_WAVE_REPEATS} veces")
check(der[-1] == 90, "termina en reposo")

print("\n=== El numero del panel coincide para cualquier valor ===")
for n in (2, 3, 4, 6):
    config.ARM_WAVE_REPEATS = n
    der, _ = correr()
    got = picos(der)
    check(got == n, f"REPEATS={n} -> llega arriba {got} veces")
config.ARM_WAVE_REPEATS = 3

print("\n=== Con ARM_WAVE_BOTH=true vuelve el izquierdo ===")
print("\n=== Sentido del brazo (ARM_INVERT_R) ===")
config.ARM_INVERT_R = False
der_normal, _ = correr()
config.ARM_INVERT_R = True
der_invertido, _ = correr()
print(f"    normal:     de {min(der_normal)} a {max(der_normal)}")
print(f"    invertido:  de {min(der_invertido)} a {max(der_invertido)}")
check(max(der_normal) >= 170 and min(der_normal) == 90,
      "sin invertir va de 90 hacia ARRIBA (90..180)")
check(min(der_invertido) <= 10 and max(der_invertido) == 90,
      "invertido va de 90 hacia el OTRO LADO (0..90)")
check(len(der_normal) == len(der_invertido),
      "el recorrido dura lo mismo, solo cambia el sentido")
check(der_normal[-1] == der_invertido[-1] == 90,
      "el reposo sigue siendo 90 en los dos (no hay que recalibrar)")
check(all(b == 180 - a for a, b in zip(der_normal, der_invertido)),
      "cada angulo es el espejo exacto del otro")
config.ARM_INVERT_R = False

config.ARM_WAVE_BOTH = True
der, izq = correr()
check(max(izq) >= 170, "el izquierdo sube a acompañar")
config.ARM_WAVE_BOTH = False

print()
if fallos:
    print(f"{len(fallos)} FALLOS:"); [print("  -",f) for f in fallos]; sys.exit(1)
print("Todo pasa.")
