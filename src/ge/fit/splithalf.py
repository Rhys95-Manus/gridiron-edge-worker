"""G1 / BT-02: k by split-half stabilization.

G1 defines k as the sample size at which a split-half correlation reaches 0.5. With G1's
weighting the reliability of a mean of n units is n / (n + k), so two halves of exactly m units
correlate at r = m / (m + k), and k = m (1 - r) / r. (Equivalently, Spearman-Brown takes r to the
reliability R of 2m units and k = 2m (1 - R) / R: the same k. Mixing the corrected R with the
half size m would halve k, so only the half-size form is used here.)

Units are a metric's own units (plays, targets, team opportunities, games), keyed by `entity`
(one entity-season, e.g. a team or a player-team stint in one season and cell) and `game`, with
x, d (default 1) and c (default 1, how many units the row stands for): a half's value is
sum x / sum d, its size sum c, as in ge.metrics.engine.summarise.

Per split: each entity's games go to half A or B at random; within each half the units are taken
in random order until m are in (a coarse unit can carry the half past m; the mean size actually
taken is used as m). Entities short of m in either half are left out. r is averaged over the
seeded splits and each m gives k_m.

No signal (BT-02, decision 2026-10-07): an m enters the k average only if the Fisher-z interval
for its r, at the configured level with standard error 1/sqrt(N - 3) over its N entities, lies
entirely above zero. If no m qualifies the stat is "no detectable signal": k is infinite and the
shrunk value is the prior. k is the inverse-variance mean of the qualifying k_m (var of r by the
delta method, (1 - r^2)^2 / (N - 3)). Every draw is seeded from the caller's key (rule 6) and
every sum is sequential over sorted rows, so the result is byte-identical for the same input."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from statistics import NormalDist
from typing import Literal

import numpy as np
import polars as pl

from ge.config import Fitting

NO_SIGNAL = "no detectable signal"
KStatus = Literal["fitted", "no_signal", "missing"]


@dataclass(frozen=True)
class SplitHalfConfig:
    """BT-02 method settings (params.yaml `fitting` group)."""

    m_grid: tuple[int, ...]
    splits: int
    min_entities: int
    confidence: float

    @staticmethod
    def from_params(f: Fitting) -> SplitHalfConfig:
        return SplitHalfConfig(
            m_grid=f.m_grid(),
            splits=int(f.bt_02_k_splits.value),
            min_entities=int(f.bt_02_k_min_entities_per_m.value),
            confidence=float(f.bt_02_no_signal_confidence.value),
        )


@dataclass(frozen=True)
class MFit:
    m: int
    m_eff: float
    r: float
    entities: float
    z_low: float  # lower end of the Fisher-z interval, back on the r scale
    signal: bool
    k: float | None
    var_k: float | None


@dataclass(frozen=True)
class KFit:
    """status fitted: k set. no_signal: k is infinite (None here; shrunk = prior). missing: too
    few entities at every m (reason says so)."""

    status: KStatus
    k: float | None
    entities: int  # distinct entities with 2m units at the smallest m used
    per_m: tuple[MFit, ...]
    reason: str | None


def seeded(key: str) -> np.random.Generator:
    """Rule 6: a Generator seeded from a stable key (sha256), never from time or order."""
    return np.random.default_rng(int(hashlib.sha256(key.encode()).hexdigest()[:16], 16))


def _prep(units: pl.DataFrame) -> pl.DataFrame:
    u = units
    for col in ("d", "c"):
        if col not in u.columns:
            u = u.with_columns(pl.lit(1.0).alias(col))
    return (
        u.select(
            pl.col("entity").cast(pl.Utf8),
            pl.col("game").cast(pl.Utf8),
            pl.col("x").cast(pl.Float64),
            pl.col("d").cast(pl.Float64),
            pl.col("c").cast(pl.Float64),
        )
        .filter(pl.col("x").is_not_null() & pl.col("d").is_not_null() & pl.col("c").is_not_null())
        .sort("entity", "game", "x", "d", "c")
    )


_HV_SCHEMA = {
    "split": pl.Int64,
    "m": pl.Int64,
    "entity": pl.Utf8,
    "v_a": pl.Float64,
    "v_b": pl.Float64,
    "n_a": pl.Float64,
    "n_b": pl.Float64,
}


def half_values(
    units: pl.DataFrame, cfg: SplitHalfConfig, seed_key: str, *, keep_games: bool = False
) -> pl.DataFrame:
    """Per split, m and qualifying entity: each half's value and size. Seasons can be computed
    separately (with their own seed keys) and concatenated before k_from_halves."""
    u = _prep(units)
    if u.is_empty():
        return pl.DataFrame(schema=_HV_SCHEMA)
    # Rows are sorted by entity then game: integer codes for entities and (entity, game) pairs.
    ent_all = u["entity"].to_numpy()
    game_all = u["game"].to_numpy()
    new_ent = np.r_[True, ent_all[1:] != ent_all[:-1]]
    new_pair = new_ent | np.r_[True, game_all[1:] != game_all[:-1]]
    e0 = np.cumsum(new_ent) - 1
    pair = np.cumsum(new_pair) - 1
    ents = pl.Series("entity", ent_all[new_ent])
    n_pairs = int(pair[-1]) + 1
    x0, d0, c0 = (u[col].to_numpy() for col in ("x", "d", "c"))
    games_all = game_all
    frames = []
    for b in range(cfg.splits):
        g = seeded(f"{seed_key}/split{b}")
        side = g.integers(0, 2, n_pairs)
        key = g.random(u.height)
        h0 = side[pair]
        order = np.lexsort((key, h0, e0))
        e, h = e0[order], h0[order].astype(np.int64)
        x, d, c = x0[order], d0[order], c0[order]
        grp = e * 2 + h
        # c before each row within its (entity, half): sequential cumulative sums.
        start = np.r_[True, grp[1:] != grp[:-1]]
        csum = np.cumsum(c)
        base = np.maximum.accumulate(np.where(start, csum - c, 0.0))
        before = csum - c - base
        for m in cfg.m_grid:
            keep = before < m
            gk = grp[keep]
            size = 2 * len(ents)
            sx = np.bincount(gk, weights=x[keep], minlength=size)
            sd = np.bincount(gk, weights=d[keep], minlength=size)
            sc = np.bincount(gk, weights=c[keep], minlength=size)
            sa, sb = slice(0, size, 2), slice(1, size, 2)
            ok = (sc[sa] >= m) & (sc[sb] >= m) & (sd[sa] != 0) & (sd[sb] != 0)
            if not ok.any():
                continue
            idx = np.flatnonzero(ok)
            df = pl.DataFrame(
                {
                    "split": np.full(idx.size, b, dtype=np.int64),
                    "m": np.full(idx.size, m, dtype=np.int64),
                    "entity": ents.gather(idx.tolist()),
                    "v_a": sx[sa][idx] / sd[sa][idx],
                    "v_b": sx[sb][idx] / sd[sb][idx],
                    "n_a": sc[sa][idx],
                    "n_b": sc[sb][idx],
                },
                schema=_HV_SCHEMA,
            )
            if keep_games:  # test aid: which games each half used
                gm = games_all[order][keep]
                ek, hk = e[keep], h[keep]
                sel = np.isin(ek, idx)
                kept = pl.DataFrame(
                    {"entity": ents.to_numpy()[ek[sel]], "_h": hk[sel], "game": gm[sel]}
                )
                gl = kept.group_by("entity", "_h").agg(pl.col("game").unique().sort())
                ga = gl.filter(pl.col("_h") == 0).select("entity", pl.col("game").alias("games_a"))
                gb = gl.filter(pl.col("_h") == 1).select("entity", pl.col("game").alias("games_b"))
                df = df.join(ga, on="entity", how="left").join(gb, on="entity", how="left")
            frames.append(df)
    if not frames:
        return pl.DataFrame(schema=_HV_SCHEMA)
    return pl.concat(frames, how="diagonal").sort("split", "m", "entity")


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    den = math.sqrt(float(np.dot(a, a)) * float(np.dot(b, b)))
    return float(np.dot(a, b)) / den if den > 0 else 0.0


def k_from_halves(hv: pl.DataFrame, cfg: SplitHalfConfig) -> KFit:
    """G1: k per m from the mean split-half r; BT-02 no-signal gate; inverse-variance mean."""
    zq = NormalDist().inv_cdf(0.5 + cfg.confidence / 2)
    per_m: list[MFit] = []
    smallest_entities = 0
    for m in cfg.m_grid:
        sub = hv.filter(pl.col("m") == m)
        rs, ns, sizes = [], [], []
        for b in range(cfg.splits):
            s = sub.filter(pl.col("split") == b).sort("entity")
            if s.height < cfg.min_entities:
                continue
            rs.append(_corr(s["v_a"].to_numpy(), s["v_b"].to_numpy()))
            ns.append(s.height)
            sizes.append(float((s["n_a"] + s["n_b"]).mean()) / 2.0)  # type: ignore[arg-type]
        if not rs:
            continue
        if not smallest_entities:
            smallest_entities = sub["entity"].n_unique()
        r = float(np.mean(rs))
        n_ent = float(np.mean(ns))
        m_eff = float(np.mean(sizes))
        rc = min(max(r, -0.999999), 0.999999)
        low = math.tanh(math.atanh(rc) - zq / math.sqrt(n_ent - 3)) if n_ent > 3 else -1.0
        if low <= 0:
            per_m.append(MFit(m, m_eff, r, n_ent, low, False, None, None))
            continue
        k = m_eff * (1 - r) / r
        var_r = (1 - r * r) ** 2 / (n_ent - 3)
        var_k = (m_eff / (r * r)) ** 2 * var_r
        per_m.append(MFit(m, m_eff, r, n_ent, low, True, k, var_k))
    if not per_m:
        return KFit(
            "missing",
            None,
            0,
            (),
            f"fewer than {cfg.min_entities} entities with 2m units for every m in {cfg.m_grid}",
        )
    usable = [p for p in per_m if p.signal and p.var_k is not None and p.var_k > 0]
    if not usable:
        return KFit(
            "no_signal",
            None,
            smallest_entities,
            tuple(per_m),
            f"{NO_SIGNAL}: no m's {cfg.confidence:.0%} Fisher-z interval for r lies above zero",
        )
    wsum = math.fsum(1 / p.var_k for p in usable)  # type: ignore[operator]
    k = math.fsum(p.k / p.var_k for p in usable) / wsum  # type: ignore[operator]
    return KFit("fitted", k, smallest_entities, tuple(per_m), None)


def split_half_k(units: pl.DataFrame, cfg: SplitHalfConfig, seed_key: str) -> KFit:
    return k_from_halves(half_values(units, cfg, seed_key), cfg)


def variance_k(units: pl.DataFrame) -> float | None:
    """Cross-check (report only): method-of-moments k = within variance / between variance for
    plain per-unit means (d = c = 1). Ratio units return None."""
    u = _prep(units)
    if u.is_empty() or (u["d"] != 1).any() or (u["c"] != 1).any():
        return None
    g = u.group_by("entity").agg(
        pl.len().alias("n"), pl.col("x").mean().alias("mean"), pl.col("x").var(ddof=1).alias("v")
    )
    g = g.sort("entity")
    n = g["n"].to_numpy().astype(np.float64)
    if n.size < 2 or (n < 2).any():
        return None
    mean = g["mean"].to_numpy()
    var = g["v"].to_numpy()
    total = n.sum()
    within = float(((n - 1) * var).sum() / (total - n.size))
    grand = float((n * mean).sum() / total)
    between_ss = float((n * (mean - grand) ** 2).sum())
    n0 = (total - float((n * n).sum()) / total) / (n.size - 1)
    tau2 = (between_ss / (n.size - 1) - within) / n0
    return within / tau2 if tau2 > 0 else None
