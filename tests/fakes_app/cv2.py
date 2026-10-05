"""Doble de OpenCV. Expone la API vieja (cv2.cv.*) y la nueva a la vez, porque
el mismo doble sirve para correr el codigo original de Python 2 y el migrado.

La camara entrega cuadros vacios y el detector devuelve las caras del guion
(clave "faces": una entrada por llamada, [] o [[x, y, w, h], ...]).
Con FAKE_NUMPY=1 las caras salen como arreglos de numpy, igual que en OpenCV 4.
"""
import os

import fakelog

__version__ = "4.fake"

CAP_PROP_FRAME_WIDTH = 3
CAP_PROP_FRAME_HEIGHT = 4
CASCADE_DO_CANNY_PRUNING = 1
CASCADE_FIND_BIGGEST_OBJECT = 4
CASCADE_DO_ROUGH_SEARCH = 8
COLOR_BGR2GRAY = 6


class _OldApi(object):
    CV_CAP_PROP_FRAME_WIDTH = 3
    CV_CAP_PROP_FRAME_HEIGHT = 4
    CV_HAAR_DO_CANNY_PRUNING = 1
    CV_HAAR_FIND_BIGGEST_OBJECT = 4
    CV_HAAR_DO_ROUGH_SEARCH = 8


cv = _OldApi()


class Frame(object):
    def __init__(self, index):
        self.index = index


class VideoCapture(object):
    def __init__(self, index):
        self.index = index
        self.count = 0
        fakelog.emit("cam_open", index=index)

    def set(self, prop, value):
        fakelog.emit("cam_set", index=self.index, prop=prop, value=value)
        return True

    def isOpened(self):
        return True

    def read(self):
        self.count += 1
        fakelog.clock.advance(0.033)   # un cuadro a 30 fps
        return True, Frame(self.count)

    def release(self):
        fakelog.emit("cam_release", index=self.index)


class CascadeClassifier(object):
    def __init__(self, path):
        self.path = path
        fakelog.emit("cascade_load", path=path, exists=os.path.exists(path))

    def empty(self):
        return False

    def detectMultiScale(self, frame, scale, neighbors, flags, min_size):
        faces = fakelog.take("faces", [])
        fakelog.emit("detect", cascade=os.path.basename(self.path), scale=scale,
                     neighbors=neighbors, flags=flags, min_size=list(min_size), faces=faces)
        if not faces:
            return ()
        if os.environ.get("FAKE_NUMPY") == "1":
            import numpy
            return numpy.array(faces, dtype=numpy.int32)
        return [tuple(f) for f in faces]


def rectangle(frame, p1, p2, color, thickness):
    fakelog.emit("rectangle", p1=[int(v) for v in p1], p2=[int(v) for v in p2])


def imshow(title, frame):
    pass


def imwrite(path, frame):
    fakelog.emit("imwrite", path=path)


def waitKey(delay):
    remaining = fakelog.scenario().get("frames")
    if remaining is not None:
        if remaining <= 0:
            return ord("q")
        fakelog.scenario()["frames"] = remaining - 1
    return -1


def destroyAllWindows():
    fakelog.emit("destroy_windows")
