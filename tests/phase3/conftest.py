"""Phase 3 fixtures: a real-data store slice (tests/phase3/fixtures/store, cut by
capture_fixtures.py) and snapshots built from it. Test games are picked from that store by
rule, never typed in."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from ge.store.snapshot import Snapshot, snapshot

_HERE = Path(__file__).parent
FIXTURES = _HERE / "fixtures"
STORE = FIXTURES / "store"
SEASON = 2024
MAIN_WEEK = 8  # weeks 1-7 (and earlier week-8 games) visible: past G4's carryover window
G4_WEEK = 3  # inside G4's weeks 1-4


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if _HERE in Path(item.fspath).parents:
            item.add_marker(pytest.mark.phase3)


def _parts(dataset: str, season: int) -> list[Path]:
    return sorted((STORE / dataset / f"season={season}").glob("pulled_at=*/part.parquet"))


def store_table(dataset: str, season: int) -> pl.DataFrame:
    """One fixture partition, after checking it records its source and pull date (rule 2)."""
    (part,) = _parts(dataset, season)
    meta = json.loads((part.parent / "part.meta.json").read_text(encoding="utf-8"))
    assert meta["source"] and meta["pulled_at"], f"{dataset} {season}: no source / pull date"
    return pl.read_parquet(part)


def first_game(week: int, season: int = SEASON) -> str:
    """The first game of a week by game_id: a rule, not a hand-picked game."""
    sched = store_table("schedules", season)
    return str(sched.filter(pl.col("week") == week).sort("game_id")["game_id"][0])


@pytest.fixture(scope="session")
def main_snap() -> Snapshot:
    return snapshot(first_game(MAIN_WEEK), root=STORE)


@pytest.fixture(scope="session")
def g4_snap() -> Snapshot:
    return snapshot(first_game(G4_WEEK), root=STORE)


@pytest.fixture(scope="session")
def ctx(main_snap: Snapshot):  # type: ignore[no-untyped-def]
    from ge.metrics.context import build_context

    return build_context(main_snap)


@pytest.fixture(scope="session")
def rows(main_snap: Snapshot) -> list[dict]:  # type: ignore[type-arg]
    """Current-season play-by-play rows visible in the main snapshot."""
    pbp = main_snap.collect("pbp")
    return pbp.filter(pl.col("season") == main_snap.season).to_dicts()


@pytest.fixture(scope="session")
def ftn(main_snap: Snapshot) -> dict[tuple[str, int], dict]:  # type: ignore[type-arg]
    """FTN rows keyed by (game_id, play_id)."""
    f = main_snap.collect("ftn_charting")
    return {(r["nflverse_game_id"], int(r["nflverse_play_id"])): r for r in f.to_dicts()}


@pytest.fixture(scope="session")
def teams(main_snap: Snapshot) -> list[str]:
    s = main_snap.collect("schedules").filter(pl.col("season") == main_snap.season)
    return sorted(set(s["home_team"].to_list()) | set(s["away_team"].to_list()))
