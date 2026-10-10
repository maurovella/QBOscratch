# Simulador: API de herramientas y cabeza 3D

Para mostrar lo que hace el robot sin tenerlo, y para que el arnés y la web se
puedan probar por separado.

```text
sensores ──stream──> ARNÉS ──POST /tools/...──> API DE HERRAMIENTAS ──WebSocket──> WEB
(cámara, mic, tacto)  decide                     apps/tools_api.py                 web/qbo_sim.html
        ▲                                        (y el robot, con --robot)         cabeza 3D
        └──────────── botones de tacto de la página: POST al input del arnés ──────────┘
```

| Parte | Dónde | Qué hace |
| --- | --- | --- |
| Arnés | otro equipo; `tools/fake_harness.py` lo reemplaza para probar | Recibe los sensores, decide y llama a una herramienta |
| API de herramientas | `apps/tools_api.py`, contrato en `qbo/tools.py` | Valida el pedido, lo reenvía a la página y, con `--robot`, lo ejecuta en la Q-board |
| Web | `web/qbo_sim.html` | Dibuja la cabeza 3D con lo que llega por el WebSocket. Sus botones de tacto le escriben al arnés |

## Correr

En una máquina de desarrollo (Windows, Mac o Linux):

```sh
python3 -m pip install aiohttp
python3 apps/tools_api.py          # API + página en http://localhost:8000
python3 tools/fake_harness.py      # opcional: arnés de prueba en :8001
```

Abrir `http://localhost:8000`. Arriba a la derecha tiene que decir *Conectado a
la API*. Probar una herramienta sin la página:

```sh
curl -X POST localhost:8000/tools/nose -H "Content-Type: application/json" -d '{"color": "green"}'
```

En el robot, la misma API además mueve la cabeza real:

```sh
apps/tools_api.py --robot           # /dev/serial0
```

En la Pi `aiohttp` viene por apt (`python3-aiohttp`, en `deploy/apt-packages.txt`).

## Contrato

Congelado. Los nombres de los campos no se cambian por separado.

```text
POST /tools/say    {"text": "Hola, acá estoy"}
POST /tools/nose   {"color": "green"}           none, red, blue, green
POST /tools/mouth  {"expression": "smile"}      smile, sad, serious, love
POST /tools/head   {"axis": 1, "angle": 20}     axis 1 gira, axis 2 inclina
```

- Cada llamada válida responde `200 {"ok": true}`.
- La página se conecta a `ws://<host>:8000/ws` y recibe el mismo JSON del POST.
  Se dibuja así: `say` con globo de texto y voz del navegador en español,
  `nose` en el LED RGB, `mouth` en la matriz de 4×5 y `head` girando o
  inclinando según el eje.
- La API escucha en `0.0.0.0:8000`. Desde otra máquina, la página se abre con la
  IP del servidor.

### Lo que el contrato no decía y quedó decidido

Ningún nombre de campo cambió. Esto es lo que hay que confirmar con el arnés:

1. **Qué herramienta es cada mensaje del WebSocket.** Se reconoce por los
   campos, que no se repiten: `text` es say, `color` es nose, `expression` es
   mouth, `axis` y `angle` son head.
2. **`angle`.** Grados, posición absoluta, 0 = mirando al frente. Eje 1
   positivo gira hacia la derecha del robot; eje 2 positivo mira hacia arriba,
   como en `scratch_extension/robot_control.js`. Se recorta a ±90° (eje 1) y
   ±40° (eje 2).
3. **Pedidos inválidos.** Un color, una expresión o un eje que no existen
   responden `400 {"ok": false, "error": "..."}` y no se dibujan. Una
   herramienta que no existe responde `404`. Las válidas responden siempre
   `200 {"ok": true}`.
4. **Input de tacto.** El arnés todavía no publicó su URL ni su JSON. Mientras
   tanto la página manda `POST http://<host>:8001/sensors/touch` con
   `{"zone": "left" | "up" | "right"}`, que es lo que entiende
   `tools/fake_harness.py`. La URL se cambia en la página o con `?touch=URL`.
   El arnés real tiene que responder con CORS, porque la página está en el
   puerto 8000 y le escribe a otro.
5. **Puertos.** La API usa el 8000. Si el arnés es otro programa en la misma
   máquina, necesita otro puerto: dos programas no pueden escuchar en el mismo.
6. **Una página que se conecta tarde** recibe primero el último `nose`, `mouth`
   y `head` de cada eje, para mostrar el estado actual. `say` no se repite.

## Qué está verificado

`tests/test_tools_api.py`, sin robot:

- Qué acepta y qué rechaza cada herramienta.
- Con robot, los bytes por la UART de `nose` y `mouth` son los mismos que
  mandaba `PiCmd.py` en Python 2.7 (golden master `tests/golden/apps_py2.json`).
  `head` usa la fórmula de `robot_control.js`.
- Cada POST válido responde `200 {"ok": true}` y llega igual por el WebSocket.

Lo que falta ver en el robot real es lo mismo que en `MIGRATION.md`: el sentido
y el rango de los servos, qué fila de la boca queda arriba y el audio, que
depende de `my_loader`. La cabeza 3D dibuja la primera fila de la boca arriba,
que es como se ven bien los patrones de `PiCmd.py`.
