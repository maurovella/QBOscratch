#!/usr/bin/env python3
"""Prueba que indices de camara entregan imagen, sin abrir ventanas.

    python3 tools/camera_probe.py            prueba los indices 0 a 3
    python3 tools/camera_probe.py 0 2        prueba solo esos

Reemplaza al RightEye.py de la carpeta Tooly, que abria las camaras 1 y 0 y
las soltaba sin decir nada. Sale con codigo 0 si al menos una dio un cuadro.
"""
import sys

import cv2


def probe(index):
    cap = cv2.VideoCapture(index)
    try:
        if not cap.isOpened():
            return "no abre"
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        ok, frame = cap.read()
        if not ok or frame is None:
            return "abre pero no entrega cuadros (nodo de metadatos o camara ocupada)"
        return "OK %dx%d" % (frame.shape[1], frame.shape[0])
    finally:
        cap.release()


def main(argv):
    indices = [int(a) for a in argv] or [0, 1, 2, 3]
    good = 0
    for index in indices:
        result = probe(index)
        good += result.startswith("OK")
        print("camara %d: %s" % (index, result))
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
