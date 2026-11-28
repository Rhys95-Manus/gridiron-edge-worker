"""PRV-09 strike grid, PRV-10 walk-forward scoring and family selection, PRV-11 calibration
checks and PRV-12's log-loss clip.

PRV-09: "Receptions X = 1 to 14. Receiving yards X = 10, 15, 20, 25, 30, 40, 50, 55, 60, 65, 70,
then every 10 to 190. Rushing yards X = 5, 10, 15, 20, 25, 30, 40, 45, 50, 60, 65, 70, then
every 10 to 180. Only pairs with 0.03 ≤ p ≤ 0.97 are scored."

PRV-10 (sync #8): "For each stat, the selected family is the candidate with the lowest log loss
summed over the 2022-2024 walk-forward pairs on the PRV-09 strike grid, with p clipped per
PRV-12. For selection and for PRV-11, the 0.03 ≤ p ≤ 0.97 filter uses the Poisson baseline's
p, so every candidate is scored on the same pairs."

PRV-11: "Calibration uses 10 equal-width probability bins. At least 1,000 scored pairs and at
least 50 per bin used. Logistic recalibration slope between 0.85 and 1.15. Absolute
calibration-in-the-large at most 0.02. Every bin with at least 50 pairs within max(0.05, 2.58 x
clustered SE) of its mean p, with standard errors clustered by player-game. Brier score no
worse than the Poisson baseline's."

PRV-12: "For scoring only, p is clipped to [ε, 1 - ε] with ε = 1e-6; logged probabilities are
not clipped."

Rulings 2026-11-27 (session 7b): the yards stats' Poisson baseline is Poisson(μ) on yards; a pair
is scored only when every candidate prices it and the Poisson p passes the filter;
calibration-in-the-large is mean(y) - mean(p); the recalibration slope and intercept come from
a logistic regression of y on logit(p clipped per PRV-12), with standard errors clustered by
player-game (CR0 sandwich, no small-sample factor).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt
import polars as pl

from ge.config import load_params
from ge.fit.logistic import fit_logistic
from ge.pricer_v0.distributions import (
    CompoundReceivingYards,
    CompoundRushingYards,
    NegativeBinomial,
    Poisson,
    generator,
)
from ge.pricer_v0.fitting import WindowFit
from ge.pricer_v0.reasons import PricerUnpriced
from ge.pricer_v0.training import YardsPools

Arr = npt.NDArray[np.float64]


def _pv0() -> Any:
    return load_params().pricer_v0


def strike_grid(stat: str) -> tuple[int, ...]:
    """PRV-09: the calibration strikes X for a stat."""
    pv = _pv0()

    def v(name: str) -> int:
        return int(getattr(pv, name).value)

    if stat == "receptions":
        return tuple(
            range(v("prv_09_receptions_min_strike"), v("prv_09_receptions_max_strike") + 1)
        )
    names = {"receiving_yards": "rec_yards", "rushing_yards": "rush_yards"}
    if stat not in names:
        raise ValueError(f"PRV-09: no strike grid for {stat!r}")
    prefix = f"prv_09_{names[stat]}_strike_"
    step, top = f"prv_09_{names[stat]}_step", f"prv_09_{names[stat]}_max_strike"
    listed = []
    i = 1
    while hasattr(pv, f"{prefix}{i}"):
        listed.append(v(f"{prefix}{i}"))
        i += 1
    return tuple(listed) + tuple(range(listed[-1] + v(step), v(top) + 1, v(step)))


def clip(p: Any) -> Arr:
    """PRV-12: p clipped to [ε, 1 - ε] for scoring only."""
    eps = float(_pv0().prv_12_log_loss_clip_eps.value)
    return np.clip(np.asarray(p, dtype=np.float64), eps, 1 - eps)


def log_loss(p: Any, y: Any) -> float:
    """PRV-10/PRV-12: summed log loss with p clipped."""
    pc = clip(p)
    yy = np.asarray(y, dtype=np.float64)
    return -math.fsum((yy * np.log(pc) + (1 - yy) * np.log(1 - pc)).tolist())


def pair_rows(
    rows: pl.DataFrame,
    strikes: Sequence[int],
    ps: Mapping[str, Sequence[Sequence[float] | None]],
) -> pl.DataFrame:
    """One pair per (player-game, strike): y = 1 when actual ≥ X (PRV-01's YES), and each
    family's p (null where that family leaves the player unpriced). `ps[family][i]` is row i's
    p ladder over `strikes`. `cluster` identifies the player-game (PRV-11)."""
    n, k = rows.height, len(strikes)
    rep = rows.select("game_id", "team", "gsis_id", "group", "actual")[
        pl.Series(np.repeat(np.arange(n, dtype=np.int64), k))
    ]
    strike = np.tile(np.asarray(strikes, dtype=np.int64), n)
    out = rep.with_columns(
        pl.Series("strike", strike),
        (pl.col("actual") >= pl.Series(strike)).cast(pl.Int8).alias("y"),
        pl.concat_str(["game_id", "team", "gsis_id"], separator="|").alias("cluster"),
    )
    cols = []
    for fam, ladders in ps.items():
        if len(ladders) != n:
            raise ValueError(f"PRV-10: {fam} has {len(ladders)} ladders for {n} rows")
        flat: list[float | None] = []
        for lad in ladders:
            if lad is None:
                flat.extend([None] * k)
            else:
                if len(lad) != k:
                    raise ValueError(f"PRV-10: {fam} ladder has {len(lad)} strikes, not {k}")
                flat.extend(float(x) for x in lad)
        cols.append(pl.Series(f"p_{fam}", flat, dtype=pl.Float64))
    return out.with_columns(cols)


def scored_pairs(pairs: pl.DataFrame, families: Sequence[str]) -> pl.DataFrame:
    """PRV-09/PRV-10: pairs whose Poisson-baseline p is within [0.03, 0.97] and that every
    candidate prices (ruling 2026-11-27)."""
    pv = _pv0()
    lo, hi = float(pv.prv_09_min_scored_p.value), float(pv.prv_09_max_scored_p.value)
    keep = pl.col("p_poisson").is_between(lo, hi, closed="both")
    for f in families:
        keep = keep & pl.col(f"p_{f}").is_not_null()
    return pairs.filter(keep)


def selection_table(pairs: pl.DataFrame, families: Sequence[str]) -> pl.DataFrame:
    """PRV-10: each candidate's log loss summed over the scored pairs, lowest first."""
    y = pairs["y"].to_numpy()
    rows = [
        {
            "family": f,
            "n_pairs": pairs.height,
            "log_loss_sum": log_loss(pairs[f"p_{f}"].to_numpy(), y),
        }
        for f in families
    ]
    t = pl.DataFrame(
        rows, schema={"family": pl.Utf8, "n_pairs": pl.Int64, "log_loss_sum": pl.Float64}
    )
    return t.with_columns((pl.col("log_loss_sum") / pl.col("n_pairs")).alias("log_loss_mean")).sort(
        "log_loss_sum", "family"
    )


# ---- PRV-11 ----


def _cluster_ids(cluster: Any) -> npt.NDArray[np.int64]:
    _, inv = np.unique(np.asarray(cluster), return_inverse=True)
    return np.asarray(inv, dtype=np.int64)


def clustered_bin_se(y: Any, cluster: Any) -> float:
    """PRV-11: standard error of a bin's observed rate, clustered by player-game (CR0):
    sqrt(Σ_c (Σ_{i in c} (y_i - ȳ))²) / n."""
    yy = np.asarray(y, dtype=np.float64)
    if yy.size == 0:
        return math.nan
    resid = yy - yy.mean()
    sums = np.bincount(_cluster_ids(cluster), weights=resid)
    return math.sqrt(float(np.sum(sums**2))) / yy.size


def _bin_index(p: Arr, n_bins: int) -> npt.NDArray[np.int64]:
    return np.minimum(np.floor(p * n_bins).astype(np.int64), n_bins - 1)


def reliability(p: Any, y: Any, cluster: Any, *, z: float) -> pl.DataFrame:
    """PRV-11's equal-width bins: n, mean p, observed rate, Wilson interval at `z`, the
    clustered SE, the tolerance max(floor, z_prv11 x SE), whether the bin is used (n ≥ the
    PRV-11 minimum) and whether it is within tolerance."""
    pv = _pv0()
    n_bins = int(pv.prv_11_probability_bins.value)
    min_bin = int(pv.prv_11_min_pairs_per_bin.value)
    floor_ = float(pv.prv_11_bin_tolerance_floor.value)
    z11 = float(pv.prv_11_bin_tolerance_z.value)
    pp = np.asarray(p, dtype=np.float64)
    yy = np.asarray(y, dtype=np.float64)
    cc = np.asarray(cluster)
    b = _bin_index(pp, n_bins)
    rows = []
    for i in range(n_bins):
        m = b == i
        n = int(m.sum())
        if n == 0:
            rows.append(
                {
                    "bin": i,
                    "lo": i / n_bins,
                    "hi": (i + 1) / n_bins,
                    "n": 0,
                    "used": False,
                    "within": False,
                }
            )
            continue
        mean_p = float(pp[m].mean())
        obs = float(yy[m].mean())
        se = clustered_bin_se(yy[m], cc[m])
        tol = max(floor_, z11 * se)
        denom = 1 + z * z / n
        centre = (obs + z * z / (2 * n)) / denom
        half = z * math.sqrt(obs * (1 - obs) / n + z * z / (4 * n * n)) / denom
        used = n >= min_bin
        rows.append(
            {
                "bin": i,
                "lo": i / n_bins,
                "hi": (i + 1) / n_bins,
                "n": n,
                "mean_p": mean_p,
                "observed": obs,
                "wilson_lo": centre - half,
                "wilson_hi": centre + half,
                "clustered_se": se,
                "tolerance": tol,
                "used": used,
                "within": used and abs(obs - mean_p) <= tol,
            }
        )
    schema = {
        "bin": pl.Int64,
        "lo": pl.Float64,
        "hi": pl.Float64,
        "n": pl.Int64,
        "mean_p": pl.Float64,
        "observed": pl.Float64,
        "wilson_lo": pl.Float64,
        "wilson_hi": pl.Float64,
        "clustered_se": pl.Float64,
        "tolerance": pl.Float64,
        "used": pl.Boolean,
        "within": pl.Boolean,
    }
    return pl.DataFrame(rows, schema=schema)


@dataclass(frozen=True)
class Recalibration:
    """PRV-11 logistic recalibration: logit P(y = 1) = intercept + slope x logit(p)."""

    intercept: float
    slope: float
    intercept_se: float
    slope_se: float


def recalibration(p: Any, y: Any, cluster: Any) -> Recalibration:
    """PRV-11: logistic regression of y on logit(p clipped per PRV-12) by IRLS
    (ge.fit.logistic), with a CR0 sandwich covariance clustered by player-game."""
    pc = clip(p)
    x = np.log(pc / (1 - pc))
    yy = np.asarray(y, dtype=np.float64)
    X = np.column_stack([np.ones_like(x), x])
    beta = fit_logistic(X, yy).coef
    # Polish with Newton steps on the unscaled problem until a step no longer shrinks (no
    # tolerance setting): fit_logistic stops when the deviance stops falling, which leaves the
    # coefficients about 1e-8 short of the maximum.
    last = math.inf
    while True:
        q = 1.0 / (1.0 + np.exp(-(X @ beta)))
        step = np.linalg.solve((X.T * (q * (1 - q))) @ X, X.T @ (yy - q))
        size = float(np.max(np.abs(step)))
        if not size < last:
            break
        beta, last = beta + step, size
    q = 1.0 / (1.0 + np.exp(-(X @ beta)))
    H = (X.T * (q * (1 - q))) @ X
    scores = X * (yy - q)[:, None]
    ids = _cluster_ids(cluster)
    g = np.zeros((int(ids.max()) + 1, 2))
    np.add.at(g, ids, scores)
    Hinv = np.linalg.inv(H)
    cov = Hinv @ (g.T @ g) @ Hinv
    se = np.sqrt(np.diag(cov))
    return Recalibration(
        intercept=float(beta[0]),
        slope=float(beta[1]),
        intercept_se=float(se[0]),
        slope_se=float(se[1]),
    )


@dataclass(frozen=True)
class Prv11Result:
    n_pairs: int
    bins: pl.DataFrame
    recal: Recalibration
    citl: float
    brier: float
    brier_baseline: float
    checks: Mapping[str, bool]

    @property
    def passed(self) -> bool:
        return all(self.checks.values())


def prv11(
    p: Any, y: Any, cluster: Any, *, p_baseline: Any, z_report: float = math.nan
) -> Prv11Result:
    """PRV-11 for one stat and family on its scored pairs: the bins, the recalibration, CITL =
    mean(y) - mean(p), Brier against the Poisson baseline's, and each criterion's pass/fail.
    `z_report` only sets the Wilson interval shown in the bins table."""
    pv = _pv0()
    pp = np.asarray(p, dtype=np.float64)
    yy = np.asarray(y, dtype=np.float64)
    pb = np.asarray(p_baseline, dtype=np.float64)
    bins = reliability(pp, yy, cluster, z=z_report if math.isfinite(z_report) else 0.0)
    rc = recalibration(pp, yy, cluster)
    citl = float(yy.mean() - pp.mean())
    brier = float(np.mean((pp - yy) ** 2))
    brier_b = float(np.mean((pb - yy) ** 2))
    used = bins.filter(pl.col("used"))
    checks = {
        "min_pairs": pp.size >= int(pv.prv_11_min_scored_pairs.value),
        "slope": float(pv.prv_11_min_recalibration_slope.value)
        <= rc.slope
        <= float(pv.prv_11_max_recalibration_slope.value),
        "citl": abs(citl) <= float(pv.prv_11_max_abs_calibration_in_the_large.value),
        "bins": bool(used["within"].all()) if used.height else False,
        "brier": brier <= brier_b,
    }
    return Prv11Result(
        n_pairs=int(pp.size),
        bins=bins,
        recal=rc,
        citl=citl,
        brier=brier,
        brier_baseline=brier_b,
        checks=checks,
    )


# ---- each candidate's p ladder for a set of player-games ----

RowKey = tuple[str, str, str]  # (game_id, team, gsis_id)
Ladder = tuple[float, ...] | None


def family_ladders(
    rows: pl.DataFrame,
    stat: str,
    fit: WindowFit,
    pools: YardsPools,
    *,
    model_version: str,
    receptions_family: str | None = None,
    rec_mu: Mapping[RowKey, float] | None = None,
) -> dict[str, list[Ladder]]:
    """PRV-04 to PRV-07: every candidate's p over the PRV-09 grid for each row (game_id, team,
    gsis_id, group, mu, carries_mean), plus the Poisson baseline; None where the family leaves
    the player unpriced (no fitted (family, group), or the compound model's mu_not_positive).
    The receiving compound model draws N from `receptions_family` (the selected PRV-04 family)
    with mean = the player's receptions μ from `rec_mu`; Monte Carlo draws are seeded per PRV-07
    with `model_version`."""
    from ge.pricer_v0.fitting import FAMILIES

    strikes = strike_grid(stat)
    n_draws = int(_pv0().prv_07_monte_carlo_draws.value)
    out: dict[str, list[Ladder]] = {f: [] for f in ("poisson", *FAMILIES[stat])}
    if stat == "receiving_yards" and receptions_family not in ("poisson", "negative_binomial"):
        raise ValueError(f"PRV-05: receptions family {receptions_family!r} is not a PRV-04 family")
    for r in rows.iter_rows(named=True):
        g, mu = str(r["group"]), float(r["mu"])
        key = (str(r["game_id"]), str(r["team"]), str(r["gsis_id"]))
        out["poisson"].append(Poisson().p_over(mu, strikes))
        if stat == "receptions":
            size = fit.nb_size.get(g)
            out["negative_binomial"].append(
                None if size is None else NegativeBinomial(size).p_over(mu, strikes)
            )
            continue
        er = fit.empirical.get((stat, g))
        out["empirical_ratio"].append(None if er is None else er.p_over(mu, strikes))
        rng = generator(key[0], model_version, key[2], stat)
        if stat == "receiving_yards":
            h = fit.hurdle.get(g)
            out["hurdle_gamma"].append(None if h is None else h.p_over(mu, strikes))
            n_family: Poisson | NegativeBinomial | None
            if receptions_family == "poisson":
                n_family = Poisson()
            else:
                size = fit.nb_size.get(g)
                n_family = None if size is None else NegativeBinomial(size)
            mu_rec = None if rec_mu is None else rec_mu.get(key)
            pool = pools.per_reception.get(g, ())
            if n_family is None or mu_rec is None or g not in fit.compound_receiving or not pool:
                out["compound"].append(None)
            else:
                got = CompoundReceivingYards(n_family, pool).p_over(
                    mu, mu_rec, strikes, rng, n_draws
                )
                out["compound"].append(None if isinstance(got, PricerUnpriced) else got)
        else:
            s = fit.shifted.get(g)
            out["shifted_gamma"].append(None if s is None else s.p_over(mu, strikes))
            size = fit.carries_size.get(g)
            pool = pools.per_carry.get(g, ())
            if size is None or not pool:
                out["compound"].append(None)
            else:
                got = CompoundRushingYards(size, pool).p_over(
                    mu, float(r["carries_mean"]), strikes, rng, n_draws
                )
                out["compound"].append(None if isinstance(got, PricerUnpriced) else got)
    return out
