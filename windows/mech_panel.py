"""MECH Panel — lanzador de escritorio para Windows.

Qué resuelve: hasta ahora, usar el panel desde una laptop Windows pedía
saberse la IP de la Pi, editar `config.txt` a mano y hacer doble click en un
.bat. En un evento eso es justo lo que no se puede pedir — la IP cambia al
cambiar de wifi y nadie se acuerda de dónde está el archivo.

Esta app hace tres cosas:

 1. **Encuentra la Pi sola.** Prueba, en orden: la dirección guardada, los
    nombres de red (`mech.local`, `mech`), y si no, BARRE la red local
    buscando quién responde en el puerto 8000 con el panel de MECH.
 2. **Abre el panel como una aplicación**, no como una pestaña: usa Edge o
    Chrome en modo `--app`, que quita la barra de direcciones y las
    pestañas. Es lo mismo que hacían los .bat, pero sin editar nada.
 3. **Recuerda la dirección** en `%APPDATA%\\MECH\\config.txt`, así que la
    segunda vez arranca directo.

## Por qué tkinter y no una app "de verdad"

Se empaqueta a .exe con PyInstaller y **no tiene ni una dependencia fuera de
la librería estándar de Python**. Eso significa un .exe de ~10 MB que
arranca al instante y se construye en un minuto. La alternativa (pywebview,
Electron, Tauri) mete un navegador entero dentro del .exe para acabar
mostrando la misma página que Edge ya sabe mostrar — y el proyecto ya
decidió no ir por ahí (ver CLAUDE.md).

## Cómo se convierte en .exe / instalador

    powershell -ExecutionPolicy Bypass -File windows\\construir_exe.ps1

Ver `windows/README.md`.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import tkinter as tk
import urllib.error
import urllib.request
from pathlib import Path
from tkinter import messagebox, ttk

APP = "MECH Panel"
PUERTO = 8000
# Nombres por los que la Pi suele responder en la red local. `mech.local` es
# mDNS (Bonjour/Avahi) y `mech` el nombre NetBIOS; cuál funciona depende del
# router, así que se prueban los dos.
NOMBRES = ("mech.local", "mech", "raspberrypi.local")
# Cuánto se espera a cada candidato. Corto a propósito: al barrer la red se
# prueban ~254 direcciones y un timeout largo lo haría eterno.
TIMEOUT_SONDEO = 0.35
TIMEOUT_HTTP = 2.0

# Paleta del proyecto (la misma del panel y del sitio).
FONDO = "#0e0e12"
SUPERFICIE = "#16161d"
BORDE = "#26262f"
TEXTO = "#e8e8ee"
APAGADO = "#8b8b99"
MORADO = "#534AB7"
VERDE = "#1D9E75"
ROJO = "#E24B4A"


# ---------------------------------------------------------------------------
# Dónde se guarda la dirección
# ---------------------------------------------------------------------------

def _carpeta_config() -> Path:
    """%APPDATA%\\MECH (o ~/.mech fuera de Windows, para poder probarlo)."""
    base = os.environ.get("APPDATA")
    carpeta = Path(base) / "MECH" if base else Path.home() / ".mech"
    carpeta.mkdir(parents=True, exist_ok=True)
    return carpeta


CONFIG = _carpeta_config() / "config.json"


def cargar_config() -> dict:
    """Lo guardado la última vez. Nunca revienta: si el archivo está roto se
    empieza de cero, que es mejor que no abrir la app."""
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception:
        return {}


def guardar_config(datos: dict) -> None:
    try:
        CONFIG.write_text(json.dumps(datos, indent=2), encoding="utf-8")
    except Exception:
        pass  # no poder guardar no debe impedir usar la app


# ---------------------------------------------------------------------------
# Encontrar la Pi
# ---------------------------------------------------------------------------

def normalizar(direccion: str) -> str:
    """Deja una dirección en forma `http://host:puerto`, sin barra final.

    Acepta lo que escriba el usuario: `mech`, `192.168.1.42`,
    `http://mech:8000/`, `mech:8000`...
    """
    d = (direccion or "").strip().rstrip("/")
    if not d:
        return ""
    if not d.startswith(("http://", "https://")):
        d = "http://" + d
    # Si no trae puerto, le ponemos el nuestro.
    resto = d.split("://", 1)[1]
    host = resto.split("/", 1)[0]
    if ":" not in host:
        d = d.replace(host, f"{host}:{PUERTO}", 1)
    return d


def responde_mech(direccion: str, timeout: float = TIMEOUT_HTTP) -> bool:
    """¿Hay un servidor de MECH en esa dirección?

    No basta con que el puerto esté abierto: se pide `/api/state`, que solo
    existe en este backend. Así no confundimos la Pi con la impresora de
    alguien que también escucha en el 8000.
    """
    try:
        with urllib.request.urlopen(direccion + "/api/state", timeout=timeout) as r:
            if r.status != 200:
                return False
            datos = json.loads(r.read().decode("utf-8", "replace"))
        return isinstance(datos, dict) and "voice_phase" in datos
    except Exception:
        return False


def _puerto_abierto(host: str, timeout: float = TIMEOUT_SONDEO) -> bool:
    """Toca el puerto sin hablar HTTP. Es MUCHÍSIMO más rápido que pedir la
    página, y por eso es lo que se usa para barrer la red."""
    try:
        with socket.create_connection((host, PUERTO), timeout=timeout):
            return True
    except OSError:
        return False


def _mi_red() -> str | None:
    """El prefijo /24 de esta máquina, ej. "192.168.1.".

    El truco del socket UDP no envía nada: solo hace que el sistema elija
    qué interfaz usaría para salir, que es la que está en la red buena. Con
    varias tarjetas (wifi + ethernet + VPN) es lo único fiable.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        return None
    partes = ip.split(".")
    if len(partes) != 4:
        return None
    return ".".join(partes[:3]) + "."


def buscar_pi(guardada: str = "", avisar=lambda m: None) -> str | None:
    """Devuelve la dirección de la Pi, o None. De lo más rápido a lo más lento.

    `avisar` recibe un texto para ir contando qué está haciendo — sin eso, la
    app parece colgada durante el barrido.
    """
    candidatos = [c for c in ([normalizar(guardada)] if guardada else []) if c]
    candidatos += [normalizar(n) for n in NOMBRES]

    for direccion in candidatos:
        avisar(f"Probando {direccion}…")
        if responde_mech(direccion):
            return direccion

    red = _mi_red()
    if not red:
        return None

    avisar(f"Buscando en la red {red}0/24… (puede tardar unos segundos)")
    # Barrido en paralelo: 254 direcciones de una en una serían minutos.
    encontrados: list[str] = []
    cerrojo = threading.Lock()

    def mirar(n: int) -> None:
        host = f"{red}{n}"
        if _puerto_abierto(host):
            with cerrojo:
                encontrados.append(host)

    hilos = [threading.Thread(target=mirar, args=(n,), daemon=True)
             for n in range(1, 255)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=3.0)

    # De los que tienen el puerto abierto, cuál es de verdad MECH.
    for host in sorted(encontrados):
        direccion = normalizar(host)
        avisar(f"Comprobando {direccion}…")
        if responde_mech(direccion, timeout=1.5):
            return direccion
    return None


# ---------------------------------------------------------------------------
# Abrir el navegador en modo aplicación
# ---------------------------------------------------------------------------

def _buscar_navegador() -> str | None:
    """Ruta de Edge o Chrome, el primero que haya."""
    candidatos = []
    for var in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
        base = os.environ.get(var)
        if not base:
            continue
        candidatos += [
            Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe",
        ]
    for ruta in candidatos:
        if ruta.exists():
            return str(ruta)
    return None


def abrir(direccion: str, ruta: str = "/", kiosko: bool = False) -> str:
    """Abre una página del servidor. Devuelve un texto de qué hizo.

    Con Edge/Chrome se usa `--app`, que abre una ventana SIN barra de
    direcciones ni pestañas: parece una aplicación de escritorio. Si no hay
    ninguno de los dos, se cae al navegador por defecto (una pestaña normal,
    pero funciona).

    ⚠️ `--autoplay-policy=no-user-gesture-required` va SIEMPRE, no solo en la
    página del proyector: sin él los videos del slot de marketing se
    reproducen MUDOS. Es el mismo flag que usa el script de la Pi.
    """
    url = direccion + ruta
    navegador = _buscar_navegador()
    if not navegador:
        import webbrowser
        webbrowser.open(url)
        return "Abierto en el navegador por defecto (no encontré Edge ni Chrome)."

    flags = [
        navegador,
        f"--kiosk={url}" if kiosko else f"--app={url}",
        "--autoplay-policy=no-user-gesture-required",
        # Perfil aparte: así la ventana de MECH no arrastra las pestañas, las
        # sesiones ni las extensiones del navegador personal de nadie.
        f"--user-data-dir={_carpeta_config() / 'navegador'}",
    ]
    if kiosko:
        flags.append("--edge-kiosk-type=fullscreen")
    subprocess.Popen(flags, close_fds=True)
    nombre = "Edge" if "msedge" in navegador.lower() else "Chrome"
    return f"Abierto en {nombre} ({'kiosko' if kiosko else 'modo aplicación'})."


def abrir_en_navegador(direccion: str, ruta: str) -> str:
    """Abre una página en el navegador de SIEMPRE, como pestaña normal.

    Es para la biblioteca de videos (`/library`): ahí se arrastran los mp4
    desde el Explorador, y conviene tener la barra de direcciones a la vista
    para copiar la dirección o pasársela a alguien del equipo.
    """
    import webbrowser
    url = direccion + ruta
    webbrowser.open(url)
    return f"Abierto en el navegador: {url}"


# ---------------------------------------------------------------------------
# La ventana
# ---------------------------------------------------------------------------

class Ventana(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP)
        self.configure(bg=FONDO)
        self.resizable(False, False)
        self.geometry("460x470")
        self._icono()

        self.cfg = cargar_config()
        self.direccion = tk.StringVar(value=self.cfg.get("direccion", ""))
        self.conectado = False

        self._construir()
        # Buscar la Pi nada más abrir, en segundo plano para que la ventana
        # aparezca YA (si no, parece que no arrancó).
        self.after(200, self.buscar)

    def _icono(self) -> None:
        # El .ico va junto al script, y dentro del .exe en la carpeta temporal
        # que crea PyInstaller (_MEIPASS).
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        ico = base / "mech.ico"
        if ico.exists():
            try:
                self.iconbitmap(str(ico))
            except tk.TclError:
                pass

    # -- construcción de la interfaz -----------------------------------

    def _construir(self) -> None:
        tk.Label(self, text="M.E.C.H", bg=FONDO, fg=TEXTO,
                 font=("Segoe UI", 22, "bold")).pack(pady=(22, 0))
        tk.Label(self, text="PANEL DE CONTROL", bg=FONDO, fg=APAGADO,
                 font=("Consolas", 9)).pack()

        # Estado de la conexión.
        fila = tk.Frame(self, bg=FONDO)
        fila.pack(pady=(18, 4))
        self.punto = tk.Canvas(fila, width=12, height=12, bg=FONDO,
                               highlightthickness=0)
        self.punto.pack(side="left", padx=(0, 8))
        self._punto(APAGADO)
        self.estado = tk.Label(fila, text="Buscando la Raspberry Pi…",
                               bg=FONDO, fg=APAGADO, font=("Segoe UI", 10))
        self.estado.pack(side="left")

        # Dirección (editable, por si la autodetección falla).
        caja = tk.Frame(self, bg=SUPERFICIE, highlightbackground=BORDE,
                        highlightthickness=1)
        caja.pack(fill="x", padx=28, pady=(12, 6))
        tk.Label(caja, text="DIRECCIÓN DE LA PI", bg=SUPERFICIE, fg=APAGADO,
                 font=("Consolas", 8)).pack(anchor="w", padx=10, pady=(8, 0))
        entrada = tk.Entry(caja, textvariable=self.direccion, bg=SUPERFICIE,
                           fg=TEXTO, insertbackground=TEXTO, relief="flat",
                           font=("Consolas", 11))
        entrada.pack(fill="x", padx=10, pady=(2, 10))
        entrada.bind("<Return>", lambda e: self.probar())

        botones = tk.Frame(self, bg=FONDO)
        botones.pack(pady=(0, 10))
        self._boton(botones, "Buscar de nuevo", self.buscar).pack(side="left", padx=4)
        self._boton(botones, "Probar", self.probar).pack(side="left", padx=4)

        # Acciones.
        self.b_panel = self._boton(self, "ABRIR EL PANEL", self.abrir_panel,
                                   color=MORADO, grande=True)
        self.b_panel.pack(fill="x", padx=28, pady=(8, 6))
        self.b_proy = self._boton(self, "Abrir la proyección", self.abrir_proyector)
        self.b_proy.pack(fill="x", padx=28, pady=3)
        self.b_kiosk = self._boton(self, "Panel a pantalla completa", self.abrir_kiosko)
        self.b_kiosk.pack(fill="x", padx=28, pady=3)
        self.b_lib = self._boton(self, "Biblioteca de videos (en el navegador)",
                                 self.abrir_biblioteca)
        self.b_lib.pack(fill="x", padx=28, pady=3)

        tk.Label(self, text="La Pi tiene que estar encendida y en la misma wifi.",
                 bg=FONDO, fg=APAGADO, font=("Segoe UI", 8)).pack(pady=(12, 0))

    def _boton(self, padre, texto, accion, color=SUPERFICIE, grande=False):
        b = tk.Button(
            padre, text=texto, command=accion, bg=color, fg=TEXTO,
            activebackground=BORDE, activeforeground=TEXTO, relief="flat",
            font=("Segoe UI", 11 if grande else 9, "bold" if grande else "normal"),
            cursor="hand2", pady=10 if grande else 6, bd=0,
            highlightbackground=BORDE, highlightthickness=1,
        )
        return b

    def _punto(self, color: str) -> None:
        self.punto.delete("all")
        self.punto.create_oval(1, 1, 11, 11, fill=color, outline="")

    # -- lógica ---------------------------------------------------------

    def _decir(self, texto: str, color: str = APAGADO) -> None:
        """Actualiza el estado. Se llama desde hilos, así que pasa por
        `after` para tocar tkinter siempre en el hilo de la interfaz."""
        self.after(0, lambda: (self.estado.config(text=texto, fg=color),
                               self._punto(color)))

    def _marcar(self, ok: bool) -> None:
        self.conectado = ok
        estado = "normal" if ok else "disabled"
        for b in (self.b_panel, self.b_proy, self.b_kiosk, self.b_lib):
            self.after(0, lambda b=b, e=estado: b.config(state=e))

    def buscar(self) -> None:
        self._marcar(False)
        self._decir("Buscando la Raspberry Pi…")

        def trabajo():
            hallada = buscar_pi(self.direccion.get(), self._decir)
            if hallada:
                self.after(0, lambda: self.direccion.set(hallada))
                self.cfg["direccion"] = hallada
                guardar_config(self.cfg)
                self._decir(f"Conectado a {hallada}", VERDE)
                self._marcar(True)
            else:
                self._decir("No encontré la Pi. Escribe su dirección y pulsa Probar.",
                            ROJO)

        threading.Thread(target=trabajo, daemon=True).start()

    def probar(self) -> None:
        direccion = normalizar(self.direccion.get())
        if not direccion:
            messagebox.showinfo(APP, "Escribe la dirección de la Pi, por ejemplo "
                                     "192.168.1.42 o mech.local")
            return
        self.direccion.set(direccion)
        self._marcar(False)
        self._decir(f"Probando {direccion}…")

        def trabajo():
            if responde_mech(direccion):
                self.cfg["direccion"] = direccion
                guardar_config(self.cfg)
                self._decir(f"Conectado a {direccion}", VERDE)
                self._marcar(True)
            else:
                self._decir("Ahí no responde MECH. ¿Está encendido el servidor?", ROJO)

        threading.Thread(target=trabajo, daemon=True).start()

    def _abrir(self, ruta: str, kiosko: bool = False) -> None:
        try:
            self._decir(abrir(self.direccion.get(), ruta, kiosko), VERDE)
        except Exception as e:
            messagebox.showerror(APP, f"No pude abrir el navegador:\n{e}")

    def abrir_panel(self) -> None:
        self._abrir("/")

    def abrir_proyector(self) -> None:
        self._abrir("/projector")

    def abrir_kiosko(self) -> None:
        self._abrir("/", kiosko=True)

    def abrir_biblioteca(self) -> None:
        try:
            self._decir(abrir_en_navegador(self.direccion.get(), "/library"), VERDE)
        except Exception as e:
            messagebox.showerror(APP, f"No pude abrir el navegador:\n{e}")


def main() -> int:
    Ventana().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
