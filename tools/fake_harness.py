#!/usr/bin/env python3
"""Arnes de prueba: reemplaza al arnes real mientras no este, para probar la cadena.

    botones de tacto de la pagina --POST--> este arnes (:8001)
    este arnes decide --POST /tools/...--> apps/tools_api.py (:8000) --> cabeza 3D

    tools/fake_harness.py            escucha el tacto en :8001 y reacciona
    tools/fake_harness.py --demo     ademas corre una secuencia al arrancar

Input de tacto, PROVISORIO hasta que el arnes real publique el suyo:
    POST http://<host>:8001/sensors/touch   {"zone": "left" | "up" | "right"}

Solo usa la biblioteca estandar.
"""

import argparse
import http.server
import json
import threading
import time
import urllib.error
import urllib.request

API = "http://127.0.0.1:8000"


def tool(name, body):
    """Llama a una herramienta de la API, tal como lo haría el arnés real."""
    req = urllib.request.Request(f"{API}/tools/{name}", data=json.dumps(body).encode("utf-8"),
                                 method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            resp, code = r.read().decode(), r.status
    except urllib.error.HTTPError as e:
        resp, code = e.read().decode(), e.code
    except urllib.error.URLError as e:
        resp, code = str(e.reason), "sin conexión"
    print(f"   POST /tools/{name:<5} {json.dumps(body, ensure_ascii=False):<34} -> {code} {resp}")


# --- el "cerebro": qué hacer ante cada toque ---------------------------------

def reaccionar(zone):
    if zone == "left":
        tool("head", {"axis": 1, "angle": -40})
        tool("nose", {"color": "blue"})
        tool("say", {"text": "¿Quién me toca a la izquierda?"})
    elif zone == "right":
        tool("head", {"axis": 1, "angle": 40})
        tool("nose", {"color": "green"})
        tool("say", {"text": "¡Hola, lado derecho!"})
    elif zone == "up":
        tool("mouth", {"expression": "love"})
        tool("nose", {"color": "red"})
        tool("head", {"axis": 2, "angle": 15})
        tool("say", {"text": "¡Qué lindo, gracias!"})
        time.sleep(2.5)
        tool("mouth", {"expression": "smile"})
        tool("head", {"axis": 2, "angle": 0})
    time.sleep(2)
    tool("head", {"axis": 1, "angle": 0})


def demo():
    pasos = [
        ("micrófono", "escuché 'hola qbo'", [("mouth", {"expression": "smile"}), ("nose", {"color": "green"}),
                                             ("say", {"text": "Hola, acá estoy"})]),
        ("cámara", "veo una cara a la derecha", [("head", {"axis": 1, "angle": 35}), ("head", {"axis": 2, "angle": 10})]),
        ("cámara", "la cara se fue", [("head", {"axis": 1, "angle": 0}), ("head", {"axis": 2, "angle": -10}),
                                      ("mouth", {"expression": "sad"}), ("nose", {"color": "blue"})]),
        ("micrófono", "escuché 'portate bien'", [("mouth", {"expression": "serious"}), ("nose", {"color": "red"}),
                                                 ("say", {"text": "Entendido"})]),
        ("arnés", "vuelvo al estado inicial", [("head", {"axis": 2, "angle": 0}), ("mouth", {"expression": "smile"}),
                                               ("nose", {"color": "none"})]),
    ]
    for sensor, que, llamadas in pasos:
        print(f"\n[{sensor}] {que}")
        for name, body in llamadas:
            tool(name, body)
        time.sleep(2.5)


# --- input de sensores --------------------------------------------------------

class Input(http.server.BaseHTTPRequestHandler):
    def cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def responder(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.cors()
        self.end_headers()

    def do_POST(self):
        if self.path != "/sensors/touch":
            return self.responder(404, {"ok": False, "error": "ruta desconocida"})
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            zone = data.get("zone")
        except (ValueError, AttributeError):
            return self.responder(400, {"ok": False, "error": "JSON inválido"})
        if zone not in ("left", "up", "right"):
            return self.responder(400, {"ok": False, "error": "zone tiene que ser left, up o right"})
        print(f"\n[tacto] {zone}")
        threading.Thread(target=reaccionar, args=(zone,), daemon=True).start()
        self.responder(200, {"ok": True})

    def log_message(self, *args):
        pass


def main():
    global API
    ap = argparse.ArgumentParser(description="Arnes de prueba del QBO")
    ap.add_argument("--api", default=API, help="dirección de la API de herramientas")
    ap.add_argument("--port", type=int, default=8001, help="puerto donde escucha el tacto")
    ap.add_argument("--demo", action="store_true", help="correr una secuencia de prueba al arrancar")
    a = ap.parse_args()
    API = a.api.rstrip("/")

    srv = http.server.ThreadingHTTPServer(("0.0.0.0", a.port), Input)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"Arnes de prueba escuchando el tacto en http://localhost:{a.port}/sensors/touch")
    print(f"Llama a la API de herramientas en {API}")
    if a.demo:
        demo()
    print("\nEsperando toques de la página (Ctrl+C para salir)...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nchau")


if __name__ == "__main__":
    main()
