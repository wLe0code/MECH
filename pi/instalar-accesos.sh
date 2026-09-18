#!/usr/bin/env bash
#
# Pone los iconos de MECH en el escritorio de la Pi.
#
# Se corre UNA sola vez (es la única vez que hace falta la terminal):
#
#     bash ~/MECH/pi/instalar-accesos.sh
#
# Después ya se usa todo con doble click. Se puede volver a correr sin
# problema: simplemente reescribe los iconos.

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
# lanzar (al clonar desde Windows se pierde el permiso).
chmod +x "$REPO"/pi/*.sh

ICONO="$REPO/frontend/icon.svg"
[ -f "$ICONO" ] || ICONO="utilities-terminal"

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
    "Actualiza el codigo y arranca el servidor de MECH" \
    "iniciar-mech.sh"

crear_acceso "Proyector MECH" \
    "Abre la proyeccion a pantalla completa, con sonido" \
    "proyector-mech.sh"

echo
echo "  Listo. Ya tenés los dos iconos en el escritorio."
echo
echo "  Si al hacer doble click el sistema pregunta qué hacer, elegí"
echo "  «Ejecutar» (o «Ejecutar en terminal»). Solo pregunta la 1ª vez."
