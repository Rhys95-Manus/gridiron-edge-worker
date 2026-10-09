"""G6 / BT-02: the opponent-adjustment ridge and its penalty by forward-chaining CV.

EPA of each play = league intercept + offense rating + defense rating + home term + error,
weighted by G3 recency (w = 0.5^(g / h), g = the offense's games ago, efficiency h). The
intercept and home term are not penalized; team ratings are (ruling 2026-10-08). The penalty
is chosen from BT-02's grid: within each training season, ratings from weeks before w predict
the plays of week w, and the play-level squared error is summed over weeks and seasons.

The design is categorical, so plays are pooled by (offense, defense, home) with summed weights
and the weighted mean EPA; weighted least squares on those groups equals it on the plays."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import polars as pl

from ge.metrics.conventions import weighted_ridge


@dataclass(frozen=True)
class RidgeRatings:
    intercept: float
    home: float
    offense: dict[str, float]
    defense: dict[str, float]


@dataclass(frozen=True)
class CVLoss:
    sse: float
    plays: int


def _weights(train: pl.DataFrame, h: float) -> pl.DataFrame:
    """Games ago for the offense, counted back from its latest training game (g = 0)."""
    games = (
        train.select("posteam", "game_id", "week")
        .unique()
        .sort(["posteam", "week", "game_id"], descending=[False, True, True])
        .with_columns(pl.int_range(pl.len()).over("posteam").cast(pl.Float64).alias("_g"))
    )
    keyed = games.select("posteam", "game_id", "_g")
    return train.join(keyed, on=["posteam", "game_id"]).with_columns(
        (pl.lit(0.5) ** (pl.col("_g") / h)).alias("_w")
    )


def _fit(train: pl.DataFrame, teams: Sequence[str], penalty: float, h: float) -> RidgeRatings:
    t = _weights(train, h)
    grp = (
        t.group_by("posteam", "defteam", "is_home")
        .agg(
            pl.col("_w").sum().alias("w"),
            (pl.col("_w") * pl.col("epa")).sum().alias("wy"),
        )
        .sort("posteam", "defteam", "is_home")
    )
    idx = {tm: i for i, tm in enumerate(teams)}
    nt = len(teams)
    X = np.zeros((grp.height, 2 + 2 * nt))
    X[:, 0] = 1.0
    X[:, 1] = grp["is_home"].to_numpy()
    rows = np.arange(grp.height)
    X[rows, 2 + np.array([idx[x] for x in grp["posteam"].to_list()])] = 1.0
    X[rows, 2 + nt + np.array([idx[x] for x in grp["defteam"].to_list()])] = 1.0
    w = grp["w"].to_numpy()
    y = grp["wy"].to_numpy() / w
    b = weighted_ridge(X, y, w, penalty, unpenalized=(0, 1))
    return RidgeRatings(
        float(b[0]),
        float(b[1]),
        {tm: float(b[2 + i]) for tm, i in idx.items()},
        {tm: float(b[2 + nt + i]) for tm, i in idx.items()},
    )


def ridge_ratings(plays: pl.DataFrame, penalty: float, h: float) -> RidgeRatings:
    """G6 ratings from every play given (columns posteam, defteam, is_home, epa, game_id,
    week), weighted from the latest game back."""
    teams = sorted(set(plays["posteam"].to_list()) | set(plays["defteam"].to_list()))
    return _fit(plays, teams, penalty, h)


def g6_cv_losses(plays: pl.DataFrame, grid: Sequence[float], h: float) -> dict[float, CVLoss]:
    """One season's forward-chaining CV: for each week after the first, fit on earlier weeks
    and score that week's plays, for every penalty in the grid."""
    plays = plays.select("game_id", "week", "posteam", "defteam", "is_home", "epa").sort(
        "week", "game_id", "posteam", "defteam", "is_home", "epa"
    )
    teams = sorted(set(plays["posteam"].to_list()) | set(plays["defteam"].to_list()))
    weeks = sorted(set(plays["week"].to_list()))
    out: dict[float, list[float]] = {p: [0.0, 0.0] for p in grid}
    for wk in weeks[1:]:
        train = plays.filter(pl.col("week") < wk)
        test = plays.filter(pl.col("week") == wk)
        y = test["epa"].to_numpy()
        hm = test["is_home"].to_numpy()
        po, de = test["posteam"].to_list(), test["defteam"].to_list()
        for p in grid:
            r = _fit(train, teams, p, h)
            pred = (
                r.intercept
                + r.home * hm
                + np.array([r.offense[t] for t in po])
                + np.array([r.defense[t] for t in de])
            )
            out[p][0] = math.fsum([out[p][0], math.fsum((y - pred) ** 2)])
            out[p][1] += len(y)
    return {p: CVLoss(float(v[0]), int(v[1])) for p, v in out.items()}


def choose_penalty(losses: Sequence[Mapping[float, CVLoss]]) -> float:
    """The grid penalty with the lowest squared error summed over seasons (ties: smaller)."""
    grid = sorted(losses[0])
    tot = {p: math.fsum(lo[p].sse for lo in losses) for p in grid}
    return min(grid, key=lambda p: (tot[p], p))
