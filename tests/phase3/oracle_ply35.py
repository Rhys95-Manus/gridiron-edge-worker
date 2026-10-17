"""Independent PLY-35 oracle for the golden test: plain Python over the fixture's raw rows, with
its own reading of the spec text (MODEL_SPEC PLY-35 row, "PLY-35 rules", BT-01 availability).
It shares no code with ge.metrics: visibility, centring, weights and sums are all redone here."""

from __future__ import annotations

import datetime as dt
import math
from collections import defaultdict
from zoneinfo import ZoneInfo

import polars as pl

from tests.phase3.conftest import store_table

ET = ZoneInfo("America/New_York")
STATS = {
    "receptions": (("receptions",), ("receptions_exp",)),
    "receiving_yards": (("rec_yards_gained",), ("rec_yards_gained_exp",)),
    "rushing_yards": (("rush_yards_gained",), ("rush_yards_gained_exp",)),
    "tds": (("rec_touchdown", "rush_touchdown"), ("rec_touchdown_exp", "rush_touchdown_exp")),
}
GROUPS = {"QB", "RB", "WR", "TE"}


def _end_times(season: int) -> dict[str, dt.datetime]:
    pbp = store_table("pbp", season).select("game_id", "time_of_day").drop_nulls()
    out: dict[str, dt.datetime] = {}
    for gid, t in pbp.iter_rows():
        v = dt.datetime.fromisoformat(t.replace("Z", "+00:00"))
        if v.tzinfo is None:
            v = v.replace(tzinfo=dt.UTC)
        if gid not in out or v > out[gid]:
            out[gid] = v
    return out


def _kickoffs(season: int) -> dict[str, dt.datetime]:
    s = store_table("schedules", season)
    out = {}
    for gid, day, time in s.select("game_id", "gameday", "gametime").iter_rows():
        local = dt.datetime.combine(dt.date.fromisoformat(day), dt.time.fromisoformat(time), ET)
        out[gid] = local.astimezone(dt.UTC)
    return out


def _weeks(season: int) -> dict[str, int]:
    return dict(store_table("schedules", season).select("game_id", "week").iter_rows())


def visible_games(season: int, target: str, as_of: dt.datetime) -> set[str]:
    """Kicked off before the target, last play by as_of, and (the fixture slice was pulled after
    these games) known at 12 noon ET the day after the last play."""
    k0 = _kickoffs(int(target[:4]))[target]
    kick, ends = _kickoffs(season), _end_times(season)
    out = set()
    for gid, end in ends.items():
        if gid == target or kick.get(gid) is None or kick[gid] >= k0 or end > as_of:
            continue
        day = end.astimezone(ET).date() + dt.timedelta(days=1)
        if dt.datetime.combine(day, dt.time(12), ET).astimezone(dt.UTC) <= as_of:
            out.add(gid)
    return out


def _rows(season: int, games: set[str]) -> list[dict[str, object]]:
    ff = store_table("ff_opportunity", season)
    out = []
    for r in ff.iter_rows(named=True):
        if r["game_id"] not in games or r["player_id"] is None:
            continue
        if (r["rec_attempt"] or 0) + (r["rush_attempt"] or 0) < 1:
            continue
        out.append(r)
    return out


def _gap(r: dict[str, object], stat: str) -> float:
    act, exp = STATS[stat]
    return math.fsum(float(r[a] or 0.0) for a in act) - math.fsum(float(r[e] or 0.0) for e in exp)  # type: ignore[arg-type]


def _group(pos: object) -> str:
    return str(pos) if pos in GROUPS else "Other"


def _means(rows: list[dict[str, object]], stat: str) -> dict[str, float]:
    acc: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        acc[_group(r["position"])].append(_gap(r, stat))
    return {g: math.fsum(v) / len(v) for g, v in acc.items()}


def oracle(
    season: int, target: str, as_of: dt.datetime, h: float, min_weeks: int
) -> tuple[dict[tuple[str, str, str], dict[str, float]], dict[tuple[str, str], float], bool]:
    """((player, team, stat) -> value, value_w, n, n_eff), the centring means used, and whether
    the previous season's mean stood in."""
    cur = _rows(season, visible_games(season, target, as_of))
    weeks = _weeks(season)
    n_weeks = len({weeks[str(r["game_id"])] for r in cur})
    fallback = n_weeks < min_weeks
    if fallback:
        prev_games = set(_end_times(season - 1))
        base = _rows(season - 1, prev_games)
    else:
        base = cur
    # games ago per team: this season's visible games by week, latest = 0 (pbp-visible games)
    team_games: dict[str, list[tuple[int, str]]] = defaultdict(list)
    vis_pbp = {
        g
        for g in _end_times(season)
        if g != target
        and _kickoffs(season)[g] < _kickoffs(int(target[:4]))[target]
        and _end_times(season)[g] <= as_of
    }
    sched = store_table("schedules", season)
    for gid, wk, home, away in sched.select(
        "game_id", "week", "home_team", "away_team"
    ).iter_rows():
        if gid in vis_pbp:
            team_games[home].append((wk, gid))
            team_games[away].append((wk, gid))
    g_of: dict[tuple[str, str], int] = {}
    for team, lst in team_games.items():
        for i, (_, gid) in enumerate(sorted(lst, key=lambda t: (-t[0], t[1]))):
            g_of[(team, gid)] = i
    means_used: dict[tuple[str, str], float] = {}
    out: dict[tuple[str, str, str], dict[str, float]] = {}
    for stat in STATS:
        mu = _means(base, stat)
        for grp, v in mu.items():
            means_used[(grp, stat)] = v
        per: dict[tuple[str, str], list[tuple[float, float]]] = defaultdict(list)
        for r in cur:
            x = _gap(r, stat) - mu[_group(r["position"])]
            g = g_of[(str(r["posteam"]), str(r["game_id"]))]
            per[(str(r["player_id"]), str(r["posteam"]))].append((x, 0.5 ** (g / h)))
        for (pid, team), xs in per.items():
            sw = math.fsum(w for _, w in xs)
            out[(pid, team, stat)] = {
                "value": math.fsum(x for x, _ in xs),
                "value_w": math.fsum(w * x for x, w in xs) / sw,
                "n": float(len(xs)),
                "n_eff": sw * sw / math.fsum(w * w for _, w in xs),
            }
    return out, means_used, fallback


def null_player_rows(season: int, target: str, as_of: dt.datetime) -> int:
    ff = store_table("ff_opportunity", season)
    games = visible_games(season, target, as_of)
    return ff.filter(pl.col("game_id").is_in(list(games)) & pl.col("player_id").is_null()).height
