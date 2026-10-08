"""Mide cuando la camara da por LLEGADA a una persona (y cuando no).

Por que existe: MECH saludaba a veces sin nadie delante. Bastaba UN
fotograma con "cara" (un reflejo, una sombra) para avisar de una llegada.
Ahora la cara tiene que mantenerse GREETING_CONFIRM_SECONDS; aqui se le
pasan a la pieza real (vision._Llegada) fotogramas de mentira con un reloj
de mentira y se cuenta cuantas llegadas da.

    python scripts/probar_llegada.py

Sale 1 si algo falla. No necesita camara, OpenCV ni claves de API.
"""
import sys, types, os, random
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "backend"))
for k in ("ANTHROPIC_API_KEY", "ELEVENLABS_API_KEY", "GOOGLE_API_KEY"):
    os.environ.setdefault(k, "x")
try:
    import dotenv  # noqa: F401
except Exception:
    d = types.ModuleType("dotenv"); d.load_dotenv = lambda *a, **k: None
    sys.modules["dotenv"] = d

import config, vision

fallos = []
def check(c, m):
    print(("ok   " if c else "FALLA"), m)
    if not c: fallos.append(m)

def correr(caras, fps=10.0, confirmar=1.0):
    """caras = lista de True/False, un valor por fotograma.
    Devuelve [(segundo, aviso), ...] con los avisos que dio."""
    config.GREETING_CONFIRM_SECONDS = confirmar
    ll = vision._Llegada()
    avisos = []
    for i, hay in enumerate(caras):
        t = 100.0 + i / fps
        a = ll.update(hay, t)
        if a:
            avisos.append((round(i / fps, 2), a))
    return avisos

def cuenta(avisos, cual):
    return sum(1 for _, a in avisos if a == cual)

random.seed(7)

# --- Lo que NO debe saludar -------------------------------------------
# 1. Un fotograma suelto cada 30 s, durante 10 minutos.
caras = [(i % 300 == 0) for i in range(6000)]
a = correr(caras)
check(cuenta(a, "llego") == 0, "un fotograma falso cada 30 s (10 min): 0 llegadas -> %d" % cuenta(a, "llego"))
check(cuenta(a, "se_fue") == 0, "...y tampoco avisa de que 'se fue' alguien")
check(cuenta(correr(caras, confirmar=0), "llego") == 20,
      "con la confirmacion en 0 (lo de antes) esos mismos fotogramas dan 20 llegadas")

# 2. Un falso positivo que parpadea: 1 de cada 10 fotogramas, 5 minutos.
caras = [(i % 10 == 0) for i in range(3000)]
check(cuenta(correr(caras), "llego") == 0, "parpadeo de 1 de cada 10 fotogramas (5 min): 0 llegadas")

# 3. Rafagas de 3 fotogramas seguidos cada 5 s.
caras = [(i % 50 < 3) for i in range(3000)]
check(cuenta(correr(caras), "llego") == 0, "rafagas de 3 fotogramas cada 5 s (5 min): 0 llegadas")

# 4. Ruido al azar: 15 % de los fotogramas, 10 minutos.
caras = [random.random() < 0.15 for _ in range(6000)]
check(cuenta(correr(caras), "llego") == 0, "ruido al azar en el 15 % de los fotogramas (10 min): 0 llegadas")

# 5. La Pi se atasca: dos fotogramas con cara separados por 5 s no son 5 s de cara.
config.GREETING_CONFIRM_SECONDS = 1.0
ll = vision._Llegada()
r = [ll.update(True, 0.0), ll.update(True, 5.0)]
check(r == [None, None], "un atasco de 5 s entre dos fotogramas no cuenta como 5 s de cara")

# --- Lo que SI debe saludar -------------------------------------------
# 6. Una persona que se queda delante.
a = correr([True] * 100)
check(cuenta(a, "llego") == 1 and a[0][0] <= 1.1, "persona delante: 1 llegada, al segundo -> %s" % a[:1])

# 7. Cara real que el detector pierde 3 de cada 10 fotogramas.
caras = [(i % 10) not in (2, 5, 8) for i in range(100)]
a = correr(caras)
check(cuenta(a, "llego") == 1 and a[0][0] <= 2.5, "cara real vista el 70 %% del tiempo: llega en %.1f s" % (a[0][0] if a else -1))

# 8. Camara lenta (4 fotogramas por segundo).
a = correr([True] * 40, fps=4.0)
check(cuenta(a, "llego") == 1 and a[0][0] <= 1.5, "a 4 fotogramas por segundo: llega en %.1f s" % (a[0][0] if a else -1))

# 9. Llega, se queda 10 s y se va: una llegada y UNA salida, a los 1.5 s de irse.
a = correr([True] * 100 + [False] * 100)
check([x for _, x in a] == ["llego", "se_fue"], "llega y se va: %s" % a)
check(len(a) == 2 and 11.4 <= a[1][0] <= 11.8, "la salida se avisa ~1.5 s despues de perder la cara")

# 10. La misma persona gira la cabeza 1 s: no es salida ni llegada nueva.
a = correr([True] * 50 + [False] * 10 + [True] * 50)
check([x for _, x in a] == ["llego"], "girar la cabeza 1 s no cuenta como irse y volver: %s" % a)

# 11. Dos visitantes, uno tras otro, con la camara vacia 30 s en medio.
a = correr([True] * 50 + [False] * 300 + [True] * 50)
check([x for _, x in a] == ["llego", "se_fue", "llego"], "dos visitantes seguidos: dos llegadas")

# 12. Pausa al narrar: reset() olvida sin avisar y luego hay que confirmar de nuevo.
config.GREETING_CONFIRM_SECONDS = 1.0
ll = vision._Llegada()
for i in range(20): ll.update(True, i / 10.0)
ll.reset()
check(not ll.present and not ll.confirmed, "reset() deja la camara 'sin nadie'")
check(ll.update(True, 2.1) is None, "tras la pausa, un fotograma suelto no vuelve a ser una llegada")

print()
if fallos:
    print("FALLARON %d:" % len(fallos))
    for f in fallos: print("  -", f)
    sys.exit(1)
print("TODO BIEN")
