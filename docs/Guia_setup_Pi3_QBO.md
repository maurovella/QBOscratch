# Guía de setup en la Raspberry Pi 3 — controlar la Q-board de QBO

**Plataforma destino:** Raspberry Pi 3, Raspberry Pi OS (Raspbian) **32-bit**, instalación nueva.
**Meta:** dejar la Pi capaz de (1) hablarle a la Q-board por `/dev/serial0` para display/táctil/nariz/mic-RMS, y (2) reproducir/grabar audio por I2S (parlante y micrófono).

> Leé primero el documento *Ingeniería inversa del firmware de la Q-board* — esta guía asume esa arquitectura (UART de control + I2S de audio).

---

## Resumen de los 4 bloques

1. **UART de control** → habilitar `/dev/serial0` (liberar la consola serie). *Imprescindible.*
2. **I2S de audio** → habilitar el bus I2S con la Pi como **maestro** y cargar un codec. *Lo más delicado.*
3. **ALSA** → crear el dispositivo `convertQBO` para `aplay`/`arecord`.
4. **Software** → Python 3 + `pyserial` + utilidades de audio, y prueba de cada subsistema.

Tiempo estimado: 30–60 min. Necesitás acceso a la Pi (teclado+monitor o SSH).

---

## Bloque 1 — UART de control (`/dev/serial0`)

En la Pi 3 hay un detalle importante: el **UART "bueno" (PL011)** está por defecto asignado al **Bluetooth**, y el UART que queda en los pines GPIO14/15 es el "mini-UART", cuyo baudrate depende del reloj de la CPU (inestable). Para un enlace serie confiable a 115200, conviene **mover el PL011 a los pines GPIO** y desactivar el BT (o al menos su uso del UART).

### 1.1 Habilitar el hardware serial y liberar la consola

```bash
sudo raspi-config
#   3 Interface Options  →  I6 Serial Port
#   "Would you like a login shell over serial?"  →  NO
#   "Would you like the serial port hardware enabled?"  →  YES
```

Esto edita `/boot/cmdline.txt` (quita `console=serial0,115200`) y agrega `enable_uart=1` a `/boot/config.txt`.

### 1.2 Pasar el UART PL011 a los GPIO (recomendado en Pi 3)

Editá `/boot/config.txt` y agregá:

```ini
# UART confiable en GPIO14/15 (mueve el PL011 fuera del Bluetooth)
enable_uart=1
dtoverlay=disable-bt
```

Luego desactivá el servicio que usa el módem BT por serie:

```bash
sudo systemctl disable hciuart
```

> Alternativa si querés conservar Bluetooth: `dtoverlay=miniuart-bt` (deja el mini-UART para BT y el PL011 en los GPIO). Para este proyecto, lo más simple y robusto es `disable-bt`.

### 1.3 Verificación

Reiniciá (`sudo reboot`) y comprobá:

```bash
ls -l /dev/serial0          # debe apuntar a ttyAMA0 (PL011)
# lrwxrwxrwx ... /dev/serial0 -> ttyAMA0
```

Si `/dev/serial0 -> ttyAMA0`, quedó bien. (Si apunta a `ttyS0`, es el mini-UART: revisá `disable-bt`.)

### 1.4 Permisos

Agregá tu usuario al grupo `dialout` para abrir el puerto sin sudo:

```bash
sudo usermod -aG dialout $USER     # reloguear después
```

---

## Bloque 2 — Bus de audio I2S (la Pi como maestro)

Este es el bloque que **no está documentado en el repo** y requiere más cuidado. La Q-board es un **esclavo I2S sin interfaz de control** (no es un codec I2C estándar tipo WM8960): simplemente consume/produce PCM cuando la Pi le da BCLK + LRCLK. Por eso, del lado de la Pi necesitás un overlay que:

- Active la interfaz I2S del SoC en los pines GPIO18/19/20/21.
- Cargue un **codec "dummy"/genérico** que haga de maestro de reloj a la tasa correcta.

> **Parámetros exactos que pide el firmware (verificados en `user.c`):** frame I2S de **2 slots × 16 bits**, formato I2S estándar (`data_delay=I2S`), **16 kHz**. Es decir, del lado de la Pi el bus es **S16_LE, 2 canales, 16000 Hz**, con **BCLK ≈ 512 kHz** (16000 × 2 × 16) y **LRCLK = 16 kHz**. El contenido es mono (`mono_mode` en la placa), pero a nivel de hardware/ALSA el frame es de **2 canales** — por eso el dispositivo `hw:` conviene abrirlo a `channels 2` y dejar que el plug `convertQBO` haga el mono→estéreo. RX de la placa (parlante) = serializer sobre PA07; TX (mic) = serializer sobre PA08.

### 2.1 Habilitar I2S

En `/boot/config.txt`:

```ini
# Activar interfaz I2S del SoC
dtparam=i2s=on
```

### 2.2 Cargar un codec genérico maestro

La opción más portable es el overlay **`googlevoicehat-soundcard`** o **`hifiberry-dac`**, pero ambos asumen un DAC específico. Para un esclavo "crudo" como la Q-board, lo correcto es el codec **`simple-audio-card` + `dummy`/`spdif-transmitter`** vía un overlay propio, o el conocido truco con **`hifiberry-dac`** (que pone la Pi como maestro I2S con un codec PCM5102 ficticio). Probá en este orden:

```ini
# Opción A (probar primero): hace a la Pi maestro I2S, codec PCM ficticio
dtoverlay=hifiberry-dac

# Opción B: codec de Google Voice HAT (I2S full-duplex, suele dar captura+reproducción)
# dtoverlay=googlevoicehat-soundcard
```

> **Por qué importa:** necesitás un overlay que genere los relojes **y** habilite **captura** (mic) además de **reproducción** (parlante). `hifiberry-dac` es solo salida; si necesitás grabar el micrófono, probablemente te sirva mejor `googlevoicehat-soundcard` (full-duplex) o un `simple-audio-card` a medida. Ver 2.4.

### 2.3 Reiniciar y verificar la tarjeta de sonido

```bash
sudo reboot
# después:
aplay -l        # lista tarjetas de REPRODUCCIÓN  → debe aparecer la I2S
arecord -l      # lista tarjetas de CAPTURA       → para el micrófono
cat /proc/asound/cards
```

Anotá el número de **card** y **device** (ej. `card 1: sndrpihifiberry [...], device 0`). Lo vas a usar como `hw:1,0`.

### 2.4 Si necesitás full-duplex (mic + parlante) — overlay a medida

Si ningún overlay listo te da captura Y reproducción a 16 kHz, creá un overlay `simple-audio-card`. Esqueleto (`qbo-i2s-overlay.dts`):

```dts
/dts-v1/;
/plugin/;
/ {
  compatible = "brcm,bcm2837";
  fragment@0 {
    target = <&i2s>;
    __overlay__ { status = "okay"; };
  };
  fragment@1 {
    target-path = "/";
    __overlay__ {
      qbo_codec: qbo-codec {
        #sound-dai-cells = <0>;
        compatible = "linux,spdif-transmitter"; /* codec dummy */
        status = "okay";
      };
      sound {
        compatible = "simple-audio-card";
        simple-audio-card,name = "QBO-I2S";
        simple-audio-card,format = "i2s";
        simple-audio-card,bitclock-master = <&dailink_master>;
        simple-audio-card,frame-master   = <&dailink_master>;
        dailink_master: simple-audio-card,cpu { sound-dai = <&i2s>; };
        simple-audio-card,codec { sound-dai = <&qbo_codec>; };
      };
    };
  };
};
```

Compilar y cargar:

```bash
dtc -@ -I dts -O dtb -o qbo-i2s.dtbo qbo-i2s-overlay.dts
sudo cp qbo-i2s.dtbo /boot/overlays/
# en /boot/config.txt:  dtoverlay=qbo-i2s
```

> Un codec "dummy" no captura; para el micrófono real probablemente debas usar `googlevoicehat-soundcard` o un codec que declare capacidad de captura. Esta parte es de **prueba y error sobre la Pi real**; documentá lo que funcione.

### 2.5 Atajo recomendado: recuperar la config original

Como la imagen original de QBO ya tenía esto resuelto, **si todavía tenés la SD original**, copiá de ahí:
- `/boot/config.txt` (las líneas `dtoverlay=` y `dtparam=i2s=on`)
- `/etc/asound.conf` (la definición de `convertQBO`)
- cualquier `.dtbo` propio en `/boot/overlays/`

Eso te ahorra todo el bloque 2.4. Si no la tenés, seguí el camino de overlays de arriba.

> **Pointer externo:** la configuración exacta de audio I2S de la imagen original de QBO no parece estar publicada de forma abierta, pero el foro de la comunidad de theCorpora tiene hilos de audio en Raspberry Pi que pueden servir de referencia (https://thecorpora.com/community/). Para el overlay genérico, los hilos de Raspberry Pi sobre `simple-audio-card` + I2S mic full-duplex son la mejor guía si tenés que reconstruirlo.

---

## Bloque 3 — ALSA: el dispositivo `convertQBO`

El código original reproduce con `aplay -D convertQBO`. `convertQBO` es un PCM "plug" que adapta el formato del archivo al que pide el codec I2S (sample rate, canales). Creá `/etc/asound.conf`:

```text
# Ajustá card/device según `aplay -l` (ej. hw:1,0)
pcm.convertQBO {
    type plug
    slave {
        pcm "hw:1,0"
        rate 16000        # debe coincidir con el firmware (16 kHz)
        channels 2        # el frame I2S es de 2 slots; el plug hace mono->estéreo
        format S16_LE
    }
}

# (opcional) dispositivo de captura para el micrófono
pcm.micQBO {
    type plug
    slave {
        pcm "hw:1,0"
        rate 16000
        channels 2        # idem; el plug entrega mono al arecord si pedís -c 1
        format S16_LE
    }
}
```

Probar:

```bash
# Encender el parlante PRIMERO por la UART (ver Bloque 4), luego:
speaker-test -D convertQBO -c 1 -t sine -f 440     # tono de prueba
aplay -D convertQBO /usr/share/sounds/alsa/Front_Center.wav
arecord -D micQBO -f S16_LE -r 16000 -c 1 prueba.wav   # grabar 
```

---

## Bloque 4 — Software y prueba de cada subsistema

### 4.1 Dependencias

```bash
sudo apt update
sudo apt install -y python3-serial python3-pip alsa-utils libttspico-utils
# pico2wave (TTS offline en español) viene en libttspico-utils
```

### 4.2 Portar `QboCmd.py` a Python 3

El `QboCmd.py` del repo es Python 2.7. Para Python 3 hay que cambiar pocas cosas: `print x` → `print(x)`, `dict.has_key(k)` → `k in dict`, y manejar bytes con `int` directamente (en Py3 iterar `bytes` ya da `int`, así que `ord(i)` se reemplaza por `i`). Puedo generarte el `qbo.py` ya portado y limpio si querés — avisame.

### 4.3 Prueba rápida de control (display, nariz, táctil) — Python 3

```python
import serial, time

PORT = "/dev/serial0"
ser = serial.Serial(PORT, 115200, timeout=1)

PEARSON = [  # misma tabla del firmware
 0x00,0x77,0xee,0x99,0x07,0x70,0xe9,0x9e,0x0e,0x79,0xe0,0x97,0x09,0x7e,0xe7,0x90,
 # ... (copiar las 256 entradas desde QboCmd.py) ...
]

def pearson(data):                 # data = [CMD, N, *params]
    h = 0
    for b in data:
        h = PEARSON[h ^ (b & 0xff)]
    return h

def frame(cmd, params=()):
    body = [cmd, len(params), *params]
    raw = body + [pearson(body)]
    out = [0xFF]
    for b in raw:                  # escapar bytes >= 0xFD
        if b >= 0xFD:
            out += [0xFD, b - 2]
        else:
            out.append(b)
    out.append(0xFE)
    return bytes(out)

def send(cmd, params=()):
    ser.reset_input_buffer()
    ser.write(frame(cmd, params))
    return ser.read(16)            # respuesta cruda (parsear si hace falta)

# Nariz azul
send(0x45, [0x01])
time.sleep(0.5)
# Boca (sonrisa): filas 0b00000/0b10001/0b01110/0b00000
send(0x44, [0b00000, 0b10001, 0b01110, 0b00000])
# Leer táctil (0=nada,1=der,2=arriba,3=izq)
print("touch:", send(0x46))
```

> Esto es solo para validar el enlace. Para producción usá la librería portada (`qbo.py`), que maneja checksum de respuesta, NACK y reintentos.

### 4.4 Prueba de audio

```bash
# 1) Encender el parlante por la UART (SET_ENABLE_SPEAKER=0x86, parámetro=1).
#    Usá la función send() del ejemplo 4.3 (calcula el checksum correctamente):
python3 -c "import qbo_test; qbo_test.send(0x86,[1])"
#   o con la librería portada:  HeadServo.SendCmdQBO(Command(0x86,1,1))

# 2) Reproducir:
aplay -D convertQBO /usr/share/sounds/alsa/Front_Center.wav

# 3) Hablar (TTS español):
pico2wave -l "es-ES" -w /tmp/tts.wav "Hola, soy Qbo" && aplay -D convertQBO /tmp/tts.wav

# 4) Grabar del micrófono:
arecord -D micQBO -f S16_LE -r 16000 -c 1 -d 3 /tmp/mic.wav && aplay -D convertQBO /tmp/mic.wav
```

---

## Checklist de verificación final

- [ ] `/dev/serial0 -> ttyAMA0` (UART PL011 en los GPIO).
- [ ] `GET_VERSION` (0x40) devuelve respuesta válida (placa viva por UART).
- [ ] `SET_STATE` cambia el color de la nariz.
- [ ] `SET_MOUTH_VALUE` dibuja en la boca.
- [ ] `GET_TOUCH` reacciona al tocar los costados.
- [ ] `aplay -l` muestra la tarjeta I2S; `speaker-test -D convertQBO` suena.
- [ ] `arecord -l` muestra captura; `arecord -D micQBO` graba audio audible.
- [ ] `GET_MIC_REPORT` (0x4B) devuelve 6 bytes que cambian con el ruido ambiente.

---

## Notas y riesgos

1. **El bloque de audio I2S es el de mayor incertidumbre.** El overlay exacto y el `asound.conf` dependían de la imagen original; si la conservás, copiá esos archivos (sección 2.5) en vez de reconstruirlos.
2. **Sample rate:** el firmware trabaja alrededor de **16 kHz**. Si el audio se escucha agudo/grave o acelerado, ajustá `rate` en `asound.conf` y/o el overlay.
3. **Encender el parlante:** sin `SET_ENABLE_SPEAKER 1` (UART) no sale sonido aunque ALSA reproduzca. Es un error común.
4. **Pi 3 vs Pi nuevas:** en Pi 3 el detalle del mini-UART/PL011 (bloque 1.2) es clave; en modelos más nuevos cambia la nomenclatura, pero vos vas con Pi 3, así que aplicá `disable-bt`.
5. **32-bit:** todo lo de esta guía funciona igual en Raspberry Pi OS 32-bit; no hay dependencia de 64-bit.
