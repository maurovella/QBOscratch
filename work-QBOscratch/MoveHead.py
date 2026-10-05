import time
import serial #handles the serial ports
import QboCmd #holds some commands we can use for Qbo

#set up ports for communicating with servos
port = '/dev/serial0'
ser = serial.Serial(port, baudrate=115200, bytesize = serial.EIGHTBITS, stopbits = serial.STOPBITS_ONE, parity = serial.PARITY_NONE, rtscts = False, dsrdtr =False, timeout = 0)
QBO = QboCmd.Controller(ser)

QBO.SetNoseColor(2)

QBO.SetServo(1, 0, 100)
QBO.SetServo(2, 0, 100)

QBO.SetPid(1,26,2,16)
QBO.SetPid(2,26,2,16)


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
QBO.SetServo(1,511, 100)#Axis,Angle,Speed
#Pause
time.sleep(10)

print("Right Positon")
#Move the head to the right
QBO.SetServo(1,290, 100)#Axis,Angle,Speed
#Pause
time.sleep(10)










