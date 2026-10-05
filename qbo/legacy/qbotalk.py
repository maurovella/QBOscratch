#!/usr/bin/env python3

# NOTE: this example requires PyAudio because it uses the Microphone class

# install TTs google
# sudo pip install gTTS 

import speech_recognition as sr
import subprocess
import json
import apiai
import time
import yaml
import os
import wave
import shlex

from qbo import paths
from qbo import tts
# from gtts import gTTS

class QBOtalk:
    def __init__(self):
        config = yaml.safe_load(open(paths.CONFIG))

        CLIENT_ACCESS_TOKEN = config["tokenAPIai"]
        print("TOKEN: " + CLIENT_ACCESS_TOKEN)
#	You can enter your token in the next line
#        CLIENT_ACCESS_TOKEN = 'YOUR_TOKEN'
        # obtain audio from the microphone
        self.r = sr.Recognizer()
        self.ai = apiai.ApiAI(CLIENT_ACCESS_TOKEN)
        self.Response = "hello"
        self.GetResponse = False
        self.GetAudio = False
        self.strAudio = ""
        self.config = config
        
        self.m = None
        for i, mic_name in enumerate (sr.Microphone.list_microphone_names()):
            if(mic_name == "dmicQBO_sv"):
                self.m = sr.Microphone(i)
        if self.m is None:
            raise RuntimeError("Microfono 'dmicQBO_sv' no encontrado. Disponibles: "
                               + str(sr.Microphone.list_microphone_names()))
        with self.m as source:
            self.r.adjust_for_ambient_noise(source)

    def Decode(self, audio):
        try:
            # print(r.recognize_google(audio,language="es-ES"))

            if (self.config["language"] == "spanish"):
                    str = self.r.recognize_google(audio, language="es-ES")
            else:
                    str = self.r.recognize_google(audio)
            print("LISTEN: " + str)
            request = self.ai.text_request()
#	    request.lang = 'es'
            request.query = str
            response = request.getresponse()
            jsonresp = response.read()
            if isinstance(jsonresp, bytes):
                jsonresp = jsonresp.decode("utf-8")
            data = json.loads(jsonresp)
            str_resp = data["result"]["fulfillment"]["speech"]

        except sr.UnknownValueError:
            str_resp = ""
        except sr.RequestError as e:
            str_resp = "Could not request results from Speech Recognition service"
        except (KeyError, TypeError, ValueError):
            # la API v1 de Dialogflow (apiai) fue apagada por Google en 2020;
            # la respuesta ya no trae result.fulfillment.speech
            print("Decode: respuesta del NLU sin formato esperado (servicio apiai discontinuado)")
            str_resp = ""
        return str_resp

    def SpeechText(self, text_to_speech):
        self.config = yaml.safe_load(open(paths.CONFIG))
        print("config:" + str(self.config))

        # el texto viene del reconocimiento de voz: va a pico2wave como argumento, sin shell
        speak = " && ".join(shlex.join(c) for c in tts.commands(text_to_speech, self.config["language"], self.config["volume"]))

#        speak = "espeak -ven+f3 \"" + text_to_speech + "\" --stdout  | aplay -D convertQBO"

#       tts = gTTS(text = text_to_speech, lang = 'en')
#       tts.save("/home/pi/Documents/say.wav")
#       self.downsampleWav("/home/pi/Documents/say.wav")
#       self.downsampleWav("./say.wav", "./say16.wav", 8000, 16000, 1, 1)
#       downsampleWav("say.wav", "say16.wav")
#       os.system("aplay -D convertQBO say16.wav")
# hasta aqui

        print("QBOtalk: " + speak)
        result = tts.speak(text_to_speech, self.config["language"], self.config["volume"])
    

    def SpeechText_2(self, text_to_speech, text_spain):
        self.config = yaml.safe_load(open(paths.CONFIG))
        print("config:" + str(self.config))
        if (self.config["language"] == "spanish"):
                text = text_spain
        else:
                text = text_to_speech
        speak = " && ".join(shlex.join(c) for c in tts.commands(text, self.config["language"], self.config["volume"]))

        print("QBOtalk_2: " + speak)
        result = tts.speak(text, self.config["language"], self.config["volume"])
    
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
#	    with open("microphone-results.wav", "wb") as f:
#    		f.write(audio.get_wav_data())
            if (self.config["language"] == "spanish"):
                    self.strAudio = self.r.recognize_google(audio, language="es-ES")
            else:
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
            audio = self.r.listen(source = source, timeout = 2)

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

 
#qbo = QBOtalk()
#qbo.Start()

#while True:
#    print("start background listening")

#    listen_thd = qbo.StartBack()

#    for _ in range(100):
#        if qbo.GetResponse:
#            listen_thd(wait_for_stop = True)
#            qbo.SpeechText(qbo.Response)
#            qbo.GetResponse = False
#            break
#        time.sleep(0.1)
#    print("End listening")

