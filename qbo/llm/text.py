"""Limpieza de la respuesta del LLM antes de mandarla al parlante.

Es clean_text() de apiTooly.py, el servidor original, copiada tal cual. El
servidor la aplicaba a cada respuesta; con Ollama no hay servidor propio, asi
que la aplica el cliente. Saca lo que un TTS leeria mal: acotaciones entre
asteriscos, corchetes o llaves, comillas dobles y emojis.
"""
import re

_EMOJI = re.compile("["
                    u"\U0001F600-\U0001F64F"  # emoticons
                    u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                    u"\U0001F680-\U0001F6FF"  # transport & map symbols
                    u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                    u"\U00002702-\U000027B0"
                    u"\U000024C2-\U0001F251"
                    "]+", flags=re.UNICODE)


def clean_text(text):
    # Remove text enclosed in asterisks
    text = re.sub(r'\*[^*]*\*', '', text)
    # Remove text enclosed in square brackets
    text = re.sub(r'\[.*?\]', '', text)
    # Remove text enclosed in curly braces
    text = re.sub(r'\{.*?\}', '', text)
    # Remove double quotes
    text = re.sub(r'"', '', text)
    text = _EMOJI.sub(r'', text)
    return text.strip()
