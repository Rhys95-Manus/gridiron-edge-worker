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
- 4th-down go model (ruling 2026-10-31): the simulator's P(go for it), a league logistic with
  one term per distance x field cell (config/sim.yaml `fourth_go`) plus linear
  score_differential, weighted by the league level the same way. Ruling 2026-11-12: every
  4th-down decision, G7 garbage time included (G-1), and one term per trailing bin x late-time
  bin in place of the game-seconds slope (G-2). BT-02's minimum (200) applies to the whole fit,
  for go-fors and other decisions alike; a cell or late term with none of one kind has no
  finite estimate and raises. COA-02's p_go is unchanged.
- Sticks spot-short (ruling 2026-11-12, S-1): per play kind (designed run, completion), the
  probability q that a gain landing exactly on the line to gain is spotted one yard short:
  q = 1 - O / E clamped to [0, 1], O the weighted count of gains exactly on the line, E the
  count expected from reference distances in the same distance bin (config/sim.yaml `sticks`),
  under the league weights rescaled to the effective sample size; E below sticks.min_expected
  raises."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
import polars as pl

from ge.config import load_params
from ge.fit.logistic import fit_logistic
from ge.metrics import plays as pf

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
    long_ln_togo: float  # ruling 2026-11-01: slope on ln(ydstogo / L) in the last distance bin
    long_ln_togo_se: float
    late: tuple[float, ...]  # ruling 2026-11-12: trailing bin x late-time bin, GO_LATE terms
    late_se: tuple[float, ...]
    cell_n: list[int]
    cell_go: list[int]
    cell_other: list[int]
    late_n: list[int]
    late_go: list[int]
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


def go_late_index(
    sd: npt.ArrayLike, seconds: npt.ArrayLike, trail_upper: list[int], late_upper: list[int]
) -> npt.NDArray[np.int64]:
    """Ruling 2026-11-12 (G-2): trailing bin x len(late_upper) + time bin when the offense
    trails (deficit -sd up to each inclusive upper edge, then beyond) with game_seconds_remaining
    at most late_upper[-1] (inclusive upper edges); -1 when leading, tied or earlier."""
    d = -np.asarray(sd, dtype=np.float64)
    t = np.asarray(seconds, dtype=np.float64)
    b = np.searchsorted(np.asarray(trail_upper, dtype=np.float64), d, side="left")
    k = np.searchsorted(np.asarray(late_upper, dtype=np.float64), t, side="left")
    on = (d > 0) & (t <= late_upper[-1])
    return np.asarray(np.where(on, b * len(late_upper) + k, -1), dtype=np.int64)


def fourth_go_rows(core: pl.DataFrame) -> pl.DataFrame:
    """Ruling 2026-11-12 (G-1): every 4th-down decision (pass, run, punt, field goal; go = pass
    or run), G7 garbage time included, since the simulator applies the model in every state;
    no-play penalties and other downs out. From core play rows with week_index."""
    d = core.filter(
        (pl.col("down") == 4)
        & pl.col("play_type").is_in(["pass", "run", "punt", "field_goal"])
        & pl.col("posteam").is_not_null()
    )
    d = d.with_columns(pl.col("play_type").is_in(["pass", "run"]).cast(pl.Float64).alias("go"))
    return d.select(GO_FEATURES).drop_nulls()


def fit_fourth_go(
    rows: pl.DataFrame,
    *,
    target_index: int,
    h: float,
    togo_upper: list[int],
    yardline_upper: list[int],
    trail_upper: list[int],
    late_seconds_upper: list[int],
) -> GoFit:
    """PRJ-02 (ruling 2026-10-31): P(go) = logistic(cell_c + b_sd x score_differential + b_long x
    ln(ydstogo / L) in the last distance bin (ruling 2026-11-01) + b_late[k] when trailing late,
    k = go_late_index (ruling 2026-11-12, G-2)). `rows`: GO_FEATURES."""
    from ge.models.sim.arrays import GO_CELLS, GO_LATE

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
    sd = d["score_differential"].to_numpy().astype(np.float64)
    late = go_late_index(sd, d["game_seconds_remaining"].to_numpy(), trail_upper,
                         late_seconds_upper)  # fmt: skip
    n_late = (len(trail_upper) + 1) * len(late_seconds_upper)
    if n_late != GO_LATE:
        raise ValueError(f"PRJ-02: the go model has {GO_LATE} late terms; the bins give {n_late}")
    late_n = np.bincount(late[late >= 0], minlength=n_late)
    late_go = np.bincount(late[late >= 0], weights=y[late >= 0], minlength=n_late).astype(np.int64)
    for k in range(n_late):
        if late_go[k] == 0 or late_go[k] == late_n[k]:
            raise NotImplementedError(
                f"PRJ-02 (ruling 2026-11-12): go-model late term {k} has {late_go[k]} go-fors of "
                f"{late_n[k]} decisions; its coefficient has no finite estimate"
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
        + [sd, long_ln_togo(togo, togo_upper)]
        + [(late == k).astype(np.float64) for k in range(n_late)]
    )  # fmt: skip
    fit = fit_logistic(X, y, w=w)
    j = n_cells + 2
    return GoFit(
        cell=tuple(float(b) for b in fit.coef[:n_cells]),
        cell_se=tuple(float(s) for s in fit.se[:n_cells]),
        score_differential=float(fit.coef[n_cells]),
        score_differential_se=float(fit.se[n_cells]),
        long_ln_togo=float(fit.coef[n_cells + 1]),
        long_ln_togo_se=float(fit.se[n_cells + 1]),
        late=tuple(float(b) for b in fit.coef[j : j + n_late]),
        late_se=tuple(float(s) for s in fit.se[j : j + n_late]),
        cell_n=[int(v) for v in cell_n],
        cell_go=[int(v) for v in cell_go],
        cell_other=[int(n - g) for n, g in zip(cell_n, cell_go, strict=True)],
        late_n=[int(v) for v in late_n],
        late_go=[int(v) for v in late_go],
        n=int(y.size),
        events=events,
        n_eff=n_eff,
    )


STICKS_FEATURES = ("week_index", "kind", "ydstogo", "yards_gained")


def sticks_rows(core: pl.DataFrame) -> pl.DataFrame:
    """PRJ-02 (ruling 2026-11-12, S-1): designed runs (kind 0) and completions (kind 1) on downs
    1-3, short of goal to go (ydstogo < yardline_100), with no penalty flag; scrimmage plays
    outside G7 garbage time, as the league tables. From core play rows with week_index."""
    run = pf.designed_run()
    comp = (
        (pl.col("complete_pass") == 1).fill_null(False)
        & (pl.col("pass_attempt") == 1).fill_null(False)
        & pf.scrimmage()
        & ~pf.garbage()
    )
    d = core.filter(
        pl.col("down").is_between(1, 3)
        & (pl.col("ydstogo") < pl.col("yardline_100")).fill_null(False)
        & (pl.col("penalty") != 1).fill_null(True)
        & (run | comp)
    )
    d = d.with_columns(pl.when(run).then(0).otherwise(1).cast(pl.Int64).alias("kind"))
    return d.select(STICKS_FEATURES).drop_nulls()


def sticks_reference(
    shares: dict[int, dict[int, float]],
    *,
    togo_min: int,
    togo_max: int,
    distance_upper: list[int],
    min_gap: int,
) -> dict[int, float]:
    """PRJ-02 (ruling 2026-11-12, S-1): ref_t = mean over reference distances t' (in
    [togo_min, togo_max], with plays, in t's distance bin, |t - t'| >= min_gap) of the share of
    plays at t' that gained exactly t. `shares[t'][g]`: that share."""
    edges = np.asarray(distance_upper, dtype=np.float64)

    def tbin(t: int) -> int:
        return int(np.searchsorted(edges, float(t), side="left"))

    ref: dict[int, float] = {}
    for t in range(togo_min, togo_max + 1):
        refs = [
            shares[u].get(t, 0.0)
            for u in range(togo_min, togo_max + 1)
            if u in shares and abs(t - u) >= min_gap and tbin(u) == tbin(t)
        ]
        if not refs:
            raise NotImplementedError(
                f"PRJ-02 (ruling 2026-11-12, S-1): distance {t} has no reference distance in its "
                f"bin at least {min_gap} yards away"
            )
        ref[t] = float(np.mean(refs))
    return ref


@dataclass(frozen=True)
class SticksFit:
    q: tuple[float, ...]  # STICKS_KINDS order, clamped to [0, 1]
    raw: tuple[float, ...]  # 1 - O / E before the clamp
    observed: tuple[float, ...]  # O, weighted (effective-sample-size scale)
    expected: tuple[float, ...]  # E, same scale
    n: list[int]
    n_eff: list[float]


def fit_sticks(
    rows: pl.DataFrame,
    *,
    target_index: int,
    h: float,
    togo_min: int,
    togo_max: int,
    distance_upper: list[int],
    min_gap: int,
    min_expected: int,
) -> SticksFit:
    """PRJ-02 (ruling 2026-11-12, S-1): q[kind] = clamp(1 - O / E, 0, 1). O = weighted count of
    plays at distance t (togo_min..togo_max) gaining exactly t; E = sum over t of W_t x ref_t
    (sticks_reference), W_t the weighted count of plays at t. Weights: the league weights
    rescaled to the kind's effective sample size. E < min_expected raises. `rows`:
    STICKS_FEATURES."""
    from ge.models.sim.arrays import STICKS_KINDS

    d = rows.drop_nulls(list(STICKS_FEATURES)).filter(
        pl.col("ydstogo").is_between(togo_min, togo_max)
    )
    q, raw, obs, exp, ns, neffs = [], [], [], [], [], []
    for k, name in enumerate(STICKS_KINDS):
        part = d.filter(pl.col("kind") == k)
        w = league_weights(part["week_index"].to_numpy(), target_index=target_index, h=h)
        n_eff = float(w.sum() ** 2 / np.square(w).sum()) if w.size else 0.0
        if w.size:
            w = w * (n_eff / w.sum())
        togo = part["ydstogo"].to_numpy().astype(np.float64)
        gain = part["yards_gained"].to_numpy().astype(np.float64)
        wt = {t: float(w[togo == t].sum()) for t in range(togo_min, togo_max + 1)}
        shares = {
            u: {g: float(w[(togo == u) & (gain == g)].sum()) / wt[u]
                for g in range(togo_min, togo_max + 1)}
            for u in wt if wt[u] > 0.0
        }  # fmt: skip
        ref = sticks_reference(shares, togo_min=togo_min, togo_max=togo_max,
                               distance_upper=distance_upper, min_gap=min_gap)  # fmt: skip
        o = sum(float(w[(togo == t) & (gain == t)].sum()) for t in wt)
        e = sum(wt[t] * ref[t] for t in wt)
        if e < min_expected:
            raise NotImplementedError(
                f"PRJ-02 (ruling 2026-11-12, S-1): the spot-short q for {name} needs an expected "
                f"count of at least {min_expected} gains on the line; got {e:.1f}"
            )
        r = 1.0 - o / e
        q.append(min(max(r, 0.0), 1.0))
        raw.append(r)
        obs.append(o)
        exp.append(e)
        ns.append(int(part.height))
        neffs.append(n_eff)
    return SticksFit(
        q=tuple(q), raw=tuple(raw), observed=tuple(obs), expected=tuple(exp), n=ns, n_eff=neffs
    )
