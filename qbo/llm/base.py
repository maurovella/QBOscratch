"""Interfaz comun de los clientes del LLM y lectura de config.yml."""
import os
import time

# Lo que dice el robot si el LLM no contesta en medio de una charla. Al arrancar
# sin LLM, TrackAndTalk ya decia la misma frase con un "Hello !" adelante.
FALLBACK_TEXT = "My mind is not ready, I will repeat whatever you say."

DEFAULT_BACKEND = "tooly_legacy"
DEFAULT_TIMEOUT_S = 60


class LLMError(Exception):
    """El LLM no dio una respuesta usable (red, timeout, HTTP o formato)."""


class ChatClient(object):
    """Un cliente mantiene una conversacion. Uso: start() una vez, chat() por turno."""

    def start(self):
        """Abre la conversacion. Devuelve un identificador o None."""
        return None

    def chat(self, message):
        """Manda lo que dijo la persona y devuelve el texto que dice el robot."""
        raise NotImplementedError


RETRY_WAIT_S = 1.0      # espera antes del primer reintento; crece 1 s, 2 s, 3 s...


def with_retries(call, retries):
    """Ejecuta call(); ante LLMError reintenta `retries` veces mas."""
    attempt = 0
    while True:
        try:
            return call()
        except LLMError as exc:
            if attempt >= retries:
                raise
            attempt += 1
            print("LLM: intento %d fallo (%s), reintento" % (attempt, exc))
            time.sleep(RETRY_WAIT_S * attempt)


def from_config(config):
    """Arma el cliente segun config.yml.

    llm_backend    "tooly_legacy" (default, el servidor FastAPI original) u "ollama"
    llm_host       URL base del servidor
    llm_model      modelo de Ollama
    llm_timeout_s  segundos de espera por pedido (default 60)
    llm_retries    reintentos por pedido (default 0 en tooly_legacy, 2 en ollama)

    Sin ninguna clave nueva, un config.yml viejo se comporta como antes. La
    variable de entorno QBO_LLM_HOST pisa a llm_host.
    """
    backend = config.get("llm_backend", DEFAULT_BACKEND)
    timeout = config.get("llm_timeout_s", DEFAULT_TIMEOUT_S)
    host = os.environ.get("QBO_LLM_HOST") or config.get("llm_host")
    if backend == "ollama":
        from qbo.llm.ollama import OllamaClient
        return OllamaClient(host=host or OllamaClient.DEFAULT_HOST,
                            model=config.get("llm_model", OllamaClient.DEFAULT_MODEL),
                            timeout=timeout, retries=config.get("llm_retries", 2))
    if backend == "tooly_legacy":
        from qbo.llm.tooly_legacy import ToolyLegacyClient
        return ToolyLegacyClient(host=host or ToolyLegacyClient.DEFAULT_HOST,
                                 timeout=timeout, retries=config.get("llm_retries", 0))
    raise LLMError("llm_backend desconocido en config.yml: %r" % (backend,))
