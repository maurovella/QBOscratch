"""API de herramientas (apps/tools_api.py, qbo/tools.py).

- El contrato: que acepta y que rechaza cada herramienta.
- Con robot: los bytes por la UART son los mismos que mandaba PiCmd.py en
  Python 2.7 (golden master tests/golden/apps_py2.json).
- La API: cada POST valido responde 200 {"ok": true} y llega igual a la pagina
  por el WebSocket.
"""
import asyncio
import json
import os

import pytest

import fakelog              # tests/fakes
import serial               # doble de tests/fakes
from conftest import ROOT, load_protocol, load_module

tools = load_module("qbo_tools_under_test", os.path.join(ROOT, "qbo", "tools.py"))

GOLDEN = json.load(open(os.path.join(ROOT, "tests", "golden", "apps_py2.json")))


def golden_tx(case):
    return [e["hex"] for e in GOLDEN["PiCmd args: " + case]["events"] if e.get("k") == "serial_tx"]


# --- contrato ------------------------------------------------------------------

@pytest.mark.parametrize("tool,body,expected", [
    ("say", {"text": "Hola, acá estoy"}, {"text": "Hola, acá estoy"}),
    ("say", {"text": "  hola  "}, {"text": "hola"}),
    ("nose", {"color": "green"}, {"color": "green"}),
    ("mouth", {"expression": "love"}, {"expression": "love"}),
    ("head", {"axis": 1, "angle": 20}, {"axis": 1, "angle": 20}),
    ("head", {"axis": 2, "angle": -12.5}, {"axis": 2, "angle": -12.5}),
    ("head", {"axis": 2, "angle": 300}, {"axis": 2, "angle": 40}),        # se recorta
    ("nose", {"color": "red", "extra": 1}, {"color": "red"}),             # solo campos del contrato
])
def test_validos(tool, body, expected):
    assert tools.validate(tool, body) == expected


@pytest.mark.parametrize("tool,body", [
    ("nose", {"color": "pink"}), ("nose", {}), ("mouth", {"expression": "wink"}),
    ("head", {"axis": 3, "angle": 10}), ("head", {"axis": True, "angle": 10}),
    ("head", {"axis": 1, "angle": "20"}), ("say", {"text": ""}), ("say", {"text": 5}),
    ("volar", {}), ("nose", ["red"]),
])
def test_invalidos(tool, body):
    with pytest.raises(tools.InvalidRequest):
        tools.validate(tool, body)


# --- robot: mismos bytes que PiCmd.py original ----------------------------------

def robot():
    ser = serial.Serial("/dev/serial0", baudrate=115200)
    said = []
    return tools.Robot(load_protocol().Controller(ser), speak=said.append), ser, said


@pytest.mark.parametrize("color", ["none", "red", "blue", "green"])
def test_nariz_igual_que_picmd(color):
    r, ser, _ = robot()
    r.run("nose", {"color": color})
    assert [fakelog.hexstr(b) for b in ser.tx] == golden_tx("-c nose -co " + color)


@pytest.mark.parametrize("expression", ["smile", "sad", "serious", "love"])
def test_boca_igual_que_picmd(expression):
    r, ser, _ = robot()
    r.run("mouth", {"expression": expression})
    assert [fakelog.hexstr(b) for b in ser.tx] == golden_tx("-c mouth -e " + expression)


def test_cabeza_usa_la_formula_de_scratch():
    # robot_control.js: 'right' 20 grados -> parseInt(20 / 0.29 + 511) = 579
    r, ser, _ = robot()
    r.run("head", {"axis": 1, "angle": 20})
    expected = load_protocol().Controller(serial.Serial("x")).SetServo(1, 579, tools.SERVO_SPEED)
    assert ser.tx == [bytes(expected)]
    assert tools.servo_position(2, 0) == 550


def test_say_no_toca_la_uart():
    r, ser, said = robot()
    r.run("say", {"text": "hola"})
    for _ in range(50):
        if said:
            break
        asyncio.run(asyncio.sleep(0.01))
    assert said == ["hola"] and ser.tx == []


# --- API HTTP + WebSocket -------------------------------------------------------

aiohttp = pytest.importorskip("aiohttp")
from aiohttp.test_utils import TestClient, TestServer  # noqa: E402

api_mod = load_module("tools_api_under_test", os.path.join(ROOT, "apps", "tools_api.py"))


def run_client(scenario, robot=None):
    async def main():
        api = api_mod.ToolsApi(robot=robot, log=lambda *a: None)
        async with TestClient(TestServer(api_mod.make_app(api))) as client:
            return await scenario(client)
    return asyncio.run(main())


def test_post_responde_ok_y_llega_igual_por_el_websocket():
    async def scenario(client):
        ws = await client.ws_connect("/ws")
        got = []
        for tool, body in [("say", {"text": "Hola, acá estoy"}), ("nose", {"color": "green"}),
                           ("mouth", {"expression": "smile"}), ("head", {"axis": 1, "angle": 20})]:
            resp = await client.post("/tools/" + tool, json=body)
            assert resp.status == 200 and await resp.json() == {"ok": True}
            got.append(json.loads((await ws.receive(timeout=2)).data))
        await ws.close()
        return got
    assert run_client(scenario) == [{"text": "Hola, acá estoy"}, {"color": "green"},
                                    {"expression": "smile"}, {"axis": 1, "angle": 20}]


def test_errores():
    async def scenario(client):
        out = []
        for path, data in [("/tools/nose", json.dumps({"color": "pink"})), ("/tools/volar", "{}"),
                           ("/tools/nose", "no es json")]:
            resp = await client.post(path, data=data, headers={"Content-Type": "application/json"})
            out.append((resp.status, (await resp.json())["ok"]))
        return out
    assert run_client(scenario) == [(400, False), (404, False), (400, False)]


def test_pagina_que_llega_tarde_recibe_el_estado():
    async def scenario(client):
        await client.post("/tools/nose", json={"color": "red"})
        await client.post("/tools/head", json={"axis": 2, "angle": 10})
        await client.post("/tools/say", json={"text": "esto no se repite"})
        ws = await client.ws_connect("/ws")
        got = [json.loads((await ws.receive(timeout=2)).data) for _ in range(2)]
        await ws.close()
        return got
    assert run_client(scenario) == [{"color": "red"}, {"axis": 2, "angle": 10}]


def test_con_robot_mueve_la_uart():
    r, ser, _ = robot()

    async def scenario(client):
        resp = await client.post("/tools/nose", json={"color": "blue"})
        return resp.status
    assert run_client(scenario, robot=r) == 200
    assert [fakelog.hexstr(b) for b in ser.tx] == golden_tx("-c nose -co blue")


def test_sirve_la_pagina():
    async def scenario(client):
        resp = await client.get("/")
        return resp.status, "ws://" in await resp.text()
    assert run_client(scenario) == (200, True)
