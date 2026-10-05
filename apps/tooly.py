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
from qbo import touch as pet
from qbo import notify as es
import multiprocessing
import threading
from email.mime.text import MIMEText
from multiprocessing import Process, Queue
import subprocess
import cv2
import serial
import binascii
from qbo import protocol as QboCmd
from qbo import paths
from qbo import tts
from qbo import llm
import shlex
import sys

config = yaml.safe_load(open(paths.CONFIG))

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
                print("LISTEN: " + str)
        except sr.UnknownValueError:
            str = ""
        except sr.RequestError as e:
            str = "Could not request results from Speech Recognition service"
        return str

    def SpeechText(self, text_to_speech):
        with self.lock:
            self.config = yaml.safe_load(open(paths.CONFIG))
            print("config:" + str(self.config))

            if (self.config["language"] == "spanish"):
                text, volume = text_to_speech, self.config["volume"]
            else:
                text, volume = text_to_speech, 40     # fijo en el original: en ingles no lee el volumen de config.yml
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


    def Llama2Connect(self):
        print("llamaaaaaa2Connect")
        # el backend (servidor original u Ollama) se elige en config.yml: ver qbo/llm
        self.llm = llm.from_config(self.config)
        return self.llm.start()

    def Llama2(self, conv_id, msg):
        # conv_id queda por compatibilidad: la conversacion la lleva el cliente
        return self.llm.chat(msg)
    
    def pet_detection(self, conv_id):
            if not self.touch:
                #if not self.lock.locked():
                touch = pet.WaitForTouch()
                if touch:
                    self.touch = True
                    try:
                        petResponse = self.Llama2(conv_id, "I pet you in your robot head")
                        self.SpeechText(petResponse)
                    except llm.LLMError as e:
                        print("LLM sin respuesta a la caricia: " + str(e))
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
        
    def Ifttt(self):
        self.r.operation_timeout = 1000
        timeout = 1000
        wait_time = 4*3600
        #wait_time = 20
        start_time = time.time()
        audio = self.listen_for_audio()
        
        response = self.Decode(audio) if audio else None
        while((response == None or response == "" ) and (time.time() - start_time) < wait_time):
            time.sleep(5)
            audio = self.listen_for_audio()
            response = self.Decode(audio) if audio else None
            
        self.SpeechText(response)
    
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
        try:
            llama2Response = self.Llama2(conv_id,response)
        except llm.LLMError as e:
            # el LLM dejo de responder en medio de la charla: avisa y repite lo que oyo
            print("LLM sin respuesta: " + str(e))
            self.SpeechText(llm.FALLBACK_TEXT)
            llama2Response = response
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

    


Kpx = 1
Kpy = 1
Ksp = 40

## Head X and Y angle limits

Xmax = 725
Xmin = 290
Ymax = 550
Ymin = 420

## Initial Head position

Xcoor = 511
Ycoor = 450
Facedet = 0



if len(sys.argv) > 1:
        port = sys.argv[1]
else:
        port = '/dev/serial0'

try:
        # Open serial port
        ser = serial.Serial(port, baudrate=115200, bytesize = serial.EIGHTBITS, stopbits = serial.STOPBITS_ONE, parity = serial.PARITY_NONE, rtscts = False, dsrdtr =False, timeout = 0)
        print("Open serial port sucessfully.")
        print(ser.name)
except:
        print("Error opening serial port.")
        sys.exit()


QBO = QboCmd.Controller(ser)

QBO.SetServo(1, Xcoor, 100)
QBO.SetServo(2, Ycoor, 100)
time.sleep(1)
#QBO.SetPid(1, 26, 12, 16)
QBO.SetPid(1, 26, 2, 16)
time.sleep(1)
#QBO.SetPid(2, 26, 12, 16)
QBO.SetPid(2, 26, 2, 16)
time.sleep(1)
QBO.SetNoseColor(2)       #Off QBO nose brigth


frontalface = cv2.CascadeClassifier(paths.HAAR_FRONTAL)              # frontal face pattern detection
profileface = cv2.CascadeClassifier(paths.HAAR_PROFILE)           # side face pattern detection

face = [0,0,320,240]    # This will hold the array that OpenCV returns when it finds a face: (makes a rectangle)
Cface = [0,0]           # Center of the face: a point calculated from the above variable

x,y,w,h = face
Cface = [(w//2+x),(h//2+y)]       # we are given an x,y corner point and a width and height, we need the center



# camera_index en config.yml: 1 en el kernel 4.9 del robot original. En kernels
# nuevos cada camara USB ocupa dos nodos V4L2 y la segunda pasa a ser la 2.
cap = cv2.VideoCapture(config.get("camera_index", 1))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)            # I have found this to be about the highest-
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)   # resolution you'll want to attempt on the pi

time.sleep(10)          # Wait for them to start

face = 150,110,20,20
Cface = [ 160, 120 ]


pet.TurnOffEmotion()
pet.CleanPet()
qbo = QBOtalk()


faceFound = False

counter = 0
llama2 = True

try:
    conv_id = qbo.Llama2Connect()
    llama2Response = qbo.Llama2(conv_id,"Hello")
    qbo.SpeechText(llama2Response)
except:
    llama2 = False
    qbo.SpeechText("Hello ! My mind is not ready, I will repeat whatever you say.")

pantilt_abs = [0,0]
    
while (True):
    ret, frame = cap.read()

    move = False
    
    fface = frontalface.detectMultiScale(frame,1.3,4,(cv2.CASCADE_DO_CANNY_PRUNING | cv2.CASCADE_FIND_BIGGEST_OBJECT | cv2.CASCADE_DO_ROUGH_SEARCH),(60,60))
    if len(fface) > 0:              # if we found a frontal face...
        face_not_found_idx = 0
        lastface = 1            # set lastface 1 (so next loop we will only look for a frontface)
        for f in fface:         # f in fface is an array with a rectangle representing a face
            faceFound = True
            face = f
            
    cv2.rectangle(frame, (face[0],face[1]),(face[0]+face[2], face[1]+face[3]),(255,0,0),2) 
    
    x,y,w,h = face
    Cface = [(w//2+x),(h//2+y)] 
    
    print(Cface)
    
    cv2.imshow('Tooly Vision', frame)
    
    key = cv2.waitKey(1) & 0xFF
    
    if (key == ord('q')):
        break
    
    if (counter>0):
        counter = counter - 1
        continue


    faceOffset_X = 160 - Cface[0]
    if (faceOffset_X > 20) | (faceOffset_X < -20):
            time.sleep(0.002)
            
            offset = pantilt_abs[0]
            offset = offset + faceOffset_X >> 1
            
            if (offset > -20) or (offset < 20):
                QBO.SetAngleRelative(1, faceOffset_X >> 1 )
                #wait for move
                time.sleep(0.05)
                pantilt_abs[0] = offset
            #print "MOVE REL X: " + str(faceOffset_X >> 1)
            move = True
    faceOffset_Y = Cface[1] - 120
    if (faceOffset_Y > 20) | (faceOffset_Y < -20):
            time.sleep(0.002)
            
            offset = pantilt_abs[1]
            offset = offset + faceOffset_Y >> 1
            
            if (offset > -10) or (offset < 10):
                QBO.SetAngleRelative(2, faceOffset_Y >> 1 )
                #wait for move
                time.sleep(0.05)
                pantilt_abs[1] = offset
            #print "MOVE REL Y: " + str(faceOffset_Y >> 1)
            move = True
    
    if faceFound and not move:
        QBO.SetNoseColor(4)
        if llama2:
            qbo.Start(conv_id)
        else:
            qbo.Ifttt()
        faceFound = False
        counter = 50
        QBO.SetNoseColor(2) 

ser.close()
cap.release()
        
cv2.destroyAllWindows()




