#!/usr/bin/env bash
#
# Pone los TRES iconos de MECH en el escritorio de la Pi.
#
# Se corre UNA sola vez. Desde el explorador de archivos: doble click en este
# archivo → «Ejecutar en terminal». O desde la terminal:
#
#     bash ~/MECH/pi/instalar-accesos.sh
#
# Después ya se usa todo con doble click. Se puede volver a correr sin
# problema: reescribe los iconos y limpia los de versiones anteriores.

set -u

REPO="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"

# El escritorio puede llamarse "Desktop" o "Escritorio" según el idioma del
# sistema; xdg-user-dir lo resuelve solo.
DESK="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
[ -z "$DESK" ] && DESK="$HOME/Desktop"
mkdir -p "$DESK"

echo "  Repo:       $REPO"
echo "  Escritorio: $DESK"
echo

# Los scripts tienen que ser ejecutables para que el .desktop los pueda
# lanzar (al clonar desde Windows se puede perder el permiso).
chmod +x "$REPO"/pi/*.sh 2>/dev/null

ICONO="$REPO/frontend/icon.svg"
[ -f "$ICONO" ] || ICONO="utilities-terminal"

# Iconos de versiones anteriores del instalador: se borran para no dejar
# botones sueltos en el escritorio que ya no corresponden a nada.
#   - "Panel MECH"       -> ahora lo abre solo «Iniciar MECH»
#   - "MECH al encender" -> sigue existiendo, pero en pi/autoarranque.sh
#   - "Proyector MECH"   -> se renombró a «Proyectar MECH»
for viejo in "Panel MECH" "MECH al encender" "Proyector MECH"; do
    if [ -f "$DESK/$viejo.desktop" ]; then
        rm -f "$DESK/$viejo.desktop"
        echo "  [quitado] $viejo"
    fi
done

crear_acceso() {
    nombre="$1"; comentario="$2"; script="$3"
    destino="$DESK/$nombre.desktop"
    cat > "$destino" <<FIN
[Desktop Entry]
Type=Application
Version=1.0
Name=$nombre
Comment=$comentario
Exec="$REPO/pi/$script"
Path=$REPO
Icon=$ICONO
Terminal=true
Categories=Utility;
FIN
    chmod +x "$destino"
    # Los gestores de archivos modernos piden marcar el lanzador como "de
    # confianza"; si no, al doble click preguntan o no hacen nada.
    gio set "$destino" metadata::trusted true 2>/dev/null || true
    echo "  [ok] $nombre"
}

crear_acceso "Iniciar MECH" \
    "Actualiza, arranca el servidor y abre el panel de control" \
    "iniciar-mech.sh"

crear_acceso "Proyectar MECH" \
    "Abre la ventana con lo que MECH proyecta, a pantalla completa" \
    "proyector-mech.sh"

crear_acceso "Apagar MECH" \
    "Para el servidor de MECH (no apaga la Raspberry Pi)" \
    "apagar-mech.sh"

echo
echo "  Listo. Ya tenés los TRES iconos en el escritorio:"
echo
echo "    Iniciar MECH     -> actualiza, arranca y abre el panel"
echo "    Proyectar MECH   -> la ventana de lo que MECH proyecta"
echo "    Apagar MECH      -> para el servidor"
echo
echo "  Si al hacer doble click el sistema pregunta qué hacer, elegí"
echo "  «Ejecutar» (o «Ejecutar en terminal»). Solo pregunta la 1ª vez."
echo
echo "  EXTRA (sin icono, para no llenar el escritorio): si querés que MECH"
echo "  arranque SOLO al encender la Pi, doble click en pi/autoarranque.sh"
echo "  desde el explorador de archivos. Se apaga igual."
