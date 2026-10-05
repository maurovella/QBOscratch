"""Corre un script del robot contra un robot de mentira.

    python run_app.py --home DIR script.py [argumentos...]

Arma DIR como /home/pi/Documents (config.yml, pipes/, deamonsScripts/), pone
pico2wave y aplay falsos en el PATH, reemplaza serial, cv2, speech_recognition
y requests por dobles, y usa un reloj falso para que los sleep() no esperen.
Todo lo observable queda en $FAKE_EVENTS, un evento JSON por linea.

Compatible con Python 2.7 y 3: el mismo arnes captura el comportamiento del
codigo original (en Docker) y el del migrado.
"""
from __future__ import print_function

import json
import os
import runpy
import stat
import sys
import threading
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
PY2 = sys.version_info[0] == 2

PIPES = ["pipe_cmd", "pipe_say", "pipe_listen", "pipe_feel", "pipe_findFace"]
DAEMONS = ["QBO_listen", "QBO_scratch", "QBO_PiFaceFast", "QBO_say", "writeWiFi.sh"]
BINARIES = ["pico2wave", "aplay", "espeak", "sudo"]

real_sleep = time.sleep


def write_executable(path, name):
    with open(path, "w") as fh:
        fh.write('#!/bin/sh\nexec "%s" "%s" "%s" "$@"\n' % (
            sys.executable, os.path.join(HERE, "fakebin.py"), name))
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def setup_home(home, scenario):
    for sub in ("pipes", "deamonsScripts", "fakebin"):
        path = os.path.join(home, sub)
        if not os.path.isdir(path):
            os.makedirs(path)
    for pipe in PIPES:
        path = os.path.join(home, "pipes", pipe)
        if not os.path.exists(path):
            os.mkfifo(path)
    for name in DAEMONS:
        write_executable(os.path.join(home, "deamonsScripts", name), name)
    for name in BINARIES:
        write_executable(os.path.join(home, "fakebin", name), name)
    os.environ["PATH"] = os.path.join(home, "fakebin") + os.pathsep + os.environ.get("PATH", "")
    config = {"age": 0, "language": "english", "startWith": "interactive-dialogflow",
              "tokenAPIai": "TOKEN_DE_PRUEBA", "op_question": True, "volume": 100,
              "gassistant_proyectid": None}
    config.update(scenario.get("config", {}))
    with open(os.path.join(home, "config.yml"), "w") as fh:
        json.dump(config, fh, sort_keys=True)


def text(data):
    return data.decode("utf-8", "replace") if isinstance(data, bytes) else data


def fifo_reader(fakelog, home, pipe):
    path = os.path.join(home, "pipes", pipe)
    while True:
        fd = os.open(path, os.O_RDONLY)
        while True:
            chunk = os.read(fd, 4096)
            if not chunk:
                break
            fakelog.emit("fifo_rx", pipe=pipe, data=text(chunk))
        os.close(fd)


def fifo_writer(home, writes):
    for item in writes:
        real_sleep(item.get("pause", 0.3))
        fd = os.open(os.path.join(home, "pipes", item["pipe"]), os.O_WRONLY)
        data = item["data"]
        os.write(fd, data if isinstance(data, bytes) else data.encode("utf-8"))
        os.close(fd)


def count_events(kind):
    total = 0
    try:
        with open(os.environ["FAKE_EVENTS"]) as fh:
            for line in fh:
                if '"k": "%s"' % kind in line:
                    total += 1
    except IOError:
        pass
    return total


def watchdog(fakelog, stop, home):
    """Red de seguridad: si el guion no corta la corrida, la corta el reloj real."""
    real_sleep(stop.get("max_real_seconds", 20))
    finish(fakelog, home, "timeout")


def install_stop(fakelog, stop, home):
    """Corta los scripts que son un bucle infinito en un punto fijo del guion.

    {"kind": K, "count": N}: termina cuando se registro el N-esimo evento K.
    Para K = "exec" (pico2wave, aplay...) se cuenta al volver de subprocess.
    """
    if "kind" not in stop:
        return
    seen = {"n": 0}

    def check(kind):
        if kind == stop["kind"]:
            seen["n"] += 1
            if seen["n"] >= stop["count"]:
                fakelog.on_emit = None
                finish(fakelog, home, "stop")

    if stop["kind"] != "exec":
        fakelog.on_emit = check
        return

    import subprocess

    def wrap(original):
        def wrapper(*args, **kwargs):
            result = original(*args, **kwargs)
            if count_events("exec") >= stop["count"]:
                finish(fakelog, home, "stop")
            return result
        return wrapper

    for name in ("call", "check_call", "run"):
        if hasattr(subprocess, name):
            setattr(subprocess, name, wrap(getattr(subprocess, name)))


_finishing = threading.Lock()


def finish(fakelog, home, reason):
    if not _finishing.acquire(False):
        real_sleep(60)      # otro hilo ya esta cerrando la corrida
    real_sleep(fakelog.scenario().get("settle", 0.15))   # que los lectores de FIFO terminen
    fakelog.on_emit = None
    emit_config(fakelog, home)
    if os.environ.get("FAKE_COUNT_FDS") == "1":
        # descriptores abiertos al terminar: sirve para detectar fugas en los FIFOs
        fakelog.emit("open_fds", n=len(os.listdir("/dev/fd")))
    fakelog.emit("exit", reason=reason)
    sys.stdout.flush()
    os._exit(0)


def emit_config(fakelog, home):
    try:
        import yaml
        with open(os.path.join(home, "config.yml")) as fh:
            fakelog.emit("config_after", config=yaml.safe_load(fh))
    except Exception as exc:
        fakelog.emit("config_after", error=type(exc).__name__)


class FakeSMTP(object):
    def __init__(self, host, port=0, **kwargs):
        import fakelog
        self.log = fakelog
        self.log.emit("smtp_connect", host=host, port=port)

    def login(self, user, password):
        self.log.emit("smtp_login", user=user, has_password=bool(password))

    def sendmail(self, sender, to, message):
        body = message.split("\n\n", 1)[-1]
        headers = dict(line.split(": ", 1) for line in message.split("\n\n", 1)[0].splitlines()
                       if ": " in line)
        self.log.emit("smtp_sendmail", sender=sender, to=to, subject=headers.get("Subject"),
                      body=body)

    def quit(self):
        pass


time_real = time.time


def main():
    argv = sys.argv[1:]
    assert argv[0] == "--home", __doc__
    home, script, script_args = argv[1], argv[2], argv[3:]

    sys.path.insert(0, os.path.join(TESTS, "fakes"))
    sys.path.insert(0, os.path.join(TESTS, "fakes_app"))
    if PY2:
        sys.path.insert(0, os.path.join(TESTS, "fakes_py2"))
    import fakelog

    # FAKE_MISSING simula paquetes que no estan instalados en el robot
    for name in os.environ.get("FAKE_MISSING", "").split(","):
        if name:
            sys.modules[name] = None

    scenario = fakelog.scenario()
    setup_home(home, scenario)

    time.sleep = fakelog.clock.sleep
    time.time = fakelog.clock.time
    import smtplib
    smtplib.SMTP_SSL = FakeSMTP

    for pipe in scenario.get("fifo_reads", []):
        thread = threading.Thread(target=fifo_reader, args=(fakelog, home, pipe))
        thread.daemon = True
        thread.start()
    if scenario.get("fifo_writes"):
        thread = threading.Thread(target=fifo_writer, args=(home, scenario["fifo_writes"]))
        thread.daemon = True
        thread.start()
    thread = threading.Thread(target=watchdog, args=(fakelog, scenario.get("stop", {}), home))
    thread.daemon = True
    thread.start()
    install_stop(fakelog, scenario.get("stop", {}), home)

    sys.argv = [script] + script_args
    sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
    reason = "end"
    try:
        runpy.run_path(script, run_name="__main__")
    except SystemExit as exc:
        reason = "sys.exit(%r)" % (exc.code,)
    except BaseException as exc:
        traceback.print_exc()
        reason = "EXC " + type(exc).__name__
    finish(fakelog, home, reason)


if __name__ == "__main__":
    main()
