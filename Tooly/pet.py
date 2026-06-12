#!/usr/bin/env python2.7

from multiprocessing import Process, Queue
import subprocess
import os
import errno
import time
import serial
import binascii
import QboCmd
import sys
import time
import yaml

port = '/dev/serial0'

try:
        print(port)
        # Open serial port
        ser = serial.Serial(port, baudrate=115200, bytesize = serial.EIGHTBITS, stopbits = serial.STOPBITS_ONE, parity = serial.PARITY_NONE, rtscts = False, dsrdtr =False, timeout = 0)
        print "Open serial port sucessfully."
        print(ser.name)
except:
        print "Error opening serial port."
        sys.exit()

HeadServo = QboCmd.Controller(ser)

def WaitForTouch():
        touch_str=""
        touch = HeadServo.GetHeadCmd("GET_TOUCH", 0)
        if touch:
                if touch == [1]:
                    touch_str = "Touch: right"
                elif touch == [2]:
                    touch_str = "Touch: up"
                elif touch == [3]:
                    touch_str = "Touch: left"

                if touch == [1] or touch == [2] or touch == [3]:
	                print(touch_str + " TO FIFO FEEL" )
	                HeadServo.SetMouth(0x1B1F0E04)
	                time.sleep(0.1)
	                HeadServo.SetNoseColor(4)
        return touch_str

def TurnOffEmotion():
    HeadServo.SetMouth(0x00000000)
    time.sleep(0.1)
    HeadServo.SetNoseColor(0)
    return


def CleanPet():
    time.sleep(0.1)
    HeadServo.GetHeadCmd("GET_TOUCH", 0)
    return
    
##while(True):
##    TurnOffEmotion()
##    time.sleep(0.1)
##    WaitForTouch()
    
    



