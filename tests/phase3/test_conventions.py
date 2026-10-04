"""G1-G7 conventions: property tests (BUILD_PLAN Phase 3) and the G6 ridge solver."""

from __future__ import annotations

import math

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from ge.config import load_params
from ge.metrics import conventions as cv

finite = st.floats(min_value=-1e3, max_value=1e3, allow_nan=False)
positive = st.floats(min_value=1e-3, max_value=1e4, allow_nan=False)


@given(observed=finite, prior=finite, k=positive)
def test_shrink_is_prior_at_n_zero(observed: float, prior: float, k: float) -> None:
    assert cv.shrink(observed, 0, prior, k) == prior


@given(observed=finite, prior=finite, k=positive)
def test_shrink_is_midpoint_at_n_equal_k(observed: float, prior: float, k: float) -> None:
    assert cv.shrink(observed, k, prior, k) == pytest.approx((observed + prior) / 2, abs=1e-9)


@given(observed=finite, prior=finite, k=positive)
def test_shrink_approaches_observed_as_n_grows(observed: float, prior: float, k: float) -> None:
    gaps = [abs(cv.shrink(observed, n, prior, k) - observed) for n in (k, 10 * k, 1000 * k)]
    eps = 4 * math.ulp(max(abs(observed), abs(prior), 1.0))  # float rounding, not shrinkage
    assert gaps[0] + eps >= gaps[1] and gaps[1] + eps >= gaps[2]
    assert gaps[2] <= abs(prior - observed) / 1000 + 1e-9


@given(observed=finite, prior=finite, k=positive, n=positive)
def test_shrink_lies_between_prior_and_observed(
    observed: float, prior: float, k: float, n: float
) -> None:
    s = cv.shrink(observed, n, prior, k)
    lo, hi = min(observed, prior), max(observed, prior)
    assert lo - 1e-9 <= s <= hi + 1e-9


@given(h=st.floats(min_value=0.5, max_value=20))
def test_weights_are_one_now_and_half_at_h(h: float) -> None:
    w = cv.recency_weights(np.array([0.0, h, 2 * h]), h)
    assert w.tolist() == pytest.approx([1.0, 0.5, 0.25])


@given(n=st.integers(min_value=1, max_value=500))
def test_n_eff_equals_n_for_equal_weights(n: int) -> None:
    assert cv.n_eff(np.ones(n)) == pytest.approx(n)


@given(g=st.lists(st.integers(min_value=0, max_value=20), min_size=1, max_size=300))
def test_n_eff_never_exceeds_n(g: list[int]) -> None:
    w = cv.recency_weights(np.array(g, dtype=float), 3)
    assert cv.n_eff(w) <= len(g) + 1e-9
    assert cv.n_eff(w) >= 1 - 1e-9


def test_weighted_mean() -> None:
    assert cv.weighted_mean(np.array([1.0, 3.0]), np.array([1.0, 0.5])) == pytest.approx(5 / 3)


def test_half_lives_come_from_params() -> None:
    p = load_params().conventions
    assert cv.half_life("usage") == p.g3_usage_half_life_games.value
    assert cv.half_life("efficiency") == p.g3_efficiency_half_life_games.value


def test_carryover_prior() -> None:
    """G4: last season's value; regressed a further 1/3 toward league on a change; unknown
    change raises (user decision 2026-10-02)."""
    extra = load_params().conventions.g4_new_caller_or_qb_extra_regression.value
    assert cv.carryover_prior(0.10, 0.0, changed=False) == 0.10
    assert cv.carryover_prior(0.10, 0.04, changed=True) == pytest.approx(0.10 + extra * (-0.06))
    with pytest.raises(NotImplementedError, match="G4"):
        cv.carryover_prior(0.10, 0.04, changed=None)


def test_g4_window_from_params() -> None:
    last = int(load_params().conventions.g4_prior_carryover_last_week.value)
    assert cv.in_carryover_window(last)
    assert cv.in_carryover_window(1)
    assert not cv.in_carryover_window(last + 1)


def test_weighted_ridge_matches_independent_solve() -> None:
    """G6: minimise sum w (y - X b)^2 + penalty * |b_penalised|^2. Checked against an
    augmented least-squares system solved by numpy.linalg.lstsq."""
    rng = np.random.default_rng(20261002)
    n, p = 200, 6
    X = np.column_stack([np.ones(n), rng.normal(size=(n, p - 1))])
    y = X @ rng.normal(size=p) + rng.normal(scale=0.3, size=n)
    w = rng.uniform(0.2, 1.0, size=n)
    lam = 3.7
    got = cv.weighted_ridge(X, y, w, lam, unpenalized=(0,))
    sw = np.sqrt(w)
    pen = np.sqrt(lam) * np.eye(p)[1:]  # intercept unpenalised
    A = np.vstack([X * sw[:, None], pen])
    b = np.concatenate([y * sw, np.zeros(p - 1)])
    want = np.linalg.lstsq(A, b, rcond=None)[0]
    assert got == pytest.approx(want, rel=1e-9, abs=1e-12)


def test_weighted_ridge_is_deterministic() -> None:
    rng = np.random.default_rng(1)
    X, y, w = rng.normal(size=(50, 4)), rng.normal(size=50), np.ones(50)
    a = cv.weighted_ridge(X, y, w, 1.0)
    b = cv.weighted_ridge(X, y, w, 1.0)
    assert a.tobytes() == b.tobytes()


def test_ridge_penalty_is_not_set_yet() -> None:
    """Q1 (2026-10-02): no initial penalty in the spec; it comes from BT-02."""
    with pytest.raises(NotImplementedError, match="G6"):
        cv.g6_penalty()


def test_shrink_rejects_negative_inputs() -> None:
    with pytest.raises(ValueError):
        cv.shrink(0.1, -1, 0.0, 10)
    with pytest.raises(ValueError):
        cv.shrink(0.1, 5, 0.0, 0)
    assert math.isnan(cv.shrink(float("nan"), 0, 0.2, 10)) is False
