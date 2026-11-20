"""PRJ-02 data correction D (approved by Rhys 2026-11-20; plans/phase5-late-timeouts.md): whether a
timeout came between two snaps, and which team called it. For seasons from config/sim.yaml
league.timeout_drop_from_season on, read it from a drop in home/away_timeouts_remaining from one
snap to the next in the same game half (the side whose count dropped called it); earlier seasons
keep the timeout-row order. Used by the clock runoff pairs (C1), the timeout rates (C9) and the
spike rate. Synthetic placeholder plays, plus one fixture cut from 2022 nflverse data
(fixtures/pbp_timeouts_2022.parquet, source and pull time in its .meta.json)."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from ge.models.sim.league import RUNNING_CLOCK, snap_pairs, timeout_rates
from ge.models.sim.settings import load_sim

FIXTURE = Path(__file__).parent / "fixtures" / "pbp_timeouts_2022.parquet"
DROP_FROM = 2022  # test setting; the config value is checked separately


def test_drop_from_season_comes_from_config() -> None:
    e = load_sim().league.timeout_drop_from_season
    assert e.value == 2022
    assert e.spec_id == "PRJ-02" and e.status == "initial"


def _game(season: int, *, row_after_next: bool, count_lags: bool = False) -> pl.DataFrame:
    """Q4 inside 2:00, home AAA on offense, trailing: AAA runs in bounds (play 1, 110 s), AAA
    calls its timeout, AAA throws incomplete (80 s, a stopped-clock snap), then runs (60 s).
    row_after_next lists the timeout row after the next snap (the 2022+ pattern); count_lags
    drops AAA's remaining count one snap late (the pre-2022 pattern)."""
    to_row = {"play_type": "no_play", "posteam": None, "defteam": None, "timeout": 1,
              "timeout_team": "AAA", "sec": 80.0}  # fmt: skip
    snap = {"play_type": "run", "posteam": "AAA", "defteam": "BBB", "timeout": 0,
            "timeout_team": None}  # fmt: skip
    a = {**snap, "sec": 110.0}
    b = {**snap, "play_type": "pass", "sec": 80.0}
    c = {**snap, "sec": 60.0}
    seq = [a, b, to_row, c] if row_after_next else [a, to_row, b, c]
    home_left = [2, 2, 1, 1] if count_lags else [2, 1, 1, 1]
    rows = []
    k = 0
    for i, r in enumerate(seq):
        is_snap = r["timeout"] == 0
        left = float(home_left[k] if is_snap else 1)
        rows.append({**r, "play_id": float(i + 1), "home_left": left})
        k += int(is_snap)
    n = len(rows)
    return pl.DataFrame(
        {
            "game_id": ["G"] * n,
            "play_id": [r["play_id"] for r in rows],
            "season": [season] * n,
            "game_half": ["Half2"] * n,
            "qtr": [4.0] * n,
            "posteam": [r["posteam"] for r in rows],
            "defteam": [r["defteam"] for r in rows],
            "home_team": ["AAA"] * n,
            "away_team": ["BBB"] * n,
            "play_type": [r["play_type"] for r in rows],
            "penalty": [0] * n,
            "timeout": [r["timeout"] for r in rows],
            "timeout_team": [r["timeout_team"] for r in rows],
            "game_seconds_remaining": [r["sec"] for r in rows],
            "half_seconds_remaining": [r["sec"] for r in rows],
            "score_differential": [-3.0] * n,
            "posteam_timeouts_remaining": [r["home_left"] for r in rows],
            "defteam_timeouts_remaining": [3.0] * n,
            "home_timeouts_remaining": [r["home_left"] for r in rows],
            "away_timeouts_remaining": [3.0] * n,
            "out_of_bounds": [0] * n,
            "complete_pass": [0] * n,
            "incomplete_pass": [int(r["play_type"] == "pass") for r in rows],
            "sack": [0] * n,
            "interception": [0] * n,
            "fumble_lost": [0] * n,
            "touchdown": [0] * n,
            "two_point_attempt": [0] * n,
            "w": [1.0] * n,
        },
        schema_overrides={"timeout_team": pl.String, "posteam": pl.String, "defteam": pl.String},
    )


def _first_pair(d: pl.DataFrame, drop_from: int) -> dict[str, object]:
    _, nxt = snap_pairs(d, drop_from=drop_from)
    first = nxt.filter(pl.col("play_id") == 1.0).select("_tb", "_tb_off", "_tb_def")
    return first.row(0, named=True)


def test_2022_row_listed_late_is_found_by_the_count_drop() -> None:
    d = _game(2022, row_after_next=True)
    assert _first_pair(d, DROP_FROM) == {"_tb": True, "_tb_off": True, "_tb_def": False}
    # by row order (a later switch season) the same pair shows no timeout
    assert _first_pair(d, 2023)["_tb"] is False


def test_pre_2022_keeps_row_order_when_the_count_lags() -> None:
    d = _game(2019, row_after_next=False, count_lags=True)
    assert _first_pair(d, DROP_FROM) == {"_tb": True, "_tb_off": True, "_tb_def": False}


def test_both_teams_call_one_each() -> None:
    d = _game(2022, row_after_next=True).with_columns(
        pl.when(pl.col("play_id") >= 2.0).then(2.0).otherwise(3.0).alias("away_timeouts_remaining")
    )
    assert _first_pair(d, DROP_FROM) == {"_tb": True, "_tb_off": True, "_tb_def": True}


def test_rates_use_the_count_drop_from_2022() -> None:
    """The one running-clock play inside 2:00 is followed by an offense timeout: the Q4
    offense-trailing rate is 1 by the drop, 0 by row order (the row is listed after the next
    snap)."""
    d = _game(2022, row_after_next=True)
    rates, _ = timeout_rates(d, two_minute=120, drop_from=DROP_FROM)
    assert rates[1, 0, 0] == pytest.approx(1.0)
    old, _ = timeout_rates(d, two_minute=120, drop_from=2023)
    assert old[1, 0, 0] == pytest.approx(0.0)


def test_real_2022_fixture() -> None:
    """On the cut 2022 games, every snap pair's flags equal the count drop computed here from the
    raw columns, and the fixture holds pairs where row order disagrees."""
    raw = pl.read_parquet(FIXTURE)
    assert set(raw["season"].to_list()) == {2022}
    _, nxt = snap_pairs(raw, drop_from=DROP_FROM)
    p = nxt.with_columns(
        pl.col("home_timeouts_remaining").shift(-1).over("game_id", "game_half").alias("h_n"),
        pl.col("away_timeouts_remaining").shift(-1).over("game_id", "game_half").alias("a_n"),
    ).filter(pl.col("h_n").is_not_null())
    home_drop = pl.col("h_n") < pl.col("home_timeouts_remaining")
    away_drop = pl.col("a_n") < pl.col("away_timeouts_remaining")
    off_home = pl.col("posteam") == pl.col("home_team")
    want = p.select(
        (home_drop | away_drop).alias("tb"),
        pl.when(off_home).then(home_drop).otherwise(away_drop).alias("off"),
        pl.when(off_home).then(away_drop).otherwise(home_drop).alias("def"),
        (pl.col("_to_n") > pl.col("_to")).alias("order"),
        pl.col("cat_name").is_in(RUNNING_CLOCK).alias("running"),
    )
    got = p.select("_tb", "_tb_off", "_tb_def")
    assert got["_tb"].to_list() == want["tb"].to_list()
    assert got["_tb_off"].to_list() == want["off"].to_list()
    assert got["_tb_def"].to_list() == want["def"].to_list()
    disagree = want.filter(pl.col("running") & (pl.col("tb") != pl.col("order")))
    assert disagree.height > 0
