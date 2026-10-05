import os
import sys
# raiz del repo en sys.path, para importar el paquete qbo sin instalarlo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import serial #handles the serial ports
from qbo import protocol as QboCmd #holds some commands we can use for Qbo

#set up ports for communicating with servos
port = '/dev/serial0'
ser = serial.Serial(port, baudrate=115200, bytesize = serial.EIGHTBITS, stopbits = serial.STOPBITS_ONE, parity = serial.PARITY_NONE, rtscts = False, dsrdtr =False, timeout = 0)
QBO = QboCmd.Controller(ser)

print("Start Positon")
#Set a start position 
QBO.SetServo(1,511, 100)#Axis,Angle,Speed
time.sleep(10)

print("Left Positon")
#Move the head to the left
QBO.SetServo(1,725, 100)#Axis,Angle,Speed
#Pause
time.sleep(10)

print("Start Positon")
#move it back to starting point
QBO.SetServo(2,511, 100)#Axis,Angle,Speed
#Pause
time.sleep(10)

print("Right Positon")
#Move the head to the right
QBO.SetServo(2,290, 100)#Axis,Angle,Speed
#Pause
time.sleep(10)










