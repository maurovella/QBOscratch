"""Ejecutable falso (pico2wave, aplay, QBO_listen...): registra con que
argumentos lo llamaron. Asi se comprueba que le llega al TTS despues de que
la shell interpreto el comando. Compatible con Python 2.7 y 3.
"""
import json
import os
import sys


def text(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value


def main():
    name = sys.argv[1]
    args = [text(a) for a in sys.argv[2:]]
    event = {"k": "exec", "argv": [name] + args}
    with open(os.environ["FAKE_EVENTS"], "a") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")
    if name == "pico2wave" and "-w" in args:
        open(args[args.index("-w") + 1], "wb").close()
    return int(os.environ.get("FAKE_EXIT_" + name, "0"))


if __name__ == "__main__":
    sys.exit(main())
