"""Independent re-computation of the player metrics (PLY-01 to PLY-17) for golden tests.

Plain Python over row dicts, re-coded from docs/MODEL_SPEC.md section 4 and the 3b rulings
(2026-10-04): shares over the games he played; one row per (player, team) stint; usage shares
keep garbage time, efficiency stats drop it (plan A26). Never imports ge.metrics."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from tests.phase3.oracle import P, designed_run, dropback, games_ago, scrimmage, target

Row = dict[str, Any]
Key = tuple[str, str]  # (player, team)
PL = P.player


def v(x: Any) -> float:
    return float(x.value)


# ---- play sets ----


def usage_target(r: Row) -> bool:
    """PLY-03: a pass play with a receiver; usage keeps garbage time (A26)."""
    return r["pass"] == 1 and r["receiver_player_id"] is not None and scrimmage(r)


def usage_carry(r: Row) -> bool:
    """PLY-05: a designed carry (rush, not a scramble); usage keeps garbage time."""
    return r["rush"] == 1 and r["qb_scramble"] != 1 and scrimmage(r)


def dropback_qb(r: Row) -> str | None:
    """The QB on a dropback: passer, or the rusher on a scramble (nflverse leaves the passer
    empty on scrambles)."""
    if r["passer_player_id"] is not None:
        return str(r["passer_player_id"])
    if r["qb_scramble"] == 1 and r["rusher_player_id"] is not None:
        return str(r["rusher_player_id"])
    return None


def owner(r: Row) -> str | None:
    """Whose opportunity a target or carry is."""
    if usage_target(r):
        return str(r["receiver_player_id"])
    if usage_carry(r):
        return None if r["rusher_player_id"] is None else str(r["rusher_player_id"])
    return None


# ---- who played ----


def team_snaps(snaps: list[Row]) -> dict[tuple[str, str], float]:
    """A12: a team-game's offensive snaps = max over its players of offense_snaps / pct."""
    out: dict[tuple[str, str], float] = {}
    for r in snaps:
        if r["offense_pct"]:
            t = r["offense_snaps"] / r["offense_pct"]
            k = (r["team"], r["game_id"])
            out[k] = max(out.get(k, 0.0), t)
    return out


def played(rows: list[Row], snaps: list[Row], xw: dict[str, str]) -> dict[Key, set[str]]:
    """(player, team) -> games he played: an offensive snap in snap counts (pfr -> gsis via
    the crosswalk; unmatched keep "pfr:<id>"), or an opportunity of his in play-by-play."""
    out: dict[Key, set[str]] = defaultdict(set)
    for r in snaps:
        if (r["offense_snaps"] or 0) > 0:
            pid = xw.get(r["pfr_player_id"], f"pfr:{r['pfr_player_id']}")
            out[(pid, r["team"])].add(r["game_id"])
    for r in rows:
        if r["posteam"] is None:
            continue
        for pid in (owner(r), dropback_qb(r) if r["qb_dropback"] == 1 and scrimmage(r) else None):
            if pid is not None:
                out[(pid, r["posteam"])].add(r["game_id"])
    return out


# ---- aggregation over (x, d, c) units ----


@dataclass
class Agg:
    n: int
    value: float | None
    value_w: float | None
    n_eff: float


def aggregate(
    units: Iterable[tuple[Key, str, int, float, float, float]], h: float
) -> dict[tuple[Key, str], Agg]:
    """Units (key, cell, games_ago, x, d, c): value = sum x / sum d, value_w the same with G3
    weights, n = sum c, n_eff = (sum w c)^2 / sum w^2 c."""
    acc: dict[tuple[Key, str], list[tuple[float, float, float, float]]] = defaultdict(list)
    for key, cell, g, x, d, c in units:
        acc[(key, cell)].append((0.5 ** (g / h), x, d, c))
    out = {}
    for k, items in acc.items():
        sx = math.fsum(x for _, x, _, _ in items)
        sd = math.fsum(d for _, _, d, _ in items)
        swx = math.fsum(w * x for w, x, _, _ in items)
        swd = math.fsum(w * d for w, _, d, _ in items)
        swc = math.fsum(w * c for w, _, _, c in items)
        sw2c = math.fsum(w * w * c for w, _, _, c in items)
        out[k] = Agg(
            n=round(math.fsum(c for *_, c in items)),
            value=sx / sd if sd else None,
            value_w=swx / swd if swd else None,
            n_eff=swc * swc / sw2c if sw2c else 0.0,
        )
    return out


def share_units(
    rows: list[Row],
    games: dict[Key, set[str]],
    keep: Callable[[Row], bool],
    cell: Callable[[Row], str | None],
    whose: Callable[[Row], str | None],
    x: Callable[[Row], float] = lambda r: 1.0,
    d: Callable[[Row], float] = lambda r: 1.0,
) -> list[tuple[Key, str, int, float, float, float]]:
    """One unit per team opportunity per player of that team who played the game: x = the
    opportunity's value if it was his, else 0; d = the opportunity's value for the team."""
    ga = games_ago(rows)
    by_game: dict[tuple[str, str], list[str]] = defaultdict(list)
    for (pid, team), gs in games.items():
        for gid in gs:
            by_game[(team, gid)].append(pid)
    out = []
    for r in rows:
        if r["posteam"] is None or not keep(r):
            continue
        c = cell(r)
        if c is None:
            continue
        team, gid = r["posteam"], r["game_id"]
        mine = whose(r)
        for pid in by_game.get((team, gid), []):
            out.append(((pid, team), c, ga[team][gid], x(r) if mine == pid else 0.0, d(r), 1.0))
    return out


def own_units(
    rows: list[Row],
    keep: Callable[[Row], bool],
    whose: Callable[[Row], str | None],
    cell: Callable[[Row], str | None],
    x: Callable[[Row], float | None],
) -> list[tuple[Key, str, int, float, float, float]]:
    """One unit per play of his (his targets, his carries...), x = the play's value."""
    ga = games_ago(rows)
    out = []
    for r in rows:
        if r["posteam"] is None or not keep(r):
            continue
        pid, c = whose(r), cell(r)
        val = x(r) if pid is not None and c is not None else None
        if val is None:
            continue
        out.append(((pid, r["posteam"]), c, ga[r["posteam"]][r["game_id"]], float(val), 1.0, 1.0))  # type: ignore[arg-type]
    return out


def shrink(a: Agg | None, prior: float, k: float) -> float:
    if a is None or a.n == 0 or a.value_w is None:
        return prior
    return (a.n_eff * a.value_w + k * prior) / (a.n_eff + k)


__all__ = [
    "PL",
    "Agg",
    "aggregate",
    "designed_run",
    "dropback",
    "dropback_qb",
    "own_units",
    "owner",
    "played",
    "share_units",
    "shrink",
    "target",
    "team_snaps",
    "usage_carry",
    "usage_target",
    "v",
]
