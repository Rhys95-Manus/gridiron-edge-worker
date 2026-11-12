"""Regressions with standard errors clustered by team-game (ruling B8, 2026-10-23), for the
PRJ-02 rating-tilt slopes and the MTC-05 / ENV weather coefficients: their predictors are
game-level, shared by every play in a team-game, so play-level classical errors are too small.

Sandwich estimator V = B^-1 M B^-1, with M the sum over clusters of the outer product of each
cluster's score sum, and the usual small-sample factors: G / (G - 1) for logistic regression,
G / (G - 1) x (N - 1) / (N - K) for least squares (the CR1 conventions). The classical standard
error is returned beside it for the report. numpy only, no randomness."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
import numpy.typing as npt

from ge.fit.logistic import fit_logistic

FloatArray = npt.NDArray[np.float64]


@dataclass(frozen=True)
class ClusteredFit:
    coef: FloatArray
    se: FloatArray  # clustered by team-game
    se_classical: FloatArray
    n: int
    clusters: int
    events: int | None  # logistic: rows with y = 1


def _cluster_meat(scores: FloatArray, groups: npt.ArrayLike) -> tuple[FloatArray, int]:
    _, inv = np.unique(np.asarray(groups), return_inverse=True)
    g = int(inv.max()) + 1
    sums = np.zeros((g, scores.shape[1]))
    np.add.at(sums, inv, scores)
    return sums.T @ sums, g


def logit_clustered(X: FloatArray, y: FloatArray, groups: npt.ArrayLike) -> ClusteredFit:
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    base = fit_logistic(X, y)
    p = 1.0 / (1.0 + np.exp(-(X @ base.coef)))
    bread = np.linalg.inv((X.T * (p * (1 - p))) @ X)
    meat, g = _cluster_meat(X * (y - p)[:, None], groups)
    if g < 2:
        raise ValueError("clustered standard errors need at least two team-games")
    v = bread @ meat @ bread * (g / (g - 1))
    return ClusteredFit(
        coef=base.coef,
        se=np.sqrt(np.diag(v)),
        se_classical=np.sqrt(np.diag(bread)),
        n=int(y.size),
        clusters=g,
        events=int(y.sum()),
    )


def ols_clustered(X: FloatArray, y: FloatArray, groups: npt.ArrayLike) -> ClusteredFit:
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    n, k = X.shape
    bread = np.linalg.inv(X.T @ X)
    coef = bread @ (X.T @ y)
    e = y - X @ coef
    meat, g = _cluster_meat(X * e[:, None], groups)
    if g < 2:
        raise ValueError("clustered standard errors need at least two team-games")
    v = bread @ meat @ bread * (g / (g - 1)) * ((n - 1) / (n - k))
    s2 = float(e @ e) / (n - k)
    return ClusteredFit(
        coef=coef,
        se=np.sqrt(np.diag(v)),
        se_classical=np.sqrt(np.diag(bread) * s2),
        n=n,
        clusters=g,
        events=None,
    )


def season_dummies(seasons: npt.ArrayLike) -> tuple[FloatArray, list[int]]:
    """One intercept column per season (no common intercept)."""
    s = np.asarray(seasons)
    levels = sorted(int(v) for v in np.unique(s))
    return np.column_stack([(s == lv).astype(np.float64) for lv in levels]), levels


def no_signal(coef: float, se: float, confidence: float) -> bool:
    """BT-02 "No signal": the two-sided interval at `confidence` includes 0."""
    z = NormalDist().inv_cdf(0.5 + confidence / 2)
    return bool(abs(coef) <= z * se)
