# Migración de QBO y Tooly a Python 3.13 y Raspbian 13

Rama `migracion-py3`, octubre de 2026. Antes: Raspbian 9, Python 2.7, kernel 4.9.
Ahora: Raspbian 13 (trixie), Python 3.13, kernel 6.x.

Todo el código Python del repo compila y pasa los tests con Python 3.13. Nada de
esto corrió todavía en el robot. La sección "Qué no se pudo verificar" dice
exactamente qué falta, y `scripts/smoke/smoke.sh` es lo que hay que correr cuando
el robot esté disponible.

## Cómo verificar sin el robot

```sh
scripts/check.sh          # gate sintáctico + 978 tests, unos 2 minutos
scripts/check.sh --fast   # solo el gate sintáctico
```

Usa `uv` si está instalado (fija Python 3.13). Si no, instalar
`requirements-dev.txt` y correr con `PYTHON=python3.13 scripts/check.sh`.

Qué comprueba:

| Qué | Cómo | Archivo |
| --- | --- | --- |
| Todos los `.py` compilan y no tienen nombres indefinidos | `compile()` y pyflakes sobre los archivos trackeados. `scripts/known_failing.txt` empezó con 21 entradas y está vacío | `scripts/check_syntax.py` |
| El protocolo UART emite los mismos bytes que en Python 2.7 | 461 casos ejecutados sobre el `QboCmd.py` original en Docker `python:2.7-slim` y guardados en `tests/golden/protocol_py2.json` | `tests/test_protocol.py` |
| Cada script hace lo mismo que en Python 2.7 | 94 escenarios contra un robot de mentira. Se compara el registro de bytes por la UART, argumentos que recibe `pico2wave`, pedidos HTTP, mails y datos en los FIFOs | `tests/test_apps_golden.py` |
| El cliente LLM | `requests` real contra un servidor HTTP local con guion | `tests/test_llm.py`, `tests/test_tooly_ollama.py` |
| Los puentes de `Python projects/` que lanzan los daemons, y sus permisos | Se ejecuta cada puente y se mira el modo en el índice de git | `tests/test_bridges.py` |
| FIFOs, `config.yml`, alertas por mail, dependencias, smoke test | | `tests/test_fifo.py` y siguientes |

El golden master se regenera con `tests/golden/generate.sh`. Necesita Docker y la
rama `legacy-python2`. No instala Python 2 en el sistema.

### El robot de mentira

`tests/harness/run_app.py` corre un script del robot con dobles de `serial`
(con un simulador mínimo de la Q-board), `cv2`, `speech_recognition`, `requests`
y `smtplib`. Pone `pico2wave` y `aplay` falsos en el `PATH`, usa FIFOs reales y un
reloj falso, así `sleep(10)` no espera. El mismo arnés corre en Python 2.7 y en
3.13, y por eso los dos registros son comparables.

Un escenario es un guion: qué caras ve la cámara, qué oye el micrófono, qué
contesta el LLM, qué toca la persona. Por ejemplo, "cuatro horas de silencio y
alerta por mail" recorre las 960 vueltas de espera, los dos mails y la respuesta
final en menos de un segundo.

## Resultado de la comparación contra Python 2.7

| Componente | Casos | Idénticos | Difieren |
| --- | --- | --- | --- |
| Protocolo UART (`qbo/protocol.py`) | 461 | 448 | 13 |
| `PiCmd.py` | 51 | 48 | 3 |
| `say.py` | 12 | 7 | 5 |
| `feel.py`, `findFace.py` | 3 | 3 | 0 |
| Tooly (`TrackAndTalk.py`, `llama2Connection.py`, `repeat.py`) | 13 | 11 | 2 |
| `autoStart.py`, `autoStop.py` | 10 | 10 | 0 |
| `RTQR.py` | 5 | 4 | 1 |

Cada diferencia está listada en el test con su motivo y con un chequeo del
resultado nuevo. Son de cuatro tipos.

1. **Decodificado de escape en `ReadResponse()`**, 6 casos. Python 2 leía `0xFF`
   después de cualquier `0xFD` y descartaba el byte siguiente. El firmware emite
   `0xFD` seguido de `valor - 2` (`serialProtocol.c`, líneas 643 a 650). La
   versión migrada decodifica como el firmware. Lo había cambiado `d0e07b4`.
2. **Parámetro único pasado como lista**, 6 casos, y un parámetro negativo, 1
   caso. En Python 2 `GetHeadCmd("RESET_SERVO", 1)` tiraba `TypeError`.
3. **Parser de `PiCmd.py`**, 3 casos de eventos y 1 de salida por pantalla.
   Opciones después de `-t` o `-p`, la palabra `help` dentro de un texto, y
   `-c listen`.
4. **Texto interpretado por la shell**, 8 casos. El TTS armaba el comando con
   comillas dobles y `shell=True`. En Python 2, una respuesta del LLM con
   `` `echo boo` `` ejecutaba `echo boo` en el robot, y un QR con una comilla en
   el SSID inyectaba comandos al lado de un `sudo`. Ahora el texto llega literal.
   Incluye el caso de `say.py`, que cortaba el mensaje del FIFO a 100 bytes.

## Qué cambió

### Estructura

```text
qbo/            código compartido: protocol.py (ex QboCmd.py), paths.py, tts.py,
                touch.py (ex pet.py), notify.py (ex emailSender.py), llm/, legacy/, data/
apps/           ejecutables: picmd, say, listen, feel, find_face, face_follow
                (ex PiFaceFast), tooly (ex TrackAndTalk), tooly_audio, repeat
tools/          scripts de prueba manual: ojos, estéreo, servos, camera_probe
Python projects/  un puente de 6 líneas por cada script que lanzan los daemons
deamonsScripts/ sin mover. Las rutas /home/pi/Documents/... son las mismas
deploy/         install.sh, paquetes apt, units de systemd
scripts/        check.sh (gate) y smoke/ (escalera para el robot)
tests/
```

Se borraron de esta rama los duplicados: `Python projects/Tooly/` entera, las
copias Python 2 dentro de `Tooly/`, `llama2ConnectionWS.py`, `Stereo2.py` y
`Python projects/config.yml`. Todo sigue en la rama `legacy-python2`, que además
recibió `work-QBOscratch/`, una cuarta copia que estaba solo en la SSD vieja.

### Python 2 a 3

- `print`, tabs y espacios mezclados, shebangs, `has_key`.
- `pipes`, `thread` y `apiai` eran imports sin uso en los archivos de Tooly. Se
  borraron. `PiFaceFast` usa `_thread`.
- `audioop`: la única función que lo usaba, `downsampleWave_2()`, no se llamaba
  desde ningún lado y nunca lo había importado. Se borró.
- `w/2` pasó a `w//2`. Con `/` el desplazamiento de la cara queda float y
  `>> 1` tira `TypeError`.
- `fface != ()` pasó a `len(fface) > 0`. Con numpy 2 esa comparación tira
  `ValueError` justo cuando hay una cara.
- `cv2.cv.CV_*` pasó a `cv2.CAP_PROP_*` y `cv2.CASCADE_*`, combinadas con `|`.
- bytes: `os.write()` sobre los FIFOs recibe bytes, y `say.py` lee hasta EOF
  antes de decodificar.
- `autoStop.py` declaraba `coding: latin-1` con el texto en UTF-8. En Python 3
  eso rompía el "Adíos". Se quitó la declaración.

### TTS

`qbo/tts.py` ejecuta `pico2wave` y `aplay -D convertQBO` con listas de
argumentos, sin shell. Mismos programas, mismos argumentos, misma voz. Para
cambiar de motor se toca solo ese archivo.

### LLM

`qbo/llm` expone `chat(mensaje) -> texto` con dos clientes.

- `tooly_legacy`: el servidor FastAPI original. Es el default si `config.yml`
  no dice nada, así un archivo viejo se comporta como antes.
- `ollama`: `POST /api/chat`. Hace en el cliente lo que hacía `apiTooly.py` en
  el servidor, con los mismos valores: prompt de sistema `TOOLY_ASSITANCE_TEXT`
  copiado de `contants.py`, historial que al llegar a 8 mensajes conserva el de
  sistema y los últimos 6, 256 tokens de respuesta y `clean_text()`.

Claves nuevas de `config.yml`: `llm_backend`, `llm_host`, `llm_model`,
`llm_timeout_s`, `llm_retries` y `camera_index`. `QBO_LLM_HOST` pisa a `llm_host`.

Un cambio de comportamiento, pedido: si el LLM deja de responder en medio de
una charla, el robot dice "My mind is not ready, I will repeat whatever you
say." y repite lo que oyó. Antes el programa terminaba con un traceback.

### Credenciales

`qbo/notify.py` lee `QBO_SMTP_USER`, `QBO_SMTP_PASSWORD` y `QBO_ALERT_TO` del
entorno. La cuenta, la contraseña y la dirección personal del destinatario ya no
están en el código. Sin esas variables el robot avisa por pantalla y no manda el
mail. `QBOtalk` dejó de imprimir el token de Dialogflow.

## Decisiones tomadas

La Fase 0 dejó doce preguntas abiertas y la respuesta fue "resolvelas con tu
criterio". Esto es lo que se decidió. Todas se pueden revertir.

| Tema | Decisión | Por qué |
| --- | --- | --- |
| Dónde commitear | Rama `migracion-py3` en el clon al día. Sin push. El submódulo de `ITBA/PF` no se tocó | Nada sale a GitHub sin que lo veas |
| Layout | `qbo/`, `apps/`, `tools/`. `deamonsScripts/` quedó donde estaba | Mover los daemons cambiaba rutas absolutas que no se pueden probar |
| Arreglos que había metido `d0e07b4` | Se conservan todos | Revertirlos devuelve bugs conocidos. Los del protocolo y del parser quedaron fijados por tests |
| Golden master con escape | Se acepta que Python 3 difiera de Python 2 | Python 2 decodificaba mal. El valor esperado sale del firmware |
| Modo Scratch | Se conserva, portado | scratchx.org ya no existe, pero borrar no era necesario |
| Dialogflow y Google Assistant | Código conservado en `qbo/legacy/`, `apiai` opcional | Los servicios están apagados. `listen.py` solo necesita la transcripción |
| `RTQR.py` (WiFi por QR) | Portado | Ver riesgos: depende de `wpa_supplicant.conf` |
| `pico2wave` | Se conserva | Mantiene la voz. Funciona en Debian trixie armhf |
| 32 o 64 bits | Sin cambio | Es una decisión de reinstalación, no de código |
| Ollama | `config.yml` apunta a `http://10.16.1.190:11434` con `qwen2.5:7b-instruct` | Es el servidor y el modelo ya instalados para la tesis |
| Alertas por mail | Se conservan, con credenciales por entorno | |
| `pi/work/QBOscratch` | Guardado en `legacy-python2` | Tiene `TestServ.py`, el script más usado del robot |

## Bugs preexistentes

Arreglados, cada uno en su commit y con test:

- `downsampleWav()` y `downsampleWave_2()`: código muerto con `NameError`.
- `PiCmd.py` importaba `QBOtalk` sin usarlo y no arrancaba sin `apiai`.
- `QBOtalk` exigía `apiai` e imprimía el token.
- `PiFaceFast.py` importaba Google Assistant aunque el modo pedido fuera Dialogflow, y no arrancaba sin esa librería.
- `websocket_server.c` no incluía `fcntl.h` ni `sys/stat.h` y no compilaba con gcc 14.
- Inyección de shell en el TTS y en `RTQR.py`.

Reportados y sin tocar, porque arreglarlos cambia cómo se comporta el robot:

| Dónde | Qué pasa |
| --- | --- |
| `apps/tooly.py`, `Start()` | `self.Decode(audio, timeout)`: `Decode` acepta un argumento. `TypeError` si hubo caricia y no hubo voz |
| `apps/tooly.py`, `Decode()` | Si Google falla, devuelve "Could not request results..." y ese texto va al LLM como si lo hubiera dicho la persona |
| `apps/tooly.py` | `listen(timeout=1000)`: espera hasta 1000 segundos |
| `apps/tooly.py` | `(offset > -20) or (offset < 20)` es siempre verdadero. El límite de giro no limita |
| `apps/tooly.py` | Tras la alerta, repite "I am notifying your relatives" sin fin hasta que alguien contesta |
| `apps/tooly.py` y `qbo/touch.py` | Dos conexiones abiertas a `/dev/serial0` en el mismo proceso |
| `apps/tooly.py` | En inglés el volumen está fijo en 40 |
| `apps/picmd.py` | `-c say` se queda esperando si `say.py` no está corriendo. Hay un test que lo documenta |
| `apps/picmd.py` | `-c servo` no acepta ángulo 0, y la ayuda dice ±180 cuando el rango real es ±800 |
| `apps/picmd.py` y los demás lectores de FIFO | Leen hasta EOF y reabren. Dos mensajes muy seguidos pueden perder el segundo, porque Linux descarta lo escrito mientras nadie tiene el FIFO abierto |
| `deamonsScripts/autoStart.py` | La línea que lanza el modo interactivo está comentada |
| `deamonsScripts/writeWiFi.sh` | `[ $currentUser=root ]` es siempre verdadero |
| Código original en Python 2 | Con la salida redirigida a un archivo, un `print` con acentos tiraba `UnicodeEncodeError`. En Python 3 no pasa |

## Sistema operativo

### PEP 668

`pip install` global está bloqueado en trixie. `deploy/install.sh` instala todo
lo compilado por apt y crea `~/qbo-venv` con `--system-site-packages`. Por pip
entra solo `SpeechRecognition`, que no tiene paquete apt.

Verificado en un contenedor `debian:trixie` `linux/arm/v7`:

| Paquete | Versión |
| --- | --- |
| Python | 3.13.5 |
| `python3-serial` | 3.5 |
| `python3-opencv` | 4.10.0 |
| `python3-numpy` | 2.2.4 |
| `python3-yaml` | 6.0.2 |
| `python3-requests` | 2.32.3 |
| `python3-pyaudio` | 0.2.13 |
| `python3-audioop-lts` | 0.2.1 |
| `SpeechRecognition` (pip, en el venv) | 3.17.0 |
| `libttspico-utils` (Debian non-free) | 1.0+git20130326-14.1 |

En ese contenedor todos importan, OpenCV 4.10 carga las dos cascadas Haar del
repo y el `pico2wave` real genera un WAV de 16 kHz mono con los argumentos de
`qbo/tts.py`.

La suite completa corrió ahí, con los paquetes de apt y el venv, bajo emulación:
973 de 974 tests pasaron. El que falló agotaba un límite de 15 segundos reales
que la emulación no cumple; con el límite ampliado pasa, verificado en una
corrida aparte de `tests/test_fifo.py`. También corre en `python:3.13-slim`
(Linux arm64) con las versiones de `requirements.txt`.

No usar `opencv-python` 5.x: no tiene `cv2.CascadeClassifier`. `requirements.txt`
lo fija en 4.10.

### pico2wave

Debian trixie lo tiene en `non-free`. Raspbian de 32 bits no: solo trae
`libttspico-data`. Ahí hay que instalar los tres `.deb` de Debian a mano.
`deploy/install.sh` detecta si falta y dice cómo. En Raspberry Pi OS de 64 bits
entra con `apt install libttspico-utils`.

Si hubiera que reemplazarlo: `espeak-ng` 1.52 está en apt. Piper no sirve en 32
bits porque `onnxruntime` no tiene wheel `armv7l`.

### UART

- `config.txt` y `cmdline.txt` están en `/boot/firmware/`.
- `sudo raspi-config nonint do_serial_hw 0` habilita el puerto y
  `do_serial_cons 1` saca la consola serie.
- La SSD vieja solo tenía `enable_uart=1`. No usaba `disable-bt`: la Q-board
  andaba sobre el mini-UART. Si con un modo no responde, probar el otro.

`docs/Guia_setup_Pi3_QBO.md` quedó actualizada.

### Audio

Es el punto sin camino verificado. Micrófono y parlante dependen de la tarjeta
`sndrpisimplecar`, que crea el módulo de kernel `my_loader`.

- `audio/rpi-i2s-audio/my_loader.c` no compilaba en el kernel nuevo por dos
  nombres que cambiaron: `struct asoc_simple_card_info` pasó a
  `struct simple_util_info` en Linux 6.7, y `SND_SOC_DAIFMT_CBS_CFS` pasó a
  `SND_SOC_DAIFMT_CBC_CFC`. Con dos definiciones de compatibilidad compila
  para los kernels 6.12.75 y 6.18.50 de Raspberry Pi (`rpi-v7`), verificado en
  un contenedor armhf con los headers oficiales. **Nunca se cargó**: eso solo
  se puede hacer en la Pi. Los pasos están en `audio/rpi-i2s-audio/README.md`.
- Los headers existen. El paquete para una Pi 3 con kernel de 32 bits es
  `linux-headers-rpi-v7`. La documentación anterior había probado
  `raspberrypi-kernel-headers` y `linux-headers-rpi-v7l`, que no existen ahí.
- `convertQBO` no está definido en `asound.conf` ni en `system/asound.conf`.
  `system/asound-convertQBO.conf` es una reconstrucción a partir del fragmento
  de `docs/QBO-AUDIO-sndrpisimplecar.md`, que nombra la tarjeta en vez de usar
  `hw:1,0`. ALSA la parsea. No se probó con la tarjeta real.
- El módulo hay que recompilarlo en cada actualización de kernel, salvo que se
  arme con DKMS.

### Cámaras

Todo indica que son USB/UVC: la Pi 3 tiene un solo puerto CSI y el robot usa
dos, `/etc/modules` de la SSD vieja no carga `bcm2835-v4l2`, y en el kernel
nuevo los índices pasaron de 0 y 1 a 0 y 2. No está confirmado con `lsusb`.
`cv2.VideoCapture` sigue sirviendo. `tools/camera_probe.py` dice qué índices
entregan imagen.

### Daemons

Los `QBO_*` no se reescribieron. Dependen del shebang y del bit de ejecución,
que ahora está en git. `deploy/systemd/` trae dos units, ninguna habilitada:
`qbo-tooly.service` y `qbo-scratch.service`, que envuelve al `QBO_scratch`
original.

## Qué no se pudo verificar

| Qué | Por qué | Cómo se cierra |
| --- | --- | --- |
| La UART real | No hay robot | Pasos 1 a 6 de `smoke.sh` |
| Audio: parlante y micrófono | Falta `my_loader` en la SSD nueva | Pasos 7 a 9 |
| Cámaras y `camera_index: 2` | No hay robot | Pasos 10 y 11 |
| `recognize_google` | Usa un servicio gratuito de Google con una clave embebida que puede dejar de andar | Paso 12 |
| Ollama real | `10.16.1.190` no es alcanzable desde donde se hizo la migración | Paso 13 |
| Tooly completo | Depende de todo lo anterior | Paso 14 |
| `apps/face_follow.py` (modo interactivo) | Usa hilos y Dialogflow. No tiene golden contra Python 2. Solo se comprobó que arranca, abre la cámara y busca caras | No hay servicio contra el cual probarlo |
| `tools/list_and_say.py`, `piface*.py`, `listen_background.py` | Dependen de `QBOtalk` | Idem |
| `websocket_server` en ejecución | Compila contra libwebsockets 4.3.5. No se probó con un cliente | Solo si se usa el modo Scratch |
| `RTQR.py` | Necesita el binding de `zbar` para Python 3. `writeWiFi.sh` escribe en `wpa_supplicant.conf`, y trixie usa NetworkManager | Solo si se usa el WiFi por QR |
| `deploy/install.sh` y las units en la Pi | Se probaron en contenedor | Correrlas en el robot |
| Raspbian frente a Debian | El contenedor es Debian armhf, no Raspbian | `apt-cache policy` en la Pi |
| Credenciales de Gmail del snapshot | No se probaron | Rotarlas |

Lo que el robot de mentira no puede ver: tiempos reales, niveles de audio, que
la cabeza se mueva hacia el lado correcto, que la voz se entienda.

## Riesgos abiertos

1. **Audio.** Sin `my_loader` no hay parlante ni micrófono, y Tooly no sirve.
   El módulo ya compila para el kernel nuevo, pero falta cargarlo y ver que
   aparezca la tarjeta. Es lo primero a probar con el robot delante.
2. **`camera_index: 2` y `llm_host`** en `config.yml` salen de la documentación,
   no de una prueba. Si la cámara no abre, `tooly.py` falla al arrancar.
3. **Reconocimiento de voz.** Depende de internet y de un servicio que Google no
   garantiza.
4. **`ReadResponse()`** ahora decodifica bien el escape. Si alguna parte del
   robot dependía del comportamiento viejo, cambia. No encontré ninguna: Tooly
   solo lee `GET_TOUCH`, que devuelve valores de 0 a 3.
5. **Timeout de 60 s al LLM.** El modelo tarda en cargar la primera vez. Si
   Ollama lo descargó de memoria, el primer turno puede agotar los reintentos.
   Se ajusta con `llm_timeout_s`.
6. **Secretos.** El historial de git está limpio. El snapshot de la SSD y
   `ITBA/PF/Tooly.zip` tienen la contraseña de la cuenta de Gmail del robot.

## En el robot, en orden

El plan de la primera sesión, escenario por escenario y con qué hacer ante cada
falla, está en `docs/Relevamiento_robot.md`.

```sh
cd /home/pi/Documents            # el repo desplegado acá
deploy/install.sh --dry-run      # ver qué va a hacer
deploy/install.sh
scripts/smoke/relevar.sh         # informe automático, no cambia nada
scripts/smoke/smoke.sh --list    # los 14 pasos
scripts/smoke/smoke.sh           # parar en el primero que falle
```
