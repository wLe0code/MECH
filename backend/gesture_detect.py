"""Detector del gesto "67" — MECH lo imita cuando alguien lo hace ante la cámara.

Pedido del equipo (sep 2026): que MECH reconozca el gesto del "67" (el de los
videos que pasó el equipo) **y solo ese**, y lo devuelva con sus brazos.

## Qué gesto es

Los dos videos de referencia muestran lo mismo a dos escalas:

  - **Video 1** (como lo hará el visitante): manos abiertas a la altura de la
    cara, una sube mientras la otra baja, alternando rápido.
  - **Video 2** (como lo hace MECH): el mismo movimiento con los BRAZOS
    enteros — uno arriba y el otro abajo, alternando.

Lo que define al gesto no es la forma de la mano: es que haya **dos cosas
moviéndose en vertical, una a cada lado, en ANTIFASE** (cuando una sube, la
otra baja) y repitiéndolo varias veces. Eso es exactamente lo que se mide.

## Por qué NO se usa la cara como referencia

El primer intento anclaba dos zonas de búsqueda a los lados del rostro. No
sirve: medido sobre el video real del equipo, con las manos delante de la
cara el detector Haar de OpenCV **solo encuentra la cara en 1 de cada 45
fotogramas**. Anclarse ahí habría hecho que el gesto no se detectara casi
nunca. Tampoco se puede usar MediaPipe Pose: la Pi corre Python 3.13 y no
tiene wheels (ver backend/vision.py).

## Cómo funciona (solo OpenCV, barato)

Por cada fotograma, a 320x180 y en gris:

 1. Diferencia con el fotograma anterior -> máscara de MOVIMIENTO. Usar
    movimiento y no color hace que dé igual la luz del stand, el tono de
    piel o la ropa: el fondo quieto no aporta nada.
 2. Si se mueve muy poco en total, no hay nadie gesticulando: se ignora.
 3. El centro horizontal del movimiento (suavizado) parte la escena en
    IZQUIERDA y DERECHA. Se exige que las dos mitades tengan una cantidad
    de movimiento parecida (`GESTURE67_BALANCE`): saludar con UNA mano deja
    todo el movimiento de un lado y se descarta ahí mismo.
 4. De cada mitad se guarda la ALTURA media del movimiento (0 arriba,
    1 abajo).

Sobre la ventana de los últimos `GESTURE67_WINDOW` segundos se pide TODO
esto a la vez:

 - que cada lado recorra al menos `GESTURE67_MIN_AMPLITUDE` de la altura
   del cuadro (si no, es alguien quieto o un temblor);
 - que las dos alturas estén **en antifase**: correlación por debajo de
   `GESTURE67_MAX_CORR` (negativa). Éste es el filtro que de verdad
   distingue el gesto: levantar las dos manos a la vez da correlación
   POSITIVA y se rechaza;
 - que se hayan **alternado** al menos `GESTURE67_MIN_ALTERNATIONS` veces
   (cuántas veces cambia de lado cuál va más arriba), para que un cruce
   suelto no cuente.

Después de acertar espera `GESTURE67_COOLDOWN` segundos antes de volver a
mirar, para no encadenar imitaciones.

⚠️ **Los huecos NO borran la ventana.** En el punto más alto del gesto la
mano se frena un instante y ese fotograma puede quedar por debajo del
mínimo de movimiento. La primera versión limpiaba el historial ahí mismo y
nunca llegaba a juntar muestras suficientes. Ahora se toleran huecos cortos
(`_MAX_GAP_S`) y solo se empieza de cero tras una pausa de verdad.

Medido contra los dos videos del equipo (dispara en los dos) y contra cinco
negativos: quieto, saludar con una mano, las dos manos a la vez, manos en
horizontal y alguien que cruza caminando — ninguno dispara. Si se tocan los
umbrales, **volver a medir las dos listas**: aflojar para pillar un caso
rompe el otro lado enseguida. El script está en
`scripts/probar_gesto67.py`.
"""

from __future__ import annotations

import math
from collections import deque

import config

# Resolución de trabajo del detector. Es a propósito MÁS PEQUEÑA que la de la
# cámara: el gesto es un movimiento grande y burdo, y a 320x180 la diferencia
# de fotogramas cuesta una fracción de milisegundo en la Pi.
_W = 320
_H = 180
# Umbral de la diferencia entre fotogramas para contar un píxel como "se
# movió". Por debajo de ~15 empieza a entrar el ruido del sensor.
_DIFF_THRESHOLD = 18
# Cuánto puede durar un hueco sin señal antes de dar la ventana por rota.
# Ver el aviso del docstring: el gesto TIENE micro-pausas en cada extremo.
_MAX_GAP_S = 0.5
# Muestras mínimas en la ventana para que las cuentas signifiquen algo.
_MIN_SAMPLES = 8
# Píxeles mínimos en un lado para fiarse de su altura media.
_MIN_SIDE_PIXELS = 40


def _correlation(a: list[float], b: list[float]) -> float:
    """Correlación de Pearson entre dos series; 0.0 si alguna es plana.

    Es el corazón del detector: mide si las dos alturas van JUNTAS (positiva —
    las dos manos suben a la vez, no es el gesto) o AL REVÉS (negativa — una
    sube mientras la otra baja, sí lo es).
    """
    n = len(a)
    if n < 2:
        return 0.0
    ma = sum(a) / n
    mb = sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = sum((x - ma) ** 2 for x in a)
    db = sum((y - mb) ** 2 for y in b)
    den = math.sqrt(da * db)
    return num / den if den > 1e-9 else 0.0


class SixtySevenDetector:
    """Va comiendo fotogramas y avisa cuando ve el gesto del "67".

    Uso: `detector.feed(frame_bgr, time.monotonic())` por cada fotograma de la
    cámara. Devuelve True UNA vez, justo cuando reconoce el gesto.
    """

    def __init__(self) -> None:
        self._cv2 = None
        self._np = None
        self._prev = None                     # fotograma anterior, en gris
        self._split_x: float | None = None    # dónde parte izquierda/derecha
        self._samples: deque = deque()        # (t, altura_izq, altura_der)
        self._last_sample_t: float = 0.0
        self._last_fire: float = 0.0
        # Lo último que se midió, para poder enseñarlo en el panel aunque no
        # llegue a disparar: es lo que permite calibrar los umbrales viendo
        # números reales en vez de adivinando.
        self.debug: dict = {}

    def reset(self) -> None:
        """Olvida lo visto (al encender/apagar la visión, o tras disparar)."""
        self._prev = None
        self._split_x = None
        self._samples.clear()
        self.debug = {}

    # ------------------------------------------------------------------

    def _lazy_imports(self) -> bool:
        """cv2/numpy se importan tarde, igual que en vision.py: sin ellos el
        server tiene que arrancar igual."""
        if self._cv2 is not None:
            return True
        try:
            import cv2
            import numpy
        except ImportError:
            return False
        self._cv2 = cv2
        self._np = numpy
        return True

    def _motion_heights(self, frame_bgr):
        """Altura media del movimiento en cada mitad, o None si no hay señal.

        Devuelve `(altura_izquierda, altura_derecha)` en 0..1, donde 0 es
        arriba del cuadro y 1 abajo.
        """
        cv2, np = self._cv2, self._np
        gris = cv2.cvtColor(cv2.resize(frame_bgr, (_W, _H)), cv2.COLOR_BGR2GRAY)
        # El desenfoque quita el ruido fino del sensor, que si no se cuela
        # como "movimiento" repartido por todo el cuadro.
        gris = cv2.GaussianBlur(gris, (5, 5), 0)
        anterior, self._prev = self._prev, gris
        if anterior is None:
            return None

        diff = cv2.absdiff(gris, anterior)
        _, mascara = cv2.threshold(diff, _DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)
        # Apertura: borra puntos sueltos y deja los bultos (manos, brazos).
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

        ys, xs = np.nonzero(mascara)
        total = len(xs)
        if total < config.GESTURE67_MIN_MOTION * _W * _H:
            return None  # nadie se está moviendo lo suficiente

        # El centro del movimiento sigue a la persona (suavizado: si no, salta
        # de un lado a otro cuando una mano se mueve más que la otra).
        centro = float(xs.mean())
        self._split_x = (centro if self._split_x is None
                         else self._split_x * 0.7 + centro * 0.3)

        izq = xs < self._split_x
        n_izq = int(izq.sum())
        n_der = total - n_izq
        if n_izq < _MIN_SIDE_PIXELS or n_der < _MIN_SIDE_PIXELS:
            return None
        # Equilibrio: saludar con UNA mano pone casi todo el movimiento de un
        # lado. El "67" mueve las dos, así que los dos lados pesan parecido.
        if min(n_izq, n_der) < config.GESTURE67_BALANCE * max(n_izq, n_der):
            return None

        return float(ys[izq].mean()) / _H, float(ys[~izq].mean()) / _H

    def feed(self, frame_bgr, now: float) -> bool:
        """Procesa un fotograma. True SOLO al reconocer el gesto."""
        if not config.GESTURE67_ENABLED:
            return False
        if not self._lazy_imports():
            return False
        if now - self._last_fire < config.GESTURE67_COOLDOWN:
            # Recién imitado: ni miramos. El fotograma anterior se descarta
            # para no arrancar con una diferencia enorme al volver.
            self._prev = None
            return False

        alturas = self._motion_heights(frame_bgr)
        if alturas is None:
            # Hueco. NO se borra la ventana salvo que la pausa sea larga: en
            # cada extremo del gesto la mano se frena un instante.
            if self._samples and now - self._last_sample_t > _MAX_GAP_S:
                self._samples.clear()
            return False

        self._samples.append((now, alturas[0], alturas[1]))
        self._last_sample_t = now
        ventana = max(0.5, config.GESTURE67_WINDOW)
        while self._samples and now - self._samples[0][0] > ventana:
            self._samples.popleft()
        if len(self._samples) < _MIN_SAMPLES:
            return False

        izq = [s[1] for s in self._samples]
        der = [s[2] for s in self._samples]
        amp_izq = max(izq) - min(izq)
        amp_der = max(der) - min(der)
        corr = _correlation(izq, der)
        # Cuántas veces se intercambiaron: cambios de signo de (izq - der).
        resta = [a - b for a, b in zip(izq, der)]
        alternancias = sum(
            1 for i in range(1, len(resta)) if (resta[i - 1] < 0) != (resta[i] < 0)
        )

        self.debug = {
            "amp_izq": round(amp_izq, 3),
            "amp_der": round(amp_der, 3),
            "correlacion": round(corr, 2),
            "alternancias": alternancias,
            "muestras": len(self._samples),
        }

        if (
            amp_izq >= config.GESTURE67_MIN_AMPLITUDE
            and amp_der >= config.GESTURE67_MIN_AMPLITUDE
            and corr <= config.GESTURE67_MAX_CORR
            and alternancias >= config.GESTURE67_MIN_ALTERNATIONS
        ):
            self._last_fire = now
            self._samples.clear()
            return True
        return False
