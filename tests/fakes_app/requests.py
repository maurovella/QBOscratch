"""Doble de requests para las corridas de punta a punta.

Guion: "http" es una lista con una entrada por llamada:
{"status": 200, "json": {...}}  o  {"raise": "ConnectionError"|"Timeout"}.
"""
import fakelog


class RequestException(IOError):
    pass


class ConnectionError(RequestException):
    pass


class Timeout(RequestException):
    pass


class HTTPError(RequestException):
    pass


class _Exceptions(object):
    RequestException = RequestException
    ConnectionError = ConnectionError
    Timeout = Timeout
    HTTPError = HTTPError


exceptions = _Exceptions()


class Response(object):
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = repr(payload)

    def json(self):
        if self._payload is None:
            raise ValueError("No JSON object could be decoded")
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPError("%s Server Error" % self.status_code)

    def __repr__(self):
        return "<Response [%s]>" % self.status_code


def post(url, json=None, **kwargs):
    step = fakelog.take("http", {"raise": "ConnectionError"})
    fakelog.emit("http_post", url=url, json=json, extra=sorted(kwargs))
    if "raise" in step:
        raise {"ConnectionError": ConnectionError, "Timeout": Timeout}[step["raise"]]("guion")
    return Response(step.get("status", 200), step.get("json"))
