#!/usr/bin/env bash
#
# Proyector MECH — abre la proyección a pantalla completa, CON SONIDO.
#
# Es lo que hay detrás del icono "Proyector MECH" del escritorio de la Pi.
#
# ⚠️ El flag `--autoplay-policy=no-user-gesture-required` NO es opcional.
# Sin él, los navegadores no dejan reproducir con sonido sin un clic previo:
# los videos del slot de marketing se ven MUDOS y la pantalla muestra "toca
# la pantalla para activar el sonido". Es un fallo que ya costó una prueba
# entera, por eso este script existe.

set -u

echo "  MECH — abrir la proyección"

# En Raspberry Pi OS Bookworm el paquete es `chromium`, pero el binario
# también existe como `chromium-browser` en instalaciones más viejas.
BIN=""
for c in chromium chromium-browser; do
    if command -v "$c" > /dev/null 2>&1; then BIN="$c"; break; fi
done
if [ -z "$BIN" ]; then
    echo "  ERROR: no encuentro Chromium. Instalalo con:  sudo apt install chromium"
    read -r -p "  Pulsa Enter para cerrar..."
    exit 1
fi

# Esperamos a que el servidor responda: lo normal es abrir esto justo
# después de "Iniciar MECH", y tarda unos segundos en levantar.
echo "  Esperando al servidor..."
LISTO=0
for _ in $(seq 1 40); do
    if curl -s -o /dev/null --max-time 2 "http://localhost:8000/projector"; then
        LISTO=1
        break
    fi
    sleep 1
done

if [ "$LISTO" -eq 0 ]; then
    echo
    echo "  El servidor no responde en http://localhost:8000"
    echo "  ¿Arrancaste MECH primero? (icono «Iniciar MECH»)"
    read -r -p "  Pulsa Enter para cerrar..."
    exit 1
fi

echo "  Abriendo a pantalla completa. Para salir: Alt+F4."
exec "$BIN" \
    --kiosk \
    --autoplay-policy=no-user-gesture-required \
    --noerrdialogs \
    --disable-session-crashed-bubble \
    --disable-infobars \
    "http://localhost:8000/projector"
