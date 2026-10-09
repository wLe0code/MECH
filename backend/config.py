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
# Cuántas veces llega el brazo ARRIBA al saludar (las «rotaciones» que se
# cuentan mirando el robot), contando la subida inicial. 3 = sube, agita dos
# veces más y baja. Pedido del equipo (sep 2026): "exactamente 3 rotaciones
# del brazo derecho hacia adelante". El mínimo es 2: con 1 no se lee como
# saludo.
# Vale para el saludo de bienvenida Y para el giro hacia afuera: es el
# mismo número, cambia solo la amplitud del arco.
ARM_WAVE_REPEATS = max(2, int(os.environ.get("ARM_WAVE_REPEATS", "3")))
# El saludo mueve SOLO EL BRAZO DERECHO (sep 2026). Con los dos se leía más
# como "manos arriba" que como un saludo. En true, el izquierdo sube a
# acompañar.
ARM_WAVE_BOTH = os.environ.get("ARM_WAVE_BOTH", "false").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)
# Sentido de giro de cada brazo, igual que DIR_FL/FR/BL/BR hacen con las
# ruedas en el .ino.
#
# Todo el código de gestos piensa en "90 = reposo, más de 90 = levantado
# hacia adelante". Si la bocina del servo está montada del otro lado, el
# brazo sube al BAJAR el ángulo y TODOS los gestos salen al revés (hacia
# atrás). Esto le da la vuelta al recorrido sin tocar el firmware ni
# desmontar el brazo (el reposo se queda en 90 en los dos casos).
#
# El DERECHO va invertido por defecto (sep 2026): el equipo reportó que
# saludaba hacia el lado contrario. Si en el robot sale hacia atrás, se
# cambia en vivo desde Ajustes → «Sentido brazos», sin reiniciar.
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
# Cuánto tiene que MANTENERSE una cara en la cámara para contar como una
# persona de verdad (segundos). Antes bastaba UN fotograma: un reflejo o una
# sombra que el detector confundía un instante ya era "llegó alguien", y MECH
# saludaba sin nadie delante (oct 2026). Los fotogramas sin cara descuentan,
# así que un falso positivo suelto nunca llega a la cuenta. 0 = como antes.
GREETING_CONFIRM_SECONDS = float(os.environ.get("GREETING_CONFIRM_SECONDS", "1.0"))
# Idioma del SALUDO (la frase que MECH suelta al ver llegar a alguien estando
# en reposo). ESPAÑOL por defecto (oct 2026, pedido del equipo): en reposo
# MECH está en español, así que saluda en español. En sep 2026 estuvo en
# inglés; se puede volver a cambiar desde Ajustes → «Idioma del saludo».
#
# ⚠️ Esto NO cambia el idioma de MECH: solo el de esa frase. El idioma lo
# sigue decidiendo la frase con la que se le despierta, y en reposo MECH
# vuelve siempre a español (ver backend/lang.py).
# Vacío o desconocido = el idioma activo.
GREETING_LANGUAGE = os.environ.get("GREETING_LANGUAGE", "es").strip().lower()
# El saludo SOLO se dispara con MECH EN REPOSO (decisión del equipo,
# sep 2026). Despierto está narrando, conversando o traduciendo, y soltar
# "¡Hola! Soy MECH" encima de eso corta la experiencia del visitante que ya
# está atendiendo. En reposo, en cambio, es justo lo que se quiere: alguien
# se acerca al stand y MECH lo recibe.
# Vale también para el botón «SALUDAR AHORA» del panel: la regla es una sola.
# Y aunque esto se apague, MECH NUNCA saluda mientras presenta algo (narra,
# proyecta marketing, piensa o graba): eso no es configurable.
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
# La media vuelta es UN SOLO tramo de `vy` (el mismo movimiento de los botones
# «GIRO» del panel) sostenido hasta que el robot queda de espaldas. NO se usa
# `w`: en el suelo del stand hacía "un movimiento raro y muy corto" — con
# estas ruedas el que gira de verdad es `vy` (sep 2026). Por eso en el panel
# los botones de GIRO mandan `vy` y los LATERALES mandan `w`.
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
# Sentido de ADELANTE/ATRÁS (sep 2026). El equipo probó el panel y el botón
# «AVANZAR» iba hacia atrás. Es el mismo MOVE que usan «avanza diez
# segundos», acercarse al visitante y la vuelta al punto de inicio, así que
# se corrige AQUÍ, una sola vez para todos, en `arduino_link.move()`: el
# código sigue pensando en "vx positivo = adelante" y el odómetro también.
# Si algún día vuelve a salir al revés (otra batería, otros motores), se
# cambia en vivo desde Ajustes → «Adelante/atrás invertido», sin reflashear.
# Ojo: el COMANDO CRUDO del panel va tal cual al Arduino, sin esta inversión.
DRIVE_INVERT_FORWARD = os.environ.get("DRIVE_INVERT_FORWARD", "true").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)

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
VOICE_SLEEP_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_SLEEP_PHRASES",
        "para de escuchar,deja de escuchar,para de recibir,ya no escuches,"
        "duermete,duerme,descansa mech,ponte en reposo,modo reposo",
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
        "vuelve a tu posicion,regresa a la proyeccion,ponte a proyectar,"
        "vuelve a la proyeccion,voltea hacia la proyeccion,"
        "mira hacia la proyeccion,mira a la proyeccion",
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
VOICE_TRANSLATE_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_TRANSLATE_PHRASES",
        "traduce mech,traduci mech,modo traductor,activa el traductor,"
        "quiero traducir,ponte a traducir,traductor mech",
    ).split(",") if p.strip()
]
VOICE_TRANSLATE_PHRASES_EN = [
    p.strip() for p in os.environ.get(
        "VOICE_TRANSLATE_PHRASES_EN",
        "translate mech,translation mode,translator mode,start translating",
    ).split(",") if p.strip()
]
VOICE_TRANSLATE_PHRASES_FR = [
    p.strip() for p in os.environ.get(
        "VOICE_TRANSLATE_PHRASES_FR",
        "traduis mech,mode traducteur,traduire mech,active le traducteur",
    ).split(",") if p.strip()
]
VOICE_TRANSLATE_PHRASES_PT = [
    p.strip() for p in os.environ.get(
        "VOICE_TRANSLATE_PHRASES_PT",
        "traduz mech,modo tradutor,traduzir mech,ativa o tradutor",
    ).split(",") if p.strip()
]
# Frases para SALIR del modo traductor. Dormirlo también lo saca.
VOICE_TRANSLATE_STOP_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_TRANSLATE_STOP_PHRASES",
        "deja de traducir,para de traducir,termina la traduccion,"
        "sal del traductor,sal del modo traductor,fin de la traduccion",
    ).split(",") if p.strip()
]
VOICE_TRANSLATE_STOP_PHRASES_EN = [
    p.strip() for p in os.environ.get(
        "VOICE_TRANSLATE_STOP_PHRASES_EN",
        "stop translating,stop the translation,exit translator,end translation",
    ).split(",") if p.strip()
]
VOICE_TRANSLATE_STOP_PHRASES_FR = [
    p.strip() for p in os.environ.get(
        "VOICE_TRANSLATE_STOP_PHRASES_FR",
        "arrete de traduire,fin de la traduction,quitte le traducteur",
    ).split(",") if p.strip()
]
VOICE_TRANSLATE_STOP_PHRASES_PT = [
    p.strip() for p in os.environ.get(
        "VOICE_TRANSLATE_STOP_PHRASES_PT",
        "para de traduzir,fim da traducao,sai do tradutor",
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

# --- Modo TRIVIA: el juego de preguntas (ver backend/trivia.py) ----------
# Al terminar de narrar una obra, MECH ofrece jugar una trivia sobre lo que
# acaba de contar. Se proyecta la pregunta con tres opciones y el visitante
# contesta en voz alta ("la A", "la segunda", o diciendo la opción).
TRIVIA_ENABLED = os.environ.get("TRIVIA_ENABLED", "true").strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)
# Cuántas preguntas por partida. Tres es lo que aguanta la gente en un stand
# con cola; con más, se van a la mitad.
TRIVIA_QUESTIONS = int(os.environ.get("TRIVIA_QUESTIONS", "3"))
# ¿Ofrecerla sola al terminar una narración? Si se apaga, la trivia sigue
# disponible pidiéndola ("juguemos una trivia").
TRIVIA_OFFER_AFTER_PLAN = os.environ.get(
    "TRIVIA_OFFER_AFTER_PLAN", "true"
).strip().lower() in (
    "1", "true", "yes", "on", "si", "sí",
)
# Segundos de espera tras cada cosa que dice MECH antes de volver a escuchar.
# Es el mismo problema del traductor: el parlante (sobre todo por Bluetooth)
# arrastra buffer y se oiría a sí mismo contestando.
TRIVIA_DRAIN_SECONDS = float(os.environ.get("TRIVIA_DRAIN_SECONDS", "0.8"))
# Cuánto se queda en pantalla el marcador final antes de limpiar.
TRIVIA_FINAL_SECONDS = float(os.environ.get("TRIVIA_FINAL_SECONDS", "8.0"))
# Modelo para GENERAR las preguntas. Vacío = el mismo de las narraciones.
CLAUDE_TRIVIA_MODEL = (
    os.environ.get("CLAUDE_TRIVIA_MODEL", "").strip() or CLAUDE_MODEL
)

# Frases para pedir la trivia en cualquier momento.
VOICE_TRIVIA_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_TRIVIA_PHRASES",
        "juguemos una trivia,jugamos una trivia,quiero jugar la trivia,"
        "hagamos una trivia,empieza la trivia,inicia la trivia,"
        "ponme una trivia,quiero una trivia,modo trivia,juego de preguntas",
    ).split(",") if p.strip()
]
VOICE_TRIVIA_PHRASES_EN = [
    p.strip() for p in os.environ.get(
        "VOICE_TRIVIA_PHRASES_EN",
        "let's play a trivia,play the trivia,start the trivia,"
        "quiz me,trivia mode,i want a quiz",
    ).split(",") if p.strip()
]
VOICE_TRIVIA_PHRASES_FR = [
    p.strip() for p in os.environ.get(
        "VOICE_TRIVIA_PHRASES_FR",
        "jouons au quiz,lance le quiz,mode quiz,je veux un quiz",
    ).split(",") if p.strip()
]
VOICE_TRIVIA_PHRASES_PT = [
    p.strip() for p in os.environ.get(
        "VOICE_TRIVIA_PHRASES_PT",
        "vamos jogar o quiz,comeca o quiz,modo quiz,quero um quiz",
    ).split(",") if p.strip()
]
# Frases para SALIR del juego. Dormirlo y el paro también lo sacan.
VOICE_TRIVIA_STOP_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_TRIVIA_STOP_PHRASES",
        "sal de la trivia,salir de la trivia,deja la trivia,"
        "termina la trivia,para la trivia,ya no quiero jugar,"
        "cancela la trivia,basta de trivia",
    ).split(",") if p.strip()
]
VOICE_TRIVIA_STOP_PHRASES_EN = [
    p.strip() for p in os.environ.get(
        "VOICE_TRIVIA_STOP_PHRASES_EN",
        "stop the trivia,quit the trivia,exit the trivia,"
        "stop the quiz,i don't want to play",
    ).split(",") if p.strip()
]
VOICE_TRIVIA_STOP_PHRASES_FR = [
    p.strip() for p in os.environ.get(
        "VOICE_TRIVIA_STOP_PHRASES_FR",
        "arrete le quiz,quitte le quiz,je ne veux plus jouer",
    ).split(",") if p.strip()
]
VOICE_TRIVIA_STOP_PHRASES_PT = [
    p.strip() for p in os.environ.get(
        "VOICE_TRIVIA_STOP_PHRASES_PT",
        "para o quiz,sai do quiz,nao quero mais jogar",
    ).split(",") if p.strip()
]
# Sí / no, para contestar a "¿quieres jugar una trivia?". Cortas a propósito:
# solo se miran cuando MECH acaba de preguntar algo.
VOICE_YES_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_YES_PHRASES",
        "si,claro,dale,vale,bueno,de acuerdo,por supuesto,obvio,"
        "esta bien,me apunto,juguemos,vamos,ok",
    ).split(",") if p.strip()
]
# "ok" va en la lista de CADA idioma (también en las de alemán, italiano,
# japonés, ruso y chino, más abajo): se dice igual en todos, y desde que cada
# idioma solo mira su propia lista (VOICE_STRICT_LANGUAGE) ya no lo hereda
# de la española.
VOICE_YES_PHRASES_EN = [
    p.strip() for p in os.environ.get(
        "VOICE_YES_PHRASES_EN",
        "yes,yeah,sure,of course,okay,ok,let's go,why not",
    ).split(",") if p.strip()
]
VOICE_YES_PHRASES_FR = [
    p.strip() for p in os.environ.get(
        "VOICE_YES_PHRASES_FR",
        "oui,bien sur,d'accord,ok,allons y,pourquoi pas",
    ).split(",") if p.strip()
]
VOICE_YES_PHRASES_PT = [
    p.strip() for p in os.environ.get(
        "VOICE_YES_PHRASES_PT",
        "sim,claro,vamos,esta bem,ok,com certeza",
    ).split(",") if p.strip()
]
VOICE_NO_PHRASES = [
    p.strip() for p in os.environ.get(
        "VOICE_NO_PHRASES",
        "no,no gracias,ahora no,mejor no,paso,otro dia,no quiero",
    ).split(",") if p.strip()
]
VOICE_NO_PHRASES_EN = [
    p.strip() for p in os.environ.get(
        "VOICE_NO_PHRASES_EN",
        "no,no thanks,not now,maybe later,nope",
    ).split(",") if p.strip()
]
VOICE_NO_PHRASES_FR = [
    p.strip() for p in os.environ.get(
        "VOICE_NO_PHRASES_FR",
        "non,non merci,pas maintenant,plus tard",
    ).split(",") if p.strip()
]
VOICE_NO_PHRASES_PT = [
    p.strip() for p in os.environ.get(
        "VOICE_NO_PHRASES_PT",
        "nao,nao obrigado,agora nao,depois",
    ).split(",") if p.strip()
]

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
# Los COMANDOS solo valen en el idioma con el que se despertó a MECH (oct
# 2026, pedido del equipo). Despierto con «wake up MECH», lo corta «hey MECH»
# y NO «oye MECH»; despierto con «ok MECH», al revés. Vale para todo lo que se
# reconoce por frase: interrumpir, dormir, moverse, marketing, traductor,
# trivia y el sí/no. Y el idioma queda fijo hasta que se duerme: decir la
# frase de despertar de OTRO idioma estando despierto ya no lo cambia.
# En false vuelve lo de antes: se aceptan las frases de todos los idiomas a
# la vez. Ver `voice_phrases._frases_activas()`.
VOICE_STRICT_LANGUAGE = os.environ.get(
    "VOICE_STRICT_LANGUAGE", "true"
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
        "stop listening,go to sleep,sleep mech,stop mech,goodbye mech",
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
        "arrete d ecouter,arrete mech,au revoir mech,bonne nuit mech,endors toi",
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
        "para de ouvir,deixa de ouvir,boa noite mech,dorme mech,vai dormir",
    ).split(",") if p.strip()
]

# --- Idiomas añadidos en oct 2026: alemán, italiano, japonés, ruso y mandarín
# Mismo mecanismo que los de arriba: cada uno se activa SI Y SOLO SI se le
# despierta en ese idioma, y al dormirse MECH vuelve solo a español.
#
#   "guten Tag MECH" / "wach auf MECH"      -> alemán    (de)
#   "ciao MECH" / "buongiorno MECH"         -> italiano  (it)
#   "こんにちは MECH" / "起きて MECH"          -> japonés   (ja)
#   "привет MECH" / "проснись MECH"         -> ruso      (ru)
#   "你好 MECH" / "醒醒 MECH"                 -> mandarín  (zh)
#
# Los cinco están dentro de lo que sabe hablar la voz (`eleven_multilingual_v2`
# de ElevenLabs) y de lo que entiende Whisper.
#
# Van todos juntos aquí, agrupados por idioma, en vez de repartidos lista por
# lista: son 14 listas por idioma y así se revisa un idioma entero de un
# vistazo. Cada una se puede tapar desde el `.env` con su misma clave.
#
# ⚠️ Colisiones que YA se evitaron (medidas con scripts/probar_idiomas.py):
#   - Nada de "hallo MECH" en alemán: "hallo" queda a una letra de "hello", y
#     un "hello MECH" en inglés despertaría a MECH en alemán.
#   - Nada de "voltati" en italiano: cae en el español "voltea", y «voltea
#     hacia la proyección» lo haría girar hacia AFUERA.
#   - Nada de "buona notte MECH" en dos palabras: «buena nota, MECH» lo dormía.
#   - En ruso, "включи переводчик" (enciende) y "выключи переводчик" (apaga)
#     están a una letra: por eso ninguna de las dos está en las listas.
def _frases(clave: str, por_defecto: str) -> list[str]:
    """Lista de frases separadas por coma, leída del `.env` si está ahí."""
    return [p.strip() for p in os.environ.get(clave, por_defecto).split(",") if p.strip()]


def _activo(clave: str, por_defecto: str = "true") -> bool:
    return os.environ.get(clave, por_defecto).strip().lower() in (
        "1", "true", "yes", "on", "si", "sí",
    )


WAKE_GERMAN_ENABLED = _activo("WAKE_GERMAN_ENABLED")
WAKE_ITALIAN_ENABLED = _activo("WAKE_ITALIAN_ENABLED")
WAKE_JAPANESE_ENABLED = _activo("WAKE_JAPANESE_ENABLED")
WAKE_RUSSIAN_ENABLED = _activo("WAKE_RUSSIAN_ENABLED")
WAKE_CHINESE_ENABLED = _activo("WAKE_CHINESE_ENABLED")
# Coreano (6 oct 2026, pedido del equipo): el décimo idioma.
#   "안녕 MECH" (annyeong) / "일어나 MECH" (ireona)  -> coreano (ko)
WAKE_KOREAN_ENABLED = _activo("WAKE_KOREAN_ENABLED")

# Cómo escribe Whisper el nombre "MECH" cuando transcribe en una escritura que
# no es la latina. En japonés, ruso o chino el nombre no sale siempre como
# "MECH": sale como suena («メック», «мек», «麦克», «멕»). Cualquier frase de
# las listas que lleve la palabra "mech" acepta también estas formas.
# Si en el panel ves «Oí en japonés: '…'» con el nombre escrito de otra manera,
# añádela aquí (sin tocar el código).
# Las coreanas de UNA sílaba («멕», «맥») solo valen sueltas o con una sílaba
# pegada («멕아»): dentro de otra palabra no («멕시코» es México).
VOICE_NAME_ALIASES = _frases(
    "VOICE_NAME_ALIASES",
    "メック,メッチ,メク,メカ,メッカ,メッシュ,"
    "麦克,麥克,梅克,迈克,邁克,美克,麦可,"
    "мех,мек,мэк,мэч,меч,мэх,мекх,"
    "메크,멕크,맥크,메카,메치,메흐,멕,맥",
)

# ---- Alemán (de) ----------------------------------------------------------
VOICE_WAKE_PHRASES_DE = _frases(
    "VOICE_WAKE_PHRASES_DE",
    "guten tag mech,guten morgen mech,guten abend mech,wach auf mech,"
    "aufwachen mech,servus mech",
)
VOICE_SLEEP_PHRASES_DE = _frases(
    "VOICE_SLEEP_PHRASES_DE",
    "hör auf zuzuhören,nicht mehr zuhören,gute nacht mech,"
    "auf wiedersehen mech,schlaf mech,geh schlafen,ruhemodus",
)
VOICE_INTERRUPT_PHRASES_DE = _frases(
    "VOICE_INTERRUPT_PHRASES_DE",
    "entschuldigung mech,warte mech,moment mech,hör mal mech",
)
VOICE_ADVANCE_PHRASES_DE = _frases(
    "VOICE_ADVANCE_PHRASES_DE",
    "vorwärts,geh vorwärts,fahr vorwärts,nach vorne,fahr nach vorne",
)
VOICE_RETREAT_PHRASES_DE = _frases(
    "VOICE_RETREAT_PHRASES_DE",
    "rückwärts,geh zurück,fahr zurück,zurück,nach hinten",
)
VOICE_OUTWARD_PHRASES_DE = _frases(
    "VOICE_OUTWARD_PHRASES_DE",
    "schau nach draußen,schau nach außen,schau raus,dreh dich um,"
    "begrüße das publikum,begrüße die leute",
)
VOICE_PROJECT_PHRASES_DE = _frases(
    "VOICE_PROJECT_PHRASES_DE",
    "zurück zur projektion,zurück zum projizieren,zurück auf deine position,"
    "zurück an deinen platz,schau auf die leinwand",
)
VOICE_MARKETING_PHRASES_DE = _frases(
    "VOICE_MARKETING_PHRASES_DE",
    "zeig marketing,zeige marketing,spiel marketing,marketing abspielen,"
    "marketing video,marketing videos",
)
VOICE_TRANSLATE_PHRASES_DE = _frases(
    "VOICE_TRANSLATE_PHRASES_DE",
    "übersetze mech,übersetz mech,übersetzer modus,übersetzungsmodus,"
    "dolmetscher modus",
)
VOICE_TRANSLATE_STOP_PHRASES_DE = _frases(
    "VOICE_TRANSLATE_STOP_PHRASES_DE",
    "hör auf zu übersetzen,übersetzung beenden,übersetzer aus,"
    "nicht mehr übersetzen",
)
VOICE_TRIVIA_PHRASES_DE = _frases(
    "VOICE_TRIVIA_PHRASES_DE",
    "lass uns ein quiz spielen,quiz spielen,starte das quiz,quiz modus,"
    "ich will ein quiz",
)
VOICE_TRIVIA_STOP_PHRASES_DE = _frases(
    "VOICE_TRIVIA_STOP_PHRASES_DE",
    "quiz beenden,stopp das quiz,hör auf mit dem quiz,"
    "ich will nicht mehr spielen",
)
VOICE_YES_PHRASES_DE = _frases(
    "VOICE_YES_PHRASES_DE",
    "ja,klar,na klar,gerne,natürlich,auf jeden fall,okay,ok,einverstanden",
)
VOICE_NO_PHRASES_DE = _frases(
    "VOICE_NO_PHRASES_DE",
    "nein,nein danke,jetzt nicht,später,lieber nicht,kein interesse",
)

# ---- Italiano (it) --------------------------------------------------------
VOICE_WAKE_PHRASES_IT = _frases(
    "VOICE_WAKE_PHRASES_IT",
    "ciao mech,buongiorno mech,buon giorno mech,salve mech,"
    "svegliati mech,sveglia mech",
)
VOICE_SLEEP_PHRASES_IT = _frases(
    "VOICE_SLEEP_PHRASES_IT",
    "smetti di ascoltare,non ascoltare più,buonanotte mech,"
    "arrivederci mech,dormi mech,vai a dormire",
)
VOICE_INTERRUPT_PHRASES_IT = _frases(
    "VOICE_INTERRUPT_PHRASES_IT",
    "scusa mech,scusami mech,senti mech,aspetta mech,ehi mech",
)
VOICE_ADVANCE_PHRASES_IT = _frases(
    "VOICE_ADVANCE_PHRASES_IT",
    "avanti,vai avanti,vieni avanti,muoviti in avanti",
)
VOICE_RETREAT_PHRASES_IT = _frases(
    "VOICE_RETREAT_PHRASES_IT",
    "indietro,vai indietro,torna indietro,muoviti indietro",
)
VOICE_OUTWARD_PHRASES_IT = _frases(
    "VOICE_OUTWARD_PHRASES_IT",
    "guarda fuori,guarda verso l esterno,girati,saluta il pubblico,"
    "saluta la gente",
)
VOICE_PROJECT_PHRASES_IT = _frases(
    "VOICE_PROJECT_PHRASES_IT",
    "torna a proiettare,torna alla proiezione,torna al tuo posto,"
    "torna in posizione,guarda lo schermo",
)
VOICE_MARKETING_PHRASES_IT = _frases(
    "VOICE_MARKETING_PHRASES_IT",
    "mostra marketing,mostra il marketing,riproduci marketing,"
    "fai partire il marketing,video marketing,video di marketing",
)
VOICE_TRANSLATE_PHRASES_IT = _frases(
    "VOICE_TRANSLATE_PHRASES_IT",
    "traduci mech,tradurre mech,modalità traduttore,modo traduttore,"
    "attiva il traduttore",
)
VOICE_TRANSLATE_STOP_PHRASES_IT = _frases(
    "VOICE_TRANSLATE_STOP_PHRASES_IT",
    "smetti di tradurre,basta tradurre,fine della traduzione,"
    "esci dal traduttore",
)
VOICE_TRIVIA_PHRASES_IT = _frases(
    "VOICE_TRIVIA_PHRASES_IT",
    "giochiamo al quiz,facciamo un quiz,inizia il quiz,modalità quiz,"
    "voglio un quiz",
)
VOICE_TRIVIA_STOP_PHRASES_IT = _frases(
    "VOICE_TRIVIA_STOP_PHRASES_IT",
    "ferma il quiz,esci dal quiz,basta quiz,non voglio più giocare",
)
VOICE_YES_PHRASES_IT = _frases(
    "VOICE_YES_PHRASES_IT",
    "si,certo,va bene,volentieri,d'accordo,ok,certamente",
)
VOICE_NO_PHRASES_IT = _frases(
    "VOICE_NO_PHRASES_IT",
    "no,no grazie,non ora,adesso no,più tardi,meglio di no",
)

# ---- Japonés (ja) ---------------------------------------------------------
# El japonés se escribe SIN espacios, así que estas frases no se comparan
# palabra por palabra: cada trozo se busca DENTRO de lo que se oyó. Un espacio
# aquí separa trozos que tienen que aparecer los dos («マーケティング 再生» casa
# con «マーケティングを再生して»). Whisper mezcla kanji y kana a su antojo, por
# eso muchas van escritas de las dos maneras (起きて / おきて).
VOICE_WAKE_PHRASES_JA = _frases(
    "VOICE_WAKE_PHRASES_JA",
    "こんにちは mech,こんにちわ mech,おはよう mech,こんばんは mech,"
    "起きて mech,おきて mech,目を覚まして mech",
)
VOICE_SLEEP_PHRASES_JA = _frases(
    "VOICE_SLEEP_PHRASES_JA",
    "聞くのをやめて,きくのをやめて,聞かないで,おやすみ mech,さようなら mech,"
    "寝て mech,ねて mech,休んで mech,スリープモード",
)
VOICE_INTERRUPT_PHRASES_JA = _frases(
    "VOICE_INTERRUPT_PHRASES_JA",
    "ねえ mech,すみません mech,ちょっと mech,待って mech,まって mech",
)
VOICE_ADVANCE_PHRASES_JA = _frases(
    "VOICE_ADVANCE_PHRASES_JA",
    "前に進んで,前へ進んで,前進,まえにすすんで,前に行って,前へ",
)
VOICE_RETREAT_PHRASES_JA = _frases(
    "VOICE_RETREAT_PHRASES_JA",
    "後ろに下がって,後ろへ下がって,後退,下がって,うしろにさがって,バックして",
)
VOICE_OUTWARD_PHRASES_JA = _frases(
    "VOICE_OUTWARD_PHRASES_JA",
    "外を見て,外を向いて,そとをみて,振り向いて,ふりむいて,後ろを向いて,"
    "みんなに挨拶して,皆さんに挨拶して",
)
VOICE_PROJECT_PHRASES_JA = _frases(
    "VOICE_PROJECT_PHRASES_JA",
    "投影に戻って,映写に戻って,プロジェクションに戻って,元の位置に戻って,"
    "スクリーンを見て,スクリーンに戻って",
)
VOICE_MARKETING_PHRASES_JA = _frases(
    "VOICE_MARKETING_PHRASES_JA",
    "マーケティング 再生,マーケティング 見せて,マーケティング 流して,"
    "マーケティング 映して,マーケティング ビデオ,マーケティング 動画",
)
VOICE_TRANSLATE_PHRASES_JA = _frases(
    "VOICE_TRANSLATE_PHRASES_JA",
    "翻訳して mech,通訳して mech,翻訳モード,通訳モード,翻訳を始めて",
)
VOICE_TRANSLATE_STOP_PHRASES_JA = _frases(
    "VOICE_TRANSLATE_STOP_PHRASES_JA",
    "翻訳をやめて,翻訳やめて,通訳をやめて,翻訳を終了,翻訳終了",
)
VOICE_TRIVIA_PHRASES_JA = _frases(
    "VOICE_TRIVIA_PHRASES_JA",
    "クイズをしよう,クイズしよう,クイズを始めて,クイズをやりたい,"
    "クイズモード,クイズを出して",
)
VOICE_TRIVIA_STOP_PHRASES_JA = _frases(
    "VOICE_TRIVIA_STOP_PHRASES_JA",
    "クイズをやめて,クイズやめて,クイズを終了,クイズ終了,もう遊びたくない",
)
VOICE_YES_PHRASES_JA = _frases(
    "VOICE_YES_PHRASES_JA",
    "はい,うん,いいよ,いいですよ,お願いします,やります,やりたい,もちろん,オーケー,ok",
)
VOICE_NO_PHRASES_JA = _frases(
    "VOICE_NO_PHRASES_JA",
    "いいえ,結構です,けっこうです,やめておく,やめとく,やらない,いらない,"
    "また今度,だめ",
)

# ---- Ruso (ru) ------------------------------------------------------------
# El nombre va escrito "mech": el matcher acepta también cómo lo escribe
# Whisper en cirílico («мек», «мех»…, ver VOICE_NAME_ALIASES).
VOICE_WAKE_PHRASES_RU = _frases(
    "VOICE_WAKE_PHRASES_RU",
    "привет mech,здравствуй mech,здравствуйте mech,добрый день mech,"
    "доброе утро mech,проснись mech,просыпайся mech",
)
VOICE_SLEEP_PHRASES_RU = _frases(
    "VOICE_SLEEP_PHRASES_RU",
    "перестань слушать,хватит слушать,не слушай,спокойной ночи mech,"
    "до свидания mech,спи mech,иди спать,режим сна",
)
VOICE_INTERRUPT_PHRASES_RU = _frases(
    "VOICE_INTERRUPT_PHRASES_RU",
    "эй mech,извини mech,извините mech,подожди mech,послушай mech,слушай mech",
)
VOICE_ADVANCE_PHRASES_RU = _frases(
    "VOICE_ADVANCE_PHRASES_RU",
    "вперёд,иди вперёд,двигайся вперёд,езжай вперёд",
)
VOICE_RETREAT_PHRASES_RU = _frases(
    "VOICE_RETREAT_PHRASES_RU",
    "назад,иди назад,двигайся назад,отъедь назад",
)
VOICE_OUTWARD_PHRASES_RU = _frases(
    "VOICE_OUTWARD_PHRASES_RU",
    "посмотри наружу,смотри наружу,повернись,развернись,"
    "поприветствуй публику,поздоровайся с людьми",
)
VOICE_PROJECT_PHRASES_RU = _frases(
    "VOICE_PROJECT_PHRASES_RU",
    "вернись к проекции,вернись на место,вернись проецировать,"
    "назад к проекции,посмотри на экран,смотри на экран",
)
VOICE_MARKETING_PHRASES_RU = _frases(
    "VOICE_MARKETING_PHRASES_RU",
    "покажи маркетинг,включи маркетинг,запусти маркетинг,маркетинг видео,"
    "покажи marketing,включи marketing",
)
VOICE_TRANSLATE_PHRASES_RU = _frases(
    "VOICE_TRANSLATE_PHRASES_RU",
    "переведи mech,переводи mech,режим переводчика,запусти переводчик,"
    "переводчик mech",
)
VOICE_TRANSLATE_STOP_PHRASES_RU = _frases(
    "VOICE_TRANSLATE_STOP_PHRASES_RU",
    "хватит переводить,перестань переводить,выйди из переводчика,"
    "конец перевода",
)
VOICE_TRIVIA_PHRASES_RU = _frases(
    "VOICE_TRIVIA_PHRASES_RU",
    "давай сыграем в викторину,сыграем в викторину,начни викторину,"
    "запусти викторину,режим викторины,хочу викторину",
)
VOICE_TRIVIA_STOP_PHRASES_RU = _frases(
    "VOICE_TRIVIA_STOP_PHRASES_RU",
    "останови викторину,выйди из викторины,хватит викторины,"
    "закончи викторину,не хочу больше играть",
)
VOICE_YES_PHRASES_RU = _frases(
    "VOICE_YES_PHRASES_RU",
    "да,конечно,давай,хорошо,ладно,согласен,согласна,поехали,ok",
)
VOICE_NO_PHRASES_RU = _frases(
    "VOICE_NO_PHRASES_RU",
    "нет,нет спасибо,не сейчас,не надо,потом,не хочу",
)

# ---- Chino mandarín (zh) --------------------------------------------------
# Como el japonés, se escribe sin espacios: cada trozo se busca DENTRO de lo
# que se oyó. Whisper escribe a veces en caracteres SIMPLIFICADOS y a veces en
# TRADICIONALES sin avisar, así que donde cambian van las dos formas
# (醒来 / 醒來, 翻译 / 翻譯).
VOICE_WAKE_PHRASES_ZH = _frases(
    "VOICE_WAKE_PHRASES_ZH",
    "你好 mech,您好 mech,早上好 mech,早安 mech,醒醒 mech,醒来 mech,"
    "醒來 mech,起床 mech",
)
VOICE_SLEEP_PHRASES_ZH = _frases(
    "VOICE_SLEEP_PHRASES_ZH",
    "别听了,別聽了,不要听了,不要聽了,停止聆听,停止聆聽,晚安 mech,"
    "再见 mech,再見 mech,睡觉 mech,睡覺 mech,去睡觉,去睡覺,休眠模式",
)
VOICE_INTERRUPT_PHRASES_ZH = _frases(
    "VOICE_INTERRUPT_PHRASES_ZH",
    "嘿 mech,喂 mech,打扰一下 mech,打擾一下 mech,不好意思 mech,"
    "等一下 mech,等等 mech",
)
VOICE_ADVANCE_PHRASES_ZH = _frases(
    "VOICE_ADVANCE_PHRASES_ZH",
    "前进,前進,往前走,向前走,往前,向前",
)
VOICE_RETREAT_PHRASES_ZH = _frases(
    "VOICE_RETREAT_PHRASES_ZH",
    "后退,後退,往后退,往後退,往后走,往後走,向后,向後",
)
VOICE_OUTWARD_PHRASES_ZH = _frases(
    "VOICE_OUTWARD_PHRASES_ZH",
    "向外看,往外看,看外面,转过去,轉過去,转身,轉身,向大家问好,"
    "向大家問好,跟大家打招呼",
)
VOICE_PROJECT_PHRASES_ZH = _frases(
    "VOICE_PROJECT_PHRASES_ZH",
    "回去投影,回到投影,继续投影,繼續投影,回到原位,回到你的位置,"
    "看屏幕,看螢幕,转回来,轉回來",
)
VOICE_MARKETING_PHRASES_ZH = _frases(
    "VOICE_MARKETING_PHRASES_ZH",
    "播放 营销,播放 營銷,播放 行销,播放 行銷,播放 宣传,播放 宣傳,"
    "播放 marketing,营销视频,行銷影片,宣传片,宣傳片",
)
VOICE_TRANSLATE_PHRASES_ZH = _frases(
    "VOICE_TRANSLATE_PHRASES_ZH",
    "翻译 mech,翻譯 mech,翻译模式,翻譯模式,开始翻译,開始翻譯",
)
VOICE_TRANSLATE_STOP_PHRASES_ZH = _frases(
    "VOICE_TRANSLATE_STOP_PHRASES_ZH",
    "停止翻译,停止翻譯,别翻译了,別翻譯了,不要翻译了,不要翻譯了,"
    "结束翻译,結束翻譯,退出翻译,退出翻譯",
)
VOICE_TRIVIA_PHRASES_ZH = _frases(
    "VOICE_TRIVIA_PHRASES_ZH",
    "玩问答,玩問答,问答游戏,問答遊戲,开始问答,開始問答,来个测验,"
    "來個測驗,玩个游戏,玩個遊戲",
)
VOICE_TRIVIA_STOP_PHRASES_ZH = _frases(
    "VOICE_TRIVIA_STOP_PHRASES_ZH",
    "停止问答,停止問答,退出问答,退出問答,结束问答,結束問答,不玩了,"
    "不想玩了,结束游戏,結束遊戲",
)
# Las de UN solo carácter (好, 是, 不…) solo cuentan si la respuesta es corta
# y empieza por él: si no, «你好» (hola) sería un sí.
VOICE_YES_PHRASES_ZH = _frases(
    "VOICE_YES_PHRASES_ZH",
    "好,好的,好啊,好呀,好吧,是,是的,可以,行,行吧,当然,當然,要,来吧,來吧,"
    "对,對,没问题,沒問題,ok",
)
VOICE_NO_PHRASES_ZH = _frases(
    "VOICE_NO_PHRASES_ZH",
    "不,不要,不用,不了,不行,算了,下次,以后再说,以後再說,不玩,不想",
)

# ---- Coreano (ko) ---------------------------------------------------------
# El coreano SÍ lleva espacios, pero las terminaciones van pegadas a la
# palabra y Whisper junta o separa a su antojo («앞으로 가줘» / «앞으로 가 줘»).
# Por eso se compara como el japonés y el chino: cada trozo se busca DENTRO de
# lo que se oyó, y un espacio aquí separa trozos que tienen que aparecer los
# dos («마케팅 재생» casa con «마케팅을 재생해 줘»).
# ⚠️ Un trozo de UNA sílaba dentro de una orden de varias («앞으로 가»,
# «잘 자 mech») tiene que ser la palabra ENTERA: «가» es además la partícula
# más común del idioma. Por eso van también las formas con la terminación
# pegada («앞으로 가줘», «잘자 mech»).
# ⚠️ Nada de «안녕히 주무세요 MECH» ("buenas noches") para dormirlo: lleva
# dentro «안녕», que es la frase de despertar.
VOICE_WAKE_PHRASES_KO = _frases(
    "VOICE_WAKE_PHRASES_KO",
    "안녕 mech,안녕하세요 mech,좋은 아침 mech,일어나 mech,일어나세요 mech,"
    "깨어나 mech",
)
VOICE_SLEEP_PHRASES_KO = _frases(
    "VOICE_SLEEP_PHRASES_KO",
    "그만 들어,듣지 마,듣지마,잘 자 mech,잘자 mech,잘 자요 mech,자러 가,"
    "쉬어 mech,수면 모드",
)
VOICE_INTERRUPT_PHRASES_KO = _frases(
    "VOICE_INTERRUPT_PHRASES_KO",
    "저기 mech,잠깐 mech,잠시만 mech,실례합니다 mech,기다려 mech,있잖아 mech",
)
VOICE_ADVANCE_PHRASES_KO = _frases(
    "VOICE_ADVANCE_PHRASES_KO",
    "앞으로 가,앞으로 가줘,앞으로 가요,앞으로 가세요,앞으로 이동,"
    "앞으로 움직여,전진",
)
VOICE_RETREAT_PHRASES_KO = _frases(
    "VOICE_RETREAT_PHRASES_KO",
    "뒤로 가,뒤로 가줘,뒤로 가요,뒤로 가세요,뒤로 이동,뒤로 움직여,"
    "뒤로 물러나,후진",
)
VOICE_OUTWARD_PHRASES_KO = _frases(
    "VOICE_OUTWARD_PHRASES_KO",
    "밖을 봐,밖을 봐줘,밖을 보세요,바깥을 봐,바깥을 봐줘,바깥을 보세요,"
    "뒤돌아,관객에게 인사,사람들에게 인사,사람들한테 인사",
)
VOICE_PROJECT_PHRASES_KO = _frases(
    "VOICE_PROJECT_PHRASES_KO",
    "투영으로 돌아가,프로젝션으로 돌아가,제자리로 돌아가,원래 위치로 돌아가,"
    "화면을 봐,화면을 봐줘,화면을 보세요,스크린을 봐,스크린을 봐줘,"
    "스크린을 보세요",
)
VOICE_MARKETING_PHRASES_KO = _frases(
    "VOICE_MARKETING_PHRASES_KO",
    "마케팅 재생,마케팅 보여,마케팅 틀어,마케팅 영상,마케팅 비디오,"
    "마케팅 동영상,marketing 재생",
)
VOICE_TRANSLATE_PHRASES_KO = _frases(
    "VOICE_TRANSLATE_PHRASES_KO",
    "번역해 mech,통역해 mech,번역 모드,통역 모드,번역 시작,통역 시작",
)
VOICE_TRANSLATE_STOP_PHRASES_KO = _frases(
    "VOICE_TRANSLATE_STOP_PHRASES_KO",
    "번역 그만,번역 중지,번역 종료,번역 멈춰,번역 끝,번역 끝내,"
    "통역 그만,통역 중지,통역 종료",
)
VOICE_TRIVIA_PHRASES_KO = _frases(
    "VOICE_TRIVIA_PHRASES_KO",
    "퀴즈 하자,퀴즈 할래,퀴즈 풀자,퀴즈 풀래,퀴즈 시작,퀴즈 모드,퀴즈 내줘,"
    "퀴즈 하고 싶어",
)
VOICE_TRIVIA_STOP_PHRASES_KO = _frases(
    "VOICE_TRIVIA_STOP_PHRASES_KO",
    "퀴즈 그만,퀴즈 중지,퀴즈 종료,퀴즈 멈춰,그만 할래,그만할래,"
    "더 안 할래",
)
# Las de UNA sílaba (네, 예, 응) solo cuentan si la respuesta es corta y
# empieza por ella, igual que en chino.
VOICE_YES_PHRASES_KO = _frases(
    "VOICE_YES_PHRASES_KO",
    "네,예,응,좋아,좋습니다,그래,물론,할게요,할래요,해볼게요,오케이,ok",
)
VOICE_NO_PHRASES_KO = _frases(
    "VOICE_NO_PHRASES_KO",
    "아니,싫어,안 해,안 할래,안할래,나중에,다음에,괜찮아요,됐어요",
)

# === Modo MÚSICA (ver backend/music.py) ======================================
# «modo música MECH» / «activa modo música»: MECH pregunta qué canción y de
# qué artista, la busca en el catálogo de Apple Music, la pone y al terminar
# pregunta si quiere otra. Se corta con «oye MECH», como una narración.
#
# QUÉ SUENA: el fragmento oficial de 30 segundos que Apple da de cada canción
# (buscador público, sin cuenta ni clave). Las canciones ENTERAS piden la
# cuenta de desarrollador de Apple y que el navegador de la Pi abra audio
# protegido; ver handoff.md.
#
# Va todo junto aquí (y no repartido idioma por idioma como lo demás) para
# poder revisar el modo entero de un vistazo.
MUSIC_ENABLED = _activo("MUSIC_ENABLED")
# País del catálogo donde se busca (código de dos letras de la tienda).
MUSIC_COUNTRY = os.environ.get("MUSIC_COUNTRY", "CR").strip().upper() or "CR"
# ¿Se permiten canciones marcadas como explícitas? En un stand con jueces y
# estudiantes, mejor no: por defecto se buscan solo las versiones limpias.
MUSIC_ALLOW_EXPLICIT = _activo("MUSIC_ALLOW_EXPLICIT", "false")
# Volumen de la música en la pantalla de proyección (0 a 1).
MUSIC_VOLUME = float(os.environ.get("MUSIC_VOLUME", "0.9"))
# Espera tras cada frase de MECH antes de volver a abrir el micrófono (el
# parlante Bluetooth arrastra buffer y MECH se oiría a sí mismo).
MUSIC_DRAIN_SECONDS = float(os.environ.get("MUSIC_DRAIN_SECONDS", "0.8"))
# Si en estos segundos ninguna pantalla avisa de que la canción empezó a
# sonar, se da por fallida (¿está abierta la proyección?).
MUSIC_START_TIMEOUT = float(os.environ.get("MUSIC_START_TIMEOUT", "12"))
# Tope de una canción, por si la pantalla nunca avisa de que terminó.
MUSIC_MAX_SECONDS = float(os.environ.get("MUSIC_MAX_SECONDS", "420"))
# Modelo que ENTIENDE el pedido («cheip of yu de ed chiran» → Shape of You,
# Ed Sheeran). Vacío = el mismo de las narraciones.
CLAUDE_MUSIC_MODEL = os.environ.get("CLAUDE_MUSIC_MODEL", "").strip() or CLAUDE_MODEL

# Tres listas por idioma:
#   VOICE_MUSIC_PHRASES       entrar al modo.
#   VOICE_MUSIC_STOP_PHRASES  salir. ⚠️ Tienen que ser frases que nadie diga
#                             pidiendo otra cosa: se miran SIEMPRE, también
#                             fuera del modo («para la música» no está: «para»
#                             y «música» salen en cualquier pregunta normal).
#                             Lleva también lo que MECH dice al salir, para que
#                             su propio eco se reconozca y muera en silencio.
#   VOICE_MUSIC_MORE_PHRASES  «otra canción». Solo se miran justo después de
#                             que MECH pregunta si seguimos.
# Las preguntas que MECH hace (lang.py, `music_*`) están escritas para NO
# contener ninguna de estas frases ni un sí/no: se oiría a sí mismo.
# `scripts/probar_musica.py` lo comprueba en los diez idiomas.
VOICE_MUSIC_PHRASES = _frases(
    "VOICE_MUSIC_PHRASES",
    "modo musica mech,modo musica,activa modo musica,activa el modo musica,"
    "activar modo musica,pon musica mech",
)
VOICE_MUSIC_STOP_PHRASES = _frases(
    "VOICE_MUSIC_STOP_PHRASES",
    "sal del modo musica,salir del modo musica,apaga la musica,"
    "quita la musica,deten la musica,basta de musica",
)
VOICE_MUSIC_MORE_PHRASES = _frases(
    "VOICE_MUSIC_MORE_PHRASES",
    "otra cancion,otra mas,pon otra,una mas,la siguiente,otro tema",
)
VOICE_MUSIC_PHRASES_EN = _frases(
    "VOICE_MUSIC_PHRASES_EN",
    "music mode mech,music mode,activate music mode,turn on music mode,"
    "play some music mech",
)
VOICE_MUSIC_STOP_PHRASES_EN = _frases(
    "VOICE_MUSIC_STOP_PHRASES_EN",
    "exit music mode,leave music mode,stop the music,turn off the music,"
    "no more music",
)
VOICE_MUSIC_MORE_PHRASES_EN = _frases(
    "VOICE_MUSIC_MORE_PHRASES_EN",
    "another song,another one,one more,play another,next song",
)
VOICE_MUSIC_PHRASES_FR = _frases(
    "VOICE_MUSIC_PHRASES_FR",
    "mode musique mech,mode musique,active le mode musique,"
    "mets de la musique mech",
)
VOICE_MUSIC_STOP_PHRASES_FR = _frases(
    "VOICE_MUSIC_STOP_PHRASES_FR",
    "quitte le mode musique,arrete la musique,coupe la musique,"
    "eteins la musique",
)
VOICE_MUSIC_MORE_PHRASES_FR = _frases(
    "VOICE_MUSIC_MORE_PHRASES_FR",
    "une autre chanson,encore une,une autre,la suivante",
)
VOICE_MUSIC_PHRASES_PT = _frases(
    "VOICE_MUSIC_PHRASES_PT",
    "modo musica mech,modo musica,ativa o modo musica,ativar modo musica,"
    "toca musica mech",
)
VOICE_MUSIC_STOP_PHRASES_PT = _frases(
    "VOICE_MUSIC_STOP_PHRASES_PT",
    "sai do modo musica,sair do modo musica,desliga a musica,"
    "tira a musica,chega de musica",
)
VOICE_MUSIC_MORE_PHRASES_PT = _frases(
    "VOICE_MUSIC_MORE_PHRASES_PT",
    "outra musica,outra cancao,mais uma,toca outra,a proxima",
)
VOICE_MUSIC_PHRASES_DE = _frases(
    "VOICE_MUSIC_PHRASES_DE",
    "musikmodus mech,musikmodus,musik modus,aktiviere den musikmodus,"
    "spiel musik mech",
)
VOICE_MUSIC_STOP_PHRASES_DE = _frases(
    "VOICE_MUSIC_STOP_PHRASES_DE",
    "musikmodus beenden,beende den musikmodus,stopp die musik,musik aus,"
    "mach die musik aus,keine musik mehr",
)
VOICE_MUSIC_MORE_PHRASES_DE = _frases(
    "VOICE_MUSIC_MORE_PHRASES_DE",
    "noch ein lied,noch eins,ein anderes lied,nächstes lied,noch einen song",
)
VOICE_MUSIC_PHRASES_IT = _frases(
    "VOICE_MUSIC_PHRASES_IT",
    "modalita musica mech,modalita musica,attiva la modalita musica,"
    "metti la musica mech",
)
VOICE_MUSIC_STOP_PHRASES_IT = _frases(
    "VOICE_MUSIC_STOP_PHRASES_IT",
    "esci dalla modalita musica,ferma la musica,spegni la musica,"
    "togli la musica,basta musica",
)
VOICE_MUSIC_MORE_PHRASES_IT = _frases(
    "VOICE_MUSIC_MORE_PHRASES_IT",
    "altra canzone,ancora una,la prossima,un altra",
)
# Japonés y chino van sin espacios: cada trozo se busca DENTRO de lo oído.
VOICE_MUSIC_PHRASES_JA = _frases(
    "VOICE_MUSIC_PHRASES_JA",
    "音楽モード,ミュージックモード,音楽をかけて,音楽かけて,音楽を流して",
)
VOICE_MUSIC_STOP_PHRASES_JA = _frases(
    "VOICE_MUSIC_STOP_PHRASES_JA",
    "音楽モードを終了,音楽モード終了,音楽を止め,音楽止め,音楽をやめ,"
    "音楽を消して",
)
VOICE_MUSIC_MORE_PHRASES_JA = _frases(
    "VOICE_MUSIC_MORE_PHRASES_JA",
    "もう一曲,もう1曲,別の曲,次の曲,他の曲",
)
# Ni «включи музыку» ni «выключи музыку»: están a una letra una de otra y el
# matcher las confundiría (encender ↔ apagar).
VOICE_MUSIC_PHRASES_RU = _frases(
    "VOICE_MUSIC_PHRASES_RU",
    "режим музыки mech,режим музыки,музыкальный режим,поставь музыку mech",
)
VOICE_MUSIC_STOP_PHRASES_RU = _frases(
    "VOICE_MUSIC_STOP_PHRASES_RU",
    "выйди из режима музыки,останови музыку,останавливаю музыку,"
    "убери музыку,хватит музыки",
)
VOICE_MUSIC_MORE_PHRASES_RU = _frases(
    "VOICE_MUSIC_MORE_PHRASES_RU",
    "другую песню,ещё одну,еще одну,следующую песню,поставь другую",
)
VOICE_MUSIC_PHRASES_ZH = _frases(
    "VOICE_MUSIC_PHRASES_ZH",
    "音乐模式,音樂模式,放音乐,放音樂,放首歌,来点音乐,來點音樂",
)
VOICE_MUSIC_STOP_PHRASES_ZH = _frases(
    "VOICE_MUSIC_STOP_PHRASES_ZH",
    "退出音乐模式,退出音樂模式,关闭音乐,關閉音樂,停止音乐,停止音樂,"
    "关掉音乐,關掉音樂,不听音乐了,不聽音樂了",
)
VOICE_MUSIC_MORE_PHRASES_ZH = _frases(
    "VOICE_MUSIC_MORE_PHRASES_ZH",
    "再来一首,再來一首,下一首,换一首,換一首,另一首",
)
# Coreano: un espacio separa trozos que tienen que aparecer los dos.
VOICE_MUSIC_PHRASES_KO = _frases(
    "VOICE_MUSIC_PHRASES_KO",
    "음악 모드,음악모드,뮤직 모드,음악 틀어줘,음악 틀어 줘,노래 틀어줘",
)
VOICE_MUSIC_STOP_PHRASES_KO = _frases(
    "VOICE_MUSIC_STOP_PHRASES_KO",
    "음악 모드 종료,음악 꺼줘,음악 꺼 줘,음악 끌게,음악 그만,음악 멈춰",
)
VOICE_MUSIC_MORE_PHRASES_KO = _frases(
    "VOICE_MUSIC_MORE_PHRASES_KO",
    "다른 노래,다음 노래,다음 곡,하나 더,한 곡 더,한곡 더",
)

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


# === Sismos recientes (vista «Sismos» del panel) =============================
# Un mapa con lo que YA tembló, en cuanto las redes sísmicas lo publican
# (2-10 minutos después). NO predice ni es una alerta temprana. Las fuentes
# (EMSC y USGS) son públicas y sin clave. Ver backend/sismos.py.
# Todo se cambia en vivo desde la propia vista del panel (tarjeta «Mi zona»).
SISMOS_ENABLED = _bool_env("SISMOS_ENABLED", "true")
# Cada cuántos segundos se pregunta por lo nuevo (mínimo 20). Las fuentes se
# actualizan cada minuto: bajar de 60 no trae nada antes y gasta más datos.
SISMOS_POLL_SECONDS = float(os.environ.get("SISMOS_POLL_SECONDS", "60"))
# «Mi zona»: el sitio donde está el robot. Dentro de este círculo se guardan
# también los sismos pequeños (los que la gente siente) y el panel los
# resalta y dice a cuántos km fueron. Por defecto, Costa Rica entera.
SISMOS_ZONE_NAME = os.environ.get("SISMOS_ZONE_NAME", "Costa Rica").strip() or "Mi zona"
SISMOS_ZONE_LAT = float(os.environ.get("SISMOS_ZONE_LAT", "9.9"))
SISMOS_ZONE_LON = float(os.environ.get("SISMOS_ZONE_LON", "-84.1"))
SISMOS_ZONE_RADIUS_KM = float(os.environ.get("SISMOS_ZONE_RADIUS_KM", "300"))
# Magnitud mínima que se guarda: del mundo entero y de «mi zona». Bajar la
# del mundo llena el mapa (de 2.5 para arriba son ~1700 sismos por semana).
SISMOS_MIN_MAG_WORLD = float(os.environ.get("SISMOS_MIN_MAG_WORLD", "4.0"))
SISMOS_MIN_MAG_ZONE = float(os.environ.get("SISMOS_MIN_MAG_ZONE", "2.5"))


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
