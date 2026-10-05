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
from qbo.legacy import qbotalk as QBOtalk
from qbo import paths

Qbo = QBOtalk.QBOtalk()

Listenig = True
listen_thd = 0


def SayFromFifo():
        print("Opening FIFO...")
        fifo = os.open(FIFO_say, os.O_RDONLY | os.O_NONBLOCK)
        # leer hasta EOF/EAGAIN y decodificar al final: un solo read(100)
        # podia truncar el mensaje o partir un caracter UTF-8
        raw = b""
        try:
                while True:
                        chunk = os.read(fifo, 4096)
                        if not chunk:
                                break
                        raw += chunk
        except OSError as oe:
                if oe.errno != errno.EAGAIN:
                        raise

        os.close(fifo)
        data = raw.decode("utf-8", errors="replace")

        if data:
                config = yaml.safe_load(open(paths.CONFIG))

                print('Read: "{0}"'.format(data))
                # shlex.quote: el texto viene del FIFO; sin escapar,
                # una comilla rompe el comando (inyeccion de shell)
                if config["language"] == "spanish":
                        speak = "espeak -v mb-es2 -s 120 " + shlex.quote(data) + " --stdout  | aplay -D convertQBO"
                else:
                        speak = "espeak -ven+f3 " + shlex.quote(data) + " --stdout  | aplay -D convertQBO"
                print("Talk: " + speak)
                result = subprocess.call(speak, shell = True)



def WaitForSpeech():
        global Listenig, listen_thd, FIFO_listen, FIFO_cmd
        if Listenig == False:
                return
        elif Qbo.GetAudio == True:
#                HeadServo.SetNoseColor(0)       #Off QBO nose brigth
                fifo = os.open(FIFO_cmd, os.O_WRONLY)
                os.write(fifo, b"-c nose -co red")
                os.close(fifo)
                listen_thd(wait_for_stop = True)
                print("Ha llegado algo al WaitForSpeech: " + Qbo.strAudio)
                fifo = os.open(FIFO_listen, os.O_WRONLY)
                os.write(fifo, Qbo.strAudio.encode())
                os.close(fifo)
        return


#============================================================================================================

#Qbo.SpeechText("I am ready.")
# FIFO init.
FIFO_listen = paths.pipe("pipe_listen")
FIFO_say = paths.pipe("pipe_say")
FIFO_cmd = paths.pipe("pipe_cmd")

try:
    os.mkfifo(FIFO_listen)
except OSError as oe: 
    if oe.errno != errno.EEXIST:
        raise
try:
    os.mkfifo(FIFO_cmd)
except OSError as oe: 
    if oe.errno != errno.EEXIST:
        raise

listen_thd = Qbo.StartBackListen()
#HeadServo.SetNoseColor(1)       # Set QBO nose green
fifo = os.open(FIFO_cmd, os.O_WRONLY)
os.write(fifo, b"-c nose -co green")
os.close(fifo)


while True:
        SayFromFifo()
        WaitForSpeech()
        if Qbo.GetAudio == True:
            fifo = os.open(FIFO_cmd, os.O_WRONLY)
            os.write(fifo, b"-c nose -co red")
            os.close(fifo)
            # HeadServo.SetNoseColor(0)       #Off QBO nose brigth
            time.sleep(1)
            print("StartBackListen")
            try:
                listen_thd = Qbo.StartBackListen()
#                HeadServo.SetNoseColor(1)       # Set QBO nose green
                fifo = os.open(FIFO_cmd, os.O_WRONLY)
                os.write(fifo, b"-c nose -co green")
                os.close(fifo)
                Qbo.GetAudio = False
            except:
                print("StartBackListe EXCEPTION")
