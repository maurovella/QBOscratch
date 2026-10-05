#!/bin/bash

cd "$(dirname "$0")"
python3 servo_config.py -d 1 -c SET_SERVO_ENABLE 0
python3 servo_config.py -d 1 -c SET_SERVO_CW_LIM 290
python3 servo_config.py -d 1 -c SET_SERVO_CCW_LIM 725