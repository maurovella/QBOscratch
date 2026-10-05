#!/bin/bash
# Escalera de pruebas en el robot: de lo mas barato a lo mas caro.
# Cada paso prueba UN subsistema. Si un paso falla, los de abajo no sirven:
# arreglar ese antes de seguir.
#
#   scripts/smoke/smoke.sh               corre todos los pasos, en orden
#   scripts/smoke/smoke.sh --from 7      empieza en el paso 7
#   scripts/smoke/smoke.sh --only 3      corre solo el paso 3
#   scripts/smoke/smoke.sh --list        muestra los pasos sin ejecutar nada
#   scripts/smoke/smoke.sh --dry-run     idem, con comando, esperado y diagnostico
#
# Los pasos marcados [vos] necesitan que alguien mire o escuche al robot y
# conteste s/n. El resultado queda en ~/qbo-smoke-<fecha>.log.

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [ -z "$QBO_PYTHON" ]; then
    if [ -x "$HOME/qbo-venv/bin/python" ]; then QBO_PYTHON="$HOME/qbo-venv/bin/python"; else QBO_PYTHON=python3; fi
fi
QBO_HOME="${QBO_HOME:-/home/pi/Documents}"
CAMERA="$("$QBO_PYTHON" -c "import sys, yaml; print(yaml.safe_load(open(sys.argv[1])).get('camera_index', 1))" "$QBO_HOME/config.yml" 2>/dev/null || echo 1)"

# Los comandos de cada paso se muestran y se ejecutan con eval: las rutas van
# escapadas para que funcionen aunque tengan espacios.
PY="$(printf '%q' "$QBO_PYTHON")"
ROOT_Q="$(printf '%q' "$ROOT")"
SMOKE="$ROOT_Q/scripts/smoke"
HOME_Q="$(printf '%q' "$QBO_HOME")"

MODE=run; FROM=1; ONLY=""
while [ $# -gt 0 ]; do
    case "$1" in
        --from) FROM="$2"; shift ;;
        --only) ONLY="$2"; shift ;;
        --list) MODE=list ;;
        --dry-run) MODE=dry ;;
        -h|--help) sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "opcion desconocida: $1"; exit 2 ;;
    esac
    shift
done

LOG="$HOME/qbo-smoke-$(date +%Y%m%d-%H%M).log"
[ "$MODE" = run ] || LOG=/dev/null
N=0; PASSED=0; FAILED=0; RESULTS=""

# step TIPO "titulo" "comando" "resultado esperado" "que significa si falla"
#   TIPO auto: pasa si el comando sale con 0.
#   TIPO vos:  ademas pregunta si se vio u oyo lo esperado.
step() {
    local kind="$1" title="$2" cmd="$3" expected="$4" onfail="$5"
    N=$((N + 1))
    [ -n "$ONLY" ] && [ "$N" != "$ONLY" ] && return
    [ -z "$ONLY" ] && [ "$N" -lt "$FROM" ] && return
    if [ "$MODE" = list ]; then
        printf '%2d. [%s] %s\n' "$N" "$kind" "$title"; return
    fi
    echo
    echo "=== Paso $N: $title [$kind]"
    echo "    comando:  $cmd"
    echo "    esperado: $expected"
    if [ "$MODE" = dry ]; then
        echo "    si falla: $onfail"; return
    fi
    echo "--- salida" | tee -a "$LOG" >/dev/null
    ( cd "$ROOT" && eval "$cmd" ) 2>&1 | tee -a "$LOG"
    local rc=${PIPESTATUS[0]} ok=1
    [ "$rc" -eq 0 ] || ok=0
    if [ "$ok" = 1 ] && [ "$kind" = vos ]; then
        printf '    Se cumplio lo esperado? [s/n] '
        read -r answer
        case "$answer" in s|S|si|SI|y|Y) ;; *) ok=0 ;; esac
    fi
    if [ "$ok" = 1 ]; then
        echo "    PASA"; PASSED=$((PASSED + 1)); RESULTS="$RESULTS\n  PASA   $N. $title"
    else
        echo "    FALLA (codigo $rc)"
        echo "    que significa: $onfail"
        FAILED=$((FAILED + 1)); RESULTS="$RESULTS\n  FALLA  $N. $title\n         -> $onfail"
    fi
    echo "paso $N: $title -> ok=$ok rc=$rc" >> "$LOG"
}

step auto "La UART existe y tenes permiso" \
    "ls -l /dev/serial0 && test -r /dev/serial0 -a -w /dev/serial0 && id -nG | grep -qw dialout" \
    "/dev/serial0 apunta a ttyAMA0 o ttyS0 y tu usuario esta en el grupo dialout" \
    "No existe: falta enable_uart=1 en /boot/firmware/config.txt (sudo raspi-config nonint do_serial_hw 0) y reiniciar. Sin permiso: sudo usermod -aG dialout \$USER y volver a entrar."

step auto "La Q-board contesta (GET_VERSION)" \
    "$PY $SMOKE/qboard.py version" \
    "GET_VERSION -> [un numero]" \
    "La placa no responde. Revisar: consola serie todavia activa (sudo raspi-config nonint do_serial_cons 1), cable del conector de la cabeza, placa sin alimentacion. Si /dev/serial0 es ttyS0 probar con dtoverlay=disable-bt, y al reves."

step vos "La nariz cambia a azul" \
    "$PY $SMOKE/qboard.py nose blue" \
    "la nariz queda azul y la respuesta repite el comando 45" \
    "La UART anda (paso 2) pero la placa rechaza la trama: mirar si dice NACK. Un NACK aca es un problema de checksum o escape en qbo/protocol.py."

step vos "La boca dibuja una sonrisa" \
    "$PY $SMOKE/qboard.py mouth smile" \
    "los LEDs de la boca forman una sonrisa" \
    "Si la nariz anduvo y esto no, es el comando SET_MOUTH_VALUE (4 bytes) o la matriz de LEDs."

step vos "El sensor tactil devuelve 1, 2 y 3" \
    "$PY $SMOKE/qboard.py touch 10" \
    "aparece 'tactil = 1 (derecha)', '2 (arriba)' y '3 (izquierda)' al tocar cada zona" \
    "Sin respuestas validas: falla la lectura (ReadResponse o el sentido RX de la UART). Con respuestas pero siempre 0: sensores capacitivos."

step vos "La cabeza se mueve y vuelve al centro" \
    "$PY $SMOKE/qboard.py head" \
    "gira a un lado y vuelve, sube y vuelve" \
    "Servos sin alimentacion, o IDs de servo cambiados (ver tools/servo_config.py y la rama legacy-python2, carpeta work-QBOscratch)."

step vos "El parlante suena (SET_ENABLE_SPEAKER + aplay)" \
    "$PY $SMOKE/qboard.py speaker on && aplay -l | grep -i sndrpisimplecar && aplay -L | grep -q convertQBO && speaker-test -D convertQBO -c 1 -t sine -f 440 -l 1" \
    "se oye un tono de 440 Hz por el parlante del robot" \
    "Sin 'sndrpisimplecar' en aplay -l: no esta cargado el modulo my_loader (ver docs/QBO-AUDIO-sndrpisimplecar.md). Sin 'convertQBO': falta /etc/asound.conf. Con las dos cosas y sin sonido: el amplificador no se habilito (paso 2 y 3) o suena por HDMI."

step vos "El microfono graba" \
    "arecord -D dmicQBO_sv -f S16_LE -r 16000 -c 2 -d 4 /tmp/qbo_mic.wav && aplay -D convertQBO /tmp/qbo_mic.wav" \
    "habla durante 4 segundos y despues se escucha tu voz por el parlante" \
    "No existe dmicQBO_sv: /etc/asound.conf. Graba silencio: bus I2S de captura (mismo modulo my_loader que el parlante)."

step vos "pico2wave habla" \
    "command -v pico2wave && QBO_HOME=$HOME_Q $PY -c \"import sys; sys.path.insert(0, sys.argv[1]); from qbo import tts; sys.exit(tts.speak('Hola, soy Tooly', 'spanish', 100))\" $ROOT_Q" \
    "el robot dice 'Hola, soy Tooly'" \
    "Falta pico2wave: instalar libttspico-utils (deploy/install.sh explica como en 32 bits). Si pico2wave existe y no suena, el problema es el paso 7."

step auto "Las camaras entregan imagen" \
    "$PY $ROOT_Q/tools/camera_probe.py" \
    "al menos una linea 'camara N: OK 320x240'. Anotar los indices que dan OK" \
    "Ninguna OK: v4l2-ctl --list-devices y lsusb. Si los indices OK no incluyen camera_index de config.yml ($CAMERA), corregir config.yml."

step auto "Detecta una cara (camara $CAMERA)" \
    "$PY $SMOKE/face_once.py $CAMERA 15" \
    "'cara detectada: centro en (x, y)' al ponerte frente al robot" \
    "Si el paso 10 paso y este no: luz, distancia, o las cascadas Haar no cargan con el OpenCV instalado."

step vos "Reconoce lo que decis (STT)" \
    "QBO_HOME=$HOME_Q $PY $SMOKE/stt_once.py 10" \
    "'transcripcion: ...' con lo que dijiste" \
    "El mensaje dice cual de tres: no existe el microfono dmicQBO_sv, no se oyo nada, o Google no responde (internet, o el servicio gratuito de recognize_google dejo de andar)."

step auto "El LLM responde" \
    "QBO_HOME=$HOME_Q $PY $SMOKE/llm_once.py Hello" \
    "'respuesta en N s: ...'" \
    "El robot no llega al servidor de config.yml (llm_host): revisar red o VPN con curl <llm_host>/api/tags. Si llega y falla, el modelo de llm_model no esta descargado (ollama list)."

step vos "Tooly completo" \
    "QBO_HOME=$HOME_Q $PY $ROOT_Q/apps/tooly.py" \
    "saluda, la nariz pasa a verde al verte, te escucha, contesta y sigue tu cara. Cerrar con q en la ventana o Ctrl+C" \
    "Todos los pasos anteriores pasaron, asi que el problema es de integracion: mirar el traceback. Necesita escritorio grafico (abre una ventana con la camara)."

if [ "$MODE" = run ]; then
    echo
    echo "=== Resumen: $PASSED pasan, $FAILED fallan"
    printf '%b\n' "$RESULTS"
    echo "Registro: $LOG"
    [ "$FAILED" -eq 0 ]
fi
