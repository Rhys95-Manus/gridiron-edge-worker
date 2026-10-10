"""PLY-14 and PRJ-06 / BT-02: availability rates.

- PLY-14 practice base rates: P(played | practice status) over every injury-report row with
  that status, whatever its eventual game designation, since the designation is what is
  missing when these rates are used (ruling 2026-10-08).
- PLY-14 return factor: first game back after missing 2+ games, sum of his snap share in that
  game / sum of his baseline (his recency-weighted snap share on the same team before the
  absence, usage half-life; ruling 2026-10-08).
- PRJ-06 weekly missed-game base rates, per position (ruling 2026-10-08): among players who
  played the team's previous game and are on its weekly roster this week, the share with no
  offensive snap.

Each needs BT-02's minimum of events (rows), else it is left missing."""

from __future__ import annotations

import math
from dataclasses import dataclass

import polars as pl

PRACTICE = ("DNP", "Limited", "Full")
POSITIONS = ("QB", "RB", "WR", "TE")


@dataclass(frozen=True)
class RateFit:
    value: float | None
    n: int
    reason: str | None = None


def _rate(flags: list[bool], min_events: int) -> RateFit:
    n = len(flags)
    if n < min_events:
        return RateFit(None, n, f"{n} rows, fewer than the {min_events}-event minimum")
    return RateFit(sum(flags) / n, n)


def practice_base_rates(rows: pl.DataFrame, min_events: int) -> dict[str, RateFit]:
    """rows: practice (DNP / Limited / Full), played (bool)."""
    if rows.is_empty():
        return {s: _rate([], min_events) for s in PRACTICE}
    return {
        s: _rate(rows.filter(pl.col("practice") == s)["played"].to_list(), min_events)
        for s in PRACTICE
    }


def return_factor(rows: pl.DataFrame, min_events: int) -> RateFit:
    """rows: baseline, return_share (one per return)."""
    n = rows.height
    if n < min_events or rows.is_empty():
        return RateFit(None, n, f"{n} returns, fewer than the {min_events}-event minimum")
    den = math.fsum(rows["baseline"].to_list())
    return RateFit(math.fsum(rows["return_share"].to_list()) / den, n)


def qb_starter_pool(rows: pl.DataFrame, min_share: float) -> pl.DataFrame:
    """PRJ-06 (spec synced 2026-10-10): the QB rows keep only QBs with at least `min_share` of
    the team's dropbacks in the team's previous game (column prev_dropback_share); RB, WR and
    TE rows are unchanged."""
    return rows.filter((pl.col("position") != "QB") | (pl.col("prev_dropback_share") >= min_share))


def missed_game_rates(rows: pl.DataFrame, min_events: int) -> dict[str, RateFit]:
    """rows: position, missed (bool)."""
    if rows.is_empty():
        return {p: _rate([], min_events) for p in POSITIONS}
    return {
        p: _rate(rows.filter(pl.col("position") == p)["missed"].to_list(), min_events)
        for p in POSITIONS
    }
