"""Orquestador principal de MECH.

Bucle:
    1. IDLE: el robot espera en pose neutral. (Opcionalmente patrulla con
       MODE:AUTO si está en modo demo solo, sin usuario cerca — pero por
       defecto arrancamos en IDLE para no perseguir gente.)
    2. LISTEN: cuando se invoca, escucha del micrófono hasta detectar
       silencio (VAD).
    3. THINK: transcribe (Whisper local) → pide plan a Claude.
    4. ACT: por cada segmento del plan:
        a. Si tiene image_prompt, genera con NanoBanana y lo proyecta.
        b. Marca el gesto al Arduino.
        c. Narra con ElevenLabs (bloqueante).
    5. Vuelve a LISTEN si hay contexto activo (dentro de una obra) o a IDLE.

Ejecución:
    python -m backend.main                     # arranca el bucle
    python -m backend.main --once "hola mech"  # un solo turno desde texto

El visor del proyector se lanza por separado:
    python -m backend.projector
"""

from __future__ import annotations

import argparse
import sys
import time

import config
import gestures
import image_gen
import llm
import projector
import stt
import tts
from arduino_link import get_link
from llm import Plan


def execute_plan(plan: Plan) -> None:
    """Recorre los segmentos del plan y los ejecuta."""
    link = get_link()
    link.set_mode("SPEAK")

    for i, seg in enumerate(plan.segments, 1):
        print(f"[Main] Segmento {i}/{len(plan.segments)}: {seg.gesture}")

        if seg.image_prompt:
            try:
                img_path = image_gen.generate_image(
                    seg.image_prompt,
                    filename=f"{plan.title.replace(' ', '_')}_{i}.png",
                )
                projector.show(img_path)
            except Exception as e:
                print(f"[Main] Imagen falló ({e}); continuando sin proyectar.")

        gestures.perform(link, seg.gesture)
        tts.speak(seg.narration, blocking=True)

    link.set_mode("IDLE")


def handle_turn(user_text: str, history: list[dict]) -> list[dict]:
    """Procesa una entrada de usuario y devuelve el historial actualizado."""
    print(f"[Main] Usuario dijo: {user_text!r}")
    if not user_text.strip():
        return history

    plan = llm.plan_response(user_text, conversation_history=history)
    print(f"[Main] Plan: modo={plan.mode}, título={plan.title!r}, "
          f"segmentos={len(plan.segments)}")

    execute_plan(plan)
    return llm.append_turn(history, user_text, plan)


def main_loop() -> None:
    config.assert_required()
    link = get_link()
    link.set_mode("IDLE")
    history: list[dict] = []

    # Saludo inicial.
    saludo = (
        "Hola, soy MECH. Pregúntame sobre obras culturales como Romeo y Julieta, "
        "Shrek o La Odisea, o sobre cómo estoy construido."
    )
    gestures.perform(link, "wave")
    tts.speak(saludo, blocking=True)

    print("[Main] Listo. Presiona Ctrl+C para salir.")
    try:
        while True:
            link.set_mode("LISTEN")
            user_text = stt.listen_once(max_seconds=20.0)
            if user_text is None:
                # No detectó voz; vuelve a esperar.
                link.set_mode("IDLE")
                time.sleep(0.5)
                continue

            try:
                history = handle_turn(user_text, history)
            except Exception as e:
                print(f"[Main] Error en turno: {e}")
                tts.speak("Disculpa, tuve un problema. ¿Puedes repetirme?", blocking=True)

            # Limita el historial para no crecer sin fin.
            if len(history) > 12:
                history = history[-12:]

    except KeyboardInterrupt:
        print("\n[Main] Apagando...")
    finally:
        link.close()
        projector.clear()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backend MECH")
    parser.add_argument(
        "--once",
        type=str,
        default=None,
        help="Ejecuta un solo turno con este texto y termina (sin STT).",
    )
    args = parser.parse_args()

    if args.once:
        config.assert_required()
        get_link().set_mode("IDLE")
        try:
            handle_turn(args.once, history=[])
        finally:
            get_link().close()
            projector.clear()
        return

    main_loop()


if __name__ == "__main__":
    main()
