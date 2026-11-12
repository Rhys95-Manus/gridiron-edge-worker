"""PRJ-02 season runner (model mode, unanchored): every game of a season simulated from its
decision-time inputs (BT-01: kickoff - 24 h), one summary row per game. Actual results are
never read here; the calibration report joins them afterwards. 2025 is refused before any read
(BT-07b). Games whose inputs cannot be built are listed with the reason.

Output: data/sim_runs/<model_version>/season=<S>.parquet. Full per-run arrays are regenerated
from the seed when needed (ruling E13)."""

from __future__ import annotations

import datetime as dt
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import yaml

from ge.config import FITTED_ROOT, window_for
from ge.ingest.raw import DATA_ROOT, read_latest
from ge.models.sim import arrays as A
from ge.models.sim.engine import SimResult, simulate
from ge.models.sim.inputs import build_game
from ge.models.sim.league import LeagueTables, load_league
from ge.models.sim.median import interpolated_median
from ge.store.holdout import refuse_holdout

RUNS_ROOT = DATA_ROOT.parent / "sim_runs"
LEAGUE_ROOT = DATA_ROOT.parent / "sim_league"
_TEAM_STATS = {
    "points": A.R_POINTS,
    "off_td": A.R_OFF_TD,
    "pass_yds": A.R_PASS_YDS,
    "rush_yds": A.R_RUSH_YDS,
    "plays": A.R_PLAYS,
    "pass_plays": A.R_PASS_PLAYS,
    "plays_g7": A.R_PLAYS_G7,
    "pass_plays_g7": A.R_PASS_PLAYS_G7,
    "first_downs": A.R_FIRST_DOWNS,
    "third_att": A.R_THIRD_ATT,
    "third_conv": A.R_THIRD_CONV,
    "rush_att": A.R_RUSH_ATT,
    "pass_att": A.R_PASS_ATT,
    "comp": A.R_COMP,
    "drives": A.R_DRIVES,
    "sack_yds": A.R_SACK_YDS,
    "fg_att": A.R_FG_ATT,
    "fg_made": A.R_FG_MADE,
    "punts": A.R_PUNTS,
    "giveaways": A.R_GIVEAWAYS,
    "downs": A.R_DOWNS,
    **{f"att_b{b}": A.R_ATT_B0 + b for b in range(4)},
    **{f"cmp_b{b}": A.R_CMP_B0 + b for b in range(4)},
    **{f"yds_b{b}": A.R_YDS_B0 + b for b in range(4)},
    # diagnostic counters (approved 2026-10-27); *_x10 are tenths of a yard
    **{f"air_att_b{b}_x10": A.R_AIR_ATT_B0 + b for b in range(4)},
    **{f"air_cmp_b{b}_x10": A.R_AIR_CMP_B0 + b for b in range(4)},
    **{f"yac_cmp_b{b}_x10": A.R_YAC_CMP_B0 + b for b in range(4)},
    "gl_clips": A.R_GL_CLIPS,
    "gl_clip_yds": A.R_GL_CLIP_YDS,
    "air_redraws": A.R_AIR_REDRAWS,
    "air_caps": A.R_AIR_CAPS,
    **{f"third_att_run{t}": A.R_THIRD_ATT_RUN0 + t for t in range(A.THIRD_BINS)},
    **{f"third_conv_run{t}": A.R_THIRD_CONV_RUN0 + t for t in range(A.THIRD_BINS)},
    **{f"third_att_pass{t}": A.R_THIRD_ATT_PASS0 + t for t in range(A.THIRD_BINS)},
    **{f"third_conv_pass{t}": A.R_THIRD_CONV_PASS0 + t for t in range(A.THIRD_BINS)},
    # diagnostic counters (approved 2026-10-30); 4th-down cell = distance bin x 3 + field bin,
    # early-down index = (down - 1) x 5 + kind (run, scramble, sack, short pass, deep pass)
    "rz_trips": A.R_RZ_TRIPS,
    "rz_td": A.R_RZ_TD,
    "rz_fg_att": A.R_RZ_FG_ATT,
    **{f"fourth_n{c}": A.R_4TH_N0 + c for c in range(A.FOURTH_CELLS)},
    **{f"fourth_go{c}": A.R_4TH_GO0 + c for c in range(A.FOURTH_CELLS)},
    **{f"fourth_conv{c}": A.R_4TH_CONV0 + c for c in range(A.FOURTH_CELLS)},
    **{f"early_n{k}": A.R_EARLY_N0 + k for k in range(2 * A.EARLY_KINDS)},
    **{f"early_yds{k}": A.R_EARLY_YDS0 + k for k in range(2 * A.EARLY_KINDS)},
    **{f"second_att{t}": A.R_SECOND_ATT0 + t for t in range(A.THIRD_BINS)},
    **{f"second_conv{t}": A.R_SECOND_CONV0 + t for t in range(A.THIRD_BINS)},
    "pen_off": A.R_PEN_OFF,
    "pen_def": A.R_PEN_DEF,
    "pen_def_fd": A.R_PEN_DEF_FD,
    "end_half": A.R_END_HALF,
    **{f"fg_att_d{b}": A.R_FG_ATT_D0 + b for b in range(A.FG_DIST_BINS)},
    **{f"fg_made_d{b}": A.R_FG_MADE_D0 + b for b in range(A.FG_DIST_BINS)},
}
SUMMARY_COLUMNS = (
    "game_id", "season", "week", "home", "away", "postseason", "neutral",
    *(f"{side}_{k}" for side in ("home", "away") for k in _TEAM_STATS),
    "margin_mean", "margin_median", "margin_sd", "total_mean", "total_median", "total_sd",
    "home_win", "ot_rate", "prj01a_spread", "prj01a_total", "prj01a_raw_spread",
    "prj01a_raw_total", "n_runs", "build_seconds", "sim_seconds", "skip_reason",
)  # fmt: skip


def season_games(season: int) -> list[str]:
    """Every game of a season (regular season and postseason), in kickoff order."""
    s = read_latest(DATA_ROOT, "schedules", season).filter(pl.col("season") == season)
    return s.sort("gameday", "gametime", "game_id")["game_id"].to_list()


def load_window_league(season: int) -> LeagueTables:
    window = window_for(season)
    if window is None:
        raise NotImplementedError(f"PRJ-02: season {season} has no fit window")
    active = yaml.safe_load((FITTED_ROOT / "active.yaml").read_text(encoding="utf-8"))
    return load_league(LEAGUE_ROOT / str(active["fit_version"]) / f"{window}.npz")


def summarize(r: SimResult) -> dict[str, Any]:
    t = r.team.astype(np.float64)
    pts = t[:, :, A.R_POINTS]
    margin = pts[:, 0] - pts[:, 1]
    total = pts.sum(axis=1)
    row: dict[str, Any] = {}
    for s, side in enumerate(("home", "away")):
        for k, idx in _TEAM_STATS.items():
            row[f"{side}_{k}"] = float(t[:, s, idx].mean())
    row.update(
        margin_mean=float(margin.mean()),
        margin_median=interpolated_median(margin.astype(np.int64)),
        margin_sd=float(margin.std()),
        total_mean=float(total.mean()),
        total_median=interpolated_median(total.astype(np.int64)),
        total_sd=float(total.std()),
        home_win=float((margin > 0).mean() + 0.5 * (margin == 0).mean()),
        ot_rate=float(r.ot.mean()),
        n_runs=int(pts.shape[0]),
    )
    return row


def run_season(
    season: int,
    *,
    n_runs: int,
    model_version: str,
    out_root: Path = RUNS_ROOT,
    games: list[str] | None = None,
    log: Callable[[str], None] = lambda s: None,
) -> Path:
    refuse_holdout(season, "PRJ-02 season simulation")  # before any read (BT-07b)
    ids = games if games is not None else season_games(season)
    league = load_window_league(season)
    rows: list[dict[str, Any]] = []
    for i, gid in enumerate(ids, 1):
        base: dict[str, Any] = {"game_id": gid, "season": season}
        t0 = time.perf_counter()
        try:
            g, info = build_game(gid, league)
        except NotImplementedError as e:
            rows.append({**base, "skip_reason": str(e)})
            log(f"{gid}: skipped: {e}")
            continue
        t1 = time.perf_counter()
        r = simulate(g, info.league, n_runs, game_id=gid, model_version=model_version)
        t2 = time.perf_counter()
        lines = info.ratings.lines
        rows.append(
            {
                **base,
                "week": info.week,
                "home": info.home,
                "away": info.away,
                "postseason": info.postseason,
                "neutral": info.neutral,
                **summarize(r),
                "prj01a_spread": lines.spread,
                "prj01a_total": lines.total,
                "prj01a_raw_spread": lines.raw_spread,
                "prj01a_raw_total": lines.raw_total,
                "build_seconds": t1 - t0,
                "sim_seconds": t2 - t1,
            }
        )
        if i % 25 == 0:
            log(f"{season}: {i}/{len(ids)} games ({dt.datetime.now(dt.UTC):%H:%M:%S}Z)")
    out = out_root / model_version / f"season={season}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df = pl.DataFrame(rows, infer_schema_length=None)
    for c in SUMMARY_COLUMNS:
        if c not in df.columns:
            df = df.with_columns(pl.lit(None).alias(c))
    df.select(SUMMARY_COLUMNS).write_parquet(out)
    return out
