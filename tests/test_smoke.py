# -*- coding: utf-8 -*-
"""Los scripts del smoke test, contra el robot de mentira.

No reemplaza correrlos en el robot: comprueba que cada uno manda lo que dice,
que su codigo de salida distingue exito de falla, y que smoke.sh recorre los
14 pasos.
"""
import os
import stat
import subprocess
import sys

import pytest

import apps_runner as ar
from conftest import ROOT, TESTS
from test_apps_golden import kinds, reason

BOARD = {"FAKE_QBOARD": "1"}
SMOKE = os.path.join(ROOT, "scripts", "smoke", "smoke.sh")


def qboard(tmp_path, *args, **kw):
    env = dict(BOARD) if kw.pop("board", True) else {}
    env.update(kw.pop("env", {}))
    return ar.run_script("scripts/smoke/qboard.py", tmp_path, args=list(args), extra_env=env, scenario=kw)


def tx(evts):
    return [e["hex"] for e in kinds(evts, "serial_tx")]


def test_qboard_version(tmp_path):
    got, out = qboard(tmp_path, "version")
    assert tx(got) == ["FF 40 00 B9 FE"]
    assert reason(got) == "sys.exit(0)", out


def test_qboard_sin_placa_falla(tmp_path):
    got, out = qboard(tmp_path, "version", board=False)
    assert reason(got) == "sys.exit(1)", out
    got, out = qboard(tmp_path / "b", "nose", "blue", board=False)
    assert reason(got) == "sys.exit(1)" and "SIN RESPUESTA" in out


def test_qboard_nariz_boca_y_parlante(tmp_path):
    casos = [(("nose", "blue"), "FF 45 01 01 60 FE"), (("nose", "none"), "FF 45 01 00 17 FE"),
             (("mouth", "smile"), "FF 44 04 00 11 0E 00 54 FE"),
             (("speaker", "on"), "FF 86 01 01 27 FE")]
    for i, (args, frame) in enumerate(casos):
        got, out = qboard(tmp_path / str(i), *args)
        assert tx(got) == [frame], args
        assert reason(got) == "sys.exit(0)", out


def test_qboard_tactil(tmp_path):
    got, out = qboard(tmp_path, "touch", "2", env={"FAKE_TOUCH": "0,1,1,2,3,0"})
    assert reason(got) == "sys.exit(0)", out
    for linea in ("tactil = 1 (derecha)", "tactil = 2 (arriba)", "tactil = 3 (izquierda)"):
        assert linea in out


def test_qboard_cabeza_dentro_de_los_limites_de_tooly(tmp_path):
    got, out = qboard(tmp_path, "head")
    assert reason(got) == "sys.exit(0)", out
    frames = tx(got)
    assert len(frames) == 6
    assert frames[0] == frames[2] == "FF 53 05 01 FD FD 01 64 00 47 FE"     # eje 1 al centro (511)


def test_face_once(tmp_path):
    got, out = ar.run_script("scripts/smoke/face_once.py", tmp_path, args=["2", "5"],
                             scenario={"faces": [[], [], [[130, 90, 60, 60]]]})
    assert reason(got) == "sys.exit(0)", out
    assert "centro en (160, 120)" in out
    assert [e["index"] for e in kinds(got, "cam_open")] == [2]
    assert kinds(got, "cascade_load") == [{"k": "cascade_load", "file": "haarcascade_frontalface_alt2.xml"}]


def test_stt_once(tmp_path):
    got, out = ar.run_script("scripts/smoke/stt_once.py", tmp_path, args=["5"],
                             scenario={"config": {"language": "spanish"}, "listens": ["audio"], "stt": ["hola robot"]})
    assert reason(got) == "sys.exit(0)", out
    assert "transcripcion (es-ES): hola robot" in out


def test_stt_once_dice_que_falla(tmp_path):
    got, out = ar.run_script("scripts/smoke/stt_once.py", tmp_path / "a", scenario={"microphones": ["bcm2835"]})
    assert reason(got) == "sys.exit(1)" and "no existe el microfono" in out
    got, out = ar.run_script("scripts/smoke/stt_once.py", tmp_path / "b",
                             scenario={"listens": ["audio"], "stt": [{"raise": "RequestError"}]})
    assert reason(got) == "sys.exit(1)" and "no se pudo consultar a Google" in out


def test_llm_once(tmp_path):
    config = {"llm_backend": "ollama", "llm_host": "http://ollama.test:11434"}
    http = [{"status": 200, "json": {"message": {"role": "assistant", "content": "Hi there"}}}]
    got, out = ar.run_script("scripts/smoke/llm_once.py", tmp_path / "a", args=["Hello"],
                             scenario={"config": config, "http": http}, extra_env={"QBO_LLM_HOST": ""})
    assert reason(got) == "sys.exit(0)", out
    assert "Hi there" in out and "ollama.test" in out
    got, out = ar.run_script("scripts/smoke/llm_once.py", tmp_path / "b",
                             scenario={"config": dict(config, llm_retries=0), "http": [{"raise": "Timeout"}]},
                             extra_env={"QBO_LLM_HOST": ""})
    assert reason(got) == "sys.exit(1)" and "no respondio" in out


# --- smoke.sh ------------------------------------------------------------------

def smoke(*args, **kw):
    return subprocess.run(["bash", SMOKE] + list(args), capture_output=True, text=True, **kw)


def test_smoke_lista_los_14_pasos_en_orden():
    out = smoke("--list").stdout.splitlines()
    assert len(out) == 14
    assert "UART" in out[0] and "Tooly completo" in out[-1]
    orden = ["UART", "GET_VERSION", "nariz", "boca", "tactil", "cabeza", "parlante", "microfono",
             "pico2wave", "camaras", "cara", "STT", "LLM", "Tooly"]
    for linea, palabra in zip(out, orden):
        assert palabra.lower() in linea.lower(), linea


def test_smoke_dry_run_no_ejecuta_nada_y_explica_cada_paso():
    result = smoke("--dry-run")
    assert result.returncode == 0
    for campo in ("comando:", "esperado:", "si falla:"):
        assert result.stdout.count(campo) == 14
    assert "PASA" not in result.stdout and "FALLA (" not in result.stdout


def _python_falso(tmp_path):
    """Un 'python' que corre los scripts dentro del robot de mentira."""
    home = tmp_path / "Documents"
    wrapper = tmp_path / "python-falso"
    wrapper.write_text('#!/bin/sh\nexec "%s" "%s" --home "%s" "$@"\n' % (
        sys.executable, os.path.join(TESTS, "harness", "run_app.py"), home))
    wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)
    events = tmp_path / "events.jsonl"
    events.write_text("")
    env = dict(os.environ, QBO_PYTHON=str(wrapper), QBO_HOME=str(home), HOME=str(tmp_path),
               FAKE_QBOARD="1", FAKE_EVENTS=str(events))
    env.pop("FAKE_SCENARIO", None)
    return env


def test_smoke_paso_3_pasa_si_la_persona_confirma(tmp_path):
    result = smoke("--only", "3", input="s\n", env=_python_falso(tmp_path))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "enviado:   FF 45 01 01 60 FE" in result.stdout
    assert "1 pasan, 0 fallan" in result.stdout


def test_smoke_paso_3_falla_si_la_persona_dice_que_no(tmp_path):
    result = smoke("--only", "3", input="n\n", env=_python_falso(tmp_path))
    assert result.returncode == 1
    assert "0 pasan, 1 fallan" in result.stdout
    assert "que significa:" in result.stdout


def test_smoke_paso_2_falla_solo_si_la_placa_no_contesta(tmp_path):
    env = _python_falso(tmp_path)
    assert smoke("--only", "2", env=env).returncode == 0
    env["FAKE_QBOARD"] = "0"
    result = smoke("--only", "2", env=env)
    assert result.returncode == 1
    assert "consola serie" in result.stdout


# --- relevar.sh ------------------------------------------------------------------

RELEVAR = os.path.join(ROOT, "scripts", "smoke", "relevar.sh")


def _relevar(tmp_path, board="1"):
    env = _python_falso(tmp_path)
    env["FAKE_QBOARD"] = board
    home = tmp_path / "Documents"
    home.mkdir(exist_ok=True)
    (home / "config.yml").write_text("language: english\nvolume: 100\ntokenAPIai: SECRETO123\n"
                                     "llm_host: http://127.0.0.1:9\ncamera_index: 2\n")
    result = subprocess.run(["bash", RELEVAR], capture_output=True, text=True, env=env)
    informes = sorted(tmp_path.glob("qbo-relevamiento-*.txt"))
    return result, (informes[-1].read_text() if informes else "")


def test_relevar_termina_bien_aunque_falte_todo(tmp_path):
    result, informe = _relevar(tmp_path, board="0")
    assert result.returncode == 0, result.stderr
    for seccion in ("Sistema", "UART y Q-board", "Audio", "Camaras", "Python", "Red y servicios externos",
                    "Repo y configuracion", "Procesos del robot", "Resumen"):
        assert "######## " + seccion in informe, seccion
    assert "FALTA  Q-board      la placa contesta GET_VERSION" in informe
    assert "FALTA  audio        tarjeta sndrpisimplecar" in informe


def test_relevar_detecta_la_placa(tmp_path):
    _result, informe = _relevar(tmp_path, board="1")
    assert "OK     Q-board      la placa contesta GET_VERSION" in informe


def test_relevar_no_copia_secretos_al_informe(tmp_path):
    # el python falso reescribe config.yml en una linea, con comillas, como JSON:
    # el formato mas dificil de enmascarar
    result, informe = _relevar(tmp_path)
    for secreto in ("SECRETO123", "TOKEN_DE_PRUEBA"):
        assert secreto not in informe and secreto not in result.stdout
    assert "tokenAPIai\": <oculto>" in informe or "tokenAPIai: <oculto>" in informe


# --- relevar.sh no filtra secretos ---------------------------------------------------

SHOW_CONFIG = os.path.join(ROOT, "scripts", "smoke", "show_config.py")

CONFIG_CON_SECRETOS = """\
language: spanish
volume: 100
camera_index: 2
llm_backend: ollama
llm_host: http://usuario:CLAVE_EN_URL@127.0.0.1:9
tokenAPIai: TOKEN_REAL
smtp_password: "CLAVE SMTP"
api_key: KEY_REAL
una_clave_que_nadie_previo: VALOR_RARO
certificado: |
  -----BEGIN PRIVATE KEY-----
  LINEA_PRIVADA
gassistant_proyectid: null
"""
SECRETOS = ["CLAVE_EN_URL", "TOKEN_REAL", "CLAVE SMTP", "KEY_REAL", "VALOR_RARO", "LINEA_PRIVADA", "PRIVATE KEY"]


def _show_config(tmp_path, texto, *args, **env):
    path = tmp_path / "config.yml"
    path.write_text(texto)
    full_env = dict(os.environ, **env)
    full_env.pop("QBO_LLM_HOST", None) if "QBO_LLM_HOST" not in env else None
    return subprocess.run([sys.executable, SHOW_CONFIG, str(path)] + list(args),
                          capture_output=True, text=True, env=full_env)


def test_show_config_solo_muestra_claves_publicas(tmp_path):
    out = _show_config(tmp_path, CONFIG_CON_SECRETOS).stdout
    for secreto in SECRETOS:
        assert secreto not in out
    assert "language: spanish" in out and "camera_index: 2" in out and "llm_backend: ollama" in out
    assert "llm_host: <oculto" in out
    assert "tokenAPIai: <oculto>" in out
    assert "gassistant_proyectid: (vacio)" in out
    # de las claves desconocidas no sale ni el nombre
    assert "otras claves: 4 (nombres y valores ocultos)" in out
    for nombre in ("smtp_password", "api_key", "una_clave_que_nadie_previo", "certificado"):
        assert nombre not in out
    assert "llm_model: (falta)" in out


def test_show_config_muestra_la_config_del_repo(tmp_path):
    with open(os.path.join(ROOT, "config.yml")) as fh:
        out = _show_config(tmp_path, fh.read()).stdout
    assert "llm_host: http://10.16.1.190:11434" in out
    assert "llm_model: qwen2.5:7b-instruct" in out
    assert "startWith: interactive-dialogflow" in out
    assert "<oculto: valor" not in out


# Formas de esconder una clave en llm_host que un recorte a mano deja pasar.
# Cada una se interpreta distinto segun quien la lea (regex, curl, requests).
URLS_TRAMPOSAS = [
    "http://usuario:S3CRETO@host:11434",
    "http://usuario:S3/CRETO@host:11434",            # barra dentro de la clave
    "http://usuario:S3@CRETO@host:11434",            # mas de una arroba
    "usuario:S3CRETO@host:11434",                    # sin esquema
    "http://host:11434/?api_key=S3CRETO",            # clave en los parametros
    "http://host:11434/S3CRETO/api",                 # clave en la ruta
    "http://host:11434#S3CRETO",
    "http://usuario:S3CRETO@host:11434\\@otro",
    "http://host:11434 S3CRETO",
    "HTTP://usuario:S3CRETO@host",
    "http://[::1]:11434/S3CRETO",
]


@pytest.mark.parametrize("url", URLS_TRAMPOSAS)
def test_show_config_no_recorta_urls_las_oculta_enteras(tmp_path, url):
    import json
    out = _show_config(tmp_path, "llm_host: %s\nlanguage: english\n" % json.dumps(url)).stdout
    assert "S3" not in out and "CRETO" not in out
    assert "llm_host: <oculto" in out
    out = _show_config(tmp_path, "language: english\n", QBO_LLM_HOST=url).stdout
    assert "S3" not in out and "CRETO" not in out


@pytest.mark.parametrize("texto", [
    "language: S3CRETO\n",                              # secreto pegado en una clave publica
    "volume: S3CRETO\n",
    "camera_index: [1, S3CRETO]\n",
    "llm_host: {url: http://h:1, token: S3CRETO}\n",    # mapa anidado bajo una clave publica
    "llm_model: \"modelo S3CRETO\"\n",
    "{language: english, S3CRETO}\n",                   # el secreto queda como nombre de clave
    "S3CRETO: 1\n",
    "? S3CRETO\n: valor\n",
    "startWith: |\n  linea\n  S3CRETO\n",
])
def test_show_config_valores_y_nombres_inesperados_no_salen(tmp_path, texto):
    result = _show_config(tmp_path, texto)
    assert "S3CRETO" not in result.stdout + result.stderr


@pytest.mark.parametrize("texto", [
    "tokenAPIai: TOKEN_REAL\n  : : [sin cerrar\n",
    "tokenAPIai: !S3CRETO_EN_UN_TAG valor\n",              # PyYAML cita el tag en el error
    "S3CRETO_SUELTO\n",                                     # un escalar, no un mapa
    "- S3CRETO_EN_LISTA\n",
    "a: &S3CRETO_ANCLA 1\nb: *S3CRETO_OTRA\n",             # alias inexistente: el error lo nombra
    "clave: \"S3CRETO sin cerrar\n",
])
def test_show_config_los_errores_no_citan_el_archivo(tmp_path, texto):
    result = _show_config(tmp_path, texto)
    salida = result.stdout + result.stderr
    assert "S3CRETO" not in salida and "TOKEN_REAL" not in salida
    assert result.returncode == 1
    assert "No se muestra el contenido" in salida


def test_show_config_llm_url_es_solo_para_curl(tmp_path):
    """--llm-url devuelve la URL sin tocar: relevar.sh la pasa a curl por el
    entorno y nunca la escribe en el informe."""
    url = "http://usuario:S3CRETO@127.0.0.1:9"
    assert _show_config(tmp_path, "llm_host: %s\n" % url, "--llm-url").stdout.strip() == url
    assert _show_config(tmp_path, "llm_host: [1, 2]\n", "--llm-url").stdout.strip() == ""


def test_relevar_con_python_real_no_filtra_ningun_secreto(tmp_path):
    home = tmp_path / "Documents"
    home.mkdir()
    (home / "config.yml").write_text(CONFIG_CON_SECRETOS)
    env = dict(os.environ, HOME=str(tmp_path), QBO_HOME=str(home), QBO_PYTHON=sys.executable,
               QBO_LLM_HOST="")
    result = subprocess.run(["bash", RELEVAR], capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr
    informe_path = sorted(tmp_path.glob("qbo-relevamiento-*.txt"))[-1]
    informe = informe_path.read_text()
    for secreto in SECRETOS:
        assert secreto not in informe and secreto not in result.stdout and secreto not in result.stderr
    assert "llm_host: <oculto" in informe
    assert "otras claves: 4 (nombres y valores ocultos)" in informe
    # el informe describe el sistema: solo lo lee su dueno
    assert stat.S_IMODE(informe_path.stat().st_mode) == 0o600
