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

# fichero config, contiene languaje
config = yaml.safe_load(open(paths.CONFIG))
print("CONFIG " + str(config))

if (config["language"] == "spanish"):
        text = "Adíos"
else:
        text = "Good bye"
result = tts.speak(text, config["language"], config["volume"])
time.sleep(0.5)

with open(os.path.join(os.path.dirname(paths.HOME), "sampleStop.log"), "w") as log:
    result = subprocess.call([paths.daemon("QBO_scratch"), "stop"], stdout=log, stderr=subprocess.STDOUT)

