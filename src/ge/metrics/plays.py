"""Shared play filters as polars expressions: G5, G7 and the play sets the spec names.

Each reading of the spec that the Phase 3 plan had to make (A3, A4, A5, A6, A13) is stated
where it is applied, so changing one touches one place.

Data: nflverse; charting: FTN Data via nflverse."""

from __future__ import annotations

import polars as pl

from ge.config import load_params

_P = load_params()
_C = _P.conventions
_O = _P.offense

RUN_CELLS = (
    "left_end",
    "left_tackle",
    "left_guard",
    "middle",
    "right_guard",
    "right_tackle",
    "right_end",
    "unknown",
)
PASS_LOCATIONS = ("left", "middle", "right")
DEPTH_BANDS = ("behind", "short", "intermediate", "deep")
PASS_CELLS = (*(f"{loc}_{b}" for loc in PASS_LOCATIONS for b in DEPTH_BANDS), "unknown")
DOWN_ZONE_CELLS = tuple(
    f"{d}_{z}" for d in ("d1", "d2", "d34") for z in ("own", "open", "red_zone", "goal_to_go")
)


def _is1(col: str) -> pl.Expr:
    return (pl.col(col) == 1).fill_null(False)


def garbage() -> pl.Expr:
    """G7: wp < 0.05 or > 0.95 in the 4th quarter. Overtime counts as 4th quarter or later
    (plan A13). A null wp is not garbage time."""
    wp = pl.col("wp")
    return (
        (pl.col("qtr") >= 4)
        & ((wp < _C.g7_garbage_wp_low.value) | (wp > _C.g7_garbage_wp_high.value))
    ).fill_null(False)


def neutral() -> pl.Expr:
    """G5: wp between 0.20 and 0.80 (inclusive) and not inside the final 2:00 of either half."""
    return (
        pl.col("wp").is_between(_C.g5_neutral_wp_min.value, _C.g5_neutral_wp_max.value)
        & (pl.col("half_seconds_remaining") > _C.g5_end_of_half_excluded_seconds.value)
    ).fill_null(False)


def scrimmage() -> pl.Expr:
    """G7 kneels, spikes and no-play penalties out; two-point tries out too (plan A4: they
    carry pass/rush and EPA but aren't plays from scrimmage downs)."""
    return (
        (pl.col("play_type") != "no_play").fill_null(True)
        & ~_is1("qb_kneel")
        & ~_is1("qb_spike")
        & ~_is1("two_point_attempt")
    )


def qualifying() -> pl.Expr:
    """Section 2: a qualifying play is pass == 1 or rush == 1 (sacks and scrambles are pass
    plays), with G7's exclusions."""
    return (_is1("pass") | _is1("rush")) & scrimmage() & ~garbage()


def dropback() -> pl.Expr:
    """Plan A3: a dropback is qb_dropback == 1, with G7's exclusions."""
    return _is1("qb_dropback") & scrimmage() & ~garbage()


def designed_run() -> pl.Expr:
    """OFF-12: rush == 1, qb_scramble == 0, no kneels; with G7's exclusions."""
    return _is1("rush") & ~_is1("qb_scramble") & scrimmage() & ~garbage()


def target() -> pl.Expr:
    """PLY-03: a target is a pass play with a receiver_player_id (qualifying)."""
    return qualifying() & _is1("pass") & pl.col("receiver_player_id").is_not_null()


def usage_target() -> pl.Expr:
    """PLY-03 for usage shares: a pass play with a receiver_player_id. Usage keeps garbage
    time (plan A26: G7 removes it from efficiency and tendency metrics only)."""
    return _is1("pass") & pl.col("receiver_player_id").is_not_null() & scrimmage()


def usage_carry() -> pl.Expr:
    """PLY-05 for usage shares: a designed carry (rush == 1, not a scramble), garbage time
    kept (plan A26)."""
    return _is1("rush") & ~_is1("qb_scramble") & scrimmage()


def dropback_qb() -> pl.Expr:
    """The QB on a dropback: passer_player_id, or rusher_player_id on a scramble (nflverse
    leaves the passer empty on scrambles: 501 of 501 in the 2024 fixture)."""
    return pl.coalesce(
        pl.col("passer_player_id"),
        pl.when(_is1("qb_scramble")).then(pl.col("rusher_player_id")),
    )


def offensive_td() -> pl.Expr:
    """Plan A20: a touchdown scored by the offense on the play (td_team == posteam)."""
    return _is1("touchdown") & (pl.col("td_team") == pl.col("posteam")).fill_null(False)


def run_cell() -> pl.Expr:
    """OFF-12 cell from run_location x run_gap, offense's view. Middle has no gap. Runs with
    no location, or left/right with no gap, go to `unknown` (plan A5), so cells still sum to
    the team's designed carries."""
    loc, gap = pl.col("run_location"), pl.col("run_gap")
    return (
        pl.when(loc == "middle")
        .then(pl.lit("middle"))
        .when(loc.is_in(["left", "right"]) & gap.is_in(["end", "tackle", "guard"]))
        .then(pl.concat_str([loc, gap], separator="_"))
        .otherwise(pl.lit("unknown"))
    )


def depth_band() -> pl.Expr:
    """OFF-13 bands: behind the line (air_yards < 0), short 0-9, intermediate 10-19, deep 20+."""
    a = pl.col("air_yards")
    return (
        pl.when(a < _O.off_13_short_min_air_yards.value)
        .then(pl.lit("behind"))
        .when(a < _O.off_13_intermediate_min_air_yards.value)
        .then(pl.lit("short"))
        .when(a < _O.off_13_deep_min_air_yards.value)
        .then(pl.lit("intermediate"))
        .when(a.is_not_null())
        .then(pl.lit("deep"))
    )


def pass_cell() -> pl.Expr:
    """OFF-13 cell: pass_location x depth band; either one missing -> `unknown`."""
    band = depth_band()
    loc = pl.col("pass_location")
    return (
        pl.when(loc.is_in(list(PASS_LOCATIONS)) & band.is_not_null())
        .then(pl.concat_str([loc, band], separator="_"))
        .otherwise(pl.lit("unknown"))
    )


def down_zone_cell() -> pl.Expr:
    """OFF-03 cell: downs {1, 2, 3-4} x zones {own 1-20 (yardline_100 >= 80), open field,
    red zone (<= 20), goal-to-go}. Goal-to-go takes precedence over red zone (plan A6)."""
    d = pl.col("down")
    yl = pl.col("yardline_100")
    dn = pl.when(d == 1).then(pl.lit("d1")).when(d == 2).then(pl.lit("d2")).otherwise(pl.lit("d34"))
    zone = (
        pl.when(_is1("goal_to_go"))
        .then(pl.lit("goal_to_go"))
        .when(yl <= _O.off_03_red_zone_max_yardline_100.value)
        .then(pl.lit("red_zone"))
        .when(yl >= _O.off_03_own_zone_min_yardline_100.value)
        .then(pl.lit("own"))
        .otherwise(pl.lit("open"))
    )
    return pl.concat_str([dn, zone], separator="_")
