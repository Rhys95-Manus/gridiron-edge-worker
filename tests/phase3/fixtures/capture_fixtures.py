"""Cut the real-data fixture store the phase3 metric tests read. Run once, by hand:

    uv run python tests/phase3/fixtures/capture_fixtures.py [main] [teams] [pre_ftn]

It copies a slice of the local raw store (data/raw, downloaded in Phase 1) into
tests/phase3/fixtures/store/, in the same dataset/season=/pulled_at= layout, keeping each
source partition's pulled_at, so `ge.store.snapshot.snapshot(..., root=STORE)` reads it like the
real store. The slice: every 2023 game (the prior season, for G4 carryover) and 2024 weeks
1-8 (the season under test), with play-by-play pruned to the columns Phase 3 uses; the
seasonless player ID crosswalk and franchise IDs; and 2021 weeks 1-6 schedules and
play-by-play, a season with no FTN charting. `main` rebuilds the store; the others add to it.
Every part
file gets a part.meta.json recording its source file, nflverse source string and pull time, per
CLAUDE.md rule 2. Nothing here chooses a game; tests pick games from the fixture by rule.

Data: nflverse; charting: FTN Data via nflverse.
"""

from __future__ import annotations

import datetime as dt
import json
import shutil
import sys
from pathlib import Path

import polars as pl

HERE = Path(__file__).parent
REPO = HERE.parents[2]
RAW = REPO / "data" / "raw"
STORE = HERE / "store"
PRIOR, SEASON, LAST_WEEK = 2023, 2024, 8

PBP_COLUMNS = [
    "play_id", "game_id", "season", "week", "season_type", "home_team", "away_team",
    "posteam", "defteam", "time_of_day", "qtr", "down", "ydstogo", "yardline_100",
    "goal_to_go", "game_seconds_remaining", "half_seconds_remaining",
    "quarter_seconds_remaining", "score_differential", "wp", "epa", "success", "pass", "rush",
    "qb_dropback", "pass_attempt", "complete_pass", "incomplete_pass", "interception", "sack",
    "qb_hit", "qb_scramble", "qb_kneel", "qb_spike", "play_type", "two_point_attempt",
    "two_point_conv_result", "extra_point_attempt", "field_goal_attempt", "punt_attempt",
    "fourth_down_converted", "fourth_down_failed", "special_teams_play", "shotgun",
    "no_huddle", "run_location", "run_gap", "pass_location", "pass_length", "air_yards",
    "yards_after_catch", "yards_gained", "passing_yards", "receiving_yards", "rushing_yards",
    "lateral_reception", "cp", "cpoe", "xpass", "pass_oe", "xyac_mean_yardage",
    "receiver_player_id", "rusher_player_id", "passer_player_id", "touchdown", "td_team",
    "td_player_id", "pass_touchdown", "rush_touchdown", "drive", "fixed_drive", "timeout",
    "timeout_team", "out_of_bounds", "penalty", "penalty_team", "fumble", "fumble_lost",
    "sack_player_id", "half_sack_1_player_id", "half_sack_2_player_id", "qb_hit_1_player_id",
    "qb_hit_2_player_id", "pass_defense_1_player_id", "pass_defense_2_player_id",
    "interception_player_id", "tackle_for_loss_1_player_id", "tackle_for_loss_2_player_id",
    "home_coach", "away_coach", "pulled_at", "source",
]  # fmt: skip

# dataset -> column holding the week (None: keep every row of the season).
WEEKED = {
    "pbp": "week",
    "ftn_charting": "week",
    "snap_counts": "week",
    "player_stats": "week",
    "injuries": "week",
    "rosters_weekly": "week",
    "depth_charts": "week",
    "nextgen_passing": "week",
    "nextgen_rushing": "week",
    "nextgen_receiving": "week",
    "schedules": None,
    "rosters": None,
}
PRIOR_ONLY = {"rosters"}  # seasonal rosters are end-of-season state: snapshots read season - 1
TARGET_ONLY = {"depth_charts"}  # snapshots read the target season's depth chart only
# DATA-04 ID crosswalk, stored for all seasons under season=0; ID columns only.
PLAYERS_COLUMNS = ["gsis_id", "pfr_id", "pulled_at", "source"]
TEAMS_COLUMNS = ["team_abbr", "team_id", "pulled_at", "source"]
PRE_FTN_SEASON, PRE_FTN_LAST_WEEK = 2021, 6  # FTN charting starts in 2022 (DATA-02)


def _latest(dataset: str, season: int) -> Path:
    parts = sorted((RAW / dataset / f"season={season}").glob("pulled_at=*/part.parquet"))
    if not parts:
        raise SystemExit(f"no {dataset} {season} in data/raw; run `uv run ge ingest nflverse`")
    return parts[-1]


def _cut(dataset: str, season: int) -> None:
    src = _latest(dataset, season)
    cols = {"pbp": PBP_COLUMNS, "players": PLAYERS_COLUMNS, "teams": TEAMS_COLUMNS}.get(dataset)
    df = pl.read_parquet(src, columns=cols)
    wk = WEEKED.get(dataset)
    note = f"every {season} row"
    last = {SEASON: LAST_WEEK, PRE_FTN_SEASON: PRE_FTN_LAST_WEEK}.get(season)
    if last is not None and wk is not None:
        df = df.filter(pl.col(wk).is_between(1, last))
        if "season_type" in df.columns:
            df = df.filter(pl.col("season_type") == "REG")
        if "game_type" in df.columns:
            df = df.filter(pl.col("game_type") == "REG")
        note = f"{season} regular season weeks 1-{last}"
    if dataset == "pbp":
        note += f"; {len(PBP_COLUMNS)} columns kept"
    if dataset == "players":
        note = "every player (seasonless crosswalk); gsis_id and pfr_id only"
    if dataset == "teams":
        note = "every team abbreviation (seasonless); team_abbr and team_id only"
    out_dir = STORE / dataset / f"season={season}" / src.parent.name
    out_dir.mkdir(parents=True, exist_ok=True)
    df.write_parquet(out_dir / "part.parquet")
    meta = {
        "source": str(src.relative_to(REPO)).replace("\\", "/"),
        "source_column": sorted(set(df["source"].to_list())) if "source" in df.columns else None,
        "pulled_at": sorted({str(v) for v in df["pulled_at"].to_list()})
        if "pulled_at" in df.columns
        else None,
        "cut_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        "rows": df.height,
        "note": note,
    }
    (out_dir / "part.meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"{dataset:18} {season} {df.shape} {(out_dir / 'part.parquet').stat().st_size:>10,} B")


def main_slices() -> None:
    """The 2023 + 2024 store and the player ID crosswalk (rebuilds the store from scratch)."""
    if STORE.exists():
        shutil.rmtree(STORE)
    for dataset in WEEKED:
        for season in (PRIOR, SEASON):
            if dataset in PRIOR_ONLY and season != PRIOR:
                continue
            if dataset in TARGET_ONLY and season != SEASON:
                continue
            _cut(dataset, season)
    _cut("players", 0)


def teams() -> None:
    """DATA-04 franchise IDs (G4: relocated teams keep their history), season=0."""
    _cut("teams", 0)


def pre_ftn() -> None:
    """A minimal 2021 slice (FTN charting starts in 2022): schedules and play-by-play for
    regular season weeks 1-PRE_FTN_LAST_WEEK, so a week-6 snapshot has plays but no charting."""
    for dataset in ("schedules", "pbp"):
        _cut(dataset, PRE_FTN_SEASON)


def combine() -> None:
    """DATA-04 combine (ruling 2026-10-04): every draft year from 2000 through the fixture's
    season, all columns (about 330 rows a year)."""
    first = 2000
    for s in range(first, SEASON + 1):
        _cut("combine", s)


STEPS = {"main": main_slices, "teams": teams, "pre_ftn": pre_ftn, "combine": combine}


if __name__ == "__main__":
    for step in sys.argv[1:] or list(STEPS):
        STEPS[step]()
    total = sum(p.stat().st_size for p in STORE.rglob("*.parquet"))
    print(f"total {total:,} B")
