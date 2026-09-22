"""Configuración centralizada del backend MECH.

Lee variables de entorno desde .env y las expone como constantes.
Todos los demás módulos importan de aquí en vez de leer os.environ.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# Claude
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-7")

# ElevenLabs
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "8mBRP99B2Ng2QwsJMFQl")
ELEVENLABS_MODEL_ID = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
# Modo ahorro: si es true, el TTS NO llama a ElevenLabs (no gasta créditos).
# MECH "narra" en seco: loguea el texto y simula la duración para que el
# flujo (gestos, fases, proyección) corra igual. Útil para probar sin gastar.
TTS_DRY_RUN = os.environ.get("TTS_DRY_RUN", "false").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)

# Gemini (NanoBanana)
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GEMINI_IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")

# Arduino
ARDUINO_PORT = os.environ.get("ARDUINO_PORT", "/dev/ttyACM0")
ARDUINO_BAUD = int(os.environ.get("ARDUINO_BAUD", "115200"))

# Gestos de los brazos mientras MECH habla.
#   "full"   = gestos reales según lo que pida Claude (wave, excited...),
#              con movimiento suave interpolado (default).
#   "subtle" = movimiento pequeño adelante/atrás cerca del reposo.
#   "off"    = los brazos NO se mueven al hablar.
ARM_GESTURE_MODE = os.environ.get("ARM_GESTURE_MODE", "full").strip().lower()
# Amplitud (grados) del movimiento suave respecto a la posición neutra (90°).
ARM_GESTURE_AMPLITUDE = int(os.environ.get("ARM_GESTURE_AMPLITUDE", "12"))
# Si true, algunos gestos también mueven las ruedas (giro corto, balanceo).
# Los movimientos son cortos y siempre terminan en STOP.
GESTURE_WHEELS = os.environ.get("GESTURE_WHEELS", "true").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)
# Velocidad del balanceo de ruedas de los gestos. También a fondo: a media
# potencia no se movía. Como es a 100, los tramos son MUY cortos
# (GESTURE_WHEEL_SECONDS) para que sea un golpecito y no un viaje.
GESTURE_WHEEL_SPEED = int(os.environ.get("GESTURE_WHEEL_SPEED", "100"))
GESTURE_WHEEL_SECONDS = float(os.environ.get("GESTURE_WHEEL_SECONDS", "0.18"))
# Velocidad con la que vuelve al punto de inicio (return_to_start).
RETURN_SPEED = int(os.environ.get("RETURN_SPEED", "100"))
# Duración (segundos) del arco de SUBIDA (y de bajada) del saludo. El equipo
# lo pidió LENTO y amable: es el gesto que ve todo el que se acerca al stand.
# Súbelo para un saludo aún más pausado; bájalo si se siente eterno.
ARM_WAVE_SECONDS = float(os.environ.get("ARM_WAVE_SECONDS", "2.2"))
# Amplitud del saludo (sep 2026: "casi no se nota"). El brazo sube desde el
# reposo (90°) hasta ARM_WAVE_HIGH y allí arriba hace ARM_WAVE_REPEATS
# vaivenes de ARM_WAVE_SWING grados. Antes el tope era 170 y el vaivén 20°;
# ahora llega arriba del todo y agita 65°, que se ve desde lejos.
# Solo sube (90→180): NO bajar de 90, que es donde el brazo choca con el
# cuerpo del robot.
ARM_WAVE_HIGH = int(os.environ.get("ARM_WAVE_HIGH", "180"))
ARM_WAVE_SWING = int(os.environ.get("ARM_WAVE_SWING", "65"))
# Cuántas veces llega el brazo ARRIBA durante el saludo — o sea, cuántas
# "rotaciones" se ven. Cuenta la subida inicial: 4 = sube, agita 3 veces más
# y baja.
#
# ⚠️ No lo cambies a "solo las agitadas": la subida inicial también se ve
# como una, así que el número del panel dejaría de coincidir con lo que se
# cuenta mirando el robot. Se midió: `scripts/probar_saludo.py`.
#
# El equipo lo pidió en "3 o 4 rotaciones" (sep 2026) -> default 4.
# Vale para el saludo de bienvenida Y para el giro hacia afuera: es el mismo
# número, lo que cambia entre ellos es la amplitud del arco.
ARM_WAVE_REPEATS = max(2, int(os.environ.get("ARM_WAVE_REPEATS", "4")))
# ¿El saludo levanta los DOS brazos?
#
# FALSE por defecto (sep 2026, pedido del equipo): saluda SOLO EL BRAZO
# DERECHO. Con los dos se leía más como "manos arriba" que como un saludo, y
# además gasta el doble de batería en el gesto que más se repite en el stand.
# Ponerlo en true recupera el comportamiento anterior (el derecho agita y el
# izquierdo sube a acompañar).
ARM_WAVE_BOTH = os.environ.get("ARM_WAVE_BOTH", "false").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)
# Sentido de giro de cada brazo, igual que DIR_FL/FR/BL/BR hacen con las
# ruedas en el .ino.
#
# Todo el código de gestos piensa en "90 = reposo, más de 90 = levantado".
# Si la bocina del servo está montada del otro lado, el brazo sube al BAJAR
# el ángulo y TODOS los gestos salen al revés. Esto le da la vuelta al
# recorrido sin tocar el firmware ni desmontar el brazo (el reposo se queda
# en 90 en los dos casos, así que no hay que recalibrar nada más).
#
# El DERECHO va invertido por defecto (sep 2026): el equipo reportó que
# saludaba hacia el lado contrario. Si en tu robot es al revés, se cambia en
# vivo desde Ajustes → «Invertir brazo derecho / izquierdo», sin reiniciar.
#
# OJO: `_bool_env` se define al final del módulo, así que aquí arriba se lee
# a mano igual que las demás claves de esta zona.
ARM_INVERT_R = os.environ.get("ARM_INVERT_R", "true").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)
ARM_INVERT_L = os.environ.get("ARM_INVERT_L", "false").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)
# Gestos MIENTRAS NARRA (proyectando):
#   "simple" (default) = UN solo brazo, recorrido corto y lento. Los servos
#                        gastan poco y la proyección no se llena de ruido
#                        mecánico. Es lo que pidió el equipo (ago 2026).
#   "full"             = las coreografías completas (dos brazos, ruedas).
# El SALUDO no se ve afectado: siempre usa la coreografía completa.
NARRATION_GESTURE_MODE = os.environ.get(
    "NARRATION_GESTURE_MODE", "simple"
).strip().lower()
# Segundos entre saludos a la cámara. Bajo = saluda a cada visitante nuevo;
# alto = no repite el saludo a quien lleva rato enfrente.
GREETING_COOLDOWN = float(os.environ.get("GREETING_COOLDOWN", "45"))
# Cuánto tiene que estar AUSENTE alguien para que MECH vuelva a saludar
# (segundos). Es la diferencia entre "otro visitante" y "el mismo de antes".
#
# Sin esto, MECH saludaba en bucle cada GREETING_COOLDOWN aunque no hubiera
# nadie: `vision.LOST_AFTER_S` son 1.5 s, así que un parpadeo del detector
# (alguien que gira la cabeza, un falso positivo con la luz de la proyección)
# ya contaba como "se fue y volvió", y el cooldown era lo único que lo
# frenaba. Ahora el reloj se REINICIA con cada pérdida: si el detector
# parpadea, nunca llega a esta cuenta y MECH no repite el saludo.
GREETING_REARM_SECONDS = float(os.environ.get("GREETING_REARM_SECONDS", "20"))
# El saludo por cámara SOLO se dispara con MECH EN REPOSO (decisión del
# equipo, sep 2026). Despierto está narrando, conversando o traduciendo, y
# soltar "¡Hola! Soy MECH" encima de eso corta la experiencia del visitante
# que ya está atendiendo. En reposo, en cambio, es justo lo que se quiere:
# alguien se acerca al stand y MECH lo recibe.
# El botón «SALUDAR AHORA» del panel NO se ve afectado (es para probarlo).
GREETING_ONLY_DORMANT = os.environ.get(
    "GREETING_ONLY_DORMANT", "true"
).strip().lower() in ("1", "true", "yes", "on", "si", "sí")

# --- Maniobra "mira hacia afuera" / "regresa a proyectar" ------------------
# MECH gira 180° para saludar al público que pasa y luego vuelve a quedar
# apuntando a donde proyecta. SIN encoders: el giro se mide POR TIEMPO, así
# que TURN_180_SECONDS hay que CALIBRARLO en el robot real (Ajustes del
# panel, en vivo): ponlo a girar y ajusta hasta que quede de espaldas.
# ⚠️ POTENCIA AL MÁXIMO por defecto (sep 2026). Los motores y las ruedas
# actuales son de mal material y el L298N se "come" ~2 V: a media potencia
# los motores zumban y no rompen la fricción estática, sobre todo girando
# (las mecanum arrastran los rodillos de lado). 100 = PWM 255. Si el giro
# sale demasiado brusco, baja PRIMERO los segundos, no la velocidad.
# La media vuelta es UN SOLO tramo LATERAL (el mismo movimiento del botón
# "LATERAL" del panel) sostenido hasta que el robot queda de espaldas. NO se
# usa rotación (`w`): en el suelo del stand hacía "un movimiento raro y muy
# corto" — con estas ruedas el que gira de verdad es el lateral (sep 2026).
TURN_180_SPEED = int(os.environ.get("TURN_180_SPEED", "100"))
# CALIBRADO EN EL ROBOT (sep 2026), en dos pasadas:
#   2.0 s  -> giraba "un poquito menos de la mitad" (~80°)
#   4.5 s  -> 165-170°, casi los 180
#   5.0 s  -> se pasaba un poco
#   4.8 s  -> valor actual
# Sigue siendo un punto de partida: cambiar de suelo, de batería o de ruedas
# obliga a reajustarlo desde Ajustes → "Media vuelta" (en vivo).
TURN_180_SECONDS = float(os.environ.get("TURN_180_SECONDS", "4.8"))
# Si gira hacia el lado contrario del que querés, ponelo en true (en vivo
# desde Ajustes). No hay que tocar el firmware ni recablear.
TURN_180_INVERT = os.environ.get("TURN_180_INVERT", "false").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)
# OBSOLETAS desde sep 2026 (la maniobra ya no tiene tramo de rotación
# aparte). Se conservan para no romper .env existentes; no hacen nada.
TURN_LATERAL_SPEED = int(os.environ.get("TURN_LATERAL_SPEED", "100"))
TURN_LATERAL_SECONDS = float(os.environ.get("TURN_LATERAL_SECONDS", "0.5"))
# Arranque a fondo: cada tramo empieza con un pulso a potencia MÁXIMA para
# romper la fricción estática, y recién después baja a la velocidad pedida.
# Es el truco clásico cuando un motor "zumba pero no arranca". Si la
# velocidad pedida ya es 100, el pulso no cambia nada. 0 = desactivado.
MOTOR_KICK_SECONDS = float(os.environ.get("MOTOR_KICK_SECONDS", "0.15"))

# RoboKit RS — movimiento por "bus de pines".
# La Pi pone estos pines GPIO (BCM) en alto/bajo; el RoboKit corre un programa
# Rogic que los lee y se mueve. Un pin activo a la vez = un comando.
# GND de la Pi -> GND del RoboKit (tierra común, obligatorio).
ROBOKIT_PIN_FWD = int(os.environ.get("ROBOKIT_PIN_FWD", "17"))    # adelante  -> RoboKit pin 2
ROBOKIT_PIN_LEFT = int(os.environ.get("ROBOKIT_PIN_LEFT", "27"))  # girar izq -> RoboKit pin 3
ROBOKIT_PIN_RIGHT = int(os.environ.get("ROBOKIT_PIN_RIGHT", "22"))  # girar der -> RoboKit pin 4

# STT
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")
WHISPER_LANGUAGE = os.environ.get("WHISPER_LANGUAGE", "es")
# Modo offline: usa el modelo ya descargado del disco SIN tocar internet, así
# no se cuelga esperando la red (clave en eventos con wifi mala). Default true.
# Ponlo en false SOLO si necesitas DESCARGAR un modelo nuevo de Whisper.
WHISPER_OFFLINE = os.environ.get("WHISPER_OFFLINE", "true").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)

# Modelo de Whisper que se usa SOLO para oír "oye MECH" mientras MECH narra.
# Vacío = el mismo que WHISPER_MODEL (no hay que descargar nada). Se carga en
# una instancia aparte limitada a pocos hilos de CPU: si no, transcribir
# mientras habla le roba núcleos al reproductor y la voz se entrecorta.
# Poner "tiny" lo hace aún más ligero y rápido (hay que descargarlo una vez).
WHISPER_INTERRUPT_MODEL = os.environ.get("WHISPER_INTERRUPT_MODEL", "").strip()
WHISPER_INTERRUPT_THREADS = int(os.environ.get("WHISPER_INTERRUPT_THREADS", "2"))
# Cuántas hipótesis explora Whisper al decodificar. 1 = lo más rápido, pero
# se queda con la primera opción; 5 (el default de faster-whisper) acierta
# notablemente más en frases cortas con ruido, a cambio de unas décimas.
# Bájalo a 1 si en el evento la respuesta se siente lenta.
WHISPER_BEAM_SIZE = int(os.environ.get("WHISPER_BEAM_SIZE", "5"))
# El de las interrupciones va SIEMPRE a 1: ahí manda el retardo (MECH sigue
# hablando mientras tanto) y solo hay que reconocer dos palabras conocidas.
WHISPER_INTERRUPT_BEAM_SIZE = int(os.environ.get("WHISPER_INTERRUPT_BEAM_SIZE", "1"))

# Audio
AUDIO_SAMPLE_RATE = int(os.environ.get("AUDIO_SAMPLE_RATE", "48000"))

# --- Cadena de audio antes de Whisper (ver docs/AUDIO.md) ----------------
# Lo mínimo que hace cualquier teléfono con el micrófono antes de pasárselo
# al reconocedor. Los dos se aplican en `stt.prepare_for_whisper()`.
#
# Pasa-altos (Hz): quita la continua y el retumbe (zumbido de red, roce de la
# ropa contra el micrófono de solapa, golpes de mesa). 0 = desactivado.
# Importa el doble: además de limpiar lo que oye Whisper, evita que una
# continua infle el piso de ruido del detector y deje a MECH sordo.
AUDIO_HIGHPASS_HZ = float(os.environ.get("AUDIO_HIGHPASS_HZ", "80"))
# Nivel objetivo (dBFS, negativo) al que se lleva la voz antes de
# transcribirla — el "AGC" del teléfono. Whisper transcribe peor lo que entra
# muy bajito, y en un stand cada visitante habla a distinta distancia y
# volumen. -16 dBFS es lo que recomienda la documentación de Whisper.
# 0 = desactivado (deja el audio como entró).
AUDIO_TARGET_DBFS = float(os.environ.get("AUDIO_TARGET_DBFS", "-16"))

VAD_AGGRESSIVENESS = int(os.environ.get("VAD_AGGRESSIVENESS", "2"))
VAD_SILENCE_TIMEOUT = float(os.environ.get("VAD_SILENCE_TIMEOUT", "1.2"))
# Cuánto más fuerte que el ruido de fondo debe sonar la voz para que MECH
# empiece a grabar (y al revés: cuando la amplitud cae cerca del piso de
# ruido, se considera que terminó de hablar). El piso de ruido se mide solo
# y se adapta al ambiente (clave en stands ruidosos como la olimpiada).
#   2.0 = sensible · 2.5 = equilibrado · 4.0+ = solo voz fuerte y cercana
VAD_ENERGY_FACTOR = float(os.environ.get("VAD_ENERGY_FACTOR", "2.5"))
# En reposo (esperando "ok MECH"), tope de duración de cada grabación: la
# frase de despertar es corta, así que cortamos rápido y revisamos enseguida.
WAKE_MAX_UTTERANCE = float(os.environ.get("WAKE_MAX_UTTERANCE", "4.0"))
# Segundos máximos que el micrófono espera por voz en cada turno. Súbelo si
# el juez/usuario tarda en empezar a hablar.
LISTEN_MAX_SECONDS = float(os.environ.get("AUDIO_LISTEN_MAX_SECONDS", "20"))

# --- Control del bucle de voz por palabra clave ---------------------------
# Si VOICE_AUTOSTART=true, el bucle de voz arranca solo al iniciar el server,
# pero EN REPOSO: el micrófono escucha únicamente la palabra para despertar.
# Así MECH queda esperando "ok MECH" sin tocar el panel.
VOICE_AUTOSTART = os.environ.get("VOICE_AUTOSTART", "true").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)
# Frases (separadas por coma) que ACTIVAN a MECH cuando está en reposo.
# El comando principal es "ok mech" (estilo Alexa/Google). Se incluyen
# variantes de cómo suele transcribirlo Whisper ("okay", "oye", etc.).
VOICE_WAKE_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_WAKE_PHRASES",
        "ok mech,okay mech,okey mech,ok mek,oye mech,"
        "despierta mech,despierta,activa mech,mech despierta",
    ).split(",") if p.strip()
]
# Frases que ponen a MECH EN REPOSO (deja de responder, sigue oyendo el wake).
# El match es por palabras en cualquier orden (ver _matches_any en server.py),
# así que "duermete", "duermete mech" y "mech duermete" funcionan igual.
#
# ⚠️ La lista es LARGA a propósito (sep 2026). El equipo reportó que a veces
# «duérmete MECH» no lo dormía: MECH soltaba una despedida larga y volvía a
# escuchar. La causa es que la frase no casaba (Whisper escribe «dormite»,
# «que duermas», «a dormir»...), el texto se iba a Claude y Claude improvisaba
# una respuesta bonita — pero dormirse no es algo que un plan pueda hacer.
# Cuantas más variantes naturales estén aquí, menos veces pasa.
# Hay además DOS redes más abajo: el intercept de `mech_app.handle_text_command`
# y el modo `sleep` del plan de Claude (ver llm.py).
VOICE_SLEEP_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_SLEEP_PHRASES",
        # ⚠️ Las formas de "dormir" PIDEN "mech" al lado, y no es un capricho:
        # el matcher perdona 2 letras en palabras de 7+ que empiecen igual, así
        # que «duermete» casa con «duermen» y la pregunta «¿los robots
        # duermen?» dormía a MECH en vez de responderse (medido en
        # scripts/probar_frases.py). Lo mismo con "buenas noches" suelto, que
        # en un stand es un saludo, no una orden.
        # Las frases que NO llevan "mech" son las que no se parecen a nada de
        # una conversación normal ("para de escuchar", "modo reposo").
        "para de escuchar,deja de escuchar,para de recibir,ya no escuches,"
        "duermete mech,duermase mech,dormite mech,duerme mech,"
        "vete a dormir mech,ponte a dormir mech,ve a dormir mech,"
        "a dormir mech,descansa mech,"
        "ponte en reposo,modo reposo,entra en reposo,"
        "buenas noches mech,hasta luego mech,adios mech",
    ).split(",") if p.strip()
]
# --- Interrumpir a MECH mientras narra ("oye MECH" / "hey MECH") ----------
# Mientras MECH presenta, un hilo aparte escucha SOLO esta frase, para que el
# visitante pueda cortarlo si necesita otra cosa. Todo lo demás que oiga
# durante la narración se descarta (es, casi siempre, el eco de su propio
# parlante). Se puede apagar desde el panel (Ajustes) o aquí.
VOICE_INTERRUPT_ENABLED = os.environ.get("VOICE_INTERRUPT_ENABLED", "true").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)
VOICE_INTERRUPT_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_INTERRUPT_PHRASES",
        "oye mech,oiga mech,disculpa mech,perdon mech",
    ).split(",") if p.strip()
]
VOICE_INTERRUPT_PHRASES_EN = [
    p.strip() for p in os.environ.get(
        "VOICE_INTERRUPT_PHRASES_EN",
        "hey mech,excuse me mech,sorry mech",
    ).split(",") if p.strip()
]
# OJO con las frases de interrupción en francés/portugués: "pardon" y
# "desculpa" ya caen solas en las españolas "perdon"/"disculpa" por la
# tolerancia de una letra, así que aquí van las que NO se parecen a ninguna.
VOICE_INTERRUPT_PHRASES_FR = [
    p.strip() for p in os.environ.get(
        "VOICE_INTERRUPT_PHRASES_FR",
        "excusez moi mech,pardon mech,attends mech",
    ).split(",") if p.strip()
]
VOICE_INTERRUPT_PHRASES_PT = [
    p.strip() for p in os.environ.get(
        "VOICE_INTERRUPT_PHRASES_PT",
        "escuta mech,desculpa mech,com licenca mech",
    ).split(",") if p.strip()
]
# Cuánto MÁS FUERTE que el ruido de fondo tiene que sonar una voz para que
# MECH la grabe MIENTRAS ÉL HABLA. Es más alto que el normal a propósito: su
# propio parlante dispara el detector todo el rato, y transcribir cada frase
# que él mismo dice satura la CPU de la Pi (audio entrecortado, panel lento y
# la interrupción llegando tarde). Con el micrófono de solapa, el visitante
# entra mucho más fuerte que el parlante, así que este filtro casi no cuesta
# detección. Súbelo si MECH se transcribe a sí mismo; bájalo si no te oye.
INTERRUPT_ENERGY_FACTOR = float(os.environ.get("INTERRUPT_ENERGY_FACTOR", "4.0"))
# Clips más cortos que esto son ruido (un golpe, una sílaba): no se
# transcriben. "oye MECH" dura ~0.8 s.
INTERRUPT_MIN_CLIP = float(os.environ.get("INTERRUPT_MIN_CLIP", "0.35"))
# Tope de duración de cada escucha mientras narra. Corto a propósito: la
# frase dura ~1 s, y cuanto más corto el clip, más rápido lo transcribe la Pi
# (y antes se corta la narración).
INTERRUPT_MAX_UTTERANCE = float(os.environ.get("INTERRUPT_MAX_UTTERANCE", "4.0"))
# Silencio (segundos) que da por terminada la frase MIENTRAS narra. Más corto
# que el normal (VAD_SILENCE_TIMEOUT) porque aquí solo esperamos dos palabras:
# esto es lo que más recorta el retardo entre "oye MECH" y el corte. De paso
# hace que dispare antes (el disparo pide media ventana de voz).
INTERRUPT_SILENCE_TIMEOUT = float(os.environ.get("INTERRUPT_SILENCE_TIMEOUT", "0.6"))

# --- Avanzar / retroceder un rato ----------------------------------------
# "avanza diez segundos" mueve a MECH hacia adelante ese tiempo. Si no se
# dice ningún número ("avanza" a secas), se usa ADVANCE_SECONDS.
# Como todo lo que mueve ruedas, va a potencia máxima: a media potencia estos
# motores solo zumban.
ADVANCE_SECONDS = float(os.environ.get("ADVANCE_SECONDS", "10"))
ADVANCE_SPEED = int(os.environ.get("ADVANCE_SPEED", "100"))
# Tope de seguridad: por mucho que le pidan, no se va a mover más que esto de
# una sola vez (en un stand, un robot lanzado varios metros es un problema).
ADVANCE_MAX_SECONDS = float(os.environ.get("ADVANCE_MAX_SECONDS", "30"))

# --- Órdenes de movimiento por voz ---------------------------------------
# Dos órdenes que NO pasan por Claude (son instantáneas y no gastan crédito):
#   "mira hacia afuera"   -> gira 180° y saluda al público que pasa.
#   "regresa a proyectar" -> deshace el giro y vuelve a su posición.
# Ver backend/maneuvers.py. El match es por palabras en cualquier orden, así
# que "MECH, mirá hacia afuera" o "mira afuera" también funcionan.
VOICE_ADVANCE_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_ADVANCE_PHRASES",
        "avanza,avanzá,adelante,ve adelante,camina adelante,muevete adelante",
    ).split(",") if p.strip()
]
VOICE_ADVANCE_PHRASES_EN = [
    p.strip() for p in os.environ.get(
        "VOICE_ADVANCE_PHRASES_EN",
        "move forward,go forward,forward",
    ).split(",") if p.strip()
]
VOICE_ADVANCE_PHRASES_FR = [
    p.strip() for p in os.environ.get(
        "VOICE_ADVANCE_PHRASES_FR",
        "avance,avancer,va tout droit,en avant",
    ).split(",") if p.strip()
]
VOICE_ADVANCE_PHRASES_PT = [
    p.strip() for p in os.environ.get(
        "VOICE_ADVANCE_PHRASES_PT",
        "avanca,va em frente,para frente,anda para frente",
    ).split(",") if p.strip()
]
VOICE_RETREAT_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_RETREAT_PHRASES",
        "retrocede,retrocedé,atras,ve atras,camina atras,muevete atras",
    ).split(",") if p.strip()
]
VOICE_RETREAT_PHRASES_EN = [
    p.strip() for p in os.environ.get(
        "VOICE_RETREAT_PHRASES_EN",
        "move back,go back,move backward,backward",
    ).split(",") if p.strip()
]
VOICE_RETREAT_PHRASES_FR = [
    p.strip() for p in os.environ.get(
        "VOICE_RETREAT_PHRASES_FR",
        "recule,reculer,en arriere,va en arriere",
    ).split(",") if p.strip()
]
VOICE_RETREAT_PHRASES_PT = [
    p.strip() for p in os.environ.get(
        "VOICE_RETREAT_PHRASES_PT",
        "recua,recuar,para tras,anda para tras",
    ).split(",") if p.strip()
]
VOICE_OUTWARD_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_OUTWARD_PHRASES",
        "mira hacia afuera,mira afuera,mira para afuera,voltea hacia afuera,"
        "date la vuelta,saluda afuera,saluda a la gente",
    ).split(",") if p.strip()
]
VOICE_OUTWARD_PHRASES_EN = [
    p.strip() for p in os.environ.get(
        "VOICE_OUTWARD_PHRASES_EN",
        "look outside,look outward,turn around,face the crowd,greet the people",
    ).split(",") if p.strip()
]
VOICE_OUTWARD_PHRASES_FR = [
    p.strip() for p in os.environ.get(
        "VOICE_OUTWARD_PHRASES_FR",
        "regarde dehors,regarde vers l exterieur,tourne toi,"
        "salue le public,salue les gens",
    ).split(",") if p.strip()
]
VOICE_OUTWARD_PHRASES_PT = [
    p.strip() for p in os.environ.get(
        "VOICE_OUTWARD_PHRASES_PT",
        "olha para fora,vira para fora,da a volta,"
        "cumprimenta o publico,cumprimenta as pessoas",
    ).split(",") if p.strip()
]
VOICE_PROJECT_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_PROJECT_PHRASES",
        "regresa a proyectar,vuelve a proyectar,regresa a tu posicion,"
        "vuelve a tu posicion,regresa a la proyeccion,ponte a proyectar",
    ).split(",") if p.strip()
]
VOICE_PROJECT_PHRASES_EN = [
    p.strip() for p in os.environ.get(
        "VOICE_PROJECT_PHRASES_EN",
        "back to projecting,go back to projecting,turn back,"
        "back to your position,face the screen",
    ).split(",") if p.strip()
]
VOICE_PROJECT_PHRASES_FR = [
    p.strip() for p in os.environ.get(
        "VOICE_PROJECT_PHRASES_FR",
        "retourne projeter,reviens projeter,retourne a ta place,"
        "reviens a ta position,regarde l ecran",
    ).split(",") if p.strip()
]
VOICE_PROJECT_PHRASES_PT = [
    p.strip() for p in os.environ.get(
        "VOICE_PROJECT_PHRASES_PT",
        "volta a projetar,volta para a projecao,volta para o teu lugar,"
        "volta para a tua posicao,olha para a tela",
    ).split(",") if p.strip()
]

# --- Proyectar el slot de MARKETING --------------------------------------
# "proyecta marketing" reproduce los videos del slot promo enteros, en fila y
# CON SU PROPIO AUDIO (MECH no narra encima). No pasa por Claude.
VOICE_MARKETING_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_MARKETING_PHRASES",
        "proyecta marketing,proyecta el marketing,pon marketing,"
        "pon el marketing,reproduce marketing,muestra marketing,"
        "video de marketing,videos de marketing",
    ).split(",") if p.strip()
]
VOICE_MARKETING_PHRASES_EN = [
    p.strip() for p in os.environ.get(
        "VOICE_MARKETING_PHRASES_EN",
        "play marketing,play the marketing,show marketing,"
        "marketing video,marketing videos",
    ).split(",") if p.strip()
]
VOICE_MARKETING_PHRASES_FR = [
    p.strip() for p in os.environ.get(
        "VOICE_MARKETING_PHRASES_FR",
        "lance le marketing,joue le marketing,montre le marketing,"
        "video marketing,videos marketing",
    ).split(",") if p.strip()
]
VOICE_MARKETING_PHRASES_PT = [
    p.strip() for p in os.environ.get(
        "VOICE_MARKETING_PHRASES_PT",
        "toca marketing,passa o marketing,mostra marketing,"
        "video de marketing,videos de marketing",
    ).split(",") if p.strip()
]
# Tope de seguridad de la reproducción (segundos). El fin normal lo avisa el
# propio proyector cuando termina el último video; esto solo evita que MECH
# se quede colgado si NO hay ninguna pantalla abierta. Con videos de ~90 s,
# 12 espacios serían ~18 min: el default deja margen de sobra.
MARKETING_MAX_SECONDS = float(os.environ.get("MARKETING_MAX_SECONDS", "1500"))

# --- Modo TRADUCTOR (ver backend/translator.py) --------------------------
# "traduce MECH" pone a MECH a traducir una conversación entre dos personas:
# pregunta el par de idiomas y, a partir de ahí, todo lo que oye lo repite en
# el otro idioma. NO pasa por el flujo normal de Claude (nada de obras, ni
# gestos, ni proyección): es una llamada corta y directa de traducción.
TRANSLATOR_ENABLED = os.environ.get("TRANSLATOR_ENABLED", "true").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)
# OJO: nada de "traduce" o "traductor" a secas. Con la palabra sola, una
# pregunta normal del stand ("¿cómo se traduce Quijote al francés?") entraría
# en modo traductor en vez de responderse. Por eso todas las frases piden dos
# palabras.
#
# Hay DOS formas de traducir, y las listas están separadas a propósito
# (pedido del equipo, sep 2026):
#
#   «traduce MECH»               -> UNA frase y se calla (VOICE_TRANSLATE_*)
#   «activa modo traductor»      -> se queda traduciendo (VOICE_TRANSLATE_ON_*)
#   «desactiva el modo traductor»-> sale del continuo (VOICE_TRANSLATE_STOP_*)
#
# ⚠️ «desactiva el modo traductor» CONTIENE «modo traductor», así que las dos
# listas se pisan por fuerza. Lo resuelve `voice_phrases.is_translate_on()`,
# que devuelve False si la frase también casa con las de salir. Si añadís
# frases aquí, comprobá que ese orden sigue teniendo sentido.
VOICE_TRANSLATE_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_TRANSLATE_PHRASES",
        "traduce mech,traduci mech,traduce una,traduce esto,traductor mech",
    ).split(",") if p.strip()
]
VOICE_TRANSLATE_PHRASES_EN = [
    p.strip() for p in os.environ.get(
        "VOICE_TRANSLATE_PHRASES_EN",
        "translate mech,translate this,translate one",
    ).split(",") if p.strip()
]
VOICE_TRANSLATE_PHRASES_FR = [
    p.strip() for p in os.environ.get(
        "VOICE_TRANSLATE_PHRASES_FR",
        "traduis mech,traduire mech,traduis ceci",
    ).split(",") if p.strip()
]
VOICE_TRANSLATE_PHRASES_PT = [
    p.strip() for p in os.environ.get(
        "VOICE_TRANSLATE_PHRASES_PT",
        "traduz mech,traduzir mech,traduz isto",
    ).split(",") if p.strip()
]
# Frases que ENCIENDEN el modo traductor CONTINUO: MECH se queda traduciendo
# todo lo que oiga, frase tras frase, hasta que le digan que lo desactive.
VOICE_TRANSLATE_ON_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_TRANSLATE_ON_PHRASES",
        "activa modo traductor,activa el modo traductor,modo traductor,"
        "activa el traductor,enciende el traductor,ponte a traducir,"
        "quiero traducir,entra en modo traductor",
    ).split(",") if p.strip()
]
VOICE_TRANSLATE_ON_PHRASES_EN = [
    p.strip() for p in os.environ.get(
        "VOICE_TRANSLATE_ON_PHRASES_EN",
        "translator mode,translation mode,turn on the translator,"
        "start translating,enable translator",
    ).split(",") if p.strip()
]
VOICE_TRANSLATE_ON_PHRASES_FR = [
    p.strip() for p in os.environ.get(
        "VOICE_TRANSLATE_ON_PHRASES_FR",
        "mode traducteur,active le traducteur,active le mode traducteur",
    ).split(",") if p.strip()
]
VOICE_TRANSLATE_ON_PHRASES_PT = [
    p.strip() for p in os.environ.get(
        "VOICE_TRANSLATE_ON_PHRASES_PT",
        "modo tradutor,ativa o tradutor,ativa o modo tradutor",
    ).split(",") if p.strip()
]
# Frases para SALIR del modo traductor (del continuo y del de una frase).
# Dormirlo y el paro de emergencia también lo sacan.
VOICE_TRANSLATE_STOP_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_TRANSLATE_STOP_PHRASES",
        "desactiva el modo traductor,desactiva modo traductor,"
        "desactiva el traductor,apaga el traductor,quita el modo traductor,"
        "deja de traducir,para de traducir,termina la traduccion,"
        "sal del traductor,sal del modo traductor,fin de la traduccion",
    ).split(",") if p.strip()
]
VOICE_TRANSLATE_STOP_PHRASES_EN = [
    p.strip() for p in os.environ.get(
        "VOICE_TRANSLATE_STOP_PHRASES_EN",
        "turn off the translator,disable translator,stop translating,"
        "stop the translation,exit translator,end translation",
    ).split(",") if p.strip()
]
VOICE_TRANSLATE_STOP_PHRASES_FR = [
    p.strip() for p in os.environ.get(
        "VOICE_TRANSLATE_STOP_PHRASES_FR",
        "desactive le traducteur,arrete de traduire,fin de la traduction,"
        "quitte le traducteur",
    ).split(",") if p.strip()
]
VOICE_TRANSLATE_STOP_PHRASES_PT = [
    p.strip() for p in os.environ.get(
        "VOICE_TRANSLATE_STOP_PHRASES_PT",
        "desativa o tradutor,para de traduzir,fim da traducao,sai do tradutor",
    ).split(",") if p.strip()
]
# Traduce en LOS DOS SENTIDOS: Whisper detecta en cuál de los dos idiomas del
# par habló cada persona y MECH responde en el otro. Es lo que hace que sirva
# para una conversación de verdad (no solo para dictarle a MECH).
# Ponlo en false para fijar el sentido (siempre origen -> destino): es menos
# cómodo, pero no se equivoca nunca de dirección. Útil si el par es
# español/portugués, que Whisper confunde en frases muy cortas.
TRANSLATOR_AUTO_DETECT = os.environ.get(
    "TRANSLATOR_AUTO_DETECT", "true"
).strip().lower() in ("1", "true", "yes", "on", "si", "sí")
# Modelo para traducir. Por defecto el mismo de siempre; si en el evento se
# nota lento, aquí se puede poner uno más rápido sin tocar el resto.
CLAUDE_TRANSLATE_MODEL = os.environ.get("CLAUDE_TRANSLATE_MODEL", "") or CLAUDE_MODEL
# Segundos de espera tras cada traducción, para que el parlante (Bluetooth,
# con buffer propio) termine de sonar ANTES de volver a abrir el micrófono.
# Sin esto MECH se oye a sí mismo y traduce su propia traducción en bucle.
TRANSLATOR_DRAIN_SECONDS = float(os.environ.get("TRANSLATOR_DRAIN_SECONDS", "0.8"))
# Lo mismo, pero en el modo CONTINUO («activa modo traductor»), donde MECH
# vuelve a escuchar justo después de cada traducción. Es MÁS LARGO a
# propósito: ahí el micrófono se abre siempre detrás de su propia voz, que es
# exactamente la situación que el modo de una frase evitaba por diseño.
#
# ⚠️ Si en el evento MECH empieza a traducir su propia traducción, ÉSTA es la
# primera perilla que hay que subir (Ajustes -> «Espera del traductor
# continuo»). La segunda es el «Umbral ruido».
TRANSLATOR_CONTINUOUS_DRAIN_SECONDS = float(
    os.environ.get("TRANSLATOR_CONTINUOUS_DRAIN_SECONDS", "1.2")
)

# --- Idiomas extra: inglés, francés y portugués (opcionales) -------------
# MECH vive en español. Los demás idiomas se activan SI Y SOLO SI se le
# despierta en ese idioma; a partir de ahí entiende, narra y subtitula en él
# hasta que se duerme (ahí vuelve solo a español). Ver backend/lang.py.
#
#   "wake up MECH"                    -> inglés
#   "bonjour MECH" / "réveille MECH"  -> francés
#   "bom dia MECH" / "acorda MECH"    -> portugués
#
# OJO al inventar frases nuevas: el matcher tolera UNA letra de error en
# palabras de 4+ letras, así que el portugués "desperta" chocaría con el
# español "despierta" y despertaría en el idioma equivocado. Por eso el
# portugués usa "acorda" y "bom dia".
WAKE_ENGLISH_ENABLED = os.environ.get("WAKE_ENGLISH_ENABLED", "true").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)
WAKE_FRENCH_ENABLED = os.environ.get("WAKE_FRENCH_ENABLED", "true").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)
WAKE_PORTUGUESE_ENABLED = os.environ.get(
    "WAKE_PORTUGUESE_ENABLED", "true"
).strip().lower() in ("1", "true", "yes", "on", "si", "sí")
# Frases que despiertan a MECH EN INGLÉS. Se incluyen las variantes de cómo
# suele transcribir Whisper esas palabras cuando todavía está escuchando en
# español ("weik ap mech", "gueik ap mech").
VOICE_WAKE_PHRASES_EN = [
    p.strip() for p in os.environ.get(
        "VOICE_WAKE_PHRASES_EN",
        "wake up mech,wake up,wakeup mech,wake mech,weik ap mech,gueik ap mech",
    ).split(",") if p.strip()
]
# Frases que ponen a MECH en reposo estando en modo inglés.
VOICE_SLEEP_PHRASES_EN = [
    p.strip() for p in os.environ.get(
        "VOICE_SLEEP_PHRASES_EN",
        "stop listening,go to sleep,sleep mech,stop mech,goodbye mech,"
        "good night mech,rest mech,go back to sleep",
    ).split(",") if p.strip()
]
# Frases que despiertan a MECH EN FRANCÉS. "bonjour" y "salut" están a
# propósito: son las que un francófono suelta primero, y Whisper las
# reconoce aunque esté escuchando en español (se incluyen las variantes de
# cómo suele escribirlas en ese caso).
VOICE_WAKE_PHRASES_FR = [
    p.strip() for p in os.environ.get(
        "VOICE_WAKE_PHRASES_FR",
        "bonjour mech,bon jour mech,bonyur mech,salut mech,"
        "reveille mech,reveille toi mech,reveil mech",
    ).split(",") if p.strip()
]
# Frases que ponen a MECH en reposo estando en modo francés.
# NO uses "dors mech" a secas: "dors" queda a una letra de "dos" y cualquier
# frase con un "dos" ("avanza dos segundos, MECH") lo dormiría.
VOICE_SLEEP_PHRASES_FR = [
    p.strip() for p in os.environ.get(
        "VOICE_SLEEP_PHRASES_FR",
        "arrete d ecouter,arrete mech,au revoir mech,bonne nuit mech,"
        "endors toi,va dormir mech,mets toi en veille",
    ).split(",") if p.strip()
]
# Frases que despiertan a MECH EN PORTUGUÉS. Nada de "olá MECH": "ola" cae
# dentro de "hola" y el saludo español despertaría en portugués.
VOICE_WAKE_PHRASES_PT = [
    p.strip() for p in os.environ.get(
        "VOICE_WAKE_PHRASES_PT",
        "bom dia mech,bon dia mech,boa tarde mech,acorda mech,"
        "acorde mech,acordar mech",
    ).split(",") if p.strip()
]
# Frases que ponen a MECH en reposo estando en modo portugués.
VOICE_SLEEP_PHRASES_PT = [
    p.strip() for p in os.environ.get(
        "VOICE_SLEEP_PHRASES_PT",
        "para de ouvir,deixa de ouvir,boa noite mech,dorme mech,vai dormir,"
        "descansa mech,modo repouso",
    ).split(",") if p.strip()
]

# Micrófono de entrada. Vacío = dispositivo por defecto del sistema.
# Se puede poner el índice (número) o parte del nombre del dispositivo.
# El mic del proyecto es el Steren MIC-9010 (receptor USB); la C930e queda
# solo para video. Lista los dispositivos con:
#   python -c "import sounddevice as sd; print(sd.query_devices())"
# y pon aquí "Steren", "MIC-9010" o el número que corresponda.
AUDIO_INPUT_DEVICE = os.environ.get("AUDIO_INPUT_DEVICE", "")
# Segundos de silencio antepuestos a cada respuesta TTS. Compensa el
# arranque lento de parlantes Bluetooth (que se comen la primera palabra).
# Súbelo si el parlante sigue cortando el inicio.
AUDIO_LEAD_SILENCE = float(os.environ.get("AUDIO_LEAD_SILENCE", "1.0"))
# --- Volumen de la VOZ ----------------------------------------------------
# Parlantes pequeños (los Logitech S150 son 1.2 W por canal, contra los ~30 W
# de un JBL Charge 5) se quedan cortos en un stand con gente alrededor. Estas
# dos claves exprimen lo que se puede por software, ANTES de mandar el audio
# al reproductor, así funcionan con pw-play, paplay y ffplay por igual.
#
# 1) Normalizar: cada frase sale al mismo nivel, pegada al máximo. ElevenLabs
#    no entrega el audio a tope, así que esto solo ya se nota. Es gratis en
#    calidad: solo escala, no distorsiona.
TTS_NORMALIZE = os.environ.get("TTS_NORMALIZE", "true").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)
# 2) Empuje extra en decibelios por encima de lo normalizado. Como ya está al
#    máximo, subir de aquí SATURARÍA — por eso se aplica con un limitador
#    suave que redondea los picos en vez de recortarlos en seco. Eso sube el
#    volumen PERCIBIDO sin que la voz suene rota.
#    0 = solo normalizar. +6 se nota bastante. Por encima de +12 la voz
#    empieza a sonar apretada; si con eso no alcanza, el problema es el
#    parlante y hace falta uno amplificado.
TTS_GAIN_DB = float(os.environ.get("TTS_GAIN_DB", "0"))

# Volumen (0-100) de la música de fondo bajo la narración (solo obras con
# música, ej. Malpaís). Bajo a propósito para que la voz quede por encima.
BACKGROUND_MUSIC_VOLUME = int(os.environ.get("BACKGROUND_MUSIC_VOLUME", "18"))

# Subtítulos de la narración en la pantalla de proyección (estilo cine:
# abajo, centrados). Se muestran haya video, imagen o nada. Van siempre en el
# idioma activo, porque son el guion que Claude acaba de generar.
SUBTITLES_ENABLED = os.environ.get("SUBTITLES_ENABLED", "true").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)

# Proyección
PROJECTOR_DISPLAY = os.environ.get("PROJECTOR_DISPLAY", ":0")
IMAGE_OUTPUT_DIR = Path(os.environ.get("IMAGE_OUTPUT_DIR", BASE_DIR / "generated_images"))
IMAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Biblioteca de videos pre-renderizados (Opción B).
# Cada obra vive en un subdirectorio (slug) con archivos seg01.mp4, seg02.mp4, ...
# Ver backend/video_library.py para el manifest y backend/video_library/README.md.
VIDEO_LIBRARY_DIR = Path(os.environ.get("VIDEO_LIBRARY_DIR", BASE_DIR / "video_library"))
VIDEO_LIBRARY_DIR.mkdir(parents=True, exist_ok=True)


def _bool_env(key: str, default: str) -> bool:
    return os.environ.get(key, default).strip().lower() in (
        "1", "true", "yes", "on", "si", "sí",
    )


# === Visión (Logitech C930e + MediaPipe) =====================================
# Detección de usuarios frente al robot: presencia, posición y distancia
# estimada (por el tamaño de la cara). Ver backend/vision.py.
VISION_ENABLED = _bool_env("VISION_ENABLED", "false")
# Índice de la cámara para OpenCV (/dev/videoN en la Pi; 0 = primera).
VISION_CAMERA_INDEX = int(os.environ.get("VISION_CAMERA_INDEX", "0"))
# Distancia mínima (metros) a la que debe estar un usuario para que MECH
# proyecte y deje de acercarse. Ajustable en vivo desde el panel (Ajustes).
VISION_MIN_DISTANCE = float(os.environ.get("VISION_MIN_DISTANCE", "1.2"))
# Si true, MECH avanza hacia el usuario hasta quedar a VISION_MIN_DISTANCE.
# Solo se mueve cuando NO está narrando (fases waiting/dormant).
VISION_APPROACH = _bool_env("VISION_APPROACH", "true")
# SIN EFECTO desde jul 2026: el robot ya no gira hacia el usuario (las
# mecanum solo van bien adelante/atrás; girar es manual desde el panel).
# La clave se conserva por compatibilidad con .env existentes.
VISION_FOLLOW = _bool_env("VISION_FOLLOW", "false")
# Si true, NO se proyectan visuales cuando no hay un usuario dentro de la
# distancia mínima (la cámara manda: sin usuario cerca = sin proyección).
# ⚠️ APAGADO por defecto (jul 2026): con la visión encendida podía suprimir
# TODA la proyección si la cámara no detectaba al usuario dentro de la
# distancia (p. ej. operando desde el laptop, o con el detector Haar que
# estima mal la distancia). Actívalo solo si de verdad querés ese
# comportamiento y ya calibraste la distancia mínima.
VISION_PROJECT_GATE = _bool_env("VISION_PROJECT_GATE", "false")
# Velocidad máxima (0-100) de los movimientos autónomos de visión.
# POTENCIA MÁXIMA (sep 2026, pedido del equipo): TODO lo que mueve ruedas
# va a 100. Con estos motores y el L298N, menos de 100 normalmente solo
# zumba. Los BRAZOS son la excepción (van suaves, ver ARM_*).
VISION_MAX_SPEED = int(os.environ.get("VISION_MAX_SPEED", "100"))

# --- Gesto "67": MECH lo imita si alguien lo hace ante la cámara ----------
# Pedido del equipo (sep 2026). El gesto son las DOS manos (o los dos brazos)
# moviéndose en vertical, una arriba y otra abajo, ALTERNANDO. Todo el detector
# está en backend/gesture_detect.py, que explica por qué se mide movimiento y
# no color ni esqueleto.
#
# ⚠️ Los umbrales de abajo se midieron contra los dos videos del equipo Y
# contra cinco negativos (quieto, una mano, dos manos a la vez, manos en
# horizontal, alguien caminando). Si los tocás, volvé a pasar las dos listas:
# `python scripts/probar_gesto67.py`. Aflojar para pillar un caso rompe el
# otro lado enseguida.
GESTURE67_ENABLED = _bool_env("GESTURE67_ENABLED", "true")
# Cuántos segundos de gesto se miran a la vez. Más corto = reacciona antes
# pero se confunde más; más largo = pide que insistan.
GESTURE67_WINDOW = float(os.environ.get("GESTURE67_WINDOW", "1.6"))
# Cuánto tiene que subir y bajar cada lado, como fracción del alto del cuadro.
# Subilo si dispara con gestos pequeños; bajalo si hay que exagerar mucho.
GESTURE67_MIN_AMPLITUDE = float(os.environ.get("GESTURE67_MIN_AMPLITUDE", "0.10"))
# Correlación máxima entre las dos alturas. NEGATIVA a propósito: es lo que
# exige la ANTIFASE (una sube mientras la otra baja) y lo que distingue este
# gesto de levantar las dos manos a la vez. Más cerca de -1 = más estricto.
GESTURE67_MAX_CORR = float(os.environ.get("GESTURE67_MAX_CORR", "-0.30"))
# Cuántas veces tienen que intercambiarse (cuál va más arriba) dentro de la
# ventana. Con 3 hace falta repetirlo; con 1 dispararía un cruce cualquiera.
GESTURE67_MIN_ALTERNATIONS = int(os.environ.get("GESTURE67_MIN_ALTERNATIONS", "3"))
# Movimiento mínimo en el cuadro (fracción de píxeles) para mirar siquiera.
GESTURE67_MIN_MOTION = float(os.environ.get("GESTURE67_MIN_MOTION", "0.010"))
# Equilibrio mínimo entre los dos lados (0-1). Es lo que descarta saludar con
# UNA sola mano, que deja casi todo el movimiento de un lado.
GESTURE67_BALANCE = float(os.environ.get("GESTURE67_BALANCE", "0.20"))
# Segundos de descanso tras imitarlo, para no encadenar imitaciones.
GESTURE67_COOLDOWN = float(os.environ.get("GESTURE67_COOLDOWN", "12"))
# --- Cómo lo hace MECH con sus brazos (video 2 del equipo) ---------------
# Un brazo arriba y el otro en reposo, intercambiándose. Sube solo por encima
# de 90°: por debajo el brazo choca con el cuerpo (ver gestures.py).
GESTURE67_ARM_HIGH = int(os.environ.get("GESTURE67_ARM_HIGH", "165"))
# Lo que tarda CADA intercambio. Bajo = más enérgico; los MG996R no bajan
# mucho de 0.3 s sin quedarse a medio camino.
GESTURE67_ARM_SECONDS = float(os.environ.get("GESTURE67_ARM_SECONDS", "0.45"))
# Cuántos intercambios hace (un "6-7" completo son 4-6).
GESTURE67_REPEATS = int(os.environ.get("GESTURE67_REPEATS", "4"))
# Si además lo dice en voz alta ("¡Seis... siete!"). Ver lang.py.
GESTURE67_SAY = _bool_env("GESTURE67_SAY", "true")


def assert_required() -> None:
    """Falla rápido si falta alguna API key crítica."""
    missing = []
    if not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not ELEVENLABS_API_KEY:
        missing.append("ELEVENLABS_API_KEY")
    if not GOOGLE_API_KEY:
        missing.append("GOOGLE_API_KEY")
    if missing:
        raise RuntimeError(
            f"Faltan variables de entorno: {', '.join(missing)}. "
            "Copia backend/.env.example a backend/.env y rellénalas."
        )


def update_env_file(updates: dict[str, str]) -> None:
    """Reescribe backend/.env aplicando `updates` (clave -> valor).

    - Conserva comentarios y líneas no tocadas.
    - Si una clave ya existe, reemplaza su valor; si no, la añade al final.
    - Usado por el panel web (vista Ajustes) para persistir cambios sin
      tener que editar el archivo a mano por SSH.

    OJO: la mayoría de las constantes de este módulo se leen UNA vez al
    importar. Escribir el .env no las cambia en caliente — para eso el
    endpoint también hace setattr() sobre las que sí son seguras en vivo.
    Las demás (API keys, modelo, sample rate, dispositivo) requieren
    reiniciar el servidor.
    """
    lines: list[str] = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()

    remaining = dict(updates)
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in remaining:
                out.append(f"{key}={remaining.pop(key)}")
                continue
        out.append(line)

    # Claves nuevas que no existían en el archivo.
    for key, value in remaining.items():
        out.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
