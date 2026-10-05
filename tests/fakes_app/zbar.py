"""Doble del lector de QR. Guion "qr": una lista de textos por cuadro escaneado."""
import fakelog


class Symbol(object):
    def __init__(self, data):
        self.data = data


class Image(object):
    def __init__(self, width, height, fmt, data):
        self.symbols = []

    def __iter__(self):
        return iter(self.symbols)


class ImageScanner(object):
    def scan(self, image):
        found = fakelog.take("qr", [])
        fakelog.emit("qr_scan", found=found)
        image.symbols = [Symbol(str(text)) for text in found]
        return len(found)
