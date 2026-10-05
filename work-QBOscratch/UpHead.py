import time
import serial #handles the serial ports
import QboCmd #holds some commands we can use for Qbo

#set up ports for communicating with servos
port = '/dev/serial0'
ser = serial.Serial(port, baudrate=115200, bytesize = serial.EIGHTBITS, stopbits = serial.STOPBITS_ONE, parity = serial.PARITY_NONE, rtscts = False, dsrdtr =False, timeout = 0)
QBO = QboCmd.Controller(ser)

print("Start Positon")
#Set a start position 
QBO.SetServo(175,511, 100)#Axis,Angle,Speed
time.sleep(10)

print("Left Positon")
#Move the head to the left
QBO.SetServo(175,725, 100)#Axis,Angle,Speed
#Pause
time.sleep(10)

print("Start Positon")
#move it back to starting point
QBO.SetServo(191,511, 100)#Axis,Angle,Speed
#Pause
time.sleep(10)

print("Right Positon")
#Move the head to the right
QBO.SetServo(191,290, 100)#Axis,Angle,Speed
#Pause
time.sleep(10)










