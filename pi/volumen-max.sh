#!/usr/bin/env bash
#
# Volumen al máximo — pone TODAS las etapas de volumen de la Pi a tope.
#
# El audio pasa por varios controles antes de llegar al parlante: el sink de
# PipeWire y uno o varios mezcladores de ALSA del dispositivo. Basta con que
# UNO esté al 40% para que todo suene flojo, y es fácil no darse cuenta
# porque no hay un sitio único donde mirarlo.
#
# Esto es ganancia GRATIS: no distorsiona, solo deja de desperdiciar margen.
# Es lo PRIMERO que hay que hacer con un parlante flojo (los Logitech S150 dan
# 1.2 W por canal, contra los ~30 W de un JBL Charge 5).
#
# NO sube por encima del 100%. Eso sería ganancia digital sin limitador y la
# voz sonaría rota; para eso está «Volumen voz» en Ajustes del panel, que
# hace lo mismo pero con un limitador suave.
#
# Se corre con doble click desde el explorador de archivos, o:
#     bash ~/MECH/pi/volumen-max.sh
#
# Con `--silencioso` resume en una línea y no espera un Enter: así lo llama
# `iniciar-mech.sh` en CADA arranque, para que nadie tenga que acordarse.

set -u

CALLADO=0
[ "${1:-}" = "--silencioso" ] && CALLADO=1
decir() { [ "$CALLADO" -eq 1 ] || echo "$1"; }

if [ "$CALLADO" -eq 1 ]; then
    echo "  Volumen del sistema al máximo..."
else
    echo "════════════════════════════════════════════════════════"
    echo "  Volumen de la Raspberry Pi al máximo"
    echo "════════════════════════════════════════════════════════"
    echo
fi

# ── 1. PipeWire / WirePlumber (lo normal en Bookworm) ───────────────────
if command -v wpctl > /dev/null 2>&1; then
    decir "  PipeWire:"
    decir "    antes:  $(wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>/dev/null || echo '?')"
    wpctl set-mute   @DEFAULT_AUDIO_SINK@ 0   2>/dev/null
    wpctl set-volume @DEFAULT_AUDIO_SINK@ 1.0 2>/dev/null
    decir "    ahora:  $(wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>/dev/null || echo '?')"
    decir ""
else
    decir "  (wpctl no está; salto PipeWire)"
    decir ""
fi

# ── 2. Mezcladores de ALSA, tarjeta por tarjeta ─────────────────────────
# Los nombres de los controles cambian según el dispositivo ("PCM",
# "Speaker", "Master", "Headphone"...), así que se enumeran en vez de
# adivinarlos. Solo se tocan los que tienen volumen de REPRODUCCIÓN.
if command -v amixer > /dev/null 2>&1; then
    TARJETAS="$(aplay -l 2>/dev/null | sed -n 's/^tarjeta \([0-9]*\).*/\1/p; s/^card \([0-9]*\).*/\1/p' | sort -u)"
    [ -z "$TARJETAS" ] && TARJETAS="0"
    for c in $TARJETAS; do
        NOMBRE="$(aplay -l 2>/dev/null | grep -E "^(tarjeta|card) $c:" | head -1 | cut -d: -f2- | cut -d, -f1)"
        decir "  Tarjeta $c:${NOMBRE}"
        CONTROLES="$(amixer -c "$c" scontrols 2>/dev/null |
                     sed -n "s/^Simple mixer control '\([^']*\)'.*/\1/p")"
        if [ -z "$CONTROLES" ]; then
            decir "    (sin controles de mezclador)"
            decir ""
            continue
        fi
        while IFS= read -r ctl; do
            [ -z "$ctl" ] && continue
            INFO="$(amixer -c "$c" sget "$ctl" 2>/dev/null)"
            # Solo los que tienen volumen de reproducción; los de captura y
            # los interruptores sueltos no nos interesan aquí.
            echo "$INFO" | grep -q "Playback channels" || continue
            echo "$INFO" | grep -q "Limits: Playback"  || continue
            ANTES="$(echo "$INFO" | grep -o '\[[0-9]*%\]' | head -1)"
            amixer -c "$c" sset "$ctl" 100% unmute > /dev/null 2>&1
            DESPUES="$(amixer -c "$c" sget "$ctl" 2>/dev/null |
                       grep -o '\[[0-9]*%\]' | head -1)"
            [ "$CALLADO" -eq 1 ] || printf "    %-22s %s -> %s\n" \
                "$ctl" "${ANTES:-?}" "${DESPUES:-?}"
        done <<< "$CONTROLES"
        decir ""
    done
else
    decir "  (amixer no está; instalalo con: sudo apt install alsa-utils)"
    decir ""
fi

# ── 3. Guardar para que sobreviva al reinicio ───────────────────────────
if command -v alsactl > /dev/null 2>&1; then
    if sudo -n true 2>/dev/null; then
        sudo alsactl store 2>/dev/null && decir "  Guardado (sobrevive al reinicio)."
    else
        decir "  Para que sobreviva al reinicio, corré una vez:"
        decir "      sudo alsactl store"
    fi
    decir ""
fi

if [ "$CALLADO" -eq 1 ]; then
    exit 0   # lo llamó iniciar-mech.sh: nada de banners ni de esperar
fi

echo "════════════════════════════════════════════════════════"
echo "  Listo. Si AÚN suena bajo:"
echo
echo "   1. Los 3 botones del parlante (-, mute, + en el frente del"
echo "      derecho): que NO este en mute, y darle varias veces al +."
echo "   2. Panel -> Ajustes -> «Volumen voz»: subilo a +6 dB."
echo "      (Eso es ganancia digital CON limitador; subir PipeWire por"
echo "       encima del 100% hace lo mismo pero sin limitador y la voz"
echo "       sale rota.)"
echo "   3. Si con eso no alcanza, es el parlante: los S150 son de 1.2 W"
echo "      por canal. Uno amplificado de 10-20 W lo resuelve de verdad."
echo "════════════════════════════════════════════════════════"
read -r -p "  Pulsa Enter para cerrar..."
