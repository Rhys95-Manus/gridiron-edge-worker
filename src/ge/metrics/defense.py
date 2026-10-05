"""Team defense profile (spec section 3): DEF-01 to DEF-08. Same filters, weights and
shrinkage as offense, on plays where the team is defteam. Directions stay in the offense's
frame ("runs to the offense's left"), so a defense's cell lines up with the opponent's.

Data: nflverse; charting: FTN Data via nflverse."""

from __future__ import annotations

from collections import defaultdict

import polars as pl

from ge.config import load_params
from ge.metrics import conventions as cv
from ge.metrics import plays as pf
from ge.metrics.context import MetricContext
from ge.metrics.engine import finish, summarise
from ge.metrics.offense import (
    SPLITS,
    hit_flag,
    run_grid,
    split_units,
    status_note,
    team_rate,
    team_units,
    zone_trips,
)

_D = load_params().defense
POSITIONS = ("RB", "TE", "WR")
MISSING_STATUSES = ("Out", "Doubtful")
PAID = "PAID: DATA-11"


def def_01(ctx: MetricContext) -> pl.DataFrame:
    """DEF-01: EPA per play allowed, overall / pass / run. Min 150 plays."""
    u = split_units(ctx, pl.col("epa"), "defense")
    return team_rate(ctx, "DEF-01", "epa", u, SPLITS, _D.def_01_min_plays.value)


def def_01_adjusted(ctx: MetricContext) -> pl.DataFrame:
    """DEF-01 / G6: opponent-adjusted EPA allowed; raises until BT-02 sets the ridge penalty."""
    cv.g6_penalty()
    raise AssertionError("unreachable")


def def_02(ctx: MetricContext) -> pl.DataFrame:
    """DEF-02: success rate allowed, overall / pass / run. Min 150 plays."""
    u = split_units(ctx, pl.col("success"), "defense")
    return team_rate(ctx, "DEF-02", "success", u, SPLITS, _D.def_02_min_plays.value)


def def_03(ctx: MetricContext) -> pl.DataFrame:
    """DEF-03: directional run defense: OFF-12's grid on designed runs against, cells in the
    offense's frame. Min 25 carries per cell."""
    return run_grid(ctx, "DEF-03", "defense", _D.def_03_min_carries_per_cell.value)


def _positions(ctx: MetricContext) -> dict[str, str]:
    """Each player's position on his latest visible weekly roster row this season (ties on
    week broken by the larger position string, so the choice is deterministic)."""
    rw = ctx.table("rosters_weekly").filter(pl.col("gsis_id").is_not_null())
    best = (
        rw.select("gsis_id", "week", pl.col("position").fill_null(""))
        .sort("gsis_id", "week", "position")
        .group_by("gsis_id", maintain_order=True)
        .last()
    )
    return dict(best.select("gsis_id", "position").iter_rows())


_DEF04_STATS = ("targets", "receptions", "yards", "tds", "epa")


def def_04(ctx: MetricContext) -> pl.DataFrame:
    """DEF-04: defense vs position (RB, TE, WR), opponent-adjusted. For targets, receptions,
    yards and TDs: ratio = sum actual allowed / sum expected, where expected = the opponent's
    per-game total to that position in its other games (plan A9; games vs this defense
    excluded; a game whose opponent has no other game is left out). EPA/target is a difference
    vs expected, not a ratio (user decision 2026-10-02). Min 4 games and 40 targets."""
    pos = _positions(ctx)
    h = cv.half_life("efficiency")
    tg = ctx.plays.filter(pf.target()).with_columns(
        pl.col("receiver_player_id").replace_strict(pos, default=None).alias("_pos"),
        pf.offensive_td().cast(pl.Float64).alias("_td"),
    )
    tg = tg.filter(pl.col("_pos").is_in(list(POSITIONS))).sort("game_id", "play_id")  # rule 6
    sums = tg.group_by("posteam", "game_id", "_pos").agg(
        pl.len().cast(pl.Float64).alias("targets"),
        pl.col("complete_pass").sum().alias("receptions"),
        pl.col("yards_gained").sum().alias("yards"),
        pl.col("_td").sum().alias("tds"),
        pl.col("epa").sum().alias("epa"),
    )
    tot: dict[tuple[str, str, str], dict[str, float]] = {
        (r["posteam"], r["game_id"], r["_pos"]): {s: float(r[s]) for s in _DEF04_STATS}
        for r in sums.iter_rows(named=True)
    }
    opp = {(r["team"], r["game_id"]): r["opponent"] for r in ctx.opponents.iter_rows(named=True)}
    games: dict[str, dict[str, float]] = defaultdict(dict)
    for r in ctx.games.iter_rows(named=True):
        games[r["team"]][r["game_id"]] = r["g"]
    k_min_games, k_min_tg = _D.def_04_min_games.value, _D.def_04_min_targets.value
    zero = dict.fromkeys(_DEF04_STATS, 0.0)
    rows = []
    for d in ctx.teams["team"].to_list():
        for p in POSITIONS:
            act, exp, actw, expw = (dict(zero) for _ in range(4))
            wsum = wsq = 0.0
            n_games = 0
            for gid, g in games.get(d, {}).items():
                o = opp[(d, gid)]
                others = [x for x in games[o] if opp[(o, x)] != d]
                if not others:
                    continue
                n_games += 1
                w = 0.5 ** (g / h)
                a = tot.get((o, gid, p), zero)
                for s in _DEF04_STATS:
                    e = sum(tot.get((o, x, p), zero)[s] for x in others) / len(others)
                    act[s] += a[s]
                    exp[s] += e
                    actw[s] += w * a[s]
                    expw[s] += w * e
                wsum += w * a["targets"]
                wsq += w * w * a["targets"]
            n = int(act["targets"])
            neff = wsum * wsum / wsq if wsq else 0.0
            below = n_games < k_min_games or n < k_min_tg
            base = {
                "entity_type": "team",
                "entity_id": d,
                "team": d,
                "cell": p,
                "n": n,
                "n_eff": neff,
                "min_n": k_min_tg,
                "below_min_sample": below,
                "note": f"games={n_games}",
            }
            for s in ("targets", "receptions", "yards", "tds"):
                rows.append(
                    {
                        **base,
                        "stat": s,
                        "value": act[s] / exp[s] if exp[s] else None,
                        "value_w": actw[s] / expw[s] if expw[s] else None,
                    }
                )
            ok = act["targets"] > 0 and exp["targets"] > 0
            rows.append(
                {
                    **base,
                    "stat": "epa_diff",
                    "value": act["epa"] / act["targets"] - exp["epa"] / exp["targets"]
                    if ok
                    else None,
                    "value_w": (actw["epa"] / actw["targets"] - expw["epa"] / expw["targets"])
                    if ok
                    else None,
                }
            )
    df = pl.DataFrame(rows, infer_schema_length=None).with_columns(
        pl.lit("DEF-04").alias("spec_id")
    )
    return finish(df).sort("entity_id", "cell", "stat")


def def_04b(ctx: MetricContext) -> pl.DataFrame:
    """DEF-04b: slot WR vs wide WR split. PAID: needs receiver alignment per play (DATA-11)."""
    raise NotImplementedError(PAID)


def def_05(ctx: MetricContext) -> pl.DataFrame:
    """DEF-05: pass rush and blitz, on dropbacks against: blitz rate (n_blitzers >= 1), mean
    rushers, mean box count (FTN), sack rate and QB-hit rate forced (sack or hit)."""
    mn = _D.def_05_min_dropbacks.value
    blitz = _D.def_05_blitz_min_blitzers.value
    has_ftn = "n_blitzers" in ctx.plays.columns
    none = pl.lit(None, dtype=pl.Float64)
    stats = {
        "blitz_rate": (pl.col("n_blitzers") >= blitz).cast(pl.Float64) if has_ftn else none,
        "rushers": pl.col("n_pass_rushers") if has_ftn else none,
        "box": pl.col("n_defense_box") if has_ftn else none,
        "sack_rate": pl.col("sack"),
        "hit_rate": hit_flag(),
    }
    out = pl.concat(
        [
            team_rate(
                ctx,
                "DEF-05",
                s,
                team_units(ctx, pf.dropback(), pl.lit("all"), x, "defense"),
                ["all"],
                mn,
            )
            for s, x in stats.items()
        ]
    )
    if not has_ftn:
        out = out.with_columns(
            pl.when(pl.col("stat").is_in(["blitz_rate", "rushers", "box"]))
            .then(pl.lit("no FTN"))
            .otherwise(pl.col("note"))
            .alias("note")
        )
    return out


def def_05b(ctx: MetricContext) -> pl.DataFrame:
    """DEF-05b: man vs zone tendency. PAID: needs coverage charting (DATA-11)."""
    raise NotImplementedError(PAID)


def def_06(ctx: MetricContext) -> pl.DataFrame:
    """DEF-06: explosive plays allowed: runs of 10+ yards and completions of 20+ yards. Plan
    A10: overall share of qualifying plays, plus a run rate (designed runs) and a pass rate
    (dropbacks)."""
    run_x = (pl.col("yards_gained") >= _D.def_06_explosive_run_min_yards.value).cast(pl.Float64)
    pass_x = (
        _flag("complete_pass")
        & (pl.col("yards_gained") >= _D.def_06_explosive_pass_min_yards.value)
    ).cast(pl.Float64)
    any_x = pl.when(pf.designed_run()).then(run_x).otherwise(pass_x)
    mn = _D.def_06_min_plays.value
    parts = [
        ("explosive", pf.qualifying(), any_x),
        ("explosive_run", pf.designed_run(), run_x),
        ("explosive_pass", pf.dropback(), pass_x),
    ]
    return pl.concat(
        [
            team_rate(
                ctx, "DEF-06", s, team_units(ctx, m, pl.lit("all"), x, "defense"), ["all"], mn
            )
            for s, m, x in parts
        ]
    )


def _flag(c: str) -> pl.Expr:
    return (pl.col(c) == 1).fill_null(False)


def def_07(ctx: MetricContext) -> pl.DataFrame:
    """DEF-07: red-zone TD rate allowed: TDs / opponent drives reaching the 20. Min 10 trips."""
    z = _D.def_07_red_zone_yardline_100.value
    return team_rate(
        ctx,
        "DEF-07",
        "td_per_trip",
        zone_trips(ctx, "defense", z),
        [f"inside_{int(z)}"],
        _D.def_07_min_trips.value,
    )


def def_08(ctx: MetricContext) -> pl.DataFrame:
    """DEF-08: missing defenders. A starter = >= 60% of the team's defensive snaps over its
    last 3 games (team snaps per game from snap counts: max of snaps / pct). Every starter gets
    a `starter` row with his status; one listed Out or Doubtful also gets an `on_off` row: EPA
    allowed per qualifying play in games without him minus games with him, n = the smaller
    side (plan A11). The numeric adjustment applies only with >= 200 plays each way."""
    look = int(_D.def_08_starter_lookback_games.value)
    min_share = _D.def_08_starter_min_snap_share.value
    min_each = _D.def_08_min_plays_each_way.value
    h = cv.half_life("efficiency")
    status = status_note(ctx)
    # Rule 6: canonical row orders, so float sums don't depend on the store's row order.
    snaps = (
        ctx.table("snap_counts")
        .select("team", "week", "game_id", "pfr_player_id", "defense_snaps", "defense_pct")
        .sort("team", "week", "pfr_player_id", "defense_snaps", nulls_last=True)
    )
    q = (
        ctx.plays.filter(pf.qualifying())
        .select("defteam", "game_id", "play_id", "g_def", "epa")
        .sort("game_id", "play_id")
    )
    rows = []
    for team in ctx.teams["team"].to_list():
        mine = snaps.filter(pl.col("team") == team)
        weeks = sorted(set(mine["week"].to_list()), reverse=True)[:look]
        recent = mine.filter(pl.col("week").is_in(weeks))
        per_game = (
            recent.filter(pl.col("defense_pct") > 0)
            .group_by("week")
            .agg((pl.col("defense_snaps") / pl.col("defense_pct")).max().alias("t"))
            .sort("week")
        )
        team_snaps = float(per_game["t"].sum()) if per_game.height else 0.0
        if team_snaps == 0:
            continue
        shares = (
            recent.group_by("pfr_player_id", maintain_order=True)
            .agg((pl.col("defense_snaps").fill_null(0).sum() / team_snaps).alias("share"))
            .sort("pfr_player_id")
        )
        plays = q.filter(pl.col("defteam") == team)
        for pfr, share in shares.filter(pl.col("share") >= min_share).iter_rows():
            gid = ctx.crosswalk.get(pfr, f"pfr:{pfr}")
            st = status.get((team, gid), "not on report")
            rows.append(
                {
                    "entity_type": "player",
                    "entity_id": gid,
                    "team": team,
                    "cell": "DEF",
                    "stat": "starter",
                    "value": share,
                    "n": len(weeks),
                    "note": st,
                }
            )
            if st not in MISSING_STATUSES:
                continue
            played = set(
                mine.filter((pl.col("pfr_player_id") == pfr) & (pl.col("defense_snaps") > 0))[
                    "game_id"
                ].to_list()
            )
            w_on = plays.filter(pl.col("game_id").is_in(list(played)))
            w_off = plays.filter(~pl.col("game_id").is_in(list(played)))
            rows.append(_on_off(team, gid, st, w_on, w_off, h, min_each))
    if not rows:
        return finish(pl.DataFrame(schema={"spec_id": pl.Utf8}).clear())
    df = pl.DataFrame(rows, infer_schema_length=None).with_columns(
        pl.lit("DEF-08").alias("spec_id")
    )
    return finish(df).sort("team", "entity_id", "stat")


def _on_off(
    team: str,
    gid: str,
    status: str,
    on: pl.DataFrame,
    off: pl.DataFrame,
    h: float,
    min_each: float,
) -> dict[str, object]:
    def stats(df: pl.DataFrame) -> tuple[int, float | None, float | None, float]:
        if df.is_empty():
            return 0, None, None, 0.0
        w = cv.recency_weights(df["g_def"].to_numpy(), h)
        x = df["epa"].to_numpy()
        return df.height, float(x.mean()), cv.weighted_mean(x, w), cv.n_eff(w)

    n1, m1, w1, e1 = stats(on)
    n0, m0, w0, e0 = stats(off)
    both = m1 is not None and m0 is not None
    n = min(n1, n0)
    return {
        "entity_type": "player",
        "entity_id": gid,
        "team": team,
        "cell": "DEF",
        "stat": "on_off",
        "value": m0 - m1 if both else None,  # type: ignore[operator]
        "value_w": w0 - w1 if both else None,  # type: ignore[operator]
        "n": n,
        "n_eff": min(e1, e0),
        "min_n": min_each,
        "below_min_sample": n < min_each,
        "note": f"{status}; plays with {n1}, without {n0}",
    }


# ---- section 6b: defensive counterparts (DEF-09 to DEF-17) ----


def def_09(ctx: MetricContext) -> pl.DataFrame:
    """DEF-09: pass map allowed: EPA per target and completion over expected allowed in
    OFF-13's 12 location x depth cells (plus `unknown`). Min 20 targets per cell."""
    from ge.metrics.offense import pass_map

    out = pass_map(ctx, "DEF-09", "defense", _D.def_09_min_targets_per_cell.value)
    return out.filter(pl.col("stat").is_in(["epa", "cpoe"]))


def _defense_gap(
    ctx: MetricContext, spec_id: str, flag: pl.Expr | None, min_n: float
) -> pl.DataFrame:
    from ge.metrics.skills import gap_metric

    return gap_metric(
        ctx,
        spec_id,
        "epa_gap",
        pf.dropback() & pl.col("defteam").is_not_null(),
        pl.col("defteam"),
        pl.col("defteam"),
        pl.col("g_def"),
        flag,
        pl.col("epa"),
        "team",
        min_n,
    )


def def_10(ctx: MetricContext) -> pl.DataFrame:
    """DEF-10: play-action defense: EPA per dropback allowed with play action minus without
    (FTN). Prior = the league gap. Min 40 play-action dropbacks. Missing before 2022."""
    pa = pl.col("is_play_action") if "is_play_action" in ctx.plays.columns else None
    return _defense_gap(ctx, "DEF-10", pa, _D.def_10_min_play_action_dropbacks.value)


def def_11(ctx: MetricContext) -> pl.DataFrame:
    """DEF-11: tackling after the catch: mean(yards_after_catch - xyac_mean_yardage) allowed
    per reception. Min 60 receptions."""
    m = (
        pf.target()
        & (pl.col("complete_pass") == 1)
        & pl.col("xyac_mean_yardage").is_not_null()
        & pl.col("yards_after_catch").is_not_null()
    )
    x = pl.col("yards_after_catch") - pl.col("xyac_mean_yardage")
    u = team_units(ctx, m, pl.lit("all"), x, "defense")
    return team_rate(ctx, "DEF-11", "yacoe", u, ["all"], _D.def_11_min_receptions.value)


def def_12(ctx: MetricContext) -> pl.DataFrame:
    """DEF-12: box tendency and box-split run defense (FTN n_defense_box): share of
    qualifying plays against with >= 8 in the box (ruling 2026-10-04: its shrink raises);
    success and yards per carry allowed on designed runs by PLY-24's box bands (A18). Min 20
    carries per band. Missing before 2022."""
    from ge.metrics.skills import BOX_BANDS, _box_band, _no_ftn

    has = "n_defense_box" in ctx.plays.columns
    box = pl.col("n_defense_box") if has else pl.lit(None, dtype=pl.Float64)
    stacked = load_params().player.ply_24_stacked_box_min.value
    share = team_units(
        ctx, pf.qualifying() & box.is_not_null(), pl.lit("all"), (box >= stacked), "defense"
    )
    parts = [team_rate(ctx, "DEF-12", "stacked_box_share", share, ["all"], None)]
    mn = _D.def_12_min_carries_per_band.value
    for stat, x in (("success", pl.col("success")), ("ypc", pl.col("yards_gained"))):
        u = team_units(ctx, pf.designed_run(), _box_band(box), x, "defense").filter(
            pl.col("cell").is_not_null()
        )
        parts.append(team_rate(ctx, "DEF-12", stat, u, BOX_BANDS, mn))
    out = pl.concat(parts)
    return out if has else _no_ftn(out, {"stacked_box_share", "success", "ypc"})


def def_13(ctx: MetricContext) -> pl.DataFrame:
    """DEF-13: blitz results: EPA per dropback allowed when blitzing (n_blitzers >= 1) minus
    when not (= 0), FTN. Prior = the league gap. Min 60 blitzed dropbacks. Missing before
    2022."""
    flag = None
    if "n_blitzers" in ctx.plays.columns:
        p = load_params().player
        n = pl.col("n_blitzers")
        flag = (
            pl.when(n >= p.ply_17_blitz_min_blitzers.value)
            .then(True)
            .when(n == p.ply_17_no_blitz_blitzers.value)
            .then(False)
        )
    return _defense_gap(ctx, "DEF-13", flag, _D.def_13_min_blitzed_dropbacks.value)


def def_14(ctx: MetricContext) -> pl.DataFrame:
    """DEF-14: quarterback runs allowed per opponent dropback: scrambles / dropbacks, and QB
    rushing yards (scrambles plus designed runs by a rusher whose weekly-roster position is
    QB) / dropbacks. Min 150 dropbacks."""
    mn = _D.def_14_min_dropbacks.value
    scr = team_units(ctx, pf.dropback(), pl.lit("all"), pl.col("qb_scramble"), "defense")
    pos = ctx.positions
    scramble = pf.dropback() & (pl.col("qb_scramble") == 1).fill_null(False)
    rusher_pos = pl.col("rusher_player_id").replace_strict(pos, default=None, return_dtype=pl.Utf8)
    qb_run = pf.designed_run() & (rusher_pos == "QB").fill_null(False)
    yards = pl.when(scramble | qb_run).then(pl.col("yards_gained")).otherwise(0.0)
    plays = ctx.plays.filter((pf.dropback() | qb_run) & pl.col("defteam").is_not_null()).select(
        pl.col("defteam").alias("entity_id"),
        pl.col("defteam").alias("team"),
        pl.lit("all").alias("cell"),
        pl.col("g_def").cast(pl.Float64).alias("g"),
        yards.cast(pl.Float64).alias("x"),
        pf.dropback().cast(pl.Float64).alias("d"),
        pf.dropback().cast(pl.Float64).alias("c"),
    )
    return pl.concat(
        [
            team_rate(ctx, "DEF-14", "scramble_rate", scr, ["all"], mn),
            team_rate(ctx, "DEF-14", "qb_rush_yards", plays, ["all"], mn),
        ]
    )


def def_15(ctx: MetricContext) -> pl.DataFrame:
    """DEF-15: formation run defense: success and yards per carry allowed on shotgun vs
    under-center designed runs. Min 25 carries each."""
    cell = pl.when(pl.col("shotgun") == 1).then(pl.lit("shotgun")).otherwise(pl.lit("under_center"))
    cells = ["shotgun", "under_center"]
    mn = _D.def_15_min_carries_each.value
    return pl.concat(
        [
            team_rate(
                ctx, "DEF-15", s, team_units(ctx, pf.designed_run(), cell, x, "defense"), cells, mn
            )
            for s, x in (("success", pl.col("success")), ("ypc", pl.col("yards_gained")))
        ]
    )


def def_16(ctx: MetricContext) -> pl.DataFrame:
    """DEF-16: end-zone pass defense: offensive TDs allowed / end-zone targets faced
    (air_yards >= yardline_100). Min 10 end-zone targets."""
    ez = pf.target() & (pl.col("air_yards") >= pl.col("yardline_100")).fill_null(False)
    u = team_units(ctx, ez, pl.lit("all"), pf.offensive_td().cast(pl.Float64), "defense")
    return team_rate(ctx, "DEF-16", "td_rate", u, ["all"], _D.def_16_min_end_zone_targets.value)


DEF17_CREDITS = {
    "sacks": (
        ("sack_player_id", 1.0),
        ("half_sack_1_player_id", 0.5),
        ("half_sack_2_player_id", 0.5),
    ),
    "qb_hits": (("qb_hit_1_player_id", 1.0), ("qb_hit_2_player_id", 1.0)),
    "passes_defensed": (("pass_defense_1_player_id", 1.0), ("pass_defense_2_player_id", 1.0)),
    "interceptions": (("interception_player_id", 1.0),),
    "tackles_for_loss": (
        ("tackle_for_loss_1_player_id", 1.0),
        ("tackle_for_loss_2_player_id", 1.0),
    ),
}


def _def17_snaps(ctx: MetricContext) -> pl.DataFrame:
    """(gsis_id, team, game_id, g, his defense snaps, team defense snaps) for games he played
    on defense; team snaps per game = max of snaps / pct (A12's rule, on defense)."""
    s = ctx.snaps
    team = (
        s.filter(pl.col("defense_pct") > 0)
        .group_by("team", "game_id")
        .agg((pl.col("defense_snaps") / pl.col("defense_pct")).max().alias("tsnaps"))
    )
    return (
        s.filter(pl.col("defense_snaps") > 0)
        .join(team, on=["team", "game_id"], how="inner")
        .join(ctx.games.select("team", "game_id", "g"), on=["team", "game_id"], how="inner")
        .select(
            "gsis_id", "team", "game_id", "g", pl.col("defense_snaps").cast(pl.Float64), "tsnaps"
        )
    )


def def_17(ctx: MetricContext) -> pl.DataFrame:
    """DEF-17: defender contribution shares: each defender's share of team sacks (half sacks
    0.5 each), QB hits, passes defensed, interceptions and tackles for loss, counting the _1
    and _2 credit columns (A19), on scrimmage plays (garbage time kept: usage) in the games
    he played (ruling 2026-10-04). n = team events in those games; k = 20 events per share;
    prior = his defensive snap share in those games. Min 200 team defensive snaps."""
    snaps = _def17_snaps(ctx)
    p = ctx.plays.filter(pf.scrimmage() & pl.col("defteam").is_not_null())
    games = snaps.select("gsis_id", "team", "game_id", "g")
    ents = games.select(pl.col("gsis_id").alias("entity_id"), "team").unique()
    mn = _D.def_17_min_team_defensive_snaps.value
    tsn = snaps.group_by("gsis_id", "team").agg(pl.col("tsnaps").sum().alias("_ts"))
    parts = []
    for stat, cols in DEF17_CREDITS.items():
        credit = pl.concat(
            [
                p.filter(pl.col(c).is_not_null()).select(
                    pl.col("defteam").alias("team"),
                    "game_id",
                    pl.col(c).alias("gsis_id"),
                    pl.lit(w).alias("_w"),
                )
                for c, w in cols
            ]
        )
        team_tot = credit.group_by("team", "game_id").agg(pl.col("_w").sum().alias("d"))
        his = credit.group_by("team", "game_id", "gsis_id").agg(pl.col("_w").sum().alias("x"))
        u = (
            games.join(team_tot, on=["team", "game_id"], how="left")
            .join(his, on=["team", "game_id", "gsis_id"], how="left")
            .select(
                pl.col("gsis_id").alias("entity_id"),
                "team",
                pl.lit("all").alias("cell"),
                "g",
                pl.col("x").fill_null(0.0),
                pl.col("d").fill_null(0.0),
                pl.col("d").fill_null(0.0).alias("c"),
            )
        )
        out = summarise(
            u,
            spec_id="DEF-17",
            stat=stat,
            entity_type="player",
            entities=ents,
            cells=["all"],
            h=cv.half_life("usage"),
            league=False,
        )
        out = out.join(
            tsn.rename({"gsis_id": "entity_id"}), on=["entity_id", "team"], how="left"
        ).with_columns(
            pl.lit(float(mn)).alias("min_n"),
            (pl.col("_ts").fill_null(0) < mn).alias("below_min_sample"),
            pl.concat_str(
                [
                    pl.lit("team defensive snaps in his games: "),
                    pl.col("_ts").round(0).cast(pl.Int64).cast(pl.Utf8),
                ]
            ).alias("note"),
        )
        parts.append(finish(out))
    return pl.concat(parts)


def def_17_prior(ctx: MetricContext) -> pl.DataFrame:
    """DEF-17's prior per defender: his defensive snap share in the games he played."""
    s = (
        _def17_snaps(ctx)
        .group_by("gsis_id", "team")
        .agg((pl.col("defense_snaps").sum() / pl.col("tsnaps").sum()).alias("prior"))
    )
    return s.select(
        pl.col("gsis_id").alias("entity_id"), "team", pl.lit("all").alias("cell"), "prior"
    )
