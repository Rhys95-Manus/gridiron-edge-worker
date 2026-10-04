"""G1-G7 global conventions (docs/MODEL_SPEC.md, "Global conventions").

Pure functions; every constant comes from config/params.yaml. The play filters G5 and G7 live
in ge.metrics.plays as polars expressions."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

import numpy as np
import numpy.typing as npt

from ge.config import load_params

HalfLife = Literal["usage", "efficiency"]
FloatArray = npt.NDArray[np.float64]


def shrink(observed: float, n: float, prior: float, k: float) -> float:
    """G1: (n * observed + k * prior) / (n + k). n may be G3's n_eff. At n = 0 the result is
    the prior whatever `observed` is (no plays: nothing observed)."""
    if n < 0:
        raise ValueError(f"G1: n must be >= 0, got {n}")
    if k <= 0:
        raise ValueError(f"G1: k must be > 0, got {k}")
    if n == 0:
        return prior
    return (n * observed + k * prior) / (n + k)


def half_life(kind: HalfLife) -> float:
    """G3: initial h = 3 games for usage metrics, 6 for efficiency metrics."""
    c = load_params().conventions
    if kind == "usage":
        return float(c.g3_usage_half_life_games.value)
    if kind == "efficiency":
        return float(c.g3_efficiency_half_life_games.value)
    raise ValueError(f"G3: unknown half-life class {kind!r}")


def recency_weights(games_ago: FloatArray, h: float) -> FloatArray:
    """G3: w = 0.5^(g / h), g = 0 for the most recent game."""
    if h <= 0:
        raise ValueError(f"G3: h must be > 0, got {h}")
    return np.power(0.5, np.asarray(games_ago, dtype=np.float64) / h)


def n_eff(weights: FloatArray) -> float:
    """G3: weighted sample size (sum w)^2 / sum w^2; replaces n in G1."""
    w = np.asarray(weights, dtype=np.float64)
    if w.size == 0:
        return 0.0
    return float(w.sum() ** 2 / np.square(w).sum())


def weighted_mean(x: FloatArray, weights: FloatArray) -> float:
    """G3: the recency-weighted observed value that G1 shrinks."""
    w = np.asarray(weights, dtype=np.float64)
    return float((np.asarray(x, dtype=np.float64) * w).sum() / w.sum())


def in_carryover_window(week: int) -> bool:
    """G4: weeks 1-4 use last season's shrunk value as the prior."""
    return week <= int(load_params().conventions.g4_prior_carryover_last_week.value)


def carryover_prior(last_season: float, league: float, *, changed: bool | None) -> float:
    """G4: last season's shrunk value, regressed a further 1/3 toward league average when the
    team has a new play-caller or quarterback. An unknown change raises (user decision
    2026-10-02): the extra regression can't be skipped or applied by assumption."""
    if changed is None:
        raise NotImplementedError(
            "G4: whether the play-caller or quarterback changed is unknown (COA-01 has no "
            "covering row, or no current-season dropbacks yet)"
        )
    if not changed:
        return last_season
    extra = float(load_params().conventions.g4_new_caller_or_qb_extra_regression.value)
    return last_season + extra * (league - last_season)


def weighted_ridge(
    X: FloatArray,
    y: FloatArray,
    w: FloatArray,
    penalty: float,
    unpenalized: Sequence[int] = (),
) -> FloatArray:
    """G6: coefficients minimising sum w (y - X b)^2 + penalty * sum over penalised b^2.
    Closed form (X'WX + penalty * D) b = X'Wy, D = identity with zeros on `unpenalized`
    (e.g. the league intercept). Deterministic: no randomness, one linear solve."""
    if penalty < 0:
        raise ValueError(f"G6: penalty must be >= 0, got {penalty}")
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    w = np.asarray(w, dtype=np.float64)
    d = np.ones(X.shape[1])
    d[list(unpenalized)] = 0.0
    xtw = X.T * w
    return np.asarray(np.linalg.solve(xtw @ X + penalty * np.diag(d), xtw @ y), dtype=np.float64)


def g6_penalty() -> float:
    """G6: the ridge penalty is tuned by cross-validation in BT-02. The spec gives no initial
    value, so there is none to use yet (user decision 2026-10-02)."""
    raise NotImplementedError("G6: ridge penalty from BT-02 (no initial value in the spec)")
