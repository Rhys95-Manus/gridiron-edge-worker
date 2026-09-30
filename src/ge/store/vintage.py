"""BT-01 version choice over the raw store's pulled_at partitions.

nflverse datasets are *versioned*: each pull is a full season, and nflverse sometimes corrects
the past. A snapshot reads the latest version pulled at or before as_of; for history older than
our first pull it reads the earliest version we hold and says so (after_as_of). Adding a pull
later never changes a past snapshot's choice.

NWS and Kalshi datasets are *observations*: each pull holds different rows (one week, one
forecast), so a snapshot reads every pull at or before as_of instead."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

from ge.ingest.raw import partitions

_TS_FORMAT = "%Y%m%dT%H%M%SZ"


@dataclass(frozen=True)
class Version:
    dataset: str
    season: int
    pulled_at: dt.datetime
    after_as_of: bool
    path: Path

    @property
    def label(self) -> str:
        """Root-independent description, safe to hash into a snapshot digest."""
        stamp = self.pulled_at.strftime(_TS_FORMAT)
        note = " (vintage_after_as_of: earliest version held)" if self.after_as_of else ""
        return f"{self.dataset}/{self.season}@{stamp}{note}"


def _pulled_at(part: Path) -> dt.datetime:
    return dt.datetime.strptime(part.name.split("=", 1)[1], _TS_FORMAT).replace(tzinfo=dt.UTC)


def _all(root: Path, dataset: str, season: int) -> list[tuple[dt.datetime, Path]]:
    return [(_pulled_at(p), p / "part.parquet") for p in partitions(root, dataset, season)]


def choose_version(root: Path, dataset: str, season: int, as_of: dt.datetime) -> Version | None:
    """BT-01: latest version pulled at or before as_of, else the earliest held (labelled)."""
    stored = _all(root, dataset, season)
    if not stored:
        return None
    on_or_before = [(t, p) for t, p in stored if t <= as_of]
    if on_or_before:
        t, p = on_or_before[-1]
        return Version(dataset, season, t, False, p)
    t, p = stored[0]
    return Version(dataset, season, t, True, p)


def observations(root: Path, dataset: str, season: int, as_of: dt.datetime | None) -> list[Version]:
    """BT-01: every pull at or before as_of (all pulls when as_of is None), oldest first."""
    return [
        Version(dataset, season, t, False, p)
        for t, p in _all(root, dataset, season)
        if as_of is None or t <= as_of
    ]
