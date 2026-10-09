"""G3 / BT-02: half-life by next-game prediction loss (ruling 2026-10-08).

For each entity-season and each of its games after the first, predict the game's value from its
earlier games: G3 weights w = 0.5^(games back / h), G1 shrink with the stat's fitted k toward the
season's league mean (sum x / sum d over every unit). Loss = sum over target games of
n (observed - predicted)^2, n = the game's units (Brier for 0/1 units, up to a constant). The
prior-only loss (predict the league mean) is the baseline; ratio = loss / baseline puts stats
in different units on one scale. One usage h and one efficiency h: the grid value with the
lowest mean ratio over that class's stats.

Weighted sums are carried forward recursively (S_t = decay S_(t-1) + game_(t-1)), so the cost
is linear in games."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import polars as pl


@dataclass(frozen=True)
class HLoss:
    loss: float
    base: float
    n: float  # units scored

    @property
    def ratio(self) -> float:
        return self.loss / self.base if self.base > 0 else math.nan


def _games(units: pl.DataFrame) -> tuple[np.ndarray, float]:
    """(3, entities, max games) array of per-game sum x, sum d, sum c (zero-padded), and the
    league mean."""
    u = units
    for col in ("d", "c"):
        if col not in u.columns:
            u = u.with_columns(pl.lit(1.0).alias(col))
    u = u.filter(pl.col("x").is_not_null())
    sd_all = math.fsum(u["d"].to_list())
    prior = math.fsum(u["x"].to_list()) / sd_all if sd_all else math.nan
    g = (
        u.group_by("entity", "gi")
        .agg(pl.col("x").sum(), pl.col("d").sum(), pl.col("c").sum())
        .sort("entity", "gi")
        .with_columns(
            pl.col("entity").rank("dense").cast(pl.Int64).alias("_e") - 1,
            pl.int_range(pl.len()).over("entity").alias("_t"),
        )
    )
    arr = np.zeros((3, int(g["_e"].max()) + 1, int(g["_t"].max()) + 1))  # type: ignore[arg-type]
    e, t = g["_e"].to_numpy(), g["_t"].to_numpy()
    for i, col in enumerate(("x", "d", "c")):
        arr[i, e, t] = g[col].to_numpy()
    return arr, prior


def half_life_losses(
    units: pl.DataFrame, k: float, hs: Sequence[float], prior: float | None = None
) -> dict[float, HLoss]:
    """units: entity, gi (chronological game index within the entity-season), x, d?, c?.
    Loops over game index with numpy vectors across entities."""
    if units.is_empty():
        return {h: HLoss(0.0, 0.0, 0.0) for h in hs}
    arr, lg = _games(units)
    pr = lg if prior is None else prior
    gx, gd, gc = arr
    n_games = gx.shape[1]
    scored = np.zeros_like(gx, dtype=bool)
    scored[:, 1:] = (gd[:, 1:] != 0) & (gc[:, 1:] > 0)
    obs = np.divide(gx, gd, out=np.zeros_like(gx), where=gd != 0)
    base = float(np.sum(np.where(scored, gc * (obs - pr) ** 2, 0.0)))
    n_tot = float(np.sum(np.where(scored, gc, 0.0)))
    out: dict[float, HLoss] = {}
    for h in hs:
        decay = 0.5 ** (1 / h)
        sx = np.zeros(gx.shape[0])
        sd = np.zeros_like(sx)
        swc = np.zeros_like(sx)
        sw2c = np.zeros_like(sx)
        loss = np.zeros_like(sx)
        for t in range(n_games):
            if t > 0:
                has = (sd != 0) & (sw2c > 0)
                n_eff = np.divide(swc * swc, sw2c, out=np.zeros_like(sx), where=sw2c > 0)
                vw = np.divide(sx, sd, out=np.zeros_like(sx), where=sd != 0)
                pred = np.where(has, (n_eff * vw + k * pr) / (n_eff + k), pr)
                loss += np.where(scored[:, t], gc[:, t] * (obs[:, t] - pred) ** 2, 0.0)
            sx = decay * sx + gx[:, t]
            sd = decay * sd + gd[:, t]
            swc = decay * swc + gc[:, t]
            sw2c = decay * decay * sw2c + gc[:, t]
        out[h] = HLoss(math.fsum(loss.tolist()), base, n_tot)
    return out


def merge(losses: Sequence[Mapping[float, HLoss]]) -> dict[float, HLoss]:
    """Sum one stat's losses over seasons."""
    hs = sorted(losses[0])
    return {
        h: HLoss(
            math.fsum(lo[h].loss for lo in losses),
            math.fsum(lo[h].base for lo in losses),
            math.fsum(lo[h].n for lo in losses),
        )
        for h in hs
    }


def choose_half_life(per_stat: Sequence[Mapping[float, HLoss]]) -> float:
    """The grid h with the lowest mean loss ratio over stats (ties: the smaller h)."""
    usable = [s for s in per_stat if all(v.base > 0 for v in s.values())]
    hs = sorted(usable[0])
    mean = {h: math.fsum(s[h].ratio for s in usable) / len(usable) for h in hs}
    return min(hs, key=lambda h: (mean[h], h))
