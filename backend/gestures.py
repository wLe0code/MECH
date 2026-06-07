"""Traducción de gestos abstractos (de Claude) a comandos del Arduino.

Centralizar esto aquí significa que si cambias el hardware (más servos,
ángulos diferentes), solo tocas este archivo, no llm.py ni main.py.

IMPORTANTE — los gestos NO se enciman. Cada gesto corre en un hilo, pero
un lock global garantiza que solo haya UNO activo a la vez. Si llega un
gesto nuevo mientras otro está en curso, el nuevo se ignora (en vez de
mandar ángulos encimados al mismo servo, que hacía que el brazo se
sacudiera sin parar). Como execute_plan llama un gesto por segmento y los
segmentos pueden venir muy rápido (sobre todo en modo ahorro de TTS),
sin este lock los brazos temblaban.
"""

from __future__ import annotations

import threading
import time

from arduino_link import ArduinoLink

# Solo un gesto a la vez. Si está tomado, los gestos nuevos se descartan.
_gesture_lock = threading.Lock()


def perform(link: ArduinoLink, gesture: str) -> None:
    """Ejecuta un gesto de forma no bloqueante y sin encimarse con otro."""

    def _run():
        # Si ya hay un gesto en curso, no encimamos: lo dejamos pasar.
        if not _gesture_lock.acquire(blocking=False):
            return
        try:
            if gesture == "neutral":
                link.arm("L", 90)
                link.arm("R", 90)
            elif gesture == "excited":
                link.arm("L", 40)
                link.arm("R", 40)
            elif gesture == "thoughtful":
                link.arm("L", 110)
                link.arm("R", 90)
            elif gesture == "wave":
                # Saludo suave: 2 movimientos y vuelve al centro.
                for angle in (60, 120, 90):
                    link.arm("R", angle)
                    time.sleep(0.35)
            elif gesture == "point":
                link.arm("R", 30)
            elif gesture == "arms_open":
                link.arm("L", 20)
                link.arm("R", 20)
            else:
                # Gesto desconocido: posición neutral.
                link.arm("L", 90)
                link.arm("R", 90)
        finally:
            _gesture_lock.release()

    threading.Thread(target=_run, daemon=True).start()
