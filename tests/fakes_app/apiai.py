"""Doble de apiai (Dialogflow V1, apagado). Solo para que el import no falle."""


class ApiAI(object):
    def __init__(self, token):
        self.token = token

    def text_request(self):
        raise RuntimeError("Dialogflow V1 no existe mas")
