# -*- coding: utf-8 -*-
"""Golden master de los scripts del robot.

tests/golden/apps_py2.json es lo que hace el codigo original (Python 2.7)
contra el robot de mentira en cada escenario de tests/golden/app_cases.py.
Aca se corre el mismo escenario sobre el codigo migrado y se exige el mismo
registro: bytes por la UART, argumentos que recibe pico2wave, pedidos HTTP,
mails, datos en los FIFOs.

Los escenarios de DIVERGENCIAS son los unicos donde el resultado cambia. Cada
uno dice por que y verifica el resultado nuevo de forma explicita.
"""
import pytest

import apps_runner as ar

# scripts que todavia no se portaron: sus escenarios se saltean
PENDIENTES = set()


def tts_text(evts):
    """Textos que recibio pico2wave, sin la marca de volumen."""
    out = []
    for event in evts:
        if event.get("k") == "exec" and event["argv"][0] == "pico2wave":
            out.append(event["argv"][-1].split(">", 1)[1])
    return out


def kinds(evts, kind):
    return [e for e in evts if e.get("k") == kind]


def reason(evts):
    return kinds(evts, "exit")[0]["reason"]


# --- divergencias documentadas ------------------------------------------------

def _pid_despues_de_p(evts, out):
    assert [e["hex"] for e in kinds(evts, "serial_tx")] == ["FF 50 04 01 1A 02 10 84 FE"]
    assert reason(evts) == "sys.exit(None)"


def _texto_con_help(evts, out):
    assert kinds(evts, "fifo_total") == [{"k": "fifo_total", "pipe": "pipe_say", "data": " help me please"}]
    assert "Options:" not in out


def _listen_sin_qbotalk(evts, out):
    assert reason(evts) == "sys.exit(None)"
    assert kinds(evts, "serial_tx") == []
    assert "listen no disponible" in out


def _texto_literal(texto):
    def check(evts, out):
        assert tts_text(evts) == [texto]
        # nada mas que QBO_listen, pico2wave y aplay: no se ejecuto el texto
        assert [e["argv"][0] for e in kinds(evts, "exec")] == ["QBO_listen", "pico2wave", "aplay", "QBO_listen"]
    return check


def _ultimo_tts(evts, texto):
    assert tts_text(evts)[-1] == texto
    assert reason(evts) == "end"
    assert {e["argv"][0] for e in kinds(evts, "exec")} == {"pico2wave", "aplay"}


_INYECCION = ("py2 armaba el comando con comillas dobles y shell=True: la shell "
              "interpretaba el texto. Ahora llega literal a pico2wave")
_SAY = {name: text for name, text, _lang in ar.app_cases.SAY_TEXTS}

DIVERGENCIAS = {
    "PiCmd args: -c pid -p 26 2 16 -x 1": (
        "py2 desincronizaba el indice despues de -p y moria con IndexError (d0e07b4 lo arreglo)",
        _pid_despues_de_p),
    "PiCmd args: -c say -t help me please": (
        "py2 trataba la palabra 'help' del texto como la opcion de ayuda y no decia nada",
        _texto_con_help),
    "PiCmd args: -c listen": (
        "py2 moria con NameError: Qbo nunca se inicializa en PiCmd.py",
        _listen_sin_qbotalk),
    "say: comillas dobles": (_INYECCION, _texto_literal(_SAY["comillas dobles"])),
    "say: sustitucion de comandos": (_INYECCION, _texto_literal(_SAY["sustitucion de comandos"])),
    "say: backticks": (_INYECCION, _texto_literal(_SAY["backticks"])),
    "say: variable de shell": (_INYECCION, _texto_literal(_SAY["variable de shell"])),
    "tooly: respuesta con caracteres de shell": (
        _INYECCION + ". En py2 la respuesta del LLM ejecutaba `echo boo` en el robot",
        lambda evts, out: _ultimo_tts(evts, "It costs $5 `echo boo` and $(echo more); ok")),
    "tooly: respuesta con comillas dobles": (
        _INYECCION + ". En py2 pico2wave recibia la frase partida en dos argumentos",
        lambda evts, out: _ultimo_tts(evts, 'She said "carpe diem" to me')),
    "say: largo 300 bytes": (
        "py2 leia 100 bytes del FIFO y tiraba el resto",
        _texto_literal(_SAY["largo 300 bytes"])),
}

ACTIVOS = [n for n, c in ar.CASES.items() if c["script"] not in PENDIENTES]


def test_el_golden_cubre_todos_los_casos():
    assert sorted(ar.GOLDEN) == sorted(ar.CASES)
    assert set(DIVERGENCIAS) <= set(ar.CASES)


def test_el_golden_muestra_la_inyeccion_de_shell_del_original():
    # si alguien regenera el golden contra el codigo nuevo, esto cambia
    assert tts_text(ar.golden("say: sustitucion de comandos")[0]) == ["son cinco pesos"]
    assert reason(ar.golden("PiCmd args: -c listen")[0]) == "EXC NameError"


@pytest.mark.parametrize("name", [n for n in ACTIVOS if n not in DIVERGENCIAS])
def test_identico_a_python2(name, tmp_path):
    got, _out = ar.run(name, tmp_path)
    expected, _ = ar.golden(name)
    assert ar.lines(got) == ar.lines(expected)


@pytest.mark.parametrize("name", [n for n in ACTIVOS if n in DIVERGENCIAS])
def test_divergencia_documentada(name, tmp_path):
    motivo, check = DIVERGENCIAS[name]
    got, out = ar.run(name, tmp_path)
    expected, _ = ar.golden(name)
    assert got != expected, "ya no diverge: sacar %r de DIVERGENCIAS" % name
    assert reason(got) != "timeout", out
    check(got, out)


def _salida_comparable(out):
    """Lo que imprime PiCmd es su interfaz. Se ignora el volcado de config."""
    return [l.rstrip() for l in out.splitlines() if not l.startswith("CONFIG ")]


# mismos eventos que py2, pero otro texto en pantalla
SALIDA_DISTINTA = {
    "PiCmd args: -c say -t Hola -l spanish": (
        "py2 desincronizaba el indice despues de -t y al llegar a -l imprimia "
        "'laguage param error'. El texto dicho es el mismo",
        ["Open serial port sucessfully.", "/dev/serial0", "Opening FIFO...<QBO>/pipes/pipe_say",
         "Saying:  Hola"]),
}


@pytest.mark.parametrize("name", [n for n in ACTIVOS if n.startswith("PiCmd") and n not in DIVERGENCIAS])
def test_picmd_imprime_lo_mismo(name, tmp_path):
    _got, out = ar.run(name, tmp_path)
    if name in SALIDA_DISTINTA:
        assert "laguage param error" in ar.golden(name)[1]
        assert _salida_comparable(out) == SALIDA_DISTINTA[name][1]
    else:
        assert _salida_comparable(out) == _salida_comparable(ar.golden(name)[1])


def test_pendientes_al_dia():
    """La lista de pendientes solo puede achicarse."""
    import os
    for script in PENDIENTES:
        path = os.path.join(ar.ROOT, ar.app_cases.SCRIPTS[script][1])
        with open(path, "rb") as fh:
            try:
                compile(fh.read(), path, "exec")
            except SyntaxError:
                continue
        pytest.fail("%s ya compila en Python 3: sacarlo de PENDIENTES" % script)


def test_tooly_usa_camera_index_de_config(tmp_path):
    """En Raspbian 13 la segunda camara USB es el indice 2, no el 1."""
    name = "tooly: servidor LLM caido, modo repetir"
    scenario = dict(ar.CASES[name]["scenario"], config={"camera_index": 2})
    got, out = ar.run(name, tmp_path, scenario=scenario)
    assert [e["index"] for e in kinds(got, "cam_open")] == [2], out
    assert [e["index"] for e in kinds(ar.golden(name)[0], "cam_open")] == [1]
