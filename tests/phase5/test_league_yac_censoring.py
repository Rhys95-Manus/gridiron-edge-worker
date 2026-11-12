"""PRJ-02 league level, YAC table (ruling 2026-10-29, P1): a weighted Kaplan-Meier estimate per
depth band, a completion the offense scored on right-censored at its distance to the goal line
from the catch point, the largest value treated as an event (Efron). Synthetic placeholder plays;
the hand-worked masses are written out in each test. The last test replays real 2024
completions (realdata)."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from ge.models.sim.league import Packed, offense_scored, pack_categories, pack_yac


def _masses(p: Packed, k: int = 0) -> dict[float, float]:
    """Category k's draw distribution as {value: probability} (ties summed)."""
    lo, hi = int(p.lo[k]), int(p.hi[k])
    prev = np.concatenate([[0.0], p.cum[lo:hi][:-1]])
    out: dict[float, float] = {}
    for v, m in zip(p.values[lo:hi], p.cum[lo:hi] - prev, strict=True):
        out[float(v)] = out.get(float(v), 0.0) + float(m)
    return {v: m for v, m in out.items() if m > 0}


def _frame(values: list[float], censored: list[bool], w: list[float] | None = None) -> pl.DataFrame:
    n = len(values)
    return pl.DataFrame(
        {"cat": [0] * n, "value": values, "censored": censored, "w": w or [1.0] * n}
    )


def _pack(df: pl.DataFrame) -> Packed:
    return pack_categories(df, n_categories=1, parent=[0], min_events=1)


def test_no_censoring_is_the_weighted_empirical_distribution() -> None:
    """With no censored play the table is the one pack_categories builds today."""
    vals, w = [4.0, 1.0, 9.0, 1.0, 6.0], [1.0, 2.0, 0.5, 1.5, 3.0]
    plain = _pack(pl.DataFrame({"cat": [0] * 5, "value": vals, "w": w}))
    km = _pack(_frame(vals, [False] * 5, w))
    assert km.values.tolist() == plain.values.tolist()
    assert km.cum.tolist() == pytest.approx(plain.cum.tolist(), abs=1e-12)
    assert km.cum[-1] == 1.0
    assert km.n.tolist() == plain.n.tolist() == [5]


def test_hand_worked_kaplan_meier() -> None:
    """Values 1, 2c, 3, 3c, 5, 8c (c = censored), unit weights; 8c is the largest, so it is an
    event (Efron).
    1: at risk 6, 1 event -> mass 1/6, S = 5/6
    2c: no event -> S = 5/6
    3: at risk 4 (3, 3c, 5, 8), 1 event -> mass 5/6 * 1/4 = 5/24, S = 5/8
    5: at risk 2, 1 event -> mass 5/8 * 1/2 = 5/16, S = 5/16
    8: at risk 1, 1 event -> mass 5/16, S = 0. Masses sum to 48/48."""
    p = _pack(_frame([1.0, 2.0, 3.0, 3.0, 5.0, 8.0], [False, True, False, True, False, True]))
    got = _masses(p)
    assert sorted(got) == [1.0, 3.0, 5.0, 8.0]
    assert got[1.0] == pytest.approx(1 / 6, abs=1e-12)
    assert got[3.0] == pytest.approx(5 / 24, abs=1e-12)
    assert got[5.0] == pytest.approx(5 / 16, abs=1e-12)
    assert got[8.0] == pytest.approx(5 / 16, abs=1e-12)
    assert p.cum[p.hi[0] - 1] == 1.0
    assert p.n.tolist() == [6]  # plays, censored ones included


def test_weights_act_like_duplicated_rows() -> None:
    vals = [2.0, 4.0, 4.0, 7.0, 10.0]
    cens = [False, True, False, True, False]
    w = [2.0, 1.0, 3.0, 2.0, 1.0]
    weighted = _masses(_pack(_frame(vals, cens, w)))
    dup_v = [v for v, k in zip(vals, w, strict=True) for _ in range(int(k))]
    dup_c = [c for c, k in zip(cens, w, strict=True) for _ in range(int(k))]
    dup = _masses(_pack(_frame(dup_v, dup_c)))
    assert weighted.keys() == dup.keys()
    for v in weighted:
        assert weighted[v] == pytest.approx(dup[v], abs=1e-12)


def test_at_a_tie_the_event_counts_before_the_censoring() -> None:
    """3 and 3c tie: the censored play is still at risk at 3, so 3's hazard is 1/2 (at risk 3, 3c)
    and not 1/1. Values 3, 3c, 9: mass at 3 = 1/3; 9 (the largest, an event) gets 2/3."""
    got = _masses(_pack(_frame([3.0, 3.0, 9.0], [False, True, False])))
    assert got[3.0] == pytest.approx(1 / 3, abs=1e-12)
    assert got[9.0] == pytest.approx(2 / 3, abs=1e-12)


def test_largest_censored_value_keeps_the_remaining_mass() -> None:
    """Values 1, 6c: 1 has mass 1/2; without Efron the other 1/2 would be lost. It sits at 6."""
    p = _pack(_frame([1.0, 6.0], [False, True]))
    assert _masses(p) == pytest.approx({1.0: 0.5, 6.0: 0.5})
    assert p.cum[p.hi[0] - 1] == 1.0


def test_only_offensive_touchdowns_are_censored() -> None:
    df = pl.DataFrame(
        {
            "posteam": ["AAA", "AAA", "AAA", "AAA"],
            "defteam": ["BBB", "BBB", "BBB", "BBB"],
            "touchdown": [1, 1, 0, None],
            "td_team": ["AAA", "BBB", None, None],
        },
        schema_overrides={"td_team": pl.String},
    )
    got = df.select(offense_scored().alias("c"))["c"].to_list()
    assert got == [True, False, False, False]  # the defense's return TD is observed as recorded


def test_pack_yac_bands_and_all_completions() -> None:
    """Band 0: 2, 5c -> {2: 1/2, 5: 1/2}. Band 1: 4, 4c, 8 -> 4: 1/3; 8 gets 2/3. Bands 2, 3:
    too few plays, so they use category 4 (every completion): 2, 4, 4c, 5c, 8 ->
    2: at risk 5 -> 1/5, S 4/5; 4: at risk 4 -> 4/5 * 1/4 = 1/5, S 3/5; 5c; 8: 3/5."""
    comp = pl.DataFrame(
        {
            "down": [1.0] * 5,
            "ydstogo": [10.0] * 5,
            "band": [0, 0, 1, 1, 1],
            "yards_after_catch": [2.0, 5.0, 4.0, 4.0, 8.0],
            "touchdown": [0, 1, 0, 1, 0],
            "td_team": [None, "AAA", None, "AAA", None],
            "posteam": ["AAA"] * 5,
            "w": [1.0] * 5,
        },
        schema_overrides={"td_team": pl.String},
    )
    p = pack_yac(comp, edges=[2, 6, 10], min_events=2)
    assert _masses(p, 0) == pytest.approx({2.0: 0.5, 5.0: 0.5})
    assert _masses(p, 1) == pytest.approx({4.0: 1 / 3, 8.0: 2 / 3})
    assert _masses(p, 4) == pytest.approx({2.0: 0.2, 4.0: 0.2, 8.0: 0.6})
    assert p.source[:5].tolist() == [0, 1, 4, 4, 4]
    assert p.n[:5].tolist() == [2, 3, 0, 0, 5]


def test_censored_estimate_recovers_the_true_mean() -> None:
    """YAC drawn from a known discrete distribution and cut at a random distance to the goal
    (half-yards, so a value never ties its cut). The Kaplan-Meier mean recovers the true mean
    within 0.05 yards (ruling 2026-10-29); the table that keeps the cut values is short."""
    rng = np.random.default_rng(20261029)
    support = np.array([-2.0, 0.0, 3.0, 8.0, 20.0, 45.0])
    prob = np.array([0.05, 0.25, 0.3, 0.25, 0.1, 0.05])
    true_mean = float(support @ prob)
    n = 200_000
    yac = rng.choice(support, p=prob, size=n)
    room = rng.integers(1, 80, size=n) + 0.5
    cens = yac >= room
    obs = np.where(cens, room, yac)
    km = _masses(_pack(_frame(obs.tolist(), cens.tolist())))
    km_mean = sum(v * m for v, m in km.items())
    assert km_mean == pytest.approx(true_mean, abs=0.05)
    assert float(obs.mean()) < true_mean - 0.05  # the bias the censoring removes


@pytest.mark.realdata
def test_replay_2024_completions_with_the_s2024_yac_table() -> None:
    """Out of sample: 2024 G7 completions keep their band, yardline and air yards; YAC is drawn
    from the S2024 window's table and the engine's goal-line clip applied once,
    min(air + yac, yardline_100). Mean yards per completion must be within 0.25 yards of actual
    for behind, short and intermediate and 0.75 for deep (ruling 2026-10-29)."""
    from ge.config import ActiveParams, load_params, use_params
    from ge.ingest.raw import DATA_ROOT, read_latest
    from ge.metrics import plays as pf
    from ge.models.sim.backtest import load_window_league

    tol = {"behind": 0.25, "short": 0.25, "intermediate": 0.25, "deep": 0.75}
    try:
        pbp = read_latest(DATA_ROOT, "pbp", 2024)
    except FileNotFoundError as exc:
        pytest.fail(f"realdata test needs the local store: {exc}")
    with use_params(ActiveParams(load_params(), None)):
        live = pbp.filter(pf.scrimmage() & ~pf.garbage())
        comp = live.filter(
            (pl.col("complete_pass") == 1)
            & (pl.col("sack") != 1)
            & pl.col("air_yards").is_not_null()
            & pl.col("yards_after_catch").is_not_null()
        ).with_columns(pf.depth_band().alias("band"))
    yac = load_window_league(2024).yac
    rng = np.random.default_rng(20261029)
    errors = {}
    for b, name in enumerate(pf.DEPTH_BANDS):
        c = comp.filter(pl.col("band") == name)
        air = c["air_yards"].to_numpy().astype(np.float64)
        yl = c["yardline_100"].to_numpy().astype(np.float64)
        lo, hi = int(yac.lo[b]), int(yac.hi[b])
        u = rng.random((50, len(air)))
        idx = np.minimum(lo + np.searchsorted(yac.cum[lo:hi], u), hi - 1)
        sim = np.minimum(air + yac.values[idx], yl).mean()
        errors[name] = float(sim - c["yards_gained"].mean())  # type: ignore[operator]
    assert all(abs(errors[k]) <= tol[k] for k in tol), errors
