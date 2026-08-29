"""Escuchar "oye MECH" MIENTRAS MECH narra, para poder cortarlo.

Por qué es un módulo aparte y no el bucle de voz de siempre: mientras MECH
presenta, el bucle principal está ocupado ejecutando el plan, y el micrófono
está oyendo sobre todo... al propio MECH por el parlante. Así que aquí se
escucha con una regla muy estricta:

- Solo importa la frase de interrupción (`VOICE_INTERRUPT_PHRASES`, en los dos
  idiomas). CUALQUIER otra cosa que se oiga durante la narración se descarta
  sin más: casi siempre es el eco del parlante.
- Las grabaciones se cortan a `INTERRUPT_MAX_UTTERANCE` segundos, porque la
  frase dura ~1 s y así se revisa enseguida.
- Si la propia narración contiene la frase (Claude escribió "oye, MECH..."),
  el listener NI SE ARRANCA: MECH se interrumpiría a sí mismo.

El micrófono del proyecto es de solapa e inalámbrico (Steren MIC-9010), así
que la voz del visitante entra bastante más fuerte que el parlante — que es
lo que hace viable esto.
"""

from __future__ import annotations

import threading
from typing import Callable

import config
import stt
import voice_phrases

# Segundos que espera voz cada vuelta antes de reintentar. No es un límite
# real: si no oye nada, simplemente vuelve a empezar.
_ESPERA = 10.0


class InterruptListener:
    """Hilo que avisa cuando alguien dice "oye MECH" durante la narración."""

    def __init__(
        self,
        on_interrupt: Callable[[str], None],
        log: Callable[[str, str], None] | None = None,
    ) -> None:
        self._on_interrupt = on_interrupt
        self._log = log or (lambda m, l="info": print(f"[{l}] {m}"))
        self._cancel: threading.Event | None = None
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, guard_text: str = "") -> bool:
        """Arranca la escucha. Devuelve False si se decidió no escuchar.

        `guard_text`: el guion que MECH va a narrar. Si ese texto contiene la
        frase de interrupción, no se escucha (se cortaría a sí mismo al oír
        su propio eco).
        """
        if not config.VOICE_INTERRUPT_ENABLED:
            return False
        if self.running:
            return True
        if guard_text and voice_phrases.is_interrupt(guard_text):
            self._log(
                "No escucho interrupciones en este guion: contiene la propia "
                "frase para interrumpir.",
                "warn",
            )
            return False

        cancel = threading.Event()
        self._cancel = cancel

        def _run() -> None:
            while not cancel.is_set():
                try:
                    audio = stt.record_until_silence(
                        max_seconds=_ESPERA,
                        cancel_event=cancel,
                        max_utterance_seconds=config.INTERRUPT_MAX_UTTERANCE,
                    )
                except Exception as e:
                    # Típico: el micrófono ya está ocupado por otro hilo.
                    # No es fatal — MECH sigue narrando, solo sin interrupción.
                    self._log(f"Sin escucha de interrupción: {e}", "warn")
                    return
                if cancel.is_set():
                    return
                if audio is None:
                    continue
                try:
                    texto = stt.transcribe(audio)
                except Exception as e:
                    self._log(f"Interrupción: falló la transcripción ({e})", "warn")
                    continue
                if cancel.is_set():
                    return
                if texto and voice_phrases.is_interrupt(texto):
                    try:
                        self._on_interrupt(texto)
                    finally:
                        return  # ya interrumpimos: este hilo termina

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        """Corta la escucha (no espera al hilo: suelta el micrófono solo)."""
        if self._cancel is not None:
            self._cancel.set()
        self._cancel = None
        self._thread = None
