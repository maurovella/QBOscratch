"""config.yml: el del repo y los formatos que hubo en el robot."""
import os

import yaml

import apps_runner as ar
from conftest import ROOT
from qbo import llm
from qbo.llm.ollama import OllamaClient
from qbo.llm.tooly_legacy import ToolyLegacyClient
from test_apps_golden import kinds

# claves que lee algun script: (clave, quien la usa)
CLAVES = ["language", "volume", "startWith", "tokenAPIai", "gassistant_proyectid"]

# el config.yml de la SSD vieja, en una linea y sin claves de Tooly
SSD_VIEJA = ("{age: 0, language: english, startWith: interactive-dialogflow, tokenAPIai: X, "
             "op_question: true, volume: 100, gassistant_proyectid: null}")


def repo_config():
    with open(os.path.join(ROOT, "config.yml")) as fh:
        return yaml.safe_load(fh)


def test_config_del_repo_tiene_todas_las_claves_que_lee_el_codigo():
    config = repo_config()
    for clave in CLAVES:
        assert clave in config, clave
    assert config["language"] in ("english", "spanish")
    assert 0 <= config["volume"] <= 500


def test_config_del_repo_apunta_tooly_a_ollama(monkeypatch):
    monkeypatch.delenv("QBO_LLM_HOST", raising=False)
    client = llm.from_config(repo_config())
    assert isinstance(client, OllamaClient)
    assert client.url.endswith(":11434/api/chat")
    assert client.model == "qwen2.5:7b-instruct"


def test_config_del_repo_no_trae_secretos():
    assert repo_config()["tokenAPIai"] == "REEMPLAZAR_TOKEN"


def test_config_de_la_ssd_vieja_sigue_funcionando(monkeypatch):
    monkeypatch.delenv("QBO_LLM_HOST", raising=False)
    config = yaml.safe_load(SSD_VIEJA)
    assert isinstance(llm.from_config(config), ToolyLegacyClient)
    assert config.get("camera_index", 1) == 1


def test_picmd_voice_conserva_las_claves_de_tooly(tmp_path):
    """-c voice reescribe config.yml con yaml.dump: no puede perder claves."""
    extra = {"llm_backend": "ollama", "llm_host": "http://h:11434", "camera_index": 2}
    scenario = {"config": extra, "fifo_reads": ["pipe_say"]}
    got, out = ar.run("PiCmd args: -c voice -l spanish", tmp_path, scenario=scenario)
    after = kinds(got, "config_after")[0]["config"]
    assert after["language"] == "spanish", out
    for clave, valor in extra.items():
        assert after[clave] == valor
