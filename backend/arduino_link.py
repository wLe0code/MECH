"""Capa de comunicación con el Arduino.

Protocolo de texto sobre serial, líneas terminadas en '\\n', a 115200 baud.
Las respuestas del Arduino se imprimen como log; no las parseamos para
mantener el código simple.

Robustez de conexión:
- Si el puerto configurado (ARDUINO_PORT) no existe, se buscan puertos que
  parezcan un Arduino (descripción "Arduino", "CH340", "ACM", etc.).
- Un hilo de fondo reintenta la conexión cada pocos segundos si el Arduino
  está desconectado (o se desconectó en caliente). Así da igual el orden en
  que se enchufen las cosas: el server puede arrancar sin Arduino y este se
  conecta solo cuando aparece.
- `on_status(conectado: bool)` permite a mech_app reflejar el estado en el
  panel en vivo.

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
    LED:<patrón>         Aro de LEDs estilo Alexa: OFF | IDLE | WAKE |
                         LISTEN | THINK | SPEAK | ERR.
"""

from __future__ import annotations

import threading
import time
from typing import Callable

import serial
from serial.tools import list_ports

import config

# Pistas para reconocer un Arduino entre los puertos serie del sistema.
_PORT_HINTS = ("arduino", "ch340", "ch341", "usb serial", "ttyacm", "usb-serial")


def _autodetect_port() -> str | None:
    """Busca un puerto que parezca un Arduino. None si no hay candidatos."""
    try:
        ports = list(list_ports.comports())
    except Exception:
        return None
    for p in ports:
        desc = f"{p.device} {p.description or ''} {p.manufacturer or ''}".lower()
        if any(h in desc for h in _PORT_HINTS):
            return p.device
    return None


class ArduinoLink:
    def __init__(self, port: str | None = None, baud: int | None = None) -> None:
        self.port = port or config.ARDUINO_PORT
        self.baud = baud or config.ARDUINO_BAUD
        self._ser: serial.Serial | None = None
        self._reader_thread: threading.Thread | None = None
        self._stop_reader = threading.Event()
        self._reconnect_thread: threading.Thread | None = None
        self._closing = False
        self._write_lock = threading.Lock()
        # Callback opcional: se llama con True/False al conectar/desconectar.
        self.on_status: Callable[[bool], None] | None = None
        # --- Odómetro adelante/atrás (aprox., por tiempo) -----------------
        # Integra vx · tiempo para saber cuánto se ha desplazado el robot
        # desde su punto de inicio, y así poder VOLVER antes de proyectar
        # (que la proyección no quede desfasada). Unidades: %velocidad · s.
        self._odo_lock = threading.Lock()
        self._odo_net = 0.0
        self._odo_vx = 0
        self._odo_t = time.monotonic()
        # Último MODE enviado. Sirve para NO reenviar el mismo modo una y otra
        # vez: en el firmware, MODE:LISTEN/SPEAK/STOP llaman a stopAllMotors(),
        # y el bucle de voz manda MODE:LISTEN en cada vuelta (cada 0.3 s
        # mientras narra). Eso MATABA cualquier movimiento de ruedas antes de
        # que se notara. Ver el comentario de set_mode().
        self._mode: str | None = None

    def _odo_update(self, new_vx: int) -> None:
        """Cierra el tramo actual del odómetro y arranca uno nuevo."""
        with self._odo_lock:
            now = time.monotonic()
            self._odo_net += self._odo_vx * (now - self._odo_t)
            self._odo_t = now
            self._odo_vx = new_vx

    def net_forward(self) -> float:
        """Desplazamiento neto adelante(+)/atrás(−) en unidades %vel·s."""
        with self._odo_lock:
            return self._odo_net + self._odo_vx * (time.monotonic() - self._odo_t)

    def reset_odometer(self) -> None:
        """Declara la posición actual como nuevo punto de inicio."""
        with self._odo_lock:
            self._odo_net = 0.0
            self._odo_t = time.monotonic()

    @property
    def is_connected(self) -> bool:
        return self._ser is not None and self._ser.is_open

    def _notify_status(self) -> None:
        if self.on_status is not None:
            try:
                self.on_status(self.is_connected)
            except Exception:
                pass

    def connect(self) -> None:
        """Intenta abrir el puerto configurado; si falla, autodetecta."""
        last_err: Exception | None = None
        candidates = [self.port]
        detected = _autodetect_port()
        if detected and detected not in candidates:
            candidates.append(detected)
        for port in candidates:
            try:
                print(f"[Arduino] Abriendo {port} @ {self.baud}...")
                self._ser = serial.Serial(port, self.baud, timeout=1)
                self.port = port
                break
            except (serial.SerialException, FileNotFoundError, OSError) as e:
                last_err = e
                self._ser = None
        if self._ser is None:
            raise last_err or serial.SerialException("Sin puertos candidatos")
        # Arduino se resetea al abrir el puerto; espera el boot.
        time.sleep(2.0)
        self._stop_reader.clear()
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()
        print(f"[Arduino] Conectado en {self.port}.")
        self._notify_status()

    def start_auto_reconnect(self, interval: float = 4.0) -> None:
        """Hilo de fondo que reintenta conectar mientras esté desconectado."""
        if self._reconnect_thread is not None and self._reconnect_thread.is_alive():
            return

        def _loop():
            while not self._closing:
                if not self.is_connected:
                    try:
                        self.connect()
                    except (serial.SerialException, FileNotFoundError, OSError):
                        pass  # sin Arduino todavía; reintentamos luego
                time.sleep(interval)

        self._reconnect_thread = threading.Thread(target=_loop, daemon=True)
        self._reconnect_thread.start()

    def _reader_loop(self) -> None:
        ser = self._ser
        if ser is None:
            return
        while not self._stop_reader.is_set():
            try:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if line:
                    print(f"[Arduino] {line}")
            except (serial.SerialException, OSError):
                # El Arduino se desenchufó en caliente.
                self._handle_disconnect()
                break

    def _handle_disconnect(self) -> None:
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None
        # El Arduino arranca en IDLE al reconectar: olvidamos el modo que
        # creíamos tener, para que el próximo set_mode() sí se envíe.
        self._mode = None
        print("[Arduino] Desconectado. Reintentando en segundo plano...")
        self._notify_status()

    def send(self, command: str) -> None:
        if not self.is_connected:
            print(f"[Arduino] (no conectado) {command}")
            return
        line = command.strip() + "\n"
        try:
            with self._write_lock:
                self._ser.write(line.encode("utf-8"))
                self._ser.flush()
        except (serial.SerialException, OSError):
            self._handle_disconnect()

    # --- Helpers de alto nivel ---

    def set_mode(self, mode: str, force: bool = False) -> None:
        """Cambia el modo del robot. **No reenvía el modo que ya está puesto.**

        Importa mucho: en el firmware, `MODE:LISTEN`, `MODE:SPEAK` y
        `MODE:STOP` llaman a `stopAllMotors()`. El bucle de voz manda
        `MODE:LISTEN` en cada vuelta, así que sin este filtro las ruedas se
        frenaban solas a los pocos milisegundos de arrancar (el giro de 180°
        y el `return_to_start` no llegaban a moverse). `force=True` lo manda
        igual: lo usa la reconexión, donde el Arduino se reinició y perdió
        el modo que tenía."""
        if not force and mode == self._mode:
            return
        self._mode = mode
        # El firmware detiene los motores al entrar a LISTEN/SPEAK/STOP:
        # reflejarlo en el odómetro.
        if mode in ("LISTEN", "SPEAK", "STOP"):
            self._odo_update(0)
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
        self._odo_update(vx)
        self.send(f"MOVE:{vx}:{vy}:{w}")

    def stop_motors(self) -> None:
        self._odo_update(0)
        self.send("STOP")

    def led(self, pattern: str) -> None:
        """Patrón del aro de LEDs (estilo Alexa). Ver firmware: OFF, IDLE,
        WAKE, LISTEN, THINK, SPEAK, ERR."""
        self.send(f"LED:{pattern.strip().upper()}")

    def close(self) -> None:
        self._closing = True
        self._stop_reader.set()
        if self._ser is not None and self._ser.is_open:
            try:
                self.stop_motors()
                self.led("OFF")
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
        except (serial.SerialException, FileNotFoundError, OSError) as e:
            print(f"[Arduino] No se pudo conectar ({e}). Reintentando en segundo plano.")
        # Pase lo que pase, dejamos el reintento automático corriendo: si el
        # Arduino aparece (o se reenchufa), se conecta solo.
        _link.start_auto_reconnect()
    return _link
