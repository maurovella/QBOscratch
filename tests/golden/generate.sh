#!/bin/sh
# Regenera los golden masters ejecutando el codigo ORIGINAL de Python 2.7.
# Usa Docker (python:2.7-slim): no instala Python 2 en el sistema.
# El codigo original sale de la rama legacy-python2, que es el snapshot de la
# SSD vieja del robot. Solo hace falta volver a correr esto si cambian los casos.
set -e
cd "$(dirname "$0")/../.."
REF="${LEGACY_REF:-legacy-python2}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/py2"
git archive "$REF" "Python projects" Tooly deamonsScripts | tar -x -C "$WORK/py2"
cp -R tests "$WORK/tests"

run_py2() {
    docker run --rm -e PYTHONDONTWRITEBYTECODE=1 -v "$WORK:/w" -w /w python:2.7-slim "$@"
}

echo "protocolo: QboCmd.py de $REF"
run_py2 python tests/golden/gen_protocol.py "/w/py2/Python projects" > tests/golden/protocol_py2.json

echo "apps: scripts de $REF contra el robot de mentira"
run_py2 python tests/golden/gen_apps.py /w/py2 /home/pi/Documents > tests/golden/apps_py2.json
