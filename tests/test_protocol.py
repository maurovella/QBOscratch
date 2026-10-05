"""Golden master del protocolo UART.

tests/golden/protocol_py2.json son los bytes exactos que produce el QboCmd.py
original corriendo en Python 2.7 (ver tests/golden/generate.sh). Estos tests
exigen que la version actual produzca lo mismo, byte a byte, salvo en los
casos listados en DIVERGENCIAS, donde el original tenia un bug y la version
migrada lo corrige. Cada divergencia tiene su valor esperado derivado de
serialProtocol.c del firmware, no del codigo bajo prueba.
"""
import json
import os

import pytest

import protocol_cases
import serial  # doble de tests/fakes
from conftest import TESTS, load_protocol

with open(os.path.join(TESTS, "golden", "protocol_py2.json")) as fh:
    GOLDEN = json.load(fh)

MOD = load_protocol()
ACTUAL = protocol_cases.run_all(MOD)


def _tx_frame(cmd, data):
    """Trama que la Pi debe emitir: escape solo de datos y checksum."""
    return protocol_cases.hx(serial.encode_frame(cmd, data))


def _rx_expected(raw):
    """Lo que debe devolver ReadResponse/ProcessRxData segun el firmware."""
    cmd, data = serial.decode_frame(raw)
    frame = [0xFF, cmd, len(data)] + data + [serial.pearson([cmd, len(data)] + data), 0xFE]
    return "%s => %r" % (protocol_cases.hx(frame), data)


RX_BUFFERS = dict(protocol_cases.rx_buffers())
P = MOD.Controller.cmd_params

# caso -> (valor esperado en Python 3, por que difiere del original)
DIVERGENCIAS = {}

_ESCAPE_BUG = ("py2 descartaba el byte posterior a 0xFD y dejaba 0xFF; el firmware "
               "emite 0xFD seguido de (valor - 2), serialProtocol.c:643-650")
for _name in ("dato 0xFD", "dato 0xFE", "dos datos escapados seguidos", "escape en el medio",
              "checksum 0xFE escapado", "checksum 0xFF escapado"):
    DIVERGENCIAS["rx/" + _name] = (_rx_expected(RX_BUFFERS[_name]), _ESCAPE_BUG)

_LIST_BUG = ("py2 comparaba lista > int y despues hacia lista & 0xff: TypeError. "
             "GetHeadCmd siempre pasa el parametro unico envuelto en una lista")
for _cmd, _arg in (("RESET_SERVO", 1), ("GET_SERVO_POSITION", 1), ("GET_SERVO_CW_LIM", 2),
                   ("SET_ENABLE_SPEAKER", 1), ("SET_MIC_INPUT", 2)):
    DIVERGENCIAS["tx/GetHeadCmd(%s,%r)" % (_cmd, _arg)] = (
        " | ".join([_tx_frame(P[_cmd][0], [_arg])] * 3), _LIST_BUG)
DIVERGENCIAS["tx/SendCmdQBO(0x86,1,[1])"] = (_tx_frame(0x86, [1]), _LIST_BUG)
DIVERGENCIAS["tx/SendCmdQBO(0x45,1,-1)"] = (
    _tx_frame(0x45, [0xFF]),
    "py2 pasaba -1 a bytearray(): ValueError. Ahora se enmascara con & 0xff")


def test_mismos_casos_que_el_golden():
    assert sorted(ACTUAL) == sorted(GOLDEN)
    assert len(GOLDEN) > 400


def test_golden_generado_con_el_codigo_original():
    # si alguien regenera el golden contra el codigo nuevo, estos valores cambian
    assert GOLDEN["rx/dato 0xFD"] == "FF 46 01 FF 40 FE => 0"
    assert GOLDEN["tx/GetHeadCmd(RESET_SERVO,1)"] == "EXC TypeError"


@pytest.mark.parametrize("case", sorted(k for k in GOLDEN if k not in DIVERGENCIAS))
def test_identico_a_python2(case):
    assert ACTUAL[case] == GOLDEN[case]


@pytest.mark.parametrize("case", sorted(DIVERGENCIAS))
def test_divergencia_documentada(case):
    esperado, motivo = DIVERGENCIAS[case]
    assert GOLDEN[case] != esperado, "ya no diverge: sacar %s de DIVERGENCIAS" % case
    assert ACTUAL[case] == esperado, motivo


def test_las_unicas_diferencias_son_las_documentadas():
    distintos = {k for k in GOLDEN if ACTUAL[k] != GOLDEN[k]}
    assert distintos == set(DIVERGENCIAS)


def test_tramas_que_usa_tooly():
    # valores fijos, para que el test falle aunque golden y codigo cambien juntos
    assert ACTUAL["tx/SetNoseColor(1)"] == "FF 45 01 01 60 FE"
    assert ACTUAL["tx/SetMouth(0x00110E00)"] == "FF 44 04 00 11 0E 00 54 FE"
    assert ACTUAL["tx/SetServo(1, 511, 100)"] == "FF 53 05 01 FD FD 01 64 00 47 FE"
    assert ACTUAL["tx/SetAngleRelative(1,-40)"] == "FF 73 03 01 D8 FD FD C2 FE"
    assert ACTUAL["tx/SetPid(1, 26, 2, 16)"] == "FF 50 04 01 1A 02 10 84 FE"
    assert ACTUAL["tx/SendCmdQBO(0x86,1,1)"] == "FF 86 01 01 27 FE"
    assert ACTUAL["tx/GetHeadCmd(GET_TOUCH,0)"] == " | ".join(["FF 46 00 60 FE"] * 3)


@pytest.mark.parametrize("value", range(256))
def test_escape_ida_y_vuelta(value):
    """Cualquier byte de dato sobrevive Pi -> placa -> Pi, incluidos FD, FE y FF."""
    port = serial.Serial("/dev/fake")
    ctrl = MOD.Controller(port)
    sent = ctrl.SendCmdQBO(MOD.Command(0x45, 1, value))
    assert serial.decode_frame(sent) == (0x45, [value])

    port.inject(serial.encode_frame(0x46, [value]))
    assert ctrl.ProcessRxData(ctrl.ReadResponse()) == [value]


def test_write_recibe_bytes():
    port = serial.Serial("/dev/fake")
    MOD.Controller(port).SetNoseColor(1)
    assert all(isinstance(chunk, bytes) for chunk in port.tx)
