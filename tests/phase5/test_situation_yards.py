"""PRJ-02 run yards and YAC by down and distance (ruling 2026-11-03, P6). Situation cells for
1st and 2nd down: down x distance bin (config/sim.yaml situation_yards.distance_upper, inclusive
upper edges). 1st/2nd-down designed runs draw from the (run cell, situation) category, parent
the run cell; 3rd/4th downs keep short yardage and late down; goal-line censored. YAC by
situation was removed (ruling 2026-11-12): YAC draws from the band. Synthetic placeholder data
only."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import polars as pl
import pytest

from ge.metrics import plays as pf
from ge.models.sim import arrays as A
from ge.models.sim.league import (
    BAND_COUNT,
    LATE_DOWN,
    RUN_CATEGORIES,
    RUN_CELL_COUNT,
    RUN_SIT0,
    SIT_CELLS,
    SIT_DIST_BINS,
    pack_categories,
    pack_runs,
    pack_yac,
    situation_cell,
)
from ge.models.sim.settings import load_sim
from tests.phase5.sim_synth import synthetic_game, synthetic_league

EDGES = [2, 6, 10]


def _masses(p, k: int) -> dict[float, float]:  # type: ignore[no-untyped-def]
    lo, hi = int(p.lo[k]), int(p.hi[k])
    prev = np.concatenate([[0.0], p.cum[lo:hi][:-1]])
    out: dict[float, float] = {}
    for v, m in zip(p.values[lo:hi], p.cum[lo:hi] - prev, strict=True):
        if m > 0:
            out[float(v)] = out.get(float(v), 0.0) + float(m)
    return out


def test_settings_and_layout() -> None:
    s = load_sim().situation_yards.distance_upper
    assert s.value == EDGES and s.spec_id == "PRJ-02" and s.status == "initial"
    assert (SIT_DIST_BINS, SIT_CELLS) == (4, 8)
    assert RUN_SIT0 == LATE_DOWN + 1 == 11
    assert RUN_CATEGORIES == RUN_SIT0 + RUN_CELL_COUNT * SIT_CELLS == 75


def test_situation_cell_downs_one_and_two_only() -> None:
    down = np.array([1, 1, 1, 2, 2, 2, 3, 4])
    togo = np.array([10, 11, 2, 2, 7, 5, 5, 1])
    assert situation_cell(down, togo, EDGES).tolist() == [2, 3, 0, 4, 6, 5, -1, -1]


def test_engine_situation_cell_matches() -> None:
    from ge.models.sim.engine import sit_cell

    e = np.array([2.0, 6.0, 10.0])
    for d, t in ((1, 10.0), (1, 11.0), (1, 2.0), (2, 2.0), (2, 7.0), (2, 5.0), (3, 5.0), (4, 1.0)):
        assert sit_cell(d, t, e) == int(situation_cell(np.array([d]), np.array([t]), EDGES)[0])


def _runs(td_third: bool = False) -> pl.DataFrame:
    """Every run cell: two 1st & 10 runs at the 50 for 4. Middle cell also: 1st & 10 at the 50
    for 0 and 9; 2nd & 6 at the 40 for 3; 2nd & 1 at the 3 for 2 (a TD when td_third); 3rd & 5
    at the 30 for 7. Unit weights."""
    rows = [(c, 4.0, 1.0, 10.0, 50.0, False) for c in pf.RUN_CELLS for _ in range(2)]
    rows += [("middle", 0.0, 1.0, 10.0, 50.0, False), ("middle", 9.0, 1.0, 10.0, 50.0, False),
             ("middle", 3.0, 2.0, 6.0, 40.0, False), ("middle", 2.0, 2.0, 1.0, 3.0, td_third),
             ("middle", 7.0, 3.0, 5.0, 30.0, False)]  # fmt: skip
    return pl.DataFrame(
        {
            "cell": [r[0] for r in rows],
            "yards_gained": [r[1] for r in rows],
            "down": [r[2] for r in rows],
            "ydstogo": [r[3] for r in rows],
            "yardline_100": [r[4] for r in rows],
            "touchdown": [1.0 if r[5] else 0.0 for r in rows],
            "td_team": ["A" if r[5] else None for r in rows],
            "posteam": ["A"] * len(rows),
            "w": [1.0] * len(rows),
        },
        schema_overrides={"td_team": pl.String},
    )


MID = list(pf.RUN_CELLS).index("middle")


def _run_cat(cell: int, sit: int) -> int:
    return RUN_SIT0 + cell * SIT_CELLS + sit


def test_pack_runs_situation_categories() -> None:
    p = pack_runs(_runs(), min_events=1)
    assert len(p.lo) == RUN_CATEGORIES
    assert _masses(p, _run_cat(MID, 2)) == pytest.approx({0.0: 1 / 4, 4.0: 1 / 2, 9.0: 1 / 4})
    assert _masses(p, _run_cat(MID, 5)) == pytest.approx({3.0: 1.0})  # 2nd & 3-6
    assert _masses(p, _run_cat(MID, 4)) == pytest.approx({2.0: 1.0})  # 2nd & 1-2
    assert _masses(p, _run_cat(0, 2)) == pytest.approx({4.0: 1.0})
    # the middle cell still holds every middle run, 3rd down included
    assert _masses(p, MID) == pytest.approx(
        {0.0: 1 / 7, 2.0: 1 / 7, 3.0: 1 / 7, 4.0: 2 / 7, 7.0: 1 / 7, 9.0: 1 / 7}
    )
    # no 3rd/4th-down run is in a situation category
    assert int(p.n[RUN_SIT0:].sum()) == 2 * len(pf.RUN_CELLS) + 4


def test_pack_runs_situation_categories_are_censored_and_fall_back_to_the_cell() -> None:
    p = pack_runs(_runs(td_third=True), min_events=1)
    assert 2.0 not in _masses(p, MID)  # the 2-yard TD run is censored in its cell ...
    # ... and alone in its situation, so the largest value is an event (Efron)
    assert _masses(p, _run_cat(MID, 4)) == pytest.approx({2.0: 1.0})
    q = pack_runs(_runs(), min_events=2)
    assert q.source[_run_cat(MID, 5)] == MID  # one 2nd & 3-6 run: the middle cell's table
    assert (q.lo[_run_cat(MID, 5)], q.hi[_run_cat(MID, 5)]) == (q.lo[MID], q.hi[MID])
    assert q.source[_run_cat(MID, 2)] == _run_cat(MID, 2)  # four 1st & 7-10 runs: its own


def test_a_thin_cell_sends_its_situations_to_every_run() -> None:
    # only the middle cell has 3+ runs: every other cell, and its situations, use every run
    q = pack_runs(_runs(), min_events=3)
    assert q.source[0] == RUN_CELL_COUNT
    assert q.source[_run_cat(0, 2)] == RUN_CELL_COUNT
    assert q.source[_run_cat(MID, 2)] == _run_cat(MID, 2)
    assert q.source[_run_cat(MID, 5)] == MID


def test_pack_runs_keeps_the_existing_categories() -> None:
    p = pack_runs(_runs(), min_events=1)
    assert _masses(p, RUN_CELL_COUNT) == pytest.approx(
        {0.0: 1 / 21, 2.0: 1 / 21, 3.0: 1 / 21, 4.0: 16 / 21, 7.0: 1 / 21, 9.0: 1 / 21}
    )
    assert _masses(p, LATE_DOWN) == pytest.approx({7.0: 1.0})  # 3rd & 5
    assert p.n[RUN_CELL_COUNT + 1] == 0  # no short-yardage run (2nd & 1 is not a 3rd/4th down)


def _comp() -> pl.DataFrame:
    """Completions (down, ydstogo, band, yac): short on 1st & 10 for 2, 6, 10; short on 3rd & 8
    for 1; intermediate on 1st & 10 for 5 (a TD) and on 2nd & 5 for 3; behind on 2nd & 5 for 4
    twice; deep on 2nd & 5 for 8 twice. Unit weights."""
    rows = [(1, 10, 1, 2.0, False), (1, 10, 1, 6.0, False), (1, 10, 1, 10.0, False),
            (3, 8, 1, 1.0, False), (1, 10, 2, 5.0, True), (2, 5, 2, 3.0, False),
            (2, 5, 0, 4.0, False), (2, 5, 0, 4.0, False), (2, 5, 3, 8.0, False),
            (2, 5, 3, 8.0, False)]  # fmt: skip
    return pl.DataFrame(
        {
            "down": [float(r[0]) for r in rows],
            "ydstogo": [float(r[1]) for r in rows],
            "band": [r[2] for r in rows],
            "yards_after_catch": [r[3] for r in rows],
            "touchdown": [1 if r[4] else 0 for r in rows],
            "td_team": ["AAA" if r[4] else None for r in rows],
            "posteam": ["AAA"] * len(rows),
            "w": [1.0] * len(rows),
        },
        schema_overrides={"td_team": pl.String},
    )


def test_pack_yac_has_no_situation_categories() -> None:
    """Ruling 2026-11-12: YAC by situation removed; the bands and every completion only."""
    p = pack_yac(_comp(), min_events=1)
    assert len(p.lo) == BAND_COUNT + 1
    assert _masses(p, 1) == pytest.approx({1.0: 0.25, 2.0: 0.25, 6.0: 0.25, 10.0: 0.25})
    assert p.n.tolist() == [2, 4, 2, 2, 10]


def test_yac_switch_is_gone() -> None:
    assert "yac_by_situation" not in type(load_sim().situation_yards).model_fields


def _run_league(first: float, second: float):  # type: ignore[no-untyped-def]
    """Cells, every run, short yardage and late down gain 2-25; every 1st-down situation
    category gains `first`, every 2nd-down one `second`."""
    run = [2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 12.0, 25.0]
    cats: list[list[float]] = [run] * RUN_SIT0
    for _c in range(RUN_CELL_COUNT):
        cats += [[first]] * SIT_DIST_BINS + [[second]] * SIT_DIST_BINS
    rows = [(k, v, 1.0) for k, vals in enumerate(cats) for v in vals]
    df = pl.DataFrame(rows, schema=["cat", "value", "w"], orient="row")
    pk = pack_categories(df, n_categories=len(cats), parent=list(range(len(cats))), min_events=1)
    return replace(synthetic_league(), run_yards=pk)


def _team(league, n=2000):  # type: ignore[no-untyped-def]
    from ge.models.sim.engine import simulate

    r = simulate(synthetic_game(), league, n, game_id="G_SIT", model_version="m1")
    return r.team.astype(np.int64).sum(axis=(0, 1))


def test_engine_draws_early_down_runs_from_their_situation() -> None:
    t = _team(_run_league(33.0, -1.0))
    k1, k2 = A.E_RUN, A.EARLY_KINDS + A.E_RUN
    n1, y1 = t[A.R_EARLY_N0 + k1], t[A.R_EARLY_YDS0 + k1]
    n2, y2 = t[A.R_EARLY_N0 + k2], t[A.R_EARLY_YDS0 + k2]
    assert n1 > 0 and n2 > 0
    assert y2 == -n2  # every 2nd-down run loses 1 (its situation category)
    assert n1 <= y1 <= 33 * n1  # 33 or the goal line
    assert y1 > 20 * n1
    run_att, run_conv = A.R_THIRD_ATT_RUN0, A.R_THIRD_CONV_RUN0
    assert t[run_att : run_att + 6].sum() > 0
    assert t[run_conv : run_conv + 6].sum() > 0  # 3rd-down runs keep their 2-25 tables


def test_engine_draws_yac_from_the_band() -> None:
    """Ruling 2026-11-12: every band 3.0, every completion 0.0 -> 30 tenths per completion."""
    cats = [[3.0]] * BAND_COUNT + [[0.0]]
    rows = [(k, v, 1.0) for k, vals in enumerate(cats) for v in vals]
    df = pl.DataFrame(rows, schema=["cat", "value", "w"], orient="row")
    yac = pack_categories(df, n_categories=len(cats), parent=list(range(len(cats))), min_events=1)
    t = _team(replace(synthetic_league(), yac=yac), 500)
    comp = t[A.R_CMP_B0 : A.R_CMP_B0 + 4].sum()
    assert comp > 0
    assert t[A.R_YAC_CMP_B0 : A.R_YAC_CMP_B0 + 4].sum() == 30 * comp  # tenths of a yard


def test_engine_refuses_the_old_run_table_and_the_situation_yac_table() -> None:
    from ge.models.sim.engine import simulate
    from tests.phase5.sim_synth import _packed

    lg = synthetic_league()
    with pytest.raises(ValueError, match="run table has no situation"):
        simulate(synthetic_game(), replace(lg, run_yards=_packed([[1.0, 3.0]] * 11)), 5,
                 game_id="G_OLD", model_version="m1")  # fmt: skip
    with pytest.raises(ValueError, match="YAC table has situation categories"):
        simulate(synthetic_game(), replace(lg, yac=_packed([[0.0, 3.0]] * (5 + 48))), 5,
                 game_id="G_OLD", model_version="m1")  # fmt: skip
