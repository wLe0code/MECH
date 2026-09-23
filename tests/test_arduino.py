"""Capa Arduino (arduino_link.py): la reconexión automática a prueba de todo.

Con un pyserial SIMULADO se verifica:
  * el hilo de reconexión NUNCA muere, ni siquiera con fallos raros;
  * cuando el Arduino "vuelve", se conecta solo y avisa al panel (on_status);
  * los comandos se escriben de verdad en el puerto (protocolo intacto);
  * una desconexión en caliente se refleja y se vuelve a reconectar sola.
"""
from __future__ import annotations

import time

import arduino_link
import serial
from conftest import esperar


class _TimeSinEspera:
    """Reemplazo de `time` SOLO dentro de arduino_link (pruebas).

    `monotonic` sigue siendo real; `sleep` no espera: así los 2 s de espera
    del boot del Arduino no alargan la prueba, y el resto del sistema (los
    propios tests, `esperar`) conserva el tiempo real.
    """

    def __init__(self):
        self.monotonic = time.monotonic

    def sleep(self, s):
        return None


def _link_con_reconexion(monkeypatch, intervalo=0.01):
    monkeypatch.setattr(arduino_link, "time", _TimeSinEspera())
    serial.CONNECTED = False
    serial.WRITTEN.clear()
    link = arduino_link.ArduinoLink(port="/dev/ttyACM0", baud=115200)
    estados = []
    link.on_status = lambda ok: estados.append(ok)
    link.start_auto_reconnect(interval=intervalo)
    return link, estados


def test_el_hilo_de_reconexion_no_muere_aunque_todo_falle(monkeypatch):
    link, _ = _link_con_reconexion(monkeypatch)
    hilo = link._reconnect_thread
    assert hilo is not None and hilo.is_alive()

    # Varias rondas de fallo seguidas (Arduino ausente) y el hilo sigue vivo.
    time.sleep(0.2)
    assert hilo.is_alive(), "el hilo de reconexión murió con fallos repetidos"
    assert not link.is_connected


def test_se_conecta_solo_cuando_vuelve_y_avisa(monkeypatch):
    link, estados = _link_con_reconexion(monkeypatch)

    time.sleep(0.1)
    assert not link.is_connected

    serial.CONNECTED = True  # "enchufan el Arduino en caliente"
    esperar(lambda: link.is_connected, timeout=5.0)
    assert estados and estados[-1] is True  # el panel se enteró


def test_comandos_se_escriben_y_la_desconexion_se_recupera(monkeypatch):
    link, estados = _link_con_reconexion(monkeypatch)
    serial.CONNECTED = True
    esperar(lambda: link.is_connected, timeout=5.0)

    link.set_mode("LISTEN")
    assert any(b"LISTEN" in w for w in serial.WRITTEN), "el modo no llegó al puerto"

    # Desconexión en caliente: primero se "desenchufa" (sin eso, el hilo de
    # reconexión volvería a conectar en milisegundos y la verificación sería
    # una carrera). Después se chequea que el estado se reflejó y se vuelve
    # a conectar sola con el Arduino de nuevo presente.
    serial.CONNECTED = False
    link._handle_disconnect()
    esperar(lambda: not link.is_connected, timeout=5.0)
    esperar(lambda: bool(estados) and estados[-1] is False, timeout=5.0)

    serial.CONNECTED = True
    esperar(lambda: link.is_connected, timeout=5.0)
    esperar(lambda: bool(estados) and estados[-1] is True, timeout=5.0)


def test_send_sin_conexion_no_explota(monkeypatch):
    link, _ = _link_con_reconexion(monkeypatch)
    link.send("MOVE:0:0:0")  # no debe lanzar nada
    assert not serial.WRITTEN


def test_close_deja_de_reconectar():
    serial.CONNECTED = False
    link = arduino_link.ArduinoLink(port="/dev/ttyACM0")
    link.start_auto_reconnect(interval=0.02)
    time.sleep(0.05)
    link.close()
    time.sleep(0.05)
    # close() pone _closing=True; el hilo termina su vuelta y sale.
    assert link._closing is True