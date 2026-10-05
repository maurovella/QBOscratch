#!/usr/bin/env python3


import os
import sys
# raiz del repo en sys.path, para importar el paquete qbo sin instalarlo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multiprocessing import Process, Queue
import time
import fileinput
import readline
import serial

#import cv2
#import binascii
from qbo import protocol as QboCmd
from qbo import paths
import sys
import os
import errno
import yaml
import pdb

# FIFO init.
FIFO_cmd = paths.pipe("pipe_cmd")

# scan stdin and send to pipe_cmd
if len(sys.argv) == 1: 
        line = ""
        while (1):
                idx = 0
                print("Opening FIFO...")
                line = input('QBO_>> ')
                with open(FIFO_cmd, 'w') as fifo:
                        print("FIFO opened")
                        print("line: ", line)
                        fifo.write(line)
                        if (line == "exit" or line == "quit"):
                                sys.exit()
                        fifo.close()
sys.exit()




#====================================================================================================

