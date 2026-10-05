"""Independent helpers for the section 6b golden tests (PLY-18 to PLY-33, DEF-09 to DEF-17).
Plain Python over row dicts; never imports ge.metrics.

3c rulings (2026-10-04): 'prior = his overall' raises until Phase 3e; league-at-position priors
pool every play by players whose weekly-roster position matches; FTN metrics are missing
before 2022."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

from tests.phase3 import oracle as o
from tests.phase3 import oracle_player as op

Row = dict[str, Any]
Units = list[tuple[op.Key, str, int, float, float, float]]


def attempt(r: Row) -> bool:
    """Plan A3: a pass attempt = pass_attempt == 1 and not a sack (qualifying, G7)."""
    return o.qualifying(r) and r["pass_attempt"] == 1 and r["sack"] != 1


def band_or_unknown(r: Row) -> str:
    return o.depth_band(r["air_yards"]) or "unknown"


def location(r: Row) -> str:
    return r["pass_location"] if r["pass_location"] in ("left", "middle", "right") else "unknown"


def ftn_field(ftn: dict[tuple[str, int], Row], r: Row, field: str) -> Any:
    f = ftn.get((r["game_id"], int(r["play_id"])))
    return None if f is None else f[field]


def positions(snap: Any) -> dict[str, str]:
    """Latest visible weekly-roster position this season; a tie on week goes to the larger
    position string."""
    import polars as pl

    rw = snap.collect("rosters_weekly").filter(pl.col("season") == snap.season)
    best: dict[str, tuple[int, str]] = {}
    for r in rw.select("gsis_id", "week", "position").to_dicts():
        if r["gsis_id"] is not None:
            cand = (r["week"], r["position"] or "")
            if r["gsis_id"] not in best or cand > best[r["gsis_id"]]:
                best[r["gsis_id"]] = cand
    return {g: p for g, (_, p) in best.items()}


def pooled_by_position(units: Units, pos: dict[str, str]) -> dict[tuple[str, str], float]:
    """(position, cell) -> sum x / sum d over every unit of players at that position."""
    sx: dict[tuple[str, str], float] = defaultdict(float)
    sd: dict[tuple[str, str], float] = defaultdict(float)
    for (pid, _), cell, _, x, d, _ in units:
        p = pos.get(pid)
        if p:
            sx[(p, cell)] += x
            sd[(p, cell)] += d
    return {k: sx[k] / sd[k] for k in sx if sd[k]}


def cell_share_units(
    rows: list[Row],
    keep: Callable[[Row], bool],
    whose: Callable[[Row], str | None],
    cell: Callable[[Row], str],
    cells: list[str],
) -> Units:
    """Share of HIS plays in each cell: one unit per his play per cell, x = 1 if in the cell."""
    ga = o.games_ago(rows)
    out: Units = []
    for r in rows:
        if r["posteam"] is None or not keep(r) or (p := whose(r)) is None:
            continue
        c0 = cell(r)
        for c in cells:
            out.append(
                (
                    (p, r["posteam"]),
                    c,
                    ga[r["posteam"]][r["game_id"]],
                    1.0 if c == c0 else 0.0,
                    1.0,
                    1.0,
                )
            )
    return out


def gap(
    rows: list[Row],
    keep: Callable[[Row], bool],
    who: Callable[[Row], tuple[str, str] | None],
    flag: Callable[[Row], bool | None],
    value: Callable[[Row], float],
    h: float,
) -> tuple[dict[tuple[str, str], dict[str, Any]], float | None]:
    """Gap = mean(value | flag) - mean(value | not flag) per entity, its G3-weighted version,
    n and n_eff of the flagged arm; plus the league gap (unweighted, pooled)."""
    ga = o.games_ago(rows)
    arms: dict[tuple[tuple[str, str], bool], list[tuple[float, float]]] = defaultdict(list)
    lg: dict[bool, list[float]] = defaultdict(list)
    for r in rows:
        if not keep(r):
            continue
        k, f = who(r), flag(r)
        if k is None or f is None:
            continue
        team = k[1]
        w = 0.5 ** (ga[team][r["game_id"]] / h)
        arms[(k, f)].append((w, value(r)))
        lg[f].append(value(r))
    out = {}
    for key in {k for k, _ in arms}:
        on, off = arms.get((key, True), []), arms.get((key, False), [])
        row: dict[str, Any] = {"n": len(on), "value": None, "value_w": None, "n_eff": 0.0}
        if on:
            ws = [w for w, _ in on]
            row["n_eff"] = sum(ws) ** 2 / sum(w * w for w in ws)
        if on and off:
            row["value"] = sum(x for _, x in on) / len(on) - sum(x for _, x in off) / len(off)
            row["value_w"] = sum(w * x for w, x in on) / sum(w for w, _ in on) - sum(
                w * x for w, x in off
            ) / sum(w for w, _ in off)
        out[key] = row
    league = (
        sum(lg[True]) / len(lg[True]) - sum(lg[False]) / len(lg[False])
        if lg[True] and lg[False]
        else None
    )
    return out, league
