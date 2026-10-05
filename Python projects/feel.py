#!/usr/bin/env python3
# Puente de compatibilidad: deamonsScripts/QBO_feel y el README lanzan esta ruta.
# El codigo vive en apps/feel.py.
import os
import runpy

runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "apps", "feel.py"),
               run_name="__main__")
