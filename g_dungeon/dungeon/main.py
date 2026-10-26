"""
====================================================================
G-DUNGEONS: PYGAME EDITION (ARSTITEKTUR STANDAR RUBRIK GAME)
====================================================================
Entry point utama untuk menjalankan game.
Menerapkan Main Game Loop, State Machine, dan Pemrograman Berorientasi Objek (OOP).
"""

import os
import sys

# Pastikan root direktori proyek masuk ke dalam sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

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

from engine.game import Game



def main() -> None:
    """Fungsi utama peluncur aplikasi game PyGame."""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
