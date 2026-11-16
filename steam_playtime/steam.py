"""Locate a Steam installation and read what it knows about installed games."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional


def _candidate_dirs() -> List[Path]:
    home = Path.home()
    dirs: List[Path] = []
    if sys.platform == "win32":
        try:
            import winreg  # type: ignore

            for hive, key, value in (
                (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
            ):
                try:
                    with winreg.OpenKey(hive, key) as k:
                        dirs.append(Path(winreg.QueryValueEx(k, value)[0]))
                except OSError:
                    pass
        except ImportError:
            pass
        for env in ("ProgramFiles(x86)", "ProgramFiles"):
            if os.environ.get(env):
                dirs.append(Path(os.environ[env]) / "Steam")
    elif sys.platform == "darwin":
        dirs.append(home / "Library" / "Application Support" / "Steam")
    else:
        dirs += [
            home / ".steam" / "steam",
            home / ".local" / "share" / "Steam",
            home / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam",
            home / "snap" / "steam" / "common" / ".local" / "share" / "Steam",
        ]
    return dirs


def find_steam_dir(override: Optional[str] = None) -> Optional[Path]:
    """Return the Steam folder (the one that contains ``logs/``), or None."""
    candidates = [Path(override)] if override else _candidate_dirs()
    for d in candidates:
        if (d / "logs").is_dir():
            return d
    return None


def library_dirs(steam_dir: Path) -> List[Path]:
    """All Steam library folders listed in libraryfolders.vdf, plus the main one."""
    libs = [steam_dir]
    for vdf in (steam_dir / "steamapps" / "libraryfolders.vdf", steam_dir / "config" / "libraryfolders.vdf"):
        if vdf.is_file():
            text = vdf.read_text(encoding="utf-8", errors="ignore")
            for raw in re.findall(r'"path"\s+"([^"]+)"', text):
                p = Path(raw.replace("\\\\", "\\"))
                if p not in libs:
                    libs.append(p)
            break
    return libs


def installed_game_names(libraries: Iterable[Path]) -> Dict[str, str]:
    """Map AppID -> name, read from appmanifest_*.acf files."""
    names: Dict[str, str] = {}
    for lib in libraries:
        apps = lib / "steamapps"
        if not apps.is_dir():
            continue
        for acf in apps.glob("appmanifest_*.acf"):
            text = acf.read_text(encoding="utf-8", errors="ignore")
            app = re.search(r'"appid"\s+"(\d+)"', text)
            name = re.search(r'"name"\s+"([^"]+)"', text)
            if app and name:
                names[app.group(1)] = name.group(1)
    return names


def process_logs(steam_dir: Path) -> List[Path]:
    """gameprocess_log files, oldest first (Steam rotates the old one to *.previous.txt)."""
    logs = list((steam_dir / "logs").glob("gameprocess_log*.txt"))
    return sorted(logs, key=lambda p: (0 if "previous" in p.name else 1, p.stat().st_mtime))
