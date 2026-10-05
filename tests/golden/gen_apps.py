"""Corre app_cases sobre el codigo original y guarda el registro normalizado.

Uso (dentro de Docker python:2.7-slim, ver generate.sh):
    python gen_apps.py <raiz del codigo py2> <home del robot> > apps_py2.json
"""
from __future__ import print_function

import io
import re
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(TESTS, "harness"))

import app_cases  # noqa: E402
import events  # noqa: E402


def run_case(case, python, script, home, extra_env=None, timeout_note=None):
    """Devuelve {"events": [...], "stdout": "..."} para un caso."""
    work = tempfile.mkdtemp()
    try:
        if os.path.isdir(home):
            shutil.rmtree(home)
        os.makedirs(home)
        scenario_path = os.path.join(work, "scenario.json")
        with io.open(scenario_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(case["scenario"], ensure_ascii=False))
        events_path = os.path.join(work, "events.jsonl")
        open(events_path, "w").close()
        env = dict(os.environ)
        env.update({"FAKE_SCENARIO": scenario_path, "FAKE_EVENTS": events_path,
                    "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8",
                    "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"})
        env.update(case["env"])
        env.update(extra_env or {})
        cwd = os.path.dirname(script) if case.get("cwd") == "script" else work
        proc = subprocess.Popen(
            [python, os.path.join(TESTS, "harness", "run_app.py"), "--home", home, script] + case["args"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, cwd=cwd)
        out, _ = proc.communicate()
        text = out.decode("utf-8", "replace")
        # el numero de linea del arnes en los tracebacks cambia al editar el arnes
        text = re.sub(r'(run_app\.py", line )\d+', r'\1N', text)
        return {"events": events.load(events_path), "stdout": text, "returncode": proc.returncode}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    root, home = sys.argv[1], sys.argv[2]
    result = {}
    for case in app_cases.CASES:
        script = os.path.join(root, app_cases.SCRIPTS[case["script"]][0])
        run = run_case(case, sys.executable, script, home)
        result[case["name"]] = {
            "events": events.normalize(run["events"], home),
            "stdout": run["stdout"].replace(home, events.HOME_TOKEN),
        }
        print("  %-55s %4d eventos" % (case["name"][:55], len(result[case["name"]]["events"])),
              file=sys.stderr)
    json.dump(result, sys.stdout, indent=1, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
