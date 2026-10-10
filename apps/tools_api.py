#!/usr/bin/env python3
"""API de herramientas del robot.

Recibe la decision ya tomada por el arnes y la ejecuta. No interpreta sensores.

    POST /tools/say    {"text": "Hola, aca estoy"}
    POST /tools/nose   {"color": "green"}
    POST /tools/mouth  {"expression": "smile"}
    POST /tools/head   {"axis": 1, "angle": 20}

Cada llamada valida responde 200 {"ok": true} y se reenvia tal cual a la
pagina por el WebSocket ws://<host>:8000/ws. La pagina (web/qbo_sim.html) se
sirve en http://<host>:8000/. El contrato y sus valores estan en qbo/tools.py.

    apps/tools_api.py                      solo la cabeza 3D, sin robot
    apps/tools_api.py --robot              ademas mueve el robot por /dev/serial0
    apps/tools_api.py --robot socket://... otro puerto (cualquier URL de pyserial)
"""
import os
import sys
# raiz del repo en sys.path, para importar el paquete qbo sin instalarlo
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import argparse
import asyncio
import json

from aiohttp import web, WSMsgType

from qbo import paths
from qbo import tools

PAGE = os.path.join(ROOT, "web", "qbo_sim.html")


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False)


class ToolsApi(object):
    def __init__(self, robot=None, log=print):
        self.robot = robot
        self.log = log
        self.pages = set()
        # ultimo mensaje de cada cosa, para que una pagina que se conecta tarde arranque igual
        self.last = {}

    async def broadcast(self, msg):
        text = dumps(msg)
        for ws in list(self.pages):
            try:
                await ws.send_str(text)
            except Exception:
                self.pages.discard(ws)

    async def tool(self, request):
        name = request.match_info["tool"]
        try:
            body = await request.json()
        except ValueError:
            return web.json_response({"ok": False, "error": "JSON invalido"}, status=400, dumps=dumps)
        try:
            msg = tools.validate(name, body)
        except tools.InvalidRequest as exc:
            self.log("[%-5s] rechazado: %s" % (name, exc))
            status = 404 if name not in tools.TOOLS else 400
            return web.json_response({"ok": False, "error": str(exc)}, status=status, dumps=dumps)

        self.log("[%-5s] %s" % (name, dumps(msg)))
        if name != "say":
            self.last[name + str(msg.get("axis", ""))] = msg
        await self.broadcast(msg)
        if self.robot is not None:
            try:
                await asyncio.get_running_loop().run_in_executor(None, self.robot.run, name, msg)
            except Exception as exc:     # el robot no debe tumbar la API ni la pagina
                self.log("[robot] error en %s: %s" % (name, exc))
        return web.json_response({"ok": True})

    async def websocket(self, request):
        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)
        self.pages.add(ws)
        self.log("[ws] pagina conectada (%d)" % len(self.pages))
        for msg in self.last.values():
            await ws.send_str(dumps(msg))
        try:
            async for m in ws:
                if m.type == WSMsgType.ERROR:
                    break
        finally:
            self.pages.discard(ws)
            self.log("[ws] pagina desconectada (%d)" % len(self.pages))
        return ws

    async def page(self, request):
        return web.FileResponse(PAGE)


@web.middleware
async def cors(request, handler):
    """La pagina puede estar en otra maquina o puerto que el arnes."""
    resp = web.Response(status=204) if request.method == "OPTIONS" else await handler(request)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


async def preflight(request):
    return web.Response(status=204)     # los encabezados CORS los agrega el middleware


def make_app(api):
    app = web.Application(middlewares=[cors])
    app.router.add_get("/", api.page)
    app.router.add_get("/ws", api.websocket)
    app.router.add_post("/tools/{tool}", api.tool)
    app.router.add_route("OPTIONS", "/tools/{tool}", preflight)
    return app


def open_robot(port):
    import serial
    from qbo import protocol
    ser = serial.serial_for_url(port, baudrate=115200, bytesize=serial.EIGHTBITS,
                                stopbits=serial.STOPBITS_ONE, parity=serial.PARITY_NONE, timeout=0)
    return tools.Robot(protocol.Controller(ser))


def main(argv=None):
    ap = argparse.ArgumentParser(description="API de herramientas del QBO")
    ap.add_argument("--host", default="0.0.0.0", help="0.0.0.0 = accesible desde otras maquinas")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--robot", nargs="?", const=paths.SERIAL_PORT, default=None,
                    help="mover tambien el robot real (por defecto %s)" % paths.SERIAL_PORT)
    args = ap.parse_args(argv)

    robot = None
    if args.robot:
        try:
            robot = open_robot(args.robot)
        except Exception as exc:
            sys.exit("No pude abrir el robot en %s: %s" % (args.robot, exc))

    print("API de herramientas del QBO")
    print("  cabeza 3D     http://localhost:%d/" % args.port)
    print("  websocket     ws://localhost:%d/ws" % args.port)
    print("  herramientas  POST http://localhost:%d/tools/{say,nose,mouth,head}" % args.port)
    print("  robot         %s" % (args.robot or "no, solo la cabeza 3D"))
    web.run_app(make_app(ToolsApi(robot)), host=args.host, port=args.port, print=None)


if __name__ == "__main__":
    main()
