#!/usr/bin/env bash
#
# Iniciar MECH — baja los últimos cambios y arranca el servidor.
#
# Es lo que hay detrás del icono "Iniciar MECH" del escritorio de la Pi.
# Hace de una vez lo que antes había que teclear a mano:
#
#     cd ~/MECH && git pull && python -m backend.server
#
# ...y además abre el PANEL DE CONTROL solo, en cuanto el servidor responde.
#
# Con dos diferencias que importan en un evento:
#   - Si NO hay internet, avisa y arranca igual con el código que ya está en
#     la Pi. Quedarse sin robot porque falló el wifi del recinto sería lo peor.
#   - Si ya había un servidor corriendo, lo cierra antes (si no, el puerto
#     8000 está ocupado y el nuevo no arranca).
#
# Con `--sin-actualizar` se salta el `git pull` y arranca directo. Lo usa el
# arranque automático al encender la Pi: en un evento no querés que el robot
# cambie de comportamiento solo porque alguien subió algo — actualizar tiene
# que ser un acto deliberado (el icono «Iniciar MECH»).
#
# Para pararlo: Ctrl+C en esta ventana, o cerrarla.

set -u

ACTUALIZAR=1
ABRIR_PANEL=1
for arg in "$@"; do
    case "$arg" in
        --sin-actualizar|--no-update) ACTUALIZAR=0 ;;
        --sin-panel)                  ABRIR_PANEL=0 ;;
    esac
done

# La carpeta del repo es la de arriba de este script, venga de donde venga
# el acceso directo.
REPO="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"

echo "════════════════════════════════════════════════════════"
echo "  MECH — actualizar e iniciar"
echo "════════════════════════════════════════════════════════"
echo "  Carpeta: $REPO"
echo

cd "$REPO" || {
    echo "  ERROR: no encuentro la carpeta de MECH."
    read -r -p "  Pulsa Enter para cerrar..."
    exit 1
}

# ── 1. Cerrar un servidor anterior ──────────────────────────────────────
# Sin esto, el puerto 8000 sigue ocupado y el server nuevo no levanta.
if pgrep -f "python.*backend[.]server" > /dev/null 2>&1; then
    echo "  Ya había un MECH corriendo: lo cierro."
    pkill -f "python.*backend[.]server"
    sleep 2
    pkill -9 -f "python.*backend[.]server" 2>/dev/null
    echo
fi

# ── 2. Bajar los últimos cambios ────────────────────────────────────────
# `timeout` para que una wifi mala no deje esto colgado para siempre, y
# `--ff-only` para no crear commits de merge por sorpresa en la Pi.
if [ "$ACTUALIZAR" -eq 1 ]; then
    echo "  Buscando actualizaciones..."
    # OJO: el resultado se guarda en una variable en vez de mandarlo por una
    # tubería a `sed`. En una tubería, el estado de salida es el del ÚLTIMO
    # comando (sed, que siempre va bien), así que el aviso de abajo no
    # saldría NUNCA aunque el pull fallara.
    SALIDA_PULL="$(timeout 25 git pull --ff-only 2>&1)"
    RC_PULL=$?
    [ -n "$SALIDA_PULL" ] && echo "$SALIDA_PULL" | sed 's/^/    /'
    if [ "$RC_PULL" -eq 0 ]; then
        echo "  Código al día."
    else
        echo
        echo "  AVISO: no pude actualizar."
        echo "  Puede ser que no haya internet, o que haya cambios sin guardar"
        echo "  en la Pi. Arranco igual con el código que ya está aquí."
    fi
else
    echo "  Arranque directo (sin buscar actualizaciones)."
fi
echo "  Versión: $(git log --oneline -1 2>/dev/null)"
echo

# ── 3. Entorno de Python ────────────────────────────────────────────────
if [ -f "$REPO/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    . "$REPO/.venv/bin/activate"
    echo "  Entorno: .venv"
else
    echo "  AVISO: no hay .venv; uso el Python del sistema."
fi

# ── 4. Volumen del sistema al máximo ────────────────────────────────────
# En cada arranque, porque es gratis y porque nadie se acuerda de hacerlo.
# El audio pasa por varias etapas (PipeWire + mezcladores de ALSA) y basta
# con que UNA quede al 40% para que el parlante suene flojo — con los
# Logitech S150 (1.2 W por canal) eso se nota mucho.
# NO sube del 100%: por encima sería ganancia digital sin limitador. Para eso
# está «Volumen voz» en Ajustes del panel, que lleva limitador suave.
if [ -x "$REPO/pi/volumen-max.sh" ]; then
    "$REPO/pi/volumen-max.sh" --silencioso < /dev/null || true
fi

# ── 5. Dónde se abre el panel ───────────────────────────────────────────
IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo
echo "  Panel de control:"
[ -n "$IP" ] && echo "      http://$IP:8000"
echo "      http://$(hostname):8000"
echo "      http://localhost:8000     (en la propia Pi)"
echo
echo "  Para parar MECH: Ctrl+C aquí, o cerrá esta ventana."
echo "════════════════════════════════════════════════════════"
echo

# ── 6. Arrancar ─────────────────────────────────────────────────────────
# El panel se abre en SEGUNDO PLANO: `panel-mech.sh` espera a que el servidor
# responda y entonces lo abre. Tiene que lanzarse ANTES del servidor porque
# éste se queda en primer plano ocupando la ventana.
if [ "$ABRIR_PANEL" -eq 1 ]; then
    ( "$REPO/pi/panel-mech.sh" --silencioso < /dev/null > /dev/null 2>&1 & )
fi

# Bucle con auto-reinicio (sep 2026): si el server se cae SOLO (un bug, el
# crash de ALSA, un bajón de corriente), se vuelve a levantar solo en vez de
# quedarse esperando a que alguien lea la ventana. Antes, cada caída exigía
# ir a la Pi a "recuperar los sistemas".
#
# Qué NO se reinicia:
#   - salida limpia (código 0): apagado pedido desde el panel/script;
#   - Ctrl+C (código 130): apagado pedido a mano en esta ventana.
# Después de MAX_CAIDAS caídas seguidas se deja la ventana abierta para poder
# leer el error: si se cae siempre al arrancar, reiniciarlo en bucle no
# arregla nada y oculta el motivo.
CAIDAS_SEGUIDAS=0
MAX_CAIDAS=5
while :; do
    python3 -m backend.server
    RC=$?
    # 0 = salida limpia; 130 = Ctrl+C. Los dos son apagados A PROPÓSITO.
    if [ "$RC" -eq 0 ] || [ "$RC" -eq 130 ]; then
        break
    fi
    CAIDAS_SEGUIDAS=$((CAIDAS_SEGUIDAS + 1))
    if [ "$CAIDAS_SEGUIDAS" -gt "$MAX_CAIDAS" ]; then
        echo
        echo "  El servidor se cayó $MAX_CAIDAS veces seguidas; dejo de"
        echo "  reintentar para poder leer el error. Corregí la causa y"
        echo "  volvé a iniciar."
        break
    fi
    echo
    echo "  El servidor se detuvo (código $RC). Lo reinicio solo en 4 s"
    echo "  (caída $CAIDAS_SEGUIDAS/$MAX_CAIDAS)..."
    echo
    sleep 4
done

# Si llegamos aquí, el servidor terminó (Ctrl+C, apagado o un error).
echo
echo "════════════════════════════════════════════════════════"
echo "  El servidor de MECH se detuvo."
echo "════════════════════════════════════════════════════════"
read -r -p "  Pulsa Enter para cerrar esta ventana..."
