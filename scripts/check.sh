#!/bin/sh
# Gate unico de la migracion. Corre en una maquina de desarrollo, sin el robot.
#   scripts/check.sh            gate sintactico + tests
#   scripts/check.sh --fast     solo gate sintactico
# Usa uv si esta instalado (fija Python 3.13, el de Raspbian 13). Si no, usa
# $PYTHON o python3 y espera que requirements-dev.txt ya este instalado.
set -e
cd "$(dirname "$0")/.."

if [ -z "$PYTHON" ] && command -v uv >/dev/null 2>&1; then
    RUN="uv run -q --no-project --python 3.13 --with-requirements requirements-dev.txt python"
else
    RUN="${PYTHON:-python3}"
fi

echo "== gate sintactico =="
$RUN scripts/check_syntax.py

if [ "$1" != "--fast" ]; then
    echo "== tests =="
    $RUN -m pytest -q tests
fi
