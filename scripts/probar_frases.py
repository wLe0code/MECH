"""Comprueba las frases de mando de MECH contra los dos lados a la vez.

Por qué existe: el matcher de `backend/voice_phrases.py` perdona errores de
Whisper a propósito, y cada vez que se afloja para pillar un caso que falla
empieza a disparar donde no debe. Las dos listas van juntas para que ese
equilibrio se vea de un vistazo:

  - COMANDOS: lo que un visitante diría, incluidas transcripciones
    deformadas reales del evento. Debe reconocerse.
  - STAND: frases normales de una conversación de stand. NO debe reconocerse
    ninguna como comando.

    python scripts/probar_frases.py

Sale 1 si algo falla. No necesita hardware ni claves de API.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import voice_phrases as vp  # noqa: E402


def _clasificar(texto: str) -> str:
    """La ÚNICA etiqueta que le corresponde, en el mismo orden que el bucle
    de voz de server.py. El orden importa: "desactiva el modo traductor"
    contiene "modo traductor"."""
    if vp.is_sleep_any(texto):
        return "reposo"
    if vp.is_translate_stop(texto):
        return "trad-off"
    if vp.is_translate_on(texto):
        return "trad-on"
    if vp.is_translate(texto):
        return "trad-una"
    if vp.is_trivia_stop(texto):
        return "trivia-off"
    if vp.is_trivia(texto):
        return "trivia"
    if vp.is_interrupt(texto):
        return "interrumpe"
    if vp.is_advance(texto):
        return "avanza"
    if vp.is_retreat(texto):
        return "retrocede"
    if vp.is_look_outward(texto):
        return "afuera"
    if vp.is_back_to_projection(texto):
        return "proyectar"
    if vp.is_play_marketing(texto):
        return "marketing"
    if vp.wake_language(texto):
        return "despierta:" + vp.wake_language(texto)
    return "nada"


# (frase, etiqueta esperada)
COMANDOS: list[tuple[str, str]] = [
    # --- Trivia (el juego de preguntas) ---
    ("juguemos una trivia", "trivia"),
    ("quiero jugar la trivia", "trivia"),
    ("empieza la trivia", "trivia"),
    ("modo trivia", "trivia"),
    ("hagamos una trivia", "trivia"),
    ("let's play a trivia", "trivia"),
    ("vamos jogar o quiz", "trivia"),
    # Salir se mira ANTES que entrar: "ya no quiero jugar" lleva "jugar".
    ("deja la trivia", "trivia-off"),
    ("sal de la trivia", "trivia-off"),
    ("para la trivia", "trivia-off"),
    ("ya no quiero jugar", "trivia-off"),
    ("stop the trivia", "trivia-off"),
    # --- Despertar, en los cuatro idiomas ---
    ("ok MECH", "despierta:es"),
    ("Okay, mech.", "despierta:es"),
    ("Despierta MECH", "despierta:es"),
    ("wake up MECH", "despierta:en"),
    ("bonjour MECH", "despierta:fr"),
    ("bom dia MECH", "despierta:pt"),
    # --- Reposo. El equipo reportó que a veces NO lo dormía ---
    ("Duérmete, MECH.", "reposo"),
    ("MECH, duérmete", "reposo"),
    ("Dormite MECH", "reposo"),
    ("Vete a dormir, MECH", "reposo"),
    ("Ponte a dormir, MECH", "reposo"),
    ("A dormir, MECH", "reposo"),
    ("Duerme, MECH.", "reposo"),
    ("Modo reposo", "reposo"),
    ("Para de escuchar", "reposo"),
    ("Adiós MECH", "reposo"),
    ("Go to sleep", "reposo"),
    ("Bonne nuit mech", "reposo"),
    ("Boa noite mech", "reposo"),
    # --- Traductor: una frase / continuo / apagar ---
    ("Traduce MECH", "trad-una"),
    ("Trasluce mech", "trad-una"),          # error real de Whisper
    ("Traduce MECH del inglés al portugués", "trad-una"),
    ("Activa modo traductor", "trad-on"),
    ("Activa el modo traductor", "trad-on"),
    ("Modo traductor", "trad-on"),
    ("Activa el traductor", "trad-on"),
    ("Translator mode", "trad-on"),
    ("Mode traducteur", "trad-on"),
    ("Modo tradutor", "trad-on"),
    ("Desactiva el modo traductor", "trad-off"),
    ("desactiva modo traductor", "trad-off"),
    ("Desactiva el traductor", "trad-off"),
    ("Apaga el traductor", "trad-off"),
    ("Deja de traducir", "trad-off"),
    ("Turn off the translator", "trad-off"),
    ("Desactive le traducteur", "trad-off"),
    ("Desativa o tradutor", "trad-off"),
    # --- Interrumpir y movimiento ---
    ("Oye MECH", "interrumpe"),
    ("Olle mech", "interrumpe"),            # yeísmo
    ("Hey MECH", "interrumpe"),
    ("Avanza diez segundos", "avanza"),
    ("Retrocede cinco segundos", "retrocede"),
    ("Mira hacia afuera", "afuera"),
    ("Mira asia afuera", "afuera"),         # h muda
    ("Regresa a proyectar", "proyectar"),
    ("Proyecta marketing", "marketing"),
    ("Proyecta marqueting", "marketing"),   # qu = k
]

# Frases normales de stand: ninguna es un comando.
STAND: list[str] = [
    # Cerca de la trivia, pero no son el comando.
    "me gusta jugar videojuegos",
    "¿de qué trata la obra?",
    "cuéntame un juego de mesa costarricense",
    "hazme una pregunta difícil",
    "los niños juegan en el parque",
    "Háblame del Quijote",
    "¿Los robots duermen?",
    "¿Cómo se traduce Quijote al francés?",
    "Cuéntame la historia de Malpaís",
    "¿Quién construyó este proyecto?",
    "El proyecto se llama MECH",
    "¿Qué avanzada tecnología usas?",
    "Cuenta la historia de la noche de la batalla",
    "¿De qué está hecho tu cuerpo?",
    "Buenas noches, ¿qué tal?",
    "Me interesa la parte de marketing de tu empresa",
    "¿Puedes hablar con más energía?",
    "Dame dos datos sobre Isaac Newton",
    "¿Tu equipo descansa alguna vez?",
    "Explícame cómo funciona el traductor",
    "¿Qué idiomas traduces?",
    "Háblame de la campaña de 1856",
    "¿Qué es un robot autónomo?",
]


def main() -> int:
    fallos = 0
    print("=== COMANDOS (deben reconocerse) ===")
    for texto, esperado in COMANDOS:
        got = _clasificar(texto)
        ok = got == esperado
        fallos += not ok
        print(f"{'ok   ' if ok else 'FALLA'} {got:12s} (esperado {esperado:12s}) {texto}")

    print("\n=== STAND (NO deben reconocerse) ===")
    for texto in STAND:
        got = _clasificar(texto)
        ok = got == "nada"
        fallos += not ok
        print(f"{'ok   ' if ok else 'FALLA'} {got:12s} {texto}")

    total = len(COMANDOS) + len(STAND)
    print()
    if fallos:
        print(f"{fallos} de {total} mal. Revisá los umbrales de voice_phrases.py")
        return 1
    print(f"Los {total} casos pasan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
