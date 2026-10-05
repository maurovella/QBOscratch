"""Que paquete necesita cada script para arrancar.

FAKE_MISSING hace que `import X` falle, como en un robot donde X no esta
instalado. apiai (Dialogflow V1) y google.assistant.library ya no existen,
asi que nada de lo que se usa hoy puede depender de ellos.
"""
import apps_runner as ar
from test_apps_golden import kinds, reason

MUERTOS = "apiai,google"


def test_picmd_no_necesita_voz_ni_camara(tmp_path):
    env = {"FAKE_MISSING": MUERTOS + ",speech_recognition,cv2,requests"}
    got, out = ar.run("PiCmd args: -c nose -co blue", tmp_path, extra_env=env)
    assert [e["hex"] for e in kinds(got, "serial_tx")] == ["FF 45 01 01 60 FE"], out
    assert reason(got) == "sys.exit(None)"


def test_listen_escucha_sin_apiai(tmp_path):
    """listen.py (modo Scratch) solo transcribe: no necesita Dialogflow."""
    scenario = {"background": ["audio"], "stt": ["hola robot"], "fifo_reads": ["pipe_listen", "pipe_cmd"],
                "stop": {"kind": "sleep", "count": 4}}
    got, out = ar.run_script("apps/listen.py", tmp_path, scenario=scenario,
                             extra_env={"FAKE_MISSING": MUERTOS})
    assert reason(got) == "stop", out
    fifos = {e["pipe"]: e["data"] for e in kinds(got, "fifo_total")}
    assert fifos["pipe_listen"] == "hola robot"


def test_qbotalk_no_imprime_el_token(tmp_path):
    scenario = {"background": [], "stop": {"kind": "sleep", "count": 2}}
    _got, out = ar.run_script("apps/listen.py", tmp_path, scenario=scenario)
    assert "TOKEN_DE_PRUEBA" not in out.split("CONFIG")[0]
    assert "TOKEN:" not in out
