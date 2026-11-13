"""PRJ-02 league level (ruling E10, 2026-10-24): the league distributions and rates the
simulation draws from, built per window from its training seasons' plays, each play weighted
0.5^(w / h_L) with w its league weeks before the target week.

Distributions are weighted empirical: the observed values with cumulative normalized weights
(a draw is a weighted resample of a real play), except YAC and run yards: weighted Kaplan-Meier
estimates with completions and runs the offense scored on censored at the goal line (rulings
2026-10-29, 2026-10-30), so the simulation's clip truncates once. Rates are weighted
frequencies. A category with fewer plays than config/sim.yaml's min_category_events uses its
parent category's draws.

Plays follow G7 (no garbage time, kneels and spikes in their own categories), as the fitted
baselines (cp, xpass) do. Field position after kicks and turnovers is the next scrimmage play's
actual position (no rulebook spot is coded)."""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import polars as pl

from ge.fit.logistic import fit_logistic
from ge.metrics import plays as pf
from ge.models.sim.settings import load_sim

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]

CLOCK_CATEGORIES = (
    "run_inbounds",
    "complete_inbounds",
    "incomplete",
    "out_of_bounds",
    "sack",
    "turnover",
    "score",
    "kneel",
    "spike",
    "penalty",
    "punt",
    "kickoff",
    "field_goal",
    "try",
)


@dataclass(frozen=True)
class Packed:
    """Weighted empirical draws for n categories: category k draws from values[lo[k]:hi[k]]
    with cumulative weights cum[lo[k]:hi[k]] (ending at 1). source[k] is the category whose
    plays it uses (itself, or its parent when it had too few)."""

    values: FloatArray
    cum: FloatArray
    lo: IntArray
    hi: IntArray
    source: IntArray
    n: IntArray  # plays per category before fallback


def censored_masses(
    value: FloatArray, censored: npt.NDArray[np.bool_], w: FloatArray
) -> FloatArray:
    """PRJ-02 YAC (ruling 2026-10-29): weighted Kaplan-Meier probability of each row, `value`
    sorted ascending. At a tie, events count before censorings (a censored play is still at
    risk at its value). The largest value is an event (Efron), so the masses sum to 1. A
    censored row gets 0; an event row its share w_i / d_v of its value's mass."""
    event = ~censored.copy()
    event[value == value[-1]] = True
    u, idx = np.unique(value, return_inverse=True)
    at_value = np.bincount(idx, weights=w, minlength=len(u))
    d = np.bincount(idx, weights=w * event, minlength=len(u))
    at_risk = np.cumsum(at_value[::-1])[::-1]
    hazard = d / at_risk
    survive = np.concatenate([[1.0], np.cumprod(1.0 - hazard)[:-1]])
    mass_v = survive * hazard
    share = np.divide(w * event, d[idx], out=np.zeros_like(w), where=d[idx] > 0)
    return np.asarray(mass_v[idx] * share, dtype=np.float64)


def pack_categories(
    df: pl.DataFrame, *, n_categories: int, parent: Sequence[int], min_events: int
) -> Packed:
    """df: cat (0..n-1), value, w, and optionally censored (bool). Values are sorted within a
    category (ties by weight). With `censored`, a category's draws are its weighted Kaplan-Meier
    estimate (censored_masses) and censored rows carry no draw; without, each row's weight."""
    d = df.drop_nulls(["cat", "value", "w"]).filter(pl.col("w") > 0).sort("cat", "value", "w")
    has_cens = "censored" in d.columns
    vals: list[float] = []
    cum: list[float] = []
    lo = np.zeros(n_categories, dtype=np.int64)
    hi = np.zeros(n_categories, dtype=np.int64)
    counts = np.zeros(n_categories, dtype=np.int64)
    for k in range(n_categories):
        part = d.filter(pl.col("cat") == k)
        counts[k] = part.height
        if part.height == 0:
            continue
        w = part["w"].to_numpy().astype(np.float64)
        v = part["value"].to_numpy().astype(np.float64)
        if has_cens:
            m = censored_masses(v, part["censored"].to_numpy().astype(np.bool_), w)
            keep = m > 0
            v = v[keep]
            c = np.cumsum(m[keep])
        else:
            c = np.cumsum(w) / w.sum()
        c[-1] = 1.0
        lo[k] = len(vals)
        vals.extend(v.tolist())
        cum.extend(c.tolist())
        hi[k] = len(vals)
    source = np.arange(n_categories, dtype=np.int64)
    for k in range(n_categories):
        if counts[k] < min_events:
            p = int(parent[k])
            if p == k or counts[p] < min_events:
                raise NotImplementedError(
                    f"PRJ-02: league category {k} has {counts[k]} plays and no usable parent"
                )
            source[k] = p
            lo[k], hi[k] = lo[p], hi[p]
    return Packed(
        values=np.asarray(vals, dtype=np.float64),
        cum=np.asarray(cum, dtype=np.float64),
        lo=lo,
        hi=hi,
        source=source,
        n=counts,
    )


def offense_scored() -> pl.Expr:
    """PRJ-02 YAC (ruling 2026-10-29): the offense scored on the play, so the goal line ended
    it and its YAC is right-censored at the distance to the goal from the catch point."""
    return _is1("touchdown") & (pl.col("td_team") == pl.col("posteam")).fill_null(False)


def pack_yac(comp: pl.DataFrame, *, min_events: int) -> Packed:
    """PRJ-02 YAC table (ruling 2026-10-29): categories are the depth bands (comp's `band`,
    0..3), then every completion (parent of each band). Each is a weighted Kaplan-Meier estimate
    with offensive-TD completions censored. The simulation then truncates at the goal line once.
    YAC by situation was removed (ruling 2026-11-12). `comp`: band, yards_after_catch, the
    offense_scored columns, w."""
    cols = (pl.col("yards_after_catch").cast(pl.Float64).alias("value"),
            offense_scored().alias("censored"), "w")  # fmt: skip
    rows = pl.concat(
        [
            comp.select(pl.col("band").cast(pl.Int64).alias("cat"), *cols),
            comp.select(pl.lit(BAND_COUNT, dtype=pl.Int64).alias("cat"), *cols),
        ]
    )
    parent = [BAND_COUNT] * (BAND_COUNT + 1)
    return pack_categories(rows, n_categories=len(parent), parent=parent, min_events=min_events)


def weighted_rate(flags: FloatArray, w: FloatArray) -> float:
    s = float(w.sum())
    if s <= 0:
        raise NotImplementedError("PRJ-02: a league rate with no weighted plays")
    return float(np.dot(flags, w) / s)


def _is1(col: str) -> pl.Expr:
    return (pl.col(col) == 1).fill_null(False)


def clock_category() -> pl.Expr:
    """PRJ-02 clock (C1): the outcome class of a play, for the runoff to the next play."""
    pt = pl.col("play_type")
    return (
        pl.when(pt == "kickoff")
        .then(pl.lit("kickoff"))
        .when(pt == "punt")
        .then(pl.lit("punt"))
        .when(pt == "field_goal")
        .then(pl.lit("field_goal"))
        .when((pt == "extra_point") | _is1("two_point_attempt"))
        .then(pl.lit("try"))
        .when(pt == "qb_kneel")
        .then(pl.lit("kneel"))
        .when(pt == "qb_spike")
        .then(pl.lit("spike"))
        .when((pt == "no_play") & _is1("penalty"))
        .then(pl.lit("penalty"))
        .when(pt == "no_play")  # timeouts and other non-plays nflverse records as no_play
        .then(pl.lit(None))
        .when(_is1("touchdown"))
        .then(pl.lit("score"))
        .when(_is1("interception") | _is1("fumble_lost"))
        .then(pl.lit("turnover"))
        .when(_is1("sack"))
        .then(pl.lit("sack"))
        .when(_is1("incomplete_pass"))
        .then(pl.lit("incomplete"))
        .when(_is1("out_of_bounds"))
        .then(pl.lit("out_of_bounds"))
        .when(_is1("complete_pass"))
        .then(pl.lit("complete_inbounds"))
        .when(pt == "run")
        .then(pl.lit("run_inbounds"))
        .otherwise(pl.lit(None))
    )


_SNAP_TYPES = ("run", "pass", "qb_kneel", "qb_spike", "field_goal", "punt", "no_play")


def next_play_outcomes(plays: pl.DataFrame, play_type: str) -> pl.DataFrame:
    """For every `play_type` play: the next scrimmage snap in the same game half (rows that are
    not snaps, such as timeouts, are skipped): whether possession changed, the next snap's
    yardline_100 (from its offense's side), and whether the play was a return touchdown."""
    snaps = (
        plays.filter(
            pl.col("play_type").is_in(_SNAP_TYPES)
            & pl.col("posteam").is_not_null()  # timeout rows: no_play with no offense
            & ((pl.col("play_type") != "no_play") | _is1("penalty"))
        )
        .select(
            "game_id",
            "game_half",
            pl.col("play_id").alias("next_play_id"),
            pl.col("posteam").alias("next_posteam"),
            pl.col("yardline_100").alias("next_yardline_100"),
        )
        .sort("game_id", "next_play_id")
    )
    kicks = plays.filter(pl.col("play_type") == play_type).sort("game_id", "play_id")
    j = kicks.join_asof(
        snaps,
        left_on="play_id",
        right_on="next_play_id",
        by=["game_id", "game_half"],
        strategy="forward",
        allow_exact_matches=False,
        check_sortedness=False,  # both sides sorted by (game_id, play id) above
    )
    return j.select(
        "game_id",
        "play_id",
        "posteam",
        "yardline_100",
        (pl.col("next_posteam") != pl.col("posteam")).alias("changed"),
        "next_yardline_100",
        _is1("return_touchdown").alias("return_td"),
    )


# ---------------------------------------------------------------- per-window tables

CORE_COLUMNS = (
    "game_id",
    "play_id",
    "season",
    "week",
    "game_half",
    "qtr",
    "posteam",
    "defteam",
    "play_type",
    "down",
    "ydstogo",
    "yardline_100",
    "game_seconds_remaining",
    "half_seconds_remaining",
    "score_differential",
    "posteam_timeouts_remaining",
    "defteam_timeouts_remaining",
    "wp",
    "pass",
    "rush",
    "qb_dropback",
    "pass_attempt",
    "complete_pass",
    "incomplete_pass",
    "sack",
    "qb_scramble",
    "qb_kneel",
    "qb_spike",
    "interception",
    "fumble_lost",
    "air_yards",
    "yards_after_catch",
    "yards_gained",
    "run_location",
    "run_gap",
    "out_of_bounds",
    "touchdown",
    "td_team",
    "return_touchdown",
    "own_kickoff_recovery_td",
    "penalty",
    "penalty_team",
    "penalty_yards",
    "first_down_penalty",
    "timeout",
    "timeout_team",
    "field_goal_attempt",
    "field_goal_result",
    "kick_distance",
    "extra_point_attempt",
    "extra_point_result",
    "two_point_attempt",
    "two_point_conv_result",
    "return_yards",
    "fumble_recovery_1_yards",
    "pass_location",
)
RUN_CELL_COUNT = len(pf.RUN_CELLS)  # 8 cells incl. unknown; category 8 = every designed run
SHORT_YARDAGE = RUN_CELL_COUNT + 1
LATE_DOWN = SHORT_YARDAGE + 1  # ruling 2026-10-30 (P5)
# run yards by situation (ruling 2026-11-03, P6): 1st and 2nd down x distance bin
# (config/sim.yaml situation_yards.distance_upper); run categories RUN_SIT0 + cell x SIT_CELLS +
# situation, each with its run cell as parent
SIT_DOWNS = 2
SIT_DIST_BINS = 4
SIT_CELLS = SIT_DOWNS * SIT_DIST_BINS
RUN_SIT0 = LATE_DOWN + 1
RUN_CATEGORIES = RUN_SIT0 + RUN_CELL_COUNT * SIT_CELLS


def situation_cell(down: npt.ArrayLike, togo: npt.ArrayLike, edges: Sequence[int]) -> IntArray:
    """Ruling 2026-11-03 (P6): (down - 1) x SIT_DIST_BINS + the first upper edge >= togo on 1st
    and 2nd down; -1 on 3rd and 4th (short yardage and late down cover them)."""
    if len(edges) != SIT_DIST_BINS - 1:
        raise ValueError(f"PRJ-02: {SIT_DIST_BINS - 1} situation distance edges expected")
    d = np.asarray(down, dtype=np.int64)
    b = np.searchsorted(np.asarray(edges, dtype=np.float64), np.asarray(togo, dtype=np.float64),
                        side="left")  # fmt: skip
    return np.asarray(np.where(d <= SIT_DOWNS, (d - 1) * SIT_DIST_BINS + b, -1), dtype=np.int64)


def pack_runs(runs: pl.DataFrame, *, min_events: int) -> Packed:
    """PRJ-02 run yards: categories are the run cells (RUN_CELLS order), every designed run,
    short yardage (ruling 2026-10-29): runs on the configured downs with ydstogo at most the
    configured distance, outside goal-to-go (the field ends those plays, so their yards would be
    cut twice), every cell pooled; and late down (ruling 2026-10-30): runs on those downs with
    more to go, every cell pooled; then one per (run cell, 1st/2nd-down situation) (ruling
    2026-11-03, P6), goal-to-go included, with its run cell as parent. Every category is a
    weighted Kaplan-Meier estimate with offensive-TD runs censored at their yards (ruling
    2026-10-30), so the simulation truncates at the goal line once. The first eleven fall back to
    every designed run."""
    sy = load_sim().short_yardage
    edges = load_sim().situation_yards.distance_upper.value
    cell_idx = {c: i for i, c in enumerate(pf.RUN_CELLS)}
    cols = (pl.col("yards_gained").cast(pl.Float64).alias("value"),
            offense_scored().alias("censored"), "w")  # fmt: skip
    on_downs = pl.col("down").is_in(sy.downs.value)
    short = (
        on_downs
        & (pl.col("ydstogo") <= sy.max_togo.value)
        & (pl.col("yardline_100") > pl.col("ydstogo"))
    ).fill_null(False)
    late = (on_downs & (pl.col("ydstogo") > sy.max_togo.value)).fill_null(False)
    cell_cat = pl.col("cell").replace_strict(cell_idx, return_dtype=pl.Int64)
    early = runs.drop_nulls(["down", "ydstogo"])
    sit = situation_cell(early["down"].to_numpy(), early["ydstogo"].to_numpy(), edges)
    early = early.with_columns(pl.Series("sit", sit)).filter(pl.col("sit") >= 0)
    rows = pl.concat(
        [
            runs.select(cell_cat.alias("cat"), *cols),
            runs.select(pl.lit(RUN_CELL_COUNT, dtype=pl.Int64).alias("cat"), *cols),
            runs.filter(short).select(pl.lit(SHORT_YARDAGE, dtype=pl.Int64).alias("cat"), *cols),
            runs.filter(late).select(pl.lit(LATE_DOWN, dtype=pl.Int64).alias("cat"), *cols),
            early.select((RUN_SIT0 + cell_cat * SIT_CELLS + pl.col("sit")).alias("cat"), *cols),
        ]
    )
    return pack_categories(rows, n_categories=RUN_CATEGORIES, min_events=min_events,
                           parent=_cell_parents(rows, RUN_SIT0, RUN_CELL_COUNT, SIT_CELLS,
                                                RUN_CELL_COUNT, min_events))  # fmt: skip


def _cell_parents(
    rows: pl.DataFrame, first: int, n_groups: int, per_group: int, every: int, min_events: int
) -> list[int]:
    """Parents for a table whose categories first.. are (group, cell): each falls back to its
    group's category (run cell or depth band), or to `every` (all plays) when the group itself
    has fewer than min_events plays, since that group then draws from `every` too (rulings
    2026-11-02, 2026-11-03). Categories before `first` fall back to `every`."""
    n = rows.drop_nulls(["cat", "value", "w"]).filter(pl.col("w") > 0).group_by("cat").len()
    count = dict(zip(n["cat"].to_list(), n["len"].to_list(), strict=True))
    groups = [g if count.get(g, 0) >= min_events else every for g in range(n_groups)]
    return [every] * first + [groups[k // per_group] for k in range(n_groups * per_group)]


SACK_DOWN_GROUPS = 3  # 1st, 2nd, 3rd/4th down (ruling 2026-10-30, P5)
SACK_DIST_BINS = 4  # config/sim.yaml sacks.distance_upper: 1-2, 3-6, 7-10, 11+


def pack_sack_offsets(drop: pl.DataFrame, *, edges: Sequence[int], min_events: int) -> FloatArray:
    """MTC-03 situation offsets (ruling 2026-10-30, P5): for each down group x distance bin,
    logit(weighted sack rate) - logit(the overall weighted rate) over drop (down, ydstogo,
    sack, w). A cell with fewer than min_events sacks uses its down group's offset; a down group
    with fewer uses 0 (the overall rate)."""
    if len(edges) != SACK_DIST_BINS - 1:
        raise ValueError(f"MTC-03: {SACK_DIST_BINS - 1} sack distance edges expected")
    d = drop.select(
        (pl.min_horizontal(pl.col("down").cast(pl.Int64), pl.lit(3)) - 1).alias("g"),
        pl.col("ydstogo").cast(pl.Float64).alias("togo"),
        (pl.col("sack") == 1).fill_null(False).cast(pl.Float64).alias("s"),
        pl.col("w").cast(pl.Float64),
    ).drop_nulls()
    g = d["g"].to_numpy()
    b = np.searchsorted(np.asarray(edges, dtype=np.float64), d["togo"].to_numpy(), side="left")
    s, w = d["s"].to_numpy(), d["w"].to_numpy()

    def logit_rate(m: npt.NDArray[np.bool_]) -> float | None:
        if int(s[m].sum()) < min_events:
            return None
        r = float((s[m] * w[m]).sum() / w[m].sum())
        return float(np.log(r / (1.0 - r)))

    base = logit_rate(np.ones(len(s), dtype=np.bool_))
    if base is None:
        raise NotImplementedError("MTC-03: too few sacks for the league situation offsets")
    out = np.zeros((SACK_DOWN_GROUPS, SACK_DIST_BINS))
    for gi in range(SACK_DOWN_GROUPS):
        grp = logit_rate(g == gi)
        for bi in range(SACK_DIST_BINS):
            cell = logit_rate((g == gi) & (b == bi))
            v = cell if cell is not None else grp
            out[gi, bi] = 0.0 if v is None else v - base
    return out


BAND_COUNT = len(pf.DEPTH_BANDS)  # 4 bands; category 4 = every attempt / completion
# pass depth by situation (ruling 2026-11-02): down group (1st, 2nd, 3rd/4th) x distance bin
# (config/sim.yaml pass_depth.distance_upper); the air table's categories AIR_CELL0 +
# band x PD_CELLS + cell, each with its band as parent
PD_DOWN_GROUPS = 3
PD_DIST_BINS = 4
PD_CELLS = PD_DOWN_GROUPS * PD_DIST_BINS
AIR_CELL0 = BAND_COUNT + 1


def depth_cell(down: npt.ArrayLike, togo: npt.ArrayLike, edges: Sequence[int]) -> IntArray:
    """Ruling 2026-11-02: (min(down, 3) - 1) x PD_DIST_BINS + the first upper edge >= togo."""
    if len(edges) != PD_DIST_BINS - 1:
        raise ValueError(f"PRJ-02: {PD_DIST_BINS - 1} pass-depth distance edges expected")
    g = np.minimum(np.asarray(down, dtype=np.int64), 3) - 1
    b = np.searchsorted(np.asarray(edges, dtype=np.float64), np.asarray(togo, dtype=np.float64),
                        side="left")  # fmt: skip
    return np.asarray(g * PD_DIST_BINS + b, dtype=np.int64)


def _with_cell(att: pl.DataFrame, edges: Sequence[int]) -> pl.DataFrame:
    c = depth_cell(att["down"].to_numpy(), att["ydstogo"].to_numpy(), edges)
    return att.with_columns(pl.Series("pd_cell", c))


def pack_depth_offsets(att: pl.DataFrame, *, edges: Sequence[int], min_events: int) -> FloatArray:
    """PRJ-02 (ruling 2026-11-02): [down group, distance bin, band] = ln(weighted band share in
    the cell / weighted band share overall) over attempts (down, ydstogo, band, w). A (cell,
    band) with fewer than min_events attempts gets 0 (no shift)."""
    d = _with_cell(att.drop_nulls(["down", "ydstogo", "band", "w"]), edges)
    cell, band, w = d["pd_cell"].to_numpy(), d["band"].to_numpy(), d["w"].to_numpy()
    overall = np.array([w[band == b].sum() for b in range(BAND_COUNT)]) / w.sum()
    out = np.zeros((PD_CELLS, BAND_COUNT))
    for c in range(PD_CELLS):
        m = cell == c
        tot = w[m].sum()
        for b in range(BAND_COUNT):
            k = m & (band == b)
            if int(k.sum()) >= min_events and overall[b] > 0.0:
                out[c, b] = float(np.log(w[k].sum() / tot / overall[b]))
    return out.reshape(PD_DOWN_GROUPS, PD_DIST_BINS, BAND_COUNT)


def pack_air(att: pl.DataFrame, *, edges: Sequence[int], min_events: int) -> Packed:
    """PRJ-02 air yards: categories 0-3 the bands, 4 every attempt (as before), then one per
    (band, situation cell) (ruling 2026-11-02) with its band as parent. `att`: down, ydstogo,
    band, air_yards, w."""
    value = pl.col("air_yards").cast(pl.Float64).alias("value")
    d = _with_cell(att.drop_nulls(["down", "ydstogo"]), edges)  # band categories keep every row
    rows = pl.concat(
        [
            att.select(pl.col("band").cast(pl.Int64).alias("cat"), value, "w"),
            att.select(pl.lit(BAND_COUNT, dtype=pl.Int64).alias("cat"), value, "w"),
            d.select((AIR_CELL0 + pl.col("band") * PD_CELLS + pl.col("pd_cell")).cast(pl.Int64)
                     .alias("cat"), value, "w"),
        ]
    )  # fmt: skip
    parent = [BAND_COUNT] * AIR_CELL0 + [k // PD_CELLS for k in range(BAND_COUNT * PD_CELLS)]
    return pack_categories(rows, n_categories=len(parent), parent=parent, min_events=min_events)


RUNNING_CLOCK = ("run_inbounds", "complete_inbounds", "sack", "kneel")
SCORE_STATES = ("trailing", "tied", "leading")


@dataclass(frozen=True)
class LeagueTables:
    """PRJ-02 league level for one window (every array is numpy, for the play loop)."""

    # RUN_CELLS order, all designed runs, short yardage (2026-10-29), late down (2026-10-30),
    # then (run cell, 1st/2nd-down situation) (2026-11-03)
    run_yards: Packed
    # DEPTH_BANDS order, all attempts, then (band, situation cell) (ruling 2026-11-02)
    air_yards: Packed
    band_share: FloatArray  # league share of attempts per band
    pass_depth_offset: FloatArray  # [down group, distance bin, band] ln share ratio (2026-11-02)
    location_share: FloatArray  # [band, PASS_LOCATIONS]: cp(state) needs a pass location
    yac: Packed  # bands, then all completions (situation categories removed 2026-11-12)
    int_rate_band: FloatArray  # per band
    fumble_run_rate: float
    fumble_completion_rate: float
    fumble_sack_rate: float
    sack_rate: float
    sack_situation_logit: FloatArray  # [down group, distance bin], MTC-03 (ruling 2026-10-30)
    sack_yards: Packed
    scramble_rate: float
    scramble_yards: Packed
    kneel_yards: Packed
    run_min_gain: float
    yac_min: float
    int_return_yards: Packed
    fumble_return_yards: Packed
    penalty_offense_rate: float
    penalty_defense_rate: float
    penalty_offense_yards: Packed
    penalty_defense_yards: Packed
    penalty_defense_first_down: float
    punt: Packed  # value = row in punt_* arrays; buckets of punt yardline, then all punts
    punt_changed: FloatArray
    punt_next_yardline: FloatArray
    punt_return_td: FloatArray
    kickoff: Packed  # value = row in kickoff_* arrays; 0 other, 1 late and kicking team trailing
    kickoff_changed: FloatArray
    kickoff_next_yardline: FloatArray
    kickoff_return_td: FloatArray  # receiving team scored on the kick
    kickoff_kicking_td: FloatArray  # kicking team scored (own recovery in the end zone)
    # K1 (ruling 2026-11-01): the raw rows behind kickoff_*, so a game rebuilds its own table
    kickoff_season: FloatArray
    kickoff_week_index: FloatArray
    kickoff_late: FloatArray  # 1 late and kicking team trailing
    kickoff_target_index: int  # the window's target week index (the test season's first week)
    fg_intercept: float
    fg_slope: float  # per yard of kick distance
    fg_offset: Packed  # kick distance - yardline_100
    fg_miss: Packed  # value = row in fg_miss_* arrays; distance buckets, then all misses
    fg_miss_changed: FloatArray
    fg_miss_next_yardline: FloatArray
    xp_rate: float
    two_point_rate: float
    clock: Packed  # category = CLOCK_CATEGORIES index + len(CLOCK_CATEGORIES) * inside_2min
    timeout_rate: FloatArray  # [half 0/1, role 0 offense/1 defense, score state]
    spike_rate: float
    punt_bucket_yards: int
    fg_miss_bucket_yards: int
    late_kickoff_seconds: int
    two_minute_seconds: int


def _w(df: pl.DataFrame, target_index: int, h: float) -> pl.DataFrame:
    return df.with_columns(
        (0.5 ** ((target_index - pl.col("week_index")) / h)).cast(pl.Float64).alias("w")
    )


def _pack1(df: pl.DataFrame, col: str, min_events: int) -> Packed:
    return pack_categories(
        df.select(pl.lit(0).alias("cat"), pl.col(col).cast(pl.Float64).alias("value"), "w"),
        n_categories=1,
        parent=[0],
        min_events=min_events,
    )


def _rate(df: pl.DataFrame, flag: pl.Expr) -> float:
    d = df.select(flag.cast(pl.Float64).alias("f"), "w").drop_nulls()
    return weighted_rate(d["f"].to_numpy(), d["w"].to_numpy())


def _rows(df: pl.DataFrame, cat: pl.Expr, n: int, parent: Sequence[int], min_events: int) -> Packed:
    """Joint outcomes: draws are row numbers of `df` (in its order)."""
    d = df.with_row_index("_r").select(
        cat.alias("cat"), pl.col("_r").cast(pl.Float64).alias("value"), "w"
    )
    return pack_categories(d, n_categories=n, parent=parent, min_events=min_events)


def _rows_bucketed(df: pl.DataFrame, bucket: pl.Expr, n_buckets: int, min_events: int) -> Packed:
    """Joint outcomes by bucket (0..n-1), with category n holding every row: a bucket with
    too few plays draws from all of them."""
    base = df.with_row_index("_r")
    d = pl.concat(
        [
            base.select(bucket.alias("cat"), pl.col("_r").cast(pl.Float64).alias("value"), "w"),
            base.select(
                pl.lit(n_buckets, dtype=pl.Int64).alias("cat"),
                pl.col("_r").cast(pl.Float64).alias("value"),
                "w",
            ),
        ]
    )
    return pack_categories(
        d, n_categories=n_buckets + 1, parent=[n_buckets] * (n_buckets + 1), min_events=min_events
    )


def kickoff_rows(plays: pl.DataFrame, late_kickoff_seconds: int) -> pl.DataFrame:
    """PRJ-02 kickoff outcomes, one row per kickoff (posteam on a kickoff row is the receiving
    team): season, week_index, late (kicking team trailing in the last late_kickoff_seconds of
    Q4 or overtime), changed, next_yardline (-1 when none), return_td (receiving team scored),
    kicking_td. `plays` carries week_index."""
    src = plays.with_columns(
        (
            (pl.col("qtr") >= 4)
            & (pl.col("game_seconds_remaining") <= late_kickoff_seconds)
            & (pl.col("score_differential") > 0)
        ).alias("late_trailing")
    )
    kos = next_play_outcomes(src, "kickoff").join(
        src.select(
            "game_id",
            "play_id",
            "season",
            "week_index",
            "late_trailing",
            "td_team",
            "own_kickoff_recovery_td",
        ),
        on=["game_id", "play_id"],
    )
    kos = kos.filter(
        pl.col("next_yardline_100").is_not_null()
        | pl.col("return_td")
        | _is1("own_kickoff_recovery_td")
    )
    return kos.select(
        "season",
        "week_index",
        pl.col("late_trailing").cast(pl.Int64).alias("late"),
        pl.col("changed").fill_null(False).cast(pl.Float64),
        pl.col("next_yardline_100").fill_null(-1.0).cast(pl.Float64).alias("next_yardline"),
        (pl.col("return_td") & (pl.col("td_team") == pl.col("posteam")).fill_null(False))
        .cast(pl.Float64)
        .alias("return_td"),
        pl.col("own_kickoff_recovery_td").fill_null(0).cast(pl.Float64).alias("kicking_td"),
    )


def game_kickoffs(
    league: LeagueTables,
    current: pl.DataFrame,
    *,
    seasons: Collection[int],
    game_index: int,
    h_l: float,
    min_events: int,
) -> LeagueTables:
    """PRJ-02 kickoff era (K1, rulings 2026-11-01, 2026-11-02): the game's kickoff table from
    the window's kickoffs in `seasons` (the game's era) plus `current`, the game's own season
    up to the game (kickoff_rows of the BT-01 snapshot), weighted 0.5^(w / h_L) with w the
    league weeks before the game. Fewer than min_events kickoffs raise."""
    if current.height and int(current["week_index"].cast(pl.Int64).max() or 0) > game_index:  # type: ignore[arg-type]
        raise ValueError("PRJ-02: a current-season kickoff after the game's week")
    keep = np.isin(league.kickoff_season, np.asarray(sorted(seasons), dtype=np.float64))
    window = pl.DataFrame(
        {
            "season": league.kickoff_season[keep].astype(np.int64),
            "week_index": league.kickoff_week_index[keep].astype(np.int64),
            "late": league.kickoff_late[keep].astype(np.int64),
            "changed": league.kickoff_changed[keep],
            "next_yardline": league.kickoff_next_yardline[keep],
            "return_td": league.kickoff_return_td[keep],
            "kicking_td": league.kickoff_kicking_td[keep],
        }
    )
    rows = pl.concat([window, current.select(window.columns).cast(window.schema)])
    n_other = int((rows["late"] == 0).sum())
    if n_other < min_events:
        raise NotImplementedError(
            f"PRJ-02 kickoff era: {n_other} kickoffs (not late) under the game's kickoff rules "
            f"before the game; the table needs {min_events}"
        )
    kos = _w(rows, game_index, h_l)
    return replace(
        league,
        kickoff=_rows(kos, pl.col("late"), 2, [0, 0], min_events),
        kickoff_changed=kos["changed"].to_numpy(),
        kickoff_next_yardline=kos["next_yardline"].to_numpy(),
        kickoff_return_td=kos["return_td"].to_numpy(),
        kickoff_kicking_td=kos["kicking_td"].to_numpy(),
        kickoff_season=kos["season"].cast(pl.Float64).to_numpy(),
        kickoff_week_index=kos["week_index"].cast(pl.Float64).to_numpy(),
        kickoff_late=kos["late"].cast(pl.Float64).to_numpy(),
    )


def build_league(
    core: pl.DataFrame,
    *,
    target_index: int,
    h_l: float,
    min_events: int,
    punt_bucket_yards: int,
    fg_miss_bucket_yards: int,
    late_kickoff_seconds: int,
    two_minute_seconds: int,
) -> LeagueTables:
    """PRJ-02 league level from one window's core play rows (CORE_COLUMNS + week_index)."""
    d = _w(core, target_index, h_l)
    live = d.filter(pf.scrimmage() & ~pf.garbage())

    runs = live.filter(pf.designed_run()).with_columns(pf.run_cell().alias("cell"))
    run_yards = pack_runs(runs, min_events=min_events)  # rulings 2026-10-29, 2026-10-30

    band_idx = {b: i for i, b in enumerate(pf.DEPTH_BANDS)}
    att = live.filter(_is1("pass_attempt") & ~_is1("sack") & pl.col("air_yards").is_not_null())
    att = att.with_columns(
        pf.depth_band().replace_strict(band_idx, return_dtype=pl.Int64).alias("band")
    )

    pd_edges = load_sim().pass_depth.distance_upper.value
    air = pack_air(att, edges=pd_edges, min_events=min_events)  # ruling 2026-11-02
    tot = float(att["w"].sum())
    band_share = np.array(
        [float(att.filter(pl.col("band") == b)["w"].sum()) / tot for b in range(BAND_COUNT)]
    )
    location_share = np.zeros((BAND_COUNT, len(pf.PASS_LOCATIONS)))
    for b in range(BAND_COUNT):
        part = att.filter((pl.col("band") == b) & pl.col("pass_location").is_not_null())
        for j, loc in enumerate(pf.PASS_LOCATIONS):
            location_share[b, j] = float(part.filter(pl.col("pass_location") == loc)["w"].sum())
        location_share[b] /= location_share[b].sum()
    comp = att.filter(_is1("complete_pass") & pl.col("yards_after_catch").is_not_null())
    # goal-line censored (ruling 2026-10-29); no situation categories (ruling 2026-11-12)
    yac = pack_yac(comp, min_events=min_events)
    int_rate_band = np.array(
        [_rate(att.filter(pl.col("band") == b), _is1("interception")) for b in range(BAND_COUNT)]
    )
    drop = live.filter(_is1("qb_dropback"))
    sacks = drop.filter(_is1("sack"))
    scr = drop.filter(~_is1("sack") & _is1("qb_scramble"))
    kneels = d.filter(pl.col("play_type") == "qb_kneel")
    ints = live.filter(_is1("interception"))
    fums = live.filter(_is1("fumble_lost"))

    snaps = d.filter(pl.col("play_type").is_in(["run", "pass", "no_play"]) & ~pf.garbage())
    pen = snaps.filter(
        (pl.col("play_type") == "no_play")
        & _is1("penalty")
        & pl.col("penalty_team").is_not_null()
        & pl.col("penalty_yards").is_not_null()
    )
    pen_off = pen.filter(pl.col("penalty_team") == pl.col("posteam"))
    pen_def = pen.filter(pl.col("penalty_team") == pl.col("defteam"))

    # punts: next snap outcomes, by bucket of the punt's yardline_100
    punts = next_play_outcomes(core, "punt").join(
        core.select("game_id", "play_id", "week_index"), on=["game_id", "play_id"]
    )
    punts = _w(punts, target_index, h_l).filter(
        pl.col("next_yardline_100").is_not_null() | pl.col("return_td")
    )
    n_pb = (100 + punt_bucket_yards - 1) // punt_bucket_yards
    punt_cat = (pl.col("yardline_100") // punt_bucket_yards).cast(pl.Int64).clip(0, n_pb - 1)
    punt = _rows_bucketed(punts, punt_cat, n_pb, min_events)

    # kickoffs (every era here; a game keeps only its own era, game_kickoffs)
    kos = _w(kickoff_rows(core, late_kickoff_seconds), target_index, h_l)
    kickoff = _rows(kos, pl.col("late"), 2, [0, 0], min_events)

    # field goals
    fga = d.filter(_is1("field_goal_attempt") & pl.col("kick_distance").is_not_null())
    y = (fga["field_goal_result"] == "made").cast(pl.Float64).to_numpy()
    X = np.column_stack([np.ones(fga.height), fga["kick_distance"].to_numpy().astype(np.float64)])
    fg = fit_logistic(X, y, w=fga["w"].to_numpy())
    fga_off = fga.with_columns((pl.col("kick_distance") - pl.col("yardline_100")).alias("off"))
    misses = next_play_outcomes(core, "field_goal").join(
        core.select("game_id", "play_id", "week_index", "field_goal_result", "kick_distance"),
        on=["game_id", "play_id"],
    )
    misses = _w(misses, target_index, h_l).filter(
        (pl.col("field_goal_result") != "made") & pl.col("next_yardline_100").is_not_null()
    )
    n_mb = 80 // fg_miss_bucket_yards + 1
    miss_cat = (pl.col("kick_distance") // fg_miss_bucket_yards).cast(pl.Int64).clip(0, n_mb - 1)
    fg_miss = _rows_bucketed(misses, miss_cat, n_mb, min_events)

    xp = d.filter(_is1("extra_point_attempt"))
    tp = d.filter(_is1("two_point_attempt"))

    clock, timeout_rate, spike_rate = clock_tables(d, two_minute_seconds, min_events)
    return LeagueTables(
        run_yards=run_yards,
        air_yards=air,
        band_share=band_share,
        pass_depth_offset=pack_depth_offsets(att, edges=pd_edges, min_events=min_events),
        location_share=location_share,
        yac=yac,
        int_rate_band=int_rate_band,
        fumble_run_rate=_rate(runs, _is1("fumble_lost")),
        fumble_completion_rate=_rate(comp, _is1("fumble_lost")),
        fumble_sack_rate=_rate(sacks, _is1("fumble_lost")),
        sack_rate=_rate(drop, _is1("sack")),
        sack_situation_logit=pack_sack_offsets(
            drop, edges=load_sim().sacks.distance_upper.value, min_events=min_events
        ),
        sack_yards=_pack1(sacks, "yards_gained", min_events),
        scramble_rate=_rate(drop.filter(~_is1("sack")), _is1("qb_scramble")),
        scramble_yards=_pack1(scr, "yards_gained", min_events),
        kneel_yards=_pack1(kneels, "yards_gained", min_events),
        run_min_gain=float(runs["yards_gained"].min()),  # type: ignore[arg-type]
        yac_min=float(comp["yards_after_catch"].min()),  # type: ignore[arg-type]
        int_return_yards=_pack1(
            ints.filter(pl.col("return_yards").is_not_null()), "return_yards", min_events
        ),
        fumble_return_yards=_pack1(
            fums.filter(pl.col("fumble_recovery_1_yards").is_not_null()),
            "fumble_recovery_1_yards",
            min_events,
        ),
        penalty_offense_rate=_rate(
            snaps,
            (pl.col("play_type") == "no_play")
            & _is1("penalty")
            & (pl.col("penalty_team") == pl.col("posteam")).fill_null(False),
        ),
        penalty_defense_rate=_rate(
            snaps,
            (pl.col("play_type") == "no_play")
            & _is1("penalty")
            & (pl.col("penalty_team") == pl.col("defteam")).fill_null(False),
        ),
        penalty_offense_yards=_pack1(pen_off, "penalty_yards", min_events),
        penalty_defense_yards=_pack1(pen_def, "penalty_yards", min_events),
        penalty_defense_first_down=_rate(pen_def, _is1("first_down_penalty")),
        punt=punt,
        punt_changed=punts["changed"].fill_null(True).cast(pl.Float64).to_numpy(),
        punt_next_yardline=punts["next_yardline_100"].fill_null(-1.0).cast(pl.Float64).to_numpy(),
        punt_return_td=punts["return_td"].cast(pl.Float64).to_numpy(),
        kickoff=kickoff,
        kickoff_changed=kos["changed"].to_numpy(),
        kickoff_next_yardline=kos["next_yardline"].to_numpy(),
        kickoff_return_td=kos["return_td"].to_numpy(),
        kickoff_kicking_td=kos["kicking_td"].to_numpy(),
        kickoff_season=kos["season"].cast(pl.Float64).to_numpy(),
        kickoff_week_index=kos["week_index"].cast(pl.Float64).to_numpy(),
        kickoff_late=kos["late"].cast(pl.Float64).to_numpy(),
        kickoff_target_index=target_index,
        fg_intercept=float(fg.coef[0]),
        fg_slope=float(fg.coef[1]),
        fg_offset=_pack1(fga_off, "off", min_events),
        fg_miss=fg_miss,
        fg_miss_changed=misses["changed"].fill_null(True).cast(pl.Float64).to_numpy(),
        fg_miss_next_yardline=misses["next_yardline_100"].cast(pl.Float64).to_numpy(),
        xp_rate=_rate(xp, pl.col("extra_point_result") == "good"),
        two_point_rate=_rate(tp, pl.col("two_point_conv_result") == "success"),
        clock=clock,
        timeout_rate=timeout_rate,
        spike_rate=spike_rate,
        punt_bucket_yards=punt_bucket_yards,
        fg_miss_bucket_yards=fg_miss_bucket_yards,
        late_kickoff_seconds=late_kickoff_seconds,
        two_minute_seconds=two_minute_seconds,
    )


def clock_tables(
    d: pl.DataFrame, two_minute: int, min_events: int
) -> tuple[Packed, FloatArray, float]:
    """Clock runoff from each play to the next snap with no timeout between (C1, E10), by the
    play's outcome class and whether it starts inside the last two minutes of a half; the rate
    at which each team calls a timeout after a running-clock play inside the last two minutes,
    by half, role and score state; and the rate of spiking the next snap there."""
    _, nxt = _snap_pairs(d)
    cat_idx = {c: i for i, c in enumerate(CLOCK_CATEGORIES)}
    nc = len(CLOCK_CATEGORIES)
    inside = (pl.col("half_seconds_remaining") <= two_minute).fill_null(False)
    runoff = nxt.filter(pl.col("_gsr_n").is_not_null() & (pl.col("_to_n") == pl.col("_to"))).select(
        (
            pl.col("cat_name").replace_strict(cat_idx, return_dtype=pl.Int64)
            + nc * inside.cast(pl.Int64)
        ).alias("cat"),
        (pl.col("game_seconds_remaining") - pl.col("_gsr_n"))
        .clip(0, None)
        .cast(pl.Float64)
        .alias("value"),
        "w",
    )
    other_regime = [*(k + nc for k in range(nc)), *range(nc)]  # the same outcome, other regime
    clock = pack_categories(runoff, n_categories=2 * nc, parent=other_regime, min_events=min_events)

    rates, spike_rate = timeout_rates(d, two_minute)
    return clock, rates, spike_rate


def _snap_pairs(d: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """(every row with a running timeout count, the snaps with their next snap's fields)."""
    rows = d.sort("game_id", "play_id").with_columns(
        _is1("timeout").cum_sum().over("game_id").alias("_to"),
        clock_category().alias("cat_name"),
    )
    snaps = rows.filter(pl.col("cat_name").is_not_null())
    nxt = snaps.with_columns(
        pl.col("game_seconds_remaining").shift(-1).over("game_id", "game_half").alias("_gsr_n"),
        pl.col("_to").shift(-1).over("game_id", "game_half").alias("_to_n"),
        pl.col("play_type").shift(-1).over("game_id", "game_half").alias("_pt_n"),
        pl.col("posteam").shift(-1).over("game_id", "game_half").alias("_pos_n"),
    )
    return rows, nxt


def timeout_rates(d: pl.DataFrame, two_minute: int) -> tuple[FloatArray, float]:
    """C9: after a running-clock play inside the last two minutes of the 2nd or 4th period,
    the rate at which a team with timeouts left calls one before the next snap, by [half,
    role (0 offense, 1 defense), score state from that team's side (trailing, tied, leading)];
    and the rate at which a trailing or tied offense spikes the next snap. A cell with no plays
    uses the same role and state in either half, then the same role in any state; with none
    at all it raises."""
    rows, nxt = _snap_pairs(d)
    inside = (pl.col("half_seconds_remaining") <= two_minute).fill_null(False)
    after = nxt.filter(
        inside
        & pl.col("cat_name").is_in(RUNNING_CLOCK)
        & pl.col("qtr").is_in([2, 4])
        & pl.col("_to_n").is_not_null()
    )
    tos = rows.filter(_is1("timeout")).select("game_id", "_to", "timeout_team")
    after = after.drop("timeout_team").join(
        tos.rename({"_to": "_to_n"}), on=["game_id", "_to_n"], how="left"
    )
    called = (pl.col("_to_n") > pl.col("_to")).fill_null(False)
    rates = np.full((2, 2, 3), np.nan)
    for role in (0, 1):
        team, left = (
            ("posteam", "posteam_timeouts_remaining")
            if role == 0
            else ("defteam", "defteam_timeouts_remaining")
        )
        sd = pl.col("score_differential") * (1 if role == 0 else -1)
        states = (sd < 0, sd == 0, sd > 0)
        flag = called & (pl.col("timeout_team") == pl.col(team)).fill_null(False)
        mine = after.filter(pl.col(left) > 0)
        for h, q in enumerate((2, 4)):
            for s, cond in enumerate(states):
                for part in (
                    mine.filter((pl.col("qtr") == q) & cond),
                    mine.filter(cond),
                    mine,
                ):
                    if part.height:
                        rates[h, role, s] = _rate(part, flag)
                        break
                else:
                    raise NotImplementedError(
                        f"PRJ-02: no running-clock plays inside two minutes for role {role}"
                    )
    sp = after.filter((pl.col("score_differential") <= 0) & (pl.col("_pos_n") == pl.col("posteam")))
    spike_rate = _rate(sp, (pl.col("_pt_n") == "qb_spike").fill_null(False))
    return rates, spike_rate


# ---------------------------------------------------------------- storage


def save_league(t: LeagueTables, path: Path) -> None:
    arrays: dict[str, Any] = {}
    for f in fields(t):
        v = getattr(t, f.name)
        if isinstance(v, Packed):
            for g in fields(v):
                arrays[f"{f.name}.{g.name}"] = getattr(v, g.name)
        else:
            arrays[f.name] = np.asarray(v)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)


def load_league(path: Path) -> LeagueTables:
    z = np.load(path)
    kw: dict[str, Any] = {}
    for f in fields(LeagueTables):
        if f.type in ("Packed", Packed):
            kw[f.name] = Packed(**{g.name: z[f"{f.name}.{g.name}"] for g in fields(Packed)})
        elif f.type in ("float", float):
            kw[f.name] = float(z[f.name])
        elif f.type in ("int", int):
            kw[f.name] = int(z[f.name])
        else:
            kw[f.name] = z[f.name]
    return LeagueTables(**kw)
