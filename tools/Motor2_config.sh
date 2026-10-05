#!/bin/bash

cd "$(dirname "$0")"
python3 servo_config.py -d 1 -c SET_SERVO_ENABLE 0
python3 servo_config.py -d 1 -c SET_SERVO_ID 2
python3 servo_config.py -d 2 -c SET_SERVO_CW_LIM 420
python3 servo_config.py -d 2 -c SET_SERVO_CCW_LIM 550