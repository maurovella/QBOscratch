#!/usr/bin/env python2.7

# NOTE: this example requires PyAudio because it uses the Microphone class

# install TTs google
# sudo pip install gTTS 

import speech_recognition as sr
import subprocess
import pipes
import json
import apiai
import time
import yaml
import os
import wave
import requests
import pet
import emailSender as es
import multiprocessing
import threading
from email.mime.text import MIMEText
# from gtts import gTTS

#url_requests = "http://pf-2023a-tooly.it.itba.edu.ar"



url = "http://pf-2023a-tooly.it.itba.edu.ar"
class QBOtalk:
    def __init__(self):
	config = yaml.safe_load(open("/home/pi/Documents/config.yml"))
        # obtain audio from the microphone
        self.r = sr.Recognizer()
        self.Response = "hello"
        self.GetResponse = False
        self.GetAudio = False
        self.strAudio = ""
	self.config = config
	self.email = False
	self.touch = False
	self.lock = threading.Lock()
        
        for i, mic_name in enumerate (sr.Microphone.list_microphone_names()):
            if(mic_name == "dmicQBO_sv"):
                self.m = sr.Microphone(i)
        with self.m as source:        
            self.r.adjust_for_ambient_noise(source)

    def Decode(self, audio):
        try:
            with self.lock:
                if (self.config["language"] == "spanish"):
                    str = self.r.recognize_google(audio, language="es-ES")
                else:
                    str = self.r.recognize_google(audio)
                print "LISTEN: " + str
        except sr.UnknownValueError:
            str = ""
        except sr.RequestError as e:
            str = "Could not request results from Speech Recognition service"
        return str

    def downsampleWav(self, src):
	print "src: " + src
        s_read = wave.open(src, 'r')
	print "frameRate: " + s_read.getframerate()
	s_read.setframerate(16000)
	print "frameRate_2: " + s_read.getframerate()
	return


    def downsampleWave_2(self, src, dst, inrate, outrate, inchannels, outchannels):
        if not os.path.exists(src):
            print 'Source not found!'
            return False

        if not os.path.exists(os.path.dirname(dst)):
	    print "dst: " + dst
	    print "path: " + os.path.dirname(dst)
            os.makedirs(os.path.dirname(dst))

        try:
            s_read = wave.open(src, 'r')
            s_write = wave.open(dst, 'w')
        except:
            print 'Failed to open files!'
            return False

        n_frames = s_read.getnframes()
        data = s_read.readframes(n_frames)

        try:
            converted = audioop.ratecv(data, 2, inchannels, inrate, outrate, None)
            if outchannels == 1:
                converted = audioop.tomono(converted[0], 2, 1, 0)
        except:
            print 'Failed to downsample wav'
            return False

        try:
            s_write.setparams((outchannels, 2, outrate, 0, 'NONE', 'Uncompressed'))
            s_write.writeframes(converted)
        except:
            print 'Failed to write wav'
            return False

        try:
            s_read.close()
            s_write.close()
        except:
            print 'Failed to close wav files'
            return False

        return True

    def SpeechText(self, text_to_speech):
        with self.lock:
            self.config = yaml.safe_load(open("/home/pi/Documents/config.yml"))
            print "config:" + str(self.config)

            if (self.config["language"] == "spanish"):
                speak = "pico2wave -l \"es-ES\" -w /home/pi/Documents/pico2wave.wav \"<volume level='" + str(self.config["volume"]) + "'>" + text_to_speech + "\" && aplay -D convertQBO /home/pi/Documents/pico2wave.wav"
    #               speak = "pico2wave -l \"es-ES\" -w /var/local/pico2wave.wav \"" + text_to_speech + "\" | aplay -D convertQBO"
            else:
                speak = "pico2wave -l \"en-US\" -w /home/pi/Documents/pico2wave.wav \"<volume level='" + str(40) + "'>" + text_to_speech + "\" && aplay -D convertQBO /home/pi/Documents/pico2wave.wav"
    #               speak = "pico2wave -l \"en-US\" -w /var/local/pico2wave.wav \"" + text_to_speech + "\" | aplay -D convertQBO"

#        speak = "espeak -ven+f3 \"" + text_to_speech + "\" --stdout  | aplay -D convertQBO"

#       tts = gTTS(text = text_to_speech, lang = 'en')
#       tts.save("/home/pi/Documents/say.wav")
#       self.downsampleWav("/home/pi/Documents/say.wav")
#       self.downsampleWav("./say.wav", "./say16.wav", 8000, 16000, 1, 1)
#       downsampleWav("say.wav", "say16.wav")
#       os.system("aplay -D convertQBO say16.wav")
# hasta aqui

            print "QBOtalk: " + speak.encode('utf-8')
            result = subprocess.call(speak, shell = True)
    

    def SpeechText_2(self, text_to_speech, text_spain):
	self.config = yaml.safe_load(open("/home/pi/Documents/config.yml"))
	print "config:" + str(self.config)
	if (self.config["language"] == "spanish"):
	    speak = "pico2wave -l \"es-ES\" -w /home/pi/Documents/pico2wave.wav \"<volume level='" + str(self.config["volume"]) + "'>" + text_spain + "\" && aplay -D convertQBO /home/pi/Documents/pico2wave.wav"
	else:
            speak = "pico2wave -l \"en-US\" -w /home/pi/Documents/pico2wave.wav \"<volume level='" + str(self.config["volume"]) + "'>" + text_to_speech + "\" && aplay -D convertQBO /home/pi/Documents/pico2wave.wav"

        print "QBOtalk_2: " + speak.encode('utf-8')
	result = subprocess.call(speak, shell = True)
    
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

            self.strAudio = self.r.recognize_google(audio)
	    self.GetAudio = True
            print("listen: " + self.strAudio)
            #print("listenSpanish: ", strSpanish)
            #self.SpeechText(self.Response)
        except:
            print("callback listen exception")
            self.strAudio = ""
            return


    def Llama2Connect(self):
        print("llamaaaaaa2Connect")
        data_requests = {
            "ckpt_dir": "llama-2-7b-chat",
            "tokenizer_path": "tokenizer.model"
        }
        url_hello = url + "/tooly_hello/"
        response = requests.post(url_hello, json=data_requests)
        print(response.text)
        if response.status_code == 200:
            conv_id = response.json()["conversation_id"]
            
            return conv_id
        else:
            print(response)

    def Llama2(self, conv_id, msg):
        url_tooly = url + "/tooly/"
        data_requests = {
            "conversation_id": conv_id,
            "message": {
                "content": msg
            }
        }
        response = requests.post(url_tooly, json=data_requests)
        return response.json()["response"]
    
    def pet_detection(self, conv_id):
            if not self.touch:
                #if not self.lock.locked():
                touch = pet.WaitForTouch()
                if touch:
                    self.touch = True
                    petResponse = self.Llama2(conv_id, "I pet you in your robot head")
                    self.SpeechText(petResponse)
                    pet.TurnOffEmotion()
                    pet.CleanPet()
                    
            #threading.Timer(10,self.pet_detection(conv_id)).start()
    
    def listen_for_audio(self, timeout = 10):
            print("Say something!")
            try:
                with self.m as source:
                    audio = self.r.listen(source = source, timeout = timeout)
            except Exception as e:
                return None
            return audio

    
    def Start(self, conv_id):
        self.touch = False  
        email = False
        self.pet_detection(conv_id)
        #pet_thread =  threading.Thread(target=self.pet_detection, args=(conv_id,))
        #pet_thread.deamon = True
        #pet_thread.start()
        print(self.r.energy_threshold)
        print(self.r.pause_threshold)
        self.r.operation_timeout = 1000
        timeout = 1000
        wait_time = 4*3600
        #wait_time = 20
        start_time = time.time()
        audio = self.listen_for_audio()
        
        response = self.Decode(audio) if audio else None
        while((response == None or response == "" ) and (time.time() - start_time) < wait_time):
            self.pet_detection(conv_id)
            time.sleep(5)
            self.pet_detection(conv_id)
            audio = self.listen_for_audio()
            response = self.Decode(audio) if audio else None
        
        if((response == None or response == "" ) and self.touch == True ):
            audio = self.listen_for_audio()
            response = self.Decode(audio, timeout) if audio else None
            self.touch = False
            
        if (((response == None or response == "" ) and self.touch == False) or response == "help" ):
            self.pet_detection(conv_id)
            self.SpeechText("Is everething okey? If you dont respond, I'm going to notify your relatives")
            audio = self.listen_for_audio(timeout)
            response = self.Decode(audio) if audio else None
            first = True
            while(((response == None or response == "") and self.touch == False) or response == "help" ):
                self.SpeechText("I am notifying your relatives to check that you are well")
                if (first == True):
                    es.sendEmail(MIMEText("Hello, the Tooly robot notice a strange behavior, could you call your relative to make sure everything is ok?"))
                    first = False
                email = True
                audio = self.listen_for_audio(timeout)
                response = self.Decode(audio) if audio else None
            if(email == True):
                es.sendEmail(MIMEText("Hello, the Tooly robot listened to your family member again, don't worry"))
                first = False
        llama2Response = self.Llama2(conv_id,response)
        self.SpeechText(llama2Response)

        
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


pet.TurnOffEmotion()
pet.CleanPet()
qbo = QBOtalk()
conv_id = qbo.Llama2Connect()
llama2Response = qbo.Llama2(conv_id,"Hello")
qbo.SpeechText(llama2Response)
#pet_thread =threading.Thread(target=qbo.pet_detection, args=(conv_id,))
#pet_thread.deamon = False
#pet_thread.start()
while True:
    qbo.Start(conv_id)
    time.sleep(1)






