"""Build a standalone executable with PyInstaller: `pip install pyinstaller`, then `python build_exe.py`.

The result is dist/SteamPlaytime.exe on Windows (dist/SteamPlaytime elsewhere).
"""
import os
import sys

import PyInstaller.__main__

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

PyInstaller.__main__.run([
    os.path.join(ROOT, "run.py"),
    "--name", "SteamPlaytime",
    "--onefile",
    "--console",
    "--clean",
    "--noconfirm",
    "--add-data", f"{os.path.join(ROOT, 'steam_playtime', 'template.html')}{os.pathsep}steam_playtime",
    *sys.argv[1:],
])
