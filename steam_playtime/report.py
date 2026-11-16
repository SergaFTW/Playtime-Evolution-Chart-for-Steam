"""Write the sessions as a self-contained HTML report, CSV or JSON."""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from . import __version__
from .sessions import Session

TEMPLATE = Path(__file__).with_name("template.html")


def render_html(sessions: List[Session], out: Path, lang: str, totals: Optional[Dict[str, dict]] = None) -> None:
    rows = [
        {"app": s.app, "name": s.name, "start": s.start.isoformat(), "end": s.end.isoformat(), "min": round(s.minutes, 1)}
        for s in sessions
    ]
    apps = {s.app for s in sessions}
    lifetime = {app: t["minutes"] for app, t in (totals or {}).items() if app in apps and t.get("minutes")}
    embed = lambda v: json.dumps(v, ensure_ascii=False).replace("</", "<\\/")
    html = (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("__DATA__", embed(rows))
        .replace("__TOTALS__", embed(lifetime))
        .replace("__LANG__", embed(lang))
        .replace("__GENERATED__", embed(datetime.now().isoformat(timespec="minutes")))
        .replace("__VERSION__", embed(__version__))
    )
    out.write_text(html, encoding="utf-8")


def write_csv(sessions: List[Session], out: Path) -> None:
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["app_id", "game", "start", "end", "minutes"])
        for s in sessions:
            w.writerow([s.app, s.name, s.start.isoformat(), s.end.isoformat(), f"{s.minutes:.1f}"])


def write_json(sessions: List[Session], out: Path) -> None:
    out.write_text(json.dumps([dict(s.to_dict(), minutes=round(s.minutes, 1)) for s in sessions], ensure_ascii=False, indent=1), encoding="utf-8")
