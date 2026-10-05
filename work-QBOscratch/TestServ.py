import time
import serial #handles the serial ports
import QboCmd #holds some commands we can use for Qbo

#set up ports for communicating with servos
port = '/dev/serial0'
ser = serial.Serial(port, baudrate=115200, bytesize = serial.EIGHTBITS, stopbits = serial.STOPBITS_ONE, parity = serial.PARITY_NONE, rtscts = False, dsrdtr =False, timeout = 0)
QBO = QboCmd.Controller(ser)


def ChangeDeviceID(device, cmd, value):
    QBO.GetHeadCmd("SET_SERVO_LED", [device,1])
    time.sleep(0.1)
    Id = QBO.GetHeadCmd("GET_SERVO_BYTE_REG", [device, 3])
    print "Present ID", Id
    time.sleep(0.1)
    QBO.GetHeadCmd(cmd, [device,value])
    print cmd, [device,value]
    time.sleep(0.1)
    newId = QBO.GetHeadCmd("GET_SERVO_BYTE_REG", [value, 3])
    print "New ID", newId
    time.sleep(.5)
    QBO.GetHeadCmd("SET_SERVO_LED", [value,0])
    time.sleep(.1)
    return


def GetServoLimits(cmd, device):
    if cmd == "SET_SERVO_CW_LIM":
        cw_limits = QBO.GetHeadCmd("GET_SERVO_CW_LIM", device)
        if cw_limits:
            result = (cw_limits[1] << 8 | cw_limits[0])
        else :
            result = 0
    elif cmd == "SET_SERVO_CCW_LIM":
        ccw_limits = QBO.GetHeadCmd("GET_SERVO_CCW_LIM", device)
        if ccw_limits:
            result = (ccw_limits[1] << 8 | ccw_limits[0])
        else :
            result = 0
    return result



#print "Port Forwad"
#print QBO.GetHeadCmd("SET_USB2SERVO_FWD",1)


#print ChangeDeviceID(2,"SET_SERVO_ID",2) 
#print QBO.GetHeadCmd("SET_SERVO_ID", [2,2])

QBO.SetServo(1, 0, 10)
QBO.SetServo(2, 0, 10)

QBO.SetPid(1,26,2,16)
QBO.SetPid(2,26,2,16)




QBO.GetHeadCmd("RESET_SERVO", 1)


axis=1

def res():
	print "Resetting servo " + str(axis)
	print QBO.GetHeadCmd("RESET_SERVO", axis)

	print QBO.GetHeadCmd("SET_SERVO_LED", [axis, 0])

	print GetServoLimits("SET_SERVO_CW_LIM", axis)
	print GetServoLimits("SET_SERVO_CCW_LIM", axis)


	print QBO.GetHeadCmd("SET_SERVO_CW_LIM", [axis,600])
	print QBO.GetHeadCmd("SET_SERVO_CCW_LIM", [axis,600])

	print GetServoLimits("SET_SERVO_CW_LIM",axis)
	print GetServoLimits("SET_SERVO_CCW_LIM",axis)

res()

QBO.SetAngle(axis,100) 
time.sleep(1)

QBO.SetAngleRelative(axis,+400) 
time.sleep(2)

QBO.SetAngleRelative(axis,-400)


time.sleep(3)

