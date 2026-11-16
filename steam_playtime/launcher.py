"""Double-click entry point (run.py and the Windows .exe).

Writes the report to the per-user data folder, so it works wherever the
program was unzipped, and keeps the window open so messages can be read.
"""
from __future__ import annotations

import sys

from .cli import _detect_lang, main
from .history import default_history_path

PROMPT = {"es": "\nPulsa Enter para cerrar esta ventana...", "en": "\nPress Enter to close this window..."}


def run() -> int:
    out = default_history_path().parent / "steam_playtime.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        code = main(["-o", str(out)] + sys.argv[1:])
    except Exception as exc:  # show the error instead of a window that vanishes
        print(f"\nError: {exc}", file=sys.stderr)
        code = 1
    try:
        input(PROMPT[_detect_lang()])
    except EOFError:
        pass
    return code


if __name__ == "__main__":
    sys.exit(run())
