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
