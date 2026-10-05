#!/usr/bin/env python3
"""Muestra config.yml sin secretos, para el informe de relevar.sh.

    show_config.py <config.yml>             imprime clave: valor
    show_config.py <config.yml> --llm-url   imprime la URL del LLM, para curl

Solo se muestran los valores de las claves de PUBLICAS. Cualquier otra clave
sale como <oculto>: una clave nueva con un secreto no llega al informe aunque
nadie se acuerde de agregarla a una lista de cosas a tapar. A llm_host se le
quita el usuario y la contrasena si los trae (http://usuario:clave@host).
"""
import os
import re
import sys

PUBLICAS = {"age", "language", "volume", "startWith", "op_question", "llm_backend", "llm_host",
            "llm_model", "llm_timeout_s", "llm_retries", "camera_index"}


def sin_credenciales(url):
    return re.sub(r"(://)[^/@\s]*@", r"\1<oculto>@", str(url))


def main(argv):
    path = argv[0]
    try:
        import yaml
        with open(path) as fh:
            config = yaml.safe_load(fh) or {}
        if not isinstance(config, dict):
            raise ValueError("config.yml no es un mapa clave: valor")
    except Exception as exc:
        # sin PyYAML o con el archivo roto no se puede separar clave de valor
        print("no se pudo leer %s (%s: %s). No se muestra el contenido." % (
            os.path.basename(path), type(exc).__name__, str(exc).splitlines()[0][:80] if str(exc) else ""))
        return 1

    if "--llm-url" in argv:
        # la misma precedencia que qbo/llm: QBO_LLM_HOST pisa a config.yml
        print(os.environ.get("QBO_LLM_HOST") or config.get("llm_host") or "")
        return 0

    for key in sorted(config, key=str):
        value = config[key]
        if key not in PUBLICAS:
            shown = "<oculto>" if value not in (None, "") else "(vacio)"
        elif key == "llm_host":
            shown = sin_credenciales(value)
        else:
            shown = value
        print("%s: %s" % (key, shown))
    if os.environ.get("QBO_LLM_HOST"):
        print("QBO_LLM_HOST (entorno, pisa a llm_host): " + sin_credenciales(os.environ["QBO_LLM_HOST"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
