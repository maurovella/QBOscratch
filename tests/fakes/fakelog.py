"""Registro de eventos de los dobles de prueba (serie, HTTP, STT, TTS).

Cada evento es una linea JSON en el archivo $FAKE_EVENTS. Compatible con
Python 2.7 y 3: lo usa tambien el generador de golden masters en Docker.
"""
import json
import os

events = []
on_emit = None      # el arnes lo usa para cortar la corrida de forma determinista


def emit(kind, **fields):
    event = {"k": kind}
    event.update(fields)
    events.append(event)
    path = os.environ.get("FAKE_EVENTS")
    if path:
        with open(path, "a") as fh:
            fh.write(json.dumps(event, sort_keys=True) + "\n")
    if on_emit is not None:
        on_emit(kind)
    return event


def hexstr(data):
    return " ".join("%02X" % b for b in bytearray(data))


# --- guion de la corrida ------------------------------------------------------

_scenario = None


def scenario():
    """Guion JSON de $FAKE_SCENARIO: que ve la camara, que oye el microfono, etc."""
    global _scenario
    if _scenario is None:
        path = os.environ.get("FAKE_SCENARIO")
        if path:
            with open(path) as fh:
                _scenario = json.load(fh)
        else:
            _scenario = {}
    return _scenario


def take(key, default=None):
    """Saca el proximo elemento de la lista `key` del guion."""
    items = scenario().get(key)
    if items:
        return items.pop(0)
    return default


class Clock(object):
    """Reloj falso: sleep() no espera, solo adelanta la hora y queda registrado."""

    def __init__(self):
        self.now = 1700000000.0

    def time(self):
        self.now += 0.001
        return self.now

    def sleep(self, seconds):
        emit("sleep", s=seconds)
        self.now += seconds

    def advance(self, seconds):
        self.now += seconds


clock = Clock()
