"""Command line entry point: ``steam-playtime`` / ``python -m steam_playtime``."""
from __future__ import annotations

import argparse
import locale
import sys
import webbrowser
from collections import defaultdict
from pathlib import Path
from typing import List, Optional

from . import __version__, history, report, steam
from .sessions import DEFAULT_EXCLUDED_APPS, normalize_names, parse_sessions


def _detect_lang() -> str:
    try:
        loc = locale.getlocale()[0] or ""
    except ValueError:
        loc = ""
    return "es" if loc.lower().startswith(("es", "spanish")) else "en"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="steam-playtime",
        description="Build a chart of your Steam play time per game over time, from Steam's own session logs.",
    )
    p.add_argument("-o", "--output", default="steam_playtime.html", help="HTML report to write (default: %(default)s)")
    p.add_argument("--steam-dir", help="Steam install folder, if it is not found automatically")
    p.add_argument("--lang", choices=["auto", "en", "es"], default="auto", help="report language (default: system language)")
    p.add_argument("--min-minutes", type=float, default=1.0, help="ignore sessions shorter than this (default: %(default)s)")
    p.add_argument("--exclude", action="append", default=[], metavar="APPID", help="AppID to leave out; repeat for more")
    p.add_argument("--include-all", action="store_true", help="keep apps excluded by default (Wallpaper Engine, redistributables, EA helper)")
    p.add_argument("--history", help="history file that keeps sessions between runs (default: per-user data folder)")
    p.add_argument("--no-history", action="store_true", help="only use the current Steam logs; do not read or update the history file")
    p.add_argument("--csv", metavar="FILE", help="also export every session to CSV")
    p.add_argument("--json", metavar="FILE", help="also export every session to JSON")
    p.add_argument("--no-open", action="store_true", help="do not open the report in the browser")
    p.add_argument("--no-covers", action="store_true", help="do not embed game cover images (smaller report)")
    p.add_argument("--demo", action="store_true", help="build the report from invented sample data, without touching Steam")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    out = Path(args.output).resolve()
    lang = _detect_lang() if args.lang == "auto" else args.lang

    if args.demo:
        from .demo import demo_sessions

        sessions = demo_sessions()
        report.render_html(sessions, out, lang)
        print(f"Report (sample data): {out}")
        if not args.no_open:
            webbrowser.open(out.as_uri())
        return 0

    steam_dir = steam.find_steam_dir(args.steam_dir)
    if not steam_dir:
        print("Steam was not found. Pass its folder with --steam-dir (the one that contains 'logs').", file=sys.stderr)
        return 1
    logs = steam.process_logs(steam_dir)
    if not logs:
        print(f"No gameprocess_log*.txt in {steam_dir / 'logs'}. Launch a game from Steam and try again.", file=sys.stderr)
        return 1

    names = steam.installed_game_names(steam.library_dirs(steam_dir))
    excluded = set(args.exclude) | (set() if args.include_all else DEFAULT_EXCLUDED_APPS)
    sessions = parse_sessions(logs, names, excluded, args.min_minutes)
    print(f"Steam: {steam_dir}")
    print(f"Read {len(sessions)} sessions from {len(logs)} log file(s).")

    if not args.no_history:
        hist_path = Path(args.history) if args.history else history.default_history_path()
        old = [s for s in history.load(hist_path) if s.app not in excluded and s.minutes >= args.min_minutes]
        sessions = history.merge(old, sessions)
        normalize_names(sessions, names)
        history.save(hist_path, sessions)
        print(f"History: {len(sessions)} sessions in total ({hist_path}).")
    else:
        normalize_names(sessions, names)

    if not sessions:
        print("No play sessions found.", file=sys.stderr)
        return 1

    images = {} if args.no_covers else steam.header_images(steam_dir, {s.app for s in sessions})
    report.render_html(sessions, out, lang, steam.playtime_totals(steam_dir), images)
    if args.csv:
        report.write_csv(sessions, Path(args.csv))
    if args.json:
        report.write_json(sessions, Path(args.json))

    totals = defaultdict(float)
    for s in sessions:
        totals[s.name] += s.minutes
    print(f"\n{sessions[0].start:%Y-%m-%d} -> {sessions[-1].end:%Y-%m-%d}")
    for name, mins in sorted(totals.items(), key=lambda x: -x[1])[:10]:
        print(f"  {mins / 60:7.1f} h  {name}")
    print(f"\nReport: {out}")
    if not args.no_open:
        webbrowser.open(out.as_uri())
    return 0
