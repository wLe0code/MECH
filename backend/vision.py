"""Visión de MECH — detección de usuarios con la Logitech C930e.

Pipeline:
  OpenCV (V4L2/USB UVC) captura a 640x360 → MediaPipe Face Detection
  (modelo full-range, alcance ~5 m) → por cada frame se calcula:

    - user_present : hay al menos una cara (con debounce para no parpadear).
    - x            : posición horizontal de la cara más grande, -1 (izq) .. +1 (der).
    - distance     : distancia estimada en metros, a partir del ancho de la
                     cara en píxeles (cara promedio ~16 cm; focal estimada
                     según el FOV de 90° de la C930e).
    - vx_user      : hacia dónde se está moviendo el usuario (deriva de x).

Comportamientos (configurables en vivo desde el panel):
    - VISION_FOLLOW   : MECH gira para quedar de frente al usuario.
    - VISION_APPROACH : MECH avanza hasta quedar a VISION_MIN_DISTANCE.
      Solo se mueve cuando NO está narrando (fases waiting/dormant) y el
      bucle de voz está activo. Siempre manda STOP al perder al usuario.
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

# Parámetros de cámara / estimación de distancia.
FRAME_W = 640
FRAME_H = 360
TARGET_FPS = 10
HFOV_DEG = 90.0           # FOV horizontal de la C930e
FACE_WIDTH_M = 0.16       # ancho promedio de una cara adulta
FOCAL_PX = (FRAME_W / 2) / math.tan(math.radians(HFOV_DEG / 2))  # ≈ 320

# Tiempo sin ver caras para declarar que el usuario se fue.
LOST_AFTER_S = 1.5
# Margen sobre la distancia mínima para no oscilar (histéresis).
APPROACH_MARGIN_M = 0.15


class Vision:
    """Hilo de visión. Publica su estado en mech_app.state["vision"]."""

    def __init__(self, app) -> None:
        self.app = app
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._driving = False  # si fuimos nosotros los que mandamos MOVE

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        if self.running:
            return True
        try:
            import cv2  # noqa: F401
            import mediapipe  # noqa: F401
        except ImportError as e:
            self.app.log(
                f"Visión no disponible (falta instalar {e.name}): "
                "pip install opencv-python-headless mediapipe",
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

    def _publish(self, enabled: bool, present: bool, x: float, distance: float | None) -> None:
        self.app.state["vision"] = {
            "enabled": enabled,
            "user_present": present,
            "x": round(x, 2),
            "distance": round(distance, 2) if distance is not None else None,
            "min_distance": config.VISION_MIN_DISTANCE,
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

    def _loop(self) -> None:
        import cv2
        import mediapipe as mp

        cap = cv2.VideoCapture(config.VISION_CAMERA_INDEX)
        # Forzar MJPG: sin esto la C930e negocia YUYV y cae a ~5 fps en la Pi.
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
        cap.set(cv2.CAP_PROP_FPS, TARGET_FPS)
        if not cap.isOpened():
            self.app.log(
                f"No se pudo abrir la cámara {config.VISION_CAMERA_INDEX}. "
                "¿Está enchufada la C930e? Revisa con: v4l2-ctl --list-devices",
                "err",
            )
            self._publish(enabled=False, present=False, x=0.0, distance=None)
            return

        detector = mp.solutions.face_detection.FaceDetection(
            model_selection=1,  # full-range: hasta ~5 m
            min_detection_confidence=0.5,
        )
        self.app.log("Visión activa: cámara abierta, detectando usuarios.", "ok")

        # Estado suavizado.
        x_s = 0.0
        dist_s: float | None = None
        last_seen = 0.0
        present = False
        last_emit = 0.0
        frame_interval = 1.0 / TARGET_FPS

        try:
            while not self._stop.is_set():
                t0 = time.monotonic()
                ok, frame = cap.read()
                if not ok:
                    self.app.log("La cámara dejó de dar frames; visión detenida.", "err")
                    break
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = detector.process(rgb)

                face = None
                if result.detections:
                    # La cara más grande = la persona más cercana.
                    face = max(
                        result.detections,
                        key=lambda d: d.location_data.relative_bounding_box.width,
                    )

                now = time.monotonic()
                if face is not None:
                    bb = face.location_data.relative_bounding_box
                    cx = (bb.xmin + bb.width / 2) * 2 - 1  # -1..+1
                    # bb.width es relativo (0..1): el resultado no depende de
                    # la resolución real que haya negociado la cámara.
                    width_px = bb.width * FRAME_W
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
        """Seguir / acercarse al usuario. Manda MOVE a baja velocidad."""
        if not present or not self._may_drive():
            self._release_drive()
            return

        max_v = max(10, min(100, config.VISION_MAX_SPEED))
        w = 0
        vx = 0

        # Girar para quedar de frente (sigue al usuario si camina).
        if config.VISION_FOLLOW and abs(x) > 0.15:
            w = int(max(-1.0, min(1.0, x)) * max_v)

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

        if vx == 0 and w == 0:
            self._release_drive()
            return
        self._driving = True
        self.app.arduino.move(vx, 0, w)


_vision: Vision | None = None


def get_vision(app) -> Vision:
    global _vision
    if _vision is None:
        _vision = Vision(app)
    return _vision
