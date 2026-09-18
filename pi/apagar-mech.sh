#!/usr/bin/env bash
#
# Apagar MECH — para el servidor (y cierra la proyección si está abierta).
#
# Es lo mismo que hacer Ctrl+C en la ventana de «Iniciar MECH», pero sin
# tener que buscarla entre las ventanas abiertas.
#
# OJO: esto apaga el SERVIDOR, no la Raspberry Pi. Para apagar la Pi, el menú
# del sistema (esquina superior izquierda) → Shutdown.

set -u

echo "════════════════════════════════════════════════════════"
echo "  Apagar MECH"
echo "════════════════════════════════════════════════════════"
echo

PATRON="python.*backend[.]server"

if ! pgrep -f "$PATRON" > /dev/null 2>&1; then
    echo "  MECH no estaba corriendo."
    echo
    echo "  (Para arrancarlo: icono «Iniciar MECH».)"
    echo "════════════════════════════════════════════════════════"
    read -r -p "  Pulsa Enter para cerrar..."
    exit 0
fi

echo "  Parando el servidor..."
pkill -f "$PATRON"

# Le damos unos segundos para que cierre bien (suelta el micrófono, manda
# STOP al Arduino). Si no muere, se fuerza.
for _ in $(seq 1 10); do
    pgrep -f "$PATRON" > /dev/null 2>&1 || break
    sleep 0.5
done
if pgrep -f "$PATRON" > /dev/null 2>&1; then
    echo "  No cerraba solo; lo fuerzo."
    pkill -9 -f "$PATRON"
    sleep 1
fi

# La proyección en kiosko se queda huérfana si no la cerramos. Solo se mata
# la del proyector (por la URL), NO cualquier navegador que tengas abierto.
if pgrep -f "chromium.*localhost:8000/projector" > /dev/null 2>&1; then
    echo "  Cerrando la proyección."
    pkill -f "chromium.*localhost:8000/projector"
fi

echo
if pgrep -f "$PATRON" > /dev/null 2>&1; then
    echo "  AVISO: algo sigue corriendo. Mirá la ventana de «Iniciar MECH»."
else
    echo "  ► MECH apagado."
fi
echo
echo "  (Esto NO apaga la Raspberry Pi, solo el servidor.)"
echo "════════════════════════════════════════════════════════"
read -r -p "  Pulsa Enter para cerrar..."
