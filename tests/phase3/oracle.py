"""Independent re-computation of Phase 3 metrics for golden tests.

Plain Python over row dicts, re-coded from docs/MODEL_SPEC.md and the approved Phase 3 plan.
It never imports ge.metrics, so a bug there can't agree with itself here. Thresholds come from
config/params.yaml (the values under test are the formulas, not the constants).

Row source: a snapshot's tables, which Phase 2 already tests for point-in-time visibility.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from itertools import pairwise
from typing import Any

from ge.config import load_params

P = load_params()
C = P.conventions
Row = dict[str, Any]


def v(entry: Any) -> float:
    return float(entry.value)


# ---- play filters (spec text quoted beside each) ----


def garbage(r: Row) -> bool:
    """G7: wp < 0.05 or > 0.95 in the 4th quarter (overtime included, plan A13)."""
    wp = r["wp"]
    return (
        r["qtr"] is not None
        and r["qtr"] >= 4
        and wp is not None
        and (wp < v(C.g7_garbage_wp_low) or wp > v(C.g7_garbage_wp_high))
    )


def neutral(r: Row) -> bool:
    """G5: wp between 0.20 and 0.80 (inclusive), not inside the final 2:00 of either half."""
    wp = r["wp"]
    return (
        wp is not None
        and v(C.g5_neutral_wp_min) <= wp <= v(C.g5_neutral_wp_max)
        and r["half_seconds_remaining"] is not None
        and r["half_seconds_remaining"] > v(C.g5_end_of_half_excluded_seconds)
    )


def scrimmage(r: Row) -> bool:
    """Excluded everywhere: no_play penalties, kneels, spikes (G7) and two-point tries (A4)."""
    return (
        r["play_type"] != "no_play"
        and r["qb_kneel"] != 1
        and r["qb_spike"] != 1
        and r["two_point_attempt"] != 1
    )


def qualifying(r: Row) -> bool:
    """Section 2: pass == 1 or rush == 1, after G7."""
    return (r["pass"] == 1 or r["rush"] == 1) and scrimmage(r) and not garbage(r)


def dropback(r: Row) -> bool:
    """A3: qb_dropback == 1, after G7."""
    return r["qb_dropback"] == 1 and scrimmage(r) and not garbage(r)


def designed_run(r: Row) -> bool:
    """OFF-12: rush == 1, qb_scramble == 0, no kneels; after G7."""
    return r["rush"] == 1 and r["qb_scramble"] != 1 and scrimmage(r) and not garbage(r)


def target(r: Row) -> bool:
    """PLY-03: pass plays with a receiver_player_id."""
    return qualifying(r) and r["pass"] == 1 and r["receiver_player_id"] is not None


# ---- G3 / G1 ----


def games_ago(rows: list[Row]) -> dict[str, dict[str, int]]:
    """G3: per team, g = 0 for its most recent visible game."""
    games: dict[str, set[tuple[int, str]]] = defaultdict(set)
    for r in rows:
        for t in (r["home_team"], r["away_team"]):
            games[t].add((r["week"], r["game_id"]))
    out: dict[str, dict[str, int]] = {}
    for t, gs in games.items():
        ordered = sorted(gs, reverse=True)
        out[t] = {gid: i for i, (_, gid) in enumerate(ordered)}
    return out


@dataclass
class Agg:
    n: int
    value: float | None
    value_w: float | None
    n_eff: float


def aggregate(units: Iterable[tuple[str, str, int, float]], h: float) -> dict[tuple[str, str], Agg]:
    """Units are (entity, cell, games_ago, x). G3 weights w = 0.5^(g/h)."""
    acc: dict[tuple[str, str], list[tuple[int, float]]] = defaultdict(list)
    for e, c, g, x in units:
        acc[(e, c)].append((g, x))
    out = {}
    for key, items in acc.items():
        ws = [0.5 ** (g / h) for g, _ in items]
        xs = [x for _, x in items]
        sw = math.fsum(ws)
        out[key] = Agg(
            n=len(xs),
            value=math.fsum(xs) / len(xs),
            value_w=math.fsum(w * x for w, x in zip(ws, xs, strict=True)) / sw,
            n_eff=sw * sw / math.fsum(w * w for w in ws),
        )
    return out


def league(units: Iterable[tuple[str, str, int, float]]) -> dict[str, float]:
    """Unweighted league mean per cell (plan A2)."""
    acc: dict[str, list[float]] = defaultdict(list)
    for _, c, _, x in units:
        acc[c].append(x)
    return {c: math.fsum(xs) / len(xs) for c, xs in acc.items()}


def shrink(a: Agg | None, prior: float, k: float) -> float:
    """G1 with n_eff in place of n (G3)."""
    if a is None or a.n == 0:
        return prior
    assert a.value_w is not None
    return (a.n_eff * a.value_w + k * prior) / (a.n_eff + k)


# ---- unit builders ----

Side = str  # "posteam" (offense) or "defteam" (defense)


def units(
    rows: list[Row],
    side: Side,
    keep: Callable[[Row], bool],
    cell: Callable[[Row], str | None],
    x: Callable[[Row], float | None],
) -> list[tuple[str, str, int, float]]:
    ga = games_ago(rows)
    out = []
    for r in rows:
        if not keep(r):
            continue
        c = cell(r)
        val = x(r)
        if c is None or val is None:
            continue
        team = r[side]
        out.append((team, c, ga[team][r["game_id"]], float(val)))
    return out


def run_cell(r: Row) -> str:
    """OFF-12 cells: left/right x end/tackle/guard, middle; no location -> unknown (A5)."""
    loc, gap = r["run_location"], r["run_gap"]
    if loc == "middle":
        return "middle"
    if loc in ("left", "right") and gap in ("end", "tackle", "guard"):
        return f"{loc}_{gap}"
    return "unknown"


def depth_band(air: float | None) -> str | None:
    if air is None:
        return None
    o = P.offense
    if air < v(o.off_13_short_min_air_yards):
        return "behind"
    if air < v(o.off_13_intermediate_min_air_yards):
        return "short"
    if air < v(o.off_13_deep_min_air_yards):
        return "intermediate"
    return "deep"


def pass_cell(r: Row) -> str:
    """OFF-13: pass_location x depth band; missing either -> unknown."""
    band = depth_band(r["air_yards"])
    loc = r["pass_location"]
    if band is None or loc not in ("left", "middle", "right"):
        return "unknown"
    return f"{loc}_{band}"


def down_zone_cell(r: Row) -> str:
    """OFF-03: downs {1, 2, 3-4} x zones; goal-to-go first, then red zone (A6)."""
    d = r["down"]
    dn = "d1" if d == 1 else "d2" if d == 2 else "d34"
    yl = r["yardline_100"]
    if r["goal_to_go"] == 1:
        z = "goal_to_go"
    elif yl <= v(P.offense.off_03_red_zone_max_yardline_100):
        z = "red_zone"
    elif yl >= v(P.offense.off_03_own_zone_min_yardline_100):
        z = "own"
    else:
        z = "open"
    return f"{dn}_{z}"


def pace_pairs(rows: list[Row]) -> list[tuple[str, str, int, float]]:
    """OFF-10 (plan A7): consecutive pbp rows (snaps and timeout rows) in the same game, drive
    and quarter for one offense; both rows qualifying snaps; the prior play neutral (G5) and
    not incomplete, out of bounds, a timeout, a penalty or a turnover; delta clipped at 45 s."""
    ga = games_ago(rows)
    cap = v(P.offense.off_10_max_snap_gap_seconds)
    seq = sorted(
        (r for r in rows if r["play_type"] is not None or r["timeout"] == 1),
        key=lambda r: (r["game_id"], r["play_id"]),
    )
    out = []
    for a, b in pairwise(seq):
        if a["game_id"] != b["game_id"] or a["posteam"] is None:
            continue
        if (a["posteam"], a["fixed_drive"], a["qtr"]) != (b["posteam"], b["fixed_drive"], b["qtr"]):
            continue
        if not (qualifying(a) and qualifying(b) and neutral(a)):
            continue
        if any(
            a[f] == 1
            for f in (
                "incomplete_pass",
                "out_of_bounds",
                "timeout",
                "penalty",
                "interception",
                "fumble_lost",
            )
        ):
            continue
        d = min(a["game_seconds_remaining"] - b["game_seconds_remaining"], cap)
        out.append((a["posteam"], "all", ga[a["posteam"]][a["game_id"]], float(d)))
    return out


def zone_trips(rows: list[Row], side: Side, zone: float) -> list[tuple[str, str, int, float]]:
    """OFF-14 / DEF-07: drives with a scrimmage snap at yardline_100 <= zone (A13); x = 1 if the
    drive produced an offensive TD. A drive whose first in-zone snap is garbage time (G7) is
    left out."""
    ga = games_ago(rows)
    snaps = ("pass", "run", "no_play", "field_goal", "punt", "qb_kneel", "qb_spike")
    drives: dict[tuple[str, float, str], list[Row]] = defaultdict(list)
    for r in rows:
        if r["posteam"] is not None and r["fixed_drive"] is not None:
            drives[(r["game_id"], r["fixed_drive"], r["posteam"])].append(r)
    out = []
    for (gid, _, team), rs in drives.items():
        rs.sort(key=lambda r: r["play_id"])
        inzone = [
            r
            for r in rs
            if r["play_type"] in snaps
            and r["yardline_100"] is not None
            and r["yardline_100"] <= zone
        ]
        if not inzone or garbage(inzone[0]):
            continue
        td = any(r["touchdown"] == 1 and r["td_team"] == team for r in rs)
        ent = team if side == "posteam" else inzone[0]["defteam"]
        out.append((ent, f"inside_{int(zone)}", ga[ent][gid], 1.0 if td else 0.0))
    return out
