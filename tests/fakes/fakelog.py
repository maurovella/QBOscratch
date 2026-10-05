"""Registro de eventos de los dobles de prueba (serie, HTTP, STT, TTS).

Cada evento es una linea JSON en el archivo $FAKE_EVENTS. Compatible con
Python 2.7 y 3: lo usa tambien el generador de golden masters en Docker.
"""
import json
import os

events = []


def emit(kind, **fields):
    event = {"k": kind}
    event.update(fields)
    events.append(event)
    path = os.environ.get("FAKE_EVENTS")
    if path:
        with open(path, "a") as fh:
            fh.write(json.dumps(event, sort_keys=True) + "\n")
    return event


def hexstr(data):
    return " ".join("%02X" % b for b in bytearray(data))
