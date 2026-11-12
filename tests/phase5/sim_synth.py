"""Synthetic PRJ-02 inputs for engine tests: league tables and one game, built from simple test
settings (round numbers chosen for the tests), not from football data or facts."""

from __future__ import annotations

import numpy as np
import polars as pl

from ge.models.sim import arrays as A
from ge.models.sim.arrays import CompiledLogit, GameArrays
from ge.models.sim.league import (
    CLOCK_CATEGORIES,
    LeagueTables,
    Packed,
    pack_categories,
)


def _packed(per_cat: list[list[float]]) -> Packed:
    rows = [(k, float(v), 1.0) for k, vals in enumerate(per_cat) for v in vals]
    df = pl.DataFrame(rows, schema=["cat", "value", "w"], orient="row")
    return pack_categories(df, n_categories=len(per_cat), parent=list(range(len(per_cat))),
                           min_events=1)  # fmt: skip


def _one(vals: list[float]) -> Packed:
    return _packed([vals])


def _air_packed(air: list[list[float]]) -> Packed:
    """Bands, all attempts, then 4 x 12 (band, situation cell) categories with no rows, each
    falling back to its band (ruling 2026-11-02)."""
    cats = [*air, [v for band in air for v in band]]
    rows = [(k, float(v), 1.0) for k, vals in enumerate(cats) for v in vals]
    df = pl.DataFrame(rows, schema=["cat", "value", "w"], orient="row")
    parent = [4] * 5 + [k // 12 for k in range(48)]
    return pack_categories(df, n_categories=53, parent=parent, min_events=1)


def _run_packed(cats: list[list[float]]) -> Packed:
    """The 11 cell / every-run / short-yardage / late-down categories, then 8 x 8 (run cell,
    1st/2nd-down situation) categories with no rows, each falling back to its cell (ruling
    2026-11-03)."""
    rows = [(k, float(v), 1.0) for k, vals in enumerate(cats) for v in vals]
    df = pl.DataFrame(rows, schema=["cat", "value", "w"], orient="row")
    parent = list(range(11)) + [k // 8 for k in range(64)]
    return pack_categories(df, n_categories=75, parent=parent, min_events=1)


def _yac_packed(cats: list[list[float]]) -> Packed:
    """Bands and every completion, then 4 x 12 (band, situation cell) categories with no rows,
    each falling back to its band (ruling 2026-11-03)."""
    rows = [(k, float(v), 1.0) for k, vals in enumerate(cats) for v in vals]
    df = pl.DataFrame(rows, schema=["cat", "value", "w"], orient="row")
    parent = list(range(5)) + [k // 12 for k in range(48)]
    return pack_categories(df, n_categories=53, parent=parent, min_events=1)


def synthetic_league() -> LeagueTables:
    run = [-2.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 12.0, 25.0]
    air = [[-4.0, -2.0], [2.0, 5.0, 8.0], [11.0, 14.0, 18.0], [22.0, 30.0, 40.0]]
    nc = len(CLOCK_CATEGORIES)
    clock = [[30.0, 40.0]] * nc + [[5.0, 10.0]] * nc
    clock[CLOCK_CATEGORIES.index("incomplete")] = [4.0, 6.0]
    clock[nc + CLOCK_CATEGORIES.index("incomplete")] = [4.0, 6.0]
    for name in ("score", "try", "kickoff", "turnover", "punt", "field_goal", "penalty"):
        clock[CLOCK_CATEGORIES.index(name)] = [5.0, 8.0]
        clock[nc + CLOCK_CATEGORIES.index(name)] = [5.0, 8.0]
    n_pb = 20
    punt_rows = list(range(4))
    kick_rows = list(range(3))
    miss_rows = list(range(2))
    return LeagueTables(
        # 8 cells, every run, short yardage (ruling 2026-10-29), late down (ruling 2026-10-30);
        # every (cell, situation) uses its cell (ruling 2026-11-03)
        run_yards=_run_packed([run] * 11),
        air_yards=_air_packed(air),  # every (band, cell) uses its band (ruling 2026-11-02)
        pass_depth_offset=np.zeros((3, 4, 4)),  # no situation shift (test setting)
        band_share=np.array([0.2, 0.5, 0.2, 0.1]),
        location_share=np.full((4, 3), 1 / 3),
        yac=_yac_packed([[0.0, 3.0, 6.0, 12.0]] * 5),  # (band, cell) -> band (2026-11-03)
        int_rate_band=np.array([0.01, 0.015, 0.03, 0.06]),
        fumble_run_rate=0.01,
        fumble_completion_rate=0.005,
        fumble_sack_rate=0.05,
        sack_rate=0.06,
        sack_situation_logit=np.zeros((3, 4)),  # no situation effect (test setting)
        sack_yards=_one([-9.0, -6.0, -4.0]),
        scramble_rate=0.05,
        scramble_yards=_one([3.0, 7.0, 12.0]),
        kneel_yards=_one([-1.0]),
        run_min_gain=-2.0,
        yac_min=0.0,
        int_return_yards=_one([0.0, 10.0, 20.0]),
        fumble_return_yards=_one([0.0, 5.0]),
        penalty_offense_rate=0.03,
        penalty_defense_rate=0.02,
        penalty_offense_yards=_one([5.0, 10.0]),
        penalty_defense_yards=_one([5.0, 15.0]),
        penalty_defense_first_down=0.5,
        punt=_packed([punt_rows] * (n_pb + 1)),
        punt_changed=np.array([1.0, 1.0, 1.0, 1.0]),
        punt_next_yardline=np.array([70.0, 75.0, 80.0, 85.0]),
        punt_return_td=np.zeros(4),
        kickoff=_packed([kick_rows, kick_rows]),
        kickoff_changed=np.zeros(3),
        kickoff_next_yardline=np.array([70.0, 75.0, 80.0]),
        kickoff_return_td=np.zeros(3),
        kickoff_kicking_td=np.zeros(3),
        kickoff_season=np.zeros(3),  # the engine never reads these (K1 rows, test setting)
        kickoff_week_index=np.zeros(3),
        kickoff_late=np.zeros(3),
        kickoff_target_index=1,
        fg_intercept=6.0,
        fg_slope=-0.1,
        fg_offset=_one([17.0, 18.0]),
        fg_miss=_packed([miss_rows] * 18),
        fg_miss_changed=np.array([1.0, 1.0]),
        fg_miss_next_yardline=np.array([60.0, 65.0]),
        xp_rate=0.95,
        two_point_rate=0.45,
        clock=_packed(clock),
        timeout_rate=np.full((2, 2, 3), 0.1),
        spike_rate=0.05,
        punt_bucket_yards=5,
        fg_miss_bucket_yards=5,
        late_kickoff_seconds=300,
        two_minute_seconds=120,
    )


def _logit(intercept: float, lin: dict[int, float] | None = None) -> CompiledLogit:
    lin = lin or {}
    return CompiledLogit(
        intercept=intercept,
        lin_feat=np.array(list(lin), dtype=np.int64),
        lin_coef=np.array(list(lin.values()), dtype=np.float64),
        sq_coef=np.zeros(len(lin)),
        cat_feat=np.zeros(0, dtype=np.int64),
        cat_level=np.zeros(0),
        cat_coef=np.zeros(0),
        int_feat=np.zeros(0, dtype=np.int64),
        int_pow=np.zeros(0, dtype=np.int64),
        int_cat=np.zeros(0, dtype=np.int64),
        int_level=np.zeros(0),
        int_coef=np.zeros(0),
        int_base_level=np.zeros(0),
    )


ROSTER = ("QB1", "QB2", "RB1", "RB2", "WR1", "WR2", "WR3", "TE1")
POS = (A.POS_QB, A.POS_QB, A.POS_RB, A.POS_RB, A.POS_WR, A.POS_WR, A.POS_WR, A.POS_TE)
TARGETS = (0.0, 0.0, 0.10, 0.05, 0.25, 0.20, 0.15, 0.25)
CARRIES = (0.05, 0.0, 0.65, 0.30, 0.0, 0.0, 0.0, 0.0)


def synthetic_game(
    *, pace: float = 28.0, proe: float = 0.0, postseason: bool = False
) -> GameArrays:
    team = np.zeros((2, A.NT))
    team[:, [A.T_PACE_N, A.T_PACE_LEAD, A.T_PACE_TRAIL]] = pace
    team[:, [A.T_PROE_N, A.T_PROE_LEAD, A.T_PROE_TRAIL]] = proe
    team[:, A.T_SACK_LOGIT] = np.log(0.06 / 0.94)
    team[:, A.T_TWO_PT] = 0.1
    team[:, A.T_CELL0 : A.T_CELL0 + 8] = 1 / 8
    pmax = len(ROSTER)
    player = np.zeros((2, pmax, A.NP))
    for s in (0, 1):
        for i in range(pmax):
            p = player[s, i]
            p[A.P_TARGET] = TARGETS[i]
            p[A.P_CARRY] = CARRIES[i]
            p[[A.P_Z20, A.P_Z10, A.P_Z5]] = TARGETS[i] + CARRIES[i]
            p[A.P_EZ] = TARGETS[i]
            p[A.P_BAND0 : A.P_BAND0 + 4] = 0.25
            p[A.P_QBBAND0 : A.P_QBBAND0 + 4] = 0.25
            p[A.P_MTC02] = 1.0
            p[A.P_SCRAMBLE] = 0.05 if POS[i] == A.POS_QB else 0.0
            p[A.P_AVAIL] = 1.0
            p[A.P_POS] = POS[i]
            p[A.P_CELL0 : A.P_CELL0 + 8] = np.nan
    rules = np.zeros(A.NG, dtype=np.int64)
    rules[[A.G_TD, A.G_FG, A.G_SAFETY, A.G_TRY_KICK, A.G_TRY_2]] = (6, 3, 2, 1, 2)
    rules[[A.G_TO_GAIN, A.G_DOWNS, A.G_FIELD, A.G_PERIODS]] = (10, 4, 100, 4)
    rules[[A.G_PERIOD_SEC, A.G_TIMEOUTS, A.G_TWO_MIN, A.G_END_ZONE]] = (900, 3, 120, 10)
    ot = np.zeros(A.NO, dtype=np.int64)
    if postseason:
        ot[:] = (900, 0, 0, 3, 2, 0, 1)
    else:
        ot[:] = (600, 1, 1, 2, 0, 1, 1)
    return GameArrays(
        team=team,
        player=player,
        n_players=np.array([pmax, pmax], dtype=np.int64),
        qb_order=np.array([[0, 1], [0, 1]], dtype=np.int64),
        xpass=_logit(0.2),  # P(pass) about 0.55 in every state (test setting)
        cp=_logit(0.6),
        wp=_logit(0.0, {A.F_SCORE_DIFF: 0.15}),
        # go model (ruling 2026-10-31): cell logits by distance 1 / 2-3 / 4+ (same for every
        # field bin), no score or time slope (test setting)
        p_go=np.array([-3.3] * 3 + [-3.75] * 3 + [-5.1] * 3 + [0.0, 0.0, 0.0]),
        fg_punt=np.array([4.0, -0.11]),
        rules=rules,
        ot=ot,
        player_ids=(ROSTER, ROSTER),
    )
