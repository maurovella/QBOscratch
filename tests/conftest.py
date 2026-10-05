"""Configuracion comun de los tests. Nada de aca necesita el robot."""
import importlib.util
import os
import sys

TESTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TESTS)

sys.path.insert(0, ROOT)     # paquete qbo

# tests/fakes va primero: `import serial` resuelve al doble, no a pyserial.
sys.path.insert(0, os.path.join(TESTS, "golden"))
sys.path.insert(0, os.path.join(TESTS, "fakes"))

# Unico lugar que sabe donde vive el driver del protocolo.
PROTOCOL_PATH = os.path.join(ROOT, "qbo", "protocol.py")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_protocol():
    return load_module("qbo_protocol_under_test", PROTOCOL_PATH)
