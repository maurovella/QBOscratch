#!/usr/bin/env python3

import os
import sys
# raiz del repo en sys.path, para importar el paquete qbo sin instalarlo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qbo import paths
from qbo import tts

import time
import fileinput
import sys
import os
import errno
import yaml
import subprocess


# read config file
config = yaml.safe_load(open(paths.CONFIG))
print("CONFIG " + str(config))

if (config["language"] == "spanish"):
        text = "Hola"
else:
        text = "Hello dear friends"
result = tts.speak(text, config["language"], config["volume"])
time.sleep(0.5)

if config["startWith"] == "scratch":
        if (config["language"] == "spanish"):
                text = "estoy en modo scratch."
        else:
                text = "I'm in scratch mode."

        result = tts.speak(text, config["language"], config["volume"])

        # User root
        with open(os.path.join(os.path.dirname(paths.HOME), "scratchMode.log"), "w") as log:
                result = subprocess.call([paths.daemon("QBO_scratch"), "start"], stdout=log, stderr=subprocess.STDOUT)

elif config["startWith"] == "interactive-dialogflow" or config["startWith"] == "interactive-gassistant":
        if (config["language"] == "spanish"):
                text = "estoy en modo interactivo. Un momento, por favor."
        else:
                text = "I'm in interactive mode. Please wait."

        result = tts.speak(text, config["language"], config["volume"])

        # User pi result = subprocess.call("/home/pi/Documents/deamonsScripts/QBO_PiFaceFast start > /home/pi/interactiveMode.log 2>&1", shell = True)

