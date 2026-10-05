# -*- coding: utf-8 -*-
"""Bordes de los FIFOs de /home/pi/Documents/pipes: fugas, bloqueos y texto.

Los daemons del modo Scratch se hablan por FIFOs con nombre. En Python 3
os.read/os.write manejan bytes, y un descriptor sin cerrar por mensaje agota
el limite del proceso en unas horas.
"""
import apps_runner as ar
from test_apps_golden import kinds, reason, tts_text

FDS = {"FAKE_COUNT_FDS": "1"}


def open_fds(evts):
    return kinds(evts, "open_fds")[0]["n"]


def fifo(evts, pipe):
    return {e["pipe"]: e["data"] for e in kinds(evts, "fifo_total")}.get(pipe, "")


def run(script, tmp_path, scenario, env=None):
    extra = dict(FDS)
    extra.update(env or {})
    return ar.run_script(script, tmp_path, scenario=scenario, extra_env=extra)


def feel(tmp_path, touches):
    scenario = {"fifo_reads": ["pipe_feel"], "stop": {"kind": "serial_tx", "count": len(touches) + 1}}
    env = {"FAKE_QBOARD": "1", "FAKE_TOUCH": ",".join(str(t) for t in touches)}
    return run("apps/feel.py", tmp_path, scenario, env)


def test_feel_no_pierde_descriptores(tmp_path):
    pocos, _ = feel(tmp_path / "a", [1, 2])
    muchos, out = feel(tmp_path / "b", [1, 2, 3] * 40)
    assert fifo(muchos, "pipe_feel").count("Touch:") == 120, out
    assert open_fds(muchos) == open_fds(pocos)


def test_find_face_no_pierde_descriptores(tmp_path):
    def corrida(carpeta, n):
        scenario = {"fifo_reads": ["pipe_findFace"], "faces": [[[130, 90, 60, 60]]] * n,
                    "stop": {"kind": "detect", "count": n + 1}}
        return run("apps/find_face.py", tmp_path / carpeta, scenario)
    pocos, _ = corrida("a", 2)
    muchos, out = corrida("b", 100)
    assert fifo(muchos, "pipe_findFace") == "160,120\n" * 100, out
    assert open_fds(muchos) == open_fds(pocos)


def test_picmd_por_fifo_no_pierde_descriptores(tmp_path):
    def corrida(carpeta, n):
        writes = [{"pipe": "pipe_cmd", "data": "-c say -t mensaje %d" % i, "pause": 0.05} for i in range(n)]
        writes.append({"pipe": "pipe_cmd", "data": "exit", "pause": 0.05})
        return run("apps/picmd.py", tmp_path / carpeta, {"fifo_reads": ["pipe_say"], "fifo_writes": writes})
    pocos, _ = corrida("a", 2)
    muchos, out = corrida("b", 40)
    assert reason(muchos) == "sys.exit(None)", out
    assert fifo(muchos, "pipe_say") == "".join(" mensaje %d" % i for i in range(40))
    assert open_fds(muchos) == open_fds(pocos)


def test_say_no_pierde_descriptores(tmp_path):
    def corrida(carpeta, n):
        writes = [{"pipe": "pipe_say", "data": "frase %d" % i, "pause": 0.05} for i in range(n)]
        return run("apps/say.py", tmp_path / carpeta,
                   {"fifo_writes": writes, "stop": {"kind": "exec", "count": 4 * n, "max_real_seconds": 15}})
    pocos, _ = corrida("a", 2)
    muchos, out = corrida("b", 25)
    assert tts_text(muchos) == ["frase %d" % i for i in range(25)], out
    assert open_fds(muchos) == open_fds(pocos)


def test_acentos_de_punta_a_punta_por_los_fifos(tmp_path):
    """pipe_cmd -> PiCmd -> pipe_say, con texto que no es ASCII."""
    texto = "¿Cómo estás, José? Mañana será otro día"
    writes = [{"pipe": "pipe_cmd", "data": "-c say -t " + texto}, {"pipe": "pipe_cmd", "data": "exit"}]
    got, out = run("apps/picmd.py", tmp_path, {"fifo_reads": ["pipe_say"], "fifo_writes": writes})
    assert fifo(got, "pipe_say") == " " + texto, out


def test_say_recibe_un_caracter_partido_entre_dos_lecturas(tmp_path):
    """Un mensaje largo con acentos llega entero aunque el FIFO lo entregue en trozos."""
    texto = "ñandú " * 900          # 6300 bytes en UTF-8, mas que un read() de 4096
    scenario = {"config": {"language": "spanish"}, "fifo_writes": [{"pipe": "pipe_say", "data": texto}],
                "stop": {"kind": "exec", "count": 4, "max_real_seconds": 5}}
    got, out = run("apps/say.py", tmp_path, scenario)
    assert tts_text(got) == [texto]
    assert "�" not in tts_text(got)[0]


def test_say_sigue_despues_de_un_escritor_que_abre_y_cierra_sin_escribir(tmp_path):
    scenario = {"fifo_writes": [{"pipe": "pipe_say", "data": ""}, {"pipe": "pipe_say", "data": "hola"}],
                "stop": {"kind": "exec", "count": 4, "max_real_seconds": 5}}
    got, out = run("apps/say.py", tmp_path, scenario)
    assert reason(got) == "stop", out
    assert tts_text(got) == ["hola"]


def test_picmd_say_sin_say_corriendo_se_queda_esperando(tmp_path):
    """Comportamiento original que se conserva: abrir pipe_say para escribir
    bloquea hasta que say.py lo abra para leer. Si say.py no esta corriendo,
    PiCmd no vuelve. Este test lo deja documentado; no es un arreglo."""
    scenario = {"stop": {"max_real_seconds": 1.5}}
    got, out = ar.run_script("apps/picmd.py", tmp_path, scenario=scenario, args=["-c", "say", "-t", "Hola"])
    assert reason(got) == "timeout"
    assert "Opening FIFO" in out
