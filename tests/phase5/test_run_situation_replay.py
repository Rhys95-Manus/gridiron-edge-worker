"""PRJ-02 run yards by situation, realdata check R-1 (approved by Rhys 2026-11-12): replay the
window's run table on a season's G7 designed runs on 1st and 2nd down, each run keeping its run
cell, situation (down x distance bin, config/sim.yaml situation_yards.distance_upper) and
yardline, its yards drawn from the (run cell, situation) category the engine uses (with that
category's fallback), clipped once at the goal line. For each of the 8 situation cells the mean
replayed yards is within max(0.20, 3 x SE) of the actual mean, SE = the season cell's standard
deviation / sqrt(n). Run on 2024 with the S2024 window and on 2023 with the S2023 window. Reads
the local nflverse store (DATA-01); no fixture."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from ge.models.sim.league import RUN_SIT0, SIT_CELLS, SIT_DIST_BINS, situation_cell
from ge.models.sim.settings import load_sim

FLOOR = 0.20
SE_MULT = 3.0
REPLAYS = 40


@pytest.mark.realdata
@pytest.mark.parametrize("season", [2024, 2023])
def test_replay_run_yards_by_situation_with_the_window_table(season: int) -> None:
    from ge.config import ActiveParams, load_params, use_params
    from ge.ingest.raw import DATA_ROOT, read_latest
    from ge.metrics import plays as pf
    from ge.models.sim.backtest import load_window_league

    try:
        pbp = read_latest(DATA_ROOT, "pbp", season)
    except FileNotFoundError as exc:
        pytest.fail(f"realdata test needs the local store: {exc}")
    with use_params(ActiveParams(load_params(), None)):
        runs = pbp.filter(pf.scrimmage() & ~pf.garbage()).filter(pf.designed_run())
        runs = runs.with_columns(pf.run_cell().alias("cell"))
    runs = runs.filter(pl.col("down").is_in([1, 2])).drop_nulls(["ydstogo", "yardline_100"])
    edges = load_sim().situation_yards.distance_upper.value
    sit = situation_cell(runs["down"].to_numpy(), runs["ydstogo"].to_numpy(), edges)
    idx_map = {c: i for i, c in enumerate(pf.RUN_CELLS)}
    cell = runs["cell"].replace_strict(idx_map, return_dtype=pl.Int64).to_numpy()
    cat = RUN_SIT0 + cell * SIT_CELLS + sit
    t = load_window_league(season).run_yards
    src = t.source[cat]
    yl = runs["yardline_100"].to_numpy().astype(np.float64)
    rng = np.random.default_rng(20261112)
    sim = np.zeros((REPLAYS, runs.height))
    for k in np.unique(src):
        m = src == k
        lo, hi = int(t.lo[k]), int(t.hi[k])
        i = np.minimum(lo + np.searchsorted(t.cum[lo:hi], rng.random((REPLAYS, int(m.sum())))),
                       hi - 1)  # fmt: skip
        sim[:, m] = np.minimum(t.values[i], yl[m])
    simmean = sim.mean(axis=0)
    actual = runs["yards_gained"].to_numpy().astype(np.float64)
    misses = []
    assert set(np.unique(sit)) <= set(range(SIT_CELLS))
    for s in range(SIT_CELLS):
        m = sit == s
        n = int(m.sum())
        assert n > 1, (season, s, n)
        diff = float(simmean[m].mean() - actual[m].mean())
        se = float(actual[m].std(ddof=1) / np.sqrt(n))
        tol = max(FLOOR, SE_MULT * se)
        label = f"down {s // SIT_DIST_BINS + 1} bin {s % SIT_DIST_BINS}"
        print(f"{season} {label}: n {n} diff {diff:+.3f} SE {se:.3f} tol {tol:.3f}")
        if abs(diff) > tol:
            misses.append((label, round(diff, 3), round(tol, 3), n))
    assert not misses, (season, misses)
