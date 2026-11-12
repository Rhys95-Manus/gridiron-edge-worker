"""PRJ-02 xpass(state), cp(state) and wp(state): logistic models distilled from nflverse's own
`xpass`, `cp` and `wp` (spec synced 2026-10-23; form ruled D4, wp added by ruling E1,
2026-10-24).

A fractional logistic fit (quasi-likelihood: the logistic deviance with nflverse's probability
as the target) on the spec's features. Down, quarter and pass_location enter as indicators
(one level dropped, a common intercept kept); every other feature as a linear and a squared
term. xpass and wp take distance as a linear and a squared term within each down (ruling
2026-10-25), and xpass adds an indicator for each distance bin within each down (ruling
2026-10-29). Rows are plays where nflverse's value is non-null. Agreement with nflverse on the
training plays (correlation, mean absolute difference, and calibration by decile of the
fitted value) is returned for the report; no term is added beyond the ruled form."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import polars as pl

from ge.fit.logistic import fit_logistic
from ge.models.sim.settings import load_sim

FloatArray = npt.NDArray[np.float64]

DISTILL_FEATURES: dict[str, tuple[str, ...]] = {
    "xpass": (
        "down",
        "ydstogo",
        "yardline_100",
        "qtr",
        "half_seconds_remaining",
        "score_differential",
        "wp",
        "posteam_timeouts_remaining",
        "defteam_timeouts_remaining",
    ),
    "cp": ("air_yards", "yardline_100", "ydstogo", "down", "pass_location"),
    # ruling E1 (2026-10-24): the simulation needs wp(state) for xpass, COA-04 and G5; no
    # betting-line features, as for xpass
    "wp": (
        "score_differential",
        "game_seconds_remaining",
        "half_seconds_remaining",
        "yardline_100",
        "down",
        "ydstogo",
        "posteam_timeouts_remaining",
        "defteam_timeouts_remaining",
        "qtr",
    ),
}
CATEGORICAL = ("down", "qtr", "pass_location")
# Ruling 2026-10-25: in xpass and wp, ydstogo enters linear and squared within each down (one
# pair per down level, replacing the overall pair), so short yardage can differ by down.
INTERACTIONS: dict[str, tuple[str, str]] = {"xpass": ("ydstogo", "down"), "wp": ("ydstogo", "down")}
# Ruling 2026-10-29 (P3): xpass also carries an indicator for each distance bin within each down
# (togo_bin_index; the last bin is the reference), named ydstogo_bin=<k>|down=<level>.
BIN_INDICATORS: dict[str, tuple[str, str]] = {"xpass": ("ydstogo", "down")}
TOGO_BIN = "ydstogo_bin"


@dataclass(frozen=True)
class Agreement:
    corr: float
    mae: float
    deciles: list[tuple[float, float, int]]  # (mean fitted, mean nflverse, rows)


@dataclass(frozen=True)
class DistillFit:
    coef: FloatArray
    terms: list[str]
    n: int
    agreement: Agreement


def _agreement(fitted: FloatArray, target: FloatArray) -> Agreement:
    order = np.argsort(fitted, kind="stable")
    deciles = []
    for chunk in np.array_split(order, 10):
        deciles.append((float(fitted[chunk].mean()), float(target[chunk].mean()), int(chunk.size)))
    return Agreement(
        corr=float(np.corrcoef(fitted, target)[0, 1]),
        mae=float(np.mean(np.abs(fitted - target))),
        deciles=deciles,
    )


def distill_fit(X: FloatArray, target: FloatArray, terms: list[str] | None = None) -> DistillFit:
    """Fractional logistic fit of `target` (probabilities in [0, 1]) on design X."""
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(target, dtype=np.float64)
    if np.any((y < 0) | (y > 1)):
        raise ValueError("PRJ-02: distillation targets must be probabilities")
    fit = fit_logistic(X, y)
    fitted = 1.0 / (1.0 + np.exp(-(X @ fit.coef)))
    names = terms if terms is not None else [f"x{i}" for i in range(X.shape[1])]
    return DistillFit(coef=fit.coef, terms=names, n=int(y.size), agreement=_agreement(fitted, y))


def design(rows: pl.DataFrame, model: str) -> tuple[FloatArray, list[str], pl.DataFrame]:
    """PRJ-02 (D4): the design matrix for `model` (xpass or cp) and its term names; rows with any
    missing feature or target are dropped. Levels are taken from the data, sorted, and the first
    is the reference."""
    feats = DISTILL_FEATURES[model]
    d = rows.drop_nulls([*feats, model])
    inter = INTERACTIONS.get(model)
    cols: list[FloatArray] = [np.ones(d.height)]
    names = ["intercept"]
    for f in feats:
        if f in CATEGORICAL:
            levels = sorted(d[f].cast(pl.String).unique().to_list())
            for lv in levels[1:]:
                cols.append((d[f].cast(pl.String) == lv).to_numpy().astype(np.float64))
                names.append(f"{f}={lv}")
        elif inter is None or f != inter[0]:
            v = d[f].to_numpy().astype(np.float64)
            cols.extend([v, v * v])
            names.extend([f, f"{f}^2"])
    if inter is not None:
        num, cat = inter
        v = d[num].to_numpy().astype(np.float64)
        for lv in sorted(d[cat].cast(pl.String).unique().to_list()):
            ind = (d[cat].cast(pl.String) == lv).to_numpy().astype(np.float64)
            cols.extend([v * ind, v * v * ind])
            names.extend([f"{num}|{cat}={lv}", f"{num}^2|{cat}={lv}"])
    bins = BIN_INDICATORS.get(model)
    if bins is not None:
        num, cat = bins
        k = togo_bin_index(d[num].to_numpy())
        ref = len(load_sim().distill.xpass_togo_bin_upper.value)
        for lv in sorted(d[cat].cast(pl.String).unique().to_list()):
            ind = (d[cat].cast(pl.String) == lv).to_numpy()
            for b in range(ref):
                col = (ind & (k == b)).astype(np.float64)
                if col.any():  # levels are taken from the data
                    cols.append(col)
                    names.append(f"{TOGO_BIN}={b}|{cat}={lv}")
    return np.column_stack(cols), names, d


def togo_bin_index(ydstogo: FloatArray) -> npt.NDArray[np.int64]:
    """PRJ-02 xpass distance bin (ruling 2026-10-29): the index of the first configured upper
    edge (config/sim.yaml distill.xpass_togo_bin_upper) at or above ydstogo; beyond the last
    edge, the reference bin len(edges)."""
    edges = np.asarray(load_sim().distill.xpass_togo_bin_upper.value, dtype=np.float64)
    v = np.asarray(ydstogo, dtype=np.float64)
    return np.asarray(np.searchsorted(edges, v, side="left"), dtype=np.int64)


def predict(coef: dict[str, float], rows: pl.DataFrame) -> FloatArray:
    """Evaluate a distilled model from its stored terms (as written to the fitted file)."""
    eta = np.full(rows.height, coef["intercept"])
    for term, b in coef.items():
        if term == "intercept":
            continue
        if "|" in term:  # distance within a down (rulings 2026-10-25, 2026-10-29)
            base, cond = term.split("|", 1)
            f, lv = cond.split("=", 1)
            ind = (rows[f].cast(pl.String) == lv).to_numpy().astype(np.float64)
            if base.startswith(f"{TOGO_BIN}="):
                k = int(base.split("=", 1)[1])
                eta += b * ind * (togo_bin_index(rows["ydstogo"].to_numpy()) == k)
                continue
            power = 2 if base.endswith("^2") else 1
            v = rows[base.removesuffix("^2")].to_numpy().astype(np.float64)
            eta += b * ind * v**power
        elif "=" in term:
            f, lv = term.split("=", 1)
            eta += b * (rows[f].cast(pl.String) == lv).to_numpy().astype(np.float64)
        elif term.endswith("^2"):
            v = rows[term[:-2]].to_numpy().astype(np.float64)
            eta += b * v * v
        else:
            eta += b * rows[term].to_numpy().astype(np.float64)
    return np.asarray(1.0 / (1.0 + np.exp(-eta)), dtype=np.float64)
