# rpi-i2s-audio

Módulo de kernel `my_loader`: registra la tarjeta de sonido I2S de la cabeza del
QBO (`sndrpisimplecar`), de la que dependen el parlante y el micrófono. Viene de
[PaulCreaser/rpi-i2s-audio](https://github.com/PaulCreaser/rpi-i2s-audio). El
contexto está en `docs/QBO-AUDIO-sndrpisimplecar.md`.

## Compilar e instalar en la Pi

```sh
uname -r                                   # por ejemplo 6.12.75+rpt-rpi-v7
sudo apt install linux-headers-rpi-v7      # Pi 3 con kernel de 32 bits
cd /home/pi/Documents/audio/rpi-i2s-audio
make -C /lib/modules/$(uname -r)/build M=$PWD modules
sudo cp my_loader.ko /lib/modules/$(uname -r)/
sudo depmod -a
sudo modprobe my_loader
aplay -l | grep sndrpisimplecar            # tiene que aparecer la tarjeta
dmesg | tail                               # si no aparece, acá dice por qué
```

Para que cargue en cada arranque, agregar `my_loader` a `/etc/modules`. Hace
falta `dtparam=i2s=on` en `/boot/firmware/config.txt`.

Si `uname -r` termina en `rpi-v8`, el paquete es `linux-headers-rpi-v8`. El
módulo hay que recompilarlo cada vez que se actualiza el kernel.

## Estado

`my_loader.c` compila para los kernels 6.12.75 y 6.18.50 de Raspberry Pi
(`rpi-v7`, ARMv7), verificado en un contenedor con los headers del archivo
oficial. Para eso necesitó dos definiciones de compatibilidad, explicadas al
principio del archivo. El original no compilaba en ninguno de los dos.

**No se cargó nunca en un kernel 6.x.** Compilar no garantiza que la tarjeta
aparezca. Lo que puede fallar al cargarlo y cómo se ve:

- El bus I2S no está habilitado o tiene otro nombre: el módulo busca
  `3f203000.i2s`. Ver `ls /sys/bus/platform/devices | grep i2s`.
- `request module load 'bcm2708-dmaengine'` da error en `dmesg`: es esperable,
  ese módulo ya no existe por separado y el aviso no impide seguir.
