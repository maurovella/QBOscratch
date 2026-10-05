"""LLM de Tooly detras de una interfaz chica: chat(mensaje) -> texto.

    cliente = llm.from_config(config)   # elige backend segun config.yml
    cliente.start()
    texto = cliente.chat("hola")        # LLMError si no hay respuesta
"""
from qbo.llm.base import FALLBACK_TEXT, ChatClient, LLMError, from_config

__all__ = ["FALLBACK_TEXT", "ChatClient", "LLMError", "from_config"]
