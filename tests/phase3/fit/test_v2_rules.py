"""Phase 3e v2 method rulings (BT-02 method and decisions log, 2026-10-09), on synthetic data
with planted values (test settings, not real-world facts):

1. A stat with a slot or role prior is split-half tested on each player's residual from that
   prior (WOPR: half WOPR minus the team-target-weighted mean slot-prior WOPR).
2. A multi-cell stat is centred on each cell's league mean in the same season.
3. For a multi-cell stat, N (Fisher-z interval and inverse-variance weights) counts distinct
   entities, not entity-cells.
4. PRJ-06's QB pool is QBs with at least 50% of the team's dropbacks in the previous game."""

from __future__ import annotations

import numpy as np
import polars as pl

from ge.config import load_params
from ge.fit.availability import qb_starter_pool
from ge.fit.centering import center_season_cell, residual
from ge.fit.splithalf import SplitHalfConfig, half_values, k_from_halves, split_half_k
from ge.fit.whole import wopr_residual_value
from tests.phase3.fit.synth import rng

LEVEL = float(load_params().fitting.bt_02_no_signal_confidence.value)
CFG = SplitHalfConfig(m_grid=(25, 50, 100), splits=20, min_entities=30, confidence=LEVEL)
REL_TOL = 0.15
MIN_SHARE = float(load_params().projection.prj_06_qb_min_prev_dropback_share.value)


def _slot_units(*, tau: float, sigma: float, key: str) -> tuple[pl.DataFrame, float]:
    """Entities in three slots with far-apart slot means; within a slot the entity mean is
    slot mean + N(0, tau^2), plays N(entity mean, sigma^2): within-slot k = sigma^2/tau^2."""
    g = rng(key)
    slot_mean = {"S1": 0.0, "S2": 3.0, "S3": 6.0}
    ents, games, per = 1200, 20, 12
    slots = np.array(list(slot_mean))[g.integers(0, 3, ents)]
    mean = np.array([slot_mean[s] for s in slots]) + g.normal(0.0, tau, ents)
    n = games * per
    x = mean[:, None] + g.normal(0.0, sigma, (ents, n))
    df = pl.DataFrame(
        {
            "entity": np.repeat([f"e{i:05d}" for i in range(ents)], n),
            "game": np.tile(np.repeat([f"g{j:03d}" for j in range(games)], per), ents),
            "x": x.ravel(),
            "p": np.repeat([slot_mean[s] for s in slots], n),
        }
    ).with_columns(pl.lit(1.0).alias("d"), pl.lit(1.0).alias("c"))
    return df, sigma**2 / tau**2


def test_rule1_residual_recovers_within_slot_k() -> None:
    u, k = _slot_units(tau=0.3, sigma=0.3 * 60**0.5, key="slots")
    raw = split_half_k(u.drop("p"), CFG, "t/raw")
    res = split_half_k(residual(u), CFG, "t/res")
    assert raw.k is not None and raw.k < 0.5 * k  # league-centred k is far too small
    assert res.k is not None and abs(res.k - k) / k < REL_TOL, (res.k, k)


def _cell_units(*, tau: float, sigma: float, key: str) -> tuple[pl.DataFrame, float]:
    """Two seasons, four cells with far-apart base rates and a season drift common to every
    entity; entity-cell effects N(0, tau^2) independent across cells: k = sigma^2/tau^2."""
    g = rng(key)
    cell_mean = {"a": -2.0, "b": 0.0, "c": 2.0, "d": 4.0}
    drift = {2001: 0.0, 2002: 1.5}
    rows = []
    for season, dr in drift.items():
        for e in range(400):
            for cell, cm in cell_mean.items():
                mu = cm + dr + g.normal(0.0, tau)
                for j in range(16):
                    for v in g.normal(mu, sigma, 8):
                        rows.append((season, f"{season}|e{e:04d}", cell, f"g{j:02d}", float(v)))
    df = pl.DataFrame(
        rows,
        schema={
            "season": pl.Int64,
            "group": pl.Utf8,
            "cell": pl.Utf8,
            "game": pl.Utf8,
            "x": pl.Float64,
        },
        orient="row",
    ).with_columns(
        (pl.col("group") + "|" + pl.col("cell")).alias("entity"),
        pl.lit(1.0).alias("d"),
        pl.lit(1.0).alias("c"),
    )
    return df, sigma**2 / tau**2


def test_rule2_season_cell_centring_recovers_k() -> None:
    u, k = _cell_units(tau=0.25, sigma=0.25 * 50**0.5, key="cells")
    raw = split_half_k(u.select("entity", "game", "x", "d", "c"), CFG, "t/craw")
    cen = split_half_k(
        center_season_cell(u).select("entity", "game", "x", "d", "c", "group"), CFG, "t/cen"
    )
    assert raw.k is not None and raw.k < 0.2 * k  # cell and season gaps pass as signal
    assert cen.k is not None and abs(cen.k - k) / k < REL_TOL, (cen.k, k)


def test_centring_uses_each_seasons_own_cell_mean() -> None:
    u = pl.DataFrame(
        {
            "season": [1, 1, 2, 2],
            "cell": ["a", "a", "a", "a"],
            "x": [1.0, 3.0, 10.0, 30.0],
            "d": [1.0, 1.0, 1.0, 1.0],
        }
    )
    got = center_season_cell(u)["x"].to_list()
    assert got == [-1.0, 1.0, -10.0, 10.0]


def test_rule3_n_counts_distinct_entities() -> None:
    u, _ = _cell_units(tau=0.25, sigma=0.25 * 50**0.5, key="cells")
    cen = center_season_cell(u).select("entity", "game", "x", "d", "c", "group")
    hv = half_values(cen, CFG, "t/n")
    fit = k_from_halves(hv, CFG)
    groups = cen["group"].n_unique()
    assert all(p.entities <= groups for p in fit.per_m)
    assert fit.entities == groups  # 800 entities, not 3,200 entity-cells
    rows = k_from_halves(hv.drop("group"), CFG)
    assert rows.entities == cen["entity"].n_unique()


def test_wopr_residual_is_target_weighted() -> None:
    # One entity, 4 team targets: 2 his (air 10 and 30 of team air 10, 30, 20, 40).
    rows = pl.DataFrame(
        {
            "entity": ["e"] * 4,
            "his_target": [1.0, 1.0, 0.0, 0.0],
            "his_air": [10.0, 30.0, 0.0, 0.0],
            "team_air": [10.0, 30.0, 20.0, 40.0],
            "c": [1.0] * 4,
            "p": [0.4, 0.4, 0.6, 0.6],  # slot-prior WOPR of his slot in each target's game
        }
    )
    got = wopr_residual_value(1.5, 0.7)(rows)["value"][0]
    wopr = 1.5 * 2 / 4 + 0.7 * 40 / 100
    assert abs(got - (wopr - 0.5)) < 1e-12


def test_prj06_qb_pool_needs_half_the_dropbacks() -> None:
    rows = pl.DataFrame(
        {
            "position": ["QB", "QB", "QB", "RB", "WR", "TE"],
            "missed": [True, False, True, True, False, False],
            "prev_dropback_share": [0.49, MIN_SHARE, 0.51, 0.0, 0.0, 0.0],
        }
    )
    kept = qb_starter_pool(rows, MIN_SHARE)
    assert kept.filter(pl.col("position") == "QB")["prev_dropback_share"].to_list() == [
        MIN_SHARE,
        0.51,
    ]
    assert kept.filter(pl.col("position") != "QB").height == 3  # RB, WR, TE unchanged
