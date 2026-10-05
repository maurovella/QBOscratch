"""Texto a voz del robot: pico2wave genera un WAV y aplay lo manda al parlante.

Es el mismo comando que armaba cada script a mano,

    pico2wave -l "es-ES" -w <wav> "<volume level='100'>texto" && aplay -D convertQBO <wav>

pero sin pasar por una shell. El texto viene del microfono, de un FIFO o del
LLM, y con shell=True unas comillas rompian el comando y un $(...) se ejecutaba.

Si hay que cambiar de motor (espeak-ng, piper) se cambia solo este archivo.
"""
import subprocess

from qbo import paths

ALSA_DEVICE = "convertQBO"

VOICES = {"spanish": "es-ES"}
DEFAULT_VOICE = "en-US"


def voice_for(language):
    """config.yml dice 'spanish' o 'english'; cualquier otro valor habla ingles."""
    return VOICES.get(language, DEFAULT_VOICE)


def commands(text, language, volume):
    """Las dos lineas de comando, como listas de argumentos."""
    markup = "<volume level='" + str(volume) + "'>" + text
    return (["pico2wave", "-l", voice_for(language), "-w", paths.TTS_WAV, markup],
            ["aplay", "-D", ALSA_DEVICE, paths.TTS_WAV])


def speak(text, language, volume):
    """Dice `text` por el parlante. Devuelve el codigo de salida, 0 si salio bien."""
    synth, play = commands(text, language, volume)
    result = subprocess.call(synth)
    if result == 0:     # el '&&' del comando original
        result = subprocess.call(play)
    return result
