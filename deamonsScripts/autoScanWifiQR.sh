#! /bin/bash

internetStatus=$(curl -s -I https://www.google.com/ | grep "HTTP/2 200")

if [ -z "$internetStatus" ]
then
        pico2wave -l "en-US" -w /home/pi/Documents/pico2wave.wav "I'm not connected to the internet. Start scanning QR code." && aplay -D convertQBO /home/pi/Documents/pico2wave.wav
	/home/pi/Documents/deamonsScripts/QBO_scratch stop
	/home/pi/Documents/deamonsScripts/QBO_PiFaceFast stop

	RTQRExec=$(ps -aux | grep RTQR.py | wc -l)

	if [ $RTQRExec -eq 2 ]
	then
		echo "Ya se esta ejecutando el reconocimiento de qr"
	else
		python /home/pi/Documents/deamonsScripts/RTQR.py
		pico2wave -l "en-US" -w /home/pi/Documents/pico2wave.wav "Got it, I'm connecting to the internet" && aplay -D convertQBO /home/pi/Documents/pico2wave.wav
		sleep 20
		internetStatus2=$(curl -s -I https://www.google.com/ | grep "HTTP/2 200")
			if [ -z "$internetStatus2" ]
			then
						pico2wave -l "en-US" -w /home/pi/Documents/pico2wave.wav "Sorry, your SSID or password is wrong, try again." && aplay -D convertQBO /home/pi/Documents/pico2wave.wav
			else
						pico2wave -l "en-US" -w /home/pi/Documents/pico2wave.wav "I am connected" && aplay -D convertQBO /home/pi/Documents/pico2wave.wav
						python /home/pi/Documents/deamonsScripts/autoStart.py
			fi

	fi

fi
