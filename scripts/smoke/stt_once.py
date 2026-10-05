#!/usr/bin/env python3
"""Escucha una frase por el microfono del robot y la transcribe con Google.

    stt_once.py [segundos de espera]

Usa el mismo camino que Tooly: dispositivo ALSA 'dmicQBO_sv', SpeechRecognition
y recognize_google en el idioma de config.yml. Sale con 0 si hubo transcripcion.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import speech_recognition as sr  # noqa: E402
import yaml  # noqa: E402

from qbo import paths  # noqa: E402

MIC_NAME = "dmicQBO_sv"


def main(argv):
    timeout = float(argv[0]) if argv else 10
    with open(paths.CONFIG) as fh:
        config = yaml.safe_load(fh)
    names = sr.Microphone.list_microphone_names()
    if MIC_NAME not in names:
        print("FALLA: no existe el microfono '%s'. PortAudio ve: %s" % (MIC_NAME, names))
        print("Eso lo define /etc/asound.conf y depende de la tarjeta I2S (modulo my_loader).")
        return 1
    recognizer = sr.Recognizer()
    with sr.Microphone(names.index(MIC_NAME)) as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Deci algo (espero %d segundos)..." % timeout)
        try:
            audio = recognizer.listen(source, timeout=timeout)
        except sr.WaitTimeoutError:
            print("FALLA: no se oyo nada. Revisar el microfono con arecord (paso anterior).")
            return 1
    language = "es-ES" if config.get("language") == "spanish" else "en-US"
    try:
        text = recognizer.recognize_google(audio, language=language)
    except sr.UnknownValueError:
        print("FALLA: hubo audio pero Google no entendio nada (%s)." % language)
        return 1
    except sr.RequestError as exc:
        print("FALLA: no se pudo consultar a Google: %s. Revisar la conexion a internet." % exc)
        return 1
    print("transcripcion (%s): %s" % (language, text))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
