"""Visor fullscreen para el proyector.

Diseño: un proceso aparte que escucha cambios en un archivo "current.txt"
dentro de IMAGE_OUTPUT_DIR. Cuando el archivo cambia, refresca la imagen
mostrada. Esto desacopla la generación de imágenes de la proyección y
permite que el main loop solo escriba archivos.

Para arrancar el visor:
    python -m backend.projector

Para mostrar una imagen desde otro módulo:
    from backend.projector import show
    show(Path("/ruta/a/imagen.png"))
"""

from __future__ import annotations

import os
import sys
import time
import tkinter as tk
from pathlib import Path

from PIL import Image, ImageTk

import config


POINTER_FILE = config.IMAGE_OUTPUT_DIR / "current.txt"


def show(image_path: Path) -> None:
    """Marca esta imagen como la que el visor debe mostrar.

    Lo único que hacemos es escribir el path en POINTER_FILE; el visor
    detecta el cambio y refresca.
    """
    POINTER_FILE.write_text(str(image_path))


def clear() -> None:
    """Vuelve a fondo negro."""
    if POINTER_FILE.exists():
        POINTER_FILE.unlink()


class Viewer:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("MECH")
        self.root.configure(bg="black")
        self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", lambda _: self.root.destroy())

        self.label = tk.Label(self.root, bg="black")
        self.label.pack(fill="both", expand=True)

        self._last_path: str | None = None
        self._photo: ImageTk.PhotoImage | None = None
        self.root.after(200, self._tick)

    def _tick(self) -> None:
        try:
            current = POINTER_FILE.read_text().strip() if POINTER_FILE.exists() else ""
        except OSError:
            current = ""

        if current != self._last_path:
            self._last_path = current
            if current and Path(current).exists():
                self._render(Path(current))
            else:
                self.label.configure(image="")
                self._photo = None

        self.root.after(200, self._tick)

    def _render(self, path: Path) -> None:
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        img = Image.open(path)
        img.thumbnail((screen_w, screen_h), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(img)
        self.label.configure(image=self._photo)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    if "DISPLAY" not in os.environ:
        os.environ["DISPLAY"] = config.PROJECTOR_DISPLAY
    Viewer().run()


if __name__ == "__main__":
    main()
