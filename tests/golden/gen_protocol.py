"""Imprime en JSON el resultado de protocol_cases sobre un QboCmd.py dado.

Uso:  python gen_protocol.py <directorio que contiene QboCmd.py>
Lo ejecuta tests/golden/generate.sh dentro de Docker python:2.7-slim.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "fakes"))
sys.path.insert(0, HERE)
sys.path.insert(0, sys.argv[1])

import QboCmd  # noqa: E402
import protocol_cases  # noqa: E402

json.dump(protocol_cases.run_all(QboCmd), sys.stdout, indent=0, sort_keys=True)
sys.stdout.write("\n")
