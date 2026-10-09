"""MTC-03 / BT-02: the OL-absence factor, estimated without the simulator (ruling 2026-10-08).

MTC-03 prices a dropback's sack odds as odds_off x odds_def / odds_league, times the factor for
each missing starting lineman (OFF-17). Here each dropback gets the offset
log(odds_off) + log(odds_def) - log(odds_league), with the team odds from leave-one-game-out
team-season sack rates (allowed: every training season is before the test season), and a
logistic model fits an intercept (nuisance, absorbs the offset's calibration) and one
coefficient on the number of missing starters: factor = exp(coefficient). Undamped: MTC-03's
lambda is BT-03's job."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import polars as pl

from ge.fit.logistic import fit_logistic


@dataclass(frozen=True)
class OLFit:
    value: float | None
    log_value: float
    se: float
    intercept: float
    dropbacks: int
    sacks: int
    reason: str | None


def _logit_odds(rate: pl.Expr) -> pl.Expr:
    return (rate / (1 - rate)).log()


def ol_absence_factor(rows: pl.DataFrame, min_events: int) -> OLFit:
    """rows: season, game_id, posteam, defteam, sack (0/1), missing (starters out, per
    posteam-game). Rows whose leave-one-out rate is 0 or 1 have no finite odds and are left
    out."""
    r = rows.select("season", "game_id", "posteam", "defteam", "sack", "missing").sort(
        "season", "game_id", "posteam", "defteam", "sack", "missing"
    )
    sacks = int(r["sack"].sum()) if r.height else 0
    if sacks < min_events:
        return OLFit(
            None, math.nan, math.nan, math.nan, r.height, sacks,
            f"{sacks} sacks, fewer than the {min_events}-event minimum",
        )  # fmt: skip

    def loo(side: str) -> pl.Expr:
        tot = pl.col("sack").sum().over("season", side)
        n = pl.len().over("season", side)
        g_tot = pl.col("sack").sum().over("season", "game_id", side)
        g_n = pl.len().over("season", "game_id", side)
        return ((tot - g_tot) / (n - g_n)).cast(pl.Float64)

    r = r.with_columns(
        loo("posteam").alias("_off"),
        loo("defteam").alias("_def"),
        (pl.col("sack").sum().over("season") / pl.len().over("season"))
        .cast(pl.Float64)
        .alias("_lg"),
    )
    ok = pl.all_horizontal(
        [(pl.col(c) > 0) & (pl.col(c) < 1) for c in ("_off", "_def", "_lg")]
    ).fill_null(False)
    r = r.filter(ok).with_columns(
        (
            _logit_odds(pl.col("_off")) + _logit_odds(pl.col("_def")) - _logit_odds(pl.col("_lg"))
        ).alias("_offset")
    )
    X = np.column_stack([np.ones(r.height), r["missing"].to_numpy().astype(np.float64)])
    fit = fit_logistic(X, r["sack"].to_numpy().astype(np.float64), offset=r["_offset"].to_numpy())
    b, se = float(fit.coef[1]), float(fit.se[1])
    return OLFit(math.exp(b), b, se, float(fit.coef[0]), r.height, fit.events, None)
