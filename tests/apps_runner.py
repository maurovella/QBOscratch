"""Corre los casos de tests/golden/app_cases.py sobre el codigo actual."""
import copy
import json
import os
import sys

from conftest import ROOT, TESTS

sys.path.insert(0, os.path.join(TESTS, "harness"))

import app_cases  # noqa: E402
import events  # noqa: E402
import gen_apps  # noqa: E402

with open(os.path.join(TESTS, "golden", "apps_py2.json"), encoding="utf-8") as fh:
    GOLDEN = json.load(fh)

CASES = {c["name"]: c for c in app_cases.CASES}


def canon(evts):
    """Quita lo que cambia por decision de la migracion y no es comportamiento.

    - cascadas Haar: se movieron a qbo/data, se compara solo el nombre de archivo;
    - http_post: `extra` son kwargs como timeout, que el original no pasaba.
    """
    out = []
    for event in copy.deepcopy(evts):
        if "repeat" in event:
            event["block"] = canon(event["block"])
        elif event["k"] == "cascade_load":
            event = {"k": "cascade_load", "file": os.path.basename(event["path"])}
        elif event["k"] == "http_post":
            event.pop("extra", None)
        out.append(event)
    return out


def run(name, tmp_path, extra_env=None, scenario=None):
    """Devuelve (eventos normalizados, stdout) del caso `name` sobre el codigo actual."""
    case = dict(CASES[name])
    if scenario is not None:
        case["scenario"] = scenario
    script = os.path.join(ROOT, app_cases.SCRIPTS[case["script"]][1])
    return run_script(script, tmp_path, case, extra_env)


def run_script(script, tmp_path, case=None, extra_env=None, args=(), scenario=None):
    """Como run(), para un script y un guion que no estan en app_cases."""
    if case is None:
        case = {"args": list(args), "scenario": scenario or {}, "env": {}, "cwd": None}
    script = os.path.join(ROOT, script)
    home = str(tmp_path / "Documents")
    env = {"QBO_HOME": home, "FAKE_NUMPY": "1"}
    env.update(extra_env or {})
    result = gen_apps.run_case(case, sys.executable, script, home, extra_env=env)
    return canon(events.normalize(result["events"], home)), result["stdout"].replace(home, events.HOME_TOKEN)


def golden(name):
    return canon(GOLDEN[name]["events"]), GOLDEN[name]["stdout"]


def lines(evts):
    return [events.describe(e) for e in evts]
