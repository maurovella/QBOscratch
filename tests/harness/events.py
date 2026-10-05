"""Lectura y normalizacion del registro de eventos de una corrida.
Compatible con Python 2.7 y 3.
"""
import json

HOME_TOKEN = "<QBO>"


def load(path):
    events = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def _replace(value, old, new):
    if isinstance(value, dict):
        return dict((k, _replace(v, old, new)) for k, v in value.items())
    if isinstance(value, list):
        return [_replace(v, old, new) for v in value]
    try:
        text_type = unicode
    except NameError:
        text_type = str
    if isinstance(value, (text_type, str)):
        return value.replace(old, new)
    return value


def normalize(events, home, aliases=()):
    """Deja el registro comparable entre corridas.

    - la raiz del robot (/home/pi/Documents o un directorio temporal) pasa a <QBO>,
    - `aliases` son pares (texto, reemplazo) para rutas que cambiaron de lugar,
    - los datos leidos de cada FIFO se juntan en un solo evento por pipe, porque
      el corte en trozos depende del reloj real.
    """
    out = []
    fifo = {}
    for event in events:
        event = _replace(event, home, HOME_TOKEN)
        for old, new in aliases:
            event = _replace(event, old, new)
        if event["k"] == "fifo_rx":
            fifo[event["pipe"]] = fifo.get(event["pipe"], "") + event["data"]
            continue
        out.append(event)
    for pipe in sorted(fifo):
        out.append({"k": "fifo_total", "pipe": pipe, "data": fifo[pipe]})
    return compress(out)


def compress(events, max_period=8, min_repeats=3):
    """Colapsa bloques repetidos: {"repeat": n, "block": [...]}."""
    out = []
    i = 0
    n = len(events)
    while i < n:
        best = None
        for period in range(1, max_period + 1):
            block = events[i:i + period]
            if len(block) < period:
                break
            repeats = 1
            while events[i + repeats * period:i + (repeats + 1) * period] == block:
                repeats += 1
            if repeats >= min_repeats and (best is None or repeats * period > best[0] * best[1]):
                best = (repeats, period)
        if best:
            repeats, period = best
            out.append({"repeat": repeats, "block": events[i:i + period]})
            i += repeats * period
        else:
            out.append(events[i])
            i += 1
    return out


def describe(event):
    """Una linea legible por evento, para los diffs de los tests."""
    if "repeat" in event:
        return "%d x [%s]" % (event["repeat"], "; ".join(describe(e) for e in event["block"]))
    kind = event["k"]
    rest = dict((k, v) for k, v in event.items() if k != "k")
    return "%s %s" % (kind, json.dumps(rest, sort_keys=True, ensure_ascii=False))
