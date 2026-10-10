"""
Package: g_dungeon/engine
Description: Modul engine game berbasis PyGame untuk G-Dungeons.
"""

import os
import sys

# Konfigurasi direktori DLL pada Windows agar SDL2_image dapat memuat libpng16-16.dll
if sys.platform == "win32":
    try:
        import ctypes
        import pygame
        _pg_dir = os.path.dirname(pygame.__file__)
        if hasattr(os, "add_dll_directory") and os.path.isdir(_pg_dir):
            os.add_dll_directory(_pg_dir)
        os.environ["PATH"] = _pg_dir + os.pathsep + os.environ.get("PATH", "")
        for _f in os.listdir(_pg_dir):
            if _f.lower().endswith(".dll"):
                try:
                    ctypes.CDLL(os.path.join(_pg_dir, _f))
                except Exception:
                    pass
    except Exception:
        pass

