"""Visión de MECH — detección de usuarios con la Logitech C930e.

Pipeline:
  OpenCV (V4L2/USB UVC) captura a 640x360 → detector de rostros → por cada
  frame se calcula:

    - user_present : hay al menos una cara (con debounce para no parpadear).
    - x            : posición horizontal de la cara más grande, -1 (izq) .. +1 (der).
    - distance     : distancia estimada en metros, a partir del ancho de la
                     cara en píxeles (cara promedio ~16 cm; focal estimada
                     según el FOV de 90° de la C930e).

Dos backends de detección (se elige el mejor disponible automáticamente):
    1. MediaPipe Face Detection (full-range, ~5 m) — el más preciso. Requiere
       `mediapipe`, que solo tiene wheels para Python 3.11/3.12.
    2. OpenCV Haar cascade — fallback que solo necesita `opencv`. Funciona en
       cualquier Python donde OpenCV instale (incluido 3.13). Alcance algo
       menor y solo caras frontales, pero suficiente para un stand.

Comportamientos (configurables en vivo desde el panel):
    - VISION_APPROACH : MECH avanza hasta quedar a VISION_MIN_DISTANCE.
      SOLO adelante/atrás (jul 2026: el robot no gira bien en el sitio;
      VISION_FOLLOW quedó sin efecto). Solo se mueve cuando NO está
      narrando (fases waiting/dormant) y siempre manda STOP al perder al
      usuario. El desplazamiento queda en el odómetro de arduino_link y
      mech_app.return_to_start() lo revierte antes de proyectar.
    - VISION_PROJECT_GATE: lo usa mech_app — sin usuario dentro de la
      distancia mínima, no se proyectan visuales.

Los imports de cv2/mediapipe son perezosos: si no están instalados (ej. en
la laptop de desarrollo), el módulo carga igual y start() loguea el aviso.

Corre en un hilo propio para no bloquear el event loop de FastAPI.
"""

from __future__ import annotations

import math
import threading
import time

import config
from gesture_detect import SixtySevenDetector

# Parámetros de cámara / estimación de distancia.
FRAME_W = 640
FRAME_H = 360
TARGET_FPS = 10
HFOV_DEG = 90.0           # FOV horizontal de la C930e
FACE_WIDTH_M = 0.16       # ancho promedio de una cara adulta
FOCAL_PX = (FRAME_W / 2) / math.tan(math.radians(HFOV_DEG / 2))  # ≈ 320

# Tiempo sin ver caras para declarar que el usuario se fue.
LOST_AFTER_S = 1.5

# --- Aguante de la cámara (sep 2026) ---------------------------------------
# El equipo vio "la cámara se enciende un momento y se apaga". Había dos
# puntos donde el código se rendía a la primera:
#   1. al abrirla, si el PRIMER fotograma no llegaba enseguida;
#   2. ya funcionando, un solo read() fallido apagaba la visión entera.
# En la Pi los fallos sueltos pasan (USB compartido con el micrófono y el
# Arduino, un bajón de corriente de un instante), así que ahora se aguanta.
#
# Segundos que se le dan a la cámara para dar su primer fotograma.
_CALENTAMIENTO_S = 2.5
# Segundos seguidos SIN fotogramas antes de dar la cámara por caída y
# reabrirla. Menos que esto es un tropiezo y se ignora.
_SIN_IMAGEN_S = 2.0
# Cuántas veces seguidas se intenta reabrirla antes de rendirse del todo.
_REINTENTOS_REABRIR = 5
# Margen sobre la distancia mínima para no oscilar (histéresis).
APPROACH_MARGIN_M = 0.15


# ── Detectores de rostro ─────────────────────────────────────────────
# Cada detector expone detect(frame_bgr) -> lista de (cx_rel, w_rel), donde
# cx_rel es el centro X de la cara en 0..1 y w_rel su ancho en 0..1 (ambos
# relativos al ancho del frame). Así el resto del código no depende del
# backend ni de la resolución real que negocie la cámara.

class _MediaPipeDetector:
    name = "mediapipe"

    def __init__(self) -> None:
        import cv2
        import mediapipe as mp
        self._cv2 = cv2
        self._fd = mp.solutions.face_detection.FaceDetection(
            model_selection=1,  # full-range: hasta ~5 m
            min_detection_confidence=0.5,
        )

    def detect(self, frame_bgr):
        rgb = self._cv2.cvtColor(frame_bgr, self._cv2.COLOR_BGR2RGB)
        res = self._fd.process(rgb)
        faces = []
        if res.detections:
            for d in res.detections:
                bb = d.location_data.relative_bounding_box
                faces.append((bb.xmin + bb.width / 2, bb.width))
        return faces

    def close(self) -> None:
        self._fd.close()


class _HaarDetector:
    name = "opencv-haar"

    def __init__(self) -> None:
        import cv2
        self._cv2 = cv2
        if not hasattr(cv2, "CascadeClassifier"):
            # OpenCV 5 eliminó el detector Haar clásico. Necesitamos la 4.x:
            raise RuntimeError(
                f"Tu OpenCV ({getattr(cv2, '__version__', '?')}) no trae "
                "CascadeClassifier (lo quitaron en OpenCV 5). Instala la "
                "serie 4: pip install \"opencv-python-headless<5\""
            )
        path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self._cascade = cv2.CascadeClassifier(path)
        if self._cascade.empty():
            raise RuntimeError("No se pudo cargar el clasificador Haar de OpenCV")

    def detect(self, frame_bgr):
        cv2 = self._cv2
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        h, w = gray.shape[:2]
        # minNeighbors alto + minSize grande = menos falsos positivos (reflejos
        # de la proyección en la oscuridad). Una cara real a ~1-2 m en 640px es
        # bastante grande, así que exigir >=60px filtra manchas pequeñas.
        rects = self._cascade.detectMultiScale(
            gray, scaleFactor=1.2, minNeighbors=7, minSize=(60, 60)
        )
        return [((x + ww / 2) / w, ww / w) for (x, y, ww, hh) in rects]

    def close(self) -> None:
        pass


def _make_detector(app):
    """Elige MediaPipe si está; si no, cae a OpenCV Haar. Devuelve
    (detector, warn_opcional)."""
    try:
        return _MediaPipeDetector(), None
    except ImportError:
        pass
    except Exception as e:
        app.log(f"MediaPipe presente pero falló ({e}); uso OpenCV.", "warn")
    return _HaarDetector(), (
        "Visión con OpenCV Haar (sin mediapipe): funciona, pero detecta solo "
        "caras frontales y a menor distancia. Para el modo full-range instala "
        "mediapipe (Python 3.11/3.12)."
    )


class _CamaraMuerta:
    """Sustituto de una cámara que no se pudo reabrir: read() siempre falla.

    Así el bucle sigue por el mismo camino (espera, reintenta, y al final se
    rinde) en vez de necesitar un caso especial para "no hay cámara".
    """

    def read(self):
        return False, None

    def release(self):
        pass


class Vision:
    """Hilo de visión. Publica su estado en mech_app.state["vision"]."""

    def __init__(self, app) -> None:
        self.app = app
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._driving = False  # si fuimos nosotros los que mandamos MOVE
        # Gesto "67": mira los mismos fotogramas, pero por su cuenta. NO
        # depende de que se detecte la cara — con las manos delante, Haar casi
        # nunca la encuentra (ver backend/gesture_detect.py).
        self._gesto67 = SixtySevenDetector()

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        if self.running:
            return True
        try:
            import cv2  # noqa: F401
        except ImportError:
            self.app.log(
                "Visión no disponible (falta OpenCV): "
                "pip install opencv-python-headless "
                "(o -r backend/requirements-vision.txt para también mediapipe).",
                "warn",
            )
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        self._thread = None
        self._release_drive()
        self._publish(enabled=False, present=False, x=0.0, distance=None)

    # ------------------------------------------------------------------

    def _publish(self, enabled: bool, present: bool, x: float,
                 distance: float | None, paused: bool = False) -> None:
        self.app.state["vision"] = {
            "enabled": enabled,
            "user_present": present,
            "x": round(x, 2),
            "distance": round(distance, 2) if distance is not None else None,
            "min_distance": config.VISION_MIN_DISTANCE,
            "paused": paused,  # True mientras MECH narra (no se detecta)
        }
        self.app.emit("vision", **self.app.state["vision"])

    def _release_drive(self) -> None:
        """Si la visión estaba moviendo el robot, lo detiene."""
        if self._driving:
            self._driving = False
            try:
                self.app.arduino.stop_motors()
            except Exception:
                pass

    def _may_drive(self) -> bool:
        """Solo conducimos cuando MECH no está narrando ni grabando."""
        s = self.app.state
        return (
            s.get("voice_phase") in ("waiting", "dormant", "off")
            and s.get("current_mode") != "STOP"
        )

    def _abrir(self, cv2, indice: int):
        """Intenta abrir una cámara por índice y CONFIRMA que da imagen.

        ⚠️ `isOpened()` NO basta. En Linux, una misma webcam expone VARIOS
        `/dev/videoN`: el primero es la imagen y los siguientes son nodos de
        metadatos. OpenCV "abre" esos nodos sin protestar y luego no entrega
        un solo fotograma — que por fuera se ve igual que una cámara rota.
        Por eso aquí se pide un fotograma de verdad antes de dar el índice
        por bueno.
        """
        cap = cv2.VideoCapture(indice)
        if not cap.isOpened():
            cap.release()
            return None
        # Forzar MJPG: sin esto la C930e negocia YUYV y cae a ~5 fps en la Pi.
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
        cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)
        # CALENTAMIENTO: tras cambiarle el formato, la C930e tarda en dar su
        # primer fotograma (en la Pi, a veces más de medio segundo). Pedir UNO
        # solo y rendirse era el síntoma exacto que vio el equipo: «la cámara
        # se enciende un momento y se apaga» — se encendía al abrirla, el
        # primer read() fallaba por impaciencia, se cerraba y se probaba la
        # siguiente. Ahora se le dan hasta `_CALENTAMIENTO_S` segundos.
        limite = time.monotonic() + _CALENTAMIENTO_S
        while time.monotonic() < limite:
            ok, _ = cap.read()
            if ok:
                return cap
            time.sleep(0.1)
        cap.release()
        return None

    def _buscar_camara(self, cv2):
        """Abre la cámara, buscándola si el índice configurado no sirve.

        **Por qué hace falta** (sep 2026): el equipo cambió la cámara de
        puerto USB y dejó de funcionar. La causa es que `VISION_CAMERA_INDEX`
        era un número FIJO, y en Linux el número de `/dev/videoN` depende del
        orden en que se enchufan los dispositivos: al cambiar de puerto (o al
        reiniciar con el receptor del micrófono puesto) la cámara pasa de
        `video0` a `video2` y el índice guardado apunta a otra cosa.

        Es el mismo problema que ya tenía el Arduino con su puerto serie, y
        se resuelve igual: se prueba primero lo configurado y, si no da
        imagen, se barren los índices. Devuelve `(cap, indice)` o
        `(None, None)`.
        """
        preferido = config.VISION_CAMERA_INDEX
        cap = self._abrir(cv2, preferido)
        if cap is not None:
            return cap, preferido

        self.app.log(
            f"La cámara {preferido} no da imagen; busco en los demás puertos…",
            "warn",
        )
        for indice in range(0, 10):
            if indice == preferido:
                continue
            cap = self._abrir(cv2, indice)
            if cap is not None:
                self.app.log(
                    f"Cámara encontrada en el índice {indice} (el .env dice "
                    f"{preferido}). Funciona igual, pero para que no tenga que "
                    f"buscarla cada vez, poné VISION_CAMERA_INDEX={indice} en "
                    "Ajustes. OJO: si volvés a cambiarla de puerto USB, el "
                    "número cambia otra vez.",
                    "warn",
                )
                return cap, indice
        return None, None

    def _loop(self) -> None:
        import cv2

        cap, indice = self._buscar_camara(cv2)
        if cap is None:
            self.app.log(
                "No encontré NINGUNA cámara (probé los índices 0 a 9). "
                "Revisá que la C930e esté enchufada y que la Pi la vea: "
                "`v4l2-ctl --list-devices` o `ls /dev/video*`. Si la lista "
                "sale vacía, es cosa del cable, del puerto o de la corriente "
                "— no del programa.",
                "err",
            )
            self._publish(enabled=False, present=False, x=0.0, distance=None)
            return
        self.app.log(f"Cámara abierta en el índice {indice}.", "ok")

        try:
            detector, warn = _make_detector(self.app)
        except Exception as e:
            self.app.log(f"No se pudo iniciar ningún detector de rostros: {e}", "err")
            cap.release()
            self._publish(enabled=False, present=False, x=0.0, distance=None)
            return
        if warn:
            self.app.log(warn, "warn")
        self.app.log(
            f"Visión activa (detector: {detector.name}): detectando usuarios.", "ok"
        )

        # Estado suavizado.
        x_s = 0.0
        dist_s: float | None = None
        last_seen = 0.0
        present = False
        last_emit = 0.0
        frame_interval = 1.0 / TARGET_FPS
        # Aguante (ver _SIN_IMAGEN_S): desde cuándo no llega un fotograma, y
        # cuándo arrancó esta cámara (para decir cuánto aguantó si se cae:
        # si siempre dura lo mismo, huele a corriente, no a programa).
        sin_imagen_desde: float | None = None
        abierta_en = time.monotonic()
        reintentos = 0

        try:
            while not self._stop.is_set():
                t0 = time.monotonic()
                ok, frame = cap.read()
                if not ok:
                    ahora = time.monotonic()
                    if sin_imagen_desde is None:
                        sin_imagen_desde = ahora
                    if ahora - sin_imagen_desde < _SIN_IMAGEN_S:
                        # Un tropiezo: se ignora. Antes, UNO solo apagaba la
                        # visión entera («se enciende y se apaga»).
                        time.sleep(0.05)
                        continue
                    # Lleva un rato sin imagen: la damos por caída y se reabre.
                    duro = ahora - abierta_en
                    cap.release()
                    self._release_drive()
                    reintentos += 1
                    if reintentos == _REINTENTOS_REABRIR + 1:
                        self.app.log(
                            f"La cámara se cayó {_REINTENTOS_REABRIR} veces "
                            "seguidas. Casi seguro es CORRIENTE o CABLE, no "
                            "el programa: mirá `dmesg | tail -20` en la Pi "
                            "(si sale 'over-current' o 'disconnect', es la "
                            "corriente; un hub USB con alimentación propia "
                            "lo arregla). NO me rindo: sigo reabriéndola "
                            "sola en segundo plano.",
                            "err",
                        )
                    # Tras los primeros 5 intentos, los avisos se espacian
                    # (cada 5 reintentos) para no llenar el panel.
                    if reintentos <= _REINTENTOS_REABRIR or reintentos % 5 == 0:
                        self.app.log(
                            f"La cámara dejó de dar imagen tras {duro:.0f} s. "
                            f"La reabro (intento {reintentos})…",
                            "warn",
                        )
                    self._publish(enabled=True, present=False, x=0.0,
                                  distance=None)
                    # Se le da un respiro antes de reabrir: si fue un bajón
                    # de corriente o el USB se reinició, el /dev/video tarda
                    # en volver a aparecer. La espera crece con los fallos
                    # (hasta 30 s) para no martillar un bus convaleciente.
                    if self._stop.wait(min(30.0, 1.5 * reintentos)):
                        break
                    nuevo, indice = self._buscar_camara(cv2)
                    if nuevo is None:
                        # Sin cámara a la vista todavía: seguimos esperando
                        # en la próxima vuelta (con el contador de fallos
                        # corriendo, así la espera crece).
                        sin_imagen_desde = time.monotonic() - _SIN_IMAGEN_S
                        cap = _CamaraMuerta()
                        continue
                    cap = nuevo
                    self.app.log(f"Cámara recuperada (índice {indice}).", "ok")
                    sin_imagen_desde = None
                    abierta_en = time.monotonic()
                    continue
                # Llegó un fotograma: si veníamos de fallos, todo en orden.
                sin_imagen_desde = None
                if reintentos and time.monotonic() - abierta_en > 30:
                    # Aguantó medio minuto seguido: el contador vuelve a cero.
                    reintentos = 0

                now = time.monotonic()

                # PAUSA durante la narración: mientras MECH habla (o piensa/
                # transcribe) hay proyección, y en la oscuridad la luz sobre
                # las superficies crea FALSOS POSITIVOS de cara. No detectamos
                # hasta que termine de hablar.
                if self.app.state.get("voice_phase") in (
                    "speaking", "thinking", "transcribing"
                ):
                    if present:
                        # No disparamos on_lost (el usuario no se fue; solo
                        # pausamos): solo dejamos de reportarlo y de conducir.
                        present = False
                        dist_s = None
                        self._release_drive()
                    if now - last_emit > 0.5:
                        last_emit = now
                        self._publish(enabled=True, present=False, x=0.0,
                                      distance=None, paused=True)
                    # Mientras narra tampoco miramos el gesto "67" (la luz de
                    # la proyección moviéndose sería movimiento constante), y
                    # se olvida lo acumulado para no arrastrar medias muestras.
                    self._gesto67.reset()
                    time.sleep(0.15)
                    continue

                # Gesto "67": va ANTES de detectar la cara y es independiente
                # de ella. Si alguien lo hace, MECH se lo devuelve.
                self._check_gesture_67(frame, now)

                faces = detector.detect(frame)  # lista de (cx_rel, w_rel)
                # La cara más grande = la persona más cercana.
                face = max(faces, key=lambda f: f[1]) if faces else None

                if face is not None:
                    cx_rel, w_rel = face
                    cx = cx_rel * 2 - 1  # -1..+1
                    # w_rel es relativo (0..1): el resultado no depende de la
                    # resolución real que haya negociado la cámara.
                    width_px = w_rel * FRAME_W
                    distance = (FACE_WIDTH_M * FOCAL_PX) / max(width_px, 1.0)
                    # Suavizado exponencial (la detección tiembla frame a frame).
                    x_s += (cx - x_s) * 0.4
                    dist_s = distance if dist_s is None else dist_s + (distance - dist_s) * 0.3
                    last_seen = now
                    if not present:
                        present = True
                        self._on_detected()
                elif present and now - last_seen > LOST_AFTER_S:
                    present = False
                    dist_s = None
                    self._on_lost()

                self._behave(present, x_s, dist_s)

                # Publicar al panel ~4 veces por segundo.
                if now - last_emit > 0.25:
                    last_emit = now
                    self._publish(enabled=True, present=present, x=x_s, distance=dist_s)

                dt = time.monotonic() - t0
                if dt < frame_interval:
                    time.sleep(frame_interval - dt)
        finally:
            self._release_drive()
            cap.release()
            detector.close()
            self.app.log("Visión detenida.", "info")
            self._publish(enabled=False, present=False, x=0.0, distance=None)

    # ------------------------------------------------------------------

    def _check_gesture_67(self, frame, now: float) -> None:
        """Pasa el fotograma al detector del "67" y avisa a mech_app si acertó.

        Va envuelto en try/except a propósito: un fallo del detector (un
        fotograma raro, OpenCV que se queja) no puede tumbar el hilo de
        visión, que es lo que hace el resto de las cosas.
        """
        if not config.GESTURE67_ENABLED:
            return
        try:
            if self._gesto67.feed(frame, now):
                medido = self._gesto67.debug
                self.app.log(
                    "¡Gesto 67 detectado! "
                    f"(antifase {medido.get('correlacion')}, "
                    f"{medido.get('alternancias')} alternancias)",
                    "ok",
                )
                self.app.on_gesture_67()
        except Exception as e:
            self.app.log(f"Fallo el detector del gesto 67: {e}", "warn")

    def _on_detected(self) -> None:
        self.app.log("Usuario detectado por la cámara.", "ok")
        try:
            self.app.on_user_detected()
        except Exception:
            pass

    def _on_lost(self) -> None:
        self.app.log("Usuario fuera de cámara.", "info")
        self._release_drive()
        try:
            self.app.on_user_lost()
        except Exception:
            pass

    def _behave(self, present: bool, x: float, distance: float | None) -> None:
        """Acercarse al usuario. SOLO adelante/atrás (decisión jul 2026: las
        mecanum de este robot no giran bien en el sitio; los giros se hacen
        manuales desde el panel, estilo carro). El desplazamiento queda en el
        odómetro de arduino_link y mech_app.return_to_start() lo revierte
        antes de proyectar, para que la proyección no quede desfasada."""
        if not present or not self._may_drive():
            self._release_drive()
            return

        max_v = max(10, min(100, config.VISION_MAX_SPEED))
        vx = 0

        # Avanzar hasta la distancia mínima (con histéresis para no oscilar).
        if (
            config.VISION_APPROACH
            and distance is not None
            and distance > config.VISION_MIN_DISTANCE + APPROACH_MARGIN_M
            and abs(x) < 0.35  # solo avanzar si la persona está más o menos al frente
        ):
            # Más lejos = más rápido, pero acotado.
            excess = distance - config.VISION_MIN_DISTANCE
            vx = int(min(max_v, 12 + excess * 25))

        if vx == 0:
            self._release_drive()
            return
        self._driving = True
        self.app.arduino.move(vx, 0, 0)


_vision: Vision | None = None


def get_vision(app) -> Vision:
    global _vision
    if _vision is None:
        _vision = Vision(app)
    return _vision
