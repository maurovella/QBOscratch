# -*- coding: utf-8 -*-
"""Casos de punta a punta: un script del robot contra el robot de mentira.

Cada caso se corre dos veces con el mismo guion: sobre el codigo original en
Python 2.7 (Docker, tests/golden/generate.sh) y sobre el migrado. Lo que se
compara es el registro de eventos: bytes por la UART, comandos de TTS con sus
argumentos, pedidos HTTP, mails, datos en los FIFOs.

Compatible con Python 2.7 y 3.
"""
from __future__ import unicode_literals

# script logico -> (ruta en la rama legacy-python2, ruta actual)
SCRIPTS = {
    "PiCmd": ("Python projects/PiCmd.py", "apps/picmd.py"),
    "say": ("Python projects/say.py", "apps/say.py"),
    "feel": ("Python projects/feel.py", "apps/feel.py"),
    "findFace": ("Python projects/findFace.py", "apps/find_face.py"),
    "TrackAndTalk": ("Tooly/TrackAndTalk.py", "apps/tooly.py"),
    "llama2Connection": ("Tooly/llama2Connection.py", "apps/tooly_audio.py"),
    "repeat": ("Tooly/repeat.py", "apps/repeat.py"),
}

CASES = []


def case(name, script, args=(), scenario=None, env=None, cwd=None):
    CASES.append({"name": name, "script": script, "args": list(args),
                  "scenario": scenario or {}, "env": env or {}, "cwd": cwd})


# --- PiCmd.py con argumentos (los comandos del .bash_history del robot) --------

PICMD_LINES = [
    "-c nose -co red", "-c nose -co blue", "-c nose -co green", "-c nose -co none",
    "-c nose -co pink", "-c nose blue", "-c nose -e smile", "-c nose",
    "-c servo -a 30 -x 1 -s 200", "-c servo -s 100 -x 1 -a -10", "-c servo -a -90 -x 2 -s 200",
    "-c servo -a 90 -x 2", "-c servo -a 0 -x 1 -s 200", "-c servo -a 30 -x 0 -s 20",
    "-c servo -a 900 -x 1 -s 100", "-c servo -s 100 -x 1 -a 0.4", "-c servo -a 30 -x 1 -s 2000",
    "-c servo -a 120 -x 2 -s 1000", "-c servo -a", "-s 100 -x 1 -a 90",
    "-c move -a 100 -x 1", "-c move_rel -a -40 -x 2", "-c move_rel -a 40 -x 1",
    "-c mouth -e smile", "-c mouth -e sad", "-c mouth -e serious", "-c mouth -e love",
    "-c mouth -e wink", "-e smile", "-c mouth -m 0 17 14 0", "-c mouth -m 31 31",
    "-c pid -x 1 -p 26 2 16", "-c pid -p 26 2 16 -x 1", "-c pid -x 2 -p 26",
    "-c say -t Hola", "-c say -t Hola mundo cruel", "-c say -t Hola -l spanish",
    "-c say -t help me please", "-c say -t", "-c say",
    "-c voice -l spanish", "-c voice -l english", "-c voice -l klingon",
    "-c listen", "-c bailar", "?", "help", "-h", "--help", "-c",
]
for _line in PICMD_LINES:
    case("PiCmd args: " + _line, "PiCmd", _line.split(),
         scenario={"fifo_reads": ["pipe_say"]})

case("PiCmd por FIFO", "PiCmd", [], scenario={
    "fifo_reads": ["pipe_say"],
    "fifo_writes": [
        {"pipe": "pipe_cmd", "data": "-c nose -co red"},
        {"pipe": "pipe_cmd", "data": "-c servo -a 30 -x 1 -s 200"},
        {"pipe": "pipe_cmd", "data": "-c mouth -e smile"},
        {"pipe": "pipe_cmd", "data": "-c say -t Hola que tal"},
        {"pipe": "pipe_cmd", "data": "-c pid -x 1 -p 26 2 16"},
        {"pipe": "pipe_cmd", "data": "-c nose -co"},
        {"pipe": "pipe_cmd", "data": "-c move_rel -a -40 -x 2\n"},
        {"pipe": "pipe_cmd", "data": "exit"},
    ]})

# --- say.py: FIFO -> pico2wave + aplay -----------------------------------------

SAY_TEXTS = [
    ("ascii", "Hola mundo", "spanish"),
    ("ingles", "Hello dear friends", "english"),
    ("acentos", "¿Cómo estás, José? Mañana llueve", "spanish"),
    ("apostrofo", "it's a nice day", "english"),
    ("comillas dobles", 'dijo "hola" y se fue', "spanish"),
    ("sustitucion de comandos", "son $(echo cinco) pesos", "spanish"),
    ("backticks", "hora `echo cero`", "spanish"),
    ("variable de shell", "cuesta $5 o $HOME", "spanish"),
    ("punto y coma", "hola; echo chau", "spanish"),
    ("largo 300 bytes", " ".join(["palabra%02d" % i for i in range(33)]), "spanish"),
]
for _name, _text, _lang in SAY_TEXTS:
    case("say: " + _name, "say", [], scenario={
        "config": {"language": _lang, "volume": 100},
        "fifo_writes": [{"pipe": "pipe_say", "data": _text}],
        "stop": {"kind": "exec", "count": 4, "max_real_seconds": 4},
    })
case("say: volumen 250", "say", [], scenario={
    "config": {"language": "spanish", "volume": 250},
    "fifo_writes": [{"pipe": "pipe_say", "data": "probando volumen"}],
    "stop": {"kind": "exec", "count": 4, "max_real_seconds": 4},
})
case("say: dos mensajes", "say", [], scenario={
    "config": {"language": "english", "volume": 100},
    "fifo_writes": [{"pipe": "pipe_say", "data": "first"}, {"pipe": "pipe_say", "data": "second"}],
    "stop": {"kind": "exec", "count": 8, "max_real_seconds": 5},
})

# --- feel.py: sensor tactil -> FIFO --------------------------------------------

case("feel: derecha, arriba, izquierda", "feel", [], env={"FAKE_QBOARD": "1", "FAKE_TOUCH": "0,0,1,0,2,3,0,0"},
     scenario={"fifo_reads": ["pipe_feel"], "stop": {"kind": "serial_tx", "count": 8}})
case("feel: valores fuera de rango", "feel", [], env={"FAKE_QBOARD": "1", "FAKE_TOUCH": "4,7,255,1"},
     scenario={"fifo_reads": ["pipe_feel"], "stop": {"kind": "serial_tx", "count": 5}})

# --- findFace.py: camara -> FIFO -------------------------------------------------

FACE = [130, 90, 60, 60]          # centrada en 320x240
case("findFace: frontal, perfil y nada", "findFace", [], cwd="script", scenario={
    "fifo_reads": ["pipe_findFace"],
    "faces": [[FACE], [[15, 7, 61, 61]], [], [[200, 100, 81, 45]], [], [], [], [], [], [], [], [[1, 2, 3, 5]]],
    "stop": {"kind": "detect", "count": 16},
})

# --- Tooly (TrackAndTalk.py) ------------------------------------------------------

HELLO = {"status": 200, "json": {"conversation_id": "conv-1"}}


def answer(text):
    return {"status": 200, "json": {"conversation_id": "conv-1", "response": text}}


BOARD = {"FAKE_QBOARD": "1"}

case("tooly: dos turnos de conversacion", "TrackAndTalk", [], env=BOARD, scenario={
    "frames": 60,
    "faces": [[FACE]] + [[]] * 50 + [[FACE]],
    "listens": ["audio", "audio"],
    "stt": ["hello tooly", "what is your name"],
    "http": [HELLO, answer("Hi, I am Tooly"), answer("Nice to meet you"), answer("My name is Tooly")],
})

case("tooly: la cabeza sigue la cara", "TrackAndTalk", [], env=BOARD, scenario={
    "frames": 9,
    "faces": [[[200, 100, 60, 60]], [[15, 7, 61, 61]], [[250, 180, 45, 45]], [[0, 0, 60, 60]],
              [[259, 179, 61, 61]], [[141, 101, 59, 59]], [[100, 90, 61, 61]], [FACE]],
    "listens": ["audio"],
    "stt": ["hi"],
    "http": [HELLO, answer("Hello"), answer("Hi there")],
})

case("tooly: servidor LLM caido, modo repetir", "TrackAndTalk", [], env=BOARD, scenario={
    "frames": 3,
    "faces": [[FACE]],
    "listens": ["audio"],
    "stt": ["repeat after me"],
    "http": [{"raise": "ConnectionError"}],
})

case("tooly: servidor LLM responde 503", "TrackAndTalk", [], env=BOARD, scenario={
    "frames": 3,
    "faces": [[FACE]],
    "listens": ["audio"],
    "stt": ["are you there"],
    "http": [{"status": 503, "json": None}],
})

case("tooly: caricia en la cabeza", "TrackAndTalk", [],
     env={"FAKE_QBOARD": "1", "FAKE_TOUCH": "0,1,0,0"}, scenario={
    "frames": 3,
    "faces": [[FACE]],
    "listens": ["audio"],
    "stt": ["thank you"],
    "http": [HELLO, answer("Hello"), answer("I like it when you pet me"), answer("You are welcome")],
})

case("tooly: cuatro horas de silencio y alerta por mail", "TrackAndTalk", [], env=BOARD, scenario={
    "frames": 3,
    "faces": [[FACE]],
    "listens": [],
    "listens_long": ["timeout", "timeout", "audio"],
    "stt": ["I am fine"],
    "http": [HELLO, answer("Hello"), answer("Good to hear that")],
})

case("tooly: pide ayuda", "TrackAndTalk", [], env=BOARD, scenario={
    "frames": 3,
    "faces": [[FACE]],
    "listens": ["audio"],
    "listens_long": ["audio"],
    "stt": ["help", "false alarm"],
    "http": [HELLO, answer("Hello"), answer("Glad you are ok")],
})

case("tooly: falla el reconocimiento de voz", "TrackAndTalk", [], env=BOARD, scenario={
    "frames": 3,
    "faces": [[FACE]],
    "listens": ["audio", "audio"],
    "stt": [{"raise": "UnknownValueError"}, {"raise": "RequestError"}],
    "http": [HELLO, answer("Hello"), answer("Sorry?")],
})

case("tooly: en castellano con acentos", "TrackAndTalk", [], env=BOARD, scenario={
    "config": {"language": "spanish", "volume": 120},
    "frames": 3,
    "faces": [[FACE]],
    "listens": ["audio"],
    "stt": ["hola, ¿cómo estás?"],
    "http": [HELLO, answer("¡Hola! Soy Tooly"), answer("Muy bien, ¿y vos? Mañana será otro día")],
})

case("tooly: respuesta con caracteres de shell", "TrackAndTalk", [], env=BOARD, scenario={
    "frames": 3,
    "faces": [[FACE]],
    "listens": ["audio"],
    "stt": ["how much is it"],
    "http": [HELLO, answer("Hello"), answer("It costs $5 `echo boo` and $(echo more); ok")],
})

case("tooly: respuesta con comillas dobles", "TrackAndTalk", [], env=BOARD, scenario={
    "frames": 3,
    "faces": [[FACE]],
    "listens": ["audio"],
    "stt": ["tell me a quote"],
    "http": [HELLO, answer("Hello"), answer('She said "carpe diem" to me')],
})

# --- variantes sin camara ---------------------------------------------------------

case("tooly_audio: un turno", "llama2Connection", [], env=BOARD, scenario={
    "listens": ["audio"],
    "stt": ["good morning"],
    "http": [HELLO, answer("Hello"), answer("Good morning to you")],
    "stop": {"kind": "exec", "count": 4, "max_real_seconds": 5},
})

case("repeat: repite lo que oye", "repeat", [], scenario={
    "listens": ["audio", "audio"],
    "stt": ["one two three", "testing"],
    "stop": {"kind": "exec", "count": 4, "max_real_seconds": 5},
})
