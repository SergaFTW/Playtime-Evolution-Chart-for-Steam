"""Turn Steam's gameprocess_log into play sessions."""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import PureWindowsPath, PurePosixPath
from typing import Dict, Iterable, List, Optional, Set, Tuple

# AppIDs that are not games or that run all day in the background.
DEFAULT_EXCLUDED_APPS = {
    "228980",   # Steamworks Common Redistributables
    "431960",   # Wallpaper Engine
    "1182480",  # EA app Steam auth helper (duplicates the real EA game)
}
# Helper executables that Steam tracks but are not play time.
EXCLUDED_EXES = {"easteamauthhelper.exe", "steamerrorreporter.exe", "steamerrorreporter64.exe"}

# AppID 480 ("Spacewar") is Valve's public test app. Many games launched outside
# the Steam store use it, so we name those sessions after their executable folder.
SPACEWAR = "480"
SPACEWAR_NAME = "Spacewar (AppID 480)"
REMOTE_PLAY_EXE = "streaming_client.exe"
REMOTE_PLAY_NAME = "Steam Remote Play"

_GENERIC_DIRS = {"bin", "binaries", "win64", "win32", "x64", "x86", "game", "build", "release", "shipping"}

LINE_RE = re.compile(r"^\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\]\s+(.*)$")
ADD_RE = re.compile(r"^AppID (\d+) adding PID (\d+) as a tracked process\s*(.*)$")
REMOVE_RE = re.compile(r"^AppID (\d+) no longer tracking PID (\d+)")
TIME_FMT = "%Y-%m-%d %H:%M:%S"


@dataclass
class Session:
    app: str
    name: str
    start: datetime
    end: datetime

    @property
    def minutes(self) -> float:
        return (self.end - self.start).total_seconds() / 60

    def to_dict(self) -> dict:
        d = asdict(self)
        d["start"] = self.start.isoformat()
        d["end"] = self.end.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Session":
        return cls(d["app"], d["name"], datetime.fromisoformat(d["start"]), datetime.fromisoformat(d["end"]))


def fallback_name(app: str) -> str:
    return f"App {app}"


def is_fallback_name(app: str, name: str) -> bool:
    return name == fallback_name(app)


def exe_path(rest: str) -> Optional[str]:
    """Pull the executable path out of the tail of an 'adding PID' line."""
    s = rest.strip().lstrip('"')
    if not s:
        return None
    m = re.match(r"(.+?\.exe)\b", s, re.IGNORECASE)
    if m:
        return m.group(1)
    return re.split(r'["\s]', s, maxsplit=1)[0] or None


def _pure(path: str):
    return PureWindowsPath(path) if ("\\" in path or re.match(r"^[A-Za-z]:", path)) else PurePosixPath(path)


def name_from_exe(path: str) -> Optional[str]:
    """Best guess at a game name from its executable path."""
    p = _pure(path)
    parts = [x for x in p.parts]
    lowered = [x.lower() for x in parts]
    if "common" in lowered:
        i = lowered.index("common")
        if i > 0 and lowered[i - 1] == "steamapps" and i + 1 < len(parts) - 1:
            return parts[i + 1]
    for folder in reversed(parts[:-1]):
        if folder.lower() not in _GENERIC_DIRS and not folder.endswith((":\\", ":", "/")):
            return folder
    return p.stem or None


def read_events(log_files: Iterable) -> List[Tuple[datetime, str, Optional[str], Optional[str], str]]:
    """(time, kind, app, pid, rest) for every relevant line, in log order."""
    events, seen = [], set()
    for path in log_files:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                m = LINE_RE.match(line.rstrip("\r\n"))
                if not m or line in seen:
                    continue
                seen.add(line)
                ts, body = datetime.strptime(m.group(1), TIME_FMT), m.group(2)
                if body.startswith("Client version"):
                    events.append((ts, "boot", None, None, ""))
                elif (a := ADD_RE.match(body)):
                    events.append((ts, "add", a.group(1), a.group(2), a.group(3)))
                elif (r := REMOVE_RE.match(body)):
                    events.append((ts, "remove", r.group(1), r.group(2), ""))
    events.sort(key=lambda e: e[0])  # stable: same-second lines keep log order
    return events


def parse_sessions(
    log_files: Iterable,
    names: Dict[str, str],
    excluded_apps: Set[str] = DEFAULT_EXCLUDED_APPS,
    min_minutes: float = 1.0,
) -> List[Session]:
    """Pair start/stop lines into sessions, merging overlapping processes of the same game."""
    open_: Dict[Tuple[str, str], Tuple[datetime, Optional[str]]] = {}
    intervals: Dict[str, List[Tuple[datetime, datetime, Optional[str]]]] = {}

    for ts, kind, app, pid, rest in read_events(log_files):
        if kind == "boot":
            # Steam restarted: anything still "running" has no reliable end time.
            open_.clear()
        elif kind == "add":
            exe = exe_path(rest)
            base = _pure(exe).name.lower() if exe else ""
            if app in excluded_apps or base in EXCLUDED_EXES:
                continue
            if base == REMOTE_PLAY_EXE:
                label = REMOTE_PLAY_NAME
            elif app == SPACEWAR:
                label = name_from_exe(exe) if exe else None
            elif app not in names and exe:
                label = name_from_exe(exe)
            else:
                label = None
            open_[(app, pid)] = (ts, label)
        elif (app, pid) in open_:
            start, label = open_.pop((app, pid))
            intervals.setdefault(app, []).append((start, ts, label))

    sessions: List[Session] = []
    for app, ivs in intervals.items():
        ivs.sort(key=lambda x: x[0])
        merged: List[list] = []
        for start, end, label in ivs:
            if merged and start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
                merged[-1][2] = merged[-1][2] or label
            else:
                merged.append([start, end, label])
        for start, end, label in merged:
            if app == SPACEWAR:
                name = label or SPACEWAR_NAME
            else:
                name = names.get(app) or label or fallback_name(app)
            s = Session(app, name, start, end)
            if s.minutes >= min_minutes:
                sessions.append(s)
    sessions.sort(key=lambda s: s.start)
    return sessions


def normalize_names(sessions: List[Session], names: Dict[str, str]) -> None:
    """Give every session of a game the same, best known name (in place)."""
    best: Dict[str, str] = dict(names)
    for s in sorted(sessions, key=lambda s: s.start):
        if s.app in (SPACEWAR,) or is_fallback_name(s.app, s.name) or s.name == REMOTE_PLAY_NAME:
            continue
        best.setdefault(s.app, s.name)
    for s in sessions:
        if s.app != SPACEWAR and s.name != REMOTE_PLAY_NAME and s.app in best:
            s.name = best[s.app]
