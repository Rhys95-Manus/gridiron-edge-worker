"""PRJ-02 C0 diagnosis (decision rows 2026-11-23: Q2, Q6, Q-C1 to Q-C7; design in
plans/phase5-c0-diagnosis.md). One bounded ablation on training seasons simulated with a
test-season window, in-sample and disclosed. Diagnosis only: never a gate input, never a season
2021-2025, never a production run.

Each game is built once (inputs.build_game with window_season, which carries DiagnosisParts),
then every variant is recomposed from that build and simulated with the same seed (common random
numbers: (game_id, model_version) for every variant; baseline_seed2 uses model_version + "-seed2"
as the Monte Carlo check). Output: data/sim_runs/diagnosis/<model_version>/season=<S>/
chunk=<NN>.parquet, one row per game and variant. Actual results are never read here."""

from __future__ import annotations

import dataclasses
import datetime as dt
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from ge.models.sim import arrays as A
from ge.models.sim.arrays import GameArrays
from ge.models.sim.backtest import (
    RUNS_ROOT,
    SUMMARY_COLUMNS,
    load_window_league,
    season_games,
    summarize,
)
from ge.models.sim.engine import simulate
from ge.models.sim.inputs import DiagnosisParts, build_game, check_diagnosis_season
from ge.models.sim.settings import load_sim

DIAG_ROOT = RUNS_ROOT / "diagnosis"
SEED2_SUFFIX = "-seed2"
VARIANTS: tuple[str, ...] = (
    "baseline",
    "no_tilt",
    "no_matchup",
    "no_environment",
    "no_player_dev",
    "no_qd_availability",
    "style_neutral",
    "tilt_only",
    "tilt_x2",
    "baseline_seed2",
)
# Q-C2: the stop-rule test counts only variants that change ONE named input or mechanism.
SINGLE_INPUT: tuple[str, ...] = (
    "no_tilt",
    "no_matchup",
    "no_environment",
    "no_player_dev",
    "no_qd_availability",
    "style_neutral",
    "tilt_x2",
)
_TILT_ONLY = ("no_matchup", "no_environment", "no_player_dev", "no_qd_availability",
              "style_neutral")  # fmt: skip
STYLE_FIELDS = (A.T_PACE_N, A.T_PACE_LEAD, A.T_PACE_TRAIL, A.T_PROE_N, A.T_PROE_LEAD,
                A.T_PROE_TRAIL, A.T_GO_OVER, A.T_TWO_PT,
                *range(A.T_CELL0, A.T_CELL0 + 8))  # fmt: skip
DEV_FIELDS = (A.P_CROE, A.P_YACOE, A.P_RYOE, A.P_SCR_SHIFT)
_WINDOW = re.compile(r"^S(\d{4})$")


def check_season(season: int, window_season: int) -> None:
    """PRJ-02 C0: see inputs.check_diagnosis_season (holdout first, then training seasons of the
    window only)."""
    check_diagnosis_season(season, window_season)


def parse_window(window: str) -> int:
    """PRJ-02 C0: 'S2021' -> 2021; only test-season windows (BT-01) are accepted."""
    m = _WINDOW.match(window)
    if m is None:
        raise ValueError(f"PRJ-02 C0: diagnosis window {window!r} is not of the form S<season>")
    season = int(m.group(1))
    from ge.config import load_params

    bt = load_params().backtest
    if not int(bt.bt_01_first_test_season.value) <= season <= int(bt.bt_01_last_test_season.value):
        raise ValueError(f"PRJ-02 C0: {window} is not a test-season window")
    return season


def tilt_probe_k() -> float:
    """Q-C4: the fixed tilt-probe multiplier (config/sim.yaml c0.tilt_probe_k, not fitted)."""
    return float(load_sim().c0.tilt_probe_k.value)


def variant_arrays(
    g: GameArrays, parts: DiagnosisParts | None, variant: str, *, tilt_k: float
) -> GameArrays:
    """PRJ-02 C0: the game's arrays with one variant's inputs switched to their neutral values
    (design table in plans/phase5-c0-diagnosis.md). The tilt, weather, MTC-01 and MTC-03 fields
    are recomposed from the build's DiagnosisParts as _build composes them, so the baseline
    reproduces the build byte for byte. Raises without parts (not a --diagnosis-window build)."""
    if parts is None:
        raise ValueError("PRJ-02 C0: ablation needs a --diagnosis-window build (no DiagnosisParts)")
    if variant not in VARIANTS:
        raise ValueError(f"PRJ-02 C0: unknown variant {variant!r}")
    off = set(_TILT_ONLY) if variant == "tilt_only" else {variant}
    k = 0.0 if "no_tilt" in off else (tilt_k if "tilt_x2" in off else 1.0)
    env, matchup, avail = ("no_environment" in off, "no_matchup" in off,
                           "no_qd_availability" in off)  # fmt: skip
    team, player = g.team.copy(), g.player.copy()
    p = parts

    def tilt(x: float) -> float:
        return 0.0 if k == 0.0 else (x if k == 1.0 else k * x)

    for s in (0, 1):
        t = team[s]
        t[A.T_CMP_SHIFT] = tilt(p.cmp_tilt[s]) + (0.0 if env else p.cmp_w[s])
        t[A.T_YAC_SHIFT] = float(np.clip(tilt(p.yac_tilt[s]), -p.yac_cap, p.yac_cap))
        t[A.T_INT_SHIFT] = tilt(p.int_tilt[s])
        ypc = tilt(p.ypc_tilt[s]) + (0.0 if matchup else p.mtc01[s])
        t[A.T_YPC_SHIFT] = float(np.clip(ypc, -p.ypc_cap, p.ypc_cap))
        t[A.T_FUM_SHIFT] = tilt(p.fum_tilt[s])
        sack = p.sack_league[s] if matchup else p.sack_eta[s]
        t[A.T_SACK_LOGIT] = float(sack + (0.0 if avail else p.sack_ol[s]))
        if env:
            t[[A.T_DEEP_SHIFT, A.T_FG_SHIFT, A.T_EXPL_SHIFT]] = 0.0
        n = int(g.n_players[s])
        if matchup:
            player[s, :n, A.P_MTC02] = 1.0
        if "no_player_dev" in off:
            player[s, :n, list(DEV_FIELDS)] = 0.0
        if avail:
            player[s, :n, A.P_AVAIL] = 1.0
    if "style_neutral" in off:
        f = list(STYLE_FIELDS)
        team[:, f] = (team[0, f] + team[1, f]) / 2
    return dataclasses.replace(g, team=team, player=player)


def run_diagnosis(
    season: int,
    *,
    window: str,
    n_runs: int,
    model_version: str,
    chunk: int,
    chunk_size: int,
    variants: tuple[str, ...] = VARIANTS,
    out_root: Path = DIAG_ROOT,
    log: Callable[[str], None] = lambda s: None,
) -> Path:
    """PRJ-02 C0: simulate one chunk (games chunk*chunk_size .. +chunk_size in kickoff order) of
    a training season with `window`'s fit, every variant per game (Q-C7: about 70-game chunks,
    one process at a time)."""
    window_season = parse_window(window)
    check_season(season, window_season)  # before any read (BT-07b)
    if chunk < 0 or chunk_size <= 0:
        raise ValueError("PRJ-02 C0: chunk must be >= 0 and chunk_size > 0")
    ids = season_games(season)
    part = ids[chunk * chunk_size : (chunk + 1) * chunk_size]
    if not part:
        raise ValueError(f"PRJ-02 C0: season {season} has no chunk {chunk} of {chunk_size} games")
    league = load_window_league(window_season)
    k = tilt_probe_k()
    rows: list[dict[str, Any]] = []
    for i, gid in enumerate(part, 1):
        base: dict[str, Any] = {"game_id": gid, "season": season, "fit_window": window}
        t0 = time.perf_counter()
        try:
            g, info = build_game(gid, league, window_season=window_season)
        except NotImplementedError as e:
            rows += [{**base, "variant": v, "skip_reason": str(e)} for v in variants]
            log(f"{gid}: skipped: {e}")
            continue
        t1 = time.perf_counter()
        lines = info.ratings.lines
        for v in variants:
            arr = variant_arrays(g, info.parts, v, tilt_k=k)
            mv = model_version + SEED2_SUFFIX if v == "baseline_seed2" else model_version
            s0 = time.perf_counter()
            r = simulate(arr, info.league, n_runs, game_id=gid, model_version=mv)
            rows.append(
                {
                    **base,
                    "variant": v,
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
                    "sim_seconds": time.perf_counter() - s0,
                }
            )
        log(f"{season} chunk {chunk}: {i}/{len(part)} games ({dt.datetime.now(dt.UTC):%H:%M:%S}Z)")
    out = out_root / model_version / f"season={season}" / f"chunk={chunk:02d}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df = pl.DataFrame(rows, infer_schema_length=None)
    cols = ("variant", "fit_window", *SUMMARY_COLUMNS)
    for c in cols:
        if c not in df.columns:
            df = df.with_columns(pl.lit(None).alias(c))
    df.select(cols).write_parquet(out)
    return out
