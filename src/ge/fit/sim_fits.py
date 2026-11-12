"""Phase 5 per-window fits for the PRJ-02 simulation.

- League week series: league points per team-game for every league week of the training
  seasons, regular season and postseason in order (PRJ-02 league level; h_L is chosen on it
  by ge.fit.league_level).
- League weights: 0.5^(w / h_L), w = league weeks before the target week. In a backtest season
  the training data are the same for every target week, so the weights for two target weeks
  differ by a constant factor, which cancels in a weighted mean and leaves a weighted
  maximum-likelihood fit unchanged: one fit per window, with w counted from the test season's
  first week, is exact. Live 2026 adds the current season's visible weeks (later).
- Field-goal attempt vs punt (ruling C8, 2026-10-23): when COA-02 does not go for it, a league
  logistic model of P(field-goal attempt) on yardline_100, weighted by the league level, at
  least 200 events (BT-02). Its standard errors use the weights rescaled to sum to the
  effective sample size (Sum w)^2 / Sum w^2, as G3 does, and are labelled approximate.
- 4th-down go model (ruling 2026-10-31): the simulator's P(go for it) on COA-02's decisions, a
  league logistic with one term per distance x field cell (config/sim.yaml `fourth_go`) plus
  linear score_differential and game_seconds_remaining, weighted by the league level the same
  way. BT-02's minimum (200) applies to the whole fit, for go-fors and other decisions alike; a
  cell with none of one kind has no finite estimate and raises. COA-02's p_go is unchanged."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import polars as pl

from ge.config import load_params
from ge.fit.logistic import fit_logistic

FloatArray = npt.NDArray[np.float64]


def league_week_series(sched: pl.DataFrame) -> pl.DataFrame:
    """PRJ-02: (season, week, week_index, points_per_team_game, team_games) for every league
    week with played games, in order."""
    played = sched.filter(pl.col("home_score").is_not_null() & pl.col("away_score").is_not_null())
    return (
        played.group_by("season", "week")
        .agg(
            (pl.col("home_score") + pl.col("away_score")).sum().alias("points"),
            (pl.len() * 2).alias("team_games"),
        )
        .sort("season", "week")
        .with_columns(
            (pl.col("points") / pl.col("team_games")).alias("points_per_team_game"),
            pl.int_range(pl.len()).alias("week_index"),
            pl.col("team_games").cast(pl.Int64),
        )
        .select("season", "week", "week_index", "points_per_team_game", "team_games")
    )


def league_weights(week_index: npt.ArrayLike, *, target_index: int, h: float) -> FloatArray:
    """PRJ-02 league level: 0.5^(w / h) with w = target_index - week_index (>= 1)."""
    w = target_index - np.asarray(week_index, dtype=np.float64)
    if np.any(w < 1):
        raise ValueError("PRJ-02: a training week at or after the target week")
    return np.asarray(0.5 ** (w / h), dtype=np.float64)


@dataclass(frozen=True)
class FgPuntFit:
    intercept: float
    slope: float  # per yard of yardline_100
    intercept_se: float  # approximate (weights rescaled to the effective sample size)
    slope_se: float
    n: int
    events: int  # field-goal attempts
    n_eff: float


def fit_fg_vs_punt(plays: pl.DataFrame, *, target_index: int, h: float) -> FgPuntFit:
    """Ruling C8: P(field-goal attempt | not going for it) = logistic(a + b x yardline_100).
    `plays`: week_index, yardline_100, fg_attempt (1 field-goal attempt, 0 punt)."""
    d = plays.drop_nulls(["week_index", "yardline_100", "fg_attempt"])
    y = d["fg_attempt"].to_numpy().astype(np.float64)
    events = int(y.sum())
    min_events = int(load_params().fitting.bt_02_min_events.value)
    if events < min_events or (y.size - events) < min_events:
        raise NotImplementedError(
            f"PRJ-02 (ruling C8): field-goal-vs-punt needs {min_events} events of each kind; "
            f"got {events} field-goal attempts and {y.size - events} punts"
        )
    w = league_weights(d["week_index"].to_numpy(), target_index=target_index, h=h)
    n_eff = float(w.sum() ** 2 / np.square(w).sum())
    w = w * (n_eff / w.sum())
    X = np.column_stack([np.ones(y.size), d["yardline_100"].to_numpy().astype(np.float64)])
    fit = fit_logistic(X, y, w=w)
    return FgPuntFit(
        intercept=float(fit.coef[0]),
        slope=float(fit.coef[1]),
        intercept_se=float(fit.se[0]),
        slope_se=float(fit.se[1]),
        n=int(y.size),
        events=events,
        n_eff=n_eff,
    )


GO_FEATURES = ("week_index", "go", "ydstogo", "yardline_100", "score_differential",
               "game_seconds_remaining")  # fmt: skip


@dataclass(frozen=True)
class GoFit:
    cell: tuple[float, ...]  # logit per cell, GO_CELLS
    cell_se: tuple[float, ...]  # approximate (weights rescaled to the effective sample size)
    score_differential: float
    score_differential_se: float
    game_seconds: float
    game_seconds_se: float
    long_ln_togo: float  # ruling 2026-11-01: slope on ln(ydstogo / L) in the last distance bin
    long_ln_togo_se: float
    cell_n: list[int]
    cell_go: list[int]
    cell_other: list[int]
    n: int
    events: int  # go-fors
    n_eff: float


def go_cell(
    togo: npt.ArrayLike, yardline: npt.ArrayLike, togo_upper: list[int], yardline_upper: list[int]
) -> npt.NDArray[np.int64]:
    """Ruling 2026-10-31: distance bin x 3 + field bin, each bin up to an inclusive upper edge."""
    tb = np.searchsorted(np.asarray(togo_upper, dtype=np.float64), np.asarray(togo), side="left")
    yb = np.searchsorted(
        np.asarray(yardline_upper, dtype=np.float64), np.asarray(yardline), side="left"
    )
    return np.asarray(tb * (len(yardline_upper) + 1) + yb, dtype=np.int64)


def long_ln_togo(togo: npt.ArrayLike, togo_upper: list[int]) -> npt.NDArray[np.float64]:
    """Ruling 2026-11-01: ln(ydstogo / L) in the last distance bin (L = its lower edge,
    togo_upper[-1] + 1), zero elsewhere."""
    t = np.asarray(togo, dtype=np.float64)
    lower = float(togo_upper[-1] + 1)
    return np.where(t >= lower, np.log(np.maximum(t, lower) / lower), 0.0)


def fourth_go_rows(core: pl.DataFrame) -> pl.DataFrame:
    """COA-02's 4th-down decisions (go = pass or run) from core play rows with week_index."""
    from ge.metrics.coaching import fourth_downs

    return fourth_downs(core).select(GO_FEATURES).drop_nulls()


def fit_fourth_go(
    rows: pl.DataFrame,
    *,
    target_index: int,
    h: float,
    togo_upper: list[int],
    yardline_upper: list[int],
) -> GoFit:
    """PRJ-02 (ruling 2026-10-31): P(go) = logistic(cell_c + b_sd x score_differential + b_t x
    game_seconds_remaining + b_long x ln(ydstogo / L) in the last distance bin (ruling
    2026-11-01)). `rows`: GO_FEATURES."""
    from ge.models.sim.arrays import GO_CELLS

    d = rows.drop_nulls(list(GO_FEATURES))
    y = d["go"].to_numpy().astype(np.float64)
    events = int(y.sum())
    min_events = int(load_params().fitting.bt_02_min_events.value)
    if events < min_events or (y.size - events) < min_events:
        raise NotImplementedError(
            f"PRJ-02 (ruling 2026-10-31): the go model needs {min_events} decisions of each kind; "
            f"got {events} go-fors and {y.size - events} others"
        )
    cell = go_cell(d["ydstogo"].to_numpy(), d["yardline_100"].to_numpy(), togo_upper,
                   yardline_upper)  # fmt: skip
    n_cells = (len(togo_upper) + 1) * (len(yardline_upper) + 1)
    if n_cells != GO_CELLS:
        raise ValueError(f"PRJ-02: the go model has {GO_CELLS} cells; the bins give {n_cells}")
    cell_n = np.bincount(cell, minlength=n_cells)
    cell_go = np.bincount(cell, weights=y, minlength=n_cells).astype(np.int64)
    for c in range(n_cells):
        if cell_go[c] == 0 or cell_go[c] == cell_n[c]:
            raise NotImplementedError(
                f"PRJ-02 (ruling 2026-10-31): go-model cell {c} has {cell_go[c]} go-fors of "
                f"{cell_n[c]} decisions; its logit has no finite estimate"
            )
    togo = d["ydstogo"].to_numpy()
    long_go = np.unique(togo[(togo >= togo_upper[-1] + 1) & (y == 1.0)])
    if long_go.size < 2:
        raise NotImplementedError(
            f"PRJ-02 (ruling 2026-11-01): the go-fors at {togo_upper[-1] + 1}+ yards to go are "
            f"all at one distance ({long_go.tolist()}); the distance slope has no finite estimate"
        )
    w = league_weights(d["week_index"].to_numpy(), target_index=target_index, h=h)
    n_eff = float(w.sum() ** 2 / np.square(w).sum())
    w = w * (n_eff / w.sum())
    X = np.column_stack(
        [(cell == c).astype(np.float64) for c in range(n_cells)]
        + [d["score_differential"].to_numpy().astype(np.float64),
           d["game_seconds_remaining"].to_numpy().astype(np.float64),
           long_ln_togo(togo, togo_upper)]
    )  # fmt: skip
    fit = fit_logistic(X, y, w=w)
    return GoFit(
        cell=tuple(float(b) for b in fit.coef[:n_cells]),
        cell_se=tuple(float(s) for s in fit.se[:n_cells]),
        score_differential=float(fit.coef[n_cells]),
        score_differential_se=float(fit.se[n_cells]),
        game_seconds=float(fit.coef[n_cells + 1]),
        game_seconds_se=float(fit.se[n_cells + 1]),
        long_ln_togo=float(fit.coef[n_cells + 2]),
        long_ln_togo_se=float(fit.se[n_cells + 2]),
        cell_n=[int(v) for v in cell_n],
        cell_go=[int(v) for v in cell_go],
        cell_other=[int(n - g) for n, g in zip(cell_n, cell_go, strict=True)],
        n=int(y.size),
        events=events,
        n_eff=n_eff,
    )
