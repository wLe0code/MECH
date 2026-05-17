"""Traducción de gestos abstractos (de Claude) a comandos del Arduino.

Centralizar esto aquí significa que si cambias el hardware (más servos,
ángulos diferentes), solo tocas este archivo, no llm.py ni main.py.
"""

from __future__ import annotations

import threading
import time

from arduino_link import ArduinoLink


def perform(link: ArduinoLink, gesture: str) -> None:
    """Ejecuta un gesto de forma no bloqueante."""

    def _run():
        if gesture == "neutral":
            link.head(90, 90)
            link.arm("L", 90)
            link.arm("R", 90)
        elif gesture == "excited":
            link.arm("L", 30)
            link.arm("R", 30)
            link.head(90, 60)
        elif gesture == "thoughtful":
            link.head(70, 100)
            link.arm("L", 110)
            link.arm("R", 90)
        elif gesture == "wave":
            for angle in (40, 140, 40, 140, 90):
                link.arm("R", angle)
                time.sleep(0.3)
        elif gesture == "point":
            link.arm("R", 20)
            link.head(110, 80)
        elif gesture == "arms_open":
            link.arm("L", 10)
            link.arm("R", 10)
            link.head(90, 80)
        else:
            link.set_mode("IDLE")

    threading.Thread(target=_run, daemon=True).start()
