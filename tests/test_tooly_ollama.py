# -*- coding: utf-8 -*-
"""Tooly con el backend de Ollama, de punta a punta contra el robot de mentira.

El robot tiene que hacer lo mismo que con el servidor original (mismos bytes
por la UART, mismo TTS), cambiando solo a quien le pregunta.
"""
import apps_runner as ar
from qbo.llm import FALLBACK_TEXT
from qbo.llm.prompt import TOOLY_ASSISTANT_TEXT
from test_apps_golden import kinds, reason, tts_text

OLLAMA = {"llm_backend": "ollama", "llm_host": "http://ollama.test:11434",
          "llm_model": "qwen2.5:7b-instruct", "llm_retries": 2}
FACE = [130, 90, 60, 60]
STARTUP_FALLBACK = "Hello ! My mind is not ready, I will repeat whatever you say."


def says(text):
    return {"status": 200, "json": {"model": "m", "done": True,
                                    "message": {"role": "assistant", "content": text}}}


def run(tmp_path, scenario, script="apps/tooly.py", touch=None):
    scenario = dict(scenario)
    scenario["config"] = dict(OLLAMA, **scenario.get("config", {}))
    env = {"FAKE_QBOARD": "1", "QBO_LLM_HOST": ""}
    if touch:
        env["FAKE_TOUCH"] = touch
    return ar.run_script(script, tmp_path, scenario=scenario, extra_env=env)


def test_dos_turnos_con_ollama(tmp_path):
    legacy = ar.CASES["tooly: dos turnos de conversacion"]["scenario"]
    scenario = dict(legacy, http=[says("Hi, I am Tooly"), says('*smiles* Nice to "meet" you'),
                                  says("My name is Tooly")])
    got, out = run(tmp_path, scenario)
    assert reason(got) == "end", out

    posts = kinds(got, "http_post")
    assert {p["url"] for p in posts} == {"http://ollama.test:11434/api/chat"}
    assert [p["json"]["messages"][-1]["content"] for p in posts] == ["Hello", "hello tooly", "what is your name"]
    assert posts[0]["json"]["messages"][0] == {"role": "system", "content": TOOLY_ASSISTANT_TEXT}
    assert posts[0]["json"]["stream"] is False and posts[0]["json"]["model"] == "qwen2.5:7b-instruct"
    assert [m["role"] for m in posts[2]["json"]["messages"]] == [
        "system", "user", "assistant", "user", "assistant", "user"]
    # lo que dice sale limpio de acotaciones y comillas
    assert tts_text(got) == ["Hi, I am Tooly", "Nice to meet you", "My name is Tooly"]

    # el resto del robot no se entera del cambio de backend
    golden, _ = ar.golden("tooly: dos turnos de conversacion")
    for kind in ("serial_tx", "detect", "stt_listen", "stt_recognize", "cam_open"):
        assert kinds(got, kind) == kinds(golden, kind), kind


def test_ollama_se_cae_en_medio_de_la_charla(tmp_path):
    scenario = {"frames": 3, "faces": [[FACE]], "listens": ["audio"], "stt": ["are you there"],
                "http": [says("Hello"), {"raise": "Timeout"}, {"raise": "Timeout"}, {"raise": "ConnectionError"}]}
    got, out = run(tmp_path, scenario)
    assert reason(got) == "end", out                      # antes: traceback y el programa moria
    assert len(kinds(got, "http_post")) == 4              # 1 saludo + 1 intento + 2 reintentos
    assert tts_text(got) == ["Hello", FALLBACK_TEXT, "are you there"]
    assert "LLM sin respuesta" in out


def test_ollama_apagado_al_arrancar_queda_en_modo_repetir(tmp_path):
    scenario = {"frames": 3, "faces": [[FACE]], "listens": ["audio"], "stt": ["repeat after me"],
                "http": [{"raise": "ConnectionError"}] * 3}
    got, out = run(tmp_path, scenario)
    assert reason(got) == "end", out
    assert len(kinds(got, "http_post")) == 3
    assert tts_text(got) == [STARTUP_FALLBACK, "repeat after me"]


def test_caricia_con_ollama_caido_no_rompe(tmp_path):
    scenario = {"frames": 3, "faces": [[FACE]], "listens": ["audio"], "stt": ["thank you"],
                "http": [says("Hello")] + [{"raise": "Timeout"}] * 3 + [says("You are welcome")]}
    got, out = run(tmp_path, scenario, touch="0,1,0,0")
    assert reason(got) == "end", out
    assert tts_text(got) == ["Hello", "You are welcome"]
    assert "FF 44 04 1B 1F 0E 04" in " ".join(e["hex"] for e in kinds(got, "serial_tx"))   # boca de carino


def test_servidor_original_caido_en_medio_de_la_charla(tmp_path):
    scenario = {"config": {"llm_backend": "tooly_legacy"}, "frames": 3, "faces": [[FACE]],
                "listens": ["audio"], "stt": ["are you there"],
                "http": [{"status": 200, "json": {"conversation_id": "c"}},
                         {"status": 200, "json": {"response": "Hello"}}, {"raise": "ConnectionError"}]}
    got, out = run(tmp_path, scenario)
    assert reason(got) == "end", out
    assert tts_text(got) == ["Hello", FALLBACK_TEXT, "are you there"]


def test_tooly_audio_con_ollama(tmp_path):
    scenario = {"listens": ["audio"], "stt": ["good morning"], "http": [says("Hello"), says("Good morning")],
                "stop": {"kind": "exec", "count": 4, "max_real_seconds": 5}}
    got, out = run(tmp_path, scenario, script="apps/tooly_audio.py")
    assert reason(got) == "stop", out
    assert tts_text(got) == ["Hello", "Good morning"]


def test_sin_microfono_el_error_dice_que_falta(tmp_path):
    """Sin la tarjeta I2S no existe dmicQBO_sv. Tooly no puede arrancar, pero
    tiene que decir por que."""
    for script in ("apps/tooly.py", "apps/tooly_audio.py", "apps/repeat.py"):
        got, out = run(tmp_path / script.replace("/", "_"), {"microphones": ["bcm2835 Headphones", "vc4-hdmi"]},
                       script=script)
        assert reason(got) == "EXC RuntimeError", out
        assert "Microfono 'dmicQBO_sv' no encontrado" in out
        assert "vc4-hdmi" in out
