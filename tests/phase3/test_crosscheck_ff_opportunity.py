"""PLY-35 rules (spec synced 2026-10-16): actual values come from ff_opportunity itself and are
cross-checked against nflverse player stats. Per player-game receptions, receiving yards,
rushing yards and receiving + rushing TDs for 2024 (never 2025, the BT-07b holdout) must match
on at least 99% of player-games, the Phase 3 cross-check bar; every mismatch is printed."""

from __future__ import annotations

import polars as pl
import pytest

from ge.ingest.raw import DATA_ROOT, read_latest

SEASON = 2024
MIN_MATCH = 0.99  # BUILD_PLAN Phase 3: "on at least 99% of player-weeks"
PAIRS = {  # ff_opportunity actual -> nflverse player_stats
    "receptions": "receptions",
    "rec_yards_gained": "receiving_yards",
    "rush_yards_gained": "rushing_yards",
    "tds": "tds",
}


@pytest.mark.realdata
def test_ff_actuals_match_player_stats() -> None:
    ff = read_latest(DATA_ROOT, "ff_opportunity", SEASON).filter(pl.col("player_id").is_not_null())
    ours = ff.group_by("game_id", "player_id").agg(
        pl.col("receptions").fill_null(0).sum(),
        pl.col("rec_yards_gained").fill_null(0).sum(),
        pl.col("rush_yards_gained").fill_null(0).sum(),
        (pl.col("rec_touchdown").fill_null(0) + pl.col("rush_touchdown").fill_null(0))
        .sum()
        .alias("tds"),
    )
    ps = read_latest(DATA_ROOT, "player_stats", SEASON).filter(
        pl.col("season_type").is_in(["REG", "POST"])
    )
    theirs = ps.select(
        "game_id",
        "player_id",
        pl.col("receptions").fill_null(0).cast(pl.Float64).alias("receptions_ps"),
        pl.col("receiving_yards").fill_null(0).cast(pl.Float64).alias("receiving_yards_ps"),
        pl.col("rushing_yards").fill_null(0).cast(pl.Float64).alias("rushing_yards_ps"),
        (pl.col("receiving_tds").fill_null(0) + pl.col("rushing_tds").fill_null(0))
        .cast(pl.Float64)
        .alias("tds_ps"),
    )
    j = ours.join(theirs, on=["game_id", "player_id"], how="full", coalesce=True).fill_null(0)
    print(f"\n{SEASON} player-games compared: {j.height}")
    failures = []
    for a, b in PAIRS.items():
        rows = j.filter((pl.col(a) != 0) | (pl.col(f"{b}_ps") != 0))
        bad = rows.filter(pl.col(a) != pl.col(f"{b}_ps"))
        rate = 1 - bad.height / rows.height
        print(f"{a} vs {b}: {rows.height} player-games, {bad.height} mismatches, {rate:.4%} match")
        for r in bad.sort("game_id", "player_id").iter_rows(named=True):
            print(f"  {r['game_id']} {r['player_id']}: ff {r[a]} vs player_stats {r[f'{b}_ps']}")
        if rate < MIN_MATCH:
            failures.append(f"{a}: {rate:.4%}")
    assert not failures, failures
