#!/bin/bash
# Relevamiento automatico del robot: junta en un archivo el estado de cada
# modulo, sin cambiar nada. No usa sudo, no instala, no mueve la cabeza.
#
#   scripts/smoke/relevar.sh
#
# Tarda menos de un minuto. Deja el informe en ~/qbo-relevamiento-<fecha>.txt y
# al final imprime una tabla: que esta OK y que FALTA. Con eso se sabe por donde
# empezar antes de correr smoke.sh. El informe es lo que hay que traer de vuelta
# si algo no anda: tiene todo lo que hace falta para diagnosticar sin el robot.

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
QBO_HOME="${QBO_HOME:-/home/pi/Documents}"
if [ -z "$QBO_PYTHON" ]; then
    if [ -x "$HOME/qbo-venv/bin/python" ]; then QBO_PYTHON="$HOME/qbo-venv/bin/python"; else QBO_PYTHON=python3; fi
fi
OUT="$HOME/qbo-relevamiento-$(date +%Y%m%d-%H%M).txt"
umask 077       # el informe describe el sistema: que lo lea solo su dueno
SUMMARY=""

have() { command -v "$1" >/dev/null 2>&1; }

# limite de tiempo por comando, si existe 'timeout'
limit() { if have timeout; then timeout "$@"; else shift; "$@"; fi; }

section() { printf '\n######## %s\n' "$1" | tee -a "$OUT"; }

# run "comando": lo muestra y guarda su salida, falle o no
run() {
    printf '\n$ %s\n' "$1" >> "$OUT"
    limit 20 bash -c "$1" >> "$OUT" 2>&1
    printf '[codigo %s]\n' "$?" >> "$OUT"
}

# check "modulo" "que se mira" "comando": OK si el comando sale con 0
check() {
    local estado=FALTA
    if limit 20 bash -c "$3" >/dev/null 2>&1; then estado=OK; fi
    SUMMARY="$SUMMARY$(printf '%-6s %-12s %s' "$estado" "$1" "$2")\n"
}

: > "$OUT"
echo "Relevamiento del robot QBO, $(date)" | tee -a "$OUT"
echo "repo: $ROOT   QBO_HOME: $QBO_HOME   python: $QBO_PYTHON" | tee -a "$OUT"

section "Sistema"
run "cat /etc/os-release"
run "uname -a"
run "tr -d '\\0' < /proc/device-tree/model"
run "whoami; id"
run "uptime; df -h / | tail -1; free -m | head -2"
run "echo DISPLAY=\$DISPLAY XDG_SESSION_TYPE=\$XDG_SESSION_TYPE; systemctl get-default"

section "Arranque (config.txt y cmdline.txt)"
run "grep -v -E '^\\s*(#|\$)' /boot/firmware/config.txt || grep -v -E '^\\s*(#|\$)' /boot/config.txt"
run "cat /boot/firmware/cmdline.txt || cat /boot/cmdline.txt"

section "UART y Q-board"
run "ls -l /dev/serial0 /dev/serial1 /dev/ttyAMA0 /dev/ttyS0"
run "systemctl is-active serial-getty@ttyS0.service serial-getty@ttyAMA0.service hciuart.service"
run "$(printf '%q' "$QBO_PYTHON") $(printf '%q' "$ROOT/scripts/smoke/qboard.py") version"

section "Audio"
run "aplay -l"
run "arecord -l"
run "aplay -L | grep -E '^(convertQBO|dmicQBO|dmicQBO_sv|speakerQBO|default)'"
run "lsmod | grep -i -E 'my_loader|snd_soc_simple|snd_soc_bcm2835_i2s|snd_soc_core'"
run "ls -l /lib/modules/\$(uname -r)/my_loader.ko; cat /etc/modules"
run "ls /sys/bus/platform/devices | grep -i i2s"
run "dpkg -l 'linux-headers*' | grep '^ii'; ls -d /lib/modules/\$(uname -r)/build"
run "cat /etc/asound.conf"
run "cat \$HOME/.asoundrc"
run "dmesg | grep -i -E 'my_loader|simple-card|asoc|i2s' | tail -20"
run "command -v pico2wave; dpkg -l | grep -i ttspico"

section "Camaras"
run "lsusb"
run "v4l2-ctl --list-devices"
run "ls -l /dev/video*"
run "$(printf '%q' "$QBO_PYTHON") $(printf '%q' "$ROOT/tools/camera_probe.py")"

section "Python"
run "$(printf '%q' "$QBO_PYTHON") --version; ls -d \$HOME/qbo-venv"
for mod in serial yaml requests numpy cv2 pyaudio speech_recognition; do
    run "$(printf '%q' "$QBO_PYTHON") -c 'import $mod; print(\"$mod\", getattr($mod, \"__version__\", \"?\"))'"
done

section "Red y servicios externos"
# La URL del LLM puede traer usuario y clave. Va a curl por una variable de
# entorno y no se escribe en el informe; lo que se muestra sale de show_config.py.
QBO_RELEVAR_LLM_URL="$("$QBO_PYTHON" "$ROOT/scripts/smoke/show_config.py" "$QBO_HOME/config.yml" --llm-url 2>/dev/null)"
export QBO_RELEVAR_LLM_URL
run "hostname -I; ip route | head -3"
run "ping -c 1 -W 3 8.8.8.8"
run "curl -s -m 8 -o /dev/null -w 'google: HTTP %{http_code}\\n' https://www.google.com"
run 'test -n "$QBO_RELEVAR_LLM_URL" && curl -s -m 8 "$QBO_RELEVAR_LLM_URL/api/tags" | head -c 600'

section "Repo y configuracion"
run "git -C $(printf '%q' "$ROOT") log --oneline -1; git -C $(printf '%q' "$ROOT") status --short | head -20"
# show_config.py muestra solo las claves publicas; el resto sale como <oculto>
run "$(printf '%q' "$QBO_PYTHON") $(printf '%q' "$ROOT/scripts/smoke/show_config.py") $(printf '%q' "$QBO_HOME/config.yml")"
run "ls -l $(printf '%q' "$QBO_HOME/pipes")"
run "ls -l $(printf '%q' "$QBO_HOME/deamonsScripts") | head -20"
run "test -f \$HOME/.config/qbo/tooly.env && echo 'tooly.env existe (no se muestra)' || echo 'tooly.env no existe: sin alertas por mail'"

section "Procesos del robot"
run "ps aux | grep -E 'PiCmd|say\\.py|listen|feel\\.py|findFace|PiFaceFast|tooly|websocket_server' | grep -v grep"
run "systemctl is-enabled qbo-tooly.service qbo-scratch.service; systemctl is-active qbo-tooly.service qbo-scratch.service"

# ---- tabla resumen ---------------------------------------------------------
PYQ="$(printf '%q' "$QBO_PYTHON")"
check "entorno"  "venv ~/qbo-venv"                          "test -x \$HOME/qbo-venv/bin/python"
check "entorno"  "paquetes Python (serial, cv2, yaml, requests, numpy)" "$PYQ -c 'import serial, cv2, yaml, requests, numpy'"
check "entorno"  "SpeechRecognition y PyAudio"              "$PYQ -c 'import speech_recognition, pyaudio'"
check "UART"     "/dev/serial0 existe"                      "test -e /dev/serial0"
check "UART"     "usuario en el grupo dialout"              "id -nG | grep -qw dialout"
check "UART"     "sin consola serie en cmdline.txt"         "f=/boot/firmware/cmdline.txt; test -f \$f || f=/boot/cmdline.txt; test -f \$f && ! grep -q 'console=serial0' \$f"
check "Q-board"  "la placa contesta GET_VERSION"            "$PYQ $(printf '%q' "$ROOT/scripts/smoke/qboard.py") version"
check "audio"    "modulo my_loader cargado"                 "lsmod | grep -q my_loader"
check "audio"    "tarjeta sndrpisimplecar"                  "aplay -l | grep -qi sndrpisimplecar"
check "audio"    "dispositivo convertQBO (parlante)"        "aplay -L | grep -q '^convertQBO'"
check "audio"    "dispositivo dmicQBO_sv (microfono)"       "aplay -L | grep -q '^dmicQBO_sv' || arecord -L | grep -q '^dmicQBO_sv'"
check "voz"      "pico2wave instalado"                      "command -v pico2wave"
check "camaras"  "al menos una camara entrega imagen"       "$PYQ $(printf '%q' "$ROOT/tools/camera_probe.py")"
check "red"      "internet (Google, para el reconocimiento de voz)" "curl -s -m 8 -o /dev/null https://www.google.com"
check "LLM"      "servidor de config.yml responde"          'test -n "$QBO_RELEVAR_LLM_URL" && curl -s -f -m 8 -o /dev/null "$QBO_RELEVAR_LLM_URL/api/tags"'
check "Tooly"    "ventana grafica disponible (DISPLAY)"     "test -n \"\$DISPLAY\""
check "mail"     "credenciales de alertas (tooly.env)"      "test -f \$HOME/.config/qbo/tooly.env"

{
    printf '\n######## Resumen\n'
    printf '%b' "$SUMMARY"
} | tee -a "$OUT"

echo
echo "Informe completo: $OUT"
echo "Que significa cada FALTA y que hacer: docs/Relevamiento_robot.md"
