#!/usr/bin/env python3
# Puente de compatibilidad: deamonsScripts/QBO_listen y el README lanzan esta ruta.
# El codigo vive en apps/listen.py.
import os
import runpy

runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "apps", "listen.py"),
               run_name="__main__")
