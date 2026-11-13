"""PRJ-02 simulation inputs as flat numpy arrays (structure of arrays) for the numba play loop.

Index constants name the columns of the per-team and per-player parameter arrays and of the
per-player stat lines. Side 0 is the home team, side 1 the away team. Every value is filled by
ge.models.sim.inputs from the metric engine, PRJ-01a ratings and the active fit; the loop never
reads anything else."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]

# ---- per team (as the offense; its opponent's defense is folded in), shape (2, NT)
T_PACE_N = 0  # OFF-10 seconds per play, neutral
T_PACE_LEAD = 1  # COA-04 seconds per play when leading
T_PACE_TRAIL = 2  # COA-04 seconds per play when trailing
T_PROE_N = 3  # OFF-05
T_PROE_LEAD = 4  # COA-04 PROE when leading
T_PROE_TRAIL = 5  # COA-04 PROE when trailing
T_SACK_LOGIT = 6  # MTC-03 game sack logit per dropback (league, both sides, lambda, OL)
T_CMP_SHIFT = 7  # completion logit: tilt + weather (MTC-05)
T_YAC_SHIFT = 8  # tilt beta_yac x net pass rating, yards (capped, E5)
T_INT_SHIFT = 9  # tilt beta_int x net pass rating, logit
T_YPC_SHIFT = 10  # tilt beta_ypc x net run rating + MTC-01, yards (capped, E5)
T_FUM_SHIFT = 11  # tilt beta_fum x net run rating, logit (0 when no-signal)
T_GO_OVER = 12  # COA-02 go_over_expected (probability units, E3)
T_TWO_PT = 13  # COA-03 two-point attempt rate
T_DEEP_SHIFT = 14  # MTC-05 deep-attempt logit shift
T_FG_SHIFT = 15  # MTC-05 / ENV-02 field-goal logit shift
T_EXPL_SHIFT = 16  # ENV-01 explosive-play logit shift (artificial surface)
T_CELL0 = 17  # OFF-12 carry shares, 8 cells in RUN_CELLS order
NT = T_CELL0 + 8

# ---- per player, shape (2, PMAX, NP)
P_TARGET = 0  # PLY-03 target share
P_CARRY = 1  # PLY-05 designed-carry share
P_Z20 = 2  # PLY-06 opportunity share inside the 20
P_Z10 = 3
P_Z5 = 4
P_EZ = 5  # PLY-32 end-zone target share
P_BAND0 = 6  # PLY-28 target share by depth band (4)
P_QBBAND0 = 10  # PLY-18 passer share by depth band (4; QBs)
P_CROE = 14  # PLY-10
P_YACOE = 15  # PLY-09 (capped, E5)
P_MTC02 = 16  # MTC-02 multiplier on his YAC (capped)
P_RYOE = 17  # PLY-11 per carry (capped, E5)
P_SCRAMBLE = 18  # PLY-22 scramble rate (QBs)
P_SCR_SHIFT = 19  # PLY-22 yards per rush minus its prior (QBs)
P_AVAIL = 20  # probability he plays (1; PLY-14 Questionable / Doubtful rates)
P_POS = 21  # 0 QB, 1 RB, 2 WR, 3 TE, 4 other
P_CELL0 = 22  # PLY-16 carry shares by cell (8); NaN when he has none
NP = P_CELL0 + 8
POS_QB, POS_RB, POS_WR, POS_TE, POS_OTHER = 0, 1, 2, 3, 4

# ---- per player stat line, shape (runs, 2, PMAX, NSTAT)
S_PASS_ATT = 0
S_PASS_CMP = 1
S_PASS_YDS = 2
S_PASS_TD = 3
S_INT = 4
S_RUSH_ATT = 5
S_RUSH_YDS = 6
S_RUSH_TD = 7
S_TARGETS = 8
S_REC = 9
S_REC_YDS = 10
S_REC_TD = 11
S_FUM_LOST = 12
S_PLAYED = 13
NSTAT = 14

# ---- per team stat line, shape (runs, 2, NTEAM)
R_POINTS = 0
R_OFF_TD = 1  # offensive touchdowns (rush + receiving)
R_PASS_YDS = 2  # gross passing yards (receivers' yards; sacks excluded)
R_RUSH_YDS = 3
R_PLAYS = 4  # OFF-11 qualifying plays (dropbacks incl. sacks and scrambles, designed runs)
R_PASS_PLAYS = 5  # dropbacks (sacks and scrambles included)
R_PASS_ATT = 6
R_DRIVES = 7
R_SACK_YDS = 8
R_FG_ATT = 9
R_FG_MADE = 10
R_PUNTS = 11
R_GIVEAWAYS = 12  # interceptions + fumbles lost
R_DOWNS = 13  # turnovers on downs
R_COMP = 14
R_PLAYS_G7 = 15  # R_PLAYS outside G7 garbage time (wp(state) < 0.05 or > 0.95 in the 4th+)
R_PASS_PLAYS_G7 = 16
R_FIRST_DOWNS = 17  # first downs gained by a play (penalties not counted)
R_THIRD_ATT = 18
R_THIRD_CONV = 19
R_RUSH_ATT = 20  # designed runs + scrambles
R_ATT_B0 = 21  # pass attempts by depth band (4): behind, short, intermediate, deep
R_CMP_B0 = 25  # completions by band (4)
R_YDS_B0 = 29  # passing yards by band (4)
# Diagnostic counters (approved 2026-10-27; they read the play, never draw): air yards in
# tenths on every attempt and on completions, YAC in tenths on completions (after its shifts and
# floor, before rounding and the goal-line clip), by band (4 each)
R_AIR_ATT_B0 = 33
R_AIR_CMP_B0 = 37
R_YAC_CMP_B0 = 41
R_GL_CLIPS = 45  # completions whose air + YAC passed the goal line
R_GL_CLIP_YDS = 46  # yards removed by that clip
R_AIR_REDRAWS = 47  # attempts whose first air draw was past the end-zone back line
R_AIR_CAPS = 48  # attempts still past it after every redraw (air capped)
THIRD_BINS = 6  # 3rd-down distance bins: 1, 2, 3, 4-6, 7-10, 11+
R_THIRD_ATT_RUN0 = 49  # designed runs on 3rd down, by bin (6)
R_THIRD_CONV_RUN0 = 55
R_THIRD_ATT_PASS0 = 61  # dropbacks (sacks and scrambles included) on 3rd down, by bin (6)
R_THIRD_CONV_PASS0 = 67
# Diagnostic counters (approved 2026-10-30; they read the play, never draw; bins in
# config/sim.yaml `diagnostics`):
R_RZ_TRIPS = 73  # drives with any snap at yardline_100 <= 20
R_RZ_TD = 74  # of those, drives ending in an offensive TD
R_RZ_FG_ATT = 75  # of those, drives ending in a field-goal attempt
FOURTH_CELLS = 9  # 4th-down cell = distance bin (1, 2-3, 4+) x 3 + field bin (<= 40, 41-60, > 60)
R_4TH_N0 = 76  # 4th-down designed runs, dropbacks, FG attempts and punts, by cell (9)
R_4TH_GO0 = 85  # of those, designed runs and dropbacks
R_4TH_CONV0 = 94  # of those, converted (gain >= distance or offensive TD, no turnover)
EARLY_KINDS = 5  # 1st/2nd-down play kinds: designed run, scramble, sack, short pass, deep pass
E_RUN, E_SCRAMBLE, E_SACK, E_SHORT, E_DEEP = range(EARLY_KINDS)
R_EARLY_N0 = 103  # plays by (down - 1) x EARLY_KINDS + kind (10)
R_EARLY_YDS0 = 113  # yards applied to the ball (0 on incompletions and interceptions) (10)
R_SECOND_ATT0 = 123  # 2nd-down plays by distance bin (THIRD_BINS)
R_SECOND_CONV0 = 129
R_PEN_OFF = 135  # no-play penalties applied, offense
R_PEN_DEF = 136  # no-play penalties applied, defense
R_PEN_DEF_FD = 137  # defensive no-play penalties that gave a first down
R_END_HALF = 138  # possessions alive when the 2nd or 4th period or an overtime period ended
FG_DIST_BINS = 4  # kick distance < 30, 30-39, 40-49, 50+
R_FG_ATT_D0 = 139
R_FG_MADE_D0 = 143
NTEAM = 147

# ---- PRJ-02 4th-down go model (ruling 2026-10-31): one logit per distance x field cell
# (config/sim.yaml `fourth_go`; cell = distance bin x 3 + field bin), then the slopes on
# score_differential; ruling 2026-11-01: long_ln_togo = slope on ln(ydstogo / L) in the last
# distance bin; ruling 2026-11-12 (G-2): one term per trailing bin x late-time bin
# (config/sim.yaml fourth_go.trail_upper, late_seconds_upper), replacing the game-seconds slope
GO_CELLS = 9
GO_TRAIL_BINS = 2
GO_TIME_BINS = 2
GO_LATE = GO_TRAIL_BINS * GO_TIME_BINS
GO_TERMS = (
    *(f"cell{c}" for c in range(GO_CELLS)),
    "sd",
    "long_ln_togo",
    *(f"trail{b}_time{k}" for b in range(GO_TRAIL_BINS) for k in range(GO_TIME_BINS)),
)


def go_key(term: str) -> str:
    """Fit key of one go-model term."""
    return f"fit:PRJ-02/go/{term}"


# ---- PRJ-02 sticks spot-short (ruling 2026-11-12, S-1): q per play kind
STICKS_KINDS = ("run", "completion")


def sticks_key(kind: str) -> str:
    """Fit key of one spot-short probability."""
    return f"fit:PRJ-02/sticks/{kind}"


# ---- model feature ids (CompiledLogit)
F_DOWN = 0
F_YDSTOGO = 1
F_YL = 2
F_QTR = 3
F_HALF_SEC = 4
F_GAME_SEC = 5
F_SCORE_DIFF = 6
F_WP = 7
F_POS_TO = 8
F_DEF_TO = 9
F_AIR = 10
F_LOC = 11  # 0 left, 1 middle, 2 right
F_TOGO_BIN = 12  # xpass distance bin (ruling 2026-10-29), set from F_YDSTOGO by the loop
NF = 13
FEATURE_IDS = {
    "down": F_DOWN,
    "ydstogo": F_YDSTOGO,
    "yardline_100": F_YL,
    "qtr": F_QTR,
    "half_seconds_remaining": F_HALF_SEC,
    "game_seconds_remaining": F_GAME_SEC,
    "score_differential": F_SCORE_DIFF,
    "wp": F_WP,
    "posteam_timeouts_remaining": F_POS_TO,
    "defteam_timeouts_remaining": F_DEF_TO,
    "air_yards": F_AIR,
    "pass_location": F_LOC,
    "ydstogo_bin": F_TOGO_BIN,
}
LOCATION_CODES = {"left": 0.0, "middle": 1.0, "right": 2.0}

# ---- game rules (config/game_rules.yaml) and overtime (config/overtime.yaml) as int arrays
G_TD, G_FG, G_SAFETY, G_TRY_KICK, G_TRY_2 = 0, 1, 2, 3, 4
G_TO_GAIN, G_DOWNS, G_FIELD, G_PERIODS, G_PERIOD_SEC, G_TIMEOUTS, G_TWO_MIN = 5, 6, 7, 8, 9, 10, 11
G_END_ZONE = 12
NG = 13
O_PERIOD_SEC, O_MAX_PERIODS, O_TIES, O_TIMEOUTS, O_TO_RESET, O_OPEN_TD, O_OPEN_SAFETY = range(7)
NO = 7


@dataclass(frozen=True)
class CompiledLogit:
    """A distilled model (ruling D4) evaluated in the loop: eta = intercept + sum over linear
    terms (coef x x + sq_coef x x^2) + sum over indicator terms (coef if x == level)."""

    intercept: float
    lin_feat: IntArray
    lin_coef: FloatArray
    sq_coef: FloatArray
    cat_feat: IntArray
    cat_level: FloatArray
    cat_coef: FloatArray
    # ruling 2026-10-25: coef x x^power when the condition feature equals the level; power 0
    # (ruling 2026-10-29, distance bins): coef when x also equals int_base_level
    int_feat: IntArray
    int_pow: IntArray
    int_cat: IntArray
    int_level: FloatArray
    int_coef: FloatArray
    int_base_level: FloatArray


def compile_logit(coefs: dict[str, float]) -> CompiledLogit:
    """From the fitted terms (fit:PRJ-02/<model>/<term>, as ge.fit.distill.design names them)."""
    lin: dict[str, list[float]] = {}
    cat: list[tuple[int, float, float]] = []
    inter: list[tuple[int, int, int, float, float, float]] = []
    for term, b in coefs.items():
        if term == "intercept":
            continue
        if "|" in term:
            base, cond = term.split("|", 1)
            f, lv = cond.split("=", 1)
            if "=" in base:  # an indicator within a level: ydstogo_bin=<k>|down=<d>
                bf, blv = base.split("=", 1)
                inter.append((FEATURE_IDS[bf], 0, FEATURE_IDS[f], float(lv), float(b), float(blv)))
                continue
            power = 2 if base.endswith("^2") else 1
            inter.append(
                (FEATURE_IDS[base.removesuffix("^2")], power, FEATURE_IDS[f], float(lv), float(b),
                 0.0)
            )  # fmt: skip
        elif "=" in term:
            f, lv = term.split("=", 1)
            level = LOCATION_CODES[lv] if f == "pass_location" else float(lv)
            cat.append((FEATURE_IDS[f], level, float(b)))
        elif term.endswith("^2"):
            lin.setdefault(term[:-2], [0.0, 0.0])[1] = float(b)
        else:
            lin.setdefault(term, [0.0, 0.0])[0] = float(b)
    return CompiledLogit(
        intercept=float(coefs["intercept"]),
        lin_feat=np.array([FEATURE_IDS[f] for f in lin], dtype=np.int64),
        lin_coef=np.array([v[0] for v in lin.values()], dtype=np.float64),
        sq_coef=np.array([v[1] for v in lin.values()], dtype=np.float64),
        cat_feat=np.array([c[0] for c in cat], dtype=np.int64),
        cat_level=np.array([c[1] for c in cat], dtype=np.float64),
        cat_coef=np.array([c[2] for c in cat], dtype=np.float64),
        int_feat=np.array([i[0] for i in inter], dtype=np.int64),
        int_pow=np.array([i[1] for i in inter], dtype=np.int64),
        int_cat=np.array([i[2] for i in inter], dtype=np.int64),
        int_level=np.array([i[3] for i in inter], dtype=np.float64),
        int_coef=np.array([i[4] for i in inter], dtype=np.float64),
        int_base_level=np.array([i[5] for i in inter], dtype=np.float64),
    )


@dataclass(frozen=True)
class GameArrays:
    """Everything one game's simulation reads besides the league tables."""

    team: FloatArray  # (2, NT)
    player: FloatArray  # (2, PMAX, NP)
    n_players: IntArray  # (2,)
    qb_order: IntArray  # (2, QMAX): player indices of the team's QBs in slot order; -1 pads
    xpass: CompiledLogit
    cp: CompiledLogit
    wp: CompiledLogit
    p_go: FloatArray  # PRJ-02 go model (ruling 2026-10-31): GO_TERMS order, see go_key
    fg_punt: FloatArray  # ruling C8: intercept, slope on yardline_100
    sticks_q: FloatArray  # ruling 2026-11-12 (S-1): spot-short q, STICKS_KINDS order
    rules: IntArray  # (NG,)
    ot: IntArray  # (NO,)
    player_ids: tuple[tuple[str, ...], tuple[str, ...]]  # gsis ids per side, for the outputs
