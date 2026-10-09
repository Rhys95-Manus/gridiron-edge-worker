"""Section 4 role slots (spec synced 2026-10-08): QB1, RB1, RB2, WR1, WR2, WR3, TE1.

Slots come from usage rank within the team: at each position, rank by snap share over the
team's games before the target game (tiebreak: target share for WR and TE, carry share for RB
and QB; then gsis_id). The depth chart is used only with no game history yet: in week 1 the
whole position is in depth-chart order; a newly signed player (no game for this team yet) is
placed at his depth-chart rank among the candidates. Depth-chart ties are broken by last
season's offensive snaps on any team (more first; none last), then gsis_id; a player not on the
chart goes last.

Who is ranked (ruling 2026-10-08): in the Phase 3e fitter, players at the position with an
offensive snap in the game; in the live engine, players on the team's latest weekly roster
with status ACT and not designated Out. The callers choose the candidates; this module ranks."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

SLOT_COUNTS = {"QB": 1, "RB": 2, "WR": 3, "TE": 1}
TIEBREAK = {"QB": "carry", "RB": "carry", "WR": "target", "TE": "target"}
SLOTS = tuple(f"{p}{i}" for p, n in SLOT_COUNTS.items() for i in range(1, n + 1))


@dataclass(frozen=True)
class History:
    """His usage over the team's games before the target game: snap share, and the tiebreak
    share for his position (targets for WR/TE, carries for RB/QB)."""

    snap_share: float
    tiebreak_share: float


def _depth_key(
    pid: str, depth: Mapping[str, float], last_snaps: Mapping[str, float]
) -> tuple[float, float, str]:
    rank = depth.get(pid, math.inf)
    snaps = last_snaps.get(pid)
    return (rank, -snaps if snaps is not None else math.inf, pid)


def rank_position(
    position: str,
    candidates: Sequence[str],
    history: Mapping[str, History],
    depth: Mapping[str, float],
    last_snaps: Mapping[str, float],
) -> list[str]:
    """Candidates at one position, best first. `history` has an entry only for players with a
    game for this team before the target game; `depth` maps player -> depth-chart rank (1 =
    starter); `last_snaps` maps player -> last season's offensive snaps on any team."""
    seen = sorted(set(candidates))
    by_depth = sorted(seen, key=lambda p: _depth_key(p, depth, last_snaps))
    hist = sorted(
        (p for p in seen if p in history),
        key=lambda p: (-history[p].snap_share, -history[p].tiebreak_share, p),
    )
    out = list(hist)
    for p in by_depth:
        if p in history:
            continue
        if p not in depth:
            continue  # placed last, below
        at = by_depth.index(p)
        out.insert(min(at, len(out)), p)
    out += [p for p in by_depth if p not in history and p not in depth]
    return out


def slot_labels(position: str, ranked: Sequence[str]) -> dict[str, str]:
    """player -> slot for the top players at a slotted position; others get no slot."""
    n = SLOT_COUNTS.get(position, 0)
    return {p: f"{position}{i + 1}" for i, p in enumerate(ranked[:n])}
