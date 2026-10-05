"""DATA-01 to DATA-05 via nflreadpy, stored per dataset and season in the raw Parquet store.

Data: nflverse; charting: FTN Data via nflverse."""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import nflreadpy as nfl
import polars as pl

from ge.config import load_ingest
from ge.ingest.raw import DATA_ROOT, read_latest, seasons_stored, write_raw

Loader = Callable[[int], pl.DataFrame]


@dataclass(frozen=True)
class Dataset:
    spec_id: str
    loader: Loader
    first_season: int | None = None  # None -> nflverse.first_season from ingest.yaml
    post_season_only: bool = False  # DATA-03: published only after each season ends
    seasonless: bool = False  # one table for all seasons, stored under season=0


SEASONLESS = 0  # the season partition a seasonless dataset is stored under


def _cfg_first() -> int:
    return load_ingest().nflverse.first_season.value


DATASETS: dict[str, Dataset] = {
    "pbp": Dataset("DATA-01", nfl.load_pbp),
    "ftn_charting": Dataset(
        "DATA-02", nfl.load_ftn_charting, first_season=load_ingest().nflverse.ftn_first_season.value
    ),
    "participation": Dataset("DATA-03", nfl.load_participation, post_season_only=True),
    "snap_counts": Dataset("DATA-04", nfl.load_snap_counts),
    "rosters": Dataset("DATA-04", nfl.load_rosters),
    # BT-01: weekly rosters, so a snapshot sees who was on a roster that week (decision
    # 2026-09-30); the seasonal file is end-of-season state.
    "rosters_weekly": Dataset("DATA-04", nfl.load_rosters_weekly),
    "depth_charts": Dataset("DATA-04", nfl.load_depth_charts),
    "schedules": Dataset("DATA-04", nfl.load_schedules),
    "injuries": Dataset("DATA-04", nfl.load_injuries),
    "player_stats": Dataset("DATA-04", nfl.load_player_stats),
    "nextgen_passing": Dataset("DATA-05", lambda s: nfl.load_nextgen_stats(s, "passing")),
    "nextgen_rushing": Dataset("DATA-05", lambda s: nfl.load_nextgen_stats(s, "rushing")),
    "nextgen_receiving": Dataset("DATA-05", lambda s: nfl.load_nextgen_stats(s, "receiving")),
    # Player ID crosswalk: snap counts key players by PFR ID, everything else by GSIS ID
    # (user decision 2026-10-02). One table covering every season.
    "players": Dataset("DATA-04", lambda _s: nfl.load_players(), seasonless=True),
    # Franchise IDs: team_id is shared by a franchise's abbreviations across relocations
    # (spec G4: relocated teams keep their history). One table covering every season.
    "teams": Dataset("DATA-04", lambda _s: nfl.load_teams(), seasonless=True),
    # Combine measurements by draft year (ruling 2026-10-04: under DATA-04; PLY-34's prior).
    "combine": Dataset(
        "DATA-04",
        lambda s: nfl.load_combine([s]),
        first_season=load_ingest().nflverse.combine_first_season.value,
    ),
}


@dataclass(frozen=True)
class PullResult:
    dataset: str
    season: int
    status: str  # written | unchanged | not_published | error
    rows: int = 0
    detail: str = ""


def current_season() -> int:
    return int(nfl.get_current_season())


def ingest_nflverse(
    seasons: list[int], datasets: list[str] | None = None, root: Path = DATA_ROOT
) -> list[PullResult]:
    """DATA-01..05: pull each dataset for each season into the raw store (idempotent)."""
    names = datasets or list(DATASETS)
    unknown = sorted(set(names) - set(DATASETS))
    if unknown:
        raise ValueError(f"unknown datasets {unknown}; choose from {sorted(DATASETS)}")
    now_season = current_season()
    lib = f"nflreadpy {version('nflreadpy')}"
    results = []
    for name in names:
        ds = DATASETS[name]
        first = ds.first_season if ds.first_season is not None else _cfg_first()
        pull_seasons = [SEASONLESS] if ds.seasonless and seasons else seasons
        for season in pull_seasons:
            if season < first and not ds.seasonless:
                continue
            if ds.post_season_only and season >= now_season:
                results.append(
                    PullResult(
                        name,
                        season,
                        "not_published",
                        detail=f"{ds.spec_id}: published only after the season",
                    )
                )
                continue
            try:
                df = ds.loader(season)
            except Exception as exc:  # recorded and reported, never silently dropped
                results.append(
                    PullResult(name, season, "error", detail=f"{type(exc).__name__}: {exc}")
                )
                continue
            pulled_at = dt.datetime.now(dt.UTC)
            source = f"nflverse ({ds.spec_id}) via {lib}: {name}({season})"
            path = write_raw(df, name, season, source=source, root=root, pulled_at=pulled_at)
            results.append(PullResult(name, season, "written" if path else "unchanged", df.height))
    return results


def completed_seasons(root: Path = DATA_ROOT) -> list[int]:
    """Stored seasons whose every scheduled game has a result."""
    out = []
    for season in seasons_stored(root, "schedules"):
        sched = read_latest(root, "schedules", season)
        if sched.height and sched["result"].null_count() == 0:
            out.append(season)
    return out
