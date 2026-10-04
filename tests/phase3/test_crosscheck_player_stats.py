"""BUILD_PLAN Phase 3 cross-check: per player-week targets, carries and receiving yards from
our counting function match nflverse player stats for 2024 (2025 is the BT-07b holdout) on at
least 99% of player-weeks; every mismatch is printed. Reads the local store (realdata)."""

from __future__ import annotations

import polars as pl
import pytest

from ge.ingest.raw import DATA_ROOT, read_latest
from ge.metrics import player

SEASON = 2024
STATS = ("targets", "carries", "receiving_yards")
MIN_MATCH = 0.99  # BUILD_PLAN Phase 3: "on at least 99% of player-weeks"


@pytest.mark.realdata
def test_counts_match_nflverse_player_stats() -> None:
    pbp = read_latest(DATA_ROOT, "pbp", SEASON)
    ours = player.weekly_counts(pbp)
    ps = read_latest(DATA_ROOT, "player_stats", SEASON).filter(
        pl.col("season_type").is_in(["REG", "POST"])
    )
    theirs = ps.select(
        "game_id",
        pl.col("player_id"),
        "player_display_name",
        *[pl.col(s).fill_null(0).cast(pl.Float64).alias(f"{s}_nflverse") for s in STATS],
    )
    j = ours.join(theirs, on=["game_id", "player_id"], how="full", coalesce=True).with_columns(
        [pl.col(s).fill_null(0).cast(pl.Float64) for s in STATS]
        + [pl.col(f"{s}_nflverse").fill_null(0) for s in STATS]
    )
    print(f"\n{SEASON} player-weeks compared: {j.height}")
    failures = []
    for s in STATS:
        rows = j.filter((pl.col(s) != 0) | (pl.col(f"{s}_nflverse") != 0))
        bad = rows.filter(pl.col(s) != pl.col(f"{s}_nflverse"))
        rate = 1 - bad.height / rows.height
        print(f"{s}: {rows.height} player-weeks, {bad.height} mismatches, match {rate:.4%}")
        with pl.Config(tbl_rows=-1, tbl_width_chars=200):
            if bad.height:
                print(
                    bad.select(
                        "game_id", "player_id", "player_display_name", s, f"{s}_nflverse"
                    ).sort("game_id", "player_id")
                )
        if rate < MIN_MATCH:
            failures.append(f"{s}: {rate:.4%}")
    assert not failures, failures
