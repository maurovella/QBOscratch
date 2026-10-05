#!/usr/bin/env python3
"""Busca una cara con la camara y las cascadas del repo, sin abrir ventanas.

    face_once.py [indice de camara] [segundos]

Sale con 0 apenas detecta una cara. Aisla camara + OpenCV + cascadas Haar.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import cv2  # noqa: E402

from qbo import paths  # noqa: E402


def main(argv):
    index = int(argv[0]) if argv else 0
    seconds = float(argv[1]) if len(argv) > 1 else 15
    cascade = cv2.CascadeClassifier(paths.HAAR_FRONTAL)
    if cascade.empty():
        print("FALLA: OpenCV no pudo cargar " + paths.HAAR_FRONTAL)
        return 1
    cap = cv2.VideoCapture(index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    print("Ponete frente a la camara %d (%d segundos)" % (index, seconds))
    frames = 0
    deadline = time.time() + seconds
    try:
        while time.time() < deadline:
            ok, frame = cap.read()
            if not ok or frame is None:
                print("FALLA: la camara %d no entrega cuadros" % index)
                return 1
            frames += 1
            flags = cv2.CASCADE_DO_CANNY_PRUNING | cv2.CASCADE_FIND_BIGGEST_OBJECT | cv2.CASCADE_DO_ROUGH_SEARCH
            faces = cascade.detectMultiScale(frame, 1.3, 4, flags, (60, 60))
            if len(faces) > 0:
                x, y, w, h = faces[0]
                print("cara detectada: centro en (%d, %d), %d cuadros leidos" % (w // 2 + x, h // 2 + y, frames))
                return 0
    finally:
        cap.release()
    print("no se detecto ninguna cara en %d cuadros" % frames)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
