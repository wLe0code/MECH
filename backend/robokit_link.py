"""Control de movimiento del RoboKit RS por 'bus de pines' GPIO.

Por qué así (y no serial/USB):
- El RoboKit RS solo corre programas hechos en Rogic; no acepta comandos en
  vivo por USB ni tiene bloque de "recibir serial". Pero SÍ puede LEER pines
  digitales en un bucle (bloque `pin [n] detected?`).
- Entonces la Pi le "habla" poniendo pines en alto/bajo, y un programa Rogic
  en el RoboKit lee esos pines y mueve los motores.

Protocolo (un pin activo a la vez = un comando):
    pin FWD  en alto  -> adelante
    pin LEFT en alto  -> girar izquierda
    pin RIGHT en alto -> girar derecha
    ninguno en alto   -> parar

Cableado (GPIO BCM de la Pi -> entrada del RoboKit, configurable en .env):
    ROBOKIT_PIN_FWD   (GPIO17, físico 11) -> señal pin 2 del RoboKit
    ROBOKIT_PIN_LEFT  (GPIO27, físico 13) -> señal pin 3 del RoboKit
    ROBOKIT_PIN_RIGHT (GPIO22, físico 15) -> señal pin 4 del RoboKit
    GND de la Pi      (físico 9)          -> GND del RoboKit   (tierra común)

Requisitos:
- gpiozero (viene en Raspberry Pi OS). En otra máquina, get_link() falla con
  un mensaje claro en vez de romper el import.
- El programa Rogic correspondiente debe estar corriendo en el RoboKit.
"""

from __future__ import annotations

import os
import sys

# Permite ejecutar/importar sin definir PYTHONPATH.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config

try:
    from gpiozero import DigitalOutputDevice
    _HAS_GPIO = True
    _GPIO_ERR = None
except Exception as exc:  # noqa: BLE001 - en dev (Windows) no hay GPIO
    _HAS_GPIO = False
    _GPIO_ERR = exc


class RoboKitLink:
    """Maneja los pines GPIO que le indican el movimiento al RoboKit."""

    def __init__(self, pin_fwd: int, pin_left: int, pin_right: int) -> None:
        self._fwd = DigitalOutputDevice(pin_fwd)
        self._left = DigitalOutputDevice(pin_left)
        self._right = DigitalOutputDevice(pin_right)
        self.stop()

    def _set(self, fwd: int, left: int, right: int) -> None:
        self._fwd.value = fwd
        self._left.value = left
        self._right.value = right

    def forward(self) -> None:
        self._set(1, 0, 0)

    def turn_left(self) -> None:
        self._set(0, 1, 0)

    def turn_right(self) -> None:
        self._set(0, 0, 1)

    def stop(self) -> None:
        self._set(0, 0, 0)

    def command(self, name: str) -> None:
        """Ejecuta un comando por nombre: adelante | izquierda | derecha | parar."""
        actions = {
            "adelante": self.forward,
            "forward": self.forward,
            "izquierda": self.turn_left,
            "left": self.turn_left,
            "derecha": self.turn_right,
            "right": self.turn_right,
            "parar": self.stop,
            "stop": self.stop,
        }
        action = actions.get(name.strip().lower())
        if action is None:
            raise ValueError(f"Comando de movimiento desconocido: {name!r}")
        action()

    def close(self) -> None:
        self.stop()
        self._fwd.close()
        self._left.close()
        self._right.close()


_link: RoboKitLink | None = None


def get_link() -> RoboKitLink:
    """Devuelve el singleton del control de movimiento (lo crea la 1ª vez)."""
    global _link
    if _link is None:
        if not _HAS_GPIO:
            raise RuntimeError(
                f"gpiozero no disponible ({_GPIO_ERR}). "
                "Este módulo solo funciona en la Raspberry Pi."
            )
        _link = RoboKitLink(
            config.ROBOKIT_PIN_FWD,
            config.ROBOKIT_PIN_LEFT,
            config.ROBOKIT_PIN_RIGHT,
        )
    return _link


# Prueba rápida desde la terminal:
#   cd ~/MECH/backend && python robokit_link.py
# (robot levantado, ruedas al aire, y el programa Rogic corriendo)
if __name__ == "__main__":
    import time

    link = get_link()
    secuencia = [
        ("adelante", 2),
        ("parar", 1),
        ("izquierda", 2),
        ("parar", 1),
        ("derecha", 2),
        ("parar", 1),
    ]
    try:
        for cmd, secs in secuencia:
            print(f"{cmd} ({secs}s)")
            link.command(cmd)
            time.sleep(secs)
    finally:
        link.stop()
        print("Listo.")
