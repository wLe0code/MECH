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
#
# ⚠️ Y el flag solo cuenta si este es el PRIMER Chromium que se abre. Chromium
# es un solo programa: si ya hay uno abierto, la ventana nueva se mete en ese
# y las banderas de esta línea se ignoran. Por eso `panel-mech.sh` lleva el
# mismo flag, y por eso aquí se mira si hay un Chromium abierto SIN él (uno
# abierto a mano, o el panel de antes de actualizar): en ese caso se cierra
# y se vuelve a abrir bien. Sin eso la proyección se queda muda (oct 2026).

set -u

REPO="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
PERMISO="--autoplay-policy=no-user-gesture-required"

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

# ── ¿Hay ya un Chromium abierto SIN el permiso de sonido? ───────────────
# Se miran solo los procesos PRINCIPALES de Chromium (los hijos —pestañas,
# gráficos— llevan `--type=`). Deja en SIN_PERMISO sus números y en
# HABIA_PANEL si alguno era el panel de MECH.
SIN_PERMISO=""
HABIA_PANEL=0
for pid in $(pgrep -u "$(id -u)" -x 'chromium(-browser?)?' 2>/dev/null); do
    [ -r "/proc/$pid/cmdline" ] || continue
    ORDEN="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null)"
    case "$ORDEN" in *--type=*) continue ;; esac
    case "$ORDEN" in *"$PERMISO"*) continue ;; esac
    SIN_PERMISO="$SIN_PERMISO $pid"
    case "$ORDEN" in *--app=http://localhost:8000*) HABIA_PANEL=1 ;; esac
done

if [ -n "$SIN_PERMISO" ]; then
    echo
    echo "  OJO: ya hay un Chromium abierto, y se abrió SIN el permiso de sonido."
    echo "  La proyección se metería en ese mismo Chromium y saldría MUDA:"
    echo "  los videos de marketing no se oirían."
    echo
    echo "  Para arreglarlo hay que cerrarlo (TODAS sus ventanas) y abrirlo de"
    echo "  nuevo con el permiso."
    [ "$HABIA_PANEL" -eq 1 ] && echo "  El panel de MECH se vuelve a abrir solo."
    echo
    RESP=""
    # Sin respuesta en 15 s (o sin teclado), se hace: es lo que casi siempre
    # se quiere, y si no la proyección no sonaría.
    read -r -t 15 -p "  Enter = sí, hazlo    ·    n y Enter = no, déjalo así: " RESP || true
    echo
    case "$RESP" in
        n|N|no|No|NO)
            echo "  Lo dejo como está. La proyección va a pedir un toque en la"
            echo "  pantalla para poder sonar."
            ;;
        *)
            echo "  Cerrando Chromium..."
            # shellcheck disable=SC2086
            kill $SIN_PERMISO 2> /dev/null
            for _ in $(seq 1 16); do
                VIVO=0
                for pid in $SIN_PERMISO; do
                    kill -0 "$pid" 2> /dev/null && VIVO=1
                done
                [ "$VIVO" -eq 0 ] && break
                sleep 0.5
            done
            # shellcheck disable=SC2086
            [ "$VIVO" -eq 1 ] && kill -9 $SIN_PERMISO 2> /dev/null
            sleep 1
            if [ "$HABIA_PANEL" -eq 1 ]; then
                echo "  Abriendo otra vez el panel..."
                ( "$REPO/pi/panel-mech.sh" --silencioso < /dev/null > /dev/null 2>&1 & )
                sleep 3
            fi
            ;;
    esac
fi

echo "  Abriendo a pantalla completa. Para salir: Alt+F4."
exec "$BIN" \
    --kiosk \
    "$PERMISO" \
    --noerrdialogs \
    --disable-session-crashed-bubble \
    --disable-infobars \
    "http://localhost:8000/projector"
