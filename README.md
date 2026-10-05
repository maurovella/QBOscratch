# Qbo

Qbo is an open-source robot created by theCorpora, good for basic SAR research,
IoRT prototyping and STEM.

Este repo es el software que corre en la Raspberry Pi del robot: el driver de la
placa de la cabeza (Q-board), los daemons originales y **Tooly**, un asistente
conversacional que escucha, le pregunta a un LLM y habla la respuesta.

Corre con Python 3.13 en Raspbian 13 (trixie). La versión original, para Python
2.7 y Raspbian 9, está en la rama `legacy-python2`. Qué cambió, qué se verificó y
qué falta probar en el robot está en [MIGRATION.md](MIGRATION.md).

## Qué hay

| Carpeta | Qué es |
| --- | --- |
| `qbo/` | Código compartido: protocolo de la Q-board (`protocol.py`), TTS (`tts.py`), cliente del LLM (`llm/`), rutas, sensor táctil, alertas por mail |
| `apps/` | Lo que se ejecuta: `tooly.py`, `picmd.py`, `say.py`, `listen.py`, `feel.py`, `find_face.py`, `face_follow.py` |
| `tools/` | Scripts de prueba manual: cámaras, servos, cabeza |
| `Python projects/` | Puentes hacia `apps/`. Los daemons y los comandos de siempre siguen usando estas rutas |
| `deamonsScripts/` | Scripts `QBO_*` de arranque y parada del modo Scratch |
| `deploy/` | Instalación en la Pi y units de systemd |
| `scripts/` | `check.sh`, el gate para desarrollo, y `smoke/`, las pruebas en el robot |
| `tests/` | Tests que corren sin el robot |
| `docs/` | Ingeniería inversa del firmware, guía de setup de la Pi, notas de audio |
| `20200325.001_H1_HeadCtrl_Qboard/` | Firmware de la Q-board (Atmel SAMD21) |
| `audio/`, `system/` | Módulo de kernel del audio I2S y configuración de ALSA |

## Instalar en el robot

El repo se despliega en `/home/pi/Documents`.

```sh
cd /home/pi/Documents
deploy/install.sh --dry-run   # muestra lo que va a hacer
deploy/install.sh
```

Instala los paquetes de `deploy/apt-packages.txt`, crea el entorno
`~/qbo-venv`, agrega al usuario a los grupos `dialout`, `audio` y `video` y crea
los FIFOs. En Raspbian 13 no se puede usar `pip install` global: todo lo
compilado viene por apt y el venv solo suma `SpeechRecognition`.

La UART, el audio I2S y ALSA se configuran a mano. Está en
[docs/Guia_setup_Pi3_QBO.md](docs/Guia_setup_Pi3_QBO.md).

## Probar el robot

```sh
scripts/smoke/relevar.sh        # 1 minuto, no cambia nada: qué está OK y qué falta
scripts/smoke/smoke.sh --list   # los 14 pasos
scripts/smoke/smoke.sh          # corre todos, en orden
scripts/smoke/smoke.sh --only 3
```

`relevar.sh` junta el estado de cada módulo en un informe. Los escenarios de
prueba, con qué hacer ante cada falla, están en
[docs/Relevamiento_robot.md](docs/Relevamiento_robot.md).

`smoke.sh` va de lo más barato a lo más caro: UART, nariz, boca, táctil, cabeza, parlante,
micrófono, voz, cámaras, cara, reconocimiento de voz, LLM y Tooly completo. Cada
paso prueba una sola cosa y dice qué significa si falla. Si uno falla, los de
abajo no sirven hasta arreglarlo.

## Comandos

Con el entorno activado (`source ~/qbo-venv/bin/activate`) y desde
`/home/pi/Documents/Python projects`:

```sh
python3 PiCmd.py -c nose -co blue           # nariz: none, red, green, blue
python3 PiCmd.py -c mouth -e smile          # boca: smile, sad, serious, love
python3 PiCmd.py -c servo -a 30 -x 1 -s 200 # servo: ángulo, eje 1 o 2, velocidad
python3 PiCmd.py -c say -t "Hola"           # necesita say.py corriendo
python3 PiCmd.py ?                          # ayuda
```

Hablar sin pasar por `PiCmd`:

```sh
pico2wave -l "es-ES" -w /home/pi/Documents/pico2wave.wav "La vida es muy compleja querido amigo" \
  && aplay -D convertQBO /home/pi/Documents/pico2wave.wav
```

Hablar directo con la placa, sin `config.yml` ni FIFOs:

```sh
python3 scripts/smoke/qboard.py version
python3 scripts/smoke/qboard.py nose blue
python3 scripts/smoke/qboard.py touch 10
```

## Tooly

```sh
python3 apps/tooly.py         # sigue la cara, escucha, pregunta al LLM y habla
python3 apps/tooly_audio.py   # lo mismo sin cámara ni cabeza
```

Tooly busca una cara. Cuando la tiene centrada pone la nariz en verde, escucha,
manda lo que oyó al LLM y dice la respuesta. Si lo acarician muestra un gesto
con la boca. Si nadie contesta durante cuatro horas pregunta si está todo bien y
avisa por mail.

Se configura en `config.yml`:

| Clave | Para qué |
| --- | --- |
| `language` | `english` o `spanish`: voz del TTS e idioma del reconocimiento |
| `volume` | Volumen de `pico2wave`, de 0 a 500 |
| `llm_backend` | `ollama`, o `tooly_legacy` para el servidor FastAPI original |
| `llm_host`, `llm_model` | Servidor y modelo de Ollama |
| `llm_timeout_s`, `llm_retries` | Espera y reintentos por pedido |
| `camera_index` | Cámara que sigue la cara. 1 en Raspbian 9, 2 en Raspbian 13 |

Si el LLM no responde, Tooly lo dice en voz alta y repite lo que oye.

Las alertas por mail leen la cuenta y los destinatarios de variables de entorno:
`QBO_SMTP_USER`, `QBO_SMTP_PASSWORD` y `QBO_ALERT_TO`. Hay un ejemplo en
`deploy/tooly.env.example`. No van en el repo.

Para que arranque solo, `deploy/systemd/qbo-tooly.service` tiene las
instrucciones en el encabezado.

## Modo Scratch

El control desde Scratch usaba ScratchX (scratchx.org), que el equipo de Scratch
archivó cuando terminó Flash. La extensión de `scratch_extension/` ya no tiene
dónde cargarse. Los daemons se conservan y siguen funcionando como interfaz por
FIFOs:

```sh
cd /home/pi/Documents/deamonsScripts
./QBO_scratch start   # websocket_server, PiCmd, say, listen, feel y findFace
./QBO_scratch stop
./lsqbo               # qué procesos están corriendo
```

`websocket_server` hay que recompilarlo en la Pi: `make -C websocketServer`
(necesita `libwebsockets-dev`).

## Desarrollo sin el robot

```sh
scripts/check.sh          # gate sintáctico + tests, unos 2 minutos
scripts/check.sh --fast   # solo el gate sintáctico
```

Los tests corren cada script contra un robot de mentira y comparan lo que hace
con lo que hacía el código original en Python 2.7. Cómo funciona y cómo se
regenera la referencia está en [MIGRATION.md](MIGRATION.md).

`QBO_HOME` cambia la raíz `/home/pi/Documents` para correr los scripts en otra
máquina.

## Notas del robot

- Los dos modos de conversación originales, Dialogflow V1 y Google Assistant
  Library, fueron apagados por Google. `apps/face_follow.py` (ex `PiFaceFast.py`)
  y `qbo/legacy/` se conservan pero no hay servicio contra el cual usarlos.
- Las cámaras hay que abrirlas a 320x240. Con resoluciones mayores no se pueden
  leer las dos a la vez. `tools/left_eye.py`, `right_eye.py` y `stereo.py` las
  muestran.
- El dump del modo interactivo quedaba en `interactiveMode.log`.

## Firmware y programador

- Paso a paso para actualizar el firmware:
  <http://thecorpora.com/community/q-board-arduino/firmware-source-code-available-guide/>
- <http://thecorpora.com/howto-hacking-updating-q-board-using-segger-mini-j-link-jtag-only-for-developers/>
- Programador: J-Link EDU Mini,
  <https://www.segger.com/products/debug-probes/j-link/models/j-link-edu-mini/>
- Guía de usuario: <https://www.generationrobots.com/media/UserGuide-qbo.pdf>
- El protocolo de la placa está documentado en
  [docs/Ingenieria_inversa_firmware_QBO.md](docs/Ingenieria_inversa_firmware_QBO.md).

## Servos

Los servos son [Dynamixel XL-320](https://www.robotis.us/dynamixel-xl-320/).

- Cómo conectarlos: <http://walker.gosrich.com/posts/xl320.html>
- <https://github.com/hackerspace-adelaide/XL320> permite conectar el pin de
  datos, GND y VCC a un Arduino y cambiarle al servo el ID y el baud rate. Sirve
  para reincorporar un servo que quedó con otra configuración.
- `tools/servo_config.py` hace lo mismo a través de la Q-board.
