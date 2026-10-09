"""G1 / BT-02: k by split-half stabilization recovers a planted k (BUILD_PLAN 3e).

Method (user proposal 2026-10-07, confirmed in the 3e plan): split each entity's games at random
into halves, take exactly m units per half, correlate the halves across entities (r), and
k_m = m (1 - r) / r, which is G1's n / (n + k) weighting solved at n = m. Pool over m by inverse
variance, averaging r over seeded splits. Tolerances are test settings stated here."""

from __future__ import annotations

import polars as pl
import pytest

from ge.config import load_params
from ge.fit.splithalf import (
    NO_SIGNAL,
    SplitHalfConfig,
    half_values,
    k_from_halves,
    split_half_k,
    variance_k,
)
from tests.phase3.fit.synth import binomial_units, gaussian_units

LEVEL = float(load_params().fitting.bt_02_no_signal_confidence.value)  # 0.95, BT-02
# A shorter m grid and fewer splits than BT-02's, to keep the test fast; the level is BT-02's.
CFG = SplitHalfConfig(m_grid=(25, 50, 100), splits=20, min_entities=30, confidence=LEVEL)
REL_TOL = 0.15  # recovered k within 15% of the planted k


@pytest.mark.parametrize("k", [40.0, 150.0])
def test_recovers_planted_binomial_k(k: float) -> None:
    u = binomial_units(k=k, mu=0.45, entities=1200, games=20, per_game=12, key=f"bin{k}")
    fit = split_half_k(u, CFG, seed_key=f"t/bin{k}")
    assert fit.k is not None
    assert abs(fit.k - k) / k < REL_TOL, fit


def test_recovers_planted_gaussian_k() -> None:
    k = 90.0
    u = gaussian_units(tau=0.1, sigma=0.1 * k**0.5, entities=1200, games=20, per_game=12, key="g")
    fit = split_half_k(u, CFG, seed_key="t/gauss")
    assert fit.k is not None
    assert abs(fit.k - k) / k < REL_TOL, fit


def test_variance_components_cross_check() -> None:
    k = 90.0
    u = gaussian_units(tau=0.1, sigma=0.1 * k**0.5, entities=1200, games=20, per_game=12, key="g")
    got = variance_k(u)
    assert got is not None and abs(got - k) / k < REL_TOL


def test_ratio_units_use_sum_x_over_sum_d() -> None:
    # The same plays written as ratio units (x / d with d = 2, x doubled) give the same k.
    u = binomial_units(k=60.0, mu=0.4, entities=400, games=12, per_game=10, key="r")
    a = split_half_k(u, CFG, seed_key="t/r")
    b = split_half_k(u.with_columns(pl.col("x") * 2, pl.lit(2.0).alias("d")), CFG, seed_key="t/r")
    assert a.k == b.k


def test_halves_are_game_disjoint_and_sized_m() -> None:
    u = binomial_units(k=60.0, mu=0.4, entities=50, games=12, per_game=10, key="d")
    hv = half_values(u, CFG, seed_key="t/d", keep_games=True)
    for (_, m, _), grp in hv.group_by("split", "m", "entity"):
        assert set(grp["games_a"][0]).isdisjoint(set(grp["games_b"][0]))
        assert grp["n_a"][0] == m and grp["n_b"][0] == m


def test_entities_short_of_2m_are_left_out() -> None:
    u = binomial_units(k=60.0, mu=0.4, entities=60, games=4, per_game=10, key="s")  # 40 plays
    hv = half_values(
        u, SplitHalfConfig(m_grid=(25,), splits=2, min_entities=1, confidence=LEVEL), seed_key="t/s"
    )
    assert hv.is_empty()


def test_deterministic_and_seed_sensitive() -> None:
    u = binomial_units(k=60.0, mu=0.4, entities=300, games=12, per_game=10, key="x")
    a = split_half_k(u, CFG, seed_key="t/x")
    assert split_half_k(u, CFG, seed_key="t/x") == a
    assert split_half_k(u.reverse(), CFG, seed_key="t/x") == a  # row order doesn't matter
    assert split_half_k(u, CFG, seed_key="t/y") != a


def test_too_few_entities_gives_no_k_with_reason() -> None:
    u = binomial_units(k=60.0, mu=0.4, entities=20, games=12, per_game=10, key="f")
    fit = split_half_k(u, CFG, seed_key="t/f")
    assert fit.k is None and fit.reason is not None and "30" in fit.reason


def test_no_signal_is_marked_no_detectable_signal() -> None:
    # BT-02 "No signal": every entity has the same true mean, so no m's 95% Fisher-z interval
    # for r lies above zero. Without the rule this data gave k = 743 (decision 2026-10-07).
    u = gaussian_units(tau=0.0, sigma=1.0, entities=400, games=12, per_game=10, key="n")
    fit = split_half_k(u, CFG, seed_key="t/n")
    assert fit.status == "no_signal"
    assert fit.k is None
    assert fit.reason is not None and NO_SIGNAL in fit.reason
    assert fit.per_m and not any(p.signal for p in fit.per_m)


def test_weak_planted_signal_still_recovered() -> None:
    # The no-signal gate must not swallow a real but weak signal: k = 400 is a large k
    # (r = 0.2 at m = 100, 0.33 at m = 200). Sized so every entity reaches m = 200 and the
    # expected standard error of k is about 5%, well inside REL_TOL. (A first version with 20
    # games per entity had a ~19% standard error and missed by 16.5%: an underpowered test,
    # not a fitter fault; the tolerance is unchanged.)
    k = 400.0
    cfg = SplitHalfConfig(m_grid=(25, 50, 100, 200), splits=20, min_entities=30, confidence=LEVEL)
    u = binomial_units(k=k, mu=0.5, entities=2000, games=40, per_game=12, key="weak")
    fit = split_half_k(u, cfg, seed_key="t/weak")
    assert fit.status == "fitted" and fit.k is not None
    assert abs(fit.k - k) / k < REL_TOL, fit


def test_pooling_across_seasons_concatenates_half_values() -> None:
    a = binomial_units(k=60.0, mu=0.4, entities=600, games=12, per_game=12, key="s1")
    b = binomial_units(k=60.0, mu=0.4, entities=600, games=12, per_game=12, key="s2")
    ha = half_values(a, CFG, seed_key="t/s1")
    hb = half_values(b.with_columns(pl.lit("other_") + pl.col("entity")), CFG, seed_key="t/s2")
    fit = k_from_halves(pl.concat([ha, hb]), CFG)
    assert fit.k is not None and abs(fit.k - 60.0) / 60.0 < REL_TOL
