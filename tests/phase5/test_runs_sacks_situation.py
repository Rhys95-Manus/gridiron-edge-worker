"""PRJ-02 run yards and MTC-03 sack rate by situation (ruling 2026-10-30, P5).
R1: every run category is a weighted Kaplan-Meier estimate with offensive-TD runs censored at
their yards (the goal line ended them), so the simulation clips once.
R2: designed runs on 3rd or 4th down with more than short_yardage.max_togo to go draw from a
pooled late-down category (parent: every designed run).
S1: P(sack) = expit(game sack logit + league offset[down group, distance bin]), the offset
logit(cell rate) - logit(overall rate), thin cells falling back to their down group.
Synthetic placeholder plays; the last two tests replay 2024 (realdata)."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import polars as pl
import pytest

from ge.models.sim import arrays as A
from ge.models.sim.league import (
    LATE_DOWN,
    RUN_CATEGORIES,
    RUN_CELL_COUNT,
    RUN_SIT0,
    SACK_DIST_BINS,
    SACK_DOWN_GROUPS,
    SHORT_YARDAGE,
    SIT_CELLS,
    pack_runs,
    pack_sack_offsets,
    situation_cell,
)
from ge.models.sim.settings import load_sim
from tests.phase5.sim_synth import _packed, _run_packed, synthetic_game, synthetic_league


def _masses(p, k: int) -> dict[float, float]:  # type: ignore[no-untyped-def]
    lo, hi = int(p.lo[k]), int(p.hi[k])
    prev = np.concatenate([[0.0], p.cum[lo:hi][:-1]])
    out: dict[float, float] = {}
    for v, m in zip(p.values[lo:hi], p.cum[lo:hi] - prev, strict=True):
        if m > 0:
            out[float(v)] = out.get(float(v), 0.0) + float(m)
    return out


def _logit(p: float) -> float:
    return float(np.log(p / (1 - p)))


def test_sack_distance_edges_come_from_config() -> None:
    assert load_sim().sacks.distance_upper.value == [2, 6, 10]


def _runs(td: list[bool] | None = None) -> pl.DataFrame:
    """Middle-cell runs: 1st & 10 at the 50 for 0 and 5; 2nd & 6 at the 3 for 3 (a TD when
    td[2]); 1st & 10 at the 40 for 10; 3rd & 5 at the 30 for 7 and 4th & 8 at the 45 for 2 (late
    down); 3rd & 2 at the 40 for 1 (short yardage)."""
    td = td or [False] * 7
    return pl.DataFrame({
        "cell": ["middle"] * 7,
        "yards_gained": [0.0, 5.0, 3.0, 10.0, 7.0, 2.0, 1.0],
        "down": [1.0, 1.0, 2.0, 1.0, 3.0, 4.0, 3.0],
        "ydstogo": [10.0, 10.0, 6.0, 10.0, 5.0, 8.0, 2.0],
        "yardline_100": [50.0, 50.0, 3.0, 40.0, 30.0, 45.0, 40.0],
        "touchdown": [1.0 if t else 0.0 for t in td],
        "td_team": ["A" if t else None for t in td],
        "posteam": ["A"] * 7,
        "w": [1.0] * 7,
    })  # fmt: skip


def test_runs_without_touchdowns_keep_their_weights() -> None:
    p = pack_runs(_runs(), min_events=1)
    mid = list(pf_cells()).index("middle")
    every = (0.0, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0)
    assert _masses(p, mid) == pytest.approx({v: 1 / 7 for v in every})


def pf_cells():  # type: ignore[no-untyped-def]
    from ge.metrics import plays as pf

    return pf.RUN_CELLS


def test_touchdown_runs_are_censored() -> None:
    """The 3-yard TD run is censored: values 0, 1, 2, 3c, 5, 7, 10 (unit weights). Up to 2 each
    keeps 1/7 (S = 4/7); at 3 no event; 5, 7, 10 share S = 4/7 equally (at risk 3, 2, 1):
    4/21 each."""
    p = pack_runs(_runs([False, False, True, False, False, False, False]), min_events=1)
    mid = list(pf_cells()).index("middle")
    got = _masses(p, mid)
    assert 3.0 not in got
    assert got == pytest.approx({0.0: 1 / 7, 1.0: 1 / 7, 2.0: 1 / 7, 5.0: 4 / 21, 7.0: 4 / 21,
                                 10.0: 4 / 21})  # fmt: skip
    assert _masses(p, RUN_CELL_COUNT) == pytest.approx(got)  # every run: censored too


def test_late_down_category() -> None:
    p = pack_runs(_runs(), min_events=1)
    assert LATE_DOWN == SHORT_YARDAGE + 1 == RUN_CELL_COUNT + 2 == 10
    assert len(p.lo) == RUN_CATEGORIES
    assert _masses(p, LATE_DOWN) == pytest.approx({2.0: 0.5, 7.0: 0.5})  # 3rd & 5, 4th & 8
    assert p.n[LATE_DOWN] == 2
    assert pack_runs(_runs(), min_events=3).source[LATE_DOWN] == RUN_CELL_COUNT


def _late_zero_league():  # type: ignore[no-untyped-def]
    """Cells and every run gain 2-25 yards, short yardage always 2, the late-down category 0."""
    run = [2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 12.0, 25.0]
    return replace(synthetic_league(), run_yards=_run_packed([run] * 9 + [[2.0], [0.0]]))


def test_late_down_runs_use_their_category() -> None:
    from ge.models.sim.engine import simulate

    r = simulate(synthetic_game(), _late_zero_league(), 3000, game_id="G_LATE", model_version="m1")
    t = r.team.astype(np.int64).sum(axis=(0, 1))
    run_att, run_conv = A.R_THIRD_ATT_RUN0, A.R_THIRD_CONV_RUN0
    assert t[run_att + 2 : run_att + 6].sum() > 0  # 3rd & 3 or more
    assert t[run_conv + 2 : run_conv + 6].sum() == 0  # late-down category: 0 yards
    assert t[run_conv] > 0 and t[run_conv + 1] > 0  # 3rd & 1, 3rd & 2: short yardage
    for d in (0, 1):  # 1st and 2nd down runs still draw from their cells (mean 8.1 yards)
        k = d * A.EARLY_KINDS + A.E_RUN
        assert t[A.R_EARLY_N0 + k] > 0
        assert t[A.R_EARLY_YDS0 + k] > 3 * t[A.R_EARLY_N0 + k]


def test_tables_without_the_late_down_category_are_refused() -> None:
    from ge.models.sim.engine import simulate

    old = replace(synthetic_league(), run_yards=_packed([[1.0, 3.0]] * 10))
    with pytest.raises(ValueError, match="late-down"):
        simulate(synthetic_game(), old, 10, game_id="G_OLD", model_version="m1")


def _drops() -> pl.DataFrame:
    """Dropbacks: (down, ydstogo, sacks, non-sacks) per cell; unit weights."""
    cells = [(1, 10, 40, 760), (1, 5, 1, 99), (2, 8, 50, 850), (3, 8, 100, 900), (3, 1, 30, 470)]
    rows = []
    for down, togo, s, ns in cells:
        x, y = float(down), float(togo)
        rows += [(x, y, 1.0, 1.0)] * s + [(x, y, 0.0, 1.0)] * ns
    return pl.DataFrame(rows, schema=["down", "ydstogo", "sack", "w"], orient="row")


def test_sack_offsets_are_logit_differences_with_down_group_fallback() -> None:
    d = _drops()
    off = pack_sack_offsets(d, edges=[2, 6, 10], min_events=30)
    assert off.shape == (SACK_DOWN_GROUPS, SACK_DIST_BINS) == (3, 4)
    base = _logit(221 / 3300)
    assert off[0, 2] == pytest.approx(_logit(40 / 800) - base)  # 1st & 7-10
    assert off[0, 1] == pytest.approx(_logit(41 / 900) - base)  # 1st & 3-6: 1 sack, down group
    assert off[0, 0] == pytest.approx(_logit(41 / 900) - base)  # empty: down group
    assert off[1, 2] == pytest.approx(_logit(50 / 900) - base)
    assert off[2, 2] == pytest.approx(_logit(100 / 1000) - base)
    assert off[2, 0] == pytest.approx(_logit(30 / 500) - base)
    assert off[2, 3] == pytest.approx(_logit(130 / 1500) - base)  # empty: down group 3rd/4th


def test_sack_offsets_reproduce_the_overall_rate_on_the_training_mix() -> None:
    """Without fallbacks, expit(base + offset) is each cell's rate, so the weighted mean over
    the training dropbacks is the overall rate exactly."""
    d = _drops().filter(~((pl.col("down") == 1) & (pl.col("ydstogo") == 5)))
    off = pack_sack_offsets(d, edges=[2, 6, 10], min_events=30)
    base = _logit(220 / 3200)
    grp = np.minimum(d["down"].to_numpy().astype(int), 3) - 1
    b = np.searchsorted([2, 6, 10], d["ydstogo"].to_numpy(), side="left")
    p = 1 / (1 + np.exp(-(base + off[grp, b])))
    assert float(p.mean()) == pytest.approx(220 / 3200, abs=1e-12)


def test_engine_sack_offsets() -> None:
    from ge.models.sim.engine import simulate

    lg = replace(synthetic_league(), sack_situation_logit=np.array([[-30.0] * 4, [-30.0] * 4,
                                                                    [0.0] * 4]))  # fmt: skip
    t = simulate(synthetic_game(), lg, 2000, game_id="G_SACK", model_version="m1").team
    t = t.astype(np.int64).sum(axis=(0, 1))
    for d in (0, 1):
        assert t[A.R_EARLY_N0 + d * A.EARLY_KINDS + A.E_SACK] == 0
    assert t[A.R_SACK_YDS] > 0  # sacks still happen on 3rd and 4th down


@pytest.mark.realdata
def test_replay_2024_run_yards_by_down_with_the_s2024_table() -> None:
    """2024 G7 designed runs keep their cell and yardline: 1st/2nd down use the (run cell,
    situation) category the engine uses (ruling 2026-11-03; R-2, approved by Rhys 2026-11-12),
    3rd/4th with more than 2 to go the late-down category, short yardage left out; yards drawn
    from the S2024 table, clipped once at the goal line. Mean within 0.20 of actual on 1st and
    2nd down, 0.75 on 3rd/4th (ruling 2026-10-30)."""
    from ge.config import ActiveParams, load_params, use_params
    from ge.ingest.raw import DATA_ROOT, read_latest
    from ge.metrics import plays as pf
    from ge.models.sim.backtest import load_window_league

    try:
        pbp = read_latest(DATA_ROOT, "pbp", 2024)
    except FileNotFoundError as exc:
        pytest.fail(f"realdata test needs the local store: {exc}")
    with use_params(ActiveParams(load_params(), None)):
        runs = pbp.filter(pf.scrimmage() & ~pf.garbage()).filter(pf.designed_run())
        runs = runs.with_columns(pf.run_cell().alias("cell"))
    late = (pl.col("down") >= 3) & (pl.col("ydstogo") > 2)
    runs = runs.filter(~((pl.col("down") >= 3) & (pl.col("ydstogo") <= 2)))
    idx_map = {c: i for i, c in enumerate(pf.RUN_CELLS)}
    cell = runs["cell"].replace_strict(idx_map, return_dtype=pl.Int64).to_numpy()
    sit = situation_cell(runs["down"].to_numpy(), runs["ydstogo"].to_numpy(),
                         load_sim().situation_yards.distance_upper.value)  # fmt: skip
    is_late = runs.select(late).to_series().to_numpy()
    cat = np.where(is_late, LATE_DOWN, RUN_SIT0 + cell * SIT_CELLS + sit)
    t = load_window_league(2024).run_yards
    src = t.source[cat]
    yl = runs["yardline_100"].to_numpy().astype(np.float64)
    rng = np.random.default_rng(20261030)
    sim = np.zeros((40, runs.height))
    for k in np.unique(src):
        m = src == k
        lo, hi = int(t.lo[k]), int(t.hi[k])
        i = np.minimum(lo + np.searchsorted(t.cum[lo:hi], rng.random((40, int(m.sum())))), hi - 1)
        sim[:, m] = np.minimum(t.values[i], yl[m])
    df = runs.with_columns(pl.Series("sim", sim.mean(axis=0)))
    for name, f, tol in (("1st", pl.col("down") == 1, 0.20), ("2nd", pl.col("down") == 2, 0.20),
                         ("3rd/4th", late, 0.75)):  # fmt: skip
        part = df.filter(f)
        diff = float(part["sim"].mean() - part["yards_gained"].mean())
        assert abs(diff) <= tol, (name, diff, part.height)


@pytest.mark.realdata
def test_2024_sack_rate_by_down_group_with_the_s2024_offsets() -> None:
    """S2024 window: expit(logit(league sack rate) + offset[cell]) averaged over 2024's G7
    dropbacks, by down group, within 0.010 of 2024's actual rate (ruling 2026-10-30)."""
    from ge.config import ActiveParams, load_params, use_params
    from ge.ingest.raw import DATA_ROOT, read_latest
    from ge.metrics import plays as pf
    from ge.models.sim.backtest import load_window_league

    try:
        pbp = read_latest(DATA_ROOT, "pbp", 2024)
    except FileNotFoundError as exc:
        pytest.fail(f"realdata test needs the local store: {exc}")
    with use_params(ActiveParams(load_params(), None)):
        drop = pbp.filter(pf.scrimmage() & ~pf.garbage()).filter(pl.col("qb_dropback") == 1)
    lg = load_window_league(2024)
    edges = load_sim().sacks.distance_upper.value
    grp = np.minimum(drop["down"].to_numpy().astype(int), 3) - 1
    b = np.searchsorted(edges, drop["ydstogo"].to_numpy(), side="left")
    p = 1 / (1 + np.exp(-(_logit(lg.sack_rate) + lg.sack_situation_logit[grp, b])))
    sacked = (drop["sack"] == 1).fill_null(False).to_numpy()
    for g, name in enumerate(("1st", "2nd", "3rd/4th")):
        m = grp == g
        diff = float(p[m].mean() - sacked[m].mean())
        assert abs(diff) <= 0.010, (name, diff, int(m.sum()))
