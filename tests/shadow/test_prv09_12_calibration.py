"""PRV-09 strike grid, PRV-10 selection pairs, PRV-11 calibration checks and PRV-12 log loss,
on synthetic data only (made-up IDs; no real players or games)."""

from __future__ import annotations

import math

import numpy as np
import polars as pl
import pytest
from scipy import stats as sps

from ge.config import load_params
from ge.pricer_v0.calibration import (
    clustered_bin_se,
    log_loss,
    pair_rows,
    prv11,
    recalibration,
    reliability,
    scored_pairs,
    selection_table,
    strike_grid,
)

PV0 = load_params().pricer_v0


def test_strike_grids_follow_prv09() -> None:
    assert strike_grid("receptions") == tuple(range(1, 15))
    assert strike_grid("receiving_yards") == (
        10,
        15,
        20,
        25,
        30,
        40,
        50,
        55,
        60,
        65,
        70,
        *range(80, 191, 10),
    )
    assert strike_grid("rushing_yards") == (
        5,
        10,
        15,
        20,
        25,
        30,
        40,
        45,
        50,
        60,
        65,
        70,
        *range(80, 181, 10),
    )


def test_log_loss_clips_per_prv12() -> None:
    eps = PV0.prv_12_log_loss_clip_eps.value
    p = np.array([0.0, 1.0, 0.25])
    y = np.array([1, 0, 1])
    want = -(math.log(eps) + math.log(eps) + math.log(0.25))
    assert log_loss(p, y) == pytest.approx(want, rel=1e-12)


def test_pair_rows_expand_each_player_game_over_the_strikes() -> None:
    rows = pl.DataFrame(
        {
            "game_id": ["G1", "G2"],
            "team": ["TMA", "TMA"],
            "gsis_id": ["A1", "A1"],
            "group": ["WR", "WR"],
            "actual": [3.0, 0.0],
        }
    )
    ps = {"poisson": [(0.9, 0.5, 0.1), (0.8, 0.4, 0.05)], "nb": [(0.9, 0.6, 0.2), None]}
    out = pair_rows(rows, (1, 2, 3), ps)
    assert out.height == 6
    assert out.filter(pl.col("game_id") == "G1")["y"].to_list() == [1, 1, 1]
    assert out.filter(pl.col("game_id") == "G2")["y"].to_list() == [0, 0, 0]
    assert out["p_nb"].null_count() == 3
    assert out["cluster"].n_unique() == 2


def test_scored_pairs_use_the_poisson_filter_and_need_every_candidate() -> None:
    lo, hi = PV0.prv_09_min_scored_p.value, PV0.prv_09_max_scored_p.value
    df = pl.DataFrame(
        {
            "p_poisson": [lo, hi, lo - 1e-9, hi + 1e-9, 0.5, 0.5],
            "p_a": [0.01, 0.99, 0.5, 0.5, 0.5, None],
            "y": [0, 1, 0, 1, 1, 1],
            "cluster": ["c1", "c1", "c2", "c2", "c3", "c3"],
        }
    )
    out = scored_pairs(df, ("a",))
    assert out["p_poisson"].to_list() == [lo, hi, 0.5]


def test_selection_table_sums_log_loss_per_candidate() -> None:
    df = pl.DataFrame({"p_a": [0.5, 0.25], "p_b": [0.9, 0.1], "y": [1, 0]})
    t = selection_table(df, ("a", "b"))
    assert t["family"].to_list() == ["b", "a"]  # sorted by summed log loss
    want_b = -(math.log(0.9) + math.log(0.9))
    assert t.filter(pl.col("family") == "b")["log_loss_sum"][0] == pytest.approx(want_b)
    assert set(t["n_pairs"].to_list()) == {2}


def test_clustered_bin_se_matches_the_hand_formula() -> None:
    y = np.array([1, 0, 1, 1, 0], dtype=float)
    c = np.array(["a", "a", "b", "c", "c"])
    ybar = y.mean()
    sums = {k: sum(y[i] - ybar for i in range(5) if c[i] == k) for k in "abc"}
    want = math.sqrt(sum(s * s for s in sums.values())) / 5
    assert clustered_bin_se(y, c) == pytest.approx(want, rel=1e-12)


def test_reliability_uses_ten_equal_width_bins_with_wilson_intervals() -> None:
    p = np.array([0.05, 0.15, 0.15, 0.95, 1.0])
    y = np.array([0, 1, 0, 1, 1])
    c = np.array(["a", "b", "c", "d", "e"])
    t = reliability(p, y, c, z=1.96)
    assert t.height == 10
    b1 = t.filter(pl.col("bin") == 1).row(0, named=True)
    assert b1["n"] == 2 and b1["mean_p"] == pytest.approx(0.15) and b1["observed"] == 0.5
    lo, hi = _wilson(1, 2, 1.96)
    assert b1["wilson_lo"] == pytest.approx(lo) and b1["wilson_hi"] == pytest.approx(hi)
    assert t.filter(pl.col("bin") == 9)["n"][0] == 2  # p = 1.0 is in the top bin
    assert t.filter(pl.col("bin") == 4)["n"][0] == 0


def _wilson(k: int, n: int, z: float) -> tuple[float, float]:
    ph = k / n
    centre = (ph + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def test_recalibration_recovers_known_slope_and_intercept() -> None:
    # two predicted probabilities; the MLE fits each group's observed rate exactly
    p = np.array([0.2] * 100 + [0.6] * 100)
    y = np.array([1] * 30 + [0] * 70 + [1] * 50 + [0] * 50)
    c = np.array([f"c{i}" for i in range(200)])
    r = recalibration(p, y, c)
    lg = lambda q: math.log(q / (1 - q))  # noqa: E731
    slope = (lg(0.5) - lg(0.3)) / (lg(0.6) - lg(0.2))
    assert r.slope == pytest.approx(slope, abs=1e-8)
    assert r.intercept == pytest.approx(lg(0.3) - slope * lg(0.2), abs=1e-8)
    assert r.slope_se > 0 and r.intercept_se > 0


def test_recalibration_clustered_se_grows_when_pairs_repeat_a_player_game() -> None:
    rng = np.random.default_rng(1)
    p = rng.uniform(0.1, 0.9, 400)
    y = (rng.uniform(size=400) < p).astype(int)
    single = recalibration(p, y, np.array([f"c{i}" for i in range(400)]))
    doubled = recalibration(
        np.concatenate([p, p]), np.concatenate([y, y]), np.array([f"c{i}" for i in range(400)] * 2)
    )
    assert doubled.slope == pytest.approx(single.slope, abs=1e-8)
    assert doubled.slope_se == pytest.approx(single.slope_se, rel=1e-6)


def test_prv11_checks_each_criterion() -> None:
    rng = np.random.default_rng(3)
    n = 4000
    p = rng.uniform(0.03, 0.97, n)
    y = (rng.uniform(size=n) < p).astype(int)
    c = np.array([f"c{i}" for i in range(n)])
    res = prv11(p, y, c, p_baseline=np.full(n, 0.5))
    assert res.checks["min_pairs"] and res.checks["slope"] and res.checks["citl"]
    assert res.checks["bins"] and res.checks["brier"] and res.passed
    assert res.citl == pytest.approx(float(y.mean() - p.mean()))
    assert res.brier == pytest.approx(float(np.mean((p - y) ** 2)))
    bad = prv11(np.clip(p * 1.5, 0, 1), y, c, p_baseline=p)
    assert not bad.passed and not bad.checks["brier"]
    few = prv11(p[:999], y[:999], c[:999], p_baseline=p[:999])
    assert not few.checks["min_pairs"]


def test_prv11_ignores_bins_under_the_minimum_for_the_bin_check() -> None:
    min_bin = int(PV0.prv_11_min_pairs_per_bin.value)
    n_ok = int(PV0.prv_11_min_scored_pairs.value)
    p = np.concatenate([np.full(n_ok, 0.55), np.full(min_bin - 1, 0.05)])
    small = np.ones(min_bin - 1)
    small[0] = 0  # not all YES, so the logistic fit has a finite maximum
    y = np.concatenate([np.arange(n_ok) % 20 < 11, small]).astype(int)
    c = np.array([f"c{i}" for i in range(p.size)])
    res = prv11(p, y, c, p_baseline=p)
    b0 = res.bins.filter(pl.col("bin") == 0).row(0, named=True)
    assert b0["used"] is False and b0["within"] is False
    assert res.checks["bins"]


def test_wilson_helper_matches_scipy_binomtest() -> None:
    ci = sps.binomtest(7, 20).proportion_ci(confidence_level=0.95, method="wilson")
    lo, hi = _wilson(7, 20, float(sps.norm.ppf(0.975)))
    assert lo == pytest.approx(ci.low) and hi == pytest.approx(ci.high)


# ---- family ladders for scoring ----

from ge.pricer_v0.calibration import family_ladders  # noqa: E402
from ge.pricer_v0.distributions import (  # noqa: E402
    CompoundReceivingYards,
    CompoundRushingYards,
    EmpiricalRatio,
    HurdleGamma,
    NegativeBinomial,
    Poisson,
    ShiftedGamma,
    generator,
)
from ge.pricer_v0.fitting import WindowFit  # noqa: E402
from ge.pricer_v0.training import YardsPools  # noqa: E402

N_DRAWS = int(PV0.prv_07_monte_carlo_draws.value)
POOL = tuple(float(v) for v in range(-2, 25))
ER = EmpiricalRatio(edges=(1.0, 20.0, 60.0), ratios=((0.0, 1.0, 2.0), (0.5, 1.5)))


def _fit() -> WindowFit:
    return WindowFit(
        window="S2023",
        test_season=2023,
        seasons=(2021, 2022),
        nb_size={"WR": 6.0},
        carries_size={"RB": 3.0},
        compound_receiving={"WR": sum(POOL) / len(POOL)},
        compound_per_carry_mean={"RB": sum(POOL) / len(POOL)},
        hurdle={"WR": HurdleGamma(alpha=1.8, zero_mass=0.1)},
        shifted={"RB": ShiftedGamma(alpha=1.4, shift=5.0)},
        empirical={("receiving_yards", "WR"): ER, ("rushing_yards", "RB"): ER},
        n={},
        missing={},
    )


POOLS = YardsPools(
    window="S2023",
    seasons=(2021, 2022),
    per_reception={"WR": POOL, "TE": POOL},
    per_carry={"RB": POOL},
    dropped_receptions=0,
    dropped_carries=0,
)


def _score_rows(groups: list[str], mus: list[float], carries: list[float]) -> pl.DataFrame:
    n = len(groups)
    return pl.DataFrame(
        {
            "game_id": [f"2023_0{i + 1}_TMA_TMB" for i in range(n)],
            "team": ["TMA"] * n,
            "gsis_id": [f"P{i}" for i in range(n)],
            "group": groups,
            "mu": mus,
            "carries_mean": carries,
            "actual": [0.0] * n,
        }
    )


def test_receptions_ladders_poisson_and_group_nb() -> None:
    rows = _score_rows(["WR", "TE"], [4.0, 3.0], [0.0, 0.0])
    s = strike_grid("receptions")
    got = family_ladders(rows, "receptions", _fit(), POOLS, model_version="0")
    assert got["poisson"] == [Poisson().p_over(4.0, s), Poisson().p_over(3.0, s)]
    assert got["negative_binomial"] == [NegativeBinomial(6.0).p_over(4.0, s), None]


def test_receiving_yards_ladders_every_candidate_and_the_baseline() -> None:
    rows = _score_rows(["WR", "WR", "TE"], [45.0, 30.0, 30.0], [0.0, 0.0, 0.0])
    s = strike_grid("receiving_yards")
    rec_mu = {("2023_01_TMA_TMB", "TMA", "P0"): 4.0, ("2023_03_TMA_TMB", "TMA", "P2"): 3.0}
    got = family_ladders(
        rows,
        "receiving_yards",
        _fit(),
        POOLS,
        model_version="0",
        receptions_family="negative_binomial",
        rec_mu=rec_mu,
    )
    assert got["poisson"][0] == Poisson().p_over(45.0, s)
    rng = generator("2023_01_TMA_TMB", "0", "P0", "receiving_yards")
    want = CompoundReceivingYards(NegativeBinomial(6.0), POOL).p_over(45.0, 4.0, s, rng, N_DRAWS)
    assert got["compound"][0] == want
    assert got["compound"][1] is None  # no receptions mu for P1
    assert got["compound"][2] is None  # TE has no compound fit
    assert got["hurdle_gamma"][0] == HurdleGamma(alpha=1.8, zero_mass=0.1).p_over(45.0, s)
    assert got["hurdle_gamma"][2] is None
    assert got["empirical_ratio"][1] == ER.p_over(30.0, s)


def test_receiving_compound_with_poisson_receptions() -> None:
    rows = _score_rows(["WR"], [45.0], [0.0])
    s = strike_grid("receiving_yards")
    got = family_ladders(
        rows,
        "receiving_yards",
        _fit(),
        POOLS,
        model_version="0",
        receptions_family="poisson",
        rec_mu={("2023_01_TMA_TMB", "TMA", "P0"): 4.0},
    )
    rng = generator("2023_01_TMA_TMB", "0", "P0", "receiving_yards")
    assert got["compound"][0] == CompoundReceivingYards(Poisson(), POOL).p_over(
        45.0, 4.0, s, rng, N_DRAWS
    )


def test_rushing_yards_ladders_and_carries_mean_not_positive() -> None:
    rows = _score_rows(["RB", "RB"], [55.0, 20.0], [12.0, 0.0])
    s = strike_grid("rushing_yards")
    got = family_ladders(rows, "rushing_yards", _fit(), POOLS, model_version="0")
    rng = generator("2023_01_TMA_TMB", "0", "P0", "rushing_yards")
    assert got["compound"][0] == CompoundRushingYards(3.0, POOL).p_over(55.0, 12.0, s, rng, N_DRAWS)
    assert got["compound"][1] is None
    assert got["shifted_gamma"][1] == ShiftedGamma(alpha=1.4, shift=5.0).p_over(20.0, s)
    assert got["empirical_ratio"][0] == ER.p_over(55.0, s)
