"""PRJ-02 game simulation: the numba play loop (MODEL_SPEC section 7, steps 1-6, with the
rating tilt, league level, overtime and weather rules, rulings C1-C12 and E1-E14).

One game is N runs. The runs are split into a fixed number of chunks (config/sim.yaml, E12);
chunk c draws from its own numpy Generator spawned from a SeedSequence seeded by
sha256(game_id, model_version), so the output is byte-identical whether the chunks run one
after another or in parallel threads.

Per play: the state (possession, down, distance, yardline, clock, score, timeouts); kneel,
spike and timeout decisions (C9); 4th-down choice (the league go model by distance x field
cell + score + time, ruling 2026-10-31, plus COA-02's go over expected, E3; field goal vs punt,
C8);
accepted no-play penalties (E10); the play call P(dropback) = xpass(state) + the offense's PROE
for its game script (OFF-05 when neutral, COA-04 when leading or trailing by wp(state), E1);
sack (MTC-03), scramble (PLY-22) or pass attempt; designed runs. Passes: target (PLY-03, zone
shares inside the 20, 10 and 5 split by each player's own target/carry mix, PLY-32 for
end-zone throws), depth band (passer x target / league shares, ruling 2026-10-25), air yards
and pass location
(league), interception (league by band + tilt), completion (cp(state) + CROE, C6, + tilt +
weather), yards after catch (league by band; situation cells removed by ruling 2026-11-12;
explosive reweighting for surface, tilt, PLY-09, MTC-02). Runs: carrier (PLY-05 / zone shares),
cell (PLY-16 or OFF-12), yards (league by cell and 1st/2nd-down situation, ruling 2026-11-03,
or the league short-yardage category on 3rd/4th and short, ruling 2026-10-29, or the late-down
category on 3rd/4th with more to go, ruling 2026-10-30; + tilt + MTC-01 + PLY-11, clipped,
C4), fumbles. Sacks: MTC-03 game logit + a league offset by down group and distance (ruling
2026-10-30). Special teams and clock from the league tables
(E10). Overtime from config/overtime.yaml. Stat lines, team totals and the first TD scorer are
recorded per run.

Simplifications (stated in the Phase 5 report): penalties are no-play penalties only, without
the half-distance rule; interception and fumble returns are clamped to the field (no
touchbacks); there is no end-of-half field-goal attempt before 4th down; kneels only in the 4th
period and overtime."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from numba import njit

from ge.config import load_params
from ge.models.sim import arrays as A
from ge.models.sim.arrays import CompiledLogit, GameArrays
from ge.models.sim.league import (
    AIR_CELL0,
    BAND_COUNT,
    CLOCK_CATEGORIES,
    LATE_DOWN,
    PD_CELLS,
    PD_DIST_BINS,
    PD_DOWN_GROUPS,
    RUN_CATEGORIES,
    RUN_CELL_COUNT,
    RUN_SIT0,
    SACK_DIST_BINS,
    SACK_DOWN_GROUPS,
    SHORT_YARDAGE,
    SIT_CELLS,
    SIT_DIST_BINS,
    SIT_DOWNS,
    LeagueTables,
    Packed,
)
from ge.models.sim.settings import load_sim

FloatArray = npt.NDArray[np.float64]
IntArray = npt.NDArray[np.int64]

# ---- merged packed tables: base category index of each table in lo / hi
TB_RUN, TB_AIR, TB_YAC, TB_SACK, TB_SCR, TB_KNEEL, TB_INTRET, TB_FUMRET = range(8)
TB_PEN_OFF, TB_PEN_DEF, TB_PUNT, TB_KO, TB_FGOFF, TB_MISS, TB_CLOCK = range(8, 15)
NTB = 15
# ---- league scalars
(
    LS_FUM_RUN,
    LS_FUM_COMP,
    LS_FUM_SACK,
    LS_RUN_MIN,
    LS_YAC_MIN,
    LS_PEN_OFF,
    LS_PEN_DEF,
    LS_PEN_FD,
    LS_FG_INT,
    LS_FG_SLOPE,
    LS_XP,
    LS_2PT,
    LS_SPIKE,
    LS_PUNT_BUCKET,
    LS_MISS_BUCKET,
    LS_LATE_KO,
    LS_TWO_MIN,
    LS_PACE_REF,
    LS_KNEEL_RUNOFF,
    LS_LEAD_WP,
    LS_TRAIL_WP,
    LS_EXPL_RUN,
    LS_EXPL_PASS,
    LS_N_PUNT_BUCKETS,
    LS_N_MISS_BUCKETS,
    LS_G7_LOW,
    LS_G7_HIGH,
    LS_SY_MAX_TOGO,
    LS_N_TOGO_EDGES,
    LS_RZ_YL,
    LS_DEEP_AIR,
    LS_STICKS_TOGO_MIN,  # ruling 2026-11-12 (S-1)
    LS_STICKS_TOGO_MAX,
) = range(33)
NLS = 33
# ---- league vectors
LA_INT0, LA_BAND0, LA_LOC0, LA_TO0 = 0, 4, 8, 20
LA_SY_DOWN0 = 32  # 1.0 when down d (1-4) is a short-yardage down (ruling 2026-10-29)
LA_TOGO_EDGE0 = 36  # xpass distance-bin upper edges (ruling 2026-10-29)
MAX_TOGO_EDGES = 8
# diagnostic counter bins (approved 2026-10-30)
LA_4TH_TOGO0 = LA_TOGO_EDGE0 + MAX_TOGO_EDGES  # 4th-down distance upper edges (2)
LA_4TH_YL0 = LA_4TH_TOGO0 + 2  # 4th-down yardline upper edges (2)
LA_FG_DIST0 = LA_4TH_YL0 + 2  # field-goal distance lower edges (FG_DIST_BINS - 1)
# MTC-03 sack situation offsets and distance edges (ruling 2026-10-30, P5)
LA_SACK0 = LA_FG_DIST0 + A.FG_DIST_BINS - 1  # [down group x SACK_DIST_BINS + bin]
LA_SACK_EDGE0 = LA_SACK0 + SACK_DOWN_GROUPS * SACK_DIST_BINS
# 4th-down go model bins (ruling 2026-10-31): distance and yardline upper edges (2 each)
LA_GO_TOGO0 = LA_SACK_EDGE0 + SACK_DIST_BINS - 1
LA_GO_YL0 = LA_GO_TOGO0 + 2
# pass depth by situation (ruling 2026-11-02): offsets [cell x BAND_COUNT + band], then edges
LA_PD0 = LA_GO_YL0 + 2
LA_PD_EDGE0 = LA_PD0 + PD_CELLS * BAND_COUNT
# run yards by situation (ruling 2026-11-03, P6): 1st/2nd-down distance upper edges
LA_SIT_EDGE0 = LA_PD_EDGE0 + PD_DIST_BINS - 1
# go model trailing x late-time bins (ruling 2026-11-12, G-2): deficit and time upper edges
LA_GO_TRAIL0 = LA_SIT_EDGE0 + SIT_DIST_BINS - 1
LA_GO_LATE0 = LA_GO_TRAIL0 + A.GO_TRAIL_BINS - 1
NLA = LA_GO_LATE0 + A.GO_TIME_BINS
C_RUN_IN = CLOCK_CATEGORIES.index("run_inbounds")
C_COMP_IN = CLOCK_CATEGORIES.index("complete_inbounds")
C_INC = CLOCK_CATEGORIES.index("incomplete")
C_OOB = CLOCK_CATEGORIES.index("out_of_bounds")
C_SACK = CLOCK_CATEGORIES.index("sack")
C_TURN = CLOCK_CATEGORIES.index("turnover")
C_SCORE = CLOCK_CATEGORIES.index("score")
C_KNEEL = CLOCK_CATEGORIES.index("kneel")
C_SPIKE = CLOCK_CATEGORIES.index("spike")
C_PEN = CLOCK_CATEGORIES.index("penalty")
C_PUNT = CLOCK_CATEGORIES.index("punt")
C_KO = CLOCK_CATEGORIES.index("kickoff")
C_FG = CLOCK_CATEGORIES.index("field_goal")
C_TRY = CLOCK_CATEGORIES.index("try")
NCLK = len(CLOCK_CATEGORIES)


@dataclass(frozen=True)
class SimResult:
    team: npt.NDArray[np.int32]  # (runs, 2, NTEAM)
    player: npt.NDArray[np.int32]  # (runs, 2, PMAX, NSTAT)
    first_td: npt.NDArray[np.int32]  # (runs, 2): side, player index (-1: team/def/ST TD)
    ot: npt.NDArray[np.int8]  # (runs,): 1 when the game went to overtime
    player_ids: tuple[tuple[str, ...], tuple[str, ...]]


# ---------------------------------------------------------------- packing (Python)


def _merge(packs: Sequence[Packed]) -> tuple[FloatArray, FloatArray, IntArray, IntArray, IntArray]:
    values = np.concatenate([p.values for p in packs])
    cum = np.concatenate([p.cum for p in packs])
    lo: list[int] = []
    hi: list[int] = []
    base: list[int] = []
    off = 0
    for p in packs:
        base.append(len(lo))
        lo.extend((p.lo + off).tolist())
        hi.extend((p.hi + off).tolist())
        off += len(p.values)
    return (
        values,
        cum,
        np.asarray(lo, dtype=np.int64),
        np.asarray(hi, dtype=np.int64),
        np.asarray(base, dtype=np.int64),
    )


def _mean(p: Packed, k: int) -> float:
    v = p.values[p.lo[k] : p.hi[k]]
    c = p.cum[p.lo[k] : p.hi[k]]
    return float(np.dot(v, np.diff(np.concatenate([[0.0], c]))))


def league_arrays(t: LeagueTables) -> tuple[object, ...]:
    """The league tables as the loop's arrays (merged packs, scalars, vectors, joint rows)."""
    packs = (
        t.run_yards,
        t.air_yards,
        t.yac,
        t.sack_yards,
        t.scramble_yards,
        t.kneel_yards,
        t.int_return_yards,
        t.fumble_return_yards,
        t.penalty_offense_yards,
        t.penalty_defense_yards,
        t.punt,
        t.kickoff,
        t.fg_offset,
        t.fg_miss,
        t.clock,
    )
    if len(t.run_yards.lo) == SHORT_YARDAGE + 1:
        raise ValueError(
            "PRJ-02: the league run table has no late-down category (ruling 2026-10-30); "
            "rebuild the league tables"
        )
    if len(t.run_yards.lo) == LATE_DOWN + 1:
        raise ValueError(
            "PRJ-02: the league run table has no situation categories (ruling 2026-11-03); "
            "rebuild the league tables"
        )
    if len(t.run_yards.lo) != RUN_CATEGORIES:
        raise ValueError(
            "PRJ-02: the league run table has no short-yardage category (ruling 2026-10-29); "
            "rebuild the league tables"
        )
    if len(t.yac.lo) != BAND_COUNT + 1:
        raise ValueError(
            "PRJ-02: the league YAC table has situation categories, removed by ruling "
            "2026-11-12; rebuild the league tables"
        )
    sit_edges = load_sim().situation_yards.distance_upper.value
    if len(sit_edges) != SIT_DIST_BINS - 1:
        raise ValueError("PRJ-02: the run situation edges do not match config/sim.yaml")
    if sorted(load_sim().short_yardage.downs.value) != list(range(SIT_DOWNS + 1, 5)):
        raise ValueError(
            f"PRJ-02: run situations cover downs 1-{SIT_DOWNS}; short yardage and late down "
            "must cover the others (rulings 2026-10-29, 2026-11-03)"
        )
    sack_edges = load_sim().sacks.distance_upper.value
    if len(sack_edges) != SACK_DIST_BINS - 1 or t.sack_situation_logit.shape != (
        SACK_DOWN_GROUPS,
        SACK_DIST_BINS,
    ):
        raise ValueError("MTC-03: the sack situation offsets do not match config/sim.yaml")
    pd_edges = load_sim().pass_depth.distance_upper.value
    if len(t.air_yards.lo) != AIR_CELL0 + BAND_COUNT * PD_CELLS:
        raise ValueError(
            "PRJ-02: the league air table has no situation categories (ruling 2026-11-02); "
            "rebuild the league tables"
        )
    if len(pd_edges) != PD_DIST_BINS - 1 or t.pass_depth_offset.shape != (
        PD_DOWN_GROUPS,
        PD_DIST_BINS,
        BAND_COUNT,
    ):
        raise ValueError("PRJ-02: the pass-depth offsets do not match config/sim.yaml")
    values, cum, lo, hi, base = _merge(packs)
    p = load_params()
    sim = load_sim()
    edges = sim.distill.xpass_togo_bin_upper.value
    if len(edges) > MAX_TOGO_EDGES:
        raise ValueError(f"PRJ-02: at most {MAX_TOGO_EDGES} xpass distance-bin edges")
    dg = sim.diagnostics
    f_togo, f_yl, fg_lower = (
        dg.fourth_togo_upper.value,
        dg.fourth_yardline_upper.value,
        dg.fg_distance_lower.value,
    )
    if len(f_togo) != 2 or len(f_yl) != 2 or len(fg_lower) != A.FG_DIST_BINS - 1:
        raise ValueError("PRJ-02: the diagnostic counter bins do not match the counter layout")
    go_togo, go_yl = sim.fourth_go.togo_upper.value, sim.fourth_go.yardline_upper.value
    if len(go_togo) != 2 or len(go_yl) != 2:
        raise ValueError(f"PRJ-02: the go model's {A.GO_CELLS} cells need 2 edges per bin set")
    go_trail, go_late_s = sim.fourth_go.trail_upper.value, sim.fourth_go.late_seconds_upper.value
    if len(go_trail) != A.GO_TRAIL_BINS - 1 or len(go_late_s) != A.GO_TIME_BINS:
        raise ValueError(
            f"PRJ-02: the go model's {A.GO_LATE} late terms need {A.GO_TRAIL_BINS - 1} deficit "
            f"edge(s) and {A.GO_TIME_BINS} time edges (ruling 2026-11-12)"
        )
    ls = np.zeros(NLS)
    ls[LS_FUM_RUN] = t.fumble_run_rate
    ls[LS_FUM_COMP] = t.fumble_completion_rate
    ls[LS_FUM_SACK] = t.fumble_sack_rate
    ls[LS_RUN_MIN] = t.run_min_gain
    ls[LS_YAC_MIN] = t.yac_min
    ls[LS_PEN_OFF] = t.penalty_offense_rate
    ls[LS_PEN_DEF] = t.penalty_defense_rate
    ls[LS_PEN_FD] = t.penalty_defense_first_down
    ls[LS_FG_INT] = t.fg_intercept
    ls[LS_FG_SLOPE] = t.fg_slope
    ls[LS_XP] = t.xp_rate
    ls[LS_2PT] = t.two_point_rate
    ls[LS_SPIKE] = t.spike_rate
    ls[LS_PUNT_BUCKET] = t.punt_bucket_yards
    ls[LS_MISS_BUCKET] = t.fg_miss_bucket_yards
    ls[LS_LATE_KO] = t.late_kickoff_seconds
    ls[LS_TWO_MIN] = t.two_minute_seconds
    n_run = t.clock.n[C_RUN_IN]
    n_cmp = t.clock.n[C_COMP_IN]
    ls[LS_PACE_REF] = (n_run * _mean(t.clock, C_RUN_IN) + n_cmp * _mean(t.clock, C_COMP_IN)) / (
        n_run + n_cmp
    )
    ls[LS_KNEEL_RUNOFF] = _mean(t.clock, NCLK + C_KNEEL)
    ls[LS_LEAD_WP] = float(p.coaching.coa_04_leading_min_wp.value)
    ls[LS_TRAIL_WP] = float(p.coaching.coa_04_trailing_max_wp.value)
    ls[LS_EXPL_RUN] = float(p.offense.off_12_explosive_run_min_yards.value)
    ls[LS_EXPL_PASS] = float(p.defense.def_06_explosive_pass_min_yards.value)
    ls[LS_N_PUNT_BUCKETS] = len(t.punt.lo) - 1
    ls[LS_N_MISS_BUCKETS] = len(t.fg_miss.lo) - 1
    ls[LS_G7_LOW] = float(p.conventions.g7_garbage_wp_low.value)
    ls[LS_G7_HIGH] = float(p.conventions.g7_garbage_wp_high.value)
    ls[LS_SY_MAX_TOGO] = float(sim.short_yardage.max_togo.value)
    ls[LS_N_TOGO_EDGES] = len(edges)
    ls[LS_RZ_YL] = float(dg.red_zone_max_yardline.value)
    ls[LS_DEEP_AIR] = float(dg.early_deep_air_min.value)
    ls[LS_STICKS_TOGO_MIN] = float(sim.sticks.togo_min.value)
    ls[LS_STICKS_TOGO_MAX] = float(sim.sticks.togo_max.value)
    la = np.zeros(NLA)
    la[LA_4TH_TOGO0 : LA_4TH_TOGO0 + 2] = f_togo
    la[LA_4TH_YL0 : LA_4TH_YL0 + 2] = f_yl
    la[LA_FG_DIST0 : LA_FG_DIST0 + len(fg_lower)] = fg_lower
    la[LA_SACK0:LA_SACK_EDGE0] = t.sack_situation_logit.reshape(-1)
    la[LA_SACK_EDGE0:LA_GO_TOGO0] = sack_edges
    la[LA_GO_TOGO0 : LA_GO_TOGO0 + 2] = go_togo
    la[LA_GO_YL0 : LA_GO_YL0 + 2] = go_yl
    la[LA_PD0:LA_PD_EDGE0] = t.pass_depth_offset.reshape(-1)
    la[LA_PD_EDGE0:LA_SIT_EDGE0] = pd_edges
    la[LA_SIT_EDGE0:LA_GO_TRAIL0] = sit_edges
    la[LA_GO_TRAIL0:LA_GO_LATE0] = go_trail
    la[LA_GO_LATE0:NLA] = go_late_s
    for d in sim.short_yardage.downs.value:
        la[LA_SY_DOWN0 + d - 1] = 1.0
    la[LA_TOGO_EDGE0 : LA_TOGO_EDGE0 + len(edges)] = edges
    la[LA_INT0 : LA_INT0 + 4] = t.int_rate_band
    la[LA_BAND0 : LA_BAND0 + 4] = t.band_share
    la[LA_LOC0 : LA_LOC0 + 12] = t.location_share.reshape(-1)
    la[LA_TO0 : LA_TO0 + 12] = t.timeout_rate.reshape(-1)
    punt = np.column_stack([t.punt_changed, t.punt_next_yardline, t.punt_return_td])
    ko = np.column_stack(
        [t.kickoff_changed, t.kickoff_next_yardline, t.kickoff_return_td, t.kickoff_kicking_td]
    )
    miss = np.column_stack([t.fg_miss_changed, t.fg_miss_next_yardline])
    return values, cum, lo, hi, base, ls, la, punt, ko, miss


def _logit_arrays(m: CompiledLogit) -> tuple[object, ...]:
    return (
        np.array([m.intercept]),
        m.lin_feat,
        m.lin_coef,
        m.sq_coef,
        m.cat_feat,
        m.cat_level,
        m.cat_coef,
        m.int_feat,
        m.int_pow,
        m.int_cat,
        m.int_level,
        m.int_coef,
        m.int_base_level,
    )


def seeds(game_id: str, model_version: str, chunks: int) -> list[np.random.SeedSequence]:
    """CLAUDE.md rule 6 / E12: chunk seeds from sha256(game_id, model_version)."""
    h = hashlib.sha256(f"{game_id}\x1f{model_version}".encode()).digest()
    return np.random.SeedSequence(int.from_bytes(h, "big")).spawn(chunks)


# ---------------------------------------------------------------- loop helpers (numba)


@njit(cache=True, nogil=True)
def _expit(x: float) -> float:
    return 1.0 / (1.0 + np.exp(-x))


@njit(cache=True, nogil=True)
def _logit(p: float) -> float:
    q = min(max(p, 1e-9), 1.0 - 1e-9)
    return np.log(q / (1.0 - q))


@njit(cache=True, nogil=True)
def _eta(x, m):
    icpt, lf, lc, sc, cf, cl, cc, inf_, ip, ic, il, ico, ibl = m
    e = icpt[0]
    for i in range(lf.shape[0]):
        v = x[lf[i]]
        e += lc[i] * v + sc[i] * v * v
    for j in range(cf.shape[0]):
        if x[cf[j]] == cl[j]:
            e += cc[j]
    for j in range(inf_.shape[0]):  # distance within a down (rulings 2026-10-25, 2026-10-29)
        if x[ic[j]] == il[j]:
            v = x[inf_[j]]
            if ip[j] == 0:  # a distance bin: an indicator
                if v == ibl[j]:
                    e += ico[j]
            else:
                e += ico[j] * (v * v if ip[j] == 2 else v)
    return e


@njit(cache=True, nogil=True)
def _draw(values, cum, lo, hi, base, table, cat, u):
    k = base[table] + cat
    a, b = lo[k], hi[k]
    i = a + np.searchsorted(cum[a:b], u)
    if i >= b:
        i = b - 1
    return values[i]


@njit(cache=True, nogil=True)
def _draw_tail(values, cum, lo, hi, base, table, cat, threshold, shift, rng):
    """A draw whose probability of being >= threshold is shifted by `shift` on the logit scale
    (ENV-01 explosive reweighting, E11); the shape inside each part is unchanged."""
    k = base[table] + cat
    a, b = lo[k], hi[k]
    if shift == 0.0:
        return _draw(values, cum, lo, hi, base, table, cat, rng.random())
    j = a + np.searchsorted(values[a:b], threshold)
    head = cum[j - 1] if j > a else 0.0
    if head <= 0.0 or head >= 1.0:
        return _draw(values, cum, lo, hi, base, table, cat, rng.random())
    p_tail = _expit(_logit(1.0 - head) + shift)
    u = head + rng.random() * (1.0 - head) if rng.random() < p_tail else rng.random() * head
    return _draw(values, cum, lo, hi, base, table, cat, u)


@njit(cache=True, nogil=True)
def _pick(w, n, rng):
    """Index drawn with weights w[:n] (>= 0); -1 when they sum to 0."""
    s = 0.0
    for i in range(n):
        s += w[i]
    if s <= 0.0:
        return -1
    u = rng.random() * s
    c = 0.0
    for i in range(n):
        c += w[i]
        if u < c:
            return i
    return n - 1


@njit(cache=True, nogil=True)
def _redistribute(share, avail, pos, n):
    """PLY-15 default rule (E6): a sitting player's share goes to the players who play, in
    proportion to their shares, with his position weighted 2x."""
    out = share.copy()
    for x in range(n):
        if avail[x] or share[x] <= 0.0:
            continue
        s = 0.0
        for j in range(n):
            if avail[j]:
                s += share[j] * (2.0 if pos[j] == pos[x] else 1.0)
        if s > 0.0:
            for j in range(n):
                if avail[j]:
                    out[j] += share[x] * share[j] * (2.0 if pos[j] == pos[x] else 1.0) / s
        out[x] = 0.0
    return out


@njit(cache=True, nogil=True)
def _sround(x, rng):
    """Stochastic rounding to whole yards: up with probability equal to the fraction, so a shift
    smaller than half a yard keeps its expected value (C4 shifts, tilt, PLY-09/11, MTC-01/02)."""
    lo = np.floor(x)
    return lo + 1.0 if rng.random() < x - lo else lo


@njit(cache=True, nogil=True)
def togo_bin(togo):
    """Diagnostic 3rd-down distance bin (A.THIRD_BINS): 1, 2, 3, 4-6, 7-10, 11+."""
    if togo <= 1.0:
        return 0
    if togo <= 2.0:
        return 1
    if togo <= 3.0:
        return 2
    if togo <= 6.0:
        return 3
    if togo <= 10.0:
        return 4
    return 5


@njit(cache=True, nogil=True)
def xpass_bin(togo, edges):
    """PRJ-02 xpass distance bin (ruling 2026-10-29), as ge.fit.distill.togo_bin_index: the
    first upper edge at or above togo; beyond the last, the reference bin len(edges)."""
    for k in range(edges.shape[0]):
        if togo <= edges[k]:
            return k
    return edges.shape[0]


@njit(cache=True, nogil=True)
def go_late(sd, game_sec, trail_edges, late_edges):
    """Ruling 2026-11-12 (G-2), as ge.fit.sim_fits.go_late_index: trailing bin x number of time
    bins + time bin when the offense trails with at most late_edges[-1] seconds left (inclusive
    upper edges); -1 otherwise."""
    if sd >= 0.0 or game_sec > late_edges[-1]:
        return -1
    return xpass_bin(-sd, trail_edges) * late_edges.shape[0] + xpass_bin(game_sec, late_edges)


@njit(cache=True, nogil=True)
def go_logit(p_go, togo, yl, sd, game_sec, togo_edges, yl_edges, trail_edges, late_edges):
    """PRJ-02 4th-down go model (ruling 2026-10-31): the cell's logit (distance bin x 3 + field
    bin, inclusive upper edges, as ge.fit.sim_fits.go_cell) + the score slope + (ruling
    2026-11-01) a slope on ln(togo / L) in the last distance bin, L its lower edge + (ruling
    2026-11-12) the trailing x late-time term, if any."""
    tb = xpass_bin(togo, togo_edges)
    c = tb * (yl_edges.shape[0] + 1) + xpass_bin(yl, yl_edges)
    x = p_go[c] + p_go[A.GO_CELLS] * sd
    if tb == togo_edges.shape[0]:
        x += p_go[A.GO_CELLS + 1] * np.log(togo / (togo_edges[-1] + 1.0))
    k = go_late(sd, game_sec, trail_edges, late_edges)
    if k >= 0:
        x += p_go[A.GO_CELLS + 2 + k]
    return x


@njit(cache=True, nogil=True)
def spot_short(gain, togo, yl, down, q, togo_min, togo_max, rng):
    """PRJ-02 sticks spot-short (ruling 2026-11-12, S-1): on downs 1-3, short of goal to go
    (togo < yl), with togo_min <= togo <= togo_max, a gain exactly equal to togo is spotted one
    yard short with probability q. Draws only when q > 0 and the rule applies, so q = 0 leaves
    the random sequence unchanged."""
    if (
        q > 0.0
        and down <= 3
        and gain == togo
        and togo < yl
        and togo_min <= togo <= togo_max
        and rng.random() < q
    ):
        return gain - 1.0
    return gain


@njit(cache=True, nogil=True)
def lower_bin(v, edges):
    """Diagnostic bin from lower edges (approved 2026-10-30): the number of edges at or below v."""
    k = 0
    for i in range(edges.shape[0]):
        if v >= edges[i]:
            k += 1
    return k


@njit(cache=True, nogil=True)
def pd_cell(down, togo, edges):
    """Pass-depth situation cell (ruling 2026-11-02), as ge.models.sim.league.depth_cell."""
    return (min(down, 3) - 1) * PD_DIST_BINS + xpass_bin(togo, edges)


@njit(cache=True, nogil=True)
def sit_cell(down, togo, edges):
    """Run situation (ruling 2026-11-03), as ge.models.sim.league.situation_cell: -1 on 3rd and
    4th down."""
    if down > SIT_DOWNS:
        return -1
    return (down - 1) * SIT_DIST_BINS + xpass_bin(togo, edges)


@njit(cache=True, nogil=True)
def shift_bands(bandp, offsets):
    """Ruling 2026-11-02: band probabilities times exp(the cell's offsets), renormalised; a
    cell with no shift leaves them untouched."""
    any_shift = False
    for b in range(4):
        if offsets[b] != 0.0:
            any_shift = True
    if not any_shift:
        return
    s = 0.0
    for b in range(4):
        bandp[b] *= np.exp(offsets[b])
        s += bandp[b]
    if s > 0.0:
        for b in range(4):
            bandp[b] /= s


@njit(cache=True, nogil=True)
def band_probs(passer, target, league, out):
    """PRJ-02 step 4 depth band (ruling 2026-10-25, replacing C5): probability proportional to
    passer share x target share / league share, renormalized, so league-average players give
    league shares. With no usable product the league shares are used."""
    s = 0.0
    for b in range(4):
        v = passer[b] * target[b] / league[b] if league[b] > 0.0 else 0.0
        out[b] = v if v > 0.0 else 0.0  # NaN and negatives count as 0
        s += out[b]
    if s <= 0.0:
        for b in range(4):
            out[b] = league[b]
        return
    for b in range(4):
        out[b] /= s


# ---------------------------------------------------------------- the game (numba)


@njit(cache=True, nogil=True)
def _game(
    rng,
    team,
    player,
    n_players,
    qb_order,
    mx,
    mc,
    mw,
    p_go,
    fg_punt,
    sticks_q,
    rules,
    ot,
    values,
    cum,
    lo,
    hi,
    base,
    ls,
    la,
    punt_rows,
    ko_rows,
    miss_rows,
    out_team,
    out_player,
    out_first,
):
    pmax = player.shape[1]
    # ---- availability (PLY-14) and per-run shares (PLY-15 default rule)
    avail = np.zeros((2, pmax), dtype=np.bool_)
    tgt = np.zeros((2, pmax))
    car = np.zeros((2, pmax))
    z20 = np.zeros((2, pmax))
    z10 = np.zeros((2, pmax))
    z5 = np.zeros((2, pmax))
    ez = np.zeros((2, pmax))
    passer = np.zeros(2, dtype=np.int64)
    for s in range(2):
        n = n_players[s]
        pos = player[s, :, A.P_POS]
        for i in range(n):
            a = player[s, i, A.P_AVAIL]
            avail[s, i] = a >= 1.0 or rng.random() < a
        tgt[s] = _redistribute(player[s, :, A.P_TARGET], avail[s], pos, n)
        car[s] = _redistribute(player[s, :, A.P_CARRY], avail[s], pos, n)
        z20[s] = _redistribute(player[s, :, A.P_Z20], avail[s], pos, n)
        z10[s] = _redistribute(player[s, :, A.P_Z10], avail[s], pos, n)
        z5[s] = _redistribute(player[s, :, A.P_Z5], avail[s], pos, n)
        ez[s] = _redistribute(player[s, :, A.P_EZ], avail[s], pos, n)
        passer[s] = qb_order[s, 0]
        for q in range(qb_order.shape[1]):
            i = qb_order[s, q]
            if i >= 0 and avail[s, i]:
                passer[s] = i
                break
        for i in range(n):
            if avail[s, i]:
                out_player[s, i, A.S_PLAYED] = 1
    w = np.zeros(pmax)
    x = np.zeros(A.NF)
    togo_edges = la[LA_TOGO_EDGE0 : LA_TOGO_EDGE0 + int(ls[LS_N_TOGO_EDGES])]
    f_togo_edges = la[LA_4TH_TOGO0 : LA_4TH_TOGO0 + 2]
    f_yl_edges = la[LA_4TH_YL0 : LA_4TH_YL0 + 2]
    fg_edges = la[LA_FG_DIST0 : LA_FG_DIST0 + A.FG_DIST_BINS - 1]
    sack_edges = la[LA_SACK_EDGE0:LA_GO_TOGO0]
    go_togo_edges = la[LA_GO_TOGO0 : LA_GO_TOGO0 + 2]
    go_yl_edges = la[LA_GO_YL0 : LA_GO_YL0 + 2]
    pd_edges = la[LA_PD_EDGE0:LA_SIT_EDGE0]
    sit_edges = la[LA_SIT_EDGE0:LA_GO_TRAIL0]
    go_trail_edges = la[LA_GO_TRAIL0:LA_GO_LATE0]
    go_late_edges = la[LA_GO_LATE0:NLA]
    rz_on = False  # the current drive has had a red-zone snap (diagnostic)
    bandp = np.zeros(4)
    cellp = np.zeros(8)

    period_sec = rules[A.G_PERIOD_SEC]
    two_min = ls[LS_TWO_MIN]
    end_zone = rules[A.G_END_ZONE]
    score = np.zeros(2, dtype=np.int64)
    tos = np.zeros(2, dtype=np.int64)
    tos[:] = rules[A.G_TIMEOUTS]
    qtr = 1
    clock = float(period_sec)
    first_kicker = 0 if rng.random() < 0.5 else 1
    in_ot = False
    ot_period = 0
    ot_first = -1
    ot_started = np.zeros(2, dtype=np.bool_)
    ot_done = np.zeros(2, dtype=np.bool_)
    game_over = False
    out_first[0] = -1
    out_first[1] = -1
    # pending: 0 none, 1 kickoff by `kicker`, 2 try by `off`
    pending = 1
    kicker = first_kicker
    off = 1 - kicker
    down = 1
    togo = 10.0
    yl = 75.0
    prev_running = False
    while not game_over:
        # ---------------- period changes
        if clock <= 0.0:
            if pending == 0 and (in_ot or qtr == 2 or qtr >= rules[A.G_PERIODS]):
                out_team[off, A.R_END_HALF] += 1
            if not in_ot and qtr < rules[A.G_PERIODS]:
                qtr += 1
                clock = float(period_sec)
                if qtr == 3:  # second half: the first-half receiver kicks
                    tos[:] = rules[A.G_TIMEOUTS]
                    kicker = 1 - first_kicker
                    pending = 1
                prev_running = False
                continue
            if not in_ot:
                if score[0] != score[1]:
                    break
                in_ot = True
                ot_period = 1
                qtr = 5
                clock = float(ot[A.O_PERIOD_SEC])
                tos[:] = ot[A.O_TIMEOUTS]
                kicker = 0 if rng.random() < 0.5 else 1
                ot_first = 1 - kicker
                pending = 1
                prev_running = False
                continue
            # overtime period ended
            if ot[A.O_MAX_PERIODS] > 0 and ot_period >= ot[A.O_MAX_PERIODS]:
                break  # tie (regular season)
            ot_period += 1
            clock = float(ot[A.O_PERIOD_SEC])
            if ot[A.O_TO_RESET] > 0 and (ot_period - 1) % ot[A.O_TO_RESET] == 0:
                tos[:] = ot[A.O_TIMEOUTS]
            prev_running = False
            continue
        half_sec = clock + (period_sec if (qtr == 1 or qtr == 3) else 0.0)
        if in_ot:
            half_sec = clock
        game_sec = clock + period_sec * max(0, 4 - qtr) if not in_ot else clock
        late = qtr == 2 or qtr >= 4
        inside = late and clock <= two_min

        # ---------------- kickoffs (start of halves, after scores)
        if pending == 1:
            if not in_ot and qtr == 2 and clock <= 0.0:
                pending = 0  # the half ended on the score: the second half opens with a kick
                continue
            rec = 1 - kicker
            sd_kick = score[kicker] - score[rec]
            cat = 1 if ((qtr >= 4) and game_sec <= ls[LS_LATE_KO] and sd_kick < 0) else 0
            r = int(_draw(values, cum, lo, hi, base, TB_KO, cat, rng.random()))
            clock -= _draw(
                values, cum, lo, hi, base, TB_CLOCK, C_KO + (NCLK if inside else 0), rng.random()
            )
            clock = max(clock, 0.0)
            pending = 0
            if ko_rows[r, 3] > 0.5:  # kicking team scored
                score[kicker] += rules[A.G_TD]
                off = kicker
                if out_first[0] < 0:
                    out_first[0] = kicker
                pending = 2
                continue
            if ko_rows[r, 2] > 0.5:  # return TD
                score[rec] += rules[A.G_TD]
                off = rec
                if out_first[0] < 0:
                    out_first[0] = rec
                if in_ot:
                    ot_started[rec] = True
                    if ot_started[0] and ot_started[1] and score[0] != score[1]:
                        break
                pending = 2
                continue
            off = kicker if ko_rows[r, 0] > 0.5 else rec
            yl = ko_rows[r, 1]
            down = 1
            togo = min(float(rules[A.G_TO_GAIN]), yl)
            out_team[off, A.R_DRIVES] += 1
            rz_on = False
            if in_ot:
                ot_started[off] = True
            prev_running = False
            continue

        # ---------------- tries after touchdowns
        if pending == 2:
            pending = 1
            kicker = off
            if rng.random() < team[off, A.T_TWO_PT]:
                if rng.random() < ls[LS_2PT]:
                    score[off] += rules[A.G_TRY_2]
            elif rng.random() < ls[LS_XP]:
                score[off] += rules[A.G_TRY_KICK]
            clock -= _draw(
                values, cum, lo, hi, base, TB_CLOCK, C_TRY + (NCLK if inside else 0), rng.random()
            )
            if clock < 0.0:
                clock = 0.0
            continue

        dfn = 1 - off
        sd = float(score[off] - score[dfn])
        # ---------------- features
        x[A.F_DOWN] = down
        x[A.F_YDSTOGO] = togo
        x[A.F_TOGO_BIN] = xpass_bin(togo, togo_edges)
        x[A.F_YL] = yl
        x[A.F_QTR] = min(qtr, 5)
        x[A.F_HALF_SEC] = half_sec
        x[A.F_GAME_SEC] = game_sec
        x[A.F_SCORE_DIFF] = sd
        x[A.F_POS_TO] = tos[off]
        x[A.F_DEF_TO] = tos[dfn]
        wp = _expit(_eta(x, mw))
        x[A.F_WP] = wp
        if wp > ls[LS_LEAD_WP]:
            proe = team[off, A.T_PROE_LEAD]
            pace = team[off, A.T_PACE_LEAD]
        elif wp < ls[LS_TRAIL_WP]:
            proe = team[off, A.T_PROE_TRAIL]
            pace = team[off, A.T_PACE_TRAIL]
        else:
            proe = team[off, A.T_PROE_N]
            pace = team[off, A.T_PACE_N]
        clock_before = clock

        # ---------------- timeouts after a running-clock play inside two minutes (C9)
        if prev_running and inside and (qtr == 2 or qtr == 4):
            h = 0 if qtr == 2 else 1
            st_off = 0 if sd < 0 else (1 if sd == 0 else 2)
            st_def = 2 - st_off
            if tos[off] > 0 and rng.random() < la[LA_TO0 + h * 6 + 0 * 3 + st_off]:
                tos[off] -= 1
                prev_running = False
            elif tos[dfn] > 0 and rng.random() < la[LA_TO0 + h * 6 + 1 * 3 + st_def]:
                tos[dfn] -= 1
                prev_running = False

        kind = 0  # 0 normal, 1 kneel, 2 spike, 3 field goal, 4 punt
        if (in_ot or qtr == 4) and sd > 0 and clock <= (5 - down - tos[dfn]) * ls[LS_KNEEL_RUNOFF]:
            kind = 1
        if (
            kind == 0
            and prev_running
            and inside
            and sd <= 0
            and down < 4
            and rng.random() < ls[LS_SPIKE]
        ):
            kind = 2
        if kind == 0 and down == 4:
            x5 = go_logit(p_go, togo, yl, sd, game_sec, go_togo_edges, go_yl_edges,
                          go_trail_edges, go_late_edges)  # fmt: skip
            pg = min(max(_expit(x5) + team[off, A.T_GO_OVER], 0.0), 1.0)
            if rng.random() >= pg:
                kind = 3 if rng.random() < _expit(fg_punt[0] + fg_punt[1] * yl) else 4
        if not rz_on and yl <= ls[LS_RZ_YL]:  # every snap kind, penalties included
            rz_on = True
            out_team[off, A.R_RZ_TRIPS] += 1
        f_cell = xpass_bin(togo, f_togo_edges) * 3 + xpass_bin(yl, f_yl_edges)
        ek = A.E_RUN  # 1st/2nd-down play kind
        fg_dist = 0.0

        new_off = off
        yl_next = yl
        cat_clock = C_RUN_IN
        scored = 0  # 0 none, 1 offense TD, 2 offense FG, 3 defense TD, 4 safety
        turnover = False
        ended = False  # possession ended without a score (punt, missed FG, downs)
        gain = 0.0
        running = False
        counts_play = False
        dropback = False
        if kind == 1:
            gain = _draw(values, cum, lo, hi, base, TB_KNEEL, 0, rng.random())
            cat_clock = C_KNEEL
            running = True
        elif kind == 2:
            cat_clock = C_SPIKE
        elif kind == 3:
            dist = yl + _draw(values, cum, lo, hi, base, TB_FGOFF, 0, rng.random())
            fg_dist = dist
            pk = _expit(ls[LS_FG_INT] + ls[LS_FG_SLOPE] * dist + team[off, A.T_FG_SHIFT])
            cat_clock = C_FG
            if rng.random() < pk:
                scored = 2
            else:
                nb = int(ls[LS_N_MISS_BUCKETS])
                b = min(int(dist // ls[LS_MISS_BUCKET]), nb - 1)
                r = int(_draw(values, cum, lo, hi, base, TB_MISS, b, rng.random()))
                if miss_rows[r, 0] > 0.5:
                    new_off = dfn
                yl_next = miss_rows[r, 1]
                ended = True
        elif kind == 4:
            nb = int(ls[LS_N_PUNT_BUCKETS])
            b = min(int(yl // ls[LS_PUNT_BUCKET]), nb - 1)
            r = int(_draw(values, cum, lo, hi, base, TB_PUNT, b, rng.random()))
            cat_clock = C_PUNT
            if punt_rows[r, 2] > 0.5:
                scored = 3
            else:
                if punt_rows[r, 0] > 0.5:
                    new_off = dfn
                yl_next = punt_rows[r, 1]
                ended = True
        else:
            # ---------------- no-play penalty
            u = rng.random()
            if u < ls[LS_PEN_OFF]:
                y = _draw(values, cum, lo, hi, base, TB_PEN_OFF, 0, rng.random())
                out_team[off, A.R_PEN_OFF] += 1
                yl = min(yl + y, 99.0)
                togo = togo + y
                clock -= _draw(
                    values,
                    cum,
                    lo,
                    hi,
                    base,
                    TB_CLOCK,
                    C_PEN + (NCLK if inside else 0),
                    rng.random(),
                )
                clock = max(clock, 0.0)
                prev_running = False
                continue
            if u < ls[LS_PEN_OFF] + ls[LS_PEN_DEF]:
                y = _draw(values, cum, lo, hi, base, TB_PEN_DEF, 0, rng.random())
                out_team[off, A.R_PEN_DEF] += 1
                yl = max(yl - y, 1.0)
                togo = togo - y
                if togo <= 0.0 or rng.random() < ls[LS_PEN_FD]:
                    out_team[off, A.R_PEN_DEF_FD] += 1
                    down = 1
                    togo = min(float(rules[A.G_TO_GAIN]), yl)
                clock -= _draw(
                    values,
                    cum,
                    lo,
                    hi,
                    base,
                    TB_CLOCK,
                    C_PEN + (NCLK if inside else 0),
                    rng.random(),
                )
                clock = max(clock, 0.0)
                prev_running = False
                continue
            # ---------------- the play call
            counts_play = True
            p_pass = min(max(_expit(_eta(x, mx)) + proe, 0.0), 1.0)
            n = n_players[off]
            if rng.random() < p_pass:
                out_team[off, A.R_PASS_PLAYS] += 1
                dropback = True
                qb = passer[off]
                # MTC-03 game sack logit + league situation offset (ruling 2026-10-30, P5)
                s_cell = (min(down, 3) - 1) * SACK_DIST_BINS + xpass_bin(togo, sack_edges)
                if rng.random() < _expit(team[off, A.T_SACK_LOGIT] + la[LA_SACK0 + s_cell]):
                    gain = _draw(values, cum, lo, hi, base, TB_SACK, 0, rng.random())
                    ek = A.E_SACK
                    out_team[off, A.R_SACK_YDS] += int(-gain)
                    cat_clock = C_SACK
                    running = True
                    if rng.random() < ls[LS_FUM_SACK]:
                        turnover = True
                elif rng.random() < player[off, qb, A.P_SCRAMBLE]:
                    g = _draw(values, cum, lo, hi, base, TB_SCR, 0, rng.random())
                    ek = A.E_SCRAMBLE
                    g = _sround(g + player[off, qb, A.P_SCR_SHIFT], rng)
                    gain = min(max(g, ls[LS_RUN_MIN]), yl)
                    out_player[off, qb, A.S_RUSH_ATT] += 1
                    out_player[off, qb, A.S_RUSH_YDS] += int(gain)
                    out_team[off, A.R_RUSH_YDS] += int(gain)
                    out_team[off, A.R_RUSH_ATT] += 1
                    cat_clock = C_RUN_IN
                    running = True
                    if gain >= yl:
                        scored = 1
                        out_player[off, qb, A.S_RUSH_TD] += 1
                        if out_first[0] < 0:
                            out_first[0] = off
                            out_first[1] = qb
                    elif rng.random() < ls[LS_FUM_RUN]:
                        turnover = True
                else:
                    out_team[off, A.R_PASS_ATT] += 1
                    out_player[off, qb, A.S_PASS_ATT] += 1
                    # target
                    zone = z5[off] if yl <= 5 else (z10[off] if yl <= 10 else z20[off])
                    tg = -1
                    if yl <= 20:
                        for i in range(n):
                            tot = tgt[off, i] + car[off, i]
                            w[i] = zone[i] * tgt[off, i] / tot if tot > 0.0 else 0.0
                        tg = _pick(w, n, rng)
                    if tg < 0:
                        for i in range(n):
                            w[i] = tgt[off, i]
                        tg = _pick(w, n, rng)
                    # depth band: passer x target / league (log5, ruling 2026-10-25), deep
                    # shifted by weather
                    band_probs(
                        player[off, qb, A.P_QBBAND0 : A.P_QBBAND0 + 4],
                        player[off, tg, A.P_BAND0 : A.P_BAND0 + 4],
                        la[LA_BAND0 : LA_BAND0 + 4],
                        bandp,
                    )
                    # situation shift and air table (ruling 2026-11-02)
                    dcell = pd_cell(down, togo, pd_edges)
                    shift_bands(bandp, la[LA_PD0 + dcell * 4 : LA_PD0 + dcell * 4 + 4])
                    if team[off, A.T_DEEP_SHIFT] != 0.0 and 0.0 < bandp[3] < 1.0:
                        pd = _expit(_logit(bandp[3]) + team[off, A.T_DEEP_SHIFT])
                        scale = (1.0 - pd) / (1.0 - bandp[3])
                        for b in range(3):
                            bandp[b] *= scale
                        bandp[3] = pd
                    air = 0.0
                    band = 0
                    tries = 0
                    for _try in range(50):
                        tries += 1
                        band = _pick(bandp, 4, rng)
                        air = _draw(values, cum, lo, hi, base, TB_AIR,
                                    AIR_CELL0 + band * PD_CELLS + dcell, rng.random())  # fmt: skip
                        if air <= yl + end_zone:
                            break
                    if tries > 1:
                        out_team[off, A.R_AIR_REDRAWS] += 1
                    if air > yl + end_zone:
                        out_team[off, A.R_AIR_CAPS] += 1
                    air = min(air, yl + end_zone)
                    ek = A.E_DEEP if air >= ls[LS_DEEP_AIR] else A.E_SHORT
                    out_team[off, A.R_AIR_ATT_B0 + band] += int(np.rint(air * 10.0))
                    if air >= yl and yl <= 20:  # an end-zone throw: PLY-32 target
                        for i in range(n):
                            w[i] = ez[off, i]
                        t2 = _pick(w, n, rng)
                        if t2 >= 0:
                            tg = t2
                    loc = _pick(la[LA_LOC0 + band * 3 : LA_LOC0 + band * 3 + 3], 3, rng)
                    out_player[off, tg, A.S_TARGETS] += 1
                    out_team[off, A.R_ATT_B0 + band] += 1
                    x[A.F_AIR] = air
                    x[A.F_LOC] = loc
                    if rng.random() < _expit(_logit(la[LA_INT0 + band]) + team[off, A.T_INT_SHIFT]):
                        out_player[off, qb, A.S_INT] += 1
                        turnover = True
                        gain = 0.0
                        ret = _draw(values, cum, lo, hi, base, TB_INTRET, 0, rng.random())
                        spot = min(max(yl - air, 1.0), 99.0)
                        yl_next = 100.0 - spot - ret
                        new_off = dfn
                        cat_clock = C_TURN
                        if yl_next <= 0.0:
                            scored = 3
                        yl_next = min(max(yl_next, 1.0), 99.0)
                    else:
                        pc = _expit(_eta(x, mc)) + player[off, tg, A.P_CROE]
                        pc = min(max(pc, 0.01), 0.99)
                        if rng.random() < _expit(_logit(pc) + team[off, A.T_CMP_SHIFT]):
                            thr = max(ls[LS_EXPL_PASS] - air, ls[LS_YAC_MIN])
                            yac = _draw_tail(
                                values,
                                cum,
                                lo,
                                hi,
                                base,
                                TB_YAC,
                                band,  # no situation categories (ruling 2026-11-12)
                                thr,
                                team[off, A.T_EXPL_SHIFT],
                                rng,
                            )
                            yac = (
                                yac * player[off, tg, A.P_MTC02]
                                + team[off, A.T_YAC_SHIFT]
                                + player[off, tg, A.P_YACOE]
                            )
                            yac = max(yac, ls[LS_YAC_MIN])
                            out_team[off, A.R_AIR_CMP_B0 + band] += int(np.rint(air * 10.0))
                            out_team[off, A.R_YAC_CMP_B0 + band] += int(np.rint(yac * 10.0))
                            g = _sround(air + yac, rng)
                            gain = min(g, yl)
                            if g > yl:
                                out_team[off, A.R_GL_CLIPS] += 1
                                out_team[off, A.R_GL_CLIP_YDS] += int(g - yl)
                            if yl - gain >= 100.0:
                                gain = yl - 99.0
                            gain = spot_short(gain, togo, yl, down, sticks_q[1],
                                              ls[LS_STICKS_TOGO_MIN], ls[LS_STICKS_TOGO_MAX],
                                              rng)  # ruling 2026-11-12 (S-1)  # fmt: skip
                            out_player[off, qb, A.S_PASS_CMP] += 1
                            out_team[off, A.R_COMP] += 1
                            out_team[off, A.R_CMP_B0 + band] += 1
                            out_team[off, A.R_YDS_B0 + band] += int(gain)
                            out_player[off, qb, A.S_PASS_YDS] += int(gain)
                            out_player[off, tg, A.S_REC] += 1
                            out_player[off, tg, A.S_REC_YDS] += int(gain)
                            out_team[off, A.R_PASS_YDS] += int(gain)
                            cat_clock = C_COMP_IN
                            running = True
                            if gain >= yl:
                                scored = 1
                                out_player[off, qb, A.S_PASS_TD] += 1
                                out_player[off, tg, A.S_REC_TD] += 1
                                if out_first[0] < 0:
                                    out_first[0] = off
                                    out_first[1] = tg
                            elif rng.random() < ls[LS_FUM_COMP]:
                                turnover = True
                                out_player[off, tg, A.S_FUM_LOST] += 1
                        else:
                            cat_clock = C_INC
            else:
                # designed run
                zone = z5[off] if yl <= 5 else (z10[off] if yl <= 10 else z20[off])
                rb = -1
                if yl <= 20:
                    for i in range(n):
                        tot = tgt[off, i] + car[off, i]
                        w[i] = zone[i] * car[off, i] / tot if tot > 0.0 else 0.0
                    rb = _pick(w, n, rng)
                if rb < 0:
                    for i in range(n):
                        w[i] = car[off, i]
                    rb = _pick(w, n, rng)
                if rb < 0:
                    rb = passer[off]
                use_own = True
                for c in range(8):
                    cellp[c] = player[off, rb, A.P_CELL0 + c]
                    if not cellp[c] >= 0.0:
                        use_own = False
                if not use_own:
                    for c in range(8):
                        cellp[c] = team[off, A.T_CELL0 + c]
                cell = _pick(cellp, 8, rng)
                if cell < 0:
                    cell = 8  # every designed run
                # short yardage (ruling 2026-10-29) and late down (ruling 2026-10-30): their own
                # league categories, cells pooled; the cell is still drawn, so the random
                # sequence is unchanged
                if la[LA_SY_DOWN0 + down - 1] > 0.0:
                    cell = SHORT_YARDAGE if togo <= ls[LS_SY_MAX_TOGO] else LATE_DOWN
                elif cell < RUN_CELL_COUNT:
                    # 1st/2nd down: the (cell, situation) category (ruling 2026-11-03); a run
                    # with no cell shares keeps every designed run
                    cell = RUN_SIT0 + cell * SIT_CELLS + sit_cell(down, togo, sit_edges)
                g = _draw_tail(
                    values,
                    cum,
                    lo,
                    hi,
                    base,
                    TB_RUN,
                    cell,
                    ls[LS_EXPL_RUN],
                    team[off, A.T_EXPL_SHIFT],
                    rng,
                )
                g = _sround(g + team[off, A.T_YPC_SHIFT] + player[off, rb, A.P_RYOE], rng)
                gain = min(max(g, ls[LS_RUN_MIN]), yl)
                # ruling 2026-11-12 (S-1)
                gain = spot_short(gain, togo, yl, down, sticks_q[0], ls[LS_STICKS_TOGO_MIN],
                                  ls[LS_STICKS_TOGO_MAX], rng)  # fmt: skip
                out_player[off, rb, A.S_RUSH_ATT] += 1
                out_player[off, rb, A.S_RUSH_YDS] += int(gain)
                out_team[off, A.R_RUSH_YDS] += int(gain)
                out_team[off, A.R_RUSH_ATT] += 1
                cat_clock = C_RUN_IN
                running = True
                if gain >= yl:
                    scored = 1
                    out_player[off, rb, A.S_RUSH_TD] += 1
                    if out_first[0] < 0:
                        out_first[0] = off
                        out_first[1] = rb
                elif rng.random() < _expit(_logit(ls[LS_FUM_RUN]) + team[off, A.T_FUM_SHIFT]):
                    turnover = True
                    out_player[off, rb, A.S_FUM_LOST] += 1
        if counts_play:
            out_team[off, A.R_PLAYS] += 1
            converted = scored == 1 or (not turnover and gain >= togo)
            if down <= 2:
                ke = (down - 1) * A.EARLY_KINDS + ek
                out_team[off, A.R_EARLY_N0 + ke] += 1
                out_team[off, A.R_EARLY_YDS0 + ke] += int(gain)
            if down == 2:
                tb = togo_bin(togo)
                out_team[off, A.R_SECOND_ATT0 + tb] += 1
                if converted:
                    out_team[off, A.R_SECOND_CONV0 + tb] += 1
            if down == 4:
                out_team[off, A.R_4TH_N0 + f_cell] += 1
                out_team[off, A.R_4TH_GO0 + f_cell] += 1
                if converted:
                    out_team[off, A.R_4TH_CONV0 + f_cell] += 1
            if down == 3:
                out_team[off, A.R_THIRD_ATT] += 1
                tb = togo_bin(togo)
                k_att = A.R_THIRD_ATT_PASS0 if dropback else A.R_THIRD_ATT_RUN0
                k_conv = A.R_THIRD_CONV_PASS0 if dropback else A.R_THIRD_CONV_RUN0
                out_team[off, k_att + tb] += 1
                if scored == 1 or (not turnover and gain >= togo):
                    out_team[off, A.R_THIRD_CONV] += 1
                    out_team[off, k_conv + tb] += 1
            if not (qtr >= 4 and (wp < ls[LS_G7_LOW] or wp > ls[LS_G7_HIGH])):  # G7
                out_team[off, A.R_PLAYS_G7] += 1
                if dropback:
                    out_team[off, A.R_PASS_PLAYS_G7] += 1
        if kind == 3:
            out_team[off, A.R_FG_ATT] += 1
            fb = lower_bin(fg_dist, fg_edges)
            out_team[off, A.R_FG_ATT_D0 + fb] += 1
            out_team[off, A.R_4TH_N0 + f_cell] += 1
            if rz_on:
                out_team[off, A.R_RZ_FG_ATT] += 1
            if scored == 2:
                out_team[off, A.R_FG_MADE] += 1
                out_team[off, A.R_FG_MADE_D0 + fb] += 1
        elif kind == 4:
            out_team[off, A.R_PUNTS] += 1
            out_team[off, A.R_4TH_N0 + f_cell] += 1
        if turnover:
            out_team[off, A.R_GIVEAWAYS] += 1

        # ---------------- outcome of the down
        if scored == 0 and not turnover and not ended and kind != 3:
            new_yl = yl - gain
            if new_yl >= 100.0:  # tackled in his own end zone
                scored = 4
            elif kind == 2:  # spike: incomplete pass
                down += 1
                if down > rules[A.G_DOWNS]:
                    ended = True
                    new_off = dfn
                    yl_next = 100.0 - yl
            elif gain >= togo:
                out_team[off, A.R_FIRST_DOWNS] += 1
                yl = new_yl
                down = 1
                togo = min(float(rules[A.G_TO_GAIN]), yl)
            else:
                yl = new_yl
                togo -= gain
                down += 1
                if down > rules[A.G_DOWNS]:
                    ended = True
                    new_off = dfn
                    yl_next = 100.0 - yl
                    out_team[off, A.R_DOWNS] += 1
        if turnover and scored == 0 and new_off == off:
            # fumbles on scrimmage plays: the defense recovers at the spot, plus a return
            new_off = dfn
            spot = min(max(yl - gain, 1.0), 99.0)
            ret = _draw(values, cum, lo, hi, base, TB_FUMRET, 0, rng.random())
            yl_next = 100.0 - spot - ret
            cat_clock = C_TURN
            running = False
            if yl_next <= 0.0:
                scored = 3
            yl_next = min(max(yl_next, 1.0), 99.0)

        # ---------------- clock (C1)
        if scored != 0:
            cat_clock = C_SCORE if scored != 2 else C_FG
            running = False
        idx = cat_clock + (NCLK if inside else 0)
        run_off = _draw(values, cum, lo, hi, base, TB_CLOCK, idx, rng.random())
        if (
            running
            and not inside
            and not turnover
            and scored == 0
            and not ended
            and cat_clock in (C_RUN_IN, C_COMP_IN)
        ):
            run_off = run_off * pace / ls[LS_PACE_REF]
        clock -= run_off
        if late and clock_before > two_min and clock < two_min:
            clock = two_min  # two-minute warning
        if clock < 0.0:
            clock = 0.0
        prev_running = running and scored == 0 and not turnover and not ended

        # ---------------- scores and possession changes
        if scored == 1 or scored == 2:
            score[off] += rules[A.G_TD] if scored == 1 else rules[A.G_FG]
            if scored == 1:
                out_team[off, A.R_OFF_TD] += 1
                if rz_on:
                    out_team[off, A.R_RZ_TD] += 1
            if in_ot:
                if (
                    scored == 1
                    and ot[A.O_OPEN_TD] == 1
                    and off == ot_first
                    and not ot_done[off]
                    and not ot_started[dfn]
                ):
                    break
                if ot_started[0] and ot_started[1] and score[off] > score[dfn] and ot_done[dfn]:
                    break
            if scored == 1:
                pending = 2
            else:
                pending = 1
                kicker = off
            if in_ot:
                ot_done[off] = True
            continue
        if scored == 3:  # defensive / return touchdown
            score[dfn] += rules[A.G_TD]
            if out_first[0] < 0:
                out_first[0] = dfn
            if in_ot:
                ot_started[dfn] = True
                ot_done[off] = True
                if ot_started[0] and ot_started[1] and score[dfn] > score[off]:
                    break
            off = dfn
            pending = 2
            continue
        if scored == 4:  # safety: the defense scores, the offense kicks
            score[dfn] += rules[A.G_SAFETY]
            if in_ot:
                if ot[A.O_OPEN_SAFETY] == 1 and off == ot_first and not ot_done[off]:
                    break
                ot_done[off] = True
                if ot_started[0] and ot_started[1] and score[dfn] > score[off]:
                    break
            pending = 1
            kicker = off
            continue
        if turnover or ended:
            if in_ot:
                ot_done[off] = True
                if ot_done[0] and ot_done[1] and score[0] != score[1]:
                    break
            if new_off != off:
                out_team[new_off, A.R_DRIVES] += 1
                rz_on = False
                if in_ot:
                    ot_started[new_off] = True
                    if ot_done[0] and ot_done[1] and score[0] != score[1]:
                        break
            off = new_off
            yl = yl_next
            down = 1
            togo = min(float(rules[A.G_TO_GAIN]), yl)
            prev_running = False
    out_team[0, A.R_POINTS] = score[0]
    out_team[1, A.R_POINTS] = score[1]
    return in_ot


@njit(cache=True, nogil=True)
def _chunk(
    rng,
    n,
    team,
    player,
    n_players,
    qb_order,
    mx,
    mc,
    mw,
    p_go,
    fg_punt,
    sticks_q,
    rules,
    ot,
    values,
    cum,
    lo,
    hi,
    base,
    ls,
    la,
    punt_rows,
    ko_rows,
    miss_rows,
    out_team,
    out_player,
    out_first,
    out_ot,
):
    for r in range(n):
        went = _game(
            rng,
            team,
            player,
            n_players,
            qb_order,
            mx,
            mc,
            mw,
            p_go,
            fg_punt,
            sticks_q,
            rules,
            ot,
            values,
            cum,
            lo,
            hi,
            base,
            ls,
            la,
            punt_rows,
            ko_rows,
            miss_rows,
            out_team[r],
            out_player[r],
            out_first[r],
        )
        out_ot[r] = 1 if went else 0


# ---------------------------------------------------------------- entry point


def simulate(
    game: GameArrays,
    league: LeagueTables,
    n_runs: int,
    *,
    game_id: str,
    model_version: str,
    parallel: bool = True,
    chunks: int | None = None,
) -> SimResult:
    """PRJ-02: n_runs runs of one game; byte-identical for the same (game_id, model_version)
    and inputs, whether chunks run serially or in parallel (E12)."""
    k = int(load_sim().runs.chunks.value) if chunks is None else chunks
    if game.p_go.shape != (len(A.GO_TERMS),):
        raise ValueError(
            f"PRJ-02: the 4th-down go model has {len(A.GO_TERMS)} terms (rulings 2026-10-31, "
            f"2026-11-01, 2026-11-12); refit the go model; got {game.p_go.shape}"
        )
    q = np.asarray(game.sticks_q, dtype=np.float64)
    if q.shape != (len(A.STICKS_KINDS),) or not ((q >= 0.0) & (q <= 1.0)).all():
        raise ValueError(
            f"PRJ-02: the sticks spot-short needs one q in [0, 1] per kind {A.STICKS_KINDS} "
            f"(ruling 2026-11-12, S-1); got {game.sticks_q!r}"
        )
    pmax = game.player.shape[1]
    out_team = np.zeros((n_runs, 2, A.NTEAM), dtype=np.int32)
    out_player = np.zeros((n_runs, 2, pmax, A.NSTAT), dtype=np.int32)
    out_first = np.zeros((n_runs, 2), dtype=np.int32)
    out_ot = np.zeros(n_runs, dtype=np.int8)
    lg = league_arrays(league)
    mx, mc, mw = (_logit_arrays(m) for m in (game.xpass, game.cp, game.wp))
    bounds = np.linspace(0, n_runs, k + 1).astype(np.int64)
    ss = seeds(game_id, model_version, k)

    def work(c: int) -> None:
        a, b = int(bounds[c]), int(bounds[c + 1])
        rng = np.random.Generator(np.random.PCG64(ss[c]))
        _chunk(
            rng,
            b - a,
            game.team,
            game.player,
            game.n_players,
            game.qb_order,
            mx,
            mc,
            mw,
            game.p_go,
            game.fg_punt,
            game.sticks_q,
            game.rules,
            game.ot,
            *lg,
            out_team[a:b],
            out_player[a:b],
            out_first[a:b],
            out_ot[a:b],
        )

    if parallel and k > 1:
        with ThreadPoolExecutor(max_workers=k) as ex:
            list(ex.map(work, range(k)))
    else:
        for c in range(k):
            work(c)
    return SimResult(
        team=out_team,
        player=out_player,
        first_td=out_first,
        ot=out_ot,
        player_ids=game.player_ids,
    )
