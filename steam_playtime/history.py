"""Keep sessions between runs, because Steam only keeps a few months of logs."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Iterable, List

from .sessions import Session, is_fallback_name

FORMAT_VERSION = 1


def default_history_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "steam-playtime" / "history.json"


def load(path: Path) -> List[Session]:
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Session.from_dict(d) for d in data.get("sessions", [])]


def merge(old: Iterable[Session], new: Iterable[Session]) -> List[Session]:
    """Union of both lists. A session is identified by game + start time; the newest read wins,
    except that a real name is never replaced by an 'App 123' placeholder."""
    by_key = {(s.app, s.start): s for s in old}
    for s in new:
        prev = by_key.get((s.app, s.start))
        if prev and is_fallback_name(s.app, s.name) and not is_fallback_name(prev.app, prev.name):
            s.name = prev.name
        by_key[(s.app, s.start)] = s
    return sorted(by_key.values(), key=lambda s: s.start)


def save(path: Path, sessions: List[Session]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps({"version": FORMAT_VERSION, "sessions": [s.to_dict() for s in sessions]}, ensure_ascii=False, indent=0),
        encoding="utf-8",
    )
    tmp.replace(path)
