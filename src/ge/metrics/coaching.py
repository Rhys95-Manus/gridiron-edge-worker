"""Coaching profile (spec section 5). COA-01 is the hand-maintained staff and play-caller
registry, config/coaching_registry.csv: nflverse does not track coordinators or who calls
plays, so every row needs a source link and an effective date. The repo ships the header only;
rows are entered by hand from sources, never from memory (rule 2)."""

from __future__ import annotations

import csv
import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ge.config import REPO_ROOT

REGISTRY_PATH = REPO_ROOT / "config" / "coaching_registry.csv"
REGISTRY_COLUMNS = (
    "team",
    "head_coach",
    "offensive_coordinator",
    "defensive_coordinator",
    "offensive_play_caller",
    "defensive_play_caller",
    "effective_date",
    "source_url",
)
_URL = re.compile(r"^https?://[^\s/]+\.[^\s/]+(/\S*)?$")


class RegistryError(ValueError):
    """COA-01: a registry row failed validation."""


@dataclass(frozen=True)
class RegistryRow:
    team: str
    head_coach: str
    offensive_coordinator: str
    defensive_coordinator: str
    offensive_play_caller: str
    defensive_play_caller: str
    effective_date: dt.date
    source_url: str


@dataclass(frozen=True)
class CoachingRegistry:
    """COA-01 rows. A row describes the staff from its effective date until the team's next
    row."""

    rows: tuple[RegistryRow, ...]

    def current(self, team: str, on: dt.date) -> RegistryRow | None:
        """The team's latest row effective on or before `on`."""
        mine = [r for r in self.rows if r.team == team and r.effective_date <= on]
        return max(mine, key=lambda r: r.effective_date) if mine else None

    def caller(self, team: str, side: Literal["offense", "defense"], on: dt.date) -> str | None:
        r = self.current(team, on)
        if r is None:
            return None
        return r.offensive_play_caller if side == "offense" else r.defensive_play_caller


def load_registry(path: Path = REGISTRY_PATH) -> CoachingRegistry:
    """COA-01: read and validate the registry. Every field is required; effective_date is an
    ISO date; source_url is an http(s) link."""
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != REGISTRY_COLUMNS:
            raise RegistryError(f"COA-01: {path} columns must be {', '.join(REGISTRY_COLUMNS)}")
        rows = []
        for i, raw in enumerate(reader, start=2):
            rows.append(_row(raw, f"{path.name} line {i}"))
    return CoachingRegistry(tuple(rows))


def _row(raw: dict[str, str | None], where: str) -> RegistryRow:
    vals = {c: (raw.get(c) or "").strip() for c in REGISTRY_COLUMNS}
    for c, v in vals.items():
        if not v:
            raise RegistryError(f"COA-01: {where}: {c} is empty")
    try:
        when = dt.date.fromisoformat(vals["effective_date"])
    except ValueError as exc:
        raise RegistryError(f"COA-01: {where}: effective_date {vals['effective_date']!r}") from exc
    if not _URL.match(vals["source_url"]):
        raise RegistryError(f"COA-01: {where}: source_url {vals['source_url']!r} is not a link")
    return RegistryRow(
        team=vals["team"],
        head_coach=vals["head_coach"],
        offensive_coordinator=vals["offensive_coordinator"],
        defensive_coordinator=vals["defensive_coordinator"],
        offensive_play_caller=vals["offensive_play_caller"],
        defensive_play_caller=vals["defensive_play_caller"],
        effective_date=when,
        source_url=vals["source_url"],
    )
