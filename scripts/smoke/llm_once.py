#!/usr/bin/env python3
"""Le manda un mensaje al LLM configurado en config.yml y muestra la respuesta.

    llm_once.py [mensaje]

Sale con 0 si hubo respuesta. Aisla la red y el servidor del LLM del resto.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import yaml  # noqa: E402

from qbo import llm, paths  # noqa: E402


def main(argv):
    message = " ".join(argv) or "Hello"
    with open(paths.CONFIG) as fh:
        config = yaml.safe_load(fh)
    print("backend: %s" % config.get("llm_backend", "tooly_legacy (default)"))
    try:
        client = llm.from_config(config)
        print("servidor: %s" % getattr(client, "url", getattr(client, "host", "?")))
        client.start()
        started = time.time()
        answer = client.chat(message)
    except llm.LLMError as exc:
        print("FALLA: el LLM no respondio: %s" % exc)
        return 1
    print("respuesta en %.1f s: %s" % (time.time() - started, answer))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
