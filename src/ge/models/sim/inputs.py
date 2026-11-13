"""PRJ-02 inputs for one game: the metric engine's shrunk values at decision time, PRJ-01a
ratings, the active fit (v5) and the game's environment, as GameArrays for the play loop.

Rulings applied here: E3 (COA-02), E4 (MTC-01/02/03), E5 (+/-15% caps), E6 (Questionable /
Doubtful), E7 (unslotted players and QB2), E9 (active fit), E11 (weather and surface), D7, B3.
Readings stated in the Phase 5 report: COA-04's leading/trailing PROE and pace replace OFF-05 /
OFF-10 in those game states (they are levels, not increments); a no-signal run-cell stat adds
nothing to MTC-01 (every cell's deviation is the overall one, as the spec does below 25
carries); one Out player's shares follow his PLY-15 rows when they exist, several Out players
the PLY-15 default rule. Everything missing raises with its spec ID; nothing is guessed."""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from ge.config import current_params, load_params, use_season
from ge.fit.sim_inputs import surface_class
from ge.fit.weather import OUTCOME_FACTORS
from ge.ingest.raw import DATA_ROOT, partitions
from ge.ingest.stadiums import load_stadiums, stadium_for_game
from ge.metrics.context import MetricContext, build_context
from ge.metrics.player import ply_14_availability
from ge.metrics.plays import DEPTH_BANDS, RUN_CELLS
from ge.metrics.registry import raw, shrunk
from ge.metrics.roles import _live_candidates, role_key
from ge.models.ratings import GameRatings, rate_context
from ge.models.sim import arrays as A
from ge.models.sim.arrays import GameArrays, compile_logit
from ge.models.sim.league import LeagueTables, game_kickoffs, kickoff_rows
from ge.models.sim.overtime import overtime_rule
from ge.models.sim.rules import game_rule, kickoff_era
from ge.models.sim.settings import load_sim
from ge.store.snapshot import snapshot

POSITION_CODES = {"QB": A.POS_QB, "RB": A.POS_RB, "FB": A.POS_RB, "WR": A.POS_WR, "TE": A.POS_TE}
WEATHER_VALUE = {
    "precipitation": "precipitation_mm",
    "snowfall": "snowfall_cm",
    "wind_speed": "wind_speed_kmh",
    "wind_gusts": "wind_gusts_kmh",
    "temperature": "temperature_c",
}
RULE_KEYS = {
    A.G_TD: "touchdown_points",
    A.G_FG: "field_goal_points",
    A.G_SAFETY: "safety_points",
    A.G_TRY_KICK: "try_kick_points",
    A.G_TRY_2: "try_run_pass_points",
    A.G_TO_GAIN: "line_to_gain_yards",
    A.G_DOWNS: "downs_per_series",
    A.G_FIELD: "field_of_play_yards",
    A.G_PERIODS: "periods",
    A.G_TIMEOUTS: "timeouts_per_half",
    A.G_TWO_MIN: "two_minute_warning_seconds",
    A.G_END_ZONE: "end_zone_yards",
}


@dataclass(frozen=True)
class GameInfo:
    game_id: str
    season: int
    week: int
    as_of: dt.datetime
    home: str
    away: str
    postseason: bool
    neutral: bool
    roof: str | None
    surface: str | None
    ratings: GameRatings
    weather: dict[str, float] | None
    notes: tuple[str, ...]
    league: LeagueTables  # the window's tables with this game's kickoff table (K1)


# ---------------------------------------------------------------- small readers


def go_model(fit_value: Callable[[str, str], float]) -> np.ndarray:
    """PRJ-02 4th-down go model (rulings 2026-10-31, 2026-11-01), in A.GO_TERMS order."""
    return np.array([fit_value(A.go_key(t), "PRJ-02") for t in A.GO_TERMS], dtype=np.float64)


def sticks_model(fit_value: Callable[[str, str], float]) -> np.ndarray:
    """PRJ-02 sticks spot-short (ruling 2026-11-12, S-1): q in A.STICKS_KINDS order."""
    return np.array(
        [fit_value(A.sticks_key(k), "PRJ-02") for k in A.STICKS_KINDS], dtype=np.float64
    )


def _fit_value(key: str, spec_id: str) -> float:
    """A fit-only value; no-signal contributes zero (BT-02); missing raises."""
    status, value, reason = current_params().fit_status(key)
    if status == "fitted" and value is not None:
        return value
    if status == "no_signal":
        return 0.0
    raise NotImplementedError(f"{spec_id}: {key} has no fitted value ({status}: {reason})")


def _model(prefix: str) -> dict[str, float]:
    f = current_params().fitted
    if f is None:
        raise NotImplementedError("PRJ-02: the season has no active fit")
    out = {k[len(prefix) :]: float(v.value) for k, v in f.values.items() if k.startswith(prefix)}
    if "intercept" not in out:
        raise NotImplementedError(f"PRJ-02: {prefix}* is not in fit {f.fit_version}/{f.window}")
    return out


def _team_value(frame: pl.DataFrame, team: str, cell: str = "all") -> float:
    row = frame.filter((pl.col("team") == team) & (pl.col("cell") == cell))
    if row.height != 1 or row["shrunk"][0] is None:
        sid = frame["spec_id"][0] if frame.height else "?"
        raise NotImplementedError(f"{sid}: no shrunk value for {team} cell {cell}")
    return float(row["shrunk"][0])


def _player_map(frame: pl.DataFrame, team: str, cell: str = "all") -> dict[str, float]:
    """Shrunk value per player of `team`; E7: a player with no shrunk value uses value_w."""
    rows = frame.filter((pl.col("team") == team) & (pl.col("cell") == cell))
    out: dict[str, float] = {}
    for pid, s, vw in rows.select("entity_id", "shrunk", "value_w").iter_rows():
        v = s if s is not None else vw
        if v is not None and np.isfinite(v):
            out[str(pid)] = float(v)
    return out


def _no_signal(frame: pl.DataFrame) -> bool:
    """A stat whose fitted k is infinite (BT-02 no detectable signal)."""
    ks = frame["k"].drop_nulls()
    return bool(ks.len() > 0 and np.isinf(ks.to_numpy()).all())


def _era5_window(game_id: str, season: int) -> dict[str, float] | None:
    parts = partitions(DATA_ROOT, "era5_game_window", season)
    if not parts:
        return None
    w = pl.read_parquet(parts[-1] / "part.parquet").filter(pl.col("game_id") == game_id)
    if w.height == 0:
        return None
    r = w.row(0, named=True)
    return {k: float(r[k]) for k in WEATHER_VALUE.values()}


# ---------------------------------------------------------------- team parameters


def _mtc01(ctx: MetricContext, off: str, dfn: str, lam: float) -> float:
    """MTC-01 on yards per carry (spec section 6): lambda x [sum_c s_c (dev_off_c + dev_def_c)
    - (dev_off_all + dev_def_all)]; a cell counts only with 25 carries on both sides, else its
    devs are the overall ones; a no-signal side uses its overall dev in every cell. With no
    qualifying cell the sum cancels, so MTC-01 is 0 and the league value (null before a
    season's first play) is not read (ruling 2026-10-27)."""
    min_c = float(load_params().matchup.mtc_01_min_carries_per_cell.value)
    o_raw, d_raw = raw(ctx, "OFF-12"), raw(ctx, "DEF-03")

    def league(frame: pl.DataFrame, stat: str, cell: str) -> float:
        r = frame.filter(
            (pl.col("entity_type") == "league")
            & (pl.col("stat") == stat)
            & (pl.col("cell") == cell)
        )
        if r.height != 1:
            raise NotImplementedError(f"MTC-01: no league {stat} for cell {cell}")
        return float(r["value"][0])

    def carries(frame: pl.DataFrame, team: str, cell: str) -> float:
        r = frame.filter(
            (pl.col("team") == team) & (pl.col("stat") == "carries") & (pl.col("cell") == cell)
        )
        v = r["value"][0] if r.height else None
        return float(v) if v is not None else 0.0  # no carries there

    qual = [carries(o_raw, off, c) >= min_c and carries(d_raw, dfn, c) >= min_c for c in RUN_CELLS]
    if not any(qual):
        return 0.0
    o_ypc, d_ypc = shrunk(ctx, "OFF-12", "ypc"), shrunk(ctx, "DEF-03", "ypc")
    o_all = _team_value(shrunk(ctx, "OFF-12", "ypc_team"), off)
    d_all = _team_value(shrunk(ctx, "DEF-03", "ypc_team"), dfn)
    l_all_o = league(o_raw, "ypc_team", "all")
    l_all_d = league(d_raw, "ypc_team", "all")
    dev_o_all, dev_d_all = o_all - l_all_o, d_all - l_all_d
    o_ns, d_ns = _no_signal(o_ypc), _no_signal(d_ypc)
    shares = shrunk(ctx, "OFF-12", "share")
    s = np.array([_team_value(shares, off, c) for c in RUN_CELLS])
    s = s / s.sum()
    total = 0.0
    for i, c in enumerate(RUN_CELLS):
        both = qual[i]
        dev_o = (
            dev_o_all
            if (o_ns or not both)
            else _team_value(o_ypc, off, c) - league(o_raw, "ypc", c)
        )
        dev_d = (
            dev_d_all
            if (d_ns or not both)
            else _team_value(d_ypc, dfn, c) - league(d_raw, "ypc", c)
        )
        total += s[i] * (dev_o + dev_d)
    return lam * (total - (dev_o_all + dev_d_all))


def _sack_logit(ctx: MetricContext, off: str, dfn: str) -> float:
    """MTC-03 (E4): logit(L) + lambda[(logit off - logit L) + (logit def - logit L)] +
    ln(OL factor) x OFF-17 starters listed Out."""
    p = load_params().matchup
    o = shrunk(ctx, "OFF-15", "sack_rate").filter(pl.col("team") == off)
    d = shrunk(ctx, "DEF-05", "sack_rate").filter(pl.col("team") == dfn)
    if o.height != 1 or d.height != 1:
        raise NotImplementedError("MTC-03: sack rates missing")
    lg = float(o["prior"][0])

    def lo(x: float) -> float:
        return float(np.log(x / (1 - x)))

    lam = float(p.mtc_03_lambda.value)
    eta = lo(lg) + lam * (
        (lo(float(o["shrunk"][0])) - lo(lg)) + (lo(float(d["shrunk"][0])) - lo(lg))
    )
    st = raw(ctx, "OFF-17").filter(
        (pl.col("team") == off) & (pl.col("stat") == "starter") & (pl.col("note") == "Out")
    )
    factor = float(current_params().params.matchup.mtc_03_ol_absence_factor.value)
    return float(eta + np.log(factor) * st.height)


# ---------------------------------------------------------------- players


def _redistribute_out(
    shares: dict[str, float],
    out: list[str],
    pos: dict[str, str],
    ply15: dict[str, dict[str, float]],
) -> dict[str, float]:
    """PLY-15 (E6): one Out player with PLY-15 rows -> his teammates' PLY-15 shares; otherwise
    each Out player's share goes to the rest by the default rule (position weighted 2x)."""
    mine = [x for x in out if shares.get(x, 0.0) > 0.0]
    if len(mine) == 1 and mine[0] in ply15 and ply15[mine[0]]:
        return {p: v for p, v in ply15[mine[0]].items() if p in shares and p not in out}
    res = dict(shares)
    for x in mine:
        sx = res.pop(x, 0.0)
        wts = {p: v * (2.0 if pos.get(p) == pos.get(x) else 1.0) for p, v in res.items()}
        tot = sum(wts.values())
        if tot > 0:
            for p in res:
                res[p] += sx * wts[p] / tot
    return {p: v for p, v in res.items() if p not in out}


def _shares(
    frame: pl.DataFrame, ply15_frame: pl.DataFrame, team: str, pool: dict[str, str], out: list[str]
) -> dict[str, float]:
    """A share stat for the active pool: Out players' history redistributed (PLY-15, E6), then
    normalized over the pool (players no longer on the roster drop out proportionally)."""
    base = _player_map(frame, team)
    pos = {**dict.fromkeys(out, ""), **pool}
    rows = ply15_frame.filter(pl.col("team") == team)
    ply15 = {x: _player_map(rows, team, f"without:{x}") for x in out}
    res = _redistribute_out(base, out, pos, ply15)
    return _norm({k: v for k, v in res.items() if k in pool})


def _norm(d: dict[str, float]) -> dict[str, float]:
    t = sum(max(v, 0.0) for v in d.values())
    return {k: max(v, 0.0) / t for k, v in d.items()} if t > 0 else d


# ---------------------------------------------------------------- the builder


def build_game(
    game_id: str,
    league: LeagueTables,
    *,
    as_of: dt.datetime | None = None,
    root: Path = DATA_ROOT,
) -> tuple[GameArrays, GameInfo]:
    """PRJ-02 inputs for one game at decision time (default kickoff - 24 h, BT-01)."""
    snap = snapshot(game_id, as_of, root=root)
    ctx = build_context(snap)
    with use_season(snap.season):
        return _build(ctx, league)


def _build(ctx: MetricContext, league: LeagueTables) -> tuple[GameArrays, GameInfo]:
    snap = ctx.snap
    tg = snap.collect("target_game").row(0, named=True)
    home, away = str(tg["home_team"]), str(tg["away_team"])
    postseason = str(tg["game_type"]) != "REG"
    neutral = str(tg.get("location") or "") == "Neutral"
    season = snap.season
    game_league = _game_league(snap, league)  # K1: raises early when the era is too thin
    p = current_params().params
    m = p.matchup
    notes: list[str] = []
    ratings = rate_context(ctx)
    rt = ratings.table.values

    def rating(team: str, kind: str) -> float:
        if (team, kind) not in rt:
            raise NotImplementedError(f"PRJ-01: no {kind} rating for {team}")
        return float(rt[(team, kind)])

    slopes = {
        c: _fit_value(f"fit:PRJ-02/tilt/{c}", "PRJ-02")
        for c in ("completion", "yac", "interception", "yards_per_carry", "fumble_lost")
    }
    cap = float(m.mtc_player_mean_adjustment_cap.value)
    ypc_mean = _pooled_mean(league.run_yards, 8)
    yac_mean = _pooled_mean(league.yac, 4)

    # environment (E11)
    roof = tg.get("roof")
    weather = None
    if roof not in ("dome", "closed"):
        weather = _era5_window(snap.game_id, season)
        if weather is None:
            raise NotImplementedError(f"MTC-05: no ERA5 game window for {snap.game_id} ({roof})")
    surf = surface_class(tg.get("surface"))
    st = stadium_for_game(load_stadiums(), tg["stadium_id"], tg["stadium"]) or {}
    elev = st.get("elevation_m")

    def weather_shift(outcome: str) -> float:
        if weather is None:
            return 0.0
        return sum(
            _fit_value(f"fit:MTC-05/{outcome}/{f}", "MTC-05") * weather[WEATHER_VALUE[f]]
            for f in OUTCOME_FACTORS[outcome]
        )

    cmp_w = weather_shift("completion")
    deep_w = weather_shift("deep_attempt")
    fg_w = weather_shift("fg_make")
    if elev is not None and roof not in ("dome", "closed"):
        fg_w += _fit_value("fit:ENV-02/fg_make/altitude", "ENV-02") * float(elev)
    expl = _fit_value("fit:ENV-01/explosive/artificial", "ENV-01") if surf == "artificial" else 0.0
    if surf is None:
        notes.append("surface unknown: no ENV-01 effect")

    # team frames
    f_pace = shrunk(ctx, "OFF-10", "seconds_per_play")
    f_proe = shrunk(ctx, "OFF-05", "proe")
    f_c4p = shrunk(ctx, "COA-04", "proe")
    f_c4s = shrunk(ctx, "COA-04", "seconds_per_play")
    f_go = shrunk(ctx, "COA-02", "go_over_expected")
    f_2pt = shrunk(ctx, "COA-03", "two_point_rate")
    f_cells = shrunk(ctx, "OFF-12", "share")
    sides = (home, away)
    team = np.zeros((2, A.NT))
    for s, off in enumerate(sides):
        dfn = sides[1 - s]
        t = team[s]
        t[A.T_PACE_N] = _team_value(f_pace, off)
        t[A.T_PACE_LEAD] = _team_value(f_c4s, off, "leading")
        t[A.T_PACE_TRAIL] = _team_value(f_c4s, off, "trailing")
        t[A.T_PROE_N] = _team_value(f_proe, off)
        t[A.T_PROE_LEAD] = _team_value(f_c4p, off, "leading")
        t[A.T_PROE_TRAIL] = _team_value(f_c4p, off, "trailing")
        t[A.T_SACK_LOGIT] = _sack_logit(ctx, off, dfn)
        net_pass = rating(off, "off_pass") + rating(dfn, "def_pass")
        net_run = rating(off, "off_run") + rating(dfn, "def_run")
        t[A.T_CMP_SHIFT] = slopes["completion"] * net_pass + cmp_w
        t[A.T_YAC_SHIFT] = float(np.clip(slopes["yac"] * net_pass, -cap * yac_mean, cap * yac_mean))
        t[A.T_INT_SHIFT] = slopes["interception"] * net_pass
        ypc = slopes["yards_per_carry"] * net_run + _mtc01(
            ctx, off, dfn, float(m.mtc_01_lambda.value)
        )
        t[A.T_YPC_SHIFT] = float(np.clip(ypc, -cap * ypc_mean, cap * ypc_mean))
        t[A.T_FUM_SHIFT] = slopes["fumble_lost"] * net_run
        t[A.T_GO_OVER] = _team_value(f_go, off)
        t[A.T_TWO_PT] = _team_value(f_2pt, off)
        t[A.T_DEEP_SHIFT] = deep_w
        t[A.T_FG_SHIFT] = fg_w
        t[A.T_EXPL_SHIFT] = expl
        cells = np.array([_team_value(f_cells, off, c) for c in RUN_CELLS])
        t[A.T_CELL0 : A.T_CELL0 + 8] = cells / cells.sum()

    # players
    player_rows, n_players, qb_order, ids = _players(ctx, sides, league, cap, ypc_mean, yac_mean)

    xpass = compile_logit(_model("fit:PRJ-02/xpass/"))
    cp = compile_logit(_model("fit:PRJ-02/cp/"))
    wp = compile_logit(_model("fit:PRJ-02/wp/"))
    p_go = go_model(_fit_value)
    fg_punt = np.array(
        [_fit_value(f"fit:PRJ-02/fg_vs_punt/{t}", "PRJ-02") for t in ("intercept", "slope")]
    )
    rules = np.zeros(A.NG, dtype=np.int64)
    for idx, key in RULE_KEYS.items():
        rules[idx] = game_rule(key, season)
    rules[A.G_PERIOD_SEC] = game_rule("period_minutes", season) * 60
    o = overtime_rule(season, postseason=postseason)
    ot = np.array(
        [
            o.period_minutes * 60,
            o.max_periods or 0,
            int(o.ties_allowed),
            o.timeouts_per_team,
            o.timeouts_reset_periods or 0,
            int(o.opening_touchdown_ends_game),
            int(o.opening_safety_ends_game),
        ],
        dtype=np.int64,
    )
    arrays = GameArrays(
        team=team,
        player=player_rows,
        n_players=n_players,
        qb_order=qb_order,
        xpass=xpass,
        cp=cp,
        wp=wp,
        p_go=p_go,
        fg_punt=fg_punt,
        sticks_q=sticks_model(_fit_value),
        rules=rules,
        ot=ot,
        player_ids=ids,
    )
    info = GameInfo(
        game_id=snap.game_id,
        season=season,
        week=snap.week,
        as_of=snap.as_of,
        home=home,
        away=away,
        postseason=postseason,
        neutral=neutral,
        roof=roof,
        surface=surf,
        ratings=ratings,
        weather=weather,
        notes=tuple(notes),
        league=game_league,
    )
    return arrays, info


def _game_league(snap: Any, league: LeagueTables) -> LeagueTables:
    """PRJ-02 kickoff era (K1, rulings 2026-11-01, 2026-11-02): the window's league tables with
    the kickoff table rebuilt for this game: window kickoffs from seasons of the game's era,
    plus the game's season's kickoffs from the snapshot (finished games by as_of, BT-01). A
    season's week w has week index target + w - 1, counted from the window's target week."""
    season = snap.season
    era = kickoff_era(season)
    window_seasons = sorted({int(s) for s in league.kickoff_season})
    same = {s for s in window_seasons if kickoff_era(s) == era}
    base = league.kickoff_target_index - 1
    pbp = snap.collect("pbp").filter(pl.col("season") == season)
    current = kickoff_rows(
        pbp.with_columns((base + pl.col("week")).alias("week_index")),
        league.late_kickoff_seconds,
    )
    return game_kickoffs(
        league,
        current,
        seasons=same,
        game_index=base + snap.week,
        h_l=_fit_value("fit:PRJ-02/h_l", "PRJ-02"),
        min_events=int(load_sim().league.min_category_events.value),
    )


def _pooled_mean(pk: Any, k: int) -> float:
    v = pk.values[pk.lo[k] : pk.hi[k]]
    c = pk.cum[pk.lo[k] : pk.hi[k]]
    return float(np.dot(v, np.diff(np.concatenate([[0.0], c]))))


def _players(
    ctx: MetricContext,
    sides: tuple[str, str],
    league: LeagueTables,
    cap: float,
    ypc_mean: float,
    yac_mean: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, tuple[tuple[str, ...], tuple[str, ...]]]:
    p = current_params().params
    q_rate = _fit_value("fit:PLY-14/game_status/Questionable", "PLY-14")
    d_rate = _fit_value("fit:PLY-14/game_status/Doubtful", "PLY-14")
    beta = float(p.matchup.mtc_02_beta.value)
    lam2 = float(p.matchup.mtc_02_lambda.value)
    f = {
        "tgt": shrunk(ctx, "PLY-03", "target_share"),
        "car": shrunk(ctx, "PLY-05", "carry_share"),
        "z": shrunk(ctx, "PLY-06", "opportunity_share"),
        "ez": shrunk(ctx, "PLY-32", "end_zone_share"),
        "b28": shrunk(ctx, "PLY-28", "share"),
        "b18": shrunk(ctx, "PLY-18", "share"),
        "croe": shrunk(ctx, "PLY-10", "croe"),
        "yacoe": shrunk(ctx, "PLY-09", "yacoe"),
        "ryoe": shrunk(ctx, "PLY-11", "ryoe_per_carry"),
        "scr": shrunk(ctx, "PLY-22", "scramble_rate"),
        "ypr": shrunk(ctx, "PLY-22", "yards_per_rush"),
        "c16": shrunk(ctx, "PLY-16", "share"),
        "snap": shrunk(ctx, "PLY-01", "snap_share"),
        "d04": shrunk(ctx, "DEF-04", "yards"),
        "p15t": shrunk(ctx, "PLY-15", "target_share"),
        "p15c": shrunk(ctx, "PLY-15", "carry_share"),
    }
    status = raw(ctx, "PLY-14").filter(pl.col("stat") == "game_status")
    avail_unknown = ply_14_availability(ctx)
    pools = [_live_candidates(ctx, t) for t in sides]
    pmax = max(len(pl_) for pl_ in pools)
    out = np.zeros((2, pmax, A.NP))
    out[:, :, A.P_CELL0 : A.P_CELL0 + 8] = np.nan
    n_players = np.zeros(2, dtype=np.int64)
    qmax = max(sum(1 for v in pl_.values() if v == "QB") for pl_ in pools)
    qb_order = np.full((2, max(qmax, 1)), -1, dtype=np.int64)
    ids: list[tuple[str, ...]] = []
    for s, team in enumerate(sides):
        dfn = sides[1 - s]
        pool = pools[s]
        st_rows = status.filter(pl.col("team") == team)
        notes = {str(a): str(b or "") for a, b in st_rows.select("entity_id", "note").iter_rows()}
        out_ids = [pid for pid, note in notes.items() if note.startswith("Out")]
        tgt = _shares(f["tgt"], f["p15t"], team, pool, out_ids)
        car = _shares(f["car"], f["p15c"], team, pool, out_ids)
        order = sorted(pool, key=lambda x: (-(tgt.get(x, 0) + car.get(x, 0)), x))
        ids.append(tuple(order))
        n_players[s] = len(order)
        zones = {
            c: _norm({k: v for k, v in _player_map(f["z"], team, c).items() if k in pool})
            for c in ("inside_20", "inside_10", "inside_5")
        }
        ez = _norm({k: v for k, v in _player_map(f["ez"], team).items() if k in pool})
        slots = {pid: sl for (pid, t), sl in ctx.slots.items() if t == team}
        qbs = [pid for pid in order if pool[pid] == "QB"]
        snaps = _player_map(f["snap"], team)
        qbs.sort(key=lambda x: (0 if slots.get(x) == "QB1" else 1, -snaps.get(x, 0.0), x))
        for j, q in enumerate(qbs):
            qb_order[s, j] = order.index(q)
        d04 = {c: _team_value(f["d04"], dfn, c) for c in ("RB", "TE", "WR")}
        for i, pid in enumerate(order):
            r = out[s, i]
            code = POSITION_CODES.get(pool[pid], A.POS_OTHER)
            r[A.P_POS] = code
            r[A.P_TARGET] = tgt.get(pid, 0.0)
            r[A.P_CARRY] = car.get(pid, 0.0)
            r[A.P_Z20] = zones["inside_20"].get(pid, 0.0)
            r[A.P_Z10] = zones["inside_10"].get(pid, 0.0)
            r[A.P_Z5] = zones["inside_5"].get(pid, 0.0)
            r[A.P_EZ] = ez.get(pid, 0.0)
            bands = np.array([_player_map(f["b28"], team, b).get(pid, np.nan) for b in DEPTH_BANDS])
            r[A.P_BAND0 : A.P_BAND0 + 4] = (
                bands / bands.sum()
                if np.all(np.isfinite(bands)) and bands.sum() > 0
                else league.band_share
            )
            if code == A.POS_QB:
                qb = np.array(
                    [_player_map(f["b18"], team, b).get(pid, np.nan) for b in DEPTH_BANDS]
                )
                if not (np.all(np.isfinite(qb)) and qb.sum() > 0):  # E7: the QB1 slot prior
                    qb = np.array(
                        [
                            current_params().extra(role_key("PLY-18", "share", b, "QB1"), "PLY-18")
                            for b in DEPTH_BANDS
                        ]
                    )
                r[A.P_QBBAND0 : A.P_QBBAND0 + 4] = qb / qb.sum()
                scr = _player_map(f["scr"], team).get(pid)
                r[A.P_SCRAMBLE] = scr if scr is not None else league.scramble_rate
                yp = f["ypr"].filter((pl.col("team") == team) & (pl.col("entity_id") == pid))
                if yp.height and yp["shrunk"][0] is not None and yp["prior"][0] is not None:
                    r[A.P_SCR_SHIFT] = float(yp["shrunk"][0]) - float(yp["prior"][0])
            r[A.P_CROE] = _player_map(f["croe"], team).get(pid, 0.0)
            r[A.P_YACOE] = float(
                np.clip(
                    _player_map(f["yacoe"], team).get(pid, 0.0), -cap * yac_mean, cap * yac_mean
                )
            )
            r[A.P_RYOE] = float(
                np.clip(_player_map(f["ryoe"], team).get(pid, 0.0), -cap * ypc_mean, cap * ypc_mean)
            )
            key = {A.POS_RB: "RB", A.POS_TE: "TE", A.POS_WR: "WR"}.get(code)
            mult = 1.0 if key is None else 1.0 + lam2 * (d04[key] ** beta - 1.0)
            r[A.P_MTC02] = float(np.clip(mult, 1.0 - cap, 1.0 + cap))
            cells = np.array([_player_map(f["c16"], team, c).get(pid, np.nan) for c in RUN_CELLS])
            if np.all(np.isfinite(cells)) and cells.sum() > 0:
                r[A.P_CELL0 : A.P_CELL0 + 8] = cells / cells.sum()
            note = notes.get(pid, "")
            if note.startswith("Questionable"):
                r[A.P_AVAIL] = q_rate
            elif note.startswith("Doubtful"):
                r[A.P_AVAIL] = d_rate
            elif note.startswith("status unknown"):
                av = avail_unknown.filter((pl.col("entity_id") == pid) & (pl.col("team") == team))[
                    "value"
                ]
                if not av.len() or av[0] is None:
                    raise NotImplementedError(f"PLY-14: no availability for {pid} (status unknown)")
                r[A.P_AVAIL] = float(av[0])
            else:
                r[A.P_AVAIL] = 1.0
        if not qbs:
            raise NotImplementedError(f"PRJ-02: {team} has no QB on its active roster")
    return out, n_players, qb_order, (ids[0], ids[1])
