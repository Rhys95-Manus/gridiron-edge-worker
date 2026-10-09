"""BT-02 for stats that are not a single mean of units (user ruling 2026-10-08): the stat is
computed whole within each half. Gaps (DEF-10, DEF-13, PLY-17, PLY-19's gap; DEF-08's on/off)
take m units on each side, so m counts the smaller side; ratios (DEF-04, PLY-04 WOPR) take m
counted units (targets). Same r, k_m = m(1 - r)/r and no-signal rule as single-mean stats.
Planted values and tolerances are test settings."""

from __future__ import annotations

import numpy as np
import polars as pl

from ge.config import load_params
from ge.fit.splithalf import SplitHalfConfig
from ge.fit.whole import gap_value, ratio_value, whole_split_half_k
from tests.phase3.fit.synth import rng

LEVEL = float(load_params().fitting.bt_02_no_signal_confidence.value)
CFG = SplitHalfConfig(m_grid=(25, 50, 100), splits=20, min_entities=30, confidence=LEVEL)
REL_TOL = 0.15


def _gap_rows(*, tau: float, sigma: float, entities: int, games: int, per_arm: int, key: str):  # type: ignore[no-untyped-def]
    g = rng(key)
    true_gap = g.normal(0.0, tau, entities)
    base = g.normal(0.0, 0.3, entities)
    rows = []
    for e in range(entities):
        for j in range(games):
            for arm in (0, 1):
                mu = base[e] + (true_gap[e] if arm else 0.0)
                for v in g.normal(mu, sigma, per_arm):
                    rows.append((f"e{e:05d}", f"g{j:03d}", arm, float(v)))
    return pl.DataFrame(
        rows,
        schema={"entity": pl.Utf8, "game": pl.Utf8, "arm": pl.Int64, "x": pl.Float64},
        orient="row",
    ).with_columns(pl.lit(1.0).alias("c"))


def test_gap_recovers_planted_k() -> None:
    # gap from m units per side: var = 2 sigma^2 / m, so k = 2 sigma^2 / tau^2 (in side units)
    tau, sigma = 0.1, 0.6
    k = 2 * sigma**2 / tau**2
    rows = _gap_rows(tau=tau, sigma=sigma, entities=1200, games=20, per_arm=8, key="gap")
    fit = whole_split_half_k(rows, CFG, "t/gap", gap_value, arm="arm")
    assert fit.status == "fitted" and fit.k is not None
    assert abs(fit.k - k) / k < REL_TOL, fit


def test_gap_without_signal_is_no_detectable_signal() -> None:
    rows = _gap_rows(tau=0.0, sigma=0.6, entities=400, games=12, per_arm=8, key="gap0")
    fit = whole_split_half_k(rows, CFG, "t/gap0", gap_value, arm="arm")
    assert fit.status == "no_signal" and fit.k is None


def test_ratio_recovers_planted_k() -> None:
    # sum(x) / sum(e) with x = rho * e + noise(sigma), e ~ U(0.5, 1.5): k = sigma^2 / tau^2
    g = rng("ratio")
    tau, sigma, entities, games, per = 0.1, 0.9, 1200, 20, 12
    k = sigma**2 / tau**2
    rho = 1.0 + g.normal(0.0, tau, entities)
    n = games * per
    e = g.uniform(0.5, 1.5, (entities, n))
    x = rho[:, None] * e + g.normal(0.0, sigma, (entities, n))
    rows = pl.DataFrame(
        {
            "entity": np.repeat([f"e{i:05d}" for i in range(entities)], n),
            "game": np.tile(np.repeat([f"g{j:03d}" for j in range(games)], per), entities),
            "num": x.ravel(),
            "den": e.ravel(),
            "c": np.ones(entities * n),
        }
    )
    fit = whole_split_half_k(rows, CFG, "t/ratio", ratio_value)
    assert fit.status == "fitted" and fit.k is not None
    assert abs(fit.k - k) / k < REL_TOL, fit


def test_whole_is_deterministic() -> None:
    rows = _gap_rows(tau=0.1, sigma=0.6, entities=100, games=10, per_arm=6, key="det")
    a = whole_split_half_k(rows, CFG, "t/d", gap_value, arm="arm")
    assert whole_split_half_k(rows.reverse(), CFG, "t/d", gap_value, arm="arm") == a
