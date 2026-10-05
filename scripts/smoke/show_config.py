#!/usr/bin/env python3
"""Muestra config.yml sin secretos, para el informe de relevar.sh.

    show_config.py <config.yml>             imprime las claves conocidas
    show_config.py <config.yml> --llm-url   imprime la URL del LLM TAL CUAL, para
                                            pasarsela a curl. Puede traer una
                                            clave: no mandar esa salida a un log.

El informe de relevar.sh se copia fuera del robot, asi que este script decide
que se puede mostrar y no al reves:

- solo se imprimen las claves de VALIDADORES, y solo si el valor tiene la forma
  esperada (un idioma conocido, un entero, http://host:puerto). Un valor con
  otra forma sale como <oculto>, sin intentar "limpiarlo": recortar una URL o un
  texto a mano es justo lo que falla cuando el secreto trae un caracter raro;
- de las demas claves no se muestra ni el nombre, solo cuantas hay. Un secreto
  mal pegado puede terminar siendo el nombre de una clave;
- si el archivo no se puede leer, se informa el tipo de error y nada mas. El
  mensaje de PyYAML puede citar texto del archivo.
"""
import os
import re
import sys

OCULTO = "<oculto: valor con forma no esperada>"

# http://host:puerto y nada mas: sin usuario, clave, ruta ni parametros
URL_SIMPLE = re.compile(r"https?://[A-Za-z0-9.\-]{1,253}(:[0-9]{1,5})?/?")
NOMBRE_DE_MODELO = re.compile(r"[A-Za-z0-9_.:\-/]{1,80}")


def una_de(*opciones):
    return lambda v: isinstance(v, str) and v in opciones


def numero(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def booleano(v):
    return isinstance(v, bool)


def url_simple(v):
    return isinstance(v, str) and URL_SIMPLE.fullmatch(v) is not None


def modelo(v):
    return isinstance(v, str) and NOMBRE_DE_MODELO.fullmatch(v) is not None


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

# claves que se sabe que guardan un secreto: se informa solo si tienen valor
SECRETAS = ("tokenAPIai", "gassistant_proyectid")


def mostrar(key, value):
    if value is None or value == "":
        return "(vacio)"
    return str(value) if VALIDADORES[key](value) else OCULTO


def load(path):
    import yaml
    with open(path) as fh:
        config = yaml.safe_load(fh)
    if config is None:
        return {}
    if not isinstance(config, dict):
        raise ValueError("no es un mapa")
    return config


def main(argv):
    path = argv[0]
    try:
        config = load(path)
    except Exception as exc:
        # solo el tipo: el mensaje puede citar el contenido del archivo
        print("no se pudo leer config.yml (%s). No se muestra el contenido." % type(exc).__name__)
        return 1

    if "--llm-url" in argv:
        # la misma precedencia que qbo/llm: QBO_LLM_HOST pisa a config.yml
        url = os.environ.get("QBO_LLM_HOST") or config.get("llm_host") or ""
        print(url if isinstance(url, str) else "")
        return 0

    for key in sorted(VALIDADORES):
        print("%s: %s" % (key, mostrar(key, config[key]) if key in config else "(falta)"))
    for key in SECRETAS:
        if key in config:
            print("%s: %s" % (key, "(vacio)" if config[key] in (None, "") else "<oculto>"))
    otras = [k for k in config if k not in VALIDADORES and k not in SECRETAS]
    if otras:
        print("otras claves: %d (nombres y valores ocultos)" % len(otras))
    env_host = os.environ.get("QBO_LLM_HOST")
    if env_host:
        print("QBO_LLM_HOST (entorno, pisa a llm_host): %s" % (env_host if url_simple(env_host) else OCULTO))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
