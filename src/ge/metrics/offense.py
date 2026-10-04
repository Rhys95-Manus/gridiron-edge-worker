"""Team offense profile (spec section 2): OFF-01 to OFF-17.

Each function takes a MetricContext and returns raw rows in the engine's schema; how each
stat is shrunk (k, prior) is declared in ge.metrics.registry. Every metric is season to date,
recency-weighted (G3) with garbage time removed (G7). All team metrics use the efficiency
half-life (plan A2).

Data: nflverse; charting: FTN Data via nflverse."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

import polars as pl

from ge.config import load_params
from ge.metrics import conventions as cv
from ge.metrics import plays as pf
from ge.metrics.context import MetricContext
from ge.metrics.engine import Side, finish, summarise

_O = load_params().offense
H: cv.HalfLife = "efficiency"
SPLITS = ("all", "pass", "run")
OL_POSITIONS = ("T", "G", "C")


def _col(side: Side) -> tuple[str, str]:
    return ("posteam", "g_off") if side == "offense" else ("defteam", "g_def")


def team_units(
    ctx: MetricContext, mask: pl.Expr, cell: pl.Expr, x: pl.Expr, side: Side
) -> pl.DataFrame:
    """Rows of (entity_id, team, cell, g, x) for the side's team on each kept play."""
    team, g = _col(side)
    return ctx.plays.filter(mask).select(
        pl.col(team).alias("entity_id"),
        pl.col(team).alias("team"),
        cell.cast(pl.Utf8).alias("cell"),
        pl.col(g).cast(pl.Float64).alias("g"),
        x.cast(pl.Float64).alias("x"),
    )


def team_rate(
    ctx: MetricContext,
    spec_id: str,
    stat: str,
    units: pl.DataFrame,
    cells: Sequence[str],
    min_n: dict[str, float] | float | None,
) -> pl.DataFrame:
    return summarise(
        units,
        spec_id=spec_id,
        stat=stat,
        entity_type="team",
        entities=ctx.teams,
        cells=cells,
        h=cv.half_life(H),
        min_n=min_n,
    )


def split_units(ctx: MetricContext, x: pl.Expr, side: Side) -> pl.DataFrame:
    """Qualifying plays as cells all / pass / run (OFF-01, OFF-02, DEF-01, DEF-02)."""
    q = pf.qualifying()
    masks = {"all": q, "pass": q & (pl.col("pass") == 1), "run": q & (pl.col("rush") == 1)}
    return pl.concat([team_units(ctx, m, pl.lit(c), x, side) for c, m in masks.items()])


def off_01(ctx: MetricContext) -> pl.DataFrame:
    """OFF-01: EPA per play, overall / pass / run: mean(epa) over qualifying plays. Min 150 plays
    (100 pass, 80 run). The opponent-adjusted value is off_01_adjusted (G6)."""
    mins = {
        "all": _O.off_01_min_plays.value,
        "pass": _O.off_01_min_pass_plays.value,
        "run": _O.off_01_min_run_plays.value,
    }
    return team_rate(ctx, "OFF-01", "epa", split_units(ctx, pl.col("epa"), "offense"), SPLITS, mins)


def off_01_adjusted(ctx: MetricContext) -> pl.DataFrame:
    """OFF-01 / G6: opponent-adjusted EPA from the weighted ridge regression. Its penalty comes
    from BT-02, so this raises until a fitted value exists (user decision 2026-10-02)."""
    cv.g6_penalty()
    raise AssertionError("unreachable")


def off_02(ctx: MetricContext) -> pl.DataFrame:
    """OFF-02: success rate, overall / pass / run: mean(success). Min 150 plays."""
    u = split_units(ctx, pl.col("success"), "offense")
    return team_rate(ctx, "OFF-02", "success", u, SPLITS, _O.off_02_min_plays.value)


def down_zone(ctx: MetricContext, spec_id: str, side: Side, min_n: float) -> pl.DataFrame:
    parts = [
        team_rate(
            ctx,
            spec_id,
            stat,
            team_units(ctx, pf.qualifying(), pf.down_zone_cell(), pl.col(stat), side),
            pf.DOWN_ZONE_CELLS,
            min_n,
        )
        for stat in ("epa", "success")
    ]
    return pl.concat(parts)


def off_03(ctx: MetricContext) -> pl.DataFrame:
    """OFF-03: EPA and success by down {1, 2, 3-4} x field zone {own 1-20, open field, red
    zone, goal-to-go}. Min 30 plays per cell."""
    return down_zone(ctx, "OFF-03", "offense", _O.off_03_min_plays_per_cell.value)


def off_04(ctx: MetricContext) -> pl.DataFrame:
    """OFF-04: early-down pass rate (neutral): mean(pass) on downs 1-2, neutral plays (G5)."""
    m = pf.qualifying() & pf.neutral() & pl.col("down").is_in([1, 2])
    u = team_units(ctx, m, pl.lit("all"), pl.col("pass"), "offense")
    return team_rate(ctx, "OFF-04", "pass_rate", u, ["all"], _O.off_04_min_plays.value)


def off_05(ctx: MetricContext) -> pl.DataFrame:
    """OFF-05: pass rate over expected (neutral): mean(pass - xpass) on neutral plays."""
    m = pf.qualifying() & pf.neutral() & pl.col("xpass").is_not_null()
    u = team_units(ctx, m, pl.lit("all"), pl.col("pass") - pl.col("xpass"), "offense")
    return team_rate(ctx, "OFF-05", "proe", u, ["all"], _O.off_05_min_plays.value)


def _ftn_rate(
    ctx: MetricContext, spec_id: str, stat: str, field: str, mask: pl.Expr, min_n: float
) -> pl.DataFrame:
    if field not in ctx.plays.columns:  # no FTN rows (before 2022): n = 0, no league value
        x = pl.lit(None, dtype=pl.Float64)
        note = "no FTN"
    else:
        x, note = pl.col(field), None
    u = team_units(ctx, mask, pl.lit("all"), x, "offense")
    out = team_rate(ctx, spec_id, stat, u, ["all"], min_n)
    return out.with_columns(pl.lit(note, dtype=pl.Utf8).alias("note")) if note else out


def ftn_join_rate(ctx: MetricContext) -> pl.DataFrame:
    """OFF-06 / OFF-07 / OFF-08 report: per offense, how many of its dropbacks and qualifying
    plays have an FTN charting row (team, plays, n, joined, rate). A play counts as joined
    when FTN charted it, whatever the field values."""
    has = "ftn_charted" in ctx.plays.columns
    joined = pl.col("ftn_charted").fill_null(False) if has else pl.lit(False)
    parts = []
    for name, mask in (("dropbacks", pf.dropback()), ("qualifying", pf.qualifying())):
        parts.append(
            ctx.plays.filter(mask)
            .group_by(pl.col("posteam").alias("team"))
            .agg(pl.len().cast(pl.Int64).alias("n"), joined.sum().cast(pl.Int64).alias("joined"))
            .with_columns(pl.lit(name).alias("plays"))
        )
    return (
        pl.concat(parts)
        .with_columns((pl.col("joined") / pl.col("n")).alias("rate"))
        .select("team", "plays", "n", "joined", "rate")
        .sort("plays", "team")
    )


def off_06(ctx: MetricContext) -> pl.DataFrame:
    """OFF-06: play-action rate: mean(is_play_action) over dropbacks (FTN)."""
    return _ftn_rate(
        ctx,
        "OFF-06",
        "play_action_rate",
        "is_play_action",
        pf.dropback(),
        _O.off_06_min_dropbacks.value,
    )


def off_07(ctx: MetricContext) -> pl.DataFrame:
    """OFF-07: pre-snap motion rate: mean(is_motion) over qualifying plays (FTN)."""
    return _ftn_rate(
        ctx, "OFF-07", "motion_rate", "is_motion", pf.qualifying(), _O.off_07_min_plays.value
    )


def off_08(ctx: MetricContext) -> pl.DataFrame:
    """OFF-08: RPO rate: mean(is_rpo) over qualifying plays (FTN)."""
    return _ftn_rate(
        ctx, "OFF-08", "rpo_rate", "is_rpo", pf.qualifying(), _O.off_08_min_plays.value
    )


def off_09(ctx: MetricContext) -> pl.DataFrame:
    """OFF-09: shotgun rate: mean(shotgun) over qualifying plays."""
    u = team_units(ctx, pf.qualifying(), pl.lit("all"), pl.col("shotgun"), "offense")
    return team_rate(ctx, "OFF-09", "shotgun_rate", u, ["all"], _O.off_09_min_plays.value)


def _flag(c: str) -> pl.Expr:
    return (pl.col(c) == 1).fill_null(False)


def pace_pairs(ctx: MetricContext) -> pl.DataFrame:
    """OFF-10 pairs: one row per kept pair, keyed by the prior play (game_id, fixed_drive,
    play_id), with the offense, its games-ago g and the clipped delta x. The sequence is the
    game's snap and timeout rows in play_id order; both plays qualifying, same drive
    (fixed_drive) and quarter, the prior play neutral (G5) and not incomplete, out of bounds, a
    timeout, a penalty or a turnover; delta capped (clipped) at 45 s."""
    cap = _O.off_10_max_snap_gap_seconds.value
    seq = (
        ctx.plays.filter(pl.col("play_type").is_not_null() | _flag("timeout"))
        .sort("game_id", "play_id")
        .with_columns(
            pf.qualifying().alias("_q"),
            pf.neutral().alias("_neutral"),
            (
                _flag("incomplete_pass")
                | _flag("out_of_bounds")
                | _flag("timeout")
                | _flag("penalty")
                | _flag("interception")
                | _flag("fumble_lost")
            ).alias("_stop"),
        )
    )
    nxt = {
        c: pl.col(c).shift(-1).over("game_id")
        for c in ("posteam", "fixed_drive", "qtr", "_q", "game_seconds_remaining")
    }
    pairs = seq.with_columns(**{f"_b{c}": e for c, e in nxt.items()}).filter(
        pl.col("posteam").is_not_null()
        & pl.col("posteam").eq_missing(pl.col("_bposteam"))
        & pl.col("fixed_drive").eq_missing(pl.col("_bfixed_drive"))
        & pl.col("qtr").eq_missing(pl.col("_bqtr"))
        & pl.col("_q")
        & pl.col("_b_q").fill_null(False)
        & pl.col("_neutral")
        & ~pl.col("_stop")
    )
    return pairs.select(
        "game_id",
        "fixed_drive",
        "play_id",
        "posteam",
        pl.col("g_off").cast(pl.Float64).alias("g"),
        pl.min_horizontal(
            pl.col("game_seconds_remaining") - pl.col("_bgame_seconds_remaining"), pl.lit(cap)
        )
        .cast(pl.Float64)
        .alias("x"),
    )


def off_10(ctx: MetricContext) -> pl.DataFrame:
    """OFF-10: neutral pace: mean seconds (game_seconds_remaining) between consecutive plays in
    the same drive and quarter, over the pairs pace_pairs keeps (plan A7)."""
    u = pace_pairs(ctx).select(
        pl.col("posteam").alias("entity_id"),
        pl.col("posteam").alias("team"),
        pl.lit("all").alias("cell"),
        "g",
        "x",
    )
    return team_rate(ctx, "OFF-10", "seconds_per_play", u, ["all"], _O.off_10_min_pairs.value)


def off_11(ctx: MetricContext) -> pl.DataFrame:
    """OFF-11: plays per game: qualifying plays / games. n = games (k in games)."""
    per_game = (
        ctx.plays.filter(pf.qualifying())
        .group_by("posteam", "game_id")
        .agg(pl.len().alias("x"), pl.col("g_off").first().alias("g"))
    )
    u = per_game.select(
        pl.col("posteam").alias("entity_id"),
        pl.col("posteam").alias("team"),
        pl.lit("all").alias("cell"),
        pl.col("g").cast(pl.Float64),
        pl.col("x").cast(pl.Float64),
    )
    return team_rate(ctx, "OFF-11", "plays_per_game", u, ["all"], _O.off_11_min_games.value)


def run_grid(ctx: MetricContext, spec_id: str, side: Side, min_n: float) -> pl.DataFrame:
    """OFF-12 / DEF-03 grid on designed runs: carries, yards/carry, EPA/carry, success,
    explosive rate (10+ yards), per cell."""
    exp = _O.off_12_explosive_run_min_yards.value
    stats = {
        "carries": pl.lit(1.0),
        "ypc": pl.col("yards_gained"),
        "epa": pl.col("epa"),
        "success": pl.col("success"),
        "explosive": (pl.col("yards_gained") >= exp).cast(pl.Float64),
    }
    return pl.concat(
        [
            team_rate(
                ctx,
                spec_id,
                s,
                team_units(ctx, pf.designed_run(), pf.run_cell(), x, side),
                pf.RUN_CELLS,
                min_n,
            )
            for s, x in stats.items()
        ]
    )


def off_12(ctx: MetricContext) -> pl.DataFrame:
    """OFF-12: directional run grid. Designed runs (rush == 1, qb_scramble == 0, no kneels) by
    run_location x run_gap in 7 cells (left/right from the offense's view; middle has no gap),
    plus an `unknown` cell for runs nflverse didn't chart (plan A5). Min 25 carries per cell."""
    return run_grid(ctx, "OFF-12", "offense", _O.off_12_min_carries_per_cell.value)


def pass_map(ctx: MetricContext, spec_id: str, side: Side, min_n: float) -> pl.DataFrame:
    """OFF-13 / DEF-09 cells on targets: target share, EPA per target, completion over
    expected. Every stat's min-sample flag uses the cell's own target count."""
    team, g = _col(side)
    tg = ctx.plays.filter(pf.target()).with_columns(pf.pass_cell().alias("_cell"))
    cells = pl.DataFrame({"cell": list(pf.PASS_CELLS)})
    share_units = tg.join(cells, how="cross").select(
        pl.col(team).alias("entity_id"),
        pl.col(team).alias("team"),
        pl.col("cell"),
        pl.col(g).cast(pl.Float64).alias("g"),
        (pl.col("_cell") == pl.col("cell")).cast(pl.Float64).alias("x"),
    )
    share = team_rate(ctx, spec_id, "share", share_units, pf.PASS_CELLS, min_n)
    epa = team_rate(
        ctx,
        spec_id,
        "epa",
        team_units(ctx, pf.target(), pf.pass_cell(), pl.col("epa"), side),
        pf.PASS_CELLS,
        min_n,
    )
    cp = pf.target() & pl.col("cp").is_not_null()
    cpoe = team_rate(
        ctx,
        spec_id,
        "cpoe",
        team_units(ctx, cp, pf.pass_cell(), pl.col("complete_pass") - pl.col("cp"), side),
        pf.PASS_CELLS,
        min_n,
    )
    counts = tg.group_by(pl.col(team).alias("entity_id"), pl.col("_cell").alias("cell")).agg(
        pl.len().alias("_targets")
    )
    share = share.join(counts, on=["entity_id", "cell"], how="left").with_columns(
        pl.when(pl.col("entity_type") == "league")
        .then(pl.lit(False))
        .otherwise(pl.col("_targets").fill_null(0) < pl.col("min_n"))
        .alias("below_min_sample")
    )
    return pl.concat([finish(share), epa, cpoe])


def off_13(ctx: MetricContext) -> pl.DataFrame:
    """OFF-13: pass map. Target share, EPA/target, completion over expected (complete_pass -
    cp) in 12 cells: pass_location {left, middle, right} x depth {behind line, short 0-9,
    intermediate 10-19, deep 20+}, plus `unknown`. Min 20 targets per cell."""
    return pass_map(ctx, "OFF-13", "offense", _O.off_13_min_targets_per_cell.value)


def zone_trips(ctx: MetricContext, side: Side, zone: float) -> pl.DataFrame:
    """OFF-14 / DEF-07: one unit per drive with a scrimmage snap at yardline_100 <= zone
    (plan A13), x = 1 if the offense scored a TD on the drive. A drive whose first in-zone
    snap is garbage time (G7) is left out."""
    snaps = ["pass", "run", "no_play", "field_goal", "punt", "qb_kneel", "qb_spike"]
    key = ["game_id", "fixed_drive", "posteam"]
    p = ctx.plays.filter(pl.col("posteam").is_not_null() & pl.col("fixed_drive").is_not_null())
    tds = p.group_by(key).agg(pf.offensive_td().any().alias("_td"))
    first = (
        p.filter(pl.col("play_type").is_in(snaps) & (pl.col("yardline_100") <= zone))
        .sort("play_id")
        .group_by(key, maintain_order=True)
        .first()
        .filter(~pf.garbage())
    )
    team, g = _col(side)
    return first.join(tds, on=key, how="left").select(
        pl.col(team).alias("entity_id"),
        pl.col(team).alias("team"),
        pl.lit(f"inside_{int(zone)}").alias("cell"),
        pl.col(g).cast(pl.Float64).alias("g"),
        pl.col("_td").cast(pl.Float64).alias("x"),
    )


def off_14(ctx: MetricContext) -> pl.DataFrame:
    """OFF-14: red zone and goal-to-go. Pass share of plays inside the 20, 10 and 5; TDs per
    drive reaching each zone. Min 20 plays; 10 trips."""
    zones = (
        _O.off_14_zone_20_yardline_100.value,
        _O.off_14_zone_10_yardline_100.value,
        _O.off_14_zone_5_yardline_100.value,
    )
    cells = [f"inside_{int(z)}" for z in zones]
    plays_u = pl.concat(
        [
            team_units(
                ctx,
                pf.qualifying() & (pl.col("yardline_100") <= z),
                pl.lit(f"inside_{int(z)}"),
                pl.col("pass"),
                "offense",
            )
            for z in zones
        ]
    )
    trips_u = pl.concat([zone_trips(ctx, "offense", z) for z in zones])
    return pl.concat(
        [
            team_rate(ctx, "OFF-14", "pass_share", plays_u, cells, _O.off_14_min_plays.value),
            team_rate(ctx, "OFF-14", "td_per_trip", trips_u, cells, _O.off_14_min_trips.value),
        ]
    )


def hit_flag() -> pl.Expr:
    """OFF-15 / DEF-05 QB-hit rate: a dropback with a sack or a QB hit (user decision
    2026-10-02; nflverse flags qb_hit on most sacks, so the literal sum double-counts)."""
    return (_flag("sack") | _flag("qb_hit")).cast(pl.Float64)


def off_15(ctx: MetricContext) -> pl.DataFrame:
    """OFF-15: pass protection proxy (true pressure rate is not in free data): sacks /
    dropbacks and (sacks or QB hits) / dropbacks, shown beside NGS time to throw (weekly
    values weighted by attempts, plan A24; display only)."""
    mn = _O.off_15_min_dropbacks.value
    sack = team_rate(
        ctx,
        "OFF-15",
        "sack_rate",
        team_units(ctx, pf.dropback(), pl.lit("all"), pl.col("sack"), "offense"),
        ["all"],
        mn,
    )
    hit = team_rate(
        ctx,
        "OFF-15",
        "hit_rate",
        team_units(ctx, pf.dropback(), pl.lit("all"), hit_flag(), "offense"),
        ["all"],
        mn,
    )
    ngs = ctx.table("nextgen_passing")
    if ngs.height:
        ttt = (
            ngs.filter(pl.col("avg_time_to_throw").is_not_null() & (pl.col("attempts") > 0))
            .group_by("team_abbr")
            .agg(
                (
                    (pl.col("attempts") * pl.col("avg_time_to_throw")).sum()
                    / pl.col("attempts").sum()
                ).alias("value"),
                pl.col("attempts").sum().cast(pl.Int64).alias("n"),
            )
            .select(
                pl.lit("OFF-15").alias("spec_id"),
                pl.lit("team").alias("entity_type"),
                pl.col("team_abbr").alias("entity_id"),
                pl.col("team_abbr").alias("team"),
                pl.lit("all").alias("cell"),
                pl.lit("time_to_throw").alias("stat"),
                "value",
                "n",
                pl.lit("NGS weekly time to throw, attempts-weighted; display only").alias("note"),
            )
        )
    else:
        ttt = pl.DataFrame()
    return pl.concat([sack, hit, finish(ttt) if ttt.height else ttt.clear()], how="diagonal")


def off_16(ctx: MetricContext) -> pl.DataFrame:
    """OFF-16: run blocking by side (a proxy that mixes blocking with the runner's skill):
    success rate and stuff rate (gain <= 0) on designed runs to the left vs right."""
    m = pf.designed_run() & pl.col("run_location").is_in(["left", "right"])
    stuff = (pl.col("yards_gained") <= _O.off_16_stuff_max_yards.value).cast(pl.Float64)
    mn = _O.off_16_min_carries_per_side.value
    side = ["left", "right"]
    return pl.concat(
        [
            team_rate(
                ctx,
                "OFF-16",
                "success",
                team_units(ctx, m, pl.col("run_location"), pl.col("success"), "offense"),
                side,
                mn,
            ),
            team_rate(
                ctx,
                "OFF-16",
                "stuff",
                team_units(ctx, m, pl.col("run_location"), stuff, "offense"),
                side,
                mn,
            ),
        ]
    )


def status_note(ctx: MetricContext) -> dict[tuple[str, str], str]:
    """(team, gsis_id) -> this week's game status: the report_status, "no game status" for a
    player on the report without one; players absent from the report aren't keys."""
    inj = ctx.injuries_now()
    return {
        (r["team"], r["gsis_id"]): r["report_status"] or "no game status"
        for r in inj.select("team", "gsis_id", "report_status").iter_rows(named=True)
    }


def off_17(ctx: MetricContext) -> pl.DataFrame:
    """OFF-17: offensive-line continuity and injuries. Starters = the 5 OL with the most
    offensive snaps in the team's last 3 games; continuity = share of the team's games this
    season in which all 5 played >= 50% of snaps (plan A8: per-snap participation isn't in
    free in-season data); plus each starter's current injury-report status. A count: no
    shrinkage."""
    n_ol = int(_O.off_17_starting_ol_count.value)
    look = int(_O.off_17_starter_lookback_games.value)
    min_pct = _O.off_17_continuity_min_snap_share.value
    snaps = ctx.table("snap_counts")
    status = status_note(ctx)
    team_rows, starter_rows = [], []
    by_team: dict[str, list[dict[str, object]]] = defaultdict(list)
    for r in snaps.select(
        "team", "week", "pfr_player_id", "position", "offense_snaps", "offense_pct"
    ).iter_rows(named=True):
        by_team[r["team"]].append(r)
    for team in ctx.teams["team"].to_list():
        mine = by_team.get(team, [])
        weeks = sorted({int(r["week"]) for r in mine}, reverse=True)  # type: ignore[call-overload]
        last = set(weeks[:look])
        tot: dict[str, float] = defaultdict(float)
        for r in mine:
            if r["week"] in last and r["position"] in OL_POSITIONS:
                tot[str(r["pfr_player_id"])] += float(r["offense_snaps"] or 0)  # type: ignore[arg-type]
        top = sorted(tot, key=lambda p: (-tot[p], p))[:n_ol]
        full = 0
        for w in weeks:
            pct = {
                r["pfr_player_id"]: float(r["offense_pct"] or 0)  # type: ignore[arg-type]
                for r in mine
                if r["week"] == w
            }
            full += all(pct.get(p, 0.0) >= min_pct for p in top)
        team_rows.append(
            {
                "entity_type": "team",
                "entity_id": team,
                "team": team,
                "cell": "OL",
                "stat": "continuity",
                "value": full / len(weeks) if weeks else None,
                "n": len(weeks),
                "note": f"starters: {len(top)} OL",
            }
        )
        xw = ctx.crosswalk
        for p in top:
            gid = xw.get(p, f"pfr:{p}")
            starter_rows.append(
                {
                    "entity_type": "player",
                    "entity_id": gid,
                    "team": team,
                    "cell": "OL",
                    "stat": "starter",
                    "value": tot[p],
                    "n": len(last),
                    "note": status.get((team, gid), "not on report"),
                }
            )
    df = pl.DataFrame(team_rows + starter_rows, infer_schema_length=None)
    return finish(df.with_columns(pl.lit("OFF-17").alias("spec_id"))).sort(
        "entity_type", "team", "entity_id"
    )
