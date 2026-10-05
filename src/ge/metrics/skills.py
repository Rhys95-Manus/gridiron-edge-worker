"""Section 6b skill-vs-skill catalog, player side: PLY-18 to PLY-34.

Same conventions as section 4 (3b rulings): one row per (player, team) stint; shares of his
own plays are usage, rates and EPA are efficiency (G7 out). 3c rulings (2026-10-04): stats
whose prior is 'his overall' (6b rule 1: his overall value, itself shrunk toward his role
prior) raise until Phase 3e; 'league QB / RB / at position' priors pool every play by players
at that weekly-roster position; FTN-based stats are missing before 2022.

Data: nflverse; charting: FTN Data via nflverse."""

from __future__ import annotations

from collections import defaultdict

import polars as pl

from ge.config import load_params
from ge.metrics import conventions as cv
from ge.metrics import plays as pf
from ge.metrics.context import MetricContext
from ge.metrics.engine import NO_FTN, finish, position_league_rows, summarise
from ge.metrics.player import _entities, _rate, own_units, share_units, stints

_P = load_params().player
BANDS = (*pf.DEPTH_BANDS, "unknown")
SIDES = (*pf.PASS_LOCATIONS, "unknown")
BOX_BANDS = ("light", "standard", "stacked")
TIMED = ("forty", "cone", "shuttle")  # lower is faster: percentiles inverted (ruling 2026-10-04)
MEASURES = {
    "height": "ht",
    "weight": "wt",
    "forty": "forty",
    "vertical": "vertical",
    "broad_jump": "broad_jump",
    "cone": "cone",
    "shuttle": "shuttle",
}


# ---- shared helpers ----


def attempt() -> pl.Expr:
    """Plan A3: a pass attempt = pass_attempt == 1 and not a sack (qualifying, G7)."""
    return (
        pf.qualifying()
        & (pl.col("pass_attempt") == 1).fill_null(False)
        & ~(pl.col("sack") == 1).fill_null(False)
    )


def band_or_unknown() -> pl.Expr:
    return pf.depth_band().fill_null("unknown")


def location() -> pl.Expr:
    loc = pl.col("pass_location")
    return pl.when(loc.is_in(list(pf.PASS_LOCATIONS))).then(loc).otherwise(pl.lit("unknown"))


def ftn(ctx: MetricContext, field: str) -> pl.Expr | None:
    """An FTN field, or None when the season has no FTN charting (before 2022)."""
    return pl.col(field) if field in ctx.plays.columns else None


def _no_ftn(df: pl.DataFrame, stats: set[str]) -> pl.DataFrame:
    """Ruling 2026-10-04: FTN-based stats are missing without FTN; the note makes the shrink
    step return null rows."""
    return df.with_columns(
        pl.when(pl.col("stat").is_in(list(stats)))
        .then(pl.lit(NO_FTN))
        .otherwise(pl.col("note"))
        .alias("note")
    )


def cell_share(
    ctx: MetricContext, mask: pl.Expr, who: pl.Expr, cell: pl.Expr, cells: tuple[str, ...]
) -> pl.DataFrame:
    """Share of HIS plays in each cell: one unit per his play per cell, x = 1 if in it."""
    base = (
        ctx.plays.filter(mask & pl.col("posteam").is_not_null())
        .select(
            who.cast(pl.Utf8).alias("entity_id"),
            pl.col("posteam").alias("team"),
            cell.cast(pl.Utf8).alias("_c"),
            pl.col("g_off").cast(pl.Float64).alias("g"),
        )
        .filter(pl.col("entity_id").is_not_null())
    )
    return base.join(pl.DataFrame({"cell": list(cells)}), how="cross").select(
        "entity_id",
        "team",
        "cell",
        "g",
        (pl.col("_c") == pl.col("cell")).cast(pl.Float64).alias("x"),
    )


def _with_position_league(
    ctx: MetricContext, frame: pl.DataFrame, units: pl.DataFrame, spec_id: str, stat: str
) -> pl.DataFrame:
    return pl.concat([frame, position_league_rows(ctx, units, spec_id, stat)])


def gap_metric(
    ctx: MetricContext,
    spec_id: str,
    stat: str,
    mask: pl.Expr,
    who: pl.Expr,
    team: pl.Expr,
    g: pl.Expr,
    flag: pl.Expr | None,
    value: pl.Expr,
    entity_type: str,
    min_n: float,
) -> pl.DataFrame:
    """Gap = mean(value | flag) - mean(value | not flag) per entity (PLY-17's form): value_w
    from G3-weighted means, n and n_eff of the flagged arm; a league row with the pooled
    league gap. With no flag column (no FTN) every row is missing."""
    h = cv.half_life("efficiency")
    plays = (
        ctx.plays.filter(mask)
        .select(
            who.cast(pl.Utf8).alias("entity_id"),
            team.alias("team"),
            g.cast(pl.Float64).alias("g"),
            (flag if flag is not None else pl.lit(None, dtype=pl.Boolean)).alias("_b"),
            value.cast(pl.Float64).alias("_v"),
            "game_id",
            "play_id",
        )
        .filter(pl.col("entity_id").is_not_null())
    )
    ents = plays.select("entity_id", "team").unique()
    arms = plays.filter(pl.col("_b").is_not_null())
    rows = []
    for (eid, tm), grp in arms.sort("game_id", "play_id").group_by(
        ["entity_id", "team"], maintain_order=True
    ):
        on = grp.filter(pl.col("_b"))
        off = grp.filter(~pl.col("_b"))
        row: dict[str, object] = {
            "entity_id": eid,
            "team": tm,
            "n": on.height,
            "n_eff": 0.0,
            "value": None,
            "value_w": None,
        }
        if on.height:
            w_on = cv.recency_weights(on["g"].to_numpy(), h)
            row["n_eff"] = cv.n_eff(w_on)
        if on.height and off.height:
            w_off = cv.recency_weights(off["g"].to_numpy(), h)
            row["value"] = _fmean(on["_v"].to_list()) - _fmean(off["_v"].to_list())
            row["value_w"] = _wmean(on["_v"].to_list(), list(w_on)) - _wmean(
                off["_v"].to_list(), list(w_off)
            )
        rows.append(row)
    got = pl.DataFrame(
        rows,
        schema={
            "entity_id": pl.Utf8,
            "team": pl.Utf8,
            "n": pl.Int64,
            "n_eff": pl.Float64,
            "value": pl.Float64,
            "value_w": pl.Float64,
        },
    )
    out = ents.join(got, on=["entity_id", "team"], how="left").with_columns(
        pl.col("n").fill_null(0), pl.col("n_eff").fill_null(0.0)
    )
    on_all = arms.filter(pl.col("_b"))["_v"].to_list()
    off_all = arms.filter(~pl.col("_b"))["_v"].to_list()
    lg = _fmean(on_all) - _fmean(off_all) if on_all and off_all else None
    league = pl.DataFrame(
        {
            "entity_type": ["league"],
            "entity_id": ["league"],
            "value": [lg],
            "value_w": [lg],
            "n": [len(on_all)],
        }
    )
    df = pl.concat(
        [
            out.with_columns(
                pl.lit(entity_type).alias("entity_type"),
                (pl.col("n") < min_n).alias("below_min_sample"),
                pl.lit(float(min_n)).alias("min_n"),
            ),
            league,
        ],
        how="diagonal_relaxed",
    ).with_columns(
        pl.lit(spec_id).alias("spec_id"), pl.lit(stat).alias("stat"), pl.lit("all").alias("cell")
    )
    df = finish(df)
    if flag is None:
        df = df.with_columns(pl.lit(NO_FTN).alias("note"))
    return df.sort("entity_type", "entity_id", "team")


def _fmean(xs: list[float]) -> float:
    import math

    return math.fsum(xs) / len(xs)


def _wmean(xs: list[float], ws: list[float]) -> float:
    import math

    return math.fsum(w * x for w, x in zip(ws, xs, strict=True)) / math.fsum(ws)


def _dropback_qb_gap(
    ctx: MetricContext, spec_id: str, flag: pl.Expr | None, min_n: float
) -> pl.DataFrame:
    return gap_metric(
        ctx,
        spec_id,
        "epa_gap",
        pf.dropback() & pl.col("posteam").is_not_null(),
        pf.dropback_qb(),
        pl.col("posteam"),
        pl.col("g_off"),
        flag,
        pl.col("epa"),
        "player",
        min_n,
    )


# ---- quarterback ----


def ply_18(ctx: MetricContext) -> pl.DataFrame:
    """PLY-18: QB depth profile: share of his attempts and EPA per attempt in each OFF-13
    depth band (attempts with no air_yards: `unknown`), and aDOT. Min 30 attempts per band.
    All three shrink toward his own overall value, so they raise until Phase 3e."""
    who = pl.col("passer_player_id")
    share = cell_share(ctx, attempt(), who, band_or_unknown(), BANDS)
    qbs = _entities(share)
    epa = own_units(ctx, attempt(), who, band_or_unknown(), pl.col("epa"))
    adot = own_units(
        ctx, attempt() & pl.col("air_yards").is_not_null(), who, pl.lit("all"), pl.col("air_yards")
    )
    return pl.concat(
        [
            _rate(ctx, "PLY-18", "share", share, BANDS, qbs, "usage"),
            _rate(
                ctx,
                "PLY-18",
                "epa",
                epa,
                BANDS,
                qbs,
                "efficiency",
                _P.ply_18_min_attempts_per_band.value,
            ),
            _rate(ctx, "PLY-18", "adot", adot, ["all"], qbs, "efficiency"),
        ]
    )


def ply_19(ctx: MetricContext) -> pl.DataFrame:
    """PLY-19: play-action split: EPA per dropback with play action minus without (FTN), and
    his play-action rate. Prior = the league play-action gap. Min 40 play-action dropbacks."""
    pa = ftn(ctx, "is_play_action")
    gap = _dropback_qb_gap(ctx, "PLY-19", pa, _P.ply_19_min_play_action_dropbacks.value)
    m = pf.dropback() & pl.col("posteam").is_not_null()
    qbs = own_units(ctx, m, pf.dropback_qb(), pl.lit("all"), pl.lit(1.0))
    x = pa.cast(pl.Float64) if pa is not None else pl.lit(None, dtype=pl.Float64)
    rate_u = (
        own_units(ctx, m, pf.dropback_qb(), pl.lit("all"), pl.lit(1.0)).head(0)
        if pa is None
        else (own_units(ctx, m & pa.is_not_null(), pf.dropback_qb(), pl.lit("all"), x))
    )
    rate = _rate(ctx, "PLY-19", "play_action_rate", rate_u, ["all"], _entities(qbs), "efficiency")
    if pa is None:
        rate = _no_ftn(rate, {"play_action_rate"})
    return pl.concat([gap, rate])


def ply_20(ctx: MetricContext) -> pl.DataFrame:
    """PLY-20: accuracy and ball security per attempt: completion over expected (complete_pass
    - cp), catchable-ball rate, interception-worthy rate, throwaway rate (FTN). Prior = league
    QB (pooled). Min 100 attempts."""
    who = pl.col("passer_player_id")
    passers = _entities(own_units(ctx, attempt(), who, pl.lit("all"), pl.lit(1.0)))
    mn = _P.ply_20_min_attempts.value
    parts = []
    cp = own_units(
        ctx,
        attempt() & pl.col("cp").is_not_null(),
        who,
        pl.lit("all"),
        pl.col("complete_pass") - pl.col("cp"),
    )
    parts.append(
        _with_position_league(
            ctx,
            _rate(ctx, "PLY-20", "cpoe", cp, ["all"], passers, "efficiency", mn),
            cp,
            "PLY-20",
            "cpoe",
        )
    )
    missing = set()
    for stat, field in (
        ("catchable_rate", "is_catchable_ball"),
        ("interception_worthy_rate", "is_interception_worthy"),
        ("throwaway_rate", "is_throw_away"),
    ):
        f = ftn(ctx, field)
        if f is None:
            u = cp.head(0)
            missing.add(stat)
        else:
            u = own_units(ctx, attempt() & f.is_not_null(), who, pl.lit("all"), f.cast(pl.Float64))
        parts.append(
            _with_position_league(
                ctx,
                _rate(ctx, "PLY-20", stat, u, ["all"], passers, "efficiency", mn),
                u,
                "PLY-20",
                stat,
            )
        )
    return _no_ftn(pl.concat(parts), missing) if missing else pl.concat(parts)


def ply_21(ctx: MetricContext) -> pl.DataFrame:
    """PLY-21: time to throw (NGS weekly, attempt-weighted; n = NGS attempts, ruling
    2026-10-04) and sacks / dropbacks charged to him (the passer, or the rusher on a scramble).
    Prior = league QB (pooled). Min 100 dropbacks."""
    mn = _P.ply_21_min_dropbacks.value
    ngs = ctx.table("nextgen_passing")
    if ngs.height:
        wk = ctx.games.select("team", "week", "g")
        ttt = (
            ngs.filter((pl.col("attempts") > 0) & pl.col("avg_time_to_throw").is_not_null())
            .join(wk, left_on=["team_abbr", "week"], right_on=["team", "week"], how="inner")
            .select(
                pl.col("player_gsis_id").alias("entity_id"),
                pl.col("team_abbr").alias("team"),
                pl.lit("all").alias("cell"),
                "g",
                (pl.col("attempts") * pl.col("avg_time_to_throw")).cast(pl.Float64).alias("x"),
                pl.col("attempts").cast(pl.Float64).alias("d"),
                pl.col("attempts").cast(pl.Float64).alias("c"),
            )
        )
    else:
        ttt = pl.DataFrame(
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
    sack = own_units(ctx, pf.dropback(), pf.dropback_qb(), pl.lit("all"), pl.col("sack"))
    return pl.concat(
        [
            _with_position_league(
                ctx,
                _rate(
                    ctx, "PLY-21", "time_to_throw", ttt, ["all"], _entities(ttt), "efficiency", mn
                ),
                ttt,
                "PLY-21",
                "time_to_throw",
            ),
            _with_position_league(
                ctx,
                _rate(ctx, "PLY-21", "sack_rate", sack, ["all"], _entities(sack), "efficiency", mn),
                sack,
                "PLY-21",
                "sack_rate",
            ),
        ]
    )


def ply_22(ctx: MetricContext) -> pl.DataFrame:
    """PLY-22: QB rushing threat, for players whose weekly-roster position is QB: scrambles /
    dropbacks; designed runs per game (games with a dropback or rush of his); yards per rush
    (designed runs and scrambles). Prior = league QB average (A16). Only yards per rush has a
    k (40 rushes, ruling 2026-10-04). Min 20 rushes."""
    rush = pf.designed_run() | (pf.dropback() & (pl.col("qb_scramble") == 1).fill_null(False))
    rushes = own_units(ctx, rush, pl.col("rusher_player_id"), pl.lit("all"), pl.col("yards_gained"))
    scr = own_units(ctx, pf.dropback(), pf.dropback_qb(), pl.lit("all"), pl.col("qb_scramble"))
    involved = ctx.plays.filter(pl.col("posteam").is_not_null()).select(
        "game_id",
        pl.col("posteam").alias("team"),
        pl.col("g_off").cast(pl.Float64).alias("g"),
        pl.when(pf.dropback()).then(pf.dropback_qb()).alias("_qb"),
        pl.when(rush).then(pl.col("rusher_player_id")).alias("_r"),
        pl.when(pf.designed_run()).then(pl.col("rusher_player_id")).alias("_dr"),
    )
    who = (
        pl.concat(
            [
                involved.select("game_id", "team", "g", pl.col(c).alias("entity_id"))
                for c in ("_qb", "_r")
            ]
        )
        .filter(pl.col("entity_id").is_not_null())
        .unique()
    )
    runs = (
        involved.filter(pl.col("_dr").is_not_null())
        .group_by("game_id", "team", pl.col("_dr").alias("entity_id"))
        .agg(pl.len().cast(pl.Float64).alias("x"))
    )
    rpg = who.join(runs, on=["game_id", "team", "entity_id"], how="left").select(
        "entity_id", "team", pl.lit("all").alias("cell"), "g", pl.col("x").fill_null(0.0)
    )
    pos = ctx.positions
    qbs = (
        pl.concat([_entities(u) for u in (rushes, scr, rpg)])
        .unique()
        .filter(pl.col("entity_id").replace_strict(pos, default=None, return_dtype=pl.Utf8) == "QB")
        .sort("entity_id", "team")
    )

    def keep(u: pl.DataFrame) -> pl.DataFrame:
        return u.join(qbs, on=["entity_id", "team"], how="semi")

    mn = _P.ply_22_min_rushes.value
    return pl.concat(
        [
            _with_position_league(
                ctx,
                _rate(
                    ctx, "PLY-22", "yards_per_rush", keep(rushes), ["all"], qbs, "efficiency", mn
                ),
                rushes,
                "PLY-22",
                "yards_per_rush",
            ),
            _rate(ctx, "PLY-22", "scramble_rate", keep(scr), ["all"], qbs, "efficiency"),
            _rate(ctx, "PLY-22", "designed_runs_per_game", keep(rpg), ["all"], qbs, "efficiency"),
        ]
    )


def ply_23(ctx: MetricContext) -> pl.DataFrame:
    """PLY-23: QB direction: share of his attempts and EPA per attempt by pass_location
    (left / middle / right; none: `unknown`). Min 40 attempts per side. Prior = his overall:
    raises until Phase 3e."""
    who = pl.col("passer_player_id")
    share = cell_share(ctx, attempt(), who, location(), SIDES)
    epa = own_units(ctx, attempt(), who, location(), pl.col("epa"))
    qbs = _entities(share)
    return pl.concat(
        [
            _rate(ctx, "PLY-23", "share", share, SIDES, qbs, "usage"),
            _rate(
                ctx,
                "PLY-23",
                "epa",
                epa,
                SIDES,
                qbs,
                "efficiency",
                _P.ply_23_min_attempts_per_side.value,
            ),
        ]
    )


# ---- running back ----


def _box_band(box: pl.Expr) -> pl.Expr:
    """PLY-24 bands: light (<= 6 in box), standard (7), stacked (>= 8)."""
    return (
        pl.when(box <= _P.ply_24_light_box_max.value)
        .then(pl.lit("light"))
        .when(box >= _P.ply_24_stacked_box_min.value)
        .then(pl.lit("stacked"))
        .when(box == _P.ply_24_standard_box.value)
        .then(pl.lit("standard"))
    )


def _backs(ctx: MetricContext) -> pl.DataFrame:
    return _entities(
        own_units(ctx, pf.designed_run(), pl.col("rusher_player_id"), pl.lit("all"), pl.lit(1.0))
    )


def ply_24(ctx: MetricContext) -> pl.DataFrame:
    """PLY-24: box-count splits on his designed runs: success rate and yards per carry vs
    light, standard and stacked boxes (FTN n_defense_box). Min 20 carries per band. Prior =
    his overall: raises until Phase 3e. Missing before 2022."""
    box = ftn(ctx, "n_defense_box")
    backs = _backs(ctx)
    who = pl.col("rusher_player_id")
    parts = []
    for stat, x in (("success", pl.col("success")), ("ypc", pl.col("yards_gained"))):
        u = (
            own_units(ctx, pf.designed_run(), who, _box_band(box), x)
            if box is not None
            else (own_units(ctx, pf.designed_run(), who, pl.lit("all"), x).head(0))
        )
        parts.append(
            _rate(
                ctx,
                "PLY-24",
                stat,
                u,
                BOX_BANDS,
                backs,
                "efficiency",
                _P.ply_24_min_carries_per_band.value,
            )
        )
    out = pl.concat(parts)
    return _no_ftn(out, {"success", "ypc"}) if box is None else out


def ply_25(ctx: MetricContext) -> pl.DataFrame:
    """PLY-25: formation split on his designed runs: success and yards per carry from shotgun
    vs under center. Min 25 carries each. Prior = his overall: raises until Phase 3e."""
    cell = pl.when(pl.col("shotgun") == 1).then(pl.lit("shotgun")).otherwise(pl.lit("under_center"))
    backs = _backs(ctx)
    who = pl.col("rusher_player_id")
    return pl.concat(
        [
            _rate(
                ctx,
                "PLY-25",
                stat,
                own_units(ctx, pf.designed_run(), who, cell, x),
                ["shotgun", "under_center"],
                backs,
                "efficiency",
                _P.ply_25_min_carries_each.value,
            )
            for stat, x in (("success", pl.col("success")), ("ypc", pl.col("yards_gained")))
        ]
    )


def ply_26(ctx: MetricContext) -> pl.DataFrame:
    """PLY-26: explosiveness and stuff avoidance on his designed runs: share of carries 10+
    yards and share at <= 0 yards, prior = league RB (pooled); plus his rushing yards over
    expected (PLY-11's value, shown alongside). Min 60 carries."""
    from ge.metrics.player import ply_11

    who = pl.col("rusher_player_id")
    mn = _P.ply_26_min_carries.value
    parts = []
    for stat, x in (
        (
            "explosive",
            (pl.col("yards_gained") >= _P.ply_26_explosive_min_yards.value).cast(pl.Float64),
        ),
        ("stuff", (pl.col("yards_gained") <= _P.ply_26_stuff_max_yards.value).cast(pl.Float64)),
    ):
        u = own_units(ctx, pf.designed_run(), who, pl.lit("all"), x)
        parts.append(
            _with_position_league(
                ctx,
                _rate(ctx, "PLY-26", stat, u, ["all"], _entities(u), "efficiency", mn),
                u,
                "PLY-26",
                stat,
            )
        )
    ry = (
        ply_11(ctx)
        .filter(pl.col("entity_type") == "player")
        .with_columns(
            pl.lit("PLY-26").alias("spec_id"),
            pl.lit("PLY-11's value, shown alongside").alias("note"),
        )
    )
    return pl.concat([*parts, ry])


# ---- receivers and tight ends ----


def ply_27(ctx: MetricContext) -> pl.DataFrame:
    """PLY-27: receiving role: target share (PLY-03's), share of team screen targets (FTN
    is_screen_pass), yards after catch over expected (PLY-09's). Role prior: raises until
    Phase 3e. Min 15 targets."""
    from ge.metrics.player import ply_03, ply_09

    scr = ftn(ctx, "is_screen_pass")
    mask = pf.usage_target() & (scr.fill_null(False) if scr is not None else pl.lit(False))
    u = share_units(ctx, mask, pl.lit("all"), pl.col("receiver_player_id"))
    ss = _rate(ctx, "PLY-27", "screen_share", u, ["all"], stints(ctx), "usage")
    if scr is None:
        ss = _no_ftn(ss, {"screen_share"})
    ts = ply_03(ctx).with_columns(pl.lit("PLY-27").alias("spec_id"))
    ya = ply_09(ctx).with_columns(pl.lit("PLY-27").alias("spec_id"))
    return pl.concat([ss, ts, ya])


def ply_28(ctx: MetricContext) -> pl.DataFrame:
    """PLY-28: receiver depth profile: share of his targets and EPA per target in each depth
    band, and aDOT. Min 15 targets per band. Prior = his overall: raises until Phase 3e."""
    who = pl.col("receiver_player_id")
    share = cell_share(ctx, pf.target(), who, band_or_unknown(), BANDS)
    keys = _entities(share)
    epa = own_units(ctx, pf.target(), who, band_or_unknown(), pl.col("epa"))
    adot = own_units(
        ctx,
        pf.target() & pl.col("air_yards").is_not_null(),
        who,
        pl.lit("all"),
        pl.col("air_yards"),
    )
    return pl.concat(
        [
            _rate(ctx, "PLY-28", "share", share, BANDS, keys, "usage"),
            _rate(
                ctx,
                "PLY-28",
                "epa",
                epa,
                BANDS,
                keys,
                "efficiency",
                _P.ply_28_min_targets_per_band.value,
            ),
            _rate(ctx, "PLY-28", "adot", adot, ["all"], keys, "efficiency"),
        ]
    )


def ply_29(ctx: MetricContext) -> pl.DataFrame:
    """PLY-29: field location: share of his targets and EPA per target by pass_location. The
    `middle` share is a rough stand-in for slot usage, labelled as a proxy. Min 20 targets per
    side. Prior = his overall: raises until Phase 3e."""
    who = pl.col("receiver_player_id")
    share = cell_share(ctx, pf.target(), who, location(), SIDES)
    keys = _entities(share)
    epa = own_units(ctx, pf.target(), who, location(), pl.col("epa"))
    out = pl.concat(
        [
            _rate(ctx, "PLY-29", "share", share, SIDES, keys, "usage"),
            _rate(
                ctx,
                "PLY-29",
                "epa",
                epa,
                SIDES,
                keys,
                "efficiency",
                _P.ply_29_min_targets_per_side.value,
            ),
        ]
    )
    mid = pl.col("cell") == "middle"
    return out.with_columns(
        pl.when(mid).then(True).otherwise(pl.col("proxy")).alias("proxy"),
        pl.when(mid)
        .then(pl.lit("middle share: rough slot-usage proxy"))
        .otherwise(pl.col("note"))
        .alias("note"),
    )


def ply_30(ctx: MetricContext) -> pl.DataFrame:
    """PLY-30: hands and ball skills (FTN): drops / catchable targets (k 60); catches /
    contested targets (k 30); created receptions / receptions (ruling 2026-10-04; no k, so its
    shrink raises). Prior = league at his position (pooled). Min 20 catchable, 10 contested."""
    who = pl.col("receiver_player_id")
    keys = _entities(own_units(ctx, pf.target(), who, pl.lit("all"), pl.lit(1.0)))
    catch, contest, drop, created = (
        ftn(ctx, f)
        for f in ("is_catchable_ball", "is_contested_ball", "is_drop", "is_created_reception")
    )
    empty = own_units(ctx, pf.target(), who, pl.lit("all"), pl.lit(1.0)).head(0)
    if catch is None:
        cases = {
            s: (empty, m)
            for s, m in (
                ("drop_rate", _P.ply_30_min_catchable.value),
                ("contested_catch_rate", _P.ply_30_min_contested.value),
                ("created_reception_rate", None),
            )
        }
    else:
        assert contest is not None and drop is not None and created is not None
        cases = {
            "drop_rate": (
                own_units(
                    ctx,
                    pf.target() & catch.fill_null(False) & drop.is_not_null(),
                    who,
                    pl.lit("all"),
                    drop.cast(pl.Float64),
                ),
                _P.ply_30_min_catchable.value,
            ),
            "contested_catch_rate": (
                own_units(
                    ctx,
                    pf.target() & contest.fill_null(False),
                    who,
                    pl.lit("all"),
                    pl.col("complete_pass"),
                ),
                _P.ply_30_min_contested.value,
            ),
            "created_reception_rate": (
                own_units(
                    ctx,
                    pf.target() & (pl.col("complete_pass") == 1) & created.is_not_null(),
                    who,
                    pl.lit("all"),
                    created.cast(pl.Float64),
                ),
                None,
            ),
        }
    parts = [
        _with_position_league(
            ctx, _rate(ctx, "PLY-30", s, u, ["all"], keys, "efficiency", m), u, "PLY-30", s
        )
        for s, (u, m) in cases.items()
    ]
    out = pl.concat(parts)
    return _no_ftn(out, set(cases)) if catch is None else out


def ply_31(ctx: MetricContext) -> pl.DataFrame:
    """PLY-31: NGS average separation and cushion, target-weighted (A24), prior league at his
    position (pooled); plus his YAC over expected (PLY-09's value, shown alongside). Min 30
    targets."""
    from ge.metrics.player import ply_09

    ngs = ctx.table("nextgen_receiving")
    mn = _P.ply_31_min_targets.value
    parts = []
    for stat, col in (("separation", "avg_separation"), ("cushion", "avg_cushion")):
        if ngs.height:
            wk = ctx.games.select("team", "week", "g")
            u = (
                ngs.filter((pl.col("targets") > 0) & pl.col(col).is_not_null())
                .join(wk, left_on=["team_abbr", "week"], right_on=["team", "week"], how="inner")
                .select(
                    pl.col("player_gsis_id").alias("entity_id"),
                    pl.col("team_abbr").alias("team"),
                    pl.lit("all").alias("cell"),
                    "g",
                    (pl.col("targets") * pl.col(col)).cast(pl.Float64).alias("x"),
                    pl.col("targets").cast(pl.Float64).alias("d"),
                    pl.col("targets").cast(pl.Float64).alias("c"),
                )
            )
        else:
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
        parts.append(
            _with_position_league(
                ctx,
                _rate(ctx, "PLY-31", stat, u, ["all"], _entities(u), "efficiency", mn),
                u,
                "PLY-31",
                stat,
            )
        )
    ya = (
        ply_09(ctx)
        .filter(pl.col("entity_type") == "player")
        .with_columns(
            pl.lit("PLY-31").alias("spec_id"),
            pl.lit("PLY-09's value, shown alongside").alias("note"),
        )
    )
    return pl.concat([*parts, ya])


def ply_32(ctx: MetricContext) -> pl.DataFrame:
    """PLY-32: end-zone targets (air_yards >= yardline_100) as a share of team end-zone
    targets in the games he played. Min 5 team end-zone targets. Prior = his PLY-06 share:
    raises until Phase 3e."""
    ez = pf.usage_target() & (pl.col("air_yards") >= pl.col("yardline_100")).fill_null(False)
    u = share_units(ctx, ez, pl.lit("all"), pl.col("receiver_player_id"))
    return _rate(
        ctx,
        "PLY-32",
        "end_zone_share",
        u,
        ["all"],
        stints(ctx),
        "usage",
        _P.ply_32_min_team_end_zone_targets.value,
    )


def ply_33(ctx: MetricContext) -> pl.DataFrame:
    """PLY-33: his share of team targets on play-action and on motion plays (FTN), in games he
    played. Min 15 targets each (team targets in that cell). Prior = his overall target
    share: raises until Phase 3e. Missing before 2022."""
    pa, mo = ftn(ctx, "is_play_action"), ftn(ctx, "is_motion")
    who = pl.col("receiver_player_id")
    if pa is None or mo is None:
        u = share_units(ctx, pl.lit(False), pl.lit("play_action"), who)
    else:
        u = pl.concat(
            [
                share_units(
                    ctx, pf.usage_target() & pa.fill_null(False), pl.lit("play_action"), who
                ),
                share_units(ctx, pf.usage_target() & mo.fill_null(False), pl.lit("motion"), who),
            ]
        )
    out = _rate(
        ctx,
        "PLY-33",
        "target_share",
        u,
        ["play_action", "motion"],
        stints(ctx),
        "usage",
        _P.ply_33_min_targets_each.value,
    )
    return _no_ftn(out, {"target_share"}) if pa is None else out


# ---- all positions ----


def _inches(ht: pl.Expr) -> pl.Expr:
    """nflverse combine height is text "feet-inches" (e.g. "6-2")."""
    parts = ht.cast(pl.Utf8).str.split_exact("-", 1)
    return parts.struct.field("field_0").cast(pl.Float64) * 12 + parts.struct.field("field_1").cast(
        pl.Float64
    )


def ply_34(ctx: MetricContext) -> pl.DataFrame:
    """PLY-34: athletic profile, a prior only (not shrunk, not paired): height, weight, 40,
    vertical, broad jump, 3-cone, shuttle, and each one's percentile within his combine `pos`
    over every draft year held up to the target season (rulings 2026-10-04). Percentile =
    (players below + half the ties) / pool; for timed drills (lower is faster) it counts the
    players above, so a higher percentile is always better. Combine rows without a pfr_id stay
    in the pools but give no one a profile. Players link by pfr_id (DATA-04 crosswalk)."""
    comb = ctx.snap.collect("combine")
    if comb.is_empty():
        return finish(pl.DataFrame(schema={"spec_id": pl.Utf8}))
    vals = comb.with_columns(_inches(pl.col("ht")).alias("ht"))
    pools: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in vals.iter_rows(named=True):
        for m, col in MEASURES.items():
            if r["pos"] is not None and r[col] is not None:
                pools[(r["pos"], m)].append(float(r[col]))
    sorted_pools = {k: sorted(v) for k, v in pools.items()}
    xw = ctx.crosswalk
    latest = (
        vals.filter(pl.col("pfr_id").is_not_null())
        .with_columns(
            pl.col("pfr_id").replace_strict(xw, default=None, return_dtype=pl.Utf8).alias("gsis")
        )
        .filter(pl.col("gsis").is_not_null())
        .sort("season", "pfr_id")
        .group_by("gsis", maintain_order=True)
        .last()
    )
    import bisect

    rows = []
    for r in latest.iter_rows(named=True):
        for m, col in MEASURES.items():
            x = r[col]
            if r["pos"] is None or x is None:
                continue
            pool = sorted_pools[(r["pos"], m)]
            below = bisect.bisect_left(pool, x)
            above = len(pool) - bisect.bisect_right(pool, x)
            ties = len(pool) - below - above
            pct = ((above if m in TIMED else below) + 0.5 * ties) / len(pool)
            base = {
                "entity_type": "player",
                "entity_id": r["gsis"],
                "cell": r["pos"],
                "n": len(pool),
                "note": f"combine {r['season']}",
            }
            rows.append({**base, "stat": m, "value": float(x)})
            rows.append(
                {
                    **base,
                    "stat": f"{m}_pctl",
                    "value": pct,
                    "note": f"combine {r['season']}; within {r['pos']}, all draft years"
                    + ("; inverted (lower is faster)" if m in TIMED else ""),
                }
            )
    df = pl.DataFrame(rows, infer_schema_length=None).with_columns(
        pl.lit("PLY-34").alias("spec_id")
    )
    return finish(df).sort("entity_id", "stat")


__all__ = ["gap_metric", "summarise"]
