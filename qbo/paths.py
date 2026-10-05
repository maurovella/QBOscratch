"""Rutas del robot, en un solo lugar.

El robot espera el repo desplegado en /home/pi/Documents. La variable de
entorno QBO_HOME cambia esa raiz, que es lo que permite correr los scripts y
los tests en una maquina de desarrollo.
"""
import os

HOME = os.environ.get("QBO_HOME", "/home/pi/Documents")

CONFIG = os.path.join(HOME, "config.yml")
PIPES = os.path.join(HOME, "pipes")
DAEMONS = os.path.join(HOME, "deamonsScripts")
TTS_WAV = os.path.join(HOME, "pico2wave.wav")
BLIP = os.path.join(HOME, "blip.wav")

# Las cascadas Haar viajan con el paquete: no dependen de donde este el repo.
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
HAAR_FRONTAL = os.path.join(DATA, "haarcascade_frontalface_alt2.xml")
HAAR_PROFILE = os.path.join(DATA, "haarcascade_profileface.xml")

SERIAL_PORT = "/dev/serial0"


def pipe(name):
    """Ruta de un FIFO: pipe_cmd, pipe_say, pipe_listen, pipe_feel, pipe_findFace."""
    return os.path.join(PIPES, name)


def daemon(name):
    """Ruta de un script de deamonsScripts/, por ejemplo QBO_listen."""
    return os.path.join(DAEMONS, name)
