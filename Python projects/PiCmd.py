#!/usr/bin/env python3
# Puente de compatibilidad: deamonsScripts/QBO_PiCmd y el README lanzan esta ruta.
# El codigo vive en apps/picmd.py.
import os
import runpy

runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "apps", "picmd.py"),
               run_name="__main__")
