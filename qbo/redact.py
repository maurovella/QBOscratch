"""Que se puede mostrar de la configuracion en pantalla, logs e informes.

Los scripts originales imprimian config.yml entero en cada arranque y en cada
frase. Eso termina en interactiveMode.log, en el journal de systemd y en los
registros del smoke test, que se copian fuera del robot.

La regla es al reves de "tapar lo secreto": solo se muestra lo que tiene la
forma esperada. Cada clave publica tiene un validador; si el valor no pasa,
sale <oculto> entero, sin intentar recortarlo. De las claves que no estan en
la lista no se muestra ni el nombre: un secreto mal pegado puede terminar
siendo el nombre de una clave.
"""
import re

OCULTO = "<oculto>"

# http://host:puerto y nada mas: sin usuario, clave, ruta ni parametros
URL_SIMPLE = re.compile(r"https?://[A-Za-z0-9.\-]{1,253}(:[0-9]{1,5})?/?")

# Nombre de modelo de Ollama: familia conocida, tamano y etiqueta. La lista de
# familias evita que un token cualquiera pase por nombre de modelo.
MODELO = re.compile(
    r"(qwen|llama|mistral|mixtral|gemma|phi|deepseek|tinyllama|codellama|neural-chat|orca|vicuna|"
    r"zephyr|nous-hermes|dolphin|starling|solar|yi|command-r|granite|smollm)"
    r"[a-z0-9.\-]{0,24}(:[a-z0-9.\-]{1,32})?")


def una_de(*opciones):
    return lambda v: isinstance(v, str) and v in opciones


def numero(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def booleano(v):
    return isinstance(v, bool)


def url_simple(v):
    return isinstance(v, str) and URL_SIMPLE.fullmatch(v) is not None


def modelo(v):
    return isinstance(v, str) and MODELO.fullmatch(v) is not None


VALIDADORES = {
    "age": numero,
    "language": una_de("english", "spanish"),
    "volume": numero,
    "startWith": una_de("scratch", "interactive-dialogflow", "interactive-gassistant", "tooly"),
    "op_question": booleano,
    "llm_backend": una_de("ollama", "tooly_legacy"),
    "llm_host": url_simple,
    "llm_model": modelo,
    "llm_timeout_s": numero,
    "llm_retries": numero,
    "camera_index": numero,
}

# claves que se sabe que guardan un secreto: solo se dice si tienen valor
SECRETAS = ("tokenAPIai", "gassistant_proyectid")


def safe_url(url):
    """La URL si es solo http://host:puerto; si trae algo mas, <oculto>."""
    return url if url_simple(url) else OCULTO


def value(key, raw):
    if raw is None or raw == "":
        return "(vacio)"
    return str(raw) if VALIDADORES[key](raw) else OCULTO


def lines(config, missing=False):
    """Una linea 'clave: valor' por clave conocida. Con missing=True tambien
    lista las claves conocidas que faltan."""
    if not isinstance(config, dict):
        return ["config.yml no es un mapa clave: valor"]
    out = []
    for key in sorted(VALIDADORES):
        if key in config:
            out.append("%s: %s" % (key, value(key, config[key])))
        elif missing:
            out.append("%s: (falta)" % key)
    for key in SECRETAS:
        if key in config:
            out.append("%s: %s" % (key, "(vacio)" if config[key] in (None, "") else OCULTO))
    otras = [k for k in config if k not in VALIDADORES and k not in SECRETAS]
    if otras:
        out.append("otras claves: %d (nombres y valores ocultos)" % len(otras))
    return out


def summary(config):
    """La configuracion en una linea, para los print de los scripts."""
    return "{" + ", ".join(lines(config)) + "}"
