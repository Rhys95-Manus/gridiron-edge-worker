"""Logistic regression by Newton's method (IRLS), for COA-02's p_go model and MTC-03's
OL-absence factor. numpy only, no randomness.

Columns are scaled by their standard deviation for the solve (a constant column is left as is)
and the coefficients scaled back. Iteration stops when a Newton step no longer lowers the
deviance, so there is no tolerance setting; standard errors come from the inverse Hessian at
the solution."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]


@dataclass(frozen=True)
class LogitFit:
    coef: FloatArray
    se: FloatArray
    n: int
    events: int  # rows with y = 1
    deviance: float


def _deviance(eta: FloatArray, y: FloatArray, w: FloatArray) -> float:
    # -2 log likelihood with log p = -log(1 + e^-eta), log(1 - p) = -log(1 + e^eta)
    ll = -(y * np.logaddexp(0.0, -eta) + (1 - y) * np.logaddexp(0.0, eta))
    return float(-2.0 * np.dot(w, ll))


def fit_logistic(
    X: FloatArray,
    y: FloatArray,
    offset: FloatArray | None = None,
    w: FloatArray | None = None,
) -> LogitFit:
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    n = X.shape[0]
    off = np.zeros(n) if offset is None else np.asarray(offset, dtype=np.float64)
    wt = np.ones(n) if w is None else np.asarray(w, dtype=np.float64)
    scale = X.std(axis=0)
    scale[scale == 0] = 1.0
    Z = X / scale
    b = np.zeros(Z.shape[1])
    dev = _deviance(Z @ b + off, y, wt)

    def hessian(beta: FloatArray) -> tuple[FloatArray, FloatArray]:
        p = 1.0 / (1.0 + np.exp(-(Z @ beta + off)))
        hw = wt * p * (1 - p)
        return (Z.T * hw) @ Z, Z.T @ (wt * (y - p))

    while True:
        H, grad = hessian(b)
        nb = b + np.linalg.solve(H, grad)
        nd = _deviance(Z @ nb + off, y, wt)
        if not nd < dev:
            break
        b, dev = nb, nd
    H, _ = hessian(b)
    cov = np.linalg.inv(H)
    return LogitFit(
        coef=b / scale,
        se=np.sqrt(np.diag(cov)) / scale,
        n=n,
        events=int(y.sum()),
        deviance=dev,
    )
