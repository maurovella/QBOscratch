# QBO — Problema de audio: `sndrpisimplecar` y `convertQBO`

Documento de contexto para continuar el diagnóstico en Cursor.

---

## Objetivo

Hacer que el robot **QBO** hable por su **altavoz integrado** (Q-board vía I2S), no por el jack 3.5 mm ni HDMI del Raspberry Pi.

---

## Causa raíz (confirmada)

El audio del QBO **no viene de un `dtoverlay`**. Lo crea el módulo kernel **`my_loader`**, del proyecto [PaulCreaser/rpi-i2s-audio](https://github.com/PaulCreaser/rpi-i2s-audio).

Al cargarse al boot, `my_loader` registra la tarjeta ASoC **`snd_rpi_simple_card`**, que ALSA expone como **`sndrpisimplecar`** (card 1 en la SSD vieja).

```
/etc/modules  →  my_loader  →  snd_rpi_simple_card  →  sndrpisimplecar
                                                      →  convertQBO (asound.conf)  →  altavoz QBO
```

**Copiar solo `/etc/asound.conf` no alcanza** sin `my_loader` cargado.

---

## Síntomas observados

### SSD nueva (Raspbian 13 Trixie, `armv7l`)

| Componente | Estado |
|------------|--------|
| `pico2wave` (TTS) | Instalado (`.deb` manual: `libttspico-data`, `libttspico0t64`, `libttspico-utils` desde Debian `non-free`) |
| `aplay /tmp/test.wav` | Suena por **jack/HDMI del Pi**, no por el robot |
| `aplay -L \| grep convert` | Aparece tras copiar `asound.conf` |
| `aplay -l` | Solo `card 0: Headphones` y `card 1: vc4hdmi` — **no hay `sndrpisimplecar`** |
| `aplay -D convertQBO ...` | Error: `Slave PCM not usable` / `Broken configuration for this PCM` |
| `my_loader` | **No instalado / no cargado** |
| Kernel headers para compilar | `raspberrypi-kernel-headers` y `linux-headers-rpi-v7l` **no encontrados** en apt |

### SSD vieja (funcionaba)

| Componente | Estado |
|------------|--------|
| Kernel | **`4.9.41-v7+`** |
| `aplay -l` | `card 1: sndrpisimplecar [snd_rpi_simple_card], device 0: simple-card_codec_link` |
| `arecord -l` | Misma tarjeta `sndrpisimplecar` |
| `aplay -D convertQBO ...` | Robot habla |
| `pico2wave` + `aplay -D convertQBO` | Funciona |
| `sudo dtoverlay -l` | **No overlays loaded** |
| `find /lib/modules -name "my_loader*"` | `/lib/modules/4.9.41-v7+/my_loader.ko` |
| `find /lib/modules -iname "*simple*"` | Vacío (el módulo se llama `my_loader`, no `*simple*`) |
| `ls -la /boot/overlays/i2s-mmap.dtbo` | **No existe** |

---

## Arquitectura de audio del QBO

```
Texto → pico2wave → archivo .wav (16 kHz mono)
                         ↓
              aplay -D convertQBO
                         ↓
              /etc/asound.conf: pcm.convertQBO
                         ↓
              pcm_slave.sl1 → hw:1,0 (16 kHz, estéreo, S16_LE)
                         ↓
              Tarjeta ALSA: sndrpisimplecar (I2S del Q-board)
                         ↓
              Altavoz del robot
```

**No es USB.** El audio del QBO va por **I2S** entre la Pi y el Q-board.

---

## Configuración confirmada en SSD vieja

### `/etc/modules`

```
i2c-dev
snd-bcm2835
my_loader
```

### `/boot/config.txt`

```
dtparam=i2s=on
dtparam=audio=on
dtoverlay=i2s-mmap
```

**Notas:**

- `dtoverlay=i2s-mmap` está en `config.txt` pero el `.dtbo` **no existe** y `dtoverlay -l` muestra **ningún overlay cargado**. Es legacy (kernels pre-4.7) y **no es lo que crea la tarjeta de audio**.
- En Trixie, `config.txt` está en **`/boot/firmware/config.txt`**.
- Lo esencial para I2S: **`dtparam=i2s=on`** + **`my_loader`**.

### Módulo kernel

| Propiedad | Valor |
|-----------|--------|
| Origen | [github.com/PaulCreaser/rpi-i2s-audio](https://github.com/PaulCreaser/rpi-i2s-audio) (`my_loader.c`) |
| Ruta SSD vieja | `/lib/modules/4.9.41-v7+/my_loader.ko` |
| Kernel compilado para | `4.9.41-v7+` |
| **¿Copiable a Trixie?** | **NO** — hay que recompilar para el kernel 6.x de Trixie |

### Dirección I2S en `my_loader.c`

| Pi | `.platform` en código |
|----|----------------------|
| Pi 2 / Pi 3 / Zero (`v7+`) | `3f203000.i2s` (default) |
| Pi 4 / Pi 5 | `20203000.i2s` (requiere editar `my_loader.c`) |

La SSD vieja usa kernel `v7+` → Pi 3 → **`3f203000.i2s`** es correcto.

---

## Archivos ALSA

### `/etc/asound.conf` (SSD vieja)

```alsa
pcm.convertQBO {
   type plug
   slave sl1
}

pcm_slave.sl1 {
   pcm "hw:1,0"
   channels 2
   rate 16000
   format S16_LE
}

pcm.dmicQBO_sv {
   type softvol
   slave.pcm dmicQBO
   control {
      name "Boost Capture Volume"
      card sndrpisimplecar
   }
   min_dB -10.0
   max_dB 30.0
}

pcm.dmicQBO {
   type hw
   channels 2
   rate 16000
   format S16_LE
   # Falta "card sndrpisimplecar" en el archivo pegado — verificar en SSD vieja
}
```

### `/home/pi/.asoundrc` (SSD vieja, fragmento)

```alsa
pcm.!default {
   type asym
   capture.pcm "mic"
   playback.pcm "speaker"
}

pcm.mic {
   type plug
   slave.pcm dmicQBO
}

pcm.speaker {
   type plug
   slave all
}
# pcm_slave.all no estaba en el fragmento pegado — copiar archivo completo desde SSD vieja
```

### Código Python que usa `convertQBO`

- `Python projects/say.py`
- `Python projects/QBOtalk.py`
- `Python projects/PiFaceFast.py`

```bash
pico2wave -l "es-ES" -w /home/pi/Documents/pico2wave.wav "..." && aplay -D convertQBO /home/pi/Documents/pico2wave.wav
```

### Micrófono (para `listen.py` / `QBOtalk.py`)

Buscan el dispositivo ALSA virtual **`dmicQBO_sv`** por nombre (`QBOtalk.py`).

---

## Por qué falla en la SSD nueva

### 1. Falta `my_loader` → no hay `sndrpisimplecar`

En Trixie, `aplay -l` muestra:

```
card 0: Headphones [bcm2835 Headphones]
card 1: vc4hdmi [vc4-hdmi]
```

En la SSD vieja, **`card 1` era `sndrpisimplecar`**, no HDMI.

### 2. `asound.conf` apunta al dispositivo equivocado

`pcm_slave.sl1` usa `hw:1,0`. En Trixie eso es **HDMI**, que no acepta 16 kHz estéreo:

```
ALSA lib pcm_params.c: Slave PCM not usable
aplay: Broken configuration for this PCM
```

### 3. El `.ko` de la SSD vieja no sirve en Trixie

| SSD vieja | SSD nueva |
|-----------|-----------|
| Kernel `4.9.41-v7+` | Kernel `6.x` (Trixie) |
| `my_loader.ko` compilado para 4.9 | Requiere **recompilación** |

---

## Bloqueo actual: kernel headers en Raspbian Trixie

Al intentar recompilar `my_loader` en la SSD nueva:

```bash
sudo apt install raspberrypi-kernel-headers   # Error: paquete no encontrado
sudo apt install linux-headers-rpi-v7l        # Error: paquete no encontrado
```

**Motivo:** el sistema es **Raspbian GNU/Linux 13 (Trixie)** con repos `raspbian.sources` + `raspi.sources`, no Raspberry Pi OS completo. En Trixie armhf los paquetes de headers del kernel RPi a veces **no están en apt** o tienen otro nombre.

### Paquetes obsoletos vs actuales

| Paquete | Estado en Trixie |
|---------|------------------|
| `raspberrypi-kernel-headers` | Obsoleto, no existe |
| `linux-headers-rpi-v7l` | De Pi OS; **no encontrado** en Raspbian Trixie armhf probado |

### Diagnóstico de headers (ejecutar en SSD nueva)

```bash
uname -a
uname -r
apt search linux-headers 2>/dev/null | head -40
apt list 'linux-headers*' 2>/dev/null | grep -iE "rpi|installed"
apt list "linux-headers-$(uname -r)" 2>/dev/null
ls -la /lib/modules/$(uname -r)/build 2>&1
cat /etc/apt/sources.list.d/raspbian.sources
cat /etc/apt/sources.list.d/raspi.sources
```

### Alternativas si apt no tiene headers

**Opción A — Buscar paquete exacto:**

```bash
sudo apt install "linux-headers-$(uname -r)"
# o probar:
sudo apt install linux-headers-rpi-v7
```

**Opción B — `rpi-update`** (kernel de GitHub con árbol `build`):

```bash
sudo apt install git
sudo rpi-update
sudo reboot
# Tras reboot:
ls -d /lib/modules/$(uname -r)/build
```

**Opción C — Clonar kernel** (lento, mucho espacio):

```bash
git clone --depth=1 --branch rpi-6.12.y https://github.com/raspberrypi/linux
cd linux
make bcm2709_defconfig
make modules_prepare
sudo ln -sf $(pwd) /lib/modules/$(uname -r)/build
```

---

## Plan de recuperación (orden de prioridad)

### 1. SSD nueva — sistema base

**`/boot/firmware/config.txt`:**

```
dtparam=i2s=on
dtparam=audio=on
```

(`dtoverlay=i2s-mmap` no es necesario.)

**`/etc/modules`:**

```
i2c-dev
snd-bcm2835
my_loader
```

**Copiar desde SSD vieja:**

- `/etc/asound.conf`
- `/home/pi/.asoundrc` (archivo completo)

### 2. SSD nueva — instalar headers del kernel

Resolver el bloqueo de headers (ver sección anterior). Verificar:

```bash
ls -d /lib/modules/$(uname -r)/build
```

### 3. SSD nueva — recompilar `my_loader`

```bash
sudo apt install git build-essential
git clone https://github.com/PaulCreaser/rpi-i2s-audio
cd rpi-i2s-audio

# Pi 3 / v7+: dejar 3f203000.i2s (default en my_loader.c)

make -C /lib/modules/$(uname -r)/build M=$(pwd) modules
```

Si compila:

```bash
sudo mkdir -p /lib/modules/$(uname -r)/extra
sudo cp my_loader.ko /lib/modules/$(uname -r)/extra/
sudo depmod -a
sudo reboot
```

**Riesgo:** `my_loader.c` es de 2017 (kernel 4.9). En kernel 6.x la compilación puede **fallar** (APIs ALSA/ASoC cambiaron: `asoc_simple_card_info`, etc.). Si `make` falla, pegar el error completo.

### 4. Verificar tras reboot

```bash
lsmod | grep my_loader
dmesg | grep -iE "my_loader|simple.card|snd_rpi"
aplay -l
arecord -l
aplay -L | grep convertQBO
```

**Éxito = aparece `sndrpisimplecar`.** Si no es card 1, ajustar `hw:1,0` en `/etc/asound.conf`.

### 5. Prueba final

```bash
pico2wave -l "es-ES" -w /tmp/test.wav "Hola"
aplay -D convertQBO /tmp/test.wav
```

Luego vía proyecto:

```bash
pico2wave -l "es-ES" -w /home/pi/Documents/pico2wave.wav "Hola" && aplay -D convertQBO /home/pi/Documents/pico2wave.wav
python3 PiCmd.py -c say -t "Hola"
```

(con `say.py` corriendo o `./QBO_scratch start`)

---

## Otros problemas de la misma migración (contexto)

| Tema | SSD vieja | SSD nueva |
|------|-----------|-----------|
| Cámaras OpenCV | Índices `0` y `1` | Índices `0` y `2` (nodos V4L2 extra por cámara) |
| `libttspico-utils` | En repos o instalado | Instalación manual `.deb` Debian (`libttspico0t64` en Trixie; URL con `%2B` en lugar de `+`) |
| Flag `pico2wave` | README dice `-2` | Correcto: **`-w`** |
| `config.yml` | `/home/pi/Documents/config.yml` | Mismo path en Pi |

---

## Comandos de diagnóstico rápido

```bash
# ¿Módulo cargado?
lsmod | grep my_loader

# ¿Existe convertQBO?
aplay -L | grep -i convert

# ¿Qué tarjetas hay?
aplay -l
cat /proc/asound/cards

# ¿I2S habilitado?
grep -E "dtparam|dtoverlay|i2s" /boot/firmware/config.txt

# ¿Headers para compilar?
ls -d /lib/modules/$(uname -r)/build

# ¿Slave roto o hardware ausente?
pico2wave -l "es-ES" -w /tmp/test.wav "test"
aplay -D convertQBO /tmp/test.wav
```

---

## Riesgos conocidos

1. **`my_loader` no compila en kernel 6.x** — APIs de ALSA cambiaron desde 4.9. Puede requerir parchear `my_loader.c` o usar un device tree overlay `simple-audio-card` moderno.
2. **Raspbian Trixie armhf sin headers en apt** — gap conocido en repos; `rpi-update` o clonar kernel como workaround.
3. **Foro theCorpora** — varios reportes de audio QBO que no funciona en Pi OS recientes (Buster+). La SSD vieja con kernel 4.9 era el entorno original.
4. **Último recurso** — imagen Pi OS / Raspbian más vieja (Stretch/Buster) donde el QBO ya tenía audio probado.

---

## Estado actual

| Item | Estado |
|------|--------|
| Causa raíz identificada | `my_loader.ko` + `/etc/modules` |
| `pico2wave` en SSD nueva | Funciona |
| `/etc/asound.conf` copiado | Sí → `convertQBO` visible en ALSA |
| `sndrpisimplecar` en SSD nueva | **No aparece** |
| `my_loader.ko` en SSD nueva | **No instalado** (`.ko` de 4.9 no es portable) |
| Recompilación `my_loader` | **Bloqueada** — sin kernel headers en apt |
| `aplay -D convertQBO` | Falla (`hw:1,0` = HDMI) |

---

## Próximo paso concreto para el agente

1. En SSD nueva: ejecutar diagnóstico de headers (`uname -a`, `apt list 'linux-headers*'`, `ls /lib/modules/$(uname -r)/build`).
2. Instalar headers vía apt exacto, `rpi-update`, o clonar kernel — lo que funcione en ese sistema.
3. Recompilar `rpi-i2s-audio` y instalar `my_loader.ko`.
4. Confirmar `/etc/modules` y `dtparam=i2s=on`, reboot.
5. Verificar `sndrpisimplecar` en `aplay -l` → probar `aplay -D convertQBO`.
6. Si `make` falla en kernel 6.x → evaluar parche de `my_loader.c` o overlay DT alternativo.

---

## Referencias

### En este repo

- `README.md` — comando manual de prueba de voz
- `Python projects/say.py` — daemon TTS con `convertQBO`
- `Python projects/config.yml` — `language`, `volume` (TTS software, no hardware)
- `Python projects/QBOtalk.py` — micrófono `dmicQBO_sv`

### Externas

- [PaulCreaser/rpi-i2s-audio](https://github.com/PaulCreaser/rpi-i2s-audio) — fuente de `my_loader.c`
- [Raspberry Pi kernel headers docs](https://www.raspberrypi.com/documentation/computers/linux_kernel.html)
- [Foro theCorpora — audio QBO en Pi OS recientes](https://thecorpora.com/community/ros-robot-operating-system/configure-raspberry-to-control-serial-ports/)

---

*Última actualización: sesión de diagnóstico — migración QBO de SSD vieja (kernel 4.9.41-v7+) a Raspbian 13 Trixie (32-bit).*
