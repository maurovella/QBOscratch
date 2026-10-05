#!/usr/bin/env python3
# Puente de compatibilidad: deamonsScripts/QBO_PiFaceFast y el README lanzan esta ruta.
# El codigo vive en apps/face_follow.py.
import os
import runpy

runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "apps", "face_follow.py"),
               run_name="__main__")
