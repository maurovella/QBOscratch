# -*- coding: utf-8 -*-
"""Cliente LLM: Ollama y el servidor original de Tooly.

Usa el paquete requests real contra un servidor HTTP local. No hace falta
ningun LLM: el servidor contesta lo que diga el guion de cada test.
"""
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from conftest import ROOT

sys.path.insert(0, ROOT)

from qbo import llm  # noqa: E402
from qbo.llm import base  # noqa: E402
from qbo.llm.ollama import OllamaClient  # noqa: E402
from qbo.llm.prompt import TOOLY_ASSISTANT_TEXT  # noqa: E402
from qbo.llm.text import clean_text  # noqa: E402
from qbo.llm.tooly_legacy import ToolyLegacyClient  # noqa: E402


class FakeServer(object):
    """Servidor HTTP con guion: una respuesta por pedido."""

    def __init__(self):
        self.script = []
        self.requests = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                outer.requests.append((self.path, body))
                step = outer.script.pop(0) if outer.script else {"status": 500, "body": "sin guion"}
                time.sleep(step.get("delay", 0))
                raw = step["body"] if isinstance(step.get("body"), str) else json.dumps(step.get("body"))
                data = raw.encode("utf-8")
                try:
                    self.send_response(step.get("status", 200))
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass    # el cliente se fue por timeout

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:" + str(self.httpd.server_address[1])
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def says(text):
    return {"status": 200, "body": {"model": "m", "message": {"role": "assistant", "content": text}, "done": True}}


@pytest.fixture
def server():
    srv = FakeServer()
    yield srv
    srv.close()


@pytest.fixture(autouse=True)
def sin_esperas(monkeypatch):
    """Los reintentos esperan 1 s, 2 s...; en los tests no."""
    monkeypatch.setattr(base, "RETRY_WAIT_S", 0)


def ollama(server, **kw):
    kw.setdefault("timeout", 5)
    return OllamaClient(host=server.url, model="qwen2.5:7b-instruct", **kw)


# --- Ollama -------------------------------------------------------------------

def test_pedido_a_api_chat(server):
    server.script = [says("Hi, I am Tooly")]
    client = ollama(server)
    client.start()
    assert client.chat("Hello") == "Hi, I am Tooly"

    path, body = server.requests[0]
    assert path == "/api/chat"
    assert body["model"] == "qwen2.5:7b-instruct"
    assert body["stream"] is False
    assert body["options"]["num_predict"] == 256
    assert body["messages"] == [{"role": "system", "content": TOOLY_ASSISTANT_TEXT},
                                {"role": "user", "content": "Hello"}]


def test_prompt_de_sistema_es_el_del_servidor_original():
    assert TOOLY_ASSISTANT_TEXT.startswith("You are a helpful robot assistant for old people, your name is tooly")
    assert TOOLY_ASSISTANT_TEXT.endswith("your nose change color to green when they pet you")
    assert len(TOOLY_ASSISTANT_TEXT) == 505


def test_el_historial_viaja_en_cada_pedido(server):
    server.script = [says("uno"), says("dos")]
    client = ollama(server)
    client.chat("a")
    client.chat("b")
    roles = [(m["role"], m["content"]) for m in server.requests[1][1]["messages"][1:]]
    assert roles == [("user", "a"), ("assistant", "uno"), ("user", "b")]


def test_recorte_del_historial_como_apiTooly(server):
    """Al llegar a 8 mensajes queda el de sistema y los ultimos 6."""
    server.script = [says("r" + str(i)) for i in range(1, 7)]
    client = ollama(server)
    for i in range(1, 7):
        client.chat("u" + str(i))
    enviados = [[m["content"] for m in body["messages"][1:]] for _path, body in server.requests]
    assert enviados[3] == ["u1", "r1", "u2", "r2", "u3", "r3", "u4"]       # 4to turno: todavia entero
    assert enviados[4] == ["u2", "r2", "u3", "r3", "u4", "r4", "u5"]       # 5to: se fue el primer turno
    assert enviados[5] == ["u3", "r3", "u4", "r4", "u5", "r5", "u6"]
    assert all(body["messages"][0]["role"] == "system" for _p, body in server.requests)


def test_limpia_la_respuesta_antes_de_hablar(server):
    server.script = [says('*smiles* Hi "friend" \U0001F600 [waves]')]
    assert ollama(server).chat("hola") == "Hi friend"


def test_mensaje_largo_se_recorta_a_3072(server):
    server.script = [says("ok")]
    ollama(server).chat("x" * 5000)
    assert len(server.requests[0][1]["messages"][1]["content"]) == 3072


def test_timeout_reintenta_y_despues_falla(server):
    server.script = [dict(says("tarde"), delay=0.6)] * 3
    client = ollama(server, timeout=0.15, retries=2)
    with pytest.raises(llm.LLMError):
        client.chat("hola")
    assert len(server.requests) == 3


def test_reintento_que_sale_bien(server):
    server.script = [{"status": 500, "body": "boom"}, says("ahora si")]
    assert ollama(server, retries=2).chat("hola") == "ahora si"
    assert len(server.requests) == 2


@pytest.mark.parametrize("step", [
    {"status": 500, "body": {"error": "model not found"}},
    {"status": 200, "body": "esto no es json"},
    {"status": 200, "body": {"done": True}},
    {"status": 200, "body": {"message": {"role": "assistant"}}},
    {"status": 200, "body": {"message": {"role": "assistant", "content": "*shrugs*"}}},
    {"status": 200, "body": {"message": {"role": "assistant", "content": ""}}},
])
def test_respuestas_inservibles_dan_LLMError(server, step):
    server.script = [step]
    with pytest.raises(llm.LLMError):
        ollama(server, retries=0).chat("hola")


def test_servidor_apagado_da_LLMError():
    client = OllamaClient(host="http://127.0.0.1:9", timeout=1, retries=1)
    with pytest.raises(llm.LLMError):
        client.chat("hola")


def test_un_turno_fallido_no_entra_al_historial(server):
    server.script = [{"status": 500, "body": "x"}, says("bien")]
    client = ollama(server, retries=0)
    with pytest.raises(llm.LLMError):
        client.chat("perdido")
    client.chat("segundo")
    assert [m["content"] for m in server.requests[1][1]["messages"][1:]] == ["segundo"]


def test_cuatro_horas_sin_hablar_empiezan_conversacion_nueva(server, monkeypatch):
    from qbo.llm import ollama as mod
    reloj = {"t": 1000.0}
    monkeypatch.setattr(mod.time, "time", lambda: reloj["t"])
    server.script = [says("uno"), says("dos"), says("tres")]
    client = ollama(server)
    client.chat("a")
    reloj["t"] += 239 * 60
    client.chat("b")
    assert len(server.requests[1][1]["messages"]) == 4
    reloj["t"] += 241 * 60
    client.chat("c")
    assert [m["content"] for m in server.requests[2][1]["messages"][1:]] == ["c"]


# --- clean_text: mismo resultado que el servidor original ------------------------

# (entrada, salida de clean_text() de apiTooly.py ejecutada sobre el snapshot)
CLEAN_SERVIDOR = [
    ('Hello! How are you today?', 'Hello! How are you today?'),
    ('*smiles* Hello there *waves*', 'Hello there'),
    ('Sure [laughs] I can help {beep}', 'Sure  I can help'),
    ('She said "carpe diem" to me', 'She said carpe diem to me'),
    ("It's a nice day, isn't it?", "It's a nice day, isn't it?"),
    ('Hi \U0001f600 friend \U0001f916\U0001f389 ok', 'Hi  friend \U0001f916 ok'),
    ('  spaces around  ', 'spaces around'),
    ('a * b * c', 'a  c'),
    ('*unclosed and [also unclosed', '*unclosed and [also unclosed'),
    ('[one] middle [two] end', 'middle  end'),
    ('{"respuesta": "hola", "accion": "nada"}', ''),
    ('\xa1Hola! \xbfC\xf3mo est\xe1s? Ma\xf1ana ser\xe1 otro d\xeda', '\xa1Hola! \xbfC\xf3mo est\xe1s? Ma\xf1ana ser\xe1 otro d\xeda'),
    ('line one\nline *two* three', 'line one\nline  three'),
    ('price is $5 `echo boo` $(ls)', 'price is $5 `echo boo` $(ls)'),
    ('', ''),
    ('\u24c2 \u2702 \u2708 texto', 'texto'),
    ('nested [a [b] c] d', 'nested  c] d'),
    ('**bold** and *italic*', 'bold and'),
]


@pytest.mark.parametrize("entrada,esperado", CLEAN_SERVIDOR)
def test_clean_text_igual_al_servidor(entrada, esperado):
    assert clean_text(entrada) == esperado


# --- servidor original -----------------------------------------------------------

def test_legacy_mismos_pedidos_que_trackandtalk(server):
    server.script = [{"status": 200, "body": {"conversation_id": "abc"}},
                     {"status": 200, "body": {"conversation_id": "abc", "response": "Hi"}}]
    client = ToolyLegacyClient(host=server.url, timeout=5)
    assert client.start() == "abc"
    assert client.chat("Hello") == "Hi"
    assert server.requests == [
        ("/tooly_hello/", {"ckpt_dir": "llama-2-7b-chat", "tokenizer_path": "tokenizer.model"}),
        ("/tooly/", {"conversation_id": "abc", "message": {"content": "Hello"}}),
    ]


def test_legacy_hello_con_503_sigue_sin_conversacion(server):
    server.script = [{"status": 503, "body": "Service Unavailable"}, {"status": 404, "body": {"detail": "x"}}]
    client = ToolyLegacyClient(host=server.url, timeout=5)
    assert client.start() is None
    with pytest.raises(llm.LLMError):
        client.chat("Hello")
    assert server.requests[1][1]["conversation_id"] is None


# --- config.yml --------------------------------------------------------------------

def test_config_vieja_usa_el_servidor_original(monkeypatch):
    monkeypatch.delenv("QBO_LLM_HOST", raising=False)
    client = llm.from_config({"language": "english", "volume": 100})
    assert isinstance(client, ToolyLegacyClient)
    assert client.host == "http://pf-2023a-tooly.it.itba.edu.ar"
    assert client.retries == 0


def test_config_ollama(monkeypatch):
    monkeypatch.delenv("QBO_LLM_HOST", raising=False)
    client = llm.from_config({"llm_backend": "ollama", "llm_host": "http://10.0.0.5:11434/",
                              "llm_model": "llama3.1", "llm_timeout_s": 12, "llm_retries": 4})
    assert isinstance(client, OllamaClient)
    assert (client.url, client.model, client.timeout, client.retries) == (
        "http://10.0.0.5:11434/api/chat", "llama3.1", 12, 4)


def test_config_ollama_defaults(monkeypatch):
    monkeypatch.delenv("QBO_LLM_HOST", raising=False)
    client = llm.from_config({"llm_backend": "ollama"})
    assert (client.url, client.model, client.timeout, client.retries) == (
        "http://localhost:11434/api/chat", "qwen2.5:7b-instruct", 60, 2)


def test_QBO_LLM_HOST_pisa_a_config(monkeypatch):
    monkeypatch.setenv("QBO_LLM_HOST", "http://otro:11434")
    client = llm.from_config({"llm_backend": "ollama", "llm_host": "http://10.0.0.5:11434"})
    assert client.url == "http://otro:11434/api/chat"


def test_backend_desconocido():
    with pytest.raises(llm.LLMError):
        llm.from_config({"llm_backend": "chatgpt"})
