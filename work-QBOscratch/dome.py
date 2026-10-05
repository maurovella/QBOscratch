import argparse
import serial
import time
import QboCmd

port = serial.Serial('/dev/serial0', 115200, timeout=0)
HeadCtrl = QboCmd.Controller(port)

print ( HeadCtrl.GetHeadCmd("SET_SERVO_ENABLE", [1,1]) )
print ( HeadCtrl.GetHeadCmd("SET_SERVO_CW_LIM", [1,350]) )
print ( HeadCtrl.GetHeadCmd("SET_SERVO_CCW_LIM", [1,600]) )
print ( HeadCtrl.GetHeadCmd("SET_SERVO_ID", [1,4]) )
print ( HeadCtrl.GetHeadCmd("SET_SERVO_LED", [4,4]) )
time.sleep(0.5)
print ( HeadCtrl.GetHeadCmd("SET_SERVO_LED", [4,0]) )

