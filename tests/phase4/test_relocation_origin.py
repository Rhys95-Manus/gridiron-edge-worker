"""COA-07 travel origin for a relocated franchise (bug fix 2026-10-15), both callers: Phase 3's
coa_07() and PRJ-01a's coa07_features, which share coaching.travel_origin.

The nflverse schedules switch a franchise's abbreviation when it relocates, while its earlier
games keep the old one. A copy of the phase3 fixture store reproduces that: the week-1 game's
home team gets a made-up 2024 abbreviation (its 2023 games keep the real one) and the copy's
teams table maps the new abbreviation to the same franchise. The travel origin (the team's
latest earlier home game, here in 2023) must be found by franchise and give exactly the values
the unrenamed team gets."""

from __future__ import annotations

import shutil
from pathlib import Path

import polars as pl
import pytest

from ge.ingest.nflverse import SEASONLESS
from ge.metrics.coaching import coa_07
from ge.metrics.context import build_context
from ge.models.ratings import coa07_features, franchise_map
from ge.store.snapshot import snapshot
from tests.phase3.conftest import STORE, first_game

NEW = "ZZT"  # a made-up abbreviation, not a real team
GAME = first_game(1)


def _part(root: Path, dataset: str, season: int) -> Path:
    (p,) = sorted((root / dataset / f"season={season}").glob("pulled_at=*/part.parquet"))
    return p


@pytest.fixture(scope="module")
def renamed(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    """(store copy with the relocation, the team's real abbreviation)."""
    dst = tmp_path_factory.mktemp("relocated") / "store"
    shutil.copytree(STORE, dst)
    sched_path = _part(dst, "schedules", 2024)
    sched = pl.read_parquet(sched_path)
    team = str(sched.filter(pl.col("game_id") == GAME)["home_team"][0])
    sched.with_columns(
        pl.col(c).replace(team, NEW) for c in ("home_team", "away_team")
    ).write_parquet(sched_path)
    teams_path = _part(dst, "teams", SEASONLESS)
    teams = pl.read_parquet(teams_path)
    row = teams.filter(pl.col("team_abbr") == team).with_columns(pl.lit(NEW).alias("team_abbr"))
    assert row.height == 1
    pl.concat([teams, row]).write_parquet(teams_path)
    return dst, team


def _values(df: pl.DataFrame, team: str) -> dict[str, float]:
    return {
        r["stat"]: r["value"] for r in df.filter(pl.col("entity_id") == team).iter_rows(named=True)
    }


def test_coa_07_finds_a_relocated_teams_origin(renamed: tuple[Path, str]) -> None:
    root, team = renamed
    want = _values(coa_07(build_context(snapshot(GAME, root=STORE))), team)
    got = coa_07(build_context(snapshot(GAME, root=root)))
    assert _values(got, NEW) == want
    assert set(want) == {"rest_days", "travel_km", "tz_change_hours"}


def _features(root: Path) -> pl.DataFrame:
    snap = snapshot(GAME, root=root)
    sched = pl.concat(
        [snap.collect("schedules"), snap.collect("target_game")], how="diagonal_relaxed"
    )
    return coa07_features(sched, [GAME], franchise_map(snap.collect("teams")))


def test_ratings_features_find_a_relocated_teams_origin(renamed: tuple[Path, str]) -> None:
    root, team = renamed
    cols = ["home", "rest_days", "travel_km", "tz_change_hours"]
    want = _features(STORE).filter(pl.col("team") == team).select(cols)
    got = _features(root).filter(pl.col("team") == NEW).select(cols)
    assert got.height == 1 and got.equals(want)


def test_without_franchise_matching_the_origin_is_lost(renamed: tuple[Path, str]) -> None:
    """The old behaviour (abbreviations matched as they are): no earlier home game, unrated."""
    root, _ = renamed
    snap = snapshot(GAME, root=root)
    sched = pl.concat(
        [snap.collect("schedules"), snap.collect("target_game")], how="diagonal_relaxed"
    )
    with pytest.raises(NotImplementedError, match="COA-07"):
        coa07_features(sched, [GAME])
