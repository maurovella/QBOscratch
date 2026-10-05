"""Cliente de Ollama (POST /api/chat) para Tooly.

El servidor original hacia cuatro cosas que aca pasan al cliente, con los
mismos valores que apiTooly.py:
  - prompt de sistema (qbo/llm/prompt.py),
  - historial: cuando llega a 8 mensajes se queda con el de sistema y los ultimos 6,
  - respuesta de 256 tokens como maximo,
  - clean_text() sobre cada respuesta.
"""
import time

import requests

from qbo.llm.base import ChatClient, LLMError, with_retries
from qbo.llm.prompt import TOOLY_ASSISTANT_TEXT
from qbo.llm.text import clean_text

MAX_GEN_TOKENS = 256        # max_gen_len del servidor original
MAX_MESSAGE_CHARS = 3072    # max_seq_len: el servidor recortaba el mensaje a ese largo
HISTORY_LIMIT = 8           # max_batch_size
HISTORY_KEEP = 6
CONVERSATION_IDLE_S = 240 * 60


class OllamaClient(ChatClient):
    DEFAULT_HOST = "http://localhost:11434"
    DEFAULT_MODEL = "qwen2.5:7b-instruct"

    def __init__(self, host=DEFAULT_HOST, model=DEFAULT_MODEL, timeout=60, retries=2,
                 system_prompt=TOOLY_ASSISTANT_TEXT):
        self.url = host.rstrip("/") + "/api/chat"
        self.model = model
        self.timeout = timeout
        self.retries = retries
        self.system = {"role": "system", "content": system_prompt}
        self.messages = [self.system]
        self.last_turn = None

    def start(self):
        self.messages = [self.system]
        self.last_turn = None
        return None

    def _request(self, messages):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            # temperatura y top_p: los defaults de chat_completion de Llama 2
            "options": {"num_predict": MAX_GEN_TOKENS, "temperature": 0.6, "top_p": 0.9},
        }
        try:
            response = requests.post(self.url, json=payload, timeout=self.timeout)
        except requests.exceptions.RequestException as exc:
            raise LLMError("%s: %s" % (type(exc).__name__, exc))
        if response.status_code != 200:
            raise LLMError("HTTP %s de %s" % (response.status_code, self.url))
        try:
            content = response.json()["message"]["content"]
        except (ValueError, KeyError, TypeError) as exc:
            raise LLMError("respuesta de Ollama sin message.content: %s" % exc)
        text = clean_text(content)
        if not text:
            raise LLMError("respuesta vacia despues de limpiarla: %r" % (content,))
        return text

    def chat(self, message):
        now = time.time()
        if self.last_turn is not None and now - self.last_turn > CONVERSATION_IDLE_S:
            # el servidor original daba la conversacion por vencida a las 4 horas
            self.messages = [self.system]
        user = {"role": "user", "content": str(message)[:MAX_MESSAGE_CHARS]}
        pending = self.messages + [user]
        text = with_retries(lambda: self._request(pending), self.retries)

        # el turno entra al historial solo si hubo respuesta
        self.messages = pending + [{"role": "assistant", "content": text}]
        if len(self.messages) >= HISTORY_LIMIT:
            self.messages = [self.system] + self.messages[-HISTORY_KEEP:]
        self.last_turn = now
        return text
