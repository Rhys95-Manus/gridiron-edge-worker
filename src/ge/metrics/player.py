"""Player profile (spec section 4): PLY-01 to PLY-17.

3b rulings (2026-10-04): shares use the team's opportunities in the games he played; rows are
keyed by (player, team) stint; usage shares keep garbage time and use the usage half-life,
efficiency stats drop it (plan A26). Player metrics shrink toward a role prior (section 4),
which Phase 3e estimates; until then those shrunk values raise. Player IDs are GSIS; snap
counts are mapped through the DATA-04 crosswalk, unmatched players keep "pfr:<id>".

Data: nflverse; charting: FTN Data via nflverse."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence

import polars as pl

from ge.config import load_params
from ge.metrics import conventions as cv
from ge.metrics import plays as pf
from ge.metrics.context import MetricContext
from ge.metrics.engine import NO_FTN, finish, summarise

_P = load_params().player
PAID = "PAID: DATA-11"
DESIGNATIONS = ("Out", "Doubtful", "Questionable")


# ---- shared builders ----


def stints(ctx: MetricContext) -> pl.DataFrame:
    """entity_id / team for every (player, team) with a game played this season."""
    return (
        ctx.played.select(pl.col("gsis_id").alias("entity_id"), "team")
        .unique()
        .sort("entity_id", "team")
    )


def _rate(
    ctx: MetricContext,
    spec_id: str,
    stat: str,
    units: pl.DataFrame,
    cells: Sequence[str],
    entities: pl.DataFrame,
    half_life: cv.HalfLife,
    min_n: float | None = None,
    league: bool = False,
) -> pl.DataFrame:
    return summarise(
        units,
        spec_id=spec_id,
        stat=stat,
        entity_type="player",
        entities=entities,
        cells=cells,
        h=cv.half_life(half_life),
        min_n=min_n,
        league=league,
    )


def share_units(
    ctx: MetricContext,
    mask: pl.Expr,
    cell: pl.Expr,
    whose: pl.Expr,
    x: pl.Expr | None = None,
    d: pl.Expr | None = None,
) -> pl.DataFrame:
    """One unit per team opportunity (mask, posteam's plays) per player of that team who
    played the game: x = the opportunity's value if it was his, else 0; d = its value for
    the team (both 1 for a plain share)."""
    opp = (
        ctx.plays.filter(mask & pl.col("posteam").is_not_null())
        .select(
            pl.col("posteam").alias("team"),
            "game_id",
            cell.cast(pl.Utf8).alias("cell"),
            whose.cast(pl.Utf8).alias("_who"),
            pl.col("g_off").cast(pl.Float64).alias("g"),
            (x if x is not None else pl.lit(1.0)).cast(pl.Float64).alias("_x"),
            (d if d is not None else pl.lit(1.0)).cast(pl.Float64).alias("d"),
        )
        .filter(pl.col("cell").is_not_null())
    )
    return opp.join(ctx.played, on=["team", "game_id"], how="inner").select(
        pl.col("gsis_id").alias("entity_id"),
        "team",
        "cell",
        "g",
        pl.when(pl.col("_who") == pl.col("gsis_id")).then(pl.col("_x")).otherwise(0.0).alias("x"),
        "d",
    )


def own_units(
    ctx: MetricContext, mask: pl.Expr, whose: pl.Expr, cell: pl.Expr, x: pl.Expr
) -> pl.DataFrame:
    """One unit per play of his (his targets, his carries...): x = the play's value."""
    return (
        ctx.plays.filter(mask & pl.col("posteam").is_not_null())
        .select(
            whose.cast(pl.Utf8).alias("entity_id"),
            pl.col("posteam").alias("team"),
            cell.cast(pl.Utf8).alias("cell"),
            pl.col("g_off").cast(pl.Float64).alias("g"),
            x.cast(pl.Float64).alias("x"),
        )
        .filter(
            pl.col("entity_id").is_not_null()
            & pl.col("cell").is_not_null()
            & pl.col("x").is_not_null()
        )
    )


def _entities(units: pl.DataFrame) -> pl.DataFrame:
    return units.select("entity_id", "team").unique().sort("entity_id", "team")


def _games_played(ctx: MetricContext) -> pl.DataFrame:
    return ctx.played.group_by(pl.col("gsis_id").alias("entity_id"), "team").agg(
        pl.len().alias("_games")
    )


def _min_games(ctx: MetricContext, df: pl.DataFrame, min_games: float) -> pl.DataFrame:
    """Section 4 minimums in games (PLY-03/04/05/08: "3 games"): greyed below that many games
    played, whatever n (team opportunities) is."""
    out = df.join(_games_played(ctx), on=["entity_id", "team"], how="left").with_columns(
        pl.lit(float(min_games)).alias("min_n"),
        (pl.col("_games").fill_null(0) < min_games).alias("below_min_sample"),
        pl.concat_str(
            [pl.lit("min in games; played "), pl.col("_games").fill_null(0).cast(pl.Utf8)]
        ).alias("note"),
    )
    return finish(out)


# ---- PLY-01 to PLY-08: usage ----


def _snap_units(ctx: MetricContext) -> pl.DataFrame:
    s = ctx.snaps
    if s.is_empty():
        return pl.DataFrame(
            schema={
                "entity_id": pl.Utf8,
                "team": pl.Utf8,
                "cell": pl.Utf8,
                "g": pl.Float64,
                "x": pl.Float64,
                "d": pl.Float64,
            }
        )
    return (
        s.filter(pl.col("offense_snaps") > 0)
        .join(ctx.games.select("team", "game_id", "g"), on=["team", "game_id"], how="inner")
        .select(
            pl.col("gsis_id").alias("entity_id"),
            "team",
            pl.lit("all").alias("cell"),
            "g",
            pl.col("offense_snaps").cast(pl.Float64).alias("x"),
            pl.col("team_offense_snaps").cast(pl.Float64).alias("d"),
        )
    )


def ply_01(ctx: MetricContext) -> pl.DataFrame:
    """PLY-01: snap share: player offense snaps / team offense snaps (A12: a team-game's
    snaps = max over its players of snaps / pct), over the games he played; n = games."""
    return _rate(
        ctx,
        "PLY-01",
        "snap_share",
        _snap_units(ctx),
        ["all"],
        stints(ctx),
        "usage",
        _P.ply_01_min_games.value,
    )


def ply_02(ctx: MetricContext) -> pl.DataFrame:
    """PLY-02: route participation needs routes (DATA-11). v1 proxy: snap share (PLY-01),
    flagged as a proxy."""
    out = ply_01(ctx).with_columns(pl.lit("PLY-02").alias("spec_id"), pl.lit(True).alias("proxy"))
    return out.with_columns(pl.lit("v1 proxy: snap share (PLY-01)").alias("note"))


def ply_02_full(ctx: MetricContext) -> pl.DataFrame:
    """PLY-02 full: share of team dropbacks where he ran a route. PAID: needs routes (DATA-11)."""
    raise NotImplementedError(PAID)


def ply_03(ctx: MetricContext) -> pl.DataFrame:
    """PLY-03: target share: targets / team targets, targets = pass plays with his
    receiver_player_id. Min 3 games."""
    u = share_units(ctx, pf.usage_target(), pl.lit("all"), pl.col("receiver_player_id"))
    out = _rate(ctx, "PLY-03", "target_share", u, ["all"], stints(ctx), "usage")
    return _min_games(ctx, out, _P.ply_03_min_games.value)


def ply_04(ctx: MetricContext) -> pl.DataFrame:
    """PLY-04: air-yards share = his air_yards / team air_yards; WOPR = 1.5 x target share +
    0.7 x air share (from the raw and the weighted shares). Min 3 games."""
    who = pl.col("receiver_player_id")
    air = pl.col("air_yards")
    ua = share_units(ctx, pf.usage_target(), pl.lit("all"), who, x=air, d=air)
    ut = share_units(ctx, pf.usage_target(), pl.lit("all"), who)
    a = _rate(ctx, "PLY-04", "air_share", ua, ["all"], stints(ctx), "usage")
    t = _rate(ctx, "PLY-04", "target_share", ut, ["all"], stints(ctx), "usage")
    wt, wa = _P.ply_04_wopr_target_weight.value, _P.ply_04_wopr_air_weight.value
    key = ["entity_id", "team", "cell"]
    w = t.join(a.select(*key, pl.col("value").alias("_av"), pl.col("value_w").alias("_aw")), on=key)
    wopr = w.with_columns(
        pl.lit("wopr").alias("stat"),
        (wt * pl.col("value") + wa * pl.col("_av")).alias("value"),
        (wt * pl.col("value_w") + wa * pl.col("_aw")).alias("value_w"),
    )
    out = pl.concat([a, finish(wopr)])
    return _min_games(ctx, out, _P.ply_04_min_games.value)


def ply_05(ctx: MetricContext) -> pl.DataFrame:
    """PLY-05: carry share: designed carries / team designed carries. Min 3 games."""
    u = share_units(ctx, pf.usage_carry(), pl.lit("all"), pl.col("rusher_player_id"))
    out = _rate(ctx, "PLY-05", "carry_share", u, ["all"], stints(ctx), "usage")
    return _min_games(ctx, out, _P.ply_05_min_games.value)


def _opportunity() -> pl.Expr:
    return pf.usage_target() | pf.usage_carry()


def _owner() -> pl.Expr:
    return (
        pl.when(pf.usage_target())
        .then(pl.col("receiver_player_id"))
        .otherwise(pl.col("rusher_player_id"))
    )


def ply_06(ctx: MetricContext) -> pl.DataFrame:
    """PLY-06: red-zone and goal-line share: his share of team carries + targets inside the
    20, 10 and 5 (yardline_100 <= zone, A13). Carries are designed carries. Min 8 team
    opportunities in the zone."""
    zones = (
        _P.ply_06_zone_20_yardline_100.value,
        _P.ply_06_zone_10_yardline_100.value,
        _P.ply_06_zone_5_yardline_100.value,
    )
    u = pl.concat(
        [
            share_units(
                ctx,
                _opportunity() & (pl.col("yardline_100") <= z),
                pl.lit(f"inside_{int(z)}"),
                _owner(),
            )
            for z in zones
        ]
    )
    cells = [f"inside_{int(z)}" for z in zones]
    return _rate(
        ctx,
        "PLY-06",
        "opportunity_share",
        u,
        cells,
        stints(ctx),
        "usage",
        _P.ply_06_min_team_opportunities.value,
    )


def ply_07(ctx: MetricContext) -> pl.DataFrame:
    """PLY-07: his share of team targets + carries on 3rd down, and in the last 2:00 of each
    half (half_seconds_remaining <= 120). Min 15 team opportunities."""
    two = _P.ply_07_two_minute_seconds.value
    u = pl.concat(
        [
            share_units(
                ctx, _opportunity() & (pl.col("down") == 3), pl.lit("third_down"), _owner()
            ),
            share_units(
                ctx,
                _opportunity() & (pl.col("half_seconds_remaining") <= two),
                pl.lit("two_minute"),
                _owner(),
            ),
        ]
    )
    return _rate(
        ctx,
        "PLY-07",
        "opportunity_share",
        u,
        ["third_down", "two_minute"],
        stints(ctx),
        "usage",
        _P.ply_07_min_team_opportunities.value,
    )


def ply_08(ctx: MetricContext) -> pl.DataFrame:
    """PLY-08: yards per route run needs routes (DATA-11). v1 proxy: receiving yards / team
    dropbacks in games he played (an efficiency stat: G7 applies). Min 3 games."""
    yards = pl.when(pl.col("complete_pass") == 1).then(pl.col("yards_gained")).otherwise(0.0)
    u = share_units(ctx, pf.dropback(), pl.lit("all"), pl.col("receiver_player_id"), x=yards)
    out = _rate(ctx, "PLY-08", "yards_per_team_dropback", u, ["all"], stints(ctx), "efficiency")
    return _min_games(ctx, out, _P.ply_08_min_games.value).with_columns(
        pl.lit(True).alias("proxy"),
        pl.concat_str(
            [pl.lit("v1 proxy: receiving yards / team dropbacks; "), pl.col("note")]
        ).alias("note"),
    )


def ply_08_full(ctx: MetricContext) -> pl.DataFrame:
    """PLY-08 full: yards per route run. PAID: needs routes (DATA-11)."""
    raise NotImplementedError(PAID)


# ---- PLY-09 to PLY-12: efficiency ----


def ply_09(ctx: MetricContext) -> pl.DataFrame:
    """PLY-09: yards after catch over expected: mean(yards_after_catch - xyac_mean_yardage) per
    reception. Min 30 receptions."""
    m = (
        pf.target()
        & (pl.col("complete_pass") == 1)
        & pl.col("xyac_mean_yardage").is_not_null()
        & pl.col("yards_after_catch").is_not_null()
    )
    u = own_units(
        ctx,
        m,
        pl.col("receiver_player_id"),
        pl.lit("all"),
        pl.col("yards_after_catch") - pl.col("xyac_mean_yardage"),
    )
    return _rate(
        ctx,
        "PLY-09",
        "yacoe",
        u,
        ["all"],
        _entities(u),
        "efficiency",
        _P.ply_09_min_receptions.value,
    )


def ply_10(ctx: MetricContext) -> pl.DataFrame:
    """PLY-10: catch rate over expected: mean(complete_pass - cp) per target (targets with no
    cp are left out). Context, not a driver: it also reflects QB accuracy. Min 40 targets."""
    u = own_units(
        ctx,
        pf.target() & pl.col("cp").is_not_null(),
        pl.col("receiver_player_id"),
        pl.lit("all"),
        pl.col("complete_pass") - pl.col("cp"),
    )
    return _rate(
        ctx, "PLY-10", "croe", u, ["all"], _entities(u), "efficiency", _P.ply_10_min_targets.value
    )


def ply_11(ctx: MetricContext) -> pl.DataFrame:
    """PLY-11: rushing yards over expected per carry: NGS weekly value, carry-weighted
    (each week counts its rush attempts). Min 50 carries."""
    ngs = ctx.table("nextgen_rushing")
    if ngs.is_empty():
        u = pl.DataFrame(
            schema={
                "entity_id": pl.Utf8,
                "team": pl.Utf8,
                "cell": pl.Utf8,
                "g": pl.Float64,
                "x": pl.Float64,
                "d": pl.Float64,
                "c": pl.Float64,
            }
        )
    else:
        wk = ctx.games.select("team", "week", "g")
        u = (
            ngs.filter(
                (pl.col("rush_attempts") > 0)
                & pl.col("rush_yards_over_expected_per_att").is_not_null()
            )
            .join(wk, left_on=["team_abbr", "week"], right_on=["team", "week"], how="inner")
            .select(
                pl.col("player_gsis_id").alias("entity_id"),
                pl.col("team_abbr").alias("team"),
                pl.lit("all").alias("cell"),
                "g",
                (pl.col("rush_attempts") * pl.col("rush_yards_over_expected_per_att"))
                .cast(pl.Float64)
                .alias("x"),
                pl.col("rush_attempts").cast(pl.Float64).alias("d"),
                pl.col("rush_attempts").cast(pl.Float64).alias("c"),
            )
        )
    return _rate(
        ctx,
        "PLY-11",
        "ryoe_per_carry",
        u,
        ["all"],
        _entities(u),
        "efficiency",
        _P.ply_11_min_carries.value,
    )


def ply_12(ctx: MetricContext) -> pl.DataFrame:
    """PLY-12: alignment (slot / wide / inline / backfield). PAID: needs alignment
    (DATA-11); v1 uses roster position only (MetricContext.positions)."""
    raise NotImplementedError(PAID)


# ---- PLY-13: trend and role change ----


def ply_13(ctx: MetricContext) -> pl.DataFrame:
    """PLY-13: L3 and L5 values of PLY-01/03/05/06 vs season. L3/L5 = the team's last 3 / 5
    games, counting the ones he played; flag a role change when |L3 - season| > 2 x sqrt(
    p(1 - p) / n), p = season share, n = team opportunities in the L3 games he played (team
    snaps for PLY-01). A test, not shrunk. Min 3 games."""
    s_win = _P.ply_13_short_window_games.value
    l_win = _P.ply_13_long_window_games.value
    sig = _P.ply_13_role_change_sigmas.value
    zones = (
        _P.ply_06_zone_20_yardline_100.value,
        _P.ply_06_zone_10_yardline_100.value,
        _P.ply_06_zone_5_yardline_100.value,
    )
    sources = {
        "PLY-01": _snap_units(ctx),
        "PLY-03": share_units(ctx, pf.usage_target(), pl.lit("all"), pl.col("receiver_player_id")),
        "PLY-05": share_units(ctx, pf.usage_carry(), pl.lit("all"), pl.col("rusher_player_id")),
        "PLY-06": pl.concat(
            [
                share_units(
                    ctx,
                    _opportunity() & (pl.col("yardline_100") <= z),
                    pl.lit(f"inside_{int(z)}"),
                    _owner(),
                )
                for z in zones
            ]
        ),
    }
    key = ["entity_id", "team", "cell"]
    gp = _games_played(ctx)
    parts = []
    for sid, u in sources.items():
        u = u.sort(*key, "g", "x", "d")
        season = u.group_by(key).agg(
            (pl.col("x").sum() / pl.col("d").sum()).alias("p"), pl.col("d").sum().alias("_sd")
        )
        season = season.filter(pl.col("_sd") != 0)

        def window(w: float, u: pl.DataFrame = u) -> pl.DataFrame:
            return (
                u.filter(pl.col("g") < w)
                .group_by(key)
                .agg(pl.col("x").sum().alias("_x"), pl.col("d").sum().alias("_d"))
            )

        l3, l5 = window(s_win), window(l_win)
        df = (
            season.join(l3, on=key, how="left")
            .join(l5.rename({"_x": "_x5", "_d": "_d5"}), on=key, how="left")
            .with_columns(pl.col(c).fill_null(0.0) for c in ("_x", "_d", "_x5", "_d5"))
        )
        df = df.with_columns(
            pl.when(pl.col("_d") > 0).then(pl.col("_x") / pl.col("_d")).alias("L3"),
            pl.when(pl.col("_d5") > 0).then(pl.col("_x5") / pl.col("_d5")).alias("L5"),
        ).with_columns(
            pl.when(pl.col("_d") > 0)
            .then(
                (
                    (pl.col("L3") - pl.col("p")).abs()
                    > sig * (pl.col("p") * (1 - pl.col("p")) / pl.col("_d")).sqrt()
                ).cast(pl.Float64)
            )
            .alias("role_change"),
            pl.concat_str([pl.lit(f"{sid}:"), pl.col("cell")]).alias("cell"),
        )
        for stat, n in (("L3", "_d"), ("L5", "_d5"), ("role_change", "_d")):
            parts.append(
                df.select(
                    "entity_id",
                    "team",
                    "cell",
                    pl.lit(stat).alias("stat"),
                    pl.col(stat).alias("value"),
                    pl.col(n).round(0).cast(pl.Int64).alias("n"),
                    pl.col("p").alias("value_w"),
                )
            )
    out = (
        pl.concat(parts)
        .join(gp, on=["entity_id", "team"], how="left")
        .with_columns(
            pl.lit("PLY-13").alias("spec_id"),
            pl.lit("player").alias("entity_type"),
            pl.lit(float(_P.ply_13_min_games.value)).alias("min_n"),
            (pl.col("_games").fill_null(0) < _P.ply_13_min_games.value).alias("below_min_sample"),
            pl.lit(
                f"value_w = season share; flagged usage half-life "
                f"{_P.ply_13_flagged_half_life_games.value} games"
            ).alias("note"),
        )
    )
    return finish(out).sort("entity_id", "team", "cell", "stat")


# ---- PLY-14: injury and practice status ----


def ply_14(ctx: MetricContext) -> pl.DataFrame:
    """PLY-14: injury and practice status. Per team, `final_report_in` = its target-week rows
    include an Out, Doubtful or Questionable (ruling 2026-10-04). Per listed player,
    `game_status`: his designation; with none, "expected to play" once the team's final
    report is in, else "status unknown" (no recommendation on his props until a status or a
    ManualNews entry arrives); `status_unknown` 1/0. `return_factor` (initial 0.85) for a
    player's first game back after missing 2+ games: the team's visible games since his last
    game with a snap, his latest team only, not when listed Out or Doubtful."""
    inj = ctx.injuries_now()
    rows: list[dict[str, object]] = []
    final: dict[str, bool] = defaultdict(bool)
    for r in inj.select("team", "report_status").iter_rows(named=True):
        final[r["team"]] |= r["report_status"] in DESIGNATIONS
    for team, is_in in sorted(final.items()):
        n = inj.filter(pl.col("team") == team).height
        rows.append(
            {
                "entity_type": "team",
                "entity_id": team,
                "team": team,
                "cell": "report",
                "stat": "final_report_in",
                "value": 1.0 if is_in else 0.0,
                "n": n,
            }
        )
    out_or_doubtful = set()
    for r in (
        inj.select("team", "gsis_id", "report_status", "practice_status")
        .unique(["team", "gsis_id"], keep="first", maintain_order=True)
        .sort("team", "gsis_id")
        .iter_rows(named=True)
    ):
        st = r["report_status"]
        if st in DESIGNATIONS:
            note = st
        else:
            note = "expected to play" if final[r["team"]] else "status unknown"
        if st in ("Out", "Doubtful"):
            out_or_doubtful.add((r["gsis_id"], r["team"]))
        practice = (r["practice_status"] or "").strip()
        full_note = f"{note}; practice: {practice}" if practice else note
        base = {
            "entity_type": "player",
            "entity_id": r["gsis_id"],
            "team": r["team"],
            "cell": "report",
        }
        rows.append({**base, "stat": "game_status", "note": full_note})
        rows.append(
            {**base, "stat": "status_unknown", "value": 1.0 if note == "status unknown" else 0.0}
        )
    rows += _returns(ctx, out_or_doubtful)
    df = pl.DataFrame(rows, infer_schema_length=None).with_columns(
        pl.lit("PLY-14").alias("spec_id")
    )
    return finish(df).sort("entity_type", "team", "entity_id", "stat")


def _returns(ctx: MetricContext, out_or_doubtful: set[tuple[str, str]]) -> list[dict[str, object]]:
    s = ctx.snaps
    if s.is_empty():
        return []
    played = s.filter(
        (
            pl.col("offense_snaps").fill_null(0)
            + pl.col("defense_snaps").fill_null(0)
            + pl.col("st_snaps").fill_null(0)
        )
        > 0
    ).join(ctx.games.select("team", "game_id", "g"), on=["team", "game_id"], how="inner")
    latest = (
        played.sort("gsis_id", "week", "team")
        .group_by("gsis_id", maintain_order=True)
        .last()
        .select("gsis_id", "team")
    )
    since = (
        played.join(latest, on=["gsis_id", "team"])
        .group_by("gsis_id", "team")
        .agg(pl.col("g").min().cast(pl.Int64).alias("missed"))
    )
    need = _P.ply_14_return_min_missed_games.value
    factor = _P.ply_14_return_factor.value
    out = []
    for pid, team, missed in since.sort("gsis_id").iter_rows():
        if missed >= need and (pid, team) not in out_or_doubtful:
            out.append(
                {
                    "entity_type": "player",
                    "entity_id": pid,
                    "team": team,
                    "cell": "report",
                    "stat": "return_factor",
                    "value": factor,
                    "n": missed,
                    "note": f"first game back after missing {missed} team games; "
                    "projected snap share x return factor (applied in PRJ-02)",
                }
            )
    return out


def ply_14_availability(ctx: MetricContext) -> pl.DataFrame:
    """PLY-14: availability from practice participation for "status unknown" players uses base
    rates fit in BT-02, which Phase 3e estimates. Until then this raises."""
    raise NotImplementedError(
        "PLY-14: practice-participation base rates come from Phase 3e (BT-02)"
    )


# ---- PLY-15: opportunity redistribution ----


def _share_values(ctx: MetricContext, mask: pl.Expr, whose: pl.Expr) -> pl.DataFrame:
    u = share_units(ctx, mask, pl.lit("all"), whose)
    return u.group_by("entity_id", "team").agg((pl.col("x").sum() / pl.col("d").sum()).alias("s"))


_PLY15 = {
    "target_share": (pf.usage_target, "receiver_player_id"),
    "carry_share": (pf.usage_carry, "rusher_player_id"),
}


def _ply_15_parts(ctx: MetricContext) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Raw rows and per-row default-rule priors for PLY-15 (ruling 2026-10-04: trigger = a
    player listed Out; redistributes target and carry shares)."""
    inj = ctx.injuries_now()
    outs = sorted(
        set(inj.filter(pl.col("report_status") == "Out").select("gsis_id", "team").iter_rows())
    )
    pos = ctx.positions
    same_w = _P.ply_15_same_position_weight.value
    k_min = _P.ply_15_min_games_without.value
    low = _P.ply_15_low_confidence_max_career_snaps.value
    h = cv.half_life("usage")
    career = _career_snaps(ctx)
    played = defaultdict(set)
    for pid, team, gid in ctx.played.iter_rows():
        played[(pid, team)].add(gid)
    gtab = ctx.games.filter(pl.col("team").is_in([t for _, t in outs]))
    rows, priors = [], []
    for stat, (mask_fn, who_col) in _PLY15.items():
        shares = {
            (p, t): s
            for p, t, s in _share_values(ctx, mask_fn(), pl.col(who_col)).iter_rows()
            if s is not None
        }
        opp = ctx.plays.filter(mask_fn() & pl.col("posteam").is_not_null()).select(
            "posteam", "game_id", pl.col(who_col).alias("_who")
        )
        for x, team in outs:
            s_x = shares.get((x, team), 0.0)
            if not s_x:
                continue
            tg = gtab.filter(pl.col("team") == team)
            g_of = dict(tg.select("game_id", "g").iter_rows())
            now = min(g_of, key=lambda g: g_of[g])
            same = [
                g
                for g in g_of
                if g not in played[(x, team)]
                and ctx.qb_by_game.get((team, g)) == ctx.qb_by_game.get((team, now))
                and _same_caller(ctx, team, g, now)
            ]
            rest = {p: s for (p, t), s in shares.items() if t == team and p != x and s > 0}
            wts = {p: s * (same_w if pos.get(p) == pos.get(x) else 1.0) for p, s in rest.items()}
            tw = sum(wts.values())
            cell = f"without:{x}"
            for p in sorted(rest):
                default = rest[p] + s_x * wts[p] / tw
                mine = [g for g in sorted(same) if g in played[(p, team)]]
                sub = opp.filter((pl.col("posteam") == team) & pl.col("game_id").is_in(mine))
                per = sub.group_by("game_id").agg(
                    pl.len().alias("d"), (pl.col("_who") == p).sum().alias("x")
                )
                per = per.sort("game_id")
                ws = [0.5 ** (g_of[g] / h) for g in per["game_id"].to_list()]
                xs, ds = per["x"].cast(pl.Float64).to_list(), per["d"].cast(pl.Float64).to_list()
                value = sum(xs) / sum(ds) if ds else None
                value_w = (
                    (
                        math.fsum(w * a for w, a in zip(ws, xs, strict=True))
                        / math.fsum(w * b for w, b in zip(ws, ds, strict=True))
                    )
                    if ds
                    else None
                )
                n_eff = cv.n_eff(pl.Series(ws, dtype=pl.Float64).to_numpy()) if ws else 0.0
                notes = [
                    f"{len(same)} team games without {x} under the same QB and play-caller",
                    f"default rule share {default:.4f}",
                ]
                if career.get(p, 0.0) < low and default > rest[p]:
                    notes.append(
                        f"low confidence: {career.get(p, 0.0):.0f} career snaps "
                        "(counted within the snapshot window)"
                    )
                rows.append(
                    {
                        "entity_type": "player",
                        "entity_id": p,
                        "team": team,
                        "cell": cell,
                        "stat": stat,
                        "value": value,
                        "value_w": value_w,
                        "n": len(ds),
                        "n_eff": n_eff,
                        "min_n": k_min,
                        "below_min_sample": len(same) < k_min,
                        "note": "; ".join(notes),
                    }
                )
                priors.append(
                    {"entity_id": p, "team": team, "cell": cell, "stat": stat, "prior": default}
                )
    if not rows:
        empty = finish(pl.DataFrame(schema={"spec_id": pl.Utf8}))
        return empty, pl.DataFrame(
            schema={
                "entity_id": pl.Utf8,
                "team": pl.Utf8,
                "cell": pl.Utf8,
                "stat": pl.Utf8,
                "prior": pl.Float64,
            }
        )
    df = pl.DataFrame(rows, infer_schema_length=None).with_columns(
        pl.lit("PLY-15").alias("spec_id")
    )
    return finish(df).sort("team", "cell", "stat", "entity_id"), pl.DataFrame(priors)


def _same_caller(ctx: MetricContext, team: str, game: str, now: str) -> bool:
    """PLY-15: same play-caller in `game` as in the team's latest game: COA-01 when it has a
    caller for both dates, else the G4 head-coach stand-in (ruling 2026-10-04)."""
    sched = ctx.table("schedules")
    day = dict(sched.select("game_id", "gameday").iter_rows())
    import datetime as dt

    a = ctx.registry.caller(team, "offense", dt.date.fromisoformat(day[game]))
    b = ctx.registry.caller(team, "offense", dt.date.fromisoformat(day[now]))
    if a is not None and b is not None:
        return a == b
    return ctx.coach_by_game.get((team, game)) == ctx.coach_by_game.get((team, now))


def _career_snaps(ctx: MetricContext) -> dict[str, float]:
    """PLY-15's 'career snaps', counted within the snapshot window (this season and the one
    before; plan A15) and labelled so."""
    s = ctx.snap.collect("snap_counts")
    if s.is_empty():
        return {}
    df = (
        s.with_columns(ctx.gsis(pl.col("pfr_player_id")).alias("_g"))
        .group_by("_g")
        .agg(pl.col("offense_snaps").fill_null(0).sum())
    )
    return {g: float(n) for g, n in df.iter_rows()}


def ply_15(ctx: MetricContext) -> pl.DataFrame:
    """PLY-15: opportunity redistribution when a teammate X is listed Out. With >= 2 team
    games this season without X under the same QB (most dropbacks in the game) and
    play-caller, the observed shares in those games (games each player played), shrunk
    (k = 2 games) toward the default rule; otherwise the default rule. Default: X's vacated
    share goes to the remaining players in proportion to their current shares, players at
    X's position weighted 2x. A vacated role going to someone with under 50 career snaps is
    marked low confidence."""
    return _ply_15_parts(ctx)[0]


def ply_15_prior(ctx: MetricContext, stat: str) -> pl.DataFrame:
    """PLY-15's default-rule share for each row: the prior its observed share shrinks to."""
    p = _ply_15_parts(ctx)[1]
    return p.filter(pl.col("stat") == stat).select("entity_id", "team", "cell", "prior")


# ---- PLY-16, PLY-17 ----


def ply_16(ctx: MetricContext) -> pl.DataFrame:
    """PLY-16: running back directional profile in OFF-12's lanes: share of his designed
    carries in each cell (usage, garbage time kept), and success rate and EPA per carry in
    each cell (efficiency, G7). Min 15 carries per cell."""
    who = pl.col("rusher_player_id")
    car = ctx.plays.filter(pf.usage_carry() & who.is_not_null() & pl.col("posteam").is_not_null())
    cells = pl.DataFrame({"cell": list(pf.RUN_CELLS)})
    su = (
        car.with_columns(pf.run_cell().alias("_c"))
        .join(cells, how="cross")
        .select(
            who.alias("entity_id"),
            pl.col("posteam").alias("team"),
            "cell",
            pl.col("g_off").cast(pl.Float64).alias("g"),
            (pl.col("_c") == pl.col("cell")).cast(pl.Float64).alias("x"),
        )
    )
    backs = _entities(su)
    mn = _P.ply_16_min_carries_per_cell.value
    parts = [_rate(ctx, "PLY-16", "share", su, pf.RUN_CELLS, backs, "usage")]
    for stat in ("success", "epa"):
        u = own_units(ctx, pf.designed_run(), who, pf.run_cell(), pl.col(stat))
        parts.append(_rate(ctx, "PLY-16", stat, u, pf.RUN_CELLS, backs, "efficiency", mn))
    return pl.concat(parts)


def ply_17(ctx: MetricContext) -> pl.DataFrame:
    """PLY-17: quarterback vs the blitz. Blitz gap = EPA per dropback with n_blitzers >= 1
    minus with n_blitzers = 0; same for sack rate. n = blitzed dropbacks (n_eff of that arm);
    league row = the league-average gap. The QB is the passer, or the rusher on a scramble.
    Without FTN (before 2022) the metric is missing (ruling 2026-10-04). Min 60 blitzed
    dropbacks."""
    has = "n_blitzers" in ctx.plays.columns
    h = cv.half_life("efficiency")
    db = (
        ctx.plays.filter(pf.dropback() & pl.col("posteam").is_not_null())
        .with_columns(pf.dropback_qb().alias("_qb"))
        .filter(pl.col("_qb").is_not_null())
    )
    qbs = (
        db.select(pl.col("_qb").alias("entity_id"), pl.col("posteam").alias("team"))
        .unique()
        .sort("entity_id", "team")
    )
    mn = _P.ply_17_min_blitzed_dropbacks.value
    if not has:
        rows = [
            qbs.with_columns(
                pl.lit(s).alias("stat"),
                pl.lit(0).alias("n"),
                pl.lit("all").alias("cell"),
                pl.lit("player").alias("entity_type"),
                pl.lit(mn).alias("min_n"),
                pl.lit(True).alias("below_min_sample"),
                pl.lit(NO_FTN).alias("note"),
            )
            for s in ("epa_gap", "sack_gap")
        ]
        lg = [
            pl.DataFrame(
                {
                    "entity_type": ["league"],
                    "entity_id": ["league"],
                    "cell": ["all"],
                    "stat": [s],
                    "n": [0],
                    "note": [NO_FTN],
                }
            )
            for s in ("epa_gap", "sack_gap")
        ]
        return finish(
            pl.concat([*rows, *lg], how="diagonal_relaxed").with_columns(
                pl.lit("PLY-17").alias("spec_id")
            )
        )
    lo, hi = _P.ply_17_no_blitz_blitzers.value, _P.ply_17_blitz_min_blitzers.value
    arms = (
        db.filter(pl.col("n_blitzers").is_not_null())
        .with_columns(
            pl.when(pl.col("n_blitzers") >= hi)
            .then(True)
            .when(pl.col("n_blitzers") == lo)
            .then(False)
            .alias("_b"),
            (pl.lit(0.5) ** (pl.col("g_off") / h)).alias("_w"),
        )
        .filter(pl.col("_b").is_not_null())
        .sort("game_id", "play_id")
    )
    rows = []
    for stat, col in (("epa_gap", "epa"), ("sack_gap", "sack")):
        g = arms.group_by(
            pl.col("_qb").alias("entity_id"), pl.col("posteam").alias("team"), "_b"
        ).agg(
            pl.len().alias("n"),
            pl.col(col).mean().alias("m"),
            ((pl.col("_w") * pl.col(col)).sum() / pl.col("_w").sum()).alias("mw"),
            (pl.col("_w").sum() ** 2 / (pl.col("_w") ** 2).sum()).alias("ne"),
        )
        on = g.filter(pl.col("_b")).drop("_b")
        off = (
            g.filter(~pl.col("_b"))
            .drop("_b")
            .rename({"n": "n0", "m": "m0", "mw": "mw0", "ne": "ne0"})
        )
        j = qbs.join(on, on=["entity_id", "team"], how="left").join(
            off, on=["entity_id", "team"], how="left"
        )
        rows.append(
            j.select(
                "entity_id",
                "team",
                pl.lit("all").alias("cell"),
                pl.lit(stat).alias("stat"),
                pl.lit("player").alias("entity_type"),
                (pl.col("m") - pl.col("m0")).alias("value"),
                (pl.col("mw") - pl.col("mw0")).alias("value_w"),
                pl.col("n").fill_null(0).cast(pl.Int64).alias("n"),
                pl.col("ne").fill_null(0.0).alias("n_eff"),
                pl.lit(float(mn)).alias("min_n"),
                (pl.col("n").fill_null(0) < mn).alias("below_min_sample"),
            )
        )
        # League gap with math.fsum: exact, so independent of row order and memory layout
        # (rule 6); a polars mean over ~9,000 rows wasn't.
        on_x = arms.filter(pl.col("_b"))[col].cast(pl.Float64).to_list()
        off_x = arms.filter(~pl.col("_b"))[col].cast(pl.Float64).to_list()
        gap = (
            (math.fsum(on_x) / len(on_x) - math.fsum(off_x) / len(off_x))
            if on_x and off_x
            else None
        )
        rows.append(
            pl.DataFrame(
                {
                    "entity_type": ["league"],
                    "entity_id": ["league"],
                    "cell": ["all"],
                    "stat": [stat],
                    "value": [gap],
                    "value_w": [gap],
                    "n": [len(on_x)],
                }
            )
        )
    df = pl.concat([finish(r.with_columns(pl.lit("PLY-17").alias("spec_id"))) for r in rows])
    return df.sort("entity_type", "entity_id", "team", "stat")


# ---- cross-check counts (BUILD_PLAN Phase 3) ----


def weekly_counts(pbp: pl.DataFrame) -> pl.DataFrame:
    """Per player-game raw counts for the cross-check against nflverse player stats: targets,
    carries and receiving yards from every play (no G7 filter: nflverse counts every play),
    excluding no-play penalties and two-point tries."""
    base = pbp.filter(
        (pl.col("play_type") != "no_play").fill_null(True)
        & ~(pl.col("two_point_attempt") == 1).fill_null(False)
    )
    tg = (
        base.filter(pl.col("receiver_player_id").is_not_null() & (pl.col("pass") == 1))
        .group_by("game_id", pl.col("receiver_player_id").alias("player_id"))
        .agg(
            pl.len().alias("targets"),
            pl.col("receiving_yards").fill_null(0).sum().alias("receiving_yards"),
        )
    )
    car = (
        base.filter(pl.col("rusher_player_id").is_not_null() & (pl.col("rush_attempt") == 1))
        .group_by("game_id", pl.col("rusher_player_id").alias("player_id"))
        .agg(pl.len().alias("carries"))
    )
    return tg.join(car, on=["game_id", "player_id"], how="full", coalesce=True).with_columns(
        pl.col("targets").fill_null(0),
        pl.col("carries").fill_null(0),
        pl.col("receiving_yards").fill_null(0),
    )
