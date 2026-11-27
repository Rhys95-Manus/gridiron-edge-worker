"""PRV-04 to PRV-06 candidate families and PRV-07 read-off, parameters as explicit inputs,
synthetic values only."""

from __future__ import annotations

import hashlib
import math

import numpy as np
import pytest

from ge.config import load_params
from ge.pricer_v0.distributions import (
    CompoundReceivingYards,
    CompoundRushingYards,
    EmpiricalRatio,
    HurdleGamma,
    LadderError,
    NegativeBinomial,
    Poisson,
    ShiftedGamma,
    check_ladder,
    generator,
    round_half_up,
    seed_key,
    thinned_targets,
)
from ge.pricer_v0.reasons import PricerUnpriced

N_DRAWS = int(load_params().pricer_v0.prv_07_monte_carlo_draws.value)
STRIKES = (1, 2, 3, 4, 5, 6, 8, 10)


def nb_pmf(y: int, mu: float, r: float) -> float:
    """Spec sync #6: P(Y = y) = Γ(y + r) / (Γ(r) y!) · (r/(r+μ))^r · (μ/(r+μ))^y."""
    log = (
        math.lgamma(y + r)
        - math.lgamma(r)
        - math.lgamma(y + 1)
        + r * math.log(r / (r + mu))
        + y * math.log(mu / (r + mu))
    )
    return math.exp(log)


def nb_sf(x: int, mu: float, r: float) -> float:
    return 1.0 - math.fsum(nb_pmf(y, mu, r) for y in range(x))


# ---- PRV-07 seeding, rounding, ladder ----


def test_seed_key_format() -> None:
    assert seed_key("2024_05_TMA_TMB", "0", "P1", "receiving_yards") == (
        "PRV-07|2024_05_TMA_TMB|0|P1|receiving_yards"
    )


def test_generator_is_default_rng_of_first_16_hex_digits() -> None:
    key = "PRV-07|g|0|P1|receptions"
    want = np.random.default_rng(int(hashlib.sha256(key.encode()).hexdigest()[:16], 16))
    got = generator("g", "0", "P1", "receptions")
    assert np.array_equal(got.integers(0, 1 << 30, 20), want.integers(0, 1 << 30, 20))


def test_round_half_up_including_negatives() -> None:
    y = np.array([2.5, 2.49, -2.5, -0.5, -0.51, 0.0, 3.0])
    assert round_half_up(y).tolist() == [3.0, 2.0, -2.0, 0.0, -1.0, 0.0, 3.0]


def test_ladder_check() -> None:
    check_ladder((1, 2, 3), (0.9, 0.9, 0.1))
    with pytest.raises(LadderError):
        check_ladder((1, 2, 3), (0.9, 0.5, 0.6))
    with pytest.raises(LadderError):
        check_ladder((2, 1), (0.9, 0.5))
    with pytest.raises(LadderError):
        check_ladder((1, 1), (0.9, 0.9))


# ---- PRV-04 ----


def test_poisson_p_over_is_one_minus_cdf_at_x_minus_one() -> None:
    mu = 4.2
    want = tuple(
        1.0 - math.fsum(math.exp(-mu) * mu**y / math.factorial(y) for y in range(x))
        for x in STRIKES
    )
    assert Poisson().p_over(mu, STRIKES) == pytest.approx(want, abs=1e-12)


def test_negative_binomial_matches_the_spec_pmf() -> None:
    mu, r = 4.2, 3.5
    want = tuple(nb_sf(x, mu, r) for x in STRIKES)
    assert NegativeBinomial(r).p_over(mu, STRIKES) == pytest.approx(want, abs=1e-10)


def test_negative_binomial_sampling_has_mean_mu_and_spec_variance() -> None:
    mu, r = 5.0, 2.0
    y = NegativeBinomial(r).sample(np.random.default_rng(7), mu, 400_000)
    assert y.mean() == pytest.approx(mu, abs=0.03)
    assert y.var() == pytest.approx(mu + mu * mu / r, rel=0.02)


def test_poisson_sampling_has_mean_mu() -> None:
    y = Poisson().sample(np.random.default_rng(7), 3.0, 400_000)
    assert y.mean() == pytest.approx(3.0, abs=0.02)


@pytest.mark.parametrize("q", [0.3, 0.65, 0.9])
def test_thinned_targets_equals_nb_with_targets_size(q: float) -> None:
    mu, r_t = 4.0, 2.5
    m_t = mu / q
    for x in STRIKES:
        brute = 0.0
        for t in range(400):
            p_t = nb_pmf(t, m_t, r_t)
            p_rec = math.fsum(math.comb(t, j) * q**j * (1 - q) ** (t - j) for j in range(x, t + 1))
            brute += p_t * p_rec
        assert thinned_targets(r_t).p_over(mu, (x,))[0] == pytest.approx(brute, abs=1e-9)
    assert thinned_targets(r_t) == NegativeBinomial(r_t)


@pytest.mark.parametrize("family", [Poisson(), NegativeBinomial(2.0)])
def test_discrete_families_need_a_positive_mean(family: Poisson | NegativeBinomial) -> None:
    with pytest.raises(ValueError):
        family.p_over(0.0, STRIKES)


# ---- PRV-05 / PRV-06 continuous ----


def test_hurdle_gamma_is_continuous_with_zero_mass() -> None:
    mu, pi = 40.0, 0.2
    theta = mu / (1 - pi)  # alpha = 1: exponential
    xs = (10, 25, 60)
    want = tuple((1 - pi) * math.exp(-(x - 0.5) / theta) for x in xs)
    assert HurdleGamma(alpha=1.0, zero_mass=pi).p_over(mu, xs) == pytest.approx(want, abs=1e-12)


def test_hurdle_gamma_below_the_zero_mass_is_not_defined() -> None:
    with pytest.raises(NotImplementedError, match="PRV-05"):
        HurdleGamma(alpha=1.0, zero_mass=0.2).p_over(40.0, (0,))


def test_shifted_gamma_is_continuous() -> None:
    mu, s = 50.0, 8.0
    theta = mu + s  # alpha = 1
    xs = (5, 30, 90)
    want = tuple(math.exp(-(x - 0.5 + s) / theta) for x in xs)
    assert ShiftedGamma(alpha=1.0, shift=s).p_over(mu, xs) == pytest.approx(want, abs=1e-12)


# ---- empirical ratio ----

EMP = EmpiricalRatio(
    edges=(10.0, 20.0, 30.0, 40.0),
    ratios=((0.0, 0.5, 1.0, 2.0), (0.2, 1.0, 1.0, 1.5, 3.0), (1.0,)),
)


def test_empirical_ratio_share_in_the_bin() -> None:
    # mu = 25 -> bin 1; mu * r = 5, 25, 25, 37.5 (-> 38), 75
    assert EMP.p_over(25.0, (5, 6, 26, 38, 39, 76)) == (1.0, 0.8, 0.4, 0.4, 0.2, 0.0)


def test_empirical_ratio_end_bins_take_mu_outside_the_edges() -> None:
    # bin 0: mu * r = 0, 2.5 -> 3, 5, 10
    assert EMP.p_over(5.0, (1, 3, 4, 10)) == (0.75, 0.75, 0.5, 0.25)
    assert EMP.p_over(99.0, (99, 100)) == (1.0, 0.0)
    assert EMP.p_over(10.0, (1,)) == (0.75,)
    assert EMP.p_over(40.0, (40,)) == (1.0,)


def test_empirical_ratio_mu_on_an_interior_edge_is_not_guessed() -> None:
    with pytest.raises(NotImplementedError, match="PRV-05"):
        EMP.p_over(20.0, (5,))


# ---- compound models (Monte Carlo) ----


def test_compound_receiving_matches_its_receptions_law_when_yards_are_constant() -> None:
    fam = CompoundReceivingYards(receptions=Poisson(), per_reception_yards=(10.0, 10.0))
    mu_rec, mu = 4.0, 40.0  # yards = 10 N exactly
    xs = (10, 20, 30, 40, 50, 60, 70, 80)
    got = fam.p_over(mu, mu_rec, xs, generator("g", "0", "P1", "receiving_yards"), N_DRAWS)
    assert not isinstance(got, PricerUnpriced)
    want = Poisson().p_over(mu_rec, tuple(x // 10 for x in xs))
    se = max(math.sqrt(p * (1 - p) / N_DRAWS) for p in want)
    assert got == pytest.approx(want, abs=5 * se)


def test_compound_receiving_scales_its_mean_to_mu() -> None:
    fam = CompoundReceivingYards(
        receptions=NegativeBinomial(3.0), per_reception_yards=(-3.0, 5.0, 12.0, 40.0)
    )
    mu = 57.0
    lo, hi = -150, 1500  # beyond every draw
    xs = tuple(range(lo, hi))
    p = fam.p_over(mu, 4.0, xs, generator("g", "0", "P1", "receiving_yards"), N_DRAWS)
    assert not isinstance(p, PricerUnpriced)
    assert p[0] == 1.0 and p[-1] == 0.0
    # integer Z: E[Z] = sum_{x >= 1} P(Z >= x) - sum_{x <= 0} P(Z < x)
    pos = math.fsum(p[xs.index(x)] for x in range(1, hi))
    neg = math.fsum(1.0 - p[xs.index(x)] for x in range(lo + 1, 1))
    assert pos - neg == pytest.approx(mu, rel=0.03)


def test_compound_is_deterministic_and_one_draw_set_serves_every_strike() -> None:
    fam = CompoundReceivingYards(
        receptions=NegativeBinomial(2.0), per_reception_yards=(1.0, 8.0, 15.0, 33.0)
    )
    xs = (10, 25, 40, 55, 70)

    def run(player: str, strikes: tuple[int, ...]) -> tuple[float, ...] | PricerUnpriced:
        return fam.p_over(
            45.0, 3.5, strikes, generator("g", "0", player, "receiving_yards"), N_DRAWS
        )

    a, b = run("P1", xs), run("P1", xs)
    assert a == b
    assert run("P2", xs) != a
    assert isinstance(a, tuple)
    assert run("P1", (40,)) == (a[2],)


def test_compound_receiving_mu_rec_not_positive() -> None:
    fam = CompoundReceivingYards(receptions=Poisson(), per_reception_yards=(10.0,))
    got = fam.p_over(40.0, 0.0, (10,), generator("g", "0", "P1", "receiving_yards"), N_DRAWS)
    assert got is PricerUnpriced.MU_NOT_POSITIVE


def test_compound_rushing_constant_yards_matches_nb_carries() -> None:
    fam = CompoundRushingYards(carries_size=4.0, per_carry_yards=(4.0,))
    carries, mu = 12.0, 48.0  # yards = 4 C exactly
    xs = (20, 40, 48, 60, 80)
    got = fam.p_over(mu, carries, xs, generator("g", "0", "P1", "rushing_yards"), N_DRAWS)
    want = tuple(nb_sf(math.ceil(x / 4), carries, 4.0) for x in xs)
    se = max(math.sqrt(p * (1 - p) / N_DRAWS) for p in want)
    assert got == pytest.approx(want, abs=5 * se)


@pytest.mark.parametrize(
    ("carries_mean", "pool"),
    [(0.0, (3.0, 5.0)), (-1.0, (3.0,)), (10.0, (-2.0, 1.0, 1.0)), (10.0, (0.0,))],
)
def test_compound_rushing_not_positive(carries_mean: float, pool: tuple[float, ...]) -> None:
    fam = CompoundRushingYards(carries_size=4.0, per_carry_yards=pool)
    got = fam.p_over(30.0, carries_mean, (10,), generator("g", "0", "P1", "rushing_yards"), N_DRAWS)
    assert got is PricerUnpriced.MU_NOT_POSITIVE


def test_compound_rushing_negative_yards_round_half_up() -> None:
    # per-carry mean 2.5 > 0, scale 5 / (2 * 2.5) = 1: losses stay negative after rounding
    fam = CompoundRushingYards(carries_size=1e9, per_carry_yards=(-5.0, 10.0))
    got = fam.p_over(5.0, 2.0, (-20, 0, 1, 50), generator("g", "0", "P1", "rushing_yards"), N_DRAWS)
    assert isinstance(got, tuple)
    assert got[0] > 0.99 and got[1] < 1.0
    check_ladder((-20, 0, 1, 50), got)
