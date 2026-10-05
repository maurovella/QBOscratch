#!/bin/bash
# Prepara una Raspberry Pi con Raspbian 13 (trixie) para correr el robot.
#
#   deploy/install.sh            instala
#   deploy/install.sh --dry-run  muestra lo que haria, sin tocar nada
#
# Estrategia (PEP 668: en trixie 'pip install' global esta bloqueado):
#   - todo lo compilado se instala con apt (deploy/apt-packages.txt),
#   - un venv en ~/qbo-venv creado con --system-site-packages ve esos paquetes,
#   - pip instala dentro del venv lo unico que apt no tiene (SpeechRecognition).
# Se puede correr mas de una vez.
set -e

QBO_HOME="${QBO_HOME:-/home/pi/Documents}"
VENV="${QBO_VENV:-$HOME/qbo-venv}"
HERE="$(cd "$(dirname "$0")" && pwd)"
DRY=""
[ "$1" = "--dry-run" ] && DRY="echo +"

echo "== paquetes apt =="
PACKAGES=$(grep -v '^#' "$HERE/apt-packages.txt" | tr '\n' ' ')
$DRY sudo apt-get update
$DRY sudo apt-get install -y $PACKAGES

echo "== venv en $VENV =="
if [ ! -x "$VENV/bin/python" ]; then
    $DRY python3 -m venv --system-site-packages "$VENV"
fi
$DRY "$VENV/bin/pip" install -r "$HERE/requirements-pi.txt"

echo "== permisos =="
# dialout: /dev/serial0. audio: ALSA. video: camaras.
$DRY sudo usermod -aG dialout,audio,video "$USER"
$DRY chmod +x "$QBO_HOME"/deamonsScripts/QBO_* "$QBO_HOME"/deamonsScripts/lsqbo \
    "$QBO_HOME"/deamonsScripts/*.sh "$QBO_HOME"/deamonsScripts/*.py "$QBO_HOME/Python projects"/*.py

echo "== FIFOs =="
$DRY mkdir -p "$QBO_HOME/pipes"
for pipe in pipe_cmd pipe_say pipe_listen pipe_feel pipe_findFace; do
    [ -p "$QBO_HOME/pipes/$pipe" ] || $DRY mkfifo "$QBO_HOME/pipes/$pipe"
done

echo "== TTS =="
if command -v pico2wave >/dev/null 2>&1; then
    echo "pico2wave: $(command -v pico2wave)"
else
    cat <<'MSG'
FALTA pico2wave. Raspbian de 32 bits no trae libttspico-utils; Debian si
(seccion non-free). En Raspberry Pi OS de 64 bits:
    sudo apt-get install libttspico-utils
En Raspbian de 32 bits, bajar de https://packages.debian.org/trixie/libttspico-utils
los .deb armhf de libttspico-data, libttspico0t64 y libttspico-utils, y:
    sudo apt-get install ./libttspico-data_*.deb ./libttspico0t64_*.deb ./libttspico-utils_*.deb
MSG
fi

echo "== listo =="
echo "Cerrar sesion y volver a entrar para que valgan los grupos nuevos."
echo "Despues: scripts/smoke/smoke.sh"
