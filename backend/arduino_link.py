"""Capa de comunicación con el Arduino.

Protocolo de texto sobre serial, líneas terminadas en '\\n', a 115200 baud.
Las respuestas del Arduino se imprimen como log; no las parseamos para
mantener el código simple.

Comandos soportados (los implementa el firmware mech_controller.ino):

    MODE:AUTO            Estado "vivo" en reposo (no conduce solo).
    MODE:IDLE            Pose neutra.
    MODE:LISTEN          Quieto, escuchando (motores detenidos).
    MODE:SPEAK           Hablando (los gestos de brazos los dispara la Pi).
    MODE:STOP            Detiene todo (ruedas, servos congelados).

    HEAD:<pan>:<tilt>    Ignorado por el firmware actual (el robot no tiene
                         cabeza física); se mantiene por compatibilidad.
    ARM:L:<angle>        Brazo izquierdo (0–180).
    ARM:R:<angle>        Brazo derecho (0–180).
    MOVE:<vx>:<vy>:<w>   Velocidad omnidireccional. vx,vy,w en [-100, 100].
                         vx=adelante/atrás, vy=lateral, w=rotación.
    STOP                 Atajo para MOVE:0:0:0.
"""

from __future__ import annotations

import threading
import time

import serial

import config


class ArduinoLink:
    def __init__(self, port: str | None = None, baud: int | None = None) -> None:
        self.port = port or config.ARDUINO_PORT
        self.baud = baud or config.ARDUINO_BAUD
        self._ser: serial.Serial | None = None
        self._reader_thread: threading.Thread | None = None
        self._stop_reader = threading.Event()

    def connect(self) -> None:
        print(f"[Arduino] Abriendo {self.port} @ {self.baud}...")
        self._ser = serial.Serial(self.port, self.baud, timeout=1)
        # Arduino se resetea al abrir el puerto; espera el boot.
        time.sleep(2.0)
        self._stop_reader.clear()
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()
        print("[Arduino] Conectado.")

    def _reader_loop(self) -> None:
        assert self._ser is not None
        while not self._stop_reader.is_set():
            try:
                line = self._ser.readline().decode("utf-8", errors="ignore").strip()
                if line:
                    print(f"[Arduino] {line}")
            except serial.SerialException:
                break

    def send(self, command: str) -> None:
        if self._ser is None or not self._ser.is_open:
            print(f"[Arduino] (no conectado) {command}")
            return
        line = command.strip() + "\n"
        self._ser.write(line.encode("utf-8"))
        self._ser.flush()

    # --- Helpers de alto nivel ---

    def set_mode(self, mode: str) -> None:
        self.send(f"MODE:{mode}")

    def head(self, pan: int, tilt: int) -> None:
        pan = max(0, min(180, int(pan)))
        tilt = max(0, min(180, int(tilt)))
        self.send(f"HEAD:{pan}:{tilt}")

    def arm(self, side: str, angle: int) -> None:
        angle = max(0, min(180, int(angle)))
        side = side.upper()
        assert side in ("L", "R")
        self.send(f"ARM:{side}:{angle}")

    def move(self, vx: int, vy: int, w: int) -> None:
        vx = max(-100, min(100, int(vx)))
        vy = max(-100, min(100, int(vy)))
        w = max(-100, min(100, int(w)))
        self.send(f"MOVE:{vx}:{vy}:{w}")

    def stop_motors(self) -> None:
        self.send("STOP")

    def close(self) -> None:
        self._stop_reader.set()
        if self._ser is not None and self._ser.is_open:
            try:
                self.stop_motors()
                self.set_mode("IDLE")
            finally:
                self._ser.close()


# Instancia singleton para uso simple.
_link: ArduinoLink | None = None


def get_link() -> ArduinoLink:
    global _link
    if _link is None:
        _link = ArduinoLink()
        try:
            _link.connect()
        except (serial.SerialException, FileNotFoundError) as e:
            print(f"[Arduino] No se pudo conectar ({e}). Funcionando sin robot.")
    return _link
