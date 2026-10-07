"""Synthetic COA-01 registry rows for tests: placeholders, not real coaches. One row per team,
season and role (schema of 2026-10-07)."""

from __future__ import annotations

import csv
from pathlib import Path

from ge.metrics.coaching import REGISTRY_COLUMNS, ROLES

URL = "https://example.invalid/synthetic-test-row"


def staff(
    team: str,
    since: str,
    *,
    caller: str | None = None,
    dcaller: str | None = None,
    season: int | None = None,
    roles: tuple[str, ...] = ROLES,
) -> list[dict[str, str]]:
    """One synthetic row per role. Play-callers default to TEST-OPC-<team> / TEST-DPC-<team>."""
    names = {
        "head_coach": f"TEST-HC-{team}",
        "offensive_coordinator": f"TEST-OC-{team}",
        "defensive_coordinator": f"TEST-DC-{team}",
        "offensive_play_caller": caller or f"TEST-OPC-{team}",
        "defensive_play_caller": dcaller or f"TEST-DPC-{team}",
    }
    return [
        {
            "team": team,
            "season": str(season or int(since[:4])),
            "role": role,
            "person": names[role],
            "effective_date": since,
            "source_url": URL,
            "quote": "synthetic test row",
            "confidence": "team_or_major",
        }
        for role in roles
    ]


def write(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(REGISTRY_COLUMNS))
        w.writeheader()
        w.writerows(rows)
    return path
