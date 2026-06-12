# Ingeniería inversa del firmware de la Q-board (QBO) — cómo se comunica con la Raspberry Pi

**Proyecto:** adaptación del robot QBO (Corpórea / theCorpora) para cuidado geriátrico
**Objetivo de este documento:** dejar documentado, con precisión, cómo la placa de la cabeza ("Q-board" / HeadCtrl) se comunica con la Raspberry Pi a través del shield, para poder controlar **display, sensores táctiles, micrófono y parlante** directamente desde la Pi.

---

## 0. Conclusión clave (leer primero)

**No hace falta desensamblar ningún binario.** El repositorio ya contiene **el código fuente C completo del firmware** de la Q-board *y* **la implementación Python de referencia que corre en la Pi**. Entre los dos, el protocolo queda 100 % descifrado. Lo único que NO está en este repo es la configuración de audio del lado de la Pi (device tree + ALSA), que vivía en la imagen de SD original (`/boot/config.txt`, `/etc/asound.conf`) — eso se cubre en la *Guía de setup*.

Archivos fuente relevantes (dentro de `QBOscratch/20200325.001_H1_HeadCtrl_Qboard/20150708.001_H1_HeadCtrl/src/`):

| Archivo | Qué contiene |
|---|---|
| `comands.h` | Lista de todos los códigos de comando |
| `serialProtocol.c/.h` | Parser del protocolo y dispatcher de comandos (el corazón) |
| `Mouth.c/.h` | Matriz de LEDs de la boca + nariz RGB |
| `CAP1203.c/.h` | Sensores táctiles capacitivos (chip CAP1203 por I2C) |
| `Analog.c` | Micrófonos analógicos (ADC) + cálculo de RMS |
| `SoundRX.c` / `SoundTX.c` | Camino de audio I2S (parlante / micrófono) |
| `user.c` | Configuración de periféricos (UART, I2C, I2S, RTC) |
| `config/conf_board.h` | **Mapa de pines del SAMD21** |
| `config/conf_usb.h` | Descriptor USB (CDC "QBO one") |

Y del lado de la Pi (`QBOscratch/Python projects/`): `QboCmd.py` (librería del protocolo), `feel.py` (lectura táctil), `say.py` (parlante), `PiCmd.py`, etc.

---

## 1. La placa: qué es

La Q-board es un microcontrolador **Atmel/Microchip SAMD21** (núcleo ARM Cortex-M0+), programado con el **Atmel Software Framework (ASF)**. Se programa/flashea por **JTAG/SWD** con un J-Link (ver enlaces en el README del repo). El firmware corre un bucle principal (`main.c`) que atiende: protocolo serial, animaciones de boca, LED de nariz, táctil, audio y servos.

---

## 2. Arquitectura de comunicación: hay TRES canales

```
                Raspberry Pi 3                         Q-board (SAMD21)
   ┌───────────────────────────────┐        ┌──────────────────────────────────┐
   │  /dev/serial0  (UART HW)       │◄──────►│  SERCOM5 USART  (PB22 TX/PB23 RX) │   ← CONTROL
   │  GPIO14 TXD / GPIO15 RXD       │ 115200 │  115200 8N1                       │
   │                                │        │                                   │
   │  I2S maestro                   │        │  I2S esclavo (SCK/FS externos)    │   ← AUDIO
   │  GPIO18 BCLK / GPIO19 LRCLK    │◄──────►│  PA10 SCK / PA11 FS               │
   │  GPIO21 DOUT → parlante        │───────►│  PA07 SD0 (DIN) → DAC → amplif.   │
   │  GPIO20 DIN  ← micrófono       │◄───────│  PA08 SD1 (DOUT) ← ADC del mic    │
   │                                │        │                                   │
   │  USB → /dev/ttyACM0            │◄──────►│  USB CDC "QBO one"                │   ← solo servos/flasheo
   └───────────────────────────────┘        └──────────────────────────────────┘
```

1. **Canal de CONTROL — UART (`/dev/serial0`, 115200 8N1).**
   Es el canal principal. Por acá viajan TODOS los comandos de alto nivel: display, nariz, **lectura táctil**, selección de micrófono, **reporte de nivel RMS del mic**, encender/apagar parlante, y control de servos. Confirmado en el firmware (`configure_usart_Serial()` en `user.c`, SERCOM5) y en TODOS los scripts Python (`port = '/dev/serial0'`, `serial.Serial(port, baudrate=115200, ...)`).

2. **Canal de AUDIO — I2S.**
   El audio "crudo" (PCM) NO va por la UART. Va por un bus **I2S** separado donde **la Raspberry Pi es el maestro** (genera BCLK y LRCLK) y **la placa es esclava** (`sck_src = SCKPIN`, `frame_sync.source = FSPIN` en `configure_i2s()`).
   - **Formato exacto del frame I2S (verificado en `user.c`):** Clock Unit 0 con **2 slots por frame**, **slot de 16 bits**, `data_delay = I2S` (formato I2S estándar, retardo de 1 bit), FS de ancho de slot. Los dos serializers usan `data_size = 16BIT`, `mono_mode = true` y `data_adjust_left_in_slot = true`. → En la práctica el stream se **enmarca como estéreo de 2 slots × 16 bits a ~16 kHz**, aunque el contenido es mono (`mono_mode`). Eso implica **BCLK ≈ 16000 × 2 × 16 = 512 kHz**. Este dato es clave para configurar el lado Pi (ver Guía de setup): el overlay/codec de la Pi debe declarar **16 bits, 2 canales, 16 kHz**, y el `convertQBO` adapta el mono del archivo a ese frame.
   - **Qué serializer es qué:** `SERIALIZER_1` = **TRANSMIT** sobre `I2S_DOUT`/PA08 → es el **micrófono** (placa→Pi). `SERIALIZER_0` = **RECEIVE** sobre `I2S_DIN`/PA07 → es el **parlante** (Pi→placa).
   - **Parlante:** la Pi reproduce → I2S DOUT (GPIO21) → la placa lo recibe en SD0/DIN (PA07) → lo convierte y lo manda al **DAC interno** del SAMD21 (`ConvertToDAC` en `SoundRX.c`) → amplificador (`AMP_IN1` PA02, `SPK_EN` PA27) → parlante.
   - **Micrófono:** la placa muestrea el micrófono seleccionado con su **ADC** (`Analog.c`), mete las muestras en el buffer I2S TX y las saca por SD1/DOUT (PA08) → I2S DIN de la Pi (GPIO20) → la Pi graba.

3. **Canal USB CDC (`/dev/ttyACM0`).**
   La placa también enumera por USB como dispositivo CDC llamado **"QBO one"** (VID/PID Atmel, ver `conf_usb.h`). Esto se usa **solo** para el modo "USB-to-servo forwarding" (`SET_USB2SERVO_FWD`, para configurar los servos Dynamixel XL-320 directamente desde una PC) y para tareas de flasheo. **No es el canal normal de control.**

> **Nota sobre el "shield":** el shield/HAT que une la Pi con la Q-board no es más que el cableado físico de estos tres grupos de pines (UART, I2S, USB) más alimentación. El mapa exacto está en la sección 7.

---

## 3. El protocolo serial (canal de control)

Definido en `serialProtocol.c` (firmware) y replicado en `QboCmd.py` (Pi). Es un protocolo de trama binaria con checksum.

### 3.1 Formato de trama

```
INPUT_FLAG | CMD | N | data[0] | ... | data[N-1] | PEARSON | OUTPUT_FLAG
   0xFF     1by  1by   ........ N bytes ........     1by       0xFE
```

- `INPUT_FLAG = 0xFF` — inicio de trama.
- `CMD` — código de comando (ver tabla, sección 4).
- `N` — número de bytes de datos (`nInputData`).
- `data[]` — parámetros.
- `PEARSON` — checksum de Pearson calculado sobre `CMD + N + data[]` (es decir, desde el byte siguiente a `0xFF` hasta el último dato, sin incluir los flags).
- `OUTPUT_FLAG = 0xFE` — fin de trama.

La trama mínima válida son **5 bytes** (`FF CMD 00 PEARSON FE`).

### 3.2 Escape de bytes

Como `0xFF`, `0xFE` y `0xFD` son bytes de control, cualquier byte de **datos o checksum** cuyo valor sea `>= 0xFD` se "escapa": se emite `INPUT_ESCAPE = 0xFD` seguido del byte original **menos 2**. Al recibir, tras un `0xFD` se le suma 2 al siguiente byte. (Los flags `0xFF`/`0xFE` de inicio/fin NO se escapan.)

### 3.3 Checksum de Pearson

Tabla de 256 bytes (idéntica en firmware y Python). Algoritmo:

```python
def pearson(data, length, offset):   # offset=1 (saltea el INPUT_FLAG), length=hasta el último dato
    h = 0
    for i in range(offset, length):
        h = pearsondata[h ^ (data[i] & 0xff)]
    return h
```

> En `fSerial_procesaEntrada()` el checksum **sí está activo** (un comentario viejo dice "disabled for debug" pero el código que valida está habilitado: `if (check != inCheck) return false;`). O sea: una trama con checksum malo se rechaza con NACK.

### 3.4 Respuesta y NACK

- **Respuesta OK:** misma estructura → `0xFF | CMD | nOut | out[0..nOut-1] | PEARSON | 0xFE`. Para comandos de tipo "SET" (sin retorno), `nOut = 0`.
- **NACK** (trama inválida, checksum malo, longitud incorrecta o comando desconocido): la placa responde solo **`0xFF 0xFE`** (2 bytes). `QboCmd.py` reintenta hasta 3 veces.

### 3.5 Cómo enviar/recibir (referencia Python existente)

`QboCmd.py` ya implementa todo esto. Métodos útiles:
- `Controller(serial)` — recibe un objeto `serial.Serial` ya abierto.
- `SendCmdQBO(Command(cmd, nInputs, data))` — arma trama, escapa, calcula checksum y escribe.
- `GetHeadCmd("NOMBRE_CMD", parametro)` — envía y devuelve los parámetros de respuesta ya parseados (con reintentos).
- Helpers de alto nivel: `SetMouth(matrix)`, `SetNoseColor(c)`, `SetServo(...)`, etc.

---

## 4. Tabla de comandos (resumen de `comands.h` + `serialProtocol.c`)

Para cada comando: código, nº de bytes de entrada que espera el firmware, nº de bytes de respuesta.

| Comando | Código | In | Out | Función |
|---|---|---|---|---|
| `GET_VERSION` | 0x40 | 0 | 2 | Devuelve `BOARD_ID`, `LIBRARY_VERSION` |
| **`SET_MOUTH_VALUE`** | **0x44** | **4** | 0 | **Dibuja la boca** (matriz 4×5, ver §5.1) |
| **`SET_STATE`** | **0x45** | **1** | 0 | **Color de la nariz** (RGB 3 bits, ver §5.2) |
| **`GET_TOUCH`** | **0x46** | **0** | **1** | **Lee sensores táctiles** (ver §5.3) |
| `SET_TOUCH_PARAMS` | 0x47 | 3 | 0 | Sensibilidad/canales/ciclo del CAP1203 |
| **`SET_MIC_INPUT`** | **0x4A** | **1** | 0 | **Selecciona micrófono** (0,1,2) |
| **`GET_MIC_REPORT`** | **0x4B** | **0** | **6** | **Nivel RMS de los 3 mics** (3× uint16) |
| `SET_SERVO_*` / `GET_SERVO_*` | 0x4C–0x73 | varía | varía | Control de servos Dynamixel XL-320 |
| `SET_SAMPLE_RATE` | 0x80 | — | — | Sample rate de audio |
| `SET_ADC_REF` | 0x81 | 1 | 0 | Referencia del ADC |
| `SET_DAC_REF` | 0x82 | 1 | 0 | Referencia del DAC |
| **`SET_ENABLE_SPEAKER`** | **0x86** | **1** | 0 | **Enciende/apaga el parlante** (1/0) |
| `SET_MEAN_RMS` | 0x87 | 1 | 0 | Modo media vs RMS del reporte de mic |
| `SET_USB2SERVO_FWD` | 0x88 | 1 | 0 | Activa forwarding USB→servos |
| `SAVE_CFG_NVRAM` | 0x8E | — | — | Guarda config en flash |
| `RESET_SOUND` | 0x8F | — | — | Reinicia subsistema de sonido |
| `SET_TOUCH_AUTO_OFF` | 0x90 | 4 | 0 | Ignora táctil cuando los servos se mueven |

> En **negrita** los comandos directamente relevantes para tu objetivo (display, táctil, mic, parlante).

---

## 5. Los cuatro subsistemas que querés controlar

### 5.1 Display — la boca (`Mouth.c`)

- Es una **matriz de LEDs de 4 filas × 5 columnas**, multiplexada por GPIO y refrescada a ~250 Hz por una interrupción de RTC (`fMouth_Main()`).
- Comando **`SET_MOUTH_VALUE` (0x44)**, 4 bytes. Cada byte es una fila y los **5 bits bajos** de cada byte son las columnas de esa fila.
- ⚠️ **Corrección verificada (orden de bytes invertido).** El firmware NO usa el `<<24|<<16|...` big-endian que sugiere un comentario viejo; el código activo hace `fMouth_SetData(*((uint32_t *)command_.inputData))`, un **cast little-endian** (el SAMD21 es little-endian). Combinado con `fMouth_SetData()` (que asigna `Mouth_Data[0][0]=(data>>24)&0x1f` … `[0][3]=data&0x1f`) y con `QboCmd.SetMouth(matrix)` (que envía `matrix>>24` primero), el resultado neto, **en términos del argumento `matrix`**, es:
  - bits **0–4** (byte bajo) → fila 0 (primera fila escaneada)
  - bits **8–12** → fila 1
  - bits **16–20** → fila 2
  - bits **24–28** (byte alto) → fila 3
  - Es decir, el orden está **invertido** respecto a lo que se documentó originalmente. En términos de los bytes serie crudos: `data[0]`→fila 3, `data[1]`→fila 2, `data[2]`→fila 1, `data[3]`→fila 0.
- **Geometría física confirmada: 4 filas × 5 columnas** (`conf_board.h`: 4 líneas de fila `G_ROW_0..3`=PA17–PA20, 5 líneas de columna `G_COLUMN_0..4`=PA12–PA16). El `#define NCOLUMS 4` de `Mouth.h` es un nombre engañoso: en realidad cuenta los **4 bytes-fila**, y cada byte lleva los 5 bits de columna.
- En `QboCmd.py`: `SetMouth(matrix)` recibe ese `uint32` y lo parte en 4 bytes (`matrix>>24` … `matrix&0xff`).
- Ejemplo (sonrisa, con el orden YA corregido): construí `matrix` para que el **byte bajo sea la fila superior**. Patrón por fila (fila0→fila3): `0b00000 / 0b01110 / 0b10001 / 0b00000`. Si lo enviás como en el doc viejo (`data[]=00000/10001/01110/00000`) sale **invertido** (un ceño en vez de sonrisa). *Qué extremo físico es "fila 0" (arriba o abajo) depende del cableado: confirmar en el robot real, igual que con los pines.*
- El firmware además soporta **animaciones** (hasta 12 frames, `fConfig_Animation`), aunque el comando para cargar frames arbitrarios no está expuesto en esta versión del protocolo (solo el frame 0 vía `SET_MOUTH_VALUE`). Hay frames de animación "de fábrica" precargados en `fInit_Mouth()`.

### 5.2 Nariz RGB (`fMouth_SetNoseColor`)

- Comando **`SET_STATE` (0x45)**, 1 byte. Bits: **bit0 = Azul (B)**, **bit1 = Rojo (R)**, **bit2 = Verde (G)**. (Lógica negada en hardware; el firmware ya invierte.)
- Combinaciones (0–7) dan los 8 colores básicos. Ej: `0x01`=azul, `0x02`=rojo, `0x04`=verde, `0x07`=blanco, `0x00`=apagada.
- En `QboCmd.py`: `SetNoseColor(color)`.

### 5.3 Sensores táctiles de los costados (`CAP1203.c`)

- Chip **CAP1203** (touch capacitivo de 3 canales) conectado por **I2C** (SERCOM3, dirección `0x28`, pines PA22/PA23 del SAMD21). El firmware lo poolea en `GetTouch_runtime()`.
- Comando **`GET_TOUCH` (0x46)**, 0 bytes de entrada → responde **1 byte**:
  - `1` = táctil **derecho**
  - `2` = táctil **superior/centro**
  - `3` = táctil **izquierdo**
  - `0` = sin toque
  (Mapeo confirmado en `feel.py`.)
- **Importante:** `GetPressedButton()` es *latcheado y se limpia al leer* — devuelve el último botón presionado y lo resetea a 0. Conviene poolear periódicamente (en `feel.py` se hace cada 250 ms).
- `SET_TOUCH_PARAMS` (0x47, 3 bytes) ajusta sensibilidad/promediado, canales habilitados y tiempo de ciclo (ver diccionarios `touch_*` en `QboCmd.py`).

### 5.4 Micrófono (`Analog.c`, `SoundTX.c`)

Hay **dos vías** distintas, y conviene no confundirlas:

**(a) Nivel/energía del sonido por la UART (para localización de fuente):**
- QBO tiene **3 micrófonos**. La placa los muestrea por ADC y calcula el **RMS** de cada uno.
- **`GET_MIC_REPORT` (0x4B)**, 0 in → **6 bytes** = 3 valores `uint16` (RMS × 10000) para mic 0/1/2. Sirve para saber "de qué lado vino el sonido" (girar la cabeza hacia quien habla).
- `SET_MIC_INPUT` (0x4A, 1 byte: 0/1/2) selecciona qué micrófono se enruta al stream de audio I2S.
- `SET_MEAN_RMS` (0x87) cambia entre reportar media o RMS.

**(b) Audio crudo (PCM) por I2S → para grabar/STT en la Pi:**
- El micrófono seleccionado se digitaliza y se envía por **I2S DOUT** (SD1, PA08) a la Pi. En la Pi aparece como un **dispositivo de captura ALSA** (se graba con `arecord`). Es lo que usa la Pi para Speech-to-Text.
- El sample rate del DAC/timing ronda los **16 kHz** (ver `configure_DAC_trigger_dma`: TC a 16000 Hz). El mic se muestrea coordinado con ese reloj.

### 5.5 Parlante (`SoundRX.c`)

- **`SET_ENABLE_SPEAKER` (0x86)**, 1 byte (`1` enciende, `0` apaga) — controla el pin `SPK_EN` (PA27) del amplificador. **Hay que encenderlo antes de reproducir.**
- El audio crudo se manda desde la Pi por **I2S DOUT** (GPIO21) → la placa lo recibe en SD0/DIN (PA07) → lo pasa al **DAC interno** (`ConvertToDAC`: convierte int16 con signo a unsigned, mono) → amplificador → parlante.
- En la Pi, el parlante es un **dispositivo de reproducción ALSA**. En el código original se usa el device ALSA llamado **`convertQBO`**: `aplay -D convertQBO archivo.wav` (ver `say.py`, `QBOtalk.py`). `convertQBO` es un PCM "plug" definido en `/etc/asound.conf` de la imagen original que hace conversión de sample rate hacia el codec I2S.
- `RESET_SOUND` (0x8F) reinicia el subsistema si el audio se "cuelga".

---

## 6. Resumen del flujo: "controlar X desde la Pi"

| Quiero… | Cómo, desde la Pi |
|---|---|
| Dibujar la boca | Comando `SET_MOUTH_VALUE` por `/dev/serial0` (`QboCmd.SetMouth`) |
| Cambiar color de nariz | Comando `SET_STATE` por `/dev/serial0` (`QboCmd.SetNoseColor`) |
| Leer táctiles | Poolear `GET_TOUCH` por `/dev/serial0` (`QboCmd.GetHeadCmd("GET_TOUCH",0)`) |
| Saber de qué lado vino un sonido | Poolear `GET_MIC_REPORT` por `/dev/serial0` |
| Elegir micrófono activo | `SET_MIC_INPUT` por `/dev/serial0` |
| Grabar audio del mic | `arecord` sobre el dispositivo de captura ALSA (I2S) |
| Reproducir audio por el parlante | `SET_ENABLE_SPEAKER 1` (UART) **+** `aplay -D convertQBO` (ALSA/I2S) |

El **canal serial** te resuelve display, nariz, táctil y la parte de control del audio. El **canal I2S/ALSA** te resuelve el audio crudo (grabar y reproducir). Por eso tu idea de "`/dev/serial0` para control + `/dev/...` de audio para mic/parlante" es exactamente la arquitectura correcta del robot.

---

## 7. Mapa de pines (shield): SAMD21 ↔ función ↔ Raspberry Pi

Del `conf_board.h` (lado SAMD21) y del pinout estándar de la Pi (lado Raspberry).

### Canal de control (UART)
| Función | Pin SAMD21 | Pin Raspberry Pi |
|---|---|---|
| UART TX (placa→Pi) | PB22 (SERCOM5) | GPIO15 / RXD (pin 10) |
| UART RX (Pi→placa) | PB23 (SERCOM5) | GPIO14 / TXD (pin 8) |
| Baud | 115200 8N1 | `/dev/serial0` |

### Canal de audio (I2S) — la Pi es maestro
| Función | Pin SAMD21 | Pin Raspberry Pi |
|---|---|---|
| Bit clock (BCLK/SCK) | PA10 | GPIO18 / PCM_CLK (pin 12) |
| Word/frame clock (LRCLK/FS) | PA11 | GPIO19 / PCM_FS (pin 35) |
| Parlante: Pi→placa | PA07 (SD0 / I2S_DIN) | GPIO21 / PCM_DOUT (pin 40) |
| Micrófono: placa→Pi | PA08 (SD1 / I2S_DOUT) | GPIO20 / PCM_DIN (pin 38) |

### Pines internos de la placa (no van a la Pi, para referencia)
| Función | Pin SAMD21 |
|---|---|
| Boca: columnas 0–4 | PA12–PA16 |
| Boca: filas 0–3 | PA17–PA20 |
| Nariz G / B / R | PA21 / PB02 / PB11 |
| Táctil CAP1203 I2C (SDA/SCL) | PA22 / PA23 (SERCOM3, addr 0x28) |
| Micrófonos 1/2/3 (ADC) | PB08 / PB09 / PA03 |
| Habilitar parlante (`SPK_EN`) | PA27 |
| Entrada amplificador (`AMP_IN1`, salida DAC) | PA02 |
| Habilitar servos (`SERVO_EN`) | PA06 |
| Bus servos XL-320 (UART) | PB10 (SERCOM4, 1 Mbaud) |

> ⚠️ **Verificar físicamente:** el conexionado exacto del conector entre la Q-board y la Pi conviene confirmarlo con un multímetro/continuidad sobre la placa real antes de cablear nada nuevo, porque pudo haber adaptadores intermedios en el shield. Los pines GPIO de la Pi de arriba son los **estándar de la función** (UART e I2S del SoC), que es lo que el driver de la Pi va a usar.

---

## 8. Qué falta / próximos pasos

1. **Audio del lado Pi:** este repo no incluye `/boot/config.txt` ni `/etc/asound.conf` de la imagen original. Para reproducir/grabar hay que (a) habilitar I2S con la Pi como maestro vía device tree, y (b) definir el dispositivo ALSA `convertQBO`. Eso está cubierto en la *Guía de setup en la Pi 3*.
2. **Modernizar el código:** `QboCmd.py` está en **Python 2.7**. Para el proyecto geriátrico conviene portarlo a Python 3 (es directo: `print()`, `has_key`→`in`, `ord()`/bytes). Puedo generártelo cuando quieras.
3. **Servos:** quedan fuera del alcance de este documento (display/táctil/mic/parlante), pero el mismo protocolo serial los cubre (`SET_SERVO*`, `GET_SERVO*`) y los motores son Dynamixel XL-320.

---

*Fuentes: código fuente del firmware (`serialProtocol.c`, `comands.h`, `Mouth.c`, `CAP1203.c/.h`, `Analog.c`, `SoundRX.c`, `SoundTX.c`, `user.c`, `config/conf_board.h`, `config/conf_usb.h`) y código Python de la Pi (`QboCmd.py`, `feel.py`, `say.py`) del repositorio QBOscratch.*
