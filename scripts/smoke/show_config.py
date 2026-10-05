#!/usr/bin/env python3
"""config.yml y el estado del LLM, sin secretos, para el informe de relevar.sh.

    show_config.py <config.yml>               imprime las claves conocidas
    show_config.py <config.yml> --check-llm   consulta /api/tags del servidor del
                                              LLM. Sale con 0 si responde.

El informe de relevar.sh se copia fuera del robot, asi que nada de lo que
imprime este script puede llevar un secreto. Las reglas estan en qbo/redact.py:
solo se muestran valores con la forma esperada, y de las claves desconocidas
no sale ni el nombre.

La URL del LLM nunca sale de este proceso. Antes habia un modo que la imprimia
para pasarsela a curl; como puede traer usuario y clave, la consulta se hace
aca adentro y afuera solo va el resultado.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from qbo import redact  # noqa: E402

NOMBRE_SEGURO = re.compile(r"[A-Za-z0-9._:\-/]{1,60}")


def load(path):
    import yaml
    with open(path) as fh:
        config = yaml.safe_load(fh)
    if config is None:
        return {}
    if not isinstance(config, dict):
        raise ValueError("no es un mapa")
    return config


def llm_url(config):
    """La misma precedencia que qbo/llm: QBO_LLM_HOST pisa a config.yml."""
    url = os.environ.get("QBO_LLM_HOST") or config.get("llm_host") or ""
    return url if isinstance(url, str) else ""


def check_llm(config):
    url = llm_url(config)
    if not url:
        print("LLM: config.yml no tiene llm_host")
        return 1
    print("LLM: servidor %s" % redact.safe_url(url))
    try:
        # requests, como el cliente del robot: entiende usuario:clave@host
        import requests
        response = requests.get(url.rstrip("/") + "/api/tags", timeout=8)
        status = response.status_code
        body = response.json()
    except Exception as exc:
        # solo el tipo: el mensaje de requests cita la URL
        print("LLM: no responde (%s)" % type(exc).__name__)
        return 1
    if status != 200:
        print("LLM: el servidor contesta HTTP %s" % status)
        return 1
    models = body.get("models", []) if isinstance(body, dict) else []
    names = [m.get("name") for m in models if isinstance(m, dict)]
    names = [n for n in names if isinstance(n, str) and NOMBRE_SEGURO.fullmatch(n)]
    print("LLM: responde, HTTP %s, %d modelos: %s" % (status, len(models), ", ".join(names[:20]) or "ninguno"))
    return 0


def main(argv):
    path = argv[0]
    try:
        config = load(path)
    except Exception as exc:
        # solo el tipo: el mensaje de PyYAML puede citar el contenido del archivo
        print("no se pudo leer config.yml (%s). No se muestra el contenido." % type(exc).__name__)
        return 1

    if "--check-llm" in argv:
        return check_llm(config)

    for line in redact.lines(config, missing=True):
        print(line)
    env_host = os.environ.get("QBO_LLM_HOST")
    if env_host:
        print("QBO_LLM_HOST (entorno, pisa a llm_host): %s" % redact.safe_url(env_host))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
