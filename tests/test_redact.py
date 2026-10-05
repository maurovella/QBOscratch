# -*- coding: utf-8 -*-
"""Nada de config.yml que no tenga la forma esperada llega a la pantalla.

Los scripts originales imprimian la configuracion entera al arrancar y en cada
frase. Eso queda en los registros del smoke test, en interactiveMode.log y en
el journal de systemd.
"""
import pytest

import apps_runner as ar
from qbo import llm, redact
from qbo.llm.ollama import OllamaClient
from qbo.llm.tooly_legacy import ToolyLegacyClient

SECRETO = "S3CRETO-de-prueba"
# claves que un robot real podria tener en config.yml ademas de las conocidas
CONFIG_SUCIA = {"tokenAPIai": SECRETO, "smtp_password": SECRETO, "nota": "clave " + SECRETO,
                "gassistant_proyectid": SECRETO}
BOARD = {"FAKE_QBOARD": "1"}


def test_summary_muestra_lo_conocido_y_cuenta_lo_demas():
    texto = redact.summary({"language": "spanish", "volume": 120, "camera_index": 2,
                            "llm_host": "http://10.0.0.5:11434", "llm_model": "qwen2.5:7b-instruct",
                            "tokenAPIai": "abc", "otra": "x", "mas": [1, 2]})
    assert texto == ("{camera_index: 2, language: spanish, llm_host: http://10.0.0.5:11434, "
                     "llm_model: qwen2.5:7b-instruct, volume: 120, tokenAPIai: <oculto>, "
                     "otras claves: 2 (nombres y valores ocultos)}")


@pytest.mark.parametrize("valor", ["http://u:p@h:1", "http://h:1/x", "http://h:1?k=v", "h:1", "ftp://h", 7, None,
                                   ["http://h:1"], "http://h:1 x", "http://h:1\nx"])
def test_safe_url_solo_acepta_host_y_puerto(valor):
    assert redact.safe_url(valor) == redact.OCULTO


def test_safe_url_deja_pasar_la_forma_simple():
    for url in ("http://10.16.1.190:11434", "https://ollama.ejemplo.org", "http://localhost:11434/"):
        assert redact.safe_url(url) == url


CASOS = [
    ("PiCmd args: -c nose -co blue", {}),
    ("PiCmd args: -c voice -l spanish", {}),
    ("autoStart: scratch en english", {}),
    ("autoStop: en spanish", {}),
    ("tooly: caricia en la cabeza", BOARD),
    ("tooly_audio: un turno", BOARD),
    ("repeat: repite lo que oye", {}),
]


@pytest.mark.parametrize("name,env", CASOS)
def test_los_scripts_no_imprimen_secretos_de_config(name, env, tmp_path):
    scenario = dict(ar.CASES[name]["scenario"])
    scenario["config"] = dict(scenario.get("config", {}), **CONFIG_SUCIA)
    _got, out = ar.run(name, tmp_path, scenario=scenario, extra_env=env)
    assert SECRETO not in out, out
    assert "smtp_password" not in out and "nota" not in out


def test_face_follow_no_imprime_secretos_de_config(tmp_path):
    scenario = {"config": dict(CONFIG_SUCIA, startWith="interactive-dialogflow"),
                "stop": {"kind": "detect", "count": 3}}
    _got, out = ar.run_script("apps/face_follow.py", tmp_path, scenario=scenario, extra_env=BOARD)
    assert SECRETO not in out


def test_tooly_no_imprime_la_clave_de_la_url_del_llm(tmp_path):
    """Con el LLM caido, el aviso por pantalla no puede llevar la URL con su clave."""
    scenario = {"config": {"llm_backend": "ollama", "llm_host": "http://usuario:%s@ollama.test:11434" % SECRETO,
                           "llm_retries": 0},
                "frames": 3, "faces": [[[130, 90, 60, 60]]], "listens": ["audio"], "stt": ["hola"],
                "http": [{"status": 200, "json": {"message": {"role": "assistant", "content": "Hello"}}},
                         {"status": 500, "json": None}]}
    _got, out = ar.run_script("apps/tooly.py", tmp_path, scenario=scenario,
                              extra_env={"FAKE_QBOARD": "1", "QBO_LLM_HOST": ""})
    assert "LLM sin respuesta" in out
    assert SECRETO not in out and "usuario" not in out


@pytest.mark.parametrize("cliente", [
    lambda url: OllamaClient(host=url, timeout=1, retries=0),
    lambda url: ToolyLegacyClient(host=url, timeout=1, retries=0),
])
def test_los_errores_del_cliente_llm_no_citan_la_url(cliente, monkeypatch):
    """Con requests real: el texto de sus excepciones si trae la URL."""
    from qbo.llm import base
    monkeypatch.setattr(base, "RETRY_WAIT_S", 0)
    for url in ("http://usuario:%s@127.0.0.1:9" % SECRETO, "http://127.0.0.1:9/%s" % SECRETO,
                "http://127.0.0.1:9/?api_key=%s" % SECRETO):
        client = cliente(url)
        with pytest.raises(llm.LLMError) as error:
            client.start()
            client.chat("hola")
        assert SECRETO not in str(error.value)
        assert "usuario" not in str(error.value)
