"""PRV-04 to PRV-06 candidate distributions and PRV-07's P(over) read-off.

Every distribution parameter is an explicit input (fitting is session 7). Spec sync #6
(2026-11-27) parameterisations:
- Negative binomial: mean μ and size r > 0, variance μ + μ²/r. Poisson is the baseline.
- PRV-04 candidate 2: targets ~ NB(mean μ/q, size r_t), receptions ~ Binomial(targets, q),
  which equals NB(r_t, mean μ), computed in closed form.
- PRV-05 compound: Monte Carlo, N from the selected PRV-04 family with mean μ_rec, Y_i drawn
  with replacement from the league per-reception yards, Yards = Σ Y_i * μ / (μ_rec * mean(Y)).
- PRV-05 hurdle gamma: P(Y ≤ 0) = π, otherwise Gamma(alpha, θ) with θ = μ / ((1 - π) alpha).
- PRV-06 compound: carries ~ NB(mean = carries mean, size), per-carry yards drawn with
  replacement, Yards = Σ draws * μ / (carries mean * mean per-carry yards); a carries mean or
  mean per-carry yards ≤ 0 is mu_not_positive.
- PRV-06 shifted gamma: Y = G - s, G ~ Gamma(alpha, θ), θ = (μ + s)/alpha.
- Empirical ratio: bins edged by training μ deciles; p = share of the bin's ratios with
  round(μ·r) ≥ X, exactly.

PRV-07: p = P(Y ≥ X) = 1 - F(X - 1) for discrete models, 1 - F(X - 0.5) for continuous ones.
Monte Carlo uses n_draws = 10,000 from numpy default_rng of the first 16 hex digits of
SHA-256('PRV-07|<game_id>|<model_version>|<gsis_id>|<stat>'), one draw set per player and stat
for every strike, yards rounded half up (floor(y + 0.5)) before comparing. p is non-increasing
in X, checked in code.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy import stats as sps

from ge.config import load_params
from ge.fit.splithalf import seeded
from ge.pricer_v0.reasons import PricerUnpriced

SPEC_ID = "PRV-07"


class LadderError(ValueError):
    """PRV-07: p increased with X for one player and stat (PRJ-04's rule)."""


def _pv0_value(name: str) -> float:
    return float(getattr(load_params().pricer_v0, name).value)


def _require_mu(mu: float, spec_id: str) -> None:
    if not mu > 0:
        raise ValueError(f"{spec_id}: μ must be > 0 (PRV-03 leaves μ <= 0 unpriced), got {mu}")


def seed_key(game_id: str, model_version: str, gsis_id: str, stat: str) -> str:
    """PRV-07: the seed key; model_version is the shadow_version (SHD-15)."""
    return f"{SPEC_ID}|{game_id}|{model_version}|{gsis_id}|{stat}"


def generator(game_id: str, model_version: str, gsis_id: str, stat: str) -> np.random.Generator:
    """PRV-07: numpy default_rng of the first 16 hex digits of SHA-256(seed_key); the same
    construction as ge.fit.splithalf.seeded, which it reuses."""
    return seeded(seed_key(game_id, model_version, gsis_id, stat))


def round_half_up(y: np.ndarray) -> np.ndarray:
    """PRV-07: floor(y + 0.5), negatives included."""
    return np.floor(np.asarray(y, dtype=float) + _pv0_value("prv_07_round_half_up_offset"))


def check_ladder(strikes: Sequence[int], ps: Sequence[float]) -> None:
    """PRV-07: p non-increasing in X; strikes strictly increasing. Raises LadderError."""
    if len(strikes) != len(ps):
        raise LadderError(f"{SPEC_ID}: {len(strikes)} strikes but {len(ps)} probabilities")
    for i in range(1, len(strikes)):
        if not strikes[i] > strikes[i - 1]:
            raise LadderError(f"{SPEC_ID}: strikes not strictly increasing: {list(strikes)}")
        if ps[i] > ps[i - 1]:
            raise LadderError(
                f"{SPEC_ID}: p rises from {ps[i - 1]} at X = {strikes[i - 1]} to {ps[i]} at "
                f"X = {strikes[i]}"
            )


def _checked(sf_at: np.ndarray, strikes: Sequence[int]) -> tuple[float, ...]:
    ps = tuple(float(x) for x in sf_at)
    check_ladder(strikes, ps)
    return ps


def _continuous_points(strikes: Sequence[int]) -> np.ndarray:
    """PRV-07: continuous models read 1 - F(X - 0.5)."""
    return np.asarray(strikes, dtype=float) - _pv0_value("prv_07_continuity_offset")


def _share_at_least(values: np.ndarray, strikes: Sequence[int]) -> tuple[float, ...]:
    """Share of whole-number values >= X for every strike, exact counts over one value set."""
    ordered = np.sort(values)
    n = ordered.size
    ps = tuple(float(n - int(np.searchsorted(ordered, x, side="left"))) / n for x in strikes)
    check_ladder(strikes, ps)
    return ps


@dataclass(frozen=True)
class Poisson:
    """PRV-04 baseline (discrete)."""

    def p_over(self, mu: float, strikes: Sequence[int]) -> tuple[float, ...]:
        """PRV-07 discrete: P(Y ≥ X) = 1 - F(X - 1)."""
        _require_mu(mu, "PRV-04")
        return _checked(sps.poisson.sf(np.asarray(strikes) - 1, mu), strikes)

    def sample(self, rng: np.random.Generator, mu: float, n: int) -> np.ndarray:
        """PRV-05 compound: n Poisson(μ) draws."""
        return rng.poisson(mu, n)


@dataclass(frozen=True)
class NegativeBinomial:
    """PRV-04 candidate 1 (and candidate 2 through thinned_targets): NB(mean μ, size r)."""

    size: float

    def __post_init__(self) -> None:
        if not self.size > 0:
            raise ValueError(f"PRV-04: NB size must be > 0, got {self.size}")

    def _p(self, mu: float) -> float:
        # mean μ, size r: success probability r / (r + μ), variance μ + μ²/r
        return self.size / (self.size + mu)

    def p_over(self, mu: float, strikes: Sequence[int]) -> tuple[float, ...]:
        """PRV-07 discrete: P(Y ≥ X) = 1 - F(X - 1)."""
        _require_mu(mu, "PRV-04")
        return _checked(sps.nbinom.sf(np.asarray(strikes) - 1, self.size, self._p(mu)), strikes)

    def sample(self, rng: np.random.Generator, mu: float, n: int) -> np.ndarray:
        """PRV-05/06 compound: n NB(mean μ, size r) draws."""
        return rng.negative_binomial(self.size, self._p(mu), n)


ReceptionsFamily = Poisson | NegativeBinomial


def thinned_targets(targets_size: float) -> NegativeBinomial:
    """PRV-04 candidate 2: targets NB(mean μ/q, size r_t) thinned by Binomial(q) is
    NB(r_t, mean μ), whatever q is."""
    return NegativeBinomial(targets_size)


@dataclass(frozen=True)
class HurdleGamma:
    """PRV-05 hurdle gamma (continuous): zero mass π, shape alpha, per position group."""

    alpha: float
    zero_mass: float

    def __post_init__(self) -> None:
        if not (self.alpha > 0 and 0 <= self.zero_mass < 1):
            raise ValueError(f"PRV-05: need alpha > 0 and 0 ≤ π < 1, got {self}")

    def p_over(self, mu: float, strikes: Sequence[int]) -> tuple[float, ...]:
        """PRV-05/PRV-07 continuous: 1 - F(X - 0.5) with F(y) = π + (1 - π) G(y) for y > 0,
        θ = μ / ((1 - π) alpha)."""
        _require_mu(mu, "PRV-05")
        y = _continuous_points(strikes)
        if (y <= 0).any():
            raise NotImplementedError(
                "PRV-05: hurdle gamma F(y) for y <= 0 is not defined (only P(Y <= 0) = π is)"
            )
        theta = mu / ((1 - self.zero_mass) * self.alpha)
        sf = (1 - self.zero_mass) * sps.gamma.sf(y, self.alpha, scale=theta)
        return _checked(sf, strikes)


@dataclass(frozen=True)
class ShiftedGamma:
    """PRV-06 shifted gamma (continuous): shape alpha, shift s, per position group."""

    alpha: float
    shift: float

    def __post_init__(self) -> None:
        if not (self.alpha > 0 and self.shift >= 0):
            raise ValueError(f"PRV-06: need alpha > 0 and s ≥ 0, got {self}")

    def p_over(self, mu: float, strikes: Sequence[int]) -> tuple[float, ...]:
        """PRV-06/PRV-07 continuous: 1 - F(X - 0.5) for Y = G - s,
        G ~ Gamma(alpha, θ = (μ + s)/alpha)."""
        _require_mu(mu, "PRV-06")
        theta = (mu + self.shift) / self.alpha
        sf = sps.gamma.sf(_continuous_points(strikes) + self.shift, self.alpha, scale=theta)
        return _checked(sf, strikes)


@dataclass(frozen=True)
class EmpiricalRatio:
    """PRV-05/06 empirical ratio: `edges` (B + 1 increasing training-μ decile edges) and the
    actual/μ ratios of each of the B bins."""

    edges: tuple[float, ...]
    ratios: tuple[tuple[float, ...], ...]

    def __post_init__(self) -> None:
        e = self.edges
        if len(e) < 2 or any(not e[i] > e[i - 1] for i in range(1, len(e))):
            raise ValueError(f"PRV-05: bin edges must be strictly increasing, got {e}")
        if len(self.ratios) != len(e) - 1 or any(not r for r in self.ratios):
            raise ValueError("PRV-05: one non-empty ratio set per bin")

    def bin_of(self, mu: float) -> int:
        """PRV-05/06: a μ below the lowest edge or above the highest goes in the end bin. A μ
        exactly on an interior edge is not settled by the spec."""
        interior = self.edges[1:-1]
        if mu in interior:
            raise NotImplementedError(
                f"PRV-05: μ = {mu} is on an interior bin edge; the spec doesn't say which bin"
            )
        return int(np.searchsorted(np.asarray(interior, dtype=float), mu, side="left"))

    def p_over(self, mu: float, strikes: Sequence[int]) -> tuple[float, ...]:
        """PRV-05/06, PRV-07: p = share of the bin's ratios with round(μ·r) ≥ X, exactly
        (round half up)."""
        _require_mu(mu, "PRV-05")
        r = np.asarray(self.ratios[self.bin_of(mu)], dtype=float)
        return _share_at_least(round_half_up(mu * r), strikes)


def _compound_sums(rng: np.random.Generator, counts: np.ndarray, pool: np.ndarray) -> np.ndarray:
    """PRV-07 draw order (rule 6): after the counts, one rng.integers call draws every per-play
    index with replacement, in draw order; draw j sums its own counts[j] plays."""
    total = int(counts.sum())
    picks = pool[rng.integers(0, pool.size, size=total)]
    owner = np.repeat(np.arange(counts.size), counts)
    return np.bincount(owner, weights=picks, minlength=counts.size)


def _pool_mean(values: tuple[float, ...], spec_id: str) -> tuple[np.ndarray, float]:
    if not values:
        raise ValueError(f"{spec_id}: empty per-play yards pool")
    pool = np.asarray(values, dtype=float)
    return pool, math.fsum(values) / len(values)


@dataclass(frozen=True)
class CompoundReceivingYards:
    """PRV-05 compound model (Monte Carlo)."""

    receptions: ReceptionsFamily
    per_reception_yards: tuple[float, ...]

    def p_over(
        self, mu: float, mu_rec: float, strikes: Sequence[int], rng: np.random.Generator, n: int
    ) -> tuple[float, ...] | PricerUnpriced:
        """PRV-05 compound, PRV-07: Yards = (Σ_{i≤N} Y_i) * μ / (μ_rec * mean(Y)); μ_rec ≤ 0
        is mu_not_positive. The spec doesn't cover mean(Y) ≤ 0, so it raises."""
        _require_mu(mu, "PRV-05")
        if not mu_rec > 0:
            return PricerUnpriced.MU_NOT_POSITIVE
        pool, mean = _pool_mean(self.per_reception_yards, "PRV-05")
        if not mean > 0:
            raise NotImplementedError(
                f"PRV-05: league mean per-reception yards is {mean}; the spec doesn't say"
            )
        counts = self.receptions.sample(rng, mu_rec, n)
        sums = _compound_sums(rng, counts, pool)
        return _share_at_least(round_half_up(sums * (mu / (mu_rec * mean))), strikes)


@dataclass(frozen=True)
class CompoundRushingYards:
    """PRV-06 compound model (Monte Carlo)."""

    carries_size: float
    per_carry_yards: tuple[float, ...]

    def p_over(
        self,
        mu: float,
        carries_mean: float,
        strikes: Sequence[int],
        rng: np.random.Generator,
        n: int,
    ) -> tuple[float, ...] | PricerUnpriced:
        """PRV-06 compound, PRV-07: Yards = Σ draws * μ / (carries mean * mean per-carry
        yards); a carries mean or mean per-carry yards ≤ 0 is mu_not_positive."""
        _require_mu(mu, "PRV-06")
        pool, mean = _pool_mean(self.per_carry_yards, "PRV-06")
        if not (carries_mean > 0 and mean > 0):
            return PricerUnpriced.MU_NOT_POSITIVE
        counts = NegativeBinomial(self.carries_size).sample(rng, carries_mean, n)
        sums = _compound_sums(rng, counts, pool)
        return _share_at_least(round_half_up(sums * (mu / (carries_mean * mean))), strikes)
