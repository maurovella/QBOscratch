#!/usr/bin/env python3
"""Habla con la Q-board por la UART, un subsistema por vez. Para el smoke test.

    qboard.py version              la placa contesta GET_VERSION
    qboard.py nose blue|red|green|none
    qboard.py mouth smile|sad|serious|love|off
    qboard.py touch [segundos]     muestra el sensor tactil (0 nada, 1 derecha, 2 arriba, 3 izquierda)
    qboard.py head                 mueve la cabeza y vuelve al centro
    qboard.py speaker on|off       SET_ENABLE_SPEAKER (0x86): habilita el amplificador

Sale con 0 si la placa contesto lo esperado. No lee config.yml ni usa FIFOs:
si esto falla, el problema esta en el cable, la UART o la placa.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import serial  # noqa: E402

from qbo import paths  # noqa: E402
from qbo import protocol as QboCmd  # noqa: E402

NOSE = {"none": 0, "blue": 1, "red": 2, "green": 4}
MOUTH = {"smile": 0x110E00, "sad": 0x0E1100, "serious": 0x1F1F00, "love": 0x1B1F0E04, "off": 0}
SET_ENABLE_SPEAKER = 0x86


def hexstr(data):
    return " ".join("%02X" % b for b in bytearray(data))


def open_board():
    port = os.environ.get("QBO_SERIAL_PORT", paths.SERIAL_PORT)
    ser = serial.Serial(port, baudrate=115200, bytesize=serial.EIGHTBITS, stopbits=serial.STOPBITS_ONE,
                        parity=serial.PARITY_NONE, rtscts=False, dsrdtr=False, timeout=0)
    return QboCmd.Controller(ser)


def acked(board, sent):
    """Lee la respuesta a un comando SET: la placa devuelve la misma cabecera."""
    print("enviado:   " + hexstr(sent))
    answer = board.ReadResponse()
    print("respuesta: " + (hexstr(answer) or "(nada)"))
    if len(answer) >= 5 and answer[1] == sent[1]:
        return 0
    if list(answer) == [0xFF, 0xFE]:
        print("NACK: la placa recibio la trama pero la rechazo (checksum o largo)")
    else:
        print("SIN RESPUESTA: la placa no contesto")
    return 1


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 2
    cmd, args = argv[0], argv[1:]
    board = open_board()

    if cmd == "version":
        version = board.GetHeadCmd("GET_VERSION", 0)
        print("GET_VERSION -> %r" % (version,))
        return 0 if version else 1

    if cmd == "nose":
        board.port.reset_input_buffer()
        return acked(board, board.SetNoseColor(NOSE[args[0]]))

    if cmd == "mouth":
        board.port.reset_input_buffer()
        return acked(board, board.SetMouth(MOUTH[args[0]]))

    if cmd == "speaker":
        board.port.reset_input_buffer()
        return acked(board, board.SendCmdQBO(QboCmd.Command(SET_ENABLE_SPEAKER, 1, 1 if args[0] == "on" else 0)))

    if cmd == "touch":
        seconds = float(args[0]) if args else 10
        names = {0: "nada", 1: "derecha", 2: "arriba", 3: "izquierda"}
        valid = 0
        last = None
        deadline = time.time() + seconds
        print("Toca los costados y la parte de arriba de la cabeza durante %d segundos" % seconds)
        while time.time() < deadline:
            touch = board.GetHeadCmd("GET_TOUCH", 0)
            if touch:
                valid += 1
                if touch[0] != last:
                    last = touch[0]
                    print("tactil = %d (%s)" % (last, names.get(last, "valor fuera de rango")))
            time.sleep(0.25)
        print("%d respuestas validas de GET_TOUCH" % valid)
        return 0 if valid else 1

    if cmd == "head":
        # dentro de los limites que usa Tooly: X 290..725, Y 420..550
        for axis, center, away in ((1, 511, 620), (2, 450, 520)):
            for angle in (center, away, center):
                print("SetServo(eje %d, %d)" % (axis, angle))
                board.SetServo(axis, angle, 100)
                time.sleep(1.5)
        return 0

    print("comando desconocido: " + cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
