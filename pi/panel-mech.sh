#!/usr/bin/env bash
#
# Panel MECH — abre el panel de control en la propia Pi.
#
# Es el panel con la barra de fase de voz arriba (EN REPOSO / PUEDES HABLAR /
# GRABANDO / PENSANDO / HABLANDO), los chips de idioma, la tarjeta del
# traductor y los Ajustes.
#
# A diferencia del proyector, este se abre en una ventana NORMAL (no kiosko):
# hay que poder usar los botones y cambiar de vista.
#
# Con `--silencioso` no habla ni espera un Enter al terminar: asi lo llama
# `iniciar-mech.sh` en segundo plano para abrir el panel solo, en cuanto el
# servidor responde.

set -u

CALLADO=0
[ "${1:-}" = "--silencioso" ] && CALLADO=1

decir() { [ "$CALLADO" -eq 1 ] || echo "$1"; }
esperar_enter() {
    [ "$CALLADO" -eq 1 ] && return 0
    read -r -p "  Pulsa Enter para cerrar..."
}

decir "  MECH — abrir el panel de control"

BIN=""
for c in chromium chromium-browser firefox; do
    if command -v "$c" > /dev/null 2>&1; then BIN="$c"; break; fi
done
if [ -z "$BIN" ]; then
    decir "  ERROR: no encuentro ningún navegador."
    decir "  Instalalo con:  sudo apt install chromium"
    esperar_enter
    exit 1
fi

# Lo normal es abrir esto justo después de «Iniciar MECH», y el servidor
# tarda unos segundos en levantar.
decir "  Esperando al servidor..."
LISTO=0
for _ in $(seq 1 40); do
    if curl -s -o /dev/null --max-time 2 "http://localhost:8000/"; then
        LISTO=1
        break
    fi
    sleep 1
done

if [ "$LISTO" -eq 0 ]; then
    decir ""
    decir "  El servidor no responde en http://localhost:8000"
    decir "  ¿Arrancaste MECH primero? (icono «Iniciar MECH»)"
    esperar_enter
    exit 1
fi

decir "  Abriendo el panel."
# --app quita la barra de direcciones y las pestañas: se ve como una
# aplicación en vez de como una página web.
if [ "$BIN" = "firefox" ]; then
    exec "$BIN" "http://localhost:8000/"
fi
exec "$BIN" --app="http://localhost:8000/" --noerrdialogs
