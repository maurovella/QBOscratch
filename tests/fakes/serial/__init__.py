"""Doble de pyserial para probar sin el robot.

Reemplaza al modulo `serial` (se antepone tests/fakes al sys.path). Guarda lo
que el codigo escribe y permite inyectar respuestas. Con FAKE_QBOARD=1 ademas
responde como el firmware de la Q-board (serialProtocol.c): ACK con el mismo
formato de trama, NACK `FF FE` si el checksum o el largo no cierran.

Compatible con Python 2.7 y 3, porque el mismo doble se usa para capturar el
comportamiento del codigo original en Docker.
"""
import os

import fakelog

__version__ = "fake"

EIGHTBITS = 8
STOPBITS_ONE = 1
PARITY_NONE = "N"

INPUT_FLAG = 0xFF
OUTPUT_FLAG = 0xFE
INPUT_ESCAPE = 0xFD

# Tabla de Pearson del firmware (copia independiente del codigo bajo prueba).
PEARSON = [
    0x00, 0x77, 0xee, 0x99, 0x07, 0x70, 0xe9, 0x9e, 0x0e, 0x79, 0xe0, 0x97,
    0x09, 0x7e, 0xe7, 0x90, 0x1d, 0x6a, 0xf3, 0x84, 0x1a, 0x6d, 0xf4, 0x83,
    0x13, 0x64, 0xfd, 0x8a, 0x14, 0x63, 0xfa, 0x8d, 0x3b, 0x4c, 0xd5, 0xa2,
    0x3c, 0x4b, 0xd2, 0xa5, 0x35, 0x42, 0xdb, 0xac, 0x32, 0x45, 0xdc, 0xab,
    0x26, 0x51, 0xc8, 0xbf, 0x21, 0x56, 0xcf, 0xb8, 0x28, 0x5f, 0xc6, 0xb1,
    0x2f, 0x58, 0xc1, 0xb6, 0x76, 0x01, 0x98, 0xef, 0x71, 0x06, 0x9f, 0xe8,
    0x78, 0x0f, 0x96, 0xe1, 0x7f, 0x08, 0x91, 0xe6, 0x6b, 0x1c, 0x85, 0xf2,
    0x6c, 0x1b, 0x82, 0xf5, 0x65, 0x12, 0x8b, 0xfc, 0x62, 0x15, 0x8c, 0xfb,
    0x4d, 0x3a, 0xa3, 0xd4, 0x4a, 0x3d, 0xa4, 0xd3, 0x43, 0x34, 0xad, 0xda,
    0x44, 0x33, 0xaa, 0xdd, 0x50, 0x27, 0xbe, 0xc9, 0x57, 0x20, 0xb9, 0xce,
    0x5e, 0x29, 0xb0, 0xc7, 0x59, 0x2e, 0xb7, 0xc0, 0xed, 0x9a, 0x03, 0x74,
    0xea, 0x9d, 0x04, 0x73, 0xe3, 0x94, 0x0d, 0x7a, 0xe4, 0x93, 0x0a, 0x7d,
    0xf0, 0x87, 0x1e, 0x69, 0xf7, 0x80, 0x19, 0x6e, 0xfe, 0x89, 0x10, 0x67,
    0xf9, 0x8e, 0x17, 0x60, 0xd6, 0xa1, 0x38, 0x4f, 0xd1, 0xa6, 0x3f, 0x48,
    0xd8, 0xaf, 0x36, 0x41, 0xdf, 0xa8, 0x31, 0x46, 0xcb, 0xbc, 0x25, 0x52,
    0xcc, 0xbb, 0x22, 0x55, 0xc5, 0xb2, 0x2b, 0x5c, 0xc2, 0xb5, 0x2c, 0x5b,
    0x9b, 0xec, 0x75, 0x02, 0x9c, 0xeb, 0x72, 0x05, 0x95, 0xe2, 0x7b, 0x0c,
    0x92, 0xe5, 0x7c, 0x0b, 0x86, 0xf1, 0x68, 0x1f, 0x81, 0xf6, 0x6f, 0x18,
    0x88, 0xff, 0x66, 0x11, 0x8f, 0xf8, 0x61, 0x16, 0xa0, 0xd7, 0x4e, 0x39,
    0xa7, 0xd0, 0x49, 0x3e, 0xae, 0xd9, 0x40, 0x37, 0xa9, 0xde, 0x47, 0x30,
    0xbd, 0xca, 0x53, 0x24, 0xba, 0xcd, 0x54, 0x23, 0xb3, 0xc4, 0x5d, 0x2a,
    0xb4, 0xc3, 0x5a, 0x2d
]


def pearson(values):
    h = 0
    for v in values:
        h = PEARSON[h ^ (v & 0xFF)]
    return h


def encode_frame(cmd, data, escape_header=False):
    """Arma una trama como la emite el firmware: FF cmd n data.. chk FE."""
    body = [cmd, len(data)] + list(data)
    body.append(pearson(body))
    out = [INPUT_FLAG]
    for idx, b in enumerate(body):
        if b >= INPUT_ESCAPE and (escape_header or idx >= 2):
            out += [INPUT_ESCAPE, b - 2]
        else:
            out.append(b)
    out.append(OUTPUT_FLAG)
    return bytes(bytearray(out))


def decode_frame(raw):
    """Devuelve (cmd, data) o None si la trama es invalida, como el firmware."""
    raw = list(bytearray(raw))
    if len(raw) < 5 or raw[0] != INPUT_FLAG or raw[-1] != OUTPUT_FLAG:
        return None
    body = []
    escaped = False
    for b in raw[1:-1]:
        if escaped:
            body.append(b + 2)
            escaped = False
        elif b == INPUT_ESCAPE:
            escaped = True
        else:
            body.append(b)
    if len(body) < 3:
        return None
    cmd, n, data, chk = body[0], body[1], body[2:-1], body[-1]
    if n != len(data) or pearson(body[:-1]) != chk:
        return None
    return cmd, data


class QBoard(object):
    """Simulador minimo de la placa: contesta ACK, y GET_TOUCH con un guion."""

    GET_TOUCH = 0x46

    def __init__(self):
        script = os.environ.get("FAKE_TOUCH", "")
        self.touch_script = [int(x) for x in script.split(",") if x != ""]

    def answer(self, frame):
        decoded = decode_frame(frame)
        if decoded is None:
            return bytes(bytearray([INPUT_FLAG, OUTPUT_FLAG]))
        cmd, _data = decoded
        if cmd == self.GET_TOUCH:
            value = self.touch_script.pop(0) if self.touch_script else 0
            return encode_frame(cmd, [value])
        return encode_frame(cmd, [])


class Serial(object):
    instances = []

    def __init__(self, port=None, baudrate=9600, **kwargs):
        self.name = port
        self.port = port
        self.baudrate = baudrate
        self.timeout = kwargs.get("timeout")
        self.kwargs = kwargs
        self.tx = []            # una entrada por write()
        self.responses = []     # respuestas crudas, una por write()
        self._rx = bytearray()
        self.is_open = True
        self.board = QBoard() if os.environ.get("FAKE_QBOARD") == "1" else None
        Serial.instances.append(self)
        fakelog.emit("serial_open", port=port, baudrate=baudrate)

    # -- API que usa el robot ------------------------------------------------
    def write(self, data):
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("unicode strings are not supported, please encode to bytes: %r" % (data,))
        data = bytes(bytearray(data))
        self.tx.append(data)
        fakelog.emit("serial_tx", hex=fakelog.hexstr(data))
        if self.responses:
            self._rx += bytearray(self.responses.pop(0))
        elif self.board is not None:
            self._rx += bytearray(self.board.answer(data))
        return len(data)

    def read(self, size=1):
        chunk = bytes(self._rx[:size])
        del self._rx[:size]
        return chunk

    def reset_input_buffer(self):
        self._rx = bytearray()

    def flush(self):
        pass

    def close(self):
        self.is_open = False

    def isOpen(self):
        return self.is_open

    @property
    def in_waiting(self):
        return len(self._rx)

    # -- ayudas para los tests ------------------------------------------------
    def inject(self, raw):
        """Deja bytes listos para leer ya, sin esperar un write()."""
        self._rx += bytearray(raw)
