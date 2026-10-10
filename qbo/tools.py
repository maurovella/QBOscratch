"""Herramientas del robot: el contrato que usa el arnes y como se ejecutan.

El arnes decide y llama a una de estas cuatro herramientas. Este modulo valida
el pedido y, si hay robot, lo ejecuta con los mismos comandos que apps/picmd.py:

    say    {"text": "Hola, aca estoy"}
    nose   {"color": "green"}          none, red, blue, green
    mouth  {"expression": "smile"}     smile, sad, serious, love
    head   {"axis": 1, "angle": 20}    axis 1 gira, axis 2 inclina. Grados,
                                       posicion absoluta, 0 = mirando al frente

No interpreta sensores. apps/tools_api.py lo expone por HTTP.
"""
import threading

TOOLS = ("say", "nose", "mouth", "head")
COLORS = ("none", "red", "blue", "green")
EXPRESSIONS = ("smile", "sad", "serious", "love")
AXES = (1, 2)

# Rango aceptado de "angle", en grados. Mas alla se recorta.
ANGLE_LIMITS = {1: (-90, 90), 2: (-40, 40)}

# Mismos valores que apps/picmd.py
NOSE_CODE = {"none": 0, "red": 2, "blue": 1, "green": 4}
MOUTH_MATRIX = {"smile": 0x110E00, "sad": 0x0E1100, "serious": 0x1F1F00, "love": 0x1B1F0E04}

# Servos Dynamixel XL-320: 0.29 grados por unidad. Centros de scratch_extension/robot_control.js
DEG_PER_UNIT = 0.29
SERVO_CENTER = {1: 511, 2: 550}
SERVO_SPEED = 100

TEXT_MAX = 500


class InvalidRequest(ValueError):
    pass


def validate(tool, body):
    """Devuelve el pedido normalizado: solo los campos del contrato.

    Lanza InvalidRequest si la herramienta no existe o un valor no es valido.
    """
    if tool not in TOOLS:
        raise InvalidRequest("no existe la herramienta '%s'" % tool)
    if not isinstance(body, dict):
        raise InvalidRequest("el cuerpo tiene que ser un objeto JSON")
    if tool == "say":
        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            raise InvalidRequest("'text' tiene que ser un texto no vacio")
        return {"text": text.strip()[:TEXT_MAX]}
    if tool == "nose":
        if body.get("color") not in COLORS:
            raise InvalidRequest("'color' tiene que ser uno de %s" % list(COLORS))
        return {"color": body["color"]}
    if tool == "mouth":
        if body.get("expression") not in EXPRESSIONS:
            raise InvalidRequest("'expression' tiene que ser uno de %s" % list(EXPRESSIONS))
        return {"expression": body["expression"]}
    axis, angle = body.get("axis"), body.get("angle")
    if isinstance(axis, bool) or axis not in AXES:
        raise InvalidRequest("'axis' tiene que ser 1 (girar) o 2 (inclinar)")
    if isinstance(angle, bool) or not isinstance(angle, (int, float)):
        raise InvalidRequest("'angle' tiene que ser un numero, en grados")
    lo, hi = ANGLE_LIMITS[axis]
    return {"axis": axis, "angle": max(lo, min(hi, angle))}


def servo_position(axis, angle):
    """Grados (0 = al frente) a la posicion del XL-320 que espera SET_SERVO."""
    return int(SERVO_CENTER[axis] + angle / DEG_PER_UNIT)


class Robot(object):
    """Ejecuta herramientas ya validadas sobre la Q-board.

    `controller` es un qbo.protocol.Controller abierto. `speak` es una funcion
    (texto) -> None; por defecto, qbo.tts en espanol.
    """

    def __init__(self, controller, speak=None):
        self.head = controller
        self.speak = speak or speak_spanish
        self.lock = threading.Lock()

    def run(self, tool, msg):
        with self.lock:
            if tool == "nose":
                self.head.SetNoseColor(NOSE_CODE[msg["color"]])
            elif tool == "mouth":
                self.head.SetMouth(MOUTH_MATRIX[msg["expression"]])
            elif tool == "head":
                self.head.SetServo(msg["axis"], servo_position(msg["axis"], msg["angle"]), SERVO_SPEED)
            elif tool == "say":
                # pico2wave tarda: no frena la API mientras habla
                threading.Thread(target=self.speak, args=(msg["text"],), daemon=True).start()


def speak_spanish(text):
    from qbo import tts
    volume = 100
    try:
        import yaml
        from qbo import paths
        with open(paths.CONFIG) as fh:
            volume = (yaml.safe_load(fh) or {}).get("volume", 100)
    except Exception:       # sin config.yml o ilegible: volumen por defecto
        pass
    try:
        if tts.speak(text, "spanish", volume) != 0:
            print("[robot] say: pico2wave o aplay terminaron con error")
    except OSError as exc:      # pico2wave o aplay no instalados
        print("[robot] say: no se pudo hablar (%s)" % exc)
