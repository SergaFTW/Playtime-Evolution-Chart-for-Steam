"""Deterministic sample data, for trying the report without Steam (--demo)."""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import List

from .sessions import Session

# Invented games: name, fake app id, weight, typical session minutes, active period (day offsets)
_GAMES = [
    ("Ashen Keep", "9000001", 9, 95, (0, 330)),
    ("Petal Circuit", "9000002", 6, 55, (40, 330)),
    ("Driftline", "9000003", 4, 70, (0, 160)),
    ("Low Orbit Salvage", "9000004", 3, 120, (90, 260)),
    ("Caravan Chess", "9000005", 2, 30, (0, 330)),
    ("Mirefolk", "9000006", 2, 80, (200, 330)),
    ("Signal Lost", "9000007", 1, 45, (120, 200)),
    ("Tin Harbor", "9000008", 1, 150, (250, 330)),
]


def demo_sessions(days: int = 330, seed: int = 7) -> List[Session]:
    rng = random.Random(seed)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=days)
    sessions: List[Session] = []
    for name, app, weight, typical, (lo, hi) in _GAMES:
        n = int(weight * days / 14)
        for _ in range(n):
            day = rng.randint(lo, min(hi, days))
            begin = start + timedelta(days=day, hours=rng.randint(16, 22), minutes=rng.randint(0, 59))
            length = max(8, rng.gauss(typical, typical / 2.5))
            sessions.append(Session(app, name, begin, begin + timedelta(minutes=length)))
    sessions.sort(key=lambda s: s.start)
    return sessions
