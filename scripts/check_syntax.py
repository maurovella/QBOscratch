#!/usr/bin/env python3
"""Gate sintactico: compila todos los .py trackeados y busca nombres indefinidos.

Sale con codigo != 0 si:
  - un archivo que no esta en scripts/known_failing.txt no compila,
  - pyflakes encuentra un nombre indefinido que no esta en esa lista,
  - una entrada de la lista ya no falla (hay que borrarla: la lista solo se achica).

No importa ningun modulo del robot, asi que corre sin hardware.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWN = os.path.join(ROOT, "scripts", "known_failing.txt")


def tracked_py_files():
    out = subprocess.check_output(["git", "-C", ROOT, "ls-files", "-z", "*.py"])
    return sorted(f for f in out.decode("utf-8").split("\0") if f)


def load_known():
    known = set()
    if os.path.exists(KNOWN):
        with open(KNOWN, encoding="utf-8") as fh:
            for line in fh:
                line = line.split("#", 1)[0].strip()
                if line:
                    known.add(line)
    return known


def compile_failures(files):
    failures = {}
    for rel in files:
        with open(os.path.join(ROOT, rel), "rb") as fh:
            src = fh.read()
        try:
            compile(src, rel, "exec")
        except (SyntaxError, ValueError) as exc:
            failures["compile:" + rel] = "%s linea %s: %s" % (
                type(exc).__name__, getattr(exc, "lineno", "?"), getattr(exc, "msg", exc))
    return failures


def undefined_names(files):
    try:
        from pyflakes import api, messages, reporter
    except ImportError:
        print("AVISO: pyflakes no esta instalado, se saltea el chequeo de nombres indefinidos")
        return None

    class Collector(reporter.Reporter):
        def __init__(self):
            self.found = {}

        def unexpectedError(self, filename, msg):
            pass

        def syntaxError(self, filename, msg, lineno, offset, text):
            pass

        def flake(self, message):
            if isinstance(message, (messages.UndefinedName, messages.UndefinedLocal)):
                rel = os.path.relpath(message.filename, ROOT)
                key = "undefined:%s:%s" % (rel, message.message_args[0])
                self.found.setdefault(key, []).append(message.lineno)

    collector = Collector()
    for rel in files:
        api.checkPath(os.path.join(ROOT, rel), reporter=collector)
    return {k: "lineas %s" % ", ".join(map(str, v)) for k, v in collector.found.items()}


def main():
    files = tracked_py_files()
    known = load_known()
    failures = compile_failures(files)
    compiling = [f for f in files if "compile:" + f not in failures]
    undefined = undefined_names(compiling)
    if undefined:
        failures.update(undefined)

    new = sorted(k for k in failures if k not in known)
    stale = sorted(k for k in known if k not in failures)
    if undefined is None:
        stale = [k for k in stale if not k.startswith("undefined:")]

    print("Python %s, %d archivos .py, %d fallas conocidas, %d nuevas" % (
        sys.version.split()[0], len(files), len(failures) - len(new), len(new)))
    for key in new:
        print("FALLA NUEVA  %s  (%s)" % (key, failures[key]))
    for key in stale:
        print("YA NO FALLA  %s  -> borrar de scripts/known_failing.txt" % key)
    return 1 if (new or stale) else 0


if __name__ == "__main__":
    sys.exit(main())
