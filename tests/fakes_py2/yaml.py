"""PyYAML minimo para la imagen python:2.7-slim, que no lo trae.

El arnes escribe config.yml como JSON, que tambien es YAML valido: en Python 3
lo lee el PyYAML real, aca alcanza con json.
"""
import json


def safe_load(stream):
    text = stream.read() if hasattr(stream, "read") else stream
    data = json.loads(text)
    return _to_str(data)


TEXT = type(u"")     # unicode en Python 2


def _to_str(value):
    # PyYAML en Python 2 devuelve str para texto ASCII, no unicode
    if isinstance(value, dict):
        return dict((_to_str(k), _to_str(v)) for k, v in value.items())
    if isinstance(value, list):
        return [_to_str(v) for v in value]
    if isinstance(value, TEXT) and str is not TEXT:
        try:
            return value.encode("ascii")
        except UnicodeEncodeError:
            return value
    return value


def dump(data, stream=None, **kwargs):
    text = json.dumps(data, sort_keys=True)
    if stream is None:
        return text
    stream.write(text)
