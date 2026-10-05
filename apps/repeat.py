#!/usr/bin/env python3

# NOTE: this example requires PyAudio because it uses the Microphone class

# install TTs google
# sudo pip install gTTS 

import os
import sys
# raiz del repo en sys.path, para importar el paquete qbo sin instalarlo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import speech_recognition as sr
import subprocess
import json
import time
import yaml
import os
import wave
import shlex
# from gtts import gTTS

from qbo import paths
from qbo import tts

class QBOtalk:
    def __init__(self):
        config = yaml.safe_load(open(paths.CONFIG))
        # obtain audio from the microphone
        self.r = sr.Recognizer()
        self.Response = "hello"
        self.GetResponse = False
        self.GetAudio = False
        self.strAudio = ""
        self.config = config
        
        for i, mic_name in enumerate (sr.Microphone.list_microphone_names()):
            if(mic_name == "dmicQBO_sv"):
                self.m = sr.Microphone(i)
        with self.m as source:        
            self.r.adjust_for_ambient_noise(source)

    def Decode(self, audio):
        try:

            if (self.config["language"] == "spanish"):
                    str = self.r.recognize_google(audio, language="es-ES")
            else:
                    str = self.r.recognize_google(audio)
            print("LISTEN: " + str)
        except sr.UnknownValueError:
            str = ""
        except sr.RequestError as e:
            str = "Could not request results from Speech Recognition service"
        return str

    def SpeechText(self, text_to_speech):
        self.config = yaml.safe_load(open(paths.CONFIG))
        print("config:" + str(self.config))

        text, volume = text_to_speech, self.config["volume"]
        speak = " && ".join(shlex.join(c) for c in tts.commands(text, self.config["language"], volume))

#        speak = "espeak -ven+f3 \"" + text_to_speech + "\" --stdout  | aplay -D convertQBO"

#       tts = gTTS(text = text_to_speech, lang = 'en')
#       tts.save("/home/pi/Documents/say.wav")
#       self.downsampleWav("/home/pi/Documents/say.wav")
#       self.downsampleWav("./say.wav", "./say16.wav", 8000, 16000, 1, 1)
#       downsampleWav("say.wav", "say16.wav")
#       os.system("aplay -D convertQBO say16.wav")
# hasta aqui

        print("QBOtalk: " + speak)
        result = tts.speak(text, self.config["language"], volume)
    

    def SpeechText_2(self, text_to_speech, text_spain):
        self.config = yaml.safe_load(open(paths.CONFIG))
        print("config:" + str(self.config))
        if (self.config["language"] == "spanish"):
            text, volume = text_spain, self.config["volume"]
        else:
            text, volume = text_to_speech, self.config["volume"]
        speak = " && ".join(shlex.join(c) for c in tts.commands(text, self.config["language"], volume))

        print("QBOtalk_2: " + speak)
        result = tts.speak(text, self.config["language"], volume)
    
    def callback(self, recognizer, audio):
        try:
            self.Response = self.Decode(audio)
            self.GetResponse = True
            print("Google say ")
            #self.SpeechText(self.Response)
        except:
            return
        
    def callback_listen(self, recognizer, audio):
        print("callback listen")
        try:
            #strSpanish = self.r.recognize_google(audio,language="es-ES")
#           with open("microphone-results.wav", "wb") as f:
#               f.write(audio.get_wav_data())
            if (self.config["language"] == "spanish"):
                    self.strAudio = self.r.recognize_google(audio, language="es-ES")
            else:
                    self.strAudio = self.r.recognize_google(audio)

            self.strAudio = self.r.recognize_google(audio)
            self.GetAudio = True
            print("listen: " + self.strAudio)
            #print("listenSpanish: ", strSpanish)
            #self.SpeechText(self.Response)
        except:
            print("callback listen exception")
            self.strAudio = ""
            return

    def Start(self):
        print("Say something!")
        self.r.operation_timeout = 10
        with self.m as source:
            audio = self.r.listen(source = source, timeout = 10)

        # recognize speech using Google Speech Recognition

        Response = self.Decode(audio)
        self.SpeechText(Response)
        
    def StartBack(self):
        with self.m as source:
            self.r.adjust_for_ambient_noise(source)

        print("start background listening")

        return self.r.listen_in_background(self.m, self.callback)

    def StartBackListen(self):
        with self.m as source:
            self.r.adjust_for_ambient_noise(source)

        print("start background only listening")

        return self.r.listen_in_background(self.m, self.callback_listen)


 
qbo = QBOtalk()
while True:
    qbo.Start()
    time.sleep(0.1)

