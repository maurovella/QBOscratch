"""Doble de SpeechRecognition (y de PyAudio, que nunca se importa).

Guion: "listens" es una lista de "audio" o "timeout" (una por listen());
"listens_long" es lo mismo para los listen() con timeout >= 1000 s;
"stt" es una lista de textos, o {"raise": "UnknownValueError"|"RequestError"}.
Cuando el guion se acaba, listen() da timeout.
"""
import fakelog

__version__ = "fake"


class UnknownValueError(Exception):
    pass


class RequestError(Exception):
    pass


class WaitTimeoutError(Exception):
    pass


class AudioData(object):
    def __init__(self, n):
        self.n = n

    def get_wav_data(self):
        return b"RIFF"


class Microphone(object):
    def __init__(self, device_index=None):
        self.device_index = device_index
        fakelog.emit("mic_open", device_index=device_index)

    @staticmethod
    def list_microphone_names():
        return fakelog.scenario().get("microphones", ["bcm2835 ALSA", "dmicQBO_sv", "default"])

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class Recognizer(object):
    def __init__(self):
        self.energy_threshold = 300
        self.pause_threshold = 0.8
        self.operation_timeout = None
        self._n = 0

    def adjust_for_ambient_noise(self, source, duration=1):
        fakelog.emit("stt_adjust")

    def listen(self, source, timeout=None, phrase_time_limit=None):
        # las esperas largas (el robot pregunta si esta todo bien) tienen guion propio
        queue = "listens_long" if (timeout or 0) >= 1000 else "listens"
        what = fakelog.take(queue, "timeout")
        fakelog.emit("stt_listen", timeout=timeout, got=what)
        if what == "timeout":
            # el robot espera hasta `timeout` segundos antes de rendirse
            fakelog.clock.advance(timeout or 0)
            raise WaitTimeoutError("listening timed out while waiting for phrase to start")
        self._n += 1
        return AudioData(self._n)

    def recognize_google(self, audio_data, key=None, language="en-US", **kwargs):
        result = fakelog.take("stt", {"raise": "UnknownValueError"})
        fakelog.emit("stt_recognize", language=language, result=result)
        if isinstance(result, dict):
            raise {"UnknownValueError": UnknownValueError, "RequestError": RequestError}[result["raise"]]()
        return result

    def listen_in_background(self, source, callback, phrase_time_limit=None):
        fakelog.emit("stt_background")

        def stopper(wait_for_stop=True):
            fakelog.emit("stt_background_stop")

        return stopper
