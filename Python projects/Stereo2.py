from cv import *

import sys
import time
import gc

cvNamedWindow("w1", CV_WINDOW_AUTOSIZE)
camera_index = 1
capture = cvCreateCameraCapture(camera_index)

def repeat():
    global capture
    global camera_index
    
    frame = cvQueryFrame(capture)
    cvShowImage("w1", frame)
    c = cvWaitKey(10)
    
    if (c=="q"):
        sys.exit(0)
        
    if (c == "r"):
        print 'reload'
        
        del capture
        
        capture = cvCreateCameraCapture(camera_index)
        
repeat()