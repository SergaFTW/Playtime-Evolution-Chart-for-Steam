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


def _apps_blocks(text: str):
    """Yield (appid, block_body) for every app entry in a localconfig.vdf 'apps' section."""
    m = re.search(r'"apps"\s*\{', text, re.IGNORECASE)
    if not m:
        return
    i, depth = m.end(), 1
    start = i
    while i < len(text) and depth:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    section = text[start : i - 1]
    for app in re.finditer(r'"(\d+)"\s*\{', section):
        j, d = app.end(), 1
        while j < len(section) and d:
            if section[j] == "{":
                d += 1
            elif section[j] == "}":
                d -= 1
            j += 1
        yield app.group(1), section[app.end() : j - 1]


def playtime_totals(steam_dir: Path) -> Dict[str, dict]:
    """Lifetime minutes and last-played time per AppID, from every user's localconfig.vdf.

    Steam keeps these totals forever, so they also cover play time from before
    the session logs start. When several accounts exist, the largest total wins.
    """
    totals: Dict[str, dict] = {}
    for vdf in (steam_dir / "userdata").glob("*/config/localconfig.vdf"):
        try:
            text = vdf.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for app, body in _apps_blocks(text):
            pt = re.search(r'"playtime"\s+"(\d+)"', body, re.IGNORECASE)
            lp = re.search(r'"lastplayed"\s+"(\d+)"', body, re.IGNORECASE)
            if not pt:
                continue
            entry = totals.setdefault(app, {"minutes": 0, "last_played": 0})
            entry["minutes"] = max(entry["minutes"], int(pt.group(1)))
            if lp:
                entry["last_played"] = max(entry["last_played"], int(lp.group(1)))
    return totals


_HEADER_NAMES = ("header.jpg", "library_header.jpg")


def header_images(steam_dir: Path, apps: Iterable[str]) -> Dict[str, Path]:
    """Store header image (460x215) per AppID from Steam's local library cache, when cached.

    Newer clients keep them in librarycache/<appid>/<hash>/; older ones as librarycache/<appid>_header.jpg.
    """
    cache = steam_dir / "appcache" / "librarycache"
    found: Dict[str, Path] = {}
    if not cache.is_dir():
        return found
    for app in set(apps):
        flat = cache / f"{app}_header.jpg"
        if flat.is_file():
            found[app] = flat
            continue
        folder = cache / app
        if not folder.is_dir():
            continue
        for name in _HEADER_NAMES:
            hits = sorted(folder.rglob(name), key=lambda p: p.stat().st_size, reverse=True)
            if hits:
                found[app] = hits[0]
                break
    return found


def process_logs(steam_dir: Path) -> List[Path]:
    """gameprocess_log files, oldest first (Steam rotates the old one to *.previous.txt)."""
    logs = list((steam_dir / "logs").glob("gameprocess_log*.txt"))
    return sorted(logs, key=lambda p: (0 if "previous" in p.name else 1, p.stat().st_mtime))
