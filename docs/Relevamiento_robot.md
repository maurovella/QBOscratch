# Relevamiento del robot: qué probar y qué hacer con cada falla

Para la primera sesión con el robot después de la migración a Python 3.13. El
objetivo no es que todo ande, es salir sabiendo qué anda, qué no y por qué.

Nada de este repo corrió todavía en el robot. Lo que dice "debería funcionar"
está respaldado por tests sin hardware (ver `MIGRATION.md`); lo que dice "no" o
"incierto" depende de cosas que solo existen en el robot.

## Antes de ir

- [ ] Llevar el código. Sin internet en la Pi alcanza con un archivo:
      `git bundle create qbo.bundle migracion-py3 legacy-python2` en la Mac,
      copiarlo por USB o `scp`, y en la Pi
      `git clone -b migracion-py3 qbo.bundle Documents`.
- [ ] Llevar la SSD vieja y un adaptador USB. De ahí salen `/etc/asound.conf`
      y `/etc/modules` originales, que no están en ningún repo.
- [ ] Teclado y monitor, o confirmar que se entra por SSH.
- [ ] Levantar Ollama en el servidor (`ollama serve`, `ollama list`) y probar
      desde una máquina de la misma red que el robot:
      `curl http://10.16.1.190:11434/api/tags`.
- [ ] Plan B para el LLM: Ollama en la notebook, en la misma red que el robot.
      En la Pi se usa con `export QBO_LLM_HOST=http://<ip de la notebook>:11434`.
- [ ] Si se van a probar las alertas por mail: cuenta con app password nueva.

## En el robot, en este orden

| Minutos | Qué | Comando |
| --- | --- | --- |
| 5 | Guardar lo que haya y poner el repo | `mv ~/Documents ~/Documents.antes` y clonar en `~/Documents` |
| 5 | Instalar | `deploy/install.sh --dry-run`, después `deploy/install.sh`, cerrar sesión y volver a entrar |
| 1 | Relevamiento automático | `scripts/smoke/relevar.sh` |
| 10 | Rama UART (U1 a U6) | `scripts/smoke/smoke.sh --from 1` hasta el paso 6 |
| 5 | Rama visión (C1, C2) | `scripts/smoke/smoke.sh --only 10` y `--only 11` |
| 5 | Rama red (R1, R2) | `scripts/smoke/smoke.sh --only 13` |
| el resto | Rama audio (A1 a A5) | Es la que más tiempo lleva. Ver abajo |
| al final | Integración (T1, T2) | Solo si audio y red pasaron |

`relevar.sh` no cambia nada en el robot y deja `~/qbo-relevamiento-<fecha>.txt`.
**Traer ese archivo de vuelta**, pase lo que pase: con eso se puede diagnosticar
sin el robot.

Las ramas son independientes. Si el audio no anda, igual se puede relevar la
UART, las cámaras y la red. Dentro de una rama sí hay orden: si un escenario
falla, los siguientes de esa rama no sirven hasta arreglarlo.

```text
E0 entorno
 ├─ UART:    U1 → U2 → U3, U4, U5, U6
 ├─ audio:   A1 → A2 → A3 → A5
 │                  └→ A4
 ├─ visión:  C1 → C2
 ├─ red:     R1, R2, R3
 └─ integración: T1 (necesita A3, A4, R1, R2) → T2 (además U2, C2)
```

## Qué espero de cada módulo

| Módulo | Rol real en el robot | Importancia para Tooly | ¿Debería funcionar mañana? |
| --- | --- | --- | --- |
| Entorno Python | Intérprete, venv y librerías | Crítica | Sí. Probado en un contenedor Debian trixie ARM de 32 bits |
| UART y Q-board | Único canal con la placa de la cabeza: LEDs, servos, táctil y habilitación del parlante | Crítica | Sí, si la UART está bien configurada. Los bytes son idénticos a los de Python 2 en 448 de 461 casos; los otros 13 son arreglos |
| Nariz y boca | Lo que el robot muestra: nariz verde al verte, gesto al acariciarlo | Media | Sí, si la UART anda |
| Sensor táctil | Detecta la caricia. Es además la única lectura que Tooly le hace a la placa | Media | Sí. Es el único camino de lectura que cambió de lógica, por eso hay que mirarlo |
| Servos de la cabeza | Siguen la cara | Media | Incierto. El historial del robot muestra muchas pruebas de servos y cambios de ID |
| Tarjeta de sonido I2S | Parlante y micrófono de la cabeza. Sin ella el robot no habla ni escucha | Crítica | **Probablemente no al primer intento.** El módulo `my_loader` ya compila para el kernel nuevo pero nunca se cargó |
| Parlante | Voz del robot | Crítica | Depende de la tarjeta |
| Micrófono | Lo que oye el robot | Crítica | Depende de la tarjeta |
| `pico2wave` | Convierte texto en audio | Crítica | Sí. La documentación del repo dice que ya está instalado en la SSD nueva |
| Cámaras | Ven a la persona | Alta | Sí. El índice puede no ser el de `config.yml` |
| Detección de cara | Decide cuándo empezar a hablar y hacia dónde girar | Alta | Sí, si la cámara entrega imagen |
| Reconocimiento de voz | Audio a texto, con un servicio gratuito de Google | Crítica | Incierto. Necesita micrófono, internet y que el servicio siga abierto |
| LLM (Ollama) | Genera la respuesta | Crítica | Incierto. Depende de que el servidor esté levantado y la Pi llegue a él |
| Alertas por mail | Avisa a un familiar tras 4 horas sin respuesta | Baja para una demo | No, hasta cargar credenciales nuevas |
| Tooly completo | El asistente | Es el objetivo | No, hasta que anden audio, voz y LLM |
| Modo Scratch | Control por FIFOs desde ScratchX | Ninguna | Parcial. ScratchX ya no existe |
| Modo interactivo original | Conversación por Dialogflow o Google Assistant | Ninguna | No. Google apagó los dos servicios |
| WiFi por QR | Configura la red mostrando un QR a la cámara | Ninguna | No |

## Escenarios

Cada escenario tiene: qué se corre, qué tiene que pasar, y qué hacer según cómo
falle. Los números de paso son los de `scripts/smoke/smoke.sh`.

### E0. El entorno está instalado

- **Módulo:** entorno Python. **Importancia:** crítica.
- **Rol:** todo lo demás corre sobre esto.
- **Expectativa:** debería funcionar.
- **Correr:** `deploy/install.sh` y después `scripts/smoke/relevar.sh`.
- **Esperado:** en el resumen, las tres líneas `entorno` dicen `OK`.

| Si pasa esto | Causa probable | Qué hacer |
| --- | --- | --- |
| `apt-get install` no encuentra un paquete | Raspbian no tiene exactamente los paquetes de Debian | Anotar cuál. `apt-cache policy <paquete>`. Sacarlo de `deploy/apt-packages.txt` y seguir: el resumen dirá qué import falta |
| `pip` falla dentro del venv | La Pi no tiene internet | Seguir. Solo falta `SpeechRecognition`: afecta a R1 y T1, no a UART ni cámaras |
| `paquetes Python` dice `FALTA` | Algún import falla | En el informe, sección "Python", está cuál y con qué error |
| Los grupos no cambian | Falta cerrar sesión | Salir y volver a entrar, o `newgrp dialout` |

### U1. La UART existe y hay permiso

- **Módulo:** UART. **Importancia:** crítica. **Paso 1.**
- **Rol:** `/dev/serial0` es el cable lógico hacia la Q-board.
- **Expectativa:** debería funcionar tras `install.sh` y un reinicio.
- **Esperado:** `/dev/serial0 -> ttyS0` o `-> ttyAMA0`, y el usuario en `dialout`.

| Si pasa esto | Causa probable | Qué hacer |
| --- | --- | --- |
| No existe `/dev/serial0` | Falta `enable_uart=1` | `sudo raspi-config nonint do_serial_hw 0` y reiniciar |
| Existe pero "Permission denied" | Usuario fuera de `dialout` | `sudo usermod -aG dialout $USER` y volver a entrar |
| El resumen marca `FALTA` en "sin consola serie" | El sistema usa el puerto como terminal | `sudo raspi-config nonint do_serial_cons 1` y reiniciar. Si no, la placa recibe basura |

### U2. La Q-board contesta

- **Módulo:** Q-board. **Importancia:** crítica. **Paso 2.**
- **Rol:** prueba de ida y vuelta. Si esto anda, el protocolo migrado habla con el firmware real.
- **Expectativa:** debería funcionar. Es la primera vez que el código Python 3 toca la placa.
- **Correr:** `python3 scripts/smoke/qboard.py version`
- **Esperado:** `GET_VERSION -> [N]`.

| Si pasa esto | Causa probable | Qué hacer |
| --- | --- | --- |
| `NACK  [255, 254]` tres veces | La placa recibe pero rechaza la trama | Es un problema de checksum o de escape en `qbo/protocol.py`. **Anotar la salida completa y avisar**: sería un bug de la migración. Probar `nose blue`: si eso anda, el problema es solo de ese comando |
| `NACK  []` tres veces, sin respuesta | No llega nada | Consola serie activa (ver U1). Placa sin alimentación. Conector de la cabeza suelto |
| Sin respuesta y `/dev/serial0 -> ttyS0` | El mini-UART no engancha el baudrate | Agregar `dtoverlay=disable-bt` a `/boot/firmware/config.txt`, `sudo systemctl disable hciuart`, reiniciar |
| Sin respuesta y `/dev/serial0 -> ttyAMA0` | Al revés | Quitar `disable-bt`. La SSD vieja usaba el mini-UART |
| Responde a veces | Baudrate inestable | Igual que la fila de `ttyS0` |

### U3 y U4. Nariz y boca

- **Módulo:** LEDs. **Importancia:** media. **Pasos 3 y 4.**
- **Rol:** la nariz verde es la señal de "te vi, hablame". La boca muestra el gesto de la caricia.
- **Expectativa:** debería funcionar si U2 pasó.
- **Correr:** `qboard.py nose blue`, `qboard.py mouth smile`. Probar también `nose red`, `nose green`, `nose none`.
- **Esperado:** se ve el color y el dibujo, y la respuesta repite el comando.

| Si pasa esto | Causa probable | Qué hacer |
| --- | --- | --- |
| Dice `respuesta: FF 45 00 ... FE` pero no se ve nada | La placa aceptó; el LED no | Hardware. Probar otro color |
| `NACK` | Trama rechazada | Igual que en U2: anotar y avisar |
| La nariz anda y la boca no | Comando de 4 bytes o matriz de LEDs | Probar `mouth love` y `mouth off`. Si ninguno, hardware |
| El color no es el pedido | Mapa de colores | Anotar qué color sale con cada nombre |

### U5. Sensor táctil

- **Módulo:** táctil. **Importancia:** media. **Paso 5.**
- **Rol:** dispara la reacción a la caricia. Es la única lectura de datos que hace Tooly.
- **Expectativa:** debería funcionar. Es el camino de lectura cuya lógica cambió respecto de Python 2, así que conviene probarlo con cuidado.
- **Correr:** `qboard.py touch 10` y tocar derecha, arriba e izquierda.
- **Esperado:** `tactil = 1 (derecha)`, `2 (arriba)`, `3 (izquierda)`.

| Si pasa esto | Causa probable | Qué hacer |
| --- | --- | --- |
| `0 respuestas validas` | La lectura falla aunque la escritura ande | Cable RX, o un bug en `ReadResponse()`. Anotar y avisar |
| Respuestas válidas pero siempre 0 | Sensores capacitivos | Tocar con la mano entera. Si sigue en 0, hardware |
| Valores distintos de 0 a 3 | El firmware devuelve otra cosa | Anotar los valores. No bloquea |

### U6. Cabeza

- **Módulo:** servos. **Importancia:** media. **Paso 6.**
- **Rol:** siguen la cara. Tooly conversa igual sin ellos.
- **Expectativa:** incierto.
- **Correr:** `qboard.py head`.
- **Esperado:** gira a un lado y vuelve, sube y vuelve.

| Si pasa esto | Causa probable | Qué hacer |
| --- | --- | --- |
| No se mueve nada | Servos sin alimentación o deshabilitados | `python3 tools/servo_config.py -d 1 -c SET_SERVO_ENABLE 1` |
| Se mueve un eje solo | Un servo con otro ID | La rama `legacy-python2`, carpeta `work-QBOscratch`, tiene `TestServ.py` y pruebas con los IDs 175 y 191 |
| Se mueve al revés o choca | Límites | Anotar. No insistir: los límites de Tooly son X 290 a 725, Y 420 a 550 |

### A1. La tarjeta de sonido aparece

- **Módulo:** tarjeta I2S. **Importancia:** crítica.
- **Rol:** crea `sndrpisimplecar`. De ella cuelgan parlante y micrófono.
- **Expectativa:** probablemente no al primer intento. Es el escenario más importante del día y el menos verificado.
- **Correr:** los pasos de `audio/rpi-i2s-audio/README.md`.
- **Esperado:** `aplay -l | grep sndrpisimplecar` muestra la tarjeta.

| Si pasa esto | Causa probable | Qué hacer |
| --- | --- | --- |
| `apt` no encuentra `linux-headers-rpi-v7` | Otro kernel o falta el repo de Raspberry Pi | `uname -r`. Si termina en `rpi-v8`, es `linux-headers-rpi-v8`. `apt list 'linux-headers*'` |
| `make` falla | Kernel distinto de 6.12 y 6.18 | Copiar el error completo. Hay que ajustar `my_loader.c` |
| `modprobe: ERROR ... Exec format error` | El `.ko` es de otro kernel | Recompilar contra `uname -r` |
| Carga, pero no aparece la tarjeta | El bus I2S no está o tiene otro nombre | `dmesg \| tail -20` y `ls /sys/bus/platform/devices \| grep i2s`. Falta `dtparam=i2s=on`, o el nombre no es `3f203000.i2s` |
| `dmesg` dice "insufficient simple_util_info" o "no info" | El driver rechaza los datos | Copiar `dmesg`. Camino alternativo: overlay de `docs/Guia_setup_Pi3_QBO.md`, sección 2.4 |
| `dmesg` muestra un error de `snd-soc-dummy` | El codec ficticio no está | `sudo modprobe snd-soc-core` y reintentar. Copiar `dmesg` |

Si A1 no sale en el tiempo disponible, cortar acá esta rama. Traer `dmesg` y el
informe de `relevar.sh`. Todo lo demás del audio depende de esto.

### A2. ALSA conoce `convertQBO` y `dmicQBO_sv`

- **Módulo:** ALSA. **Importancia:** crítica.
- **Rol:** son los nombres que usa el código. `convertQBO` para hablar, `dmicQBO_sv` para escuchar.
- **Expectativa:** incierto. La definición de `convertQBO` del repo es una reconstrucción.
- **Correr:** `aplay -L | grep -E 'convertQBO|dmicQBO'`
- **Esperado:** aparecen los dos nombres.

| Si pasa esto | Causa probable | Qué hacer |
| --- | --- | --- |
| No aparece ninguno | Falta `/etc/asound.conf` | `sudo cp system/asound.conf /etc/asound.conf` y agregarle el contenido de `system/asound-convertQBO.conf` |
| Aparece `dmicQBO_sv` y no `convertQBO` | Falta solo la parte reconstruida | Agregar `system/asound-convertQBO.conf` al final de `/etc/asound.conf` |
| Hay un `/etc/asound.conf` de la SSD vieja a mano | Es la definición original | Usar esa y **copiarla al repo** como `system/asound.conf.original`. Si dice `hw:1,0`, cambiarlo por `hw:sndrpisimplecar,0` |

### A3. El parlante suena

- **Módulo:** parlante. **Importancia:** crítica. **Paso 7.**
- **Rol:** la voz del robot. El amplificador se enciende por la UART.
- **Expectativa:** debería funcionar si A1 y A2 pasaron.
- **Esperado:** un tono de 440 Hz por el parlante de la cabeza.

| Si pasa esto | Causa probable | Qué hacer |
| --- | --- | --- |
| `Slave PCM not usable` | `convertQBO` apunta a otra tarjeta | Revisar que diga `hw:sndrpisimplecar,0` |
| No da error y no suena | Amplificador apagado | `qboard.py speaker on` tiene que mostrar respuesta. Si U2 falla, esto también |
| Suena por HDMI o por el jack | ALSA usa otra tarjeta | `aplay -D convertQBO` explícito. Revisar `~/.asoundrc` |
| Suena agudo, grave o entrecortado | Frecuencia de muestreo | Anotar. El firmware trabaja a 16 kHz |

### A4. El micrófono graba

- **Módulo:** micrófono. **Importancia:** crítica. **Paso 8.**
- **Rol:** lo que oye el robot.
- **Expectativa:** debería funcionar si A1 pasó.
- **Esperado:** se graba 4 segundos y se escucha la voz al reproducir.

| Si pasa esto | Causa probable | Qué hacer |
| --- | --- | --- |
| `Unknown PCM dmicQBO_sv` | ALSA | Volver a A2 |
| Graba silencio | Captura I2S | `arecord -D hw:sndrpisimplecar,0 -f S16_LE -r 16000 -c 2 -d 3 /tmp/x.wav`. Si también es silencio, es el bus |
| Se oye muy bajo | Ganancia | `alsamixer`, control "Boost Capture Volume" |

### A5. `pico2wave` habla

- **Módulo:** TTS. **Importancia:** crítica. **Paso 9.**
- **Rol:** texto a audio.
- **Expectativa:** debería funcionar si A3 pasó.
- **Esperado:** el robot dice "Hola, soy Tooly".

| Si pasa esto | Causa probable | Qué hacer |
| --- | --- | --- |
| `pico2wave: command not found` | No está instalado | `deploy/install.sh` dice cómo: tres `.deb` de Debian |
| Genera el wav y no suena | Parlante | Volver a A3 |
| Dice otra cosa o corta | Texto | Anotar la frase exacta. Sería un bug de `qbo/tts.py` |

Se puede probar aunque A3 falle: `pico2wave -l es-ES -w /tmp/t.wav "hola" && ls -l /tmp/t.wav`
confirma que el TTS genera audio, aunque no se oiga.

### C1. Las cámaras entregan imagen

- **Módulo:** cámaras. **Importancia:** alta. **Paso 10.**
- **Rol:** ver a la persona.
- **Expectativa:** debería funcionar.
- **Correr:** `python3 tools/camera_probe.py`
- **Esperado:** dos líneas `OK 320x240`. Anotar los índices.

| Si pasa esto | Causa probable | Qué hacer |
| --- | --- | --- |
| Ninguna `OK` | Cámaras sin detectar | `lsusb` y `v4l2-ctl --list-devices`. Si no aparecen, cable USB |
| `OK` en 0 y 2 | Lo esperado en el kernel nuevo | `camera_index: 2` en `config.yml` ya está bien |
| `OK` en 0 y 1 | Como en el kernel viejo | Cambiar `camera_index` a 1 en `/home/pi/Documents/config.yml` |
| Una sola `OK` | Una cámara no anda | Usar esa en `camera_index`. Tooly necesita una sola |

### C2. Detecta una cara

- **Módulo:** visión. **Importancia:** alta. **Paso 11.**
- **Rol:** dispara la conversación y guía la cabeza.
- **Expectativa:** debería funcionar si C1 pasó.
- **Esperado:** `cara detectada: centro en (x, y)`.

| Si pasa esto | Causa probable | Qué hacer |
| --- | --- | --- |
| `no se detecto ninguna cara` | Luz, distancia o ángulo | Ponerse a 50 cm, de frente, con luz. Probar la otra cámara: `face_once.py 0 15` |
| `OpenCV no pudo cargar` | Cascadas | No debería pasar. Anotar `python3 -c "import cv2; print(cv2.__version__)"` |

### R1. Reconoce lo que se dice

- **Módulo:** reconocimiento de voz. **Importancia:** crítica. **Paso 12.**
- **Rol:** audio a texto. Usa un servicio gratuito de Google con una clave pública.
- **Expectativa:** incierto.
- **Esperado:** `transcripcion (en-US): ...` con lo dicho.

| Si pasa esto | Causa probable | Qué hacer |
| --- | --- | --- |
| `no existe el microfono 'dmicQBO_sv'` | Audio | Volver a A2 |
| `no se oyo nada` | Micrófono | Volver a A4 |
| `Google no entendio nada` | Idioma o ruido | `language` en `config.yml`. Hablar claro y cerca |
| `no se pudo consultar a Google` | Sin internet, o el servicio dejó de aceptar la clave pública | `curl -I https://www.google.com`. Si hay internet y falla siempre, el servicio cambió: hay que elegir otro motor. Anotar el error exacto |

### R2. El LLM responde

- **Módulo:** LLM. **Importancia:** crítica. **Paso 13.**
- **Rol:** genera lo que dice el robot. No necesita audio ni cámara para probarse.
- **Expectativa:** incierto.
- **Correr:** `python3 scripts/smoke/llm_once.py Hello`
- **Esperado:** `respuesta en N s: ...`. Anotar los segundos.

| Si pasa esto | Causa probable | Qué hacer |
| --- | --- | --- |
| `ConnectionError` | La Pi no llega al servidor | `curl http://10.16.1.190:11434/api/tags`. Si no responde: red, VPN, o Ollama apagado. Plan B: `export QBO_LLM_HOST=http://<notebook>:11434` |
| `HTTP 404` | El modelo no está descargado | En el servidor, `ollama list`. Cambiar `llm_model` en `config.yml` |
| `Timeout` | El modelo tarda en cargar | Reintentar: la segunda vez ya está en memoria. Subir `llm_timeout_s` |
| Responde en más de 10 segundos | Modelo grande o GPU ocupada | Anotar. Afecta la conversación, no la bloquea |
| Responde en otro idioma o muy largo | Modelo y prompt | Anotar la respuesta. No es un bug de la migración |

### R3. Alertas por mail

- **Módulo:** mail. **Importancia:** baja para una primera sesión.
- **Rol:** avisa a un familiar si nadie contesta en 4 horas.
- **Expectativa:** no funciona hasta crear `~/.config/qbo/tooly.env`.
- **Qué hacer:** dejarlo para otro día, salvo que sobre tiempo. Sin credenciales Tooly avisa por pantalla y sigue.

### T1. Tooly sin cámara

- **Módulo:** integración. **Importancia:** es el objetivo.
- **Rol:** el ciclo escuchar, preguntar, hablar, sin cabeza ni cámara.
- **Expectativa:** solo si A3, A4, A5, R1 y R2 pasaron.
- **Correr:** `python3 apps/tooly_audio.py`
- **Esperado:** saluda con la respuesta del LLM, escucha y contesta.

| Si pasa esto | Causa probable | Qué hacer |
| --- | --- | --- |
| `Microfono 'dmicQBO_sv' no encontrado` | Audio | A2 |
| Termina al arrancar con `LLMError` | El LLM no respondió al saludo. Esta variante no tiene modo repetir | R2 |
| Saluda, y más tarde dice "My mind is not ready" | El LLM dejó de responder en medio de la charla | R2. Sigue andando y repite lo que oye |
| Saluda y después no contesta nunca | No oye | R1. Mirar si imprime `LISTEN:` |
| Traceback | Bug de integración | Copiar el traceback completo |

### T2. Tooly completo

- **Módulo:** integración. **Importancia:** es el objetivo. **Paso 14.**
- **Rol:** sigue la cara, escucha, pregunta al LLM y habla.
- **Expectativa:** solo si T1, U2 y C2 pasaron.
- **Correr:** `python3 apps/tooly.py` desde el escritorio gráfico.
- **Esperado:** nariz roja, ventana con la cámara, nariz verde al verte, conversación.

| Si pasa esto | Causa probable | Qué hacer |
| --- | --- | --- |
| `cannot connect to X server` o error de `imshow` | No hay escritorio | Correrlo desde el escritorio, o `export DISPLAY=:0` |
| Error en `detectMultiScale` al arrancar | La cámara de `camera_index` no entrega imagen | C1 |
| Nunca pone la nariz verde | No detecta la cara centrada | C2. La cabeza tiene que poder moverse (U6) |
| La cabeza se va para un costado | Signo del seguimiento | Anotar hacia dónde. No bloquea la conversación |
| Conversa una vez y queda mudo | Espera de 50 cuadros, o el LLM tardó | Esperar 10 segundos. Mirar la terminal |

### S1. Modo Scratch

- **Módulo:** daemons originales. **Importancia:** ninguna para Tooly.
- **Rol:** interfaz por FIFOs para ScratchX, que ya no existe.
- **Expectativa:** `PiCmd`, `feel` y `findFace` deberían andar. `say` y `listen` dependen del audio. `websocket_server` hay que recompilarlo.
- **Correr solo si sobra tiempo:** `cd deamonsScripts && ./QBO_PiCmd start`, y desde otra terminal `python3 "Python projects/PiCmd.py" -c nose -co red`.

### X1. Lo que no vale la pena probar

- Modo interactivo original (`PiFaceFast` con Dialogflow o Google Assistant): los servicios no existen.
- WiFi por QR (`RTQR.py`): falta el lector de QR para Python 3 y el script escribe una configuración que Raspbian 13 no usa.

## Planilla

Completar en el momento. `OK`, `FALLA` o `no probado`, y una línea de qué se vio.

| Escenario | Resultado | Qué se vio |
| --- | --- | --- |
| E0 entorno | | |
| U1 UART | | |
| U2 Q-board contesta | | |
| U3 nariz | | |
| U4 boca | | |
| U5 táctil | | |
| U6 cabeza | | |
| A1 tarjeta de sonido | | |
| A2 ALSA | | |
| A3 parlante | | |
| A4 micrófono | | |
| A5 pico2wave | | |
| C1 cámaras (índices: ) | | |
| C2 cara | | |
| R1 reconocimiento de voz | | |
| R2 LLM (segundos: ) | | |
| T1 Tooly sin cámara | | |
| T2 Tooly completo | | |

## Qué traer de vuelta

1. `~/qbo-relevamiento-*.txt` y `~/qbo-smoke-*.log`.
2. `dmesg > ~/dmesg.txt` después de intentar cargar `my_loader`.
3. De la SSD vieja: `/etc/asound.conf`, `/etc/modules`, `/etc/rc.local`.
4. Esta planilla.
5. Cualquier traceback, entero.
