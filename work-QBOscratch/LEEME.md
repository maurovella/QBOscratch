# work-QBOscratch

Copia de `/home/pi/work/QBOscratch/Python projects/` de la SSD vieja del robot,
tal como estaba (Python 2.7). Era un clon de `faturita/QBOscratch` con cambios
sin commitear, usado como banco de pruebas de servos hasta julio de 2025.

No estaba en ningun repo. Tiene cosas que no existen en otro lado:

- `TestServ.py`, `TestingServos.py`, `dome.py`, `Motor3_config.sh`.
- `QboCmd.py` con un parche propio para el parametro unico pasado como lista.
- `PiFace.py`, `UpHead.py` y `ServoConfig.py` con IDs de servo 175 y 191.
- `PiFaceFast.py` con `VideoCapture(1)`.

Se omiten los `.pyc` y las cascadas Haar, identicas a las de `Python projects/`.
