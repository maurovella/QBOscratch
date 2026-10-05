"""Casos del golden master del protocolo UART de la Q-board.

Se ejecutan igual sobre el QboCmd.py original (Python 2.7, en Docker) y sobre
la version migrada. `run_all(mod)` devuelve {nombre: resultado} con todo en
texto, para poder guardarlo en JSON y compararlo byte a byte.

Compatible con Python 2.7 y 3. No usar f-strings ni nada posterior a 2.7.
"""
import sys

import serial  # el doble de tests/fakes


def hx(data):
    return " ".join("%02X" % b for b in bytearray(data))


class _Quiet(object):
    """Los metodos de QboCmd imprimen; el golden solo mira bytes."""

    def write(self, _text):
        pass

    def flush(self):
        pass


def _controller(mod):
    port = serial.Serial("/dev/fake")
    return port, mod.Controller(port)


def _call(fn):
    saved = sys.stdout
    sys.stdout = _Quiet()
    try:
        try:
            return fn()
        except Exception as exc:  # el tipo de excepcion tambien es comportamiento
            return "EXC " + type(exc).__name__
    finally:
        sys.stdout = saved


# --- TX: metodo publico -> bytes escritos -----------------------------------

MOUTHS = [0x110E00, 0x0E1100, 0x1F1F00, 0x1B1F0E04, 0x00000000, 0xFFFFFFFF, 0x00FD00FE, 0x1F1F1F1F]
SERVOS = [(1, 511, 100), (2, 450, 100), (1, 725, 100), (2, 290, 100), (1, 0, 10), (2, 0, 10),
          (1, 253, 255), (2, 254, 253), (1, 255, 254), (1, 1023, 1999), (2, 420, 40), (1, 550, 0)]
PIDS = [(1, 26, 2, 16), (2, 26, 2, 16), (1, 26, 12, 16), (2, 0, 0, 0), (1, 253, 254, 255)]
RAW = [  # (cmd, nInputs, data)
    (0x86, 1, 1), (0x86, 1, 0),              # SET_ENABLE_SPEAKER
    (0x45, 1, 253), (0x45, 1, 254), (0x45, 1, 255),
    (0x40, 0, []), (0x46, 0, []),            # GET_VERSION, GET_TOUCH
    (0x54, 2, [1, 1]), (0x54, 2, [2, 0]),    # SET_SERVO_ENABLE
    (0x4C, 3, [1, 350]), (0x4D, 3, [1, 600]),  # limites: un valor > 255 ocupa 2 bytes
    (0x4C, 3, [1, 0xFFFE]), (0x4D, 3, [2, 0x8001]), (0x4C, 3, [1, 0xFD00]),  # byte alto con bit 7
    (0x4C, 3, [1, 256]), (0x54, 2, [1, 255]),  # frontera entre 1 y 2 bytes
    (0x44, 4, [0xFD, 0xFE, 0xFF, 0x00]),
    (0x86, 1, [1]),                          # parametro unico pasado como lista
    (0x45, 1, -1),                           # negativo
]
HEAD_CMDS = [  # (nombre de comando, argumento de GetHeadCmd)
    ("GET_TOUCH", 0), ("GET_VERSION", 0), ("GET_HEAD_SERVOS", 0),
    ("RESET_SERVO", 1), ("GET_SERVO_POSITION", 1), ("GET_SERVO_CW_LIM", 2),
    ("SET_SERVO_LED", [1, 1]), ("SET_SERVO_ENABLE", [1, 0]),
    ("SET_SERVO_CW_LIM", [1, 350]), ("SET_SERVO_CCW_LIM", [2, 600]), ("SET_SERVO_CW_LIM", [1, 65000]),
    ("SET_ENABLE_SPEAKER", 1), ("SET_MIC_INPUT", 2), ("NO_EXISTE", 0),
]


def tx_cases(mod):
    out = {}

    def tx(name, fn):
        port, ctrl = _controller(mod)
        res = _call(lambda: fn(ctrl))
        if isinstance(res, str) and res.startswith("EXC "):
            out["tx/" + name] = res
        else:
            out["tx/" + name] = " | ".join(hx(w) for w in port.tx)

    for color in (0, 1, 2, 4, 3, 7, 253, 254, 255):
        tx("SetNoseColor(%d)" % color, lambda c, v=color: c.SetNoseColor(v))
    for m in MOUTHS:
        tx("SetMouth(0x%08X)" % m, lambda c, v=m: c.SetMouth(v))
    for args in SERVOS:
        tx("SetServo%r" % (args,), lambda c, a=args: c.SetServo(*a))
    for axis in (1, 2):
        for angle in (511, 290, 725, 420, 550, 253, 254, 255, 100):
            tx("SetAngle(%d,%d)" % (axis, angle), lambda c, a=axis, g=angle: c.SetAngle(a, g))
        # el seguimiento de cara manda desplazamientos chicos, positivos y negativos
        for angle in range(-80, 81):
            tx("SetAngleRelative(%d,%d)" % (axis, angle),
               lambda c, a=axis, g=angle: c.SetAngleRelative(a, g))
        for angle in (400, -400, 127, -128, 253, 254, 255, 256, -3, -2, -1):
            tx("SetAngleRelative(%d,%d)" % (axis, angle),
               lambda c, a=axis, g=angle: c.SetAngleRelative(a, g))
    for args in PIDS:
        tx("SetPid%r" % (args,), lambda c, a=args: c.SetPid(*a))
    for cmd, n, data in RAW:
        tx("SendCmdQBO(0x%02X,%d,%r)" % (cmd, n, data),
           lambda c, k=cmd, i=n, d=data: c.SendCmdQBO(mod.Command(k, i, d)))
    for name, arg in HEAD_CMDS:
        # sin respuesta de la placa: GetHeadCmd reintenta 3 veces
        tx("GetHeadCmd(%s,%r)" % (name, arg), lambda c, k=name, a=arg: c.GetHeadCmd(k, a))
    return out


# --- RX: bytes crudos -> ReadResponse() y ProcessRxData() --------------------

def _escaped_checksum_frames():
    """Busca datos cuyo checksum de respuesta valga FD, FE y FF."""
    found = {}
    for cmd in (0x46, 0x5D, 0x4B):
        for a in range(256):
            for b in (0, 1, 7):
                data = [a, b] if cmd != 0x46 else [a]
                chk = serial.pearson([cmd, len(data)] + data)
                if chk >= 0xFD and chk not in found and a < 0xFD:
                    found[chk] = (cmd, data)
    return [found[k] for k in sorted(found)]


def rx_buffers():
    enc = serial.encode_frame
    bufs = []
    for v in range(0, 8):
        bufs.append(("GET_TOUCH=%d" % v, enc(0x46, [v])))
    bufs.append(("ACK sin datos", enc(0x45, [])))
    bufs.append(("GET_VERSION", enc(0x40, [7])))
    bufs.append(("GET_HEAD_SERVOS 4 bytes", enc(0x5C, [0xFF, 0x01, 0xC2, 0x01])))
    bufs.append(("GET_MIC_REPORT 6 bytes", enc(0x4B, [10, 0, 200, 3, 0, 99])))
    bufs.append(("GET_SERVO_POSITION 511", enc(0x5D, [0xFF, 0x01])))
    for v in (0xFC, 0xFD, 0xFE, 0xFF):
        bufs.append(("dato 0x%02X" % v, enc(0x46, [v])))
    bufs.append(("dos datos escapados seguidos", enc(0x5D, [0xFD, 0xFE])))
    bufs.append(("escape en el medio", enc(0x4B, [1, 0xFE, 2, 0xFD, 3, 4])))
    for cmd, data in _escaped_checksum_frames():
        chk = serial.pearson([cmd, len(data)] + data)
        bufs.append(("checksum 0x%02X escapado" % chk, enc(cmd, data)))
    nack = bytes(bytearray([0xFF, 0xFE]))
    bufs.append(("NACK", nack))
    bufs.append(("vacio (timeout)", b""))
    bufs.append(("basura antes del flag", bytes(bytearray([0x00, 0x13, 0x37])) + enc(0x46, [1])))
    bufs.append(("dos tramas seguidas", enc(0x46, [1]) + enc(0x46, [3])))
    bufs.append(("NACK y despues trama", nack + enc(0x46, [2])))
    bufs.append(("trama truncada", enc(0x46, [1])[:-2]))
    bad = bytearray(enc(0x46, [1]))
    bad[-2] ^= 0x01
    bufs.append(("checksum malo", bytes(bad)))
    bufs.append(("largo declarado no coincide", bytes(bytearray([0xFF, 0x46, 0x02, 0x01, 0x10, 0xFE]))))
    bufs.append(("flag de inicio repetido", bytes(bytearray([0xFF])) + enc(0x46, [2])))
    return bufs


def rx_cases(mod):
    out = {}
    for name, raw in rx_buffers():
        port, ctrl = _controller(mod)
        port.inject(raw)
        frame = _call(ctrl.ReadResponse)
        if isinstance(frame, str):
            out["rx/" + name] = frame
            continue
        params = _call(lambda: ctrl.ProcessRxData(frame))
        out["rx/" + name] = "%s => %r" % (hx(frame), params)
    return out


# --- ida y vuelta: GetHeadCmd con respuestas inyectadas ----------------------

def roundtrip_cases(mod):
    out = {}
    enc = serial.encode_frame
    nack = bytes(bytearray([0xFF, 0xFE]))
    scripts = [
        ("GET_TOUCH responde 1", "GET_TOUCH", 0, [enc(0x46, [1])]),
        ("GET_TOUCH responde 3", "GET_TOUCH", 0, [enc(0x46, [3])]),
        ("GET_TOUCH NACK y despues 2", "GET_TOUCH", 0, [nack, enc(0x46, [2])]),
        ("GET_TOUCH tres NACK", "GET_TOUCH", 0, [nack, nack, nack]),
        ("GET_TOUCH sin respuesta", "GET_TOUCH", 0, []),
        ("GET_HEAD_SERVOS", "GET_HEAD_SERVOS", 0, [enc(0x5C, [0xFF, 0x01, 0xC2, 0x01])]),
        ("SET_SERVO_LED ACK", "SET_SERVO_LED", [1, 1], [enc(0x51, [])]),
    ]
    for name, cmd, arg, responses in scripts:
        port, ctrl = _controller(mod)
        port.responses = list(responses)
        res = _call(lambda: ctrl.GetHeadCmd(cmd, arg))
        out["rt/" + name] = "%r <= %s" % (res, " | ".join(hx(w) for w in port.tx))
    return out


def run_all(mod):
    out = {}
    out.update(tx_cases(mod))
    out.update(rx_cases(mod))
    out.update(roundtrip_cases(mod))
    return out
