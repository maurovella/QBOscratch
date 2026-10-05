import os
import sys
import subprocess
# raiz del repo en sys.path, para importar el paquete qbo sin instalarlo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qbo import paths

import zbar
from PIL import Image
import cv2

def main():

    # Set 0 to default camera
    capture = cv2.VideoCapture(0)

    while True:

        # Breaks down the video into frames
        ret, frame = capture.read()

        # Displays the current frame
        #cv2.imshow('Current', frame)

        # Converts image to grayscale.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Uses PIL to convert the grayscale image into a ndary array that ZBar can understand.
        image = Image.fromarray(gray)
        width, height = image.size
        zbar_image = zbar.Image(width, height, 'Y800', image.tobytes())

        # Scans the zbar image.
        scanner = zbar.ImageScanner()
        scanner.scan(zbar_image)

        # Prints data from image.
        for decoded in zbar_image:
            
            #O btain string info qr
            info = decoded.data
            
            # Check if QR contain WiFi string
            if info[0:7] == "WIFI:S:":
                
                # Get indexs
                indexEndName = info.find(";T:")
                indexEndType = info.find(";P:")
                indexEndPass = len(info) - 2
                indexStartHidden = info.find(";H:true;")
                hidden = False
                
                # Check if wifi hidden
                if indexStartHidden != -1:
                    hidden = True
                    indexEndPass = indexStartHidden
                
                # Obtain values
                ssid = info[7:indexEndName]
                type = info[indexEndName+3:indexEndType]
                password = info[indexEndType+3:indexEndPass]
                
                result = subprocess.call(["aplay", os.path.join(paths.HOME, "blip2.wav")])
                
                # lista de argumentos, sin shell: el SSID y la clave salen de un QR
                # que puede mostrar cualquiera, y esto corre con sudo
                wificonfig = ["sudo", "bash", paths.daemon("writeWiFi.sh"), '"%s"' % ssid, '"%s"' % password, type]
                print(wificonfig)
                subprocess.call(wificonfig)
                
                return

if __name__ == "__main__":
    main()
