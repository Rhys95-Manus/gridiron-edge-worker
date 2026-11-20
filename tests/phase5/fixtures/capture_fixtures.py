"""Cut the real-data fixtures the phase5 unit tests use. Run once, by hand:

    uv run python tests/phase5/fixtures/capture_fixtures.py

nflverse slices come from the local raw store (data/raw, downloaded in Phase 1). Every fixture has
a <name>.meta.json recording its source and pull time, per CLAUDE.md rule 2. Games are picked by
rule, never typed by hand. Never 2025.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import polars as pl

HERE = Path(__file__).parent
REPO = HERE.parents[2]
RAW = REPO / "data" / "raw"
TIMEOUT_COLUMNS = (
    "game_id", "play_id", "season", "game_half", "qtr", "posteam", "defteam", "home_team",
    "away_team", "play_type", "game_seconds_remaining", "half_seconds_remaining",
    "score_differential", "posteam_timeouts_remaining", "defteam_timeouts_remaining",
    "home_timeouts_remaining", "away_timeouts_remaining", "timeout", "timeout_team", "penalty",
    "out_of_bounds", "complete_pass", "incomplete_pass", "sack", "interception", "fumble_lost",
    "touchdown", "two_point_attempt", "pulled_at", "source",
)  # fmt: skip


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


def _latest(dataset: str, season: int) -> Path:
    parts = sorted((RAW / dataset / f"season={season}").glob("pulled_at=*/part.parquet"))
    if not parts:
        raise SystemExit(f"no {dataset} {season} in data/raw; run `uv run ge ingest nflverse`")
    return parts[-1]


def timeouts_2022() -> None:
    """Every row of the first two 2022 games (schedule kickoff order) that have a running-clock
    snap inside 2:00 of the 2nd or 4th quarter where the timeout-row order and the
    home/away timeouts-remaining drop disagree about a timeout before the next snap."""
    season = 2022
    pbp_path, sched_path = _latest("pbp", season), _latest("schedules", season)
    pbp = pl.read_parquet(pbp_path, columns=list(TIMEOUT_COLUMNS))
    order = (
        pl.read_parquet(sched_path)
        .filter(pl.col("season") == season)
        .sort("gameday", "gametime", "game_id")["game_id"]
        .to_list()
    )
    is_to = (pl.col("timeout") == 1).fill_null(False).cast(pl.Int64)
    rows = pbp.sort("game_id", "play_id").with_columns(is_to.cum_sum().over("game_id").alias("_to"))
    snaps = rows.filter(
        pl.col("play_type").is_in(["run", "pass"]) & pl.col("posteam").is_not_null()
        | pl.col("play_type").is_in(["qb_kneel", "qb_spike", "field_goal", "punt", "kickoff"])
    )
    nxt = snaps.with_columns(
        *[pl.col(c).shift(-1).over("game_id", "game_half").alias(f"{c}_n")
          for c in ("_to", "home_timeouts_remaining", "away_timeouts_remaining")]
    )  # fmt: skip
    late = nxt.filter(
        pl.col("qtr").is_in([2, 4])
        & (pl.col("half_seconds_remaining") <= 120)
        & pl.col("play_type").is_in(["run", "pass"])
        & (pl.col("out_of_bounds") == 0)
        & (pl.col("incomplete_pass") == 0)
        & pl.col("_to_n").is_not_null()
    )
    late = late.with_columns(
        (pl.col("_to_n") > pl.col("_to")).alias("by_order"),
        (
            (pl.col("home_timeouts_remaining_n") < pl.col("home_timeouts_remaining"))
            | (pl.col("away_timeouts_remaining_n") < pl.col("away_timeouts_remaining"))
        ).alias("by_drop"),
    )
    bad = set(late.filter(pl.col("by_order") != pl.col("by_drop"))["game_id"].to_list())
    games = [g for g in order if g in bad][:2]
    df = pbp.filter(pl.col("game_id").is_in(games)).sort("game_id", "play_id")
    name = "pbp_timeouts_2022"
    df.write_parquet(HERE / f"{name}.parquet")
    meta = {
        "source": [str(p.relative_to(REPO)).replace("\\", "/") for p in (pbp_path, sched_path)],
        "source_column": sorted({str(v) for v in df["source"].to_list()}),
        "pulled_at": sorted({str(v) for v in df["pulled_at"].to_list()}),
        "cut_at": _now(),
        "rows": df.height,
        "games": games,
        "note": "every row of the first two 2022 games (kickoff order) where a late running-clock "
        "snap's timeout-row order and timeouts-remaining drop disagree (data correction D, "
        "approved by Rhys 2026-11-20)",
    }
    (HERE / f"{name}.meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print("wrote", name, df.shape, games)


if __name__ == "__main__":
    steps = {"timeouts_2022": timeouts_2022}
    for step in sys.argv[1:] or list(steps):
        steps[step]()
