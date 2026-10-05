"""Los puentes de 'Python projects/': las rutas que lanzan deamonsScripts/QBO_*.

Cada puente tiene que comportarse igual que el script de apps/ al que delega,
y tiene que estar marcado como ejecutable en git, porque los daemons lo
ejecutan directamente.
"""
import os
import subprocess

import pytest

import apps_runner as ar
from conftest import ROOT
from test_apps_golden import kinds, reason, tts_text

BRIDGES = ["PiCmd.py", "say.py", "listen.py", "feel.py", "findFace.py", "PiFaceFast.py"]


def bridge(name):
    return os.path.join("Python projects", name)


def test_picmd_por_el_puente(tmp_path):
    got, out = ar.run_script(bridge("PiCmd.py"), tmp_path, args=["-c", "nose", "-co", "blue"])
    assert [e["hex"] for e in kinds(got, "serial_tx")] == ["FF 45 01 01 60 FE"], out
    got, out = ar.run_script(bridge("PiCmd.py"), tmp_path / "ayuda", args=["?"])
    assert "-c [command] servo, nose, say, mouth, listen or voice" in out


def test_say_por_el_puente(tmp_path):
    scenario = {"fifo_writes": [{"pipe": "pipe_say", "data": "Hola"}],
                "stop": {"kind": "exec", "count": 4, "max_real_seconds": 5}}
    got, out = ar.run_script(bridge("say.py"), tmp_path, scenario=scenario)
    assert tts_text(got) == ["Hola"], out


def test_feel_por_el_puente(tmp_path):
    scenario = {"fifo_reads": ["pipe_feel"], "stop": {"kind": "serial_tx", "count": 3}}
    got, out = ar.run_script(bridge("feel.py"), tmp_path, scenario=scenario,
                             extra_env={"FAKE_QBOARD": "1", "FAKE_TOUCH": "1,2"})
    assert kinds(got, "fifo_total")[0]["data"] == "Touch: rightTouch: up", out


def test_find_face_por_el_puente_sin_depender_del_directorio_actual(tmp_path):
    scenario = {"fifo_reads": ["pipe_findFace"], "faces": [[[130, 90, 60, 60]]],
                "stop": {"kind": "detect", "count": 2}}
    got, out = ar.run_script(bridge("findFace.py"), tmp_path, scenario=scenario)
    assert kinds(got, "fifo_total")[0]["data"] == "160,120\n", out
    assert len(kinds(got, "cascade_load")) == 2


def test_listen_por_el_puente(tmp_path):
    scenario = {"background": ["audio"], "stt": ["hola"], "fifo_reads": ["pipe_listen", "pipe_cmd"],
                "stop": {"kind": "sleep", "count": 4}}
    got, out = ar.run_script(bridge("listen.py"), tmp_path, scenario=scenario)
    assert {e["pipe"]: e["data"] for e in kinds(got, "fifo_total")}["pipe_listen"] == "hola", out


def test_face_follow_arranca_por_el_puente(tmp_path):
    """El modo interactivo original no tiene golden: aca solo se comprueba que
    importa, abre la camara y llega a buscar caras, sin los paquetes de
    Dialogflow ni de Google Assistant instalados."""
    scenario = {"config": {"startWith": "interactive-dialogflow"}, "stop": {"kind": "detect", "count": 3}}
    got, out = ar.run_script(bridge("PiFaceFast.py"), tmp_path, scenario=scenario,
                             extra_env={"FAKE_QBOARD": "1", "FAKE_MISSING": "apiai,google"})
    assert reason(got) == "stop", out
    assert [e["index"] for e in kinds(got, "cam_open")] == [0]
    assert kinds(got, "serial_tx"), out


@pytest.mark.parametrize("path", [bridge(n) for n in BRIDGES] + [
    "deamonsScripts/QBO_scratch", "deamonsScripts/QBO_PiCmd", "deamonsScripts/QBO_say",
    "deamonsScripts/QBO_listen", "deamonsScripts/QBO_feel", "deamonsScripts/QBO_findFace",
    "deamonsScripts/QBO_PiFaceFast", "deamonsScripts/QBO_server", "deamonsScripts/lsqbo",
    "deploy/install.sh", "scripts/check.sh", "scripts/smoke/smoke.sh"])
def test_ejecutable_en_git(path):
    """El repo tiene core.filemode=false: el modo hay que mirarlo en el indice."""
    mode = subprocess.check_output(["git", "-C", ROOT, "ls-files", "-s", "--", path]).decode().split()[0]
    assert mode == "100755", path


def test_cada_daemon_lanza_un_puente_que_existe():
    for daemon, script in [("QBO_PiCmd", "PiCmd.py"), ("QBO_say", "say.py"), ("QBO_listen", "listen.py"),
                           ("QBO_feel", "feel.py"), ("QBO_findFace", "findFace.py"),
                           ("QBO_PiFaceFast", "PiFaceFast.py")]:
        with open(os.path.join(ROOT, "deamonsScripts", daemon)) as fh:
            assert script in fh.read(), daemon
        assert os.path.isfile(os.path.join(ROOT, "Python projects", script))
