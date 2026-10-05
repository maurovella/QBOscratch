"""Cliente del servidor original de Tooly (apiTooly.py: FastAPI + Llama 2).

Mismo protocolo que usaba TrackAndTalk.py:
  POST /tooly_hello/  -> {"conversation_id": ...}
  POST /tooly/        {"conversation_id", "message": {"content"}} -> {"response": ...}
El servidor guarda el historial, aplica el prompt de sistema y limpia la respuesta.

Se conserva para poder comparar con el comportamiento anterior. El host
historico respondia 503 en octubre de 2026.
"""
import requests

from qbo.llm.base import ChatClient, LLMError, with_retries


class ToolyLegacyClient(ChatClient):
    DEFAULT_HOST = "http://pf-2023a-tooly.it.itba.edu.ar"

    def __init__(self, host=DEFAULT_HOST, timeout=60, retries=0):
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.conversation_id = None

    def _post(self, path, payload):
        try:
            return requests.post(self.host + path, json=payload, timeout=self.timeout)
        except requests.exceptions.RequestException as exc:
            raise LLMError("%s: %s" % (type(exc).__name__, exc))

    def start(self):
        data_requests = {
            "ckpt_dir": "llama-2-7b-chat",
            "tokenizer_path": "tokenizer.model"
        }
        response = with_retries(lambda: self._post("/tooly_hello/", data_requests), self.retries)
        print(response.text)
        if response.status_code == 200:
            try:
                self.conversation_id = response.json()["conversation_id"]
            except (ValueError, KeyError, TypeError) as exc:
                raise LLMError("respuesta de /tooly_hello/ sin conversation_id: %s" % exc)
        else:
            # igual que el original: avisa y sigue con conversation_id None
            print(response)
        return self.conversation_id

    def chat(self, message):
        data_requests = {
            "conversation_id": self.conversation_id,
            "message": {
                "content": message
            }
        }

        def call():
            response = self._post("/tooly/", data_requests)
            try:
                return response.json()["response"]
            except (ValueError, KeyError, TypeError) as exc:
                raise LLMError("HTTP %s sin campo response: %s" % (response.status_code, exc))

        return with_retries(call, self.retries)
