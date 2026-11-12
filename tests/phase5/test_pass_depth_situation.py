"""PRJ-02 pass depth by down and distance (ruling 2026-11-02): 12 situation cells (down group
1st / 2nd / 3rd-4th x distance bins from config/sim.yaml pass_depth.distance_upper). The depth
band probability is the log5 result times exp(ln(cell share / overall share)), renormalised; a
(cell, band) with fewer than min_category_events attempts has no shift. Air yards are drawn from
the (band, cell) table, whose parent is the band's all-situation table. Synthetic placeholder
data only."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import polars as pl
import pytest

from ge.models.sim import arrays as A
from ge.models.sim.league import (
    AIR_CELL0,
    BAND_COUNT,
    PD_CELLS,
    PD_DIST_BINS,
    PD_DOWN_GROUPS,
    depth_cell,
    pack_air,
    pack_depth_offsets,
)
from ge.models.sim.settings import load_sim
from tests.phase5.sim_synth import _packed, synthetic_game, synthetic_league

EDGES = [2, 6, 10]


def test_settings_and_layout() -> None:
    s = load_sim().pass_depth.distance_upper
    assert s.value == EDGES and s.spec_id == "PRJ-02"
    assert (PD_DOWN_GROUPS, PD_DIST_BINS, PD_CELLS) == (3, 4, 12)
    assert AIR_CELL0 == BAND_COUNT + 1


def test_depth_cell_uses_inclusive_upper_edges() -> None:
    down = np.array([1, 1, 2, 3, 3, 4, 4])
    togo = np.array([10, 11, 2, 7, 6, 1, 15])
    assert depth_cell(down, togo, EDGES).tolist() == [2, 3, 4, 10, 9, 8, 11]


def test_engine_depth_cell_matches() -> None:
    from ge.models.sim.engine import pd_cell

    e = np.array([2.0, 6.0, 10.0])
    for d, t in ((1, 10.0), (1, 11.0), (2, 2.0), (3, 7.0), (3, 6.0), (4, 1.0), (4, 15.0)):
        assert pd_cell(d, t, e) == int(depth_cell(np.array([d]), np.array([t]), EDGES)[0])


def _att(rows: list[tuple[int, int, float, int]]) -> pl.DataFrame:
    """rows: (down, ydstogo, air_yards, count), weight 1 each."""
    out = [(d, t, a, 1.0) for d, t, a, n in rows for _ in range(n)]
    return pl.DataFrame(out, schema=["down", "ydstogo", "air_yards", "w"], orient="row")


def _band(air: float) -> int:
    return 0 if air < 0 else (1 if air < 10 else (2 if air < 20 else 3))


def test_offsets_are_log_share_ratios_and_thin_pairs_get_none() -> None:
    # 1st & 10: 90 short, 30 intermediate; 3rd & 8: 30 short, 30 intermediate (synthetic)
    att = _att([(1, 10, 5.0, 90), (1, 10, 12.0, 30), (3, 8, 5.0, 30), (3, 8, 12.0, 30)])
    att = att.with_columns(
        pl.col("air_yards").map_elements(_band, return_dtype=pl.Int64).alias("band")
    )
    off = pack_depth_offsets(att, edges=EDGES, min_events=30)
    assert off.shape == (PD_DOWN_GROUPS, PD_DIST_BINS, BAND_COUNT)
    overall = np.array([0.0, 120 / 180, 60 / 180, 0.0])
    assert off[2, 2, 1] == pytest.approx(np.log(0.5 / overall[1]))
    assert off[2, 2, 2] == pytest.approx(np.log(0.5 / overall[2]))
    assert off[0, 2, 1] == pytest.approx(np.log(0.75 / overall[1]))
    assert off[0, 2, 2] == pytest.approx(np.log(0.25 / overall[2]))  # 30 = the minimum: shifted
    assert off[2, 2, 0] == 0.0 and off[2, 2, 3] == 0.0  # no attempts: no shift
    assert (off[1] == 0.0).all()  # no 2nd-down attempts


def test_air_table_keeps_band_categories_and_falls_back_by_band() -> None:
    att = _att([(1, 10, -2.0, 40), (1, 10, 5.0, 40), (1, 10, 12.0, 40), (1, 10, 25.0, 40),
                (3, 8, 7.0, 40), (3, 8, 15.0, 5)])  # fmt: skip
    att = att.with_columns(
        pl.col("air_yards").map_elements(_band, return_dtype=pl.Int64).alias("band")
    )
    pk = pack_air(att, edges=EDGES, min_events=30)
    assert len(pk.lo) == AIR_CELL0 + BAND_COUNT * PD_CELLS
    short_all = pk.values[pk.lo[1] : pk.hi[1]]
    assert sorted(short_all.tolist()) == [5.0] * 40 + [7.0] * 40
    c = AIR_CELL0 + 1 * PD_CELLS + 10  # short band, 3rd & 7-10
    assert pk.values[pk.lo[c] : pk.hi[c]].tolist() == [7.0] * 40
    thin = AIR_CELL0 + 2 * PD_CELLS + 10  # intermediate, 3rd & 7-10: 5 attempts
    assert pk.source[thin] == 2
    assert (pk.lo[thin], pk.hi[thin]) == (pk.lo[2], pk.hi[2])


def _air(per_cat: dict[int, list[float]], band_vals: list[list[float]]):  # type: ignore[no-untyped-def]
    """A 53-category air table: bands, all attempts, then (band, cell) categories."""
    cats = [*band_vals, [v for b in band_vals for v in b]]
    cats += [per_cat.get(AIR_CELL0 + k, []) for k in range(BAND_COUNT * PD_CELLS)]
    rows = [(k, float(v), 1.0) for k, vals in enumerate(cats) for v in vals]
    df = pl.DataFrame(rows, schema=["cat", "value", "w"], orient="row")
    from ge.models.sim.league import pack_categories

    parent = [BAND_COUNT] * AIR_CELL0 + [k // PD_CELLS for k in range(BAND_COUNT * PD_CELLS)]
    return pack_categories(df, n_categories=len(cats), parent=parent, min_events=1)


def _sim(league, n=400):  # type: ignore[no-untyped-def]
    from ge.models.sim.engine import simulate

    return simulate(synthetic_game(), league, n, game_id="G_PD", model_version="m1").team.astype(
        np.int64
    )


def test_engine_band_offsets_shift_every_cell() -> None:
    off = np.zeros((PD_DOWN_GROUPS, PD_DIST_BINS, BAND_COUNT))
    off[..., 3] = 50.0  # deep in every situation (test setting)
    t = _sim(replace(synthetic_league(), pass_depth_offset=off))
    att = t[..., A.R_ATT_B0 : A.R_ATT_B0 + 4]
    assert att.sum() > 0
    assert att[..., :3].sum() == 0


def test_engine_draws_air_from_the_cell_table() -> None:
    lg = synthetic_league()
    band_vals = [[-4.0, -2.0], [2.0, 5.0, 8.0], [11.0, 14.0, 18.0], [22.0]]
    cells = {AIR_CELL0 + 3 * PD_CELLS + c: [33.0] for c in range(PD_CELLS)}  # deep: 33 everywhere
    off = np.zeros((PD_DOWN_GROUPS, PD_DIST_BINS, BAND_COUNT))
    off[..., 3] = 50.0
    t = _sim(replace(lg, air_yards=_air(cells, band_vals), pass_depth_offset=off))
    n = t[..., A.R_ATT_B0 + 3].sum()
    caps = t[..., A.R_AIR_CAPS].sum()
    air10 = t[..., A.R_AIR_ATT_B0 + 3].sum()  # tenths of a yard
    assert 0 < caps < n
    # every deep attempt draws 33 from its cell table (the band table has only 22); attempts
    # near the goal line are capped below 33
    assert 330 * (n - caps) <= air10 < 330 * n


def test_engine_refuses_the_old_air_table() -> None:
    lg = synthetic_league()
    air = [[-4.0, -2.0], [2.0, 5.0, 8.0], [11.0, 14.0, 18.0], [22.0, 30.0, 40.0]]
    old = replace(lg, air_yards=_packed([*air, [v for b in air for v in b]]))
    with pytest.raises(ValueError, match="PRJ-02"):
        _sim(old, 5)
