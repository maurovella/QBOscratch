#!/usr/bin/env python3

import os
import sys
# raiz del repo en sys.path, para importar el paquete qbo sin instalarlo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multiprocessing import Process, Queue
import subprocess
import os
import errno
import time
import serial
import binascii
#import QboCmd
import sys
import time
import yaml
import shlex
from qbo import paths
from qbo import tts


def SayFromFile():
        print("Opening FIFO...")
        while True:
                fifo = os.open(FIFO_say, os.O_RDONLY)
                # leer hasta EOF y decodificar al final: un solo read(100)
                # podia truncar el mensaje o partir un caracter UTF-8
                raw = b""
                while True:
                        chunk = os.read(fifo, 4096)
                        if not chunk:
                                break
                        raw += chunk
                os.close(fifo)
                data = raw.decode("utf-8", errors="replace")

                if data:
                        config = yaml.safe_load(open(paths.CONFIG))
 
                        print('Read: "{0}"'.format(data))
                        # el texto viene del FIFO: va a pico2wave como argumento, sin shell
                        speak = " && ".join(shlex.join(c) for c in tts.commands(data, config["language"], config["volume"]))

                        print("say.py: " + speak)
#
#	                if config["languaje"] == "english":
#		        	speak = "espeak -ven+f3 \"" + data + "\" --stdout  | aplay -D convertQBO"
#               	elif config["languaje"] == "spanish":
#		        	speak = "espeak -v mb-es2 -s 120 \"" + data + "\" --stdout  | aplay -D convertQBO"
                        print("say.py: " + speak)
                        
                        result = subprocess.call([paths.daemon("QBO_listen"), "stop"])
                        result = tts.speak(data, config["language"], config["volume"])
                        result = subprocess.call([paths.daemon("QBO_listen"), "start"])

#============================================================================================================

FIFO_say = paths.pipe("pipe_say")

#
#try:
#    os.mkfifo(FIFO_say)
#except OSError as oe: 
#    if oe.errno != errno.EEXIST:
#        raise

while True:
        SayFromFile()
