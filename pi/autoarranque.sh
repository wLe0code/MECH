#!/usr/bin/env bash
#
# MECH al encender — interruptor del arranque automático.
#
# Es lo que hay detrás del icono "MECH al encender" del escritorio. Cada vez
# que se hace doble click, CAMBIA el estado y lo dice:
#
#   apagado -> encendido : al prender la Pi, MECH arranca solo y queda
#                          escuchando "ok MECH". Cero terminal, cero clicks.
#   encendido -> apagado : vuelve a arrancarse solo con el icono.
#
# El arranque automático usa `--sin-actualizar` a propósito: en un evento no
# querés que el robot cambie de comportamiento al encenderlo solo porque
# alguien subió algo. Actualizar sigue siendo un acto deliberado (el icono
# "Iniciar MECH").

set -u

REPO="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
DESTINO="$HOME/.config/autostart/mech.desktop"

echo "════════════════════════════════════════════════════════"
echo "  MECH al encender la Pi"
echo "════════════════════════════════════════════════════════"
echo

if [ -f "$DESTINO" ]; then
    rm -f "$DESTINO"
    echo "  ► APAGADO."
    echo
    echo "  Al encender la Pi, MECH ya NO arranca solo."
    echo "  Para arrancarlo: icono «Iniciar MECH» del escritorio."
else
    mkdir -p "$(dirname "$DESTINO")"
    cat > "$DESTINO" <<FIN
[Desktop Entry]
Type=Application
Version=1.0
Name=MECH
Comment=Arranca el servidor de MECH al iniciar la sesion
Exec="$REPO/pi/iniciar-mech.sh" --sin-actualizar
Path=$REPO
Terminal=true
X-GNOME-Autostart-enabled=true
FIN
    echo "  ► ENCENDIDO."
    echo
    echo "  Al encender la Pi, MECH arranca solo y queda escuchando"
    echo "  «ok MECH». No hay que tocar nada más."
    echo
    echo "  Arranca SIN buscar actualizaciones, a propósito: así el robot"
    echo "  siempre se enciende con el código que ya probaste. Para"
    echo "  actualizar, usá el icono «Iniciar MECH»."
fi

echo
echo "  (Doble click otra vez en este icono para cambiarlo.)"
echo "════════════════════════════════════════════════════════"
read -r -p "  Pulsa Enter para cerrar..."
