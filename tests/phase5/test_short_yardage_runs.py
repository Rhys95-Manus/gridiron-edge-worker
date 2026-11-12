"""PRJ-02 short-yardage runs (ruling 2026-10-29, P2): a designed run on 3rd or 4th down with 2
yards or fewer to go draws its yards from a league short-yardage category (training runs in
that situation, not goal-to-go, every cell pooled; parent: every designed run) instead of the
carrier's cell. Synthetic placeholder plays; the last test replays 2024 short-yardage runs
(realdata)."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from ge.models.sim import arrays as A
from ge.models.sim.league import RUN_CATEGORIES, RUN_CELL_COUNT, SHORT_YARDAGE, pack_runs
from ge.models.sim.settings import load_sim
from tests.phase5.sim_synth import _packed, _run_packed, synthetic_game, synthetic_league


def _masses(p, k: int) -> dict[float, float]:  # type: ignore[no-untyped-def]
    lo, hi = int(p.lo[k]), int(p.hi[k])
    prev = np.concatenate([[0.0], p.cum[lo:hi][:-1]])
    out: dict[float, float] = {}
    for v, m in zip(p.values[lo:hi], p.cum[lo:hi] - prev, strict=True):
        out[float(v)] = out.get(float(v), 0.0) + float(m)
    return out


def test_short_yardage_settings_come_from_config() -> None:
    s = load_sim().short_yardage
    assert s.downs.value == [3, 4]
    assert s.max_togo.value == 2


def _runs() -> pl.DataFrame:
    """3rd & 1 at the 50 for 0; 4th & 2 at the 40 for 3 (weight 3); 3rd & 1 goal-to-go at the 1
    for 1 (excluded: the field ends the play); 2nd & 1 at the 60 for 5 (excluded: down);
    3rd & 3 at the 30 for 7 (excluded: distance)."""
    return pl.DataFrame({
        "cell": ["middle", "left_guard", "middle", "right_end", "left_end"],
        "yards_gained": [0.0, 3.0, 1.0, 5.0, 7.0],
        "down": [3.0, 4.0, 3.0, 2.0, 3.0],
        "ydstogo": [1.0, 2.0, 1.0, 1.0, 3.0],
        "yardline_100": [50.0, 40.0, 1.0, 60.0, 30.0],
        "touchdown": [0.0] * 5,  # no TD runs: nothing censored (ruling 2026-10-30)
        "td_team": [None] * 5,
        "posteam": ["A"] * 5,
        "w": [1.0, 3.0, 1.0, 1.0, 1.0],
    })  # fmt: skip


def test_pack_runs_short_yardage_category() -> None:
    p = pack_runs(_runs(), min_events=1)
    assert SHORT_YARDAGE == RUN_CELL_COUNT + 1 == 9
    assert len(p.lo) == RUN_CATEGORIES  # + late down, situations (rulings 2026-10-30, 11-03)
    assert _masses(p, SHORT_YARDAGE) == pytest.approx({0.0: 0.25, 3.0: 0.75})
    assert p.n[SHORT_YARDAGE] == 2
    assert p.n[RUN_CELL_COUNT] == 5  # every designed run, short yardage included
    assert p.source[SHORT_YARDAGE] == SHORT_YARDAGE


def test_short_yardage_falls_back_to_every_run() -> None:
    p = pack_runs(_runs(), min_events=3)
    assert p.source[SHORT_YARDAGE] == RUN_CELL_COUNT


def _zero_short_yardage_league():  # type: ignore[no-untyped-def]
    """Every cell gains 2-25 yards; the short-yardage category always gains 0; the late-down
    category (ruling 2026-10-30) gains 2-25 like the cells."""
    from dataclasses import replace

    run = [2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 12.0, 25.0]
    return replace(synthetic_league(), run_yards=_run_packed([run] * 9 + [[0.0]] + [run]))


def test_third_and_fourth_and_short_runs_use_the_short_yardage_category() -> None:
    from ge.models.sim.engine import simulate

    r = simulate(synthetic_game(), _zero_short_yardage_league(), 3000, game_id="G_SY",
                 model_version="m1")  # fmt: skip
    t = r.team.astype(np.int64).sum(axis=(0, 1))
    assert t[A.R_THIRD_ATT_RUN0] > 0 and t[A.R_THIRD_ATT_RUN0 + 1] > 0
    assert t[A.R_THIRD_CONV_RUN0] == 0 and t[A.R_THIRD_CONV_RUN0 + 1] == 0  # 3rd & 1, 3rd & 2
    assert t[A.R_THIRD_CONV_RUN0 + 2] > 0  # 3rd & 3 still draws from its cell (>= 2 yards)


def test_tables_without_the_category_are_refused() -> None:
    from dataclasses import replace

    from ge.models.sim.engine import simulate

    old = replace(synthetic_league(), run_yards=_packed([[1.0, 3.0]] * 9))
    with pytest.raises(ValueError, match="short-yardage"):
        simulate(synthetic_game(), old, 10, game_id="G_OLD", model_version="m1")


@pytest.mark.realdata
def test_replay_2024_short_yardage_runs_with_the_s2024_table() -> None:
    """2024 G7 designed runs on 3rd or 4th down with 2 yards or fewer to go keep their distance
    and yardline; yards are drawn from the S2024 short-yardage category, clipped at the goal
    line once. P(gain >= ydstogo) within 0.04 of the actual conversion (ruling 2026-10-29)."""
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
    runs = runs.filter(pl.col("down").is_in([3, 4]) & (pl.col("ydstogo") <= 2))
    conv = ((pl.col("first_down") == 1) | (pl.col("touchdown") == 1)).fill_null(False)
    actual = float(runs.select(conv.mean()).item())
    t = load_window_league(2024).run_yards
    lo, hi = int(t.lo[SHORT_YARDAGE]), int(t.hi[SHORT_YARDAGE])
    rng = np.random.default_rng(20261029)
    u = rng.random((50, runs.height))
    idx = np.minimum(lo + np.searchsorted(t.cum[lo:hi], u), hi - 1)
    yl = runs["yardline_100"].to_numpy().astype(np.float64)
    gain = np.minimum(t.values[idx], yl)
    sim = float((gain >= runs["ydstogo"].to_numpy()).mean())
    assert abs(sim - actual) <= 0.04, (sim, actual, runs.height)
