"""InterruptListener (interrupt_listener.py): sobrevivir a un corte del mic.

El bug que se corrigió: si el micrófono se caía a mitad de una narración, la
escucha de "oye MECH" moría hasta la próxima narración. Ahora un
MicProcessCrashed se reabre a los 3 s y la escucha continúa.
"""
from __future__ import annotations

import time

import config
import stt
from conftest import esperar
from interrupt_listener import InterruptListener


def _arrancar(monkeypatch, record_fake):
    monkeypatch.setattr(stt, "record_until_silence", record_fake)
    monkeypatch.setattr(config, "VOICE_INTERRUPT_ENABLED", True)
    monkeypatch.setattr("interrupt_listener.time", time)  # sin cambios

    logs = []
    interrupciones = []
    listener = InterruptListener(
        on_interrupt=lambda t: interrupciones.append(t),
        log=lambda m, l="info": logs.append((l, m)),
    )
    return listener, logs, interrupciones


def test_el_corte_del_mic_no_mata_la_escucha(monkeypatch):
    llamadas = {"n": 0}

    def record_fake(**kw):
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            raise stt.MicProcessCrashed("El proceso del micrófono murió (código -6).")
        return None  # entrega la escucha normal (silencio) después

    listener, logs, _ = _arrancar(monkeypatch, record_fake)

    # Parche al sleep a 0 para que la prueba no espere 3 s reales.
    import interrupt_listener as il

    monkeypatch.setattr(il.time, "sleep", lambda s: None)

    assert listener.start(guard_text="") is True
    esperar(lambda: llamadas["n"] >= 2, timeout=5.0)
    listener.stop()

    assert llamadas["n"] >= 2, "después del crash la escucha siguió reintentando"
    assert any("reabro en 3 s" in m for _, m in logs), logs


def test_sin_mic_la_narracion_sigue_y_se_avisa(monkeypatch):
    def record_fake(**kw):
        raise stt.MicProcessCrashed("El proceso del micrófono murió (código -6).")

    listener, logs, interrupciones = _arrancar(monkeypatch, record_fake)
    import interrupt_listener as il

    monkeypatch.setattr(il.time, "sleep", lambda s: None)

    listener.start(guard_text="")
    esperar(lambda: any("reabro en 3 s" in m for _, m in logs), timeout=5.0)
    listener.stop()
    assert interrupciones == []  # nunca se disparó una interrupción falsa


def test_otros_fallos_siguen_siendo_no_fatales(monkeypatch):
    def record_fake(**kw):
        raise RuntimeError("micrófono ocupado por otro hilo")

    listener, logs, interrupciones = _arrancar(monkeypatch, record_fake)
    listener.start(guard_text="")
    esperar(
        lambda: any("Sin escucha de interrupción" in m for _, m in logs),
        timeout=5.0,
    )
    listener.stop()
    assert interrupciones == []