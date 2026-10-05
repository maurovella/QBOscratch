"""Alertas por mail: credenciales por entorno, nunca en el codigo."""
import os
import re

import apps_runner as ar
from conftest import ROOT
from test_apps_golden import kinds, reason, tts_text

ALERTA = "tooly: cuatro horas de silencio y alerta por mail"


def test_usa_la_cuenta_y_los_destinatarios_del_entorno(tmp_path):
    env = {"QBO_SMTP_USER": "otro@example.org", "QBO_ALERT_TO": "a@example.org, b@example.org"}
    home = str(tmp_path / "Documents")
    case = ar.CASES[ALERTA]
    script = os.path.join(ROOT, ar.app_cases.SCRIPTS[case["script"]][1])
    base = {"QBO_HOME": home, "QBO_SMTP_PASSWORD": "x"}
    base.update(env)
    raw = ar.gen_apps.run_case(case, ar.sys.executable, script, home, extra_env=base)["events"]
    mails = [e for e in raw if e["k"] == "smtp_sendmail"]
    assert [m["sender"] for m in mails] == ["otro@example.org"] * 2
    assert [m["to"] for m in mails] == [["a@example.org", "b@example.org"]] * 2
    assert [e["user"] for e in raw if e["k"] == "smtp_login"] == ["otro@example.org"] * 2


def test_sin_credenciales_no_manda_mail_y_el_robot_sigue(tmp_path):
    env = {"QBO_SMTP_USER": "", "QBO_SMTP_PASSWORD": "", "QBO_ALERT_TO": ""}
    got, out = ar.run(ALERTA, tmp_path, extra_env=env)
    assert reason(got) == "end", out
    assert kinds(got, "smtp_connect") == []
    assert out.count("email NO enviado") == 2
    # la conversacion continua igual despues de la alerta
    assert tts_text(got)[-1] == "Good to hear that"


def test_no_hay_direcciones_ni_claves_en_el_codigo():
    patron = re.compile(r"[\w.+-]+@(gmail|hotmail|yahoo|outlook)\.\w+")
    for carpeta in ("qbo", "apps", "tools", "tests"):
        for base, _dirs, files in os.walk(os.path.join(ROOT, carpeta)):
            for name in files:
                if name.endswith((".py", ".json", ".yml")):
                    with open(os.path.join(base, name), encoding="utf-8", errors="replace") as fh:
                        assert not patron.search(fh.read()), os.path.join(base, name)
