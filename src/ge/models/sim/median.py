"""PRJ-01b: the interpolated (mid-distribution) median of whole-number simulation results."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt


def interpolated_median(x: npt.ArrayLike) -> float:
    """PRJ-01b: the value s at which P(X < s) + 1/2 P(X = s) = 0.5, interpolated linearly
    between whole numbers. If that holds over a run of whole numbers, s is the run's midpoint
    (ruling B5, 2026-10-23).

    With n results, 2 n P(X < k) + n P(X = k) = 2 less(k) + count(k) is an integer, so the
    comparison with 0.5 (= n in those units) is exact."""
    a = np.asarray(x)
    if a.size == 0:
        raise ValueError("PRJ-01b: no simulation results")
    if not np.all(np.isfinite(a)) or not np.all(a == np.round(a)):
        raise ValueError("PRJ-01b: margins and totals must be whole numbers")
    vals, counts = np.unique(a.astype(np.int64), return_counts=True)
    n = int(a.size)
    ks = np.arange(int(vals[0]), int(vals[-1]) + 1)
    cnt = np.zeros(ks.size, dtype=np.int64)
    cnt[vals - vals[0]] = counts
    less = np.concatenate(([0], np.cumsum(cnt)[:-1]))
    g = 2 * less + cnt  # 2 n * mid-distribution function at each whole number
    hits = np.flatnonzero(g == n)
    if hits.size:
        return float((ks[hits[0]] + ks[hits[-1]]) / 2)
    i = int(np.searchsorted(g, n))  # g is non-decreasing; g[0] < n < g[-1]
    lo, hi = int(g[i - 1]), int(g[i])
    return float(ks[i - 1] + (n - lo) / (hi - lo))
