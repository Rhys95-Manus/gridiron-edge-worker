"""PRJ-02 rating tilt, as the simulation applies it: each component shifts by its slope times
the net rating of its side (offense rating + opposing defense rating, 01a EPA per play centred
on the league)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TiltSlopes:
    completion: float  # logit per EPA/play, net pass
    yac: float  # yards per EPA/play, net pass
    interception: float  # logit per EPA/play, net pass
    yards_per_carry: float  # yards per EPA/play, net run
    fumble: float  # logit per EPA/play (fumble lost), net run


@dataclass(frozen=True)
class TiltShifts:
    completion_logit: float
    yac_yards: float
    interception_logit: float
    ypc_yards: float
    fumble_logit: float


def tilt_shifts(slopes: TiltSlopes, *, net_pass: float, net_run: float) -> TiltShifts:
    """PRJ-02 rating tilt: the five shifts for one offense against one defense."""
    return TiltShifts(
        completion_logit=slopes.completion * net_pass,
        yac_yards=slopes.yac * net_pass,
        interception_logit=slopes.interception * net_pass,
        ypc_yards=slopes.yards_per_carry * net_run,
        fumble_logit=slopes.fumble * net_run,
    )
