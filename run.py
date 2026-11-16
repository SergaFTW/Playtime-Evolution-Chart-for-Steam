"""Double-click this file (or run `python run.py`) to build your Steam playtime report."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from steam_playtime.launcher import run  # noqa: E402

sys.exit(run())
