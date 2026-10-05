# Comandos de prueba anotados en el robot

Notas de terminal que estaban en `Python projects/commands` y `Tooly/commands` de la SSD vieja.
Son de Python 2: hoy el interprete es `python3`. Se conservan como referencia de que se probaba y como.

## Python projects/commands

```text
pico2wave -l "es-ES" -2 /home/pi/Documents/pico2wave.wav "La vida es muy compleja querido amigo" && aplay -D convertQBO /home/pi/Documents/pico2wave.wav
python PiCmd.py -c say -t "Hola"

python listen.py

python PiCmd.py -c nose -co blue

```

## Tooly/commands

```text



wav

python RightEye.py

python PiCmd.py -c nose -co green



pico2wave -l "es-ES" -w /home/pi/Documents/pico2wave.wav "Hola"  && aplay -D convertQBO /home/pi/Documents/pico2wave.wavPlaying WAVE '/home/pi/Documents/pico2wave.wav' : Signed 16 bit Little Endian, Rate 16000 Hz, Mono





python findFace.py:

libv4l2: error setting pixformat: Device or resource busy
HIGHGUI ERROR: libv4l unable to ioctl S_FMT
libv4l2: error setting pixformat: Device or resource busy
libv4l1: error setting pixformat: Device or resource busy
HIGHGUI ERROR: libv4l unable to ioctl VIDIOCSPICT
```
