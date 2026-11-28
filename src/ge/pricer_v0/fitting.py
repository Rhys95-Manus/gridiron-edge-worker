"""PRV-04 to PRV-06 distribution parameters by maximum likelihood (PRV-10), per position group,
and the pv0 params_fitted files.

PRV-10 (spec sync #8): "Each family's distribution parameters are fitted by maximum likelihood
on the training window's player-games, each with its point-in-time μ at as_of = kickoff - 24 h
under BT-01." PRV-04 to PRV-06 selection: "Each fitted family needs at least 500 player-games
per position group in its training window." "One r per position group and family, fitted."
"A (family, position group) with fewer than 500 training player-games is not fitted. Players in
that group are unpriced as no_fitted_params for that family."

Rulings 2026-11-27 (session 7b):
- PRV-04 candidate 2 (targets with a shrunk catch rate) is not fitted: no spec ID defines the
  shrunk catch rate. Receptions candidates here are Poisson (nothing to fit) and NB.
- Continuous families use the interval likelihood that matches PRV-07's read-off: a whole
  number y has mass F(y + 0.5) - F(y - 0.5); for the hurdle gamma y <= 0 has mass π and y >= 1
  has F(y + 0.5) - F(max(y - 0.5, 0)).
- Files: config/params_fitted/pv0/<window>.yaml in the v4 FittedFile format (scalar values),
  each empirical-ratio decile edge its own key; the bins' ratios go in
  <window>_empirical_ratio.parquet beside it, whose sha256 is in the edge keys' method text.
- Decile edges: linear interpolation (numpy's default) on the group's training μ; the end
  edges are the min and max μ; tied edges stop the fit.

Optimisers are scipy's defaults (BFGS with the analytic gradient for the NB size, Nelder-Mead
for the gamma families), on log parameters, started from moment estimates of the data; a fit
that does not converge raises. The NB size has a finite maximum only when the data are
over-dispersed against μ (sum of (y - μ)² - y > 0, the score of 1/r at 0); otherwise the
(family, group) is reported not fitted.

Data: nflverse; charting: FTN Data via nflverse; expected points: ffopportunity (ffverse) via
nflverse; data license not stated by the source.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import polars as pl
import yaml
from scipy import optimize
from scipy import special as spf
from scipy import stats as sps

from ge.config import ATTRIBUTION, FITTED_ROOT, FittedFile, _read_yaml, load_params
from ge.pricer_v0.distributions import EmpiricalRatio, HurdleGamma, ShiftedGamma
from ge.pricer_v0.training import YardsPools
from ge.store.holdout import Window

FIT_VERSION = "pv0"
FIT_ROOT = FITTED_ROOT / FIT_VERSION
SIDECAR_SUFFIX = "_empirical_ratio.parquet"
Arr = npt.NDArray[np.float64]

# PRV-04 to PRV-06 candidates fitted here (PRV-04 candidate 2 waits for a catch-rate spec).
FAMILIES: Mapping[str, tuple[str, ...]] = {
    "receptions": ("poisson", "negative_binomial"),
    "receiving_yards": ("compound", "hurdle_gamma", "empirical_ratio"),
    "rushing_yards": ("compound", "shifted_gamma", "empirical_ratio"),
}
_STAT_SPEC = {"receptions": "PRV-04", "receiving_yards": "PRV-05", "rushing_yards": "PRV-06"}
# "deciles": tenths of the training μ distribution, by definition of the word.
_DECILE_LEVELS = np.linspace(0.0, 1.0, 11)


@dataclass(frozen=True)
class NotFitted:
    """A (family, group) with no fitted value, and why."""

    reason: str


def _arr(x: Any) -> Arr:
    return np.asarray(x, dtype=np.float64)


def _min_n() -> int:
    return int(load_params().pricer_v0.prv_min_player_games_per_position_group.value)


# ---- negative binomial size ----


def _nb_negll_and_grad(t: Arr, y: Arr, mu: Arr) -> tuple[float, Arr]:
    r = math.exp(float(t[0]))
    ll = np.sum(
        spf.gammaln(y + r)
        - spf.gammaln(r)
        - spf.gammaln(y + 1)
        + r * np.log(r / (r + mu))
        + y * np.log(mu / (r + mu))
    )
    d_r = np.sum(spf.digamma(y + r) - spf.digamma(r) + np.log(r / (r + mu)) + (mu - y) / (r + mu))
    return -float(ll), np.array([-float(d_r) * r])


def nb_size_mle(y: Any, mu: Any) -> float | NotFitted:
    """PRV-04 (and PRV-06's carries): the NB size r maximising Σ log NB(y | mean μ, size r)."""
    y_, mu_ = _arr(y), _arr(mu)
    excess = float(np.sum((y_ - mu_) ** 2 - y_))
    if not excess > 0:
        return NotFitted(
            f"not over-dispersed against mu (sum((y - mu)^2 - y) = {excess:.6g}): "
            "no finite NB size maximises the likelihood"
        )
    r0 = float(np.sum(mu_**2)) / excess
    res = optimize.minimize(
        _nb_negll_and_grad, np.array([math.log(r0)]), args=(y_, mu_), jac=True, method="BFGS"
    )
    if not res.success:
        raise RuntimeError(f"PRV-04: NB size fit did not converge: {res.message}")
    return math.exp(float(res.x[0]))


# ---- gamma interval likelihoods ----


def _log_gamma_mass(lo: Arr, hi: Arr, shape: float, scale: Arr) -> Arr:
    """log P(lo < G <= hi) for G ~ Gamma(shape, scale), lo >= 0, using the upper tail where
    the interval lies above the mean (keeps precision in both tails)."""
    upper = lo > shape * scale
    with np.errstate(divide="ignore"):
        mass = np.where(
            upper,
            sps.gamma.sf(lo, shape, scale=scale) - sps.gamma.sf(hi, shape, scale=scale),
            sps.gamma.cdf(hi, shape, scale=scale) - sps.gamma.cdf(lo, shape, scale=scale),
        )
        return np.where(mass > 0, np.log(np.where(mass > 0, mass, 1.0)), -np.inf)


def _minimise(f: Callable[[Arr], float], x0: Arr, spec_id: str, what: str) -> Arr:
    res = optimize.minimize(f, x0, method="Nelder-Mead")
    if not res.success:
        raise RuntimeError(f"{spec_id}: {what} fit did not converge: {res.message}")
    return np.asarray(res.x, dtype=np.float64)


def hurdle_gamma_mle(y: Any, mu: Any) -> tuple[float, float] | NotFitted:
    """PRV-05 hurdle gamma: π = the share of training player-games with receiving yards <= 0
    (its maximum-likelihood value); alpha maximises the interval likelihood of the y >= 1 rows with
    θ = μ / ((1 - π) alpha). Returns (alpha, π)."""
    y_, mu_ = _arr(y), _arr(mu)
    pi = float(np.mean(y_ <= 0))
    pos = y_ > 0
    if not pos.any():
        return NotFitted("no player-game with receiving yards > 0")
    yp, m = y_[pos], mu_[pos] / (1 - pi)
    lo, hi = np.maximum(yp - 0.5, 0.0), yp + 0.5

    def negll(x: Arr) -> float:
        a = math.exp(float(x[0]))
        v = float(np.sum(_log_gamma_mass(lo, hi, a, m / a)))
        return -v if math.isfinite(v) else math.inf

    cv2 = float(np.mean(((yp - m) / m) ** 2))
    if not cv2 > 0:
        return NotFitted("positive receiving yards equal mu / (1 - pi) exactly: no spread")
    x = _minimise(negll, np.array([-math.log(cv2)]), "PRV-05", "hurdle gamma")
    return math.exp(float(x[0])), pi


def shifted_gamma_mle(y: Any, mu: Any) -> tuple[float, float] | NotFitted:
    """PRV-06 shifted gamma: Y = G - s, G ~ Gamma(alpha, θ = (μ + s)/alpha), s >= 0; (alpha, s)
    maximise the interval likelihood. Every y needs y + 0.5 + s > 0, so s is searched above
    max(0, -min(y) - 0.5). Returns (alpha, s)."""
    y_, mu_ = _arr(y), _arr(mu)
    if y_.size == 0:
        return NotFitted("no player-games")
    s_lo = max(0.0, -float(y_.min()) - 0.5)

    def unpack(x: Arr) -> tuple[float, float]:
        return math.exp(float(x[0])), s_lo + math.exp(float(x[1]))

    def negll(x: Arr) -> float:
        a, s = unpack(x)
        lo, hi = np.maximum(y_ - 0.5 + s, 0.0), y_ + 0.5 + s
        v = float(np.sum(_log_gamma_mass(lo, hi, a, (mu_ + s) / a)))
        return -v if math.isfinite(v) else math.inf

    spread = float(np.mean(np.abs(y_ - mu_)))
    if not spread > 0:
        return NotFitted("rushing yards equal mu exactly: no spread")
    s0 = s_lo + spread
    a0 = float(np.mean((mu_ + s0) ** 2) / np.mean((y_ - mu_) ** 2))
    x = _minimise(negll, np.array([math.log(a0), math.log(spread)]), "PRV-06", "shifted gamma")
    return unpack(x)


# ---- empirical ratio ----


def empirical_ratio_fit(mu: Any, actual: Any, spec_id: str = "PRV-05") -> EmpiricalRatio:
    """PRV-05/06 empirical ratio: training rows with μ <= 0 are left out; edges are the
    training μ deciles (linear interpolation, min and max at the ends); each bin holds the
    ratios actual/μ of its rows, in row order, with a μ on an interior edge in the upper bin."""
    mu_, a_ = _arr(mu), _arr(actual)
    keep = mu_ > 0
    mu_, a_ = mu_[keep], a_[keep]
    edges = np.quantile(mu_, _DECILE_LEVELS)
    if np.any(np.diff(edges) <= 0):
        raise ValueError(f"{spec_id}: tied empirical-ratio decile edges {edges.tolist()}")
    bins = np.searchsorted(edges[1:-1], mu_, side="right")
    ratios = a_ / mu_
    per_bin = tuple(tuple(float(r) for r in ratios[bins == b]) for b in range(edges.size - 1))
    return EmpiricalRatio(edges=tuple(float(e) for e in edges), ratios=per_bin)


# ---- one window ----


def _key(spec_id: str, family: str, param: str, stat: str, group: str) -> str:
    return f"fit:{FIT_VERSION}/{spec_id}/{family}/{param}/{stat}/{group}"


def nb_key(group: str) -> str:
    return _key("PRV-04", "negative_binomial", "size", "receptions", group)


def carries_key(group: str) -> str:
    return _key("PRV-06", "compound", "carries_size", "rushing_yards", group)


def per_carry_mean_key(group: str) -> str:
    return _key("PRV-06", "compound", "per_carry_mean", "rushing_yards", group)


def per_reception_mean_key(group: str) -> str:
    return _key("PRV-05", "compound", "per_reception_mean", "receiving_yards", group)


def hurdle_keys(group: str) -> tuple[str, str]:
    return (
        _key("PRV-05", "hurdle_gamma", "alpha", "receiving_yards", group),
        _key("PRV-05", "hurdle_gamma", "zero_mass", "receiving_yards", group),
    )


def shifted_keys(group: str) -> tuple[str, str]:
    return (
        _key("PRV-06", "shifted_gamma", "alpha", "rushing_yards", group),
        _key("PRV-06", "shifted_gamma", "shift", "rushing_yards", group),
    )


def edge_key(stat: str, group: str, i: int) -> str:
    return _key(_STAT_SPEC[stat], "empirical_ratio", f"edge_{i:02d}", stat, group)


@dataclass(frozen=True)
class WindowFit:
    """PRV-04 to PRV-06 fitted values for one PRV-10 window. compound_receiving and
    compound_per_carry_mean hold the window's per-play pool mean for each group the compound
    model may price; `n` is the training player-games behind each fitted key; `missing` says
    why a (family, group) is not fitted."""

    window: str
    test_season: int | None
    seasons: tuple[int, ...]
    nb_size: Mapping[str, float]
    carries_size: Mapping[str, float]
    compound_receiving: Mapping[str, float]
    compound_per_carry_mean: Mapping[str, float]
    hurdle: Mapping[str, HurdleGamma]
    shifted: Mapping[str, ShiftedGamma]
    empirical: Mapping[tuple[str, str], EmpiricalRatio]
    n: Mapping[str, int]
    missing: Mapping[str, str]


def _col(df: pl.DataFrame, name: str) -> Arr:
    return df[name].cast(pl.Float64).to_numpy()


def fit_window(window: Window, rows: Mapping[str, pl.DataFrame], pools: YardsPools) -> WindowFit:
    """PRV-04 to PRV-06 fits for `window` from each stat's training rows (training_rows of the
    window's seasons: group, mu, actual, carries_mean, carries) and the window's yard pools."""
    if pools.window != window.name:
        raise ValueError(f"PRV-10: pools are for {pools.window}, not {window.name}")
    min_n = _min_n()
    nb: dict[str, float] = {}
    carries: dict[str, float] = {}
    comp_rec: dict[str, float] = {}
    comp_rush: dict[str, float] = {}
    hurdle: dict[str, HurdleGamma] = {}
    shifted: dict[str, ShiftedGamma] = {}
    emp: dict[tuple[str, str], EmpiricalRatio] = {}
    n: dict[str, int] = {}
    missing: dict[str, str] = {}

    def too_few(keys: tuple[str, ...], count: int) -> bool:
        if count >= min_n:
            return False
        for k in keys:
            missing[k] = (
                f"fewer than {min_n} training player-games in the position group (n = {count})"
            )
        return True

    def not_fitted(keys: tuple[str, ...], why: NotFitted) -> None:
        for k in keys:
            missing[k] = why.reason

    def groups(stat: str) -> list[tuple[str, pl.DataFrame]]:
        df = rows[stat]
        return [
            (str(g), part) for (g,), part in df.sort("group").group_by("group", maintain_order=True)
        ]

    for g, part in groups("receptions"):
        k = nb_key(g)
        if too_few((k,), part.height):
            continue
        r = nb_size_mle(_col(part, "actual"), _col(part, "mu"))
        if isinstance(r, NotFitted):
            not_fitted((k,), r)
        else:
            nb[k.rsplit("/", 1)[1]] = r
            n[k] = part.height

    for g, part in groups("receiving_yards"):
        mu, y = _col(part, "mu"), _col(part, "actual")
        k_comp = per_reception_mean_key(g)
        if not too_few((k_comp,), part.height):
            pool = pools.per_reception.get(g, ())
            if not pool:
                missing[k_comp] = "empty per-reception yard pool"
            else:
                comp_rec[g] = math.fsum(pool) / len(pool)
                n[k_comp] = part.height
        k_h = hurdle_keys(g)
        if not too_few(k_h, part.height):
            h = hurdle_gamma_mle(y, mu)
            if isinstance(h, NotFitted):
                not_fitted(k_h, h)
            else:
                hurdle[g] = HurdleGamma(alpha=h[0], zero_mass=h[1])
                n.update(dict.fromkeys(k_h, part.height))
        k_e = tuple(edge_key("receiving_yards", g, i) for i in range(_DECILE_LEVELS.size))
        if not too_few(k_e, part.height):
            emp[("receiving_yards", g)] = empirical_ratio_fit(mu, y, "PRV-05")
            n.update(dict.fromkeys(k_e, int(np.sum(mu > 0))))

    for g, part in groups("rushing_yards"):
        mu, y = _col(part, "mu"), _col(part, "actual")
        k_c = (carries_key(g), per_carry_mean_key(g))
        usable = part.filter(pl.col("carries_mean") > 0)
        if not too_few(k_c, usable.height):
            pool = pools.per_carry.get(g, ())
            r = nb_size_mle(_col(usable, "carries"), _col(usable, "carries_mean"))
            if not pool:
                not_fitted(k_c, NotFitted("empty per-carry yard pool"))
            elif isinstance(r, NotFitted):
                not_fitted(k_c, r)
            else:
                carries[g] = r
                comp_rush[g] = math.fsum(pool) / len(pool)
                n.update(dict.fromkeys(k_c, usable.height))
        k_s = shifted_keys(g)
        if not too_few(k_s, part.height):
            s = shifted_gamma_mle(y, mu)
            if isinstance(s, NotFitted):
                not_fitted(k_s, s)
            else:
                shifted[g] = ShiftedGamma(alpha=s[0], shift=s[1])
                n.update(dict.fromkeys(k_s, part.height))
        k_e = tuple(edge_key("rushing_yards", g, i) for i in range(_DECILE_LEVELS.size))
        if not too_few(k_e, part.height):
            emp[("rushing_yards", g)] = empirical_ratio_fit(mu, y, "PRV-06")
            n.update(dict.fromkeys(k_e, int(np.sum(mu > 0))))

    return WindowFit(
        window=window.name,
        test_season=window.test_season,
        seasons=window.seasons,
        nb_size=nb,
        carries_size=carries,
        compound_receiving=comp_rec,
        compound_per_carry_mean=comp_rush,
        hurdle=hurdle,
        shifted=shifted,
        empirical=emp,
        n=n,
        missing=dict(sorted(missing.items())),
    )


# ---- files ----

_SIDECAR_SCHEMA: dict[str, pl.DataType | type[pl.DataType]] = {
    "stat": pl.Utf8,
    "group": pl.Utf8,
    "bin": pl.Int64,
    "ratio": pl.Float64,
}
_METHODS = {
    "negative_binomial": "maximum likelihood (BFGS on log r) of NB(actual receptions | mean = "
    "point-in-time PRV-03 mu, size r) over the group's training player-games (PRV-10)",
    "carries_size": "maximum likelihood (BFGS on log r) of NB(actual ff rush_attempt | mean = "
    "the PRV-06 carries mean, size r) over the group's training player-games with carries mean "
    "> 0 (PRV-10)",
    "per_carry_mean": "mean of the window's PRV-06 per-carry yard pool for the group (pool "
    "size {pool}); not maximum likelihood: the compound model's scaling input",
    "per_reception_mean": "mean of the window's PRV-05 per-reception yard pool for the group "
    "(pool size {pool}); not maximum likelihood: the compound model's scaling input",
    "alpha_hurdle": "maximum likelihood (Nelder-Mead on log alpha) of the interval mass "
    "F(y + 0.5) - F(max(y - 0.5, 0)) of the y >= 1 training player-games, theta = mu / ((1 - "
    "pi) alpha) (ruling 2026-11-27)",
    "zero_mass": "share of the group's training player-games with receiving yards <= 0 (its "
    "maximum-likelihood value)",
    "shifted_gamma": "maximum likelihood (Nelder-Mead on log alpha and log(s - s_min)) of the "
    "interval mass F(y + 0.5) - F(y - 0.5), Y = G - s, theta = (mu + s) / alpha (ruling "
    "2026-11-27)",
    "edge": "training mu decile {i} of 10 (linear interpolation; 0 and 10 are the min and max) "
    "over the group's training player-games with mu > 0; bin ratios in {sidecar} sha256 "
    "{digest}",
}


def _value(spec_id: str, value: float, method: str, seasons: list[int], n: int) -> dict[str, Any]:
    return {
        "spec_id": spec_id,
        "status": "fitted",
        "value": float(value),
        "method": method,
        "seasons": list(seasons),
        "n": int(n),
        "initial_value": None,
    }


def write_fit_file(
    fit: WindowFit,
    folder: Path = FIT_ROOT,
    *,
    data_as_of: str,
    data_digest: str,
    code_commit: str,
    pools: YardsPools | None = None,
) -> Path:
    """Write <folder>/<window>.yaml (v4 FittedFile format) and its empirical-ratio sidecar.
    Returns the YAML path."""
    folder.mkdir(parents=True, exist_ok=True)
    seasons = list(fit.seasons)
    side_rows = [
        {"stat": stat, "group": g, "bin": b, "ratio": r}
        for (stat, g), er in sorted(fit.empirical.items())
        for b, ratios in enumerate(er.ratios)
        for r in ratios
    ]
    sidecar = folder / f"{fit.window}{SIDECAR_SUFFIX}"
    pl.DataFrame(side_rows, schema=_SIDECAR_SCHEMA).write_parquet(sidecar)
    digest = hashlib.sha256(sidecar.read_bytes()).hexdigest()

    def pool_size(kind: str, g: str) -> int:
        if pools is None:
            return 0
        src = pools.per_reception if kind == "rec" else pools.per_carry
        return len(src.get(g, ()))

    values: dict[str, dict[str, Any]] = {}
    for g, r in sorted(fit.nb_size.items()):
        k = nb_key(g)
        values[k] = _value("PRV-04", r, _METHODS["negative_binomial"], seasons, fit.n[k])
    for g, r in sorted(fit.carries_size.items()):
        k = carries_key(g)
        values[k] = _value("PRV-06", r, _METHODS["carries_size"], seasons, fit.n[k])
    for g, m in sorted(fit.compound_per_carry_mean.items()):
        k = per_carry_mean_key(g)
        method = _METHODS["per_carry_mean"].format(pool=pool_size("rush", g))
        values[k] = _value("PRV-06", m, method, seasons, fit.n[k])
    for g, m in sorted(fit.compound_receiving.items()):
        k = per_reception_mean_key(g)
        method = _METHODS["per_reception_mean"].format(pool=pool_size("rec", g))
        values[k] = _value("PRV-05", m, method, seasons, fit.n[k])
    for g, h in sorted(fit.hurdle.items()):
        ka_, kz = hurdle_keys(g)
        values[ka_] = _value("PRV-05", h.alpha, _METHODS["alpha_hurdle"], seasons, fit.n[ka_])
        values[kz] = _value("PRV-05", h.zero_mass, _METHODS["zero_mass"], seasons, fit.n[kz])
    for g, s in sorted(fit.shifted.items()):
        ka_, ks = shifted_keys(g)
        values[ka_] = _value("PRV-06", s.alpha, _METHODS["shifted_gamma"], seasons, fit.n[ka_])
        values[ks] = _value("PRV-06", s.shift, _METHODS["shifted_gamma"], seasons, fit.n[ks])
    for (stat, g), er in sorted(fit.empirical.items()):
        for i, e in enumerate(er.edges):
            k = edge_key(stat, g, i)
            method = _METHODS["edge"].format(i=i, sidecar=sidecar.name, digest=digest)
            values[k] = _value(_STAT_SPEC[stat], e, method, seasons, fit.n[k])
    doc = {
        "fit_version": FIT_VERSION,
        "window": fit.window,
        "test_season": fit.test_season,
        "seasons": list(seasons),
        "data_as_of": data_as_of,
        "data_digest": data_digest,
        "code_commit": code_commit,
        "attribution": ATTRIBUTION,
        "values": values,
        "missing": dict(fit.missing),
    }
    path = folder / f"{fit.window}.yaml"
    header = (
        f"# Pricer v0 (PRV-04 to PRV-06) fit, PRV-10 window {fit.window}. Generated by "
        "ge.pricer_v0.fitting; do not edit by hand.\n"
    )
    path.write_text(
        header + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
        newline="\n",
    )
    return path


def read_fit_file(window: str, folder: Path = FIT_ROOT) -> WindowFit:
    """Read a pv0 window file and its sidecar back; a sidecar whose sha256 differs from the
    one recorded in the edge keys raises ValueError."""
    from ge.config import _check_fitted

    path = folder / f"{window}.yaml"
    f = FittedFile.model_validate(_read_yaml(path))
    _check_fitted(f, path, load_params())
    sidecar = folder / f"{window}{SIDECAR_SUFFIX}"
    digest = hashlib.sha256(sidecar.read_bytes()).hexdigest()
    vals = {k: float(v.value) for k, v in f.values.items()}

    def groups_of(prefix: str) -> list[str]:
        return sorted({k.rsplit("/", 1)[1] for k in vals if k.startswith(prefix)})

    def p(spec_id: str, family: str, param: str, stat: str) -> str:
        return f"fit:{FIT_VERSION}/{spec_id}/{family}/{param}/{stat}/"

    nb = {
        g: vals[nb_key(g)]
        for g in groups_of(p("PRV-04", "negative_binomial", "size", "receptions"))
    }
    carries = {
        g: vals[carries_key(g)]
        for g in groups_of(p("PRV-06", "compound", "carries_size", "rushing_yards"))
    }
    per_carry = {
        g: vals[per_carry_mean_key(g)]
        for g in groups_of(p("PRV-06", "compound", "per_carry_mean", "rushing_yards"))
    }
    comp_rec = {
        g: vals[per_reception_mean_key(g)]
        for g in groups_of(p("PRV-05", "compound", "per_reception_mean", "receiving_yards"))
    }
    hurdle = {
        g: HurdleGamma(alpha=vals[hurdle_keys(g)[0]], zero_mass=vals[hurdle_keys(g)[1]])
        for g in groups_of(p("PRV-05", "hurdle_gamma", "alpha", "receiving_yards"))
    }
    shifted = {
        g: ShiftedGamma(alpha=vals[shifted_keys(g)[0]], shift=vals[shifted_keys(g)[1]])
        for g in groups_of(p("PRV-06", "shifted_gamma", "alpha", "rushing_yards"))
    }
    side = pl.read_parquet(sidecar)
    emp: dict[tuple[str, str], EmpiricalRatio] = {}
    for stat in ("receiving_yards", "rushing_yards"):
        for g in groups_of(p(_STAT_SPEC[stat], "empirical_ratio", "edge_00", stat)):
            method = f.values[edge_key(stat, g, 0)].method
            if digest not in method:
                raise ValueError(f"PRV-10: {sidecar} sha256 {digest} is not the one in {path}")
            edges = tuple(vals[edge_key(stat, g, i)] for i in range(_DECILE_LEVELS.size))
            mine = side.filter((pl.col("stat") == stat) & (pl.col("group") == g))
            ratios = tuple(
                tuple(mine.filter(pl.col("bin") == b)["ratio"].to_list())
                for b in range(len(edges) - 1)
            )
            emp[(stat, g)] = EmpiricalRatio(edges=edges, ratios=ratios)
    return WindowFit(
        window=f.window,
        test_season=f.test_season,
        seasons=tuple(f.seasons),
        nb_size=nb,
        carries_size=carries,
        compound_receiving=comp_rec,
        compound_per_carry_mean=per_carry,
        hurdle=hurdle,
        shifted=shifted,
        empirical=emp,
        n={k: v.n for k, v in f.values.items()},
        missing=dict(f.missing),
    )
