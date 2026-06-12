#! /bin/bash

currentUser=`whoami`

if [ $currentUser=root ]
then
	if [ $# -eq 3 ]
	then
		if [ "$3" == "nopass" ]
		then
			echo "Configurando Wifi: $1"
			echo "" >> /etc/wpa_supplicant/wpa_supplicant.conf
			echo "network={" >> /etc/wpa_supplicant/wpa_supplicant.conf
			echo "        ssid=$1" >> /etc/wpa_supplicant/wpa_supplicant.conf
			echo "        key_mgmt=NONE" >> /etc/wpa_supplicant/wpa_supplicant.conf
			echo "}" >> /etc/wpa_supplicant/wpa_supplicant.conf
		elif [ "$3" == "WEP" ]
		then
			echo "Configurando Wifi: $1"
			echo "" >> /etc/wpa_supplicant/wpa_supplicant.conf
			echo "network={" >> /etc/wpa_supplicant/wpa_supplicant.conf
			echo " 	      ssid=$1" >> /etc/wpa_supplicant/wpa_supplicant.conf
			echo "	      psk=$2" >> /etc/wpa_supplicant/wpa_supplicant.conf
			echo "}" >> /etc/wpa_supplicant/wpa_supplicant.conf
		elif [ "$3" == "WPA" ]
		then
	                echo "Configurando Wifi $1"
	                echo "" >> /etc/wpa_supplicant/wpa_supplicant.conf
	                echo "network={" >> /etc/wpa_supplicant/wpa_supplicant.conf
	                echo "        ssid=$1" >> /etc/wpa_supplicant/wpa_supplicant.conf
	                echo "        psk=$2" >> /etc/wpa_supplicant/wpa_supplicant.conf
	                echo "        key_mgmt=WPA-PSK" >> /etc/wpa_supplicant/wpa_supplicant.conf
	                echo "}" >> /etc/wpa_supplicant/wpa_supplicant.conf
		else
			echo "Tipo de WiFi no soportado"
		fi

		echo "Stopping WPA_SUPPLICANT"
		pidWpaSupplicant=`pidof wpa_supplicant`

		kill $pidWpaSupplicant
		sleep 1

		echo "Starting WPA_SUPPLICANT"
		sudo wpa_supplicant -B -c/etc/wpa_supplicant/wpa_supplicant.conf -iwlan0

	else
		echo "Este script requiere exactamente 3 parametros. Ej. writeWifi.sh SSID PASS TYPE"
	fi

else
	echo "Es necesario ejecutar este script como superusuario"
fi
