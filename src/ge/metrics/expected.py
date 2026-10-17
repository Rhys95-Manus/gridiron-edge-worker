"""PLY-35 expected production from opportunity (spec synced 2026-10-16): per player-game
actual minus expected receptions, receiving yards, rushing yards and TDs from nflverse
ff_opportunity (DATA-04, model v1.0.0), centred on the league mean gap for the player's position
group and summed over his games in the (player, team) stint.

The expected values come from one fixed model whose README states it was trained on nflverse
data from 2006-2020; the training code is not published, so that is the source's statement.

Data: nflverse; charting: FTN Data via nflverse; expected points: ffopportunity (ffverse) via
nflverse; data license not stated by the source."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import TYPE_CHECKING

import polars as pl

from ge.metrics import conventions as cv
from ge.metrics.engine import empty_raw, finish, param, summarise
from ge.store.snapshot import FF

if TYPE_CHECKING:
    from ge.metrics.context import MetricContext

SPEC_ID = "PLY-35"
# stat -> (actual columns, expected columns); TDs are receiving + rushing (PLY-35 row).
STATS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "receptions": (("receptions",), ("receptions_exp",)),
    "receiving_yards": (("rec_yards_gained",), ("rec_yards_gained_exp",)),
    "rushing_yards": (("rush_yards_gained",), ("rush_yards_gained_exp",)),
    "tds": (("rec_touchdown", "rush_touchdown"), ("rec_touchdown_exp", "rush_touchdown_exp")),
}
NUMERIC_COLUMNS = (
    "rec_attempt",
    "rush_attempt",
    "receptions",
    "receptions_exp",
    "rec_yards_gained",
    "rec_yards_gained_exp",
    "rush_yards_gained",
    "rush_yards_gained_exp",
    "rec_touchdown",
    "rec_touchdown_exp",
    "rush_touchdown",
    "rush_touchdown_exp",
)
GROUPS = ("QB", "RB", "WR", "TE")  # PLY-35 rules; every other position pools into OTHER
OTHER = "Other"
NO_PLAYER = "rows_no_player_id"
NO_MEAN = "no centring mean for this position group"


def position_group(position: pl.Expr) -> pl.Expr:
    """PLY-35 rules: QB, RB, WR and TE are their own groups; every other position, and rows with
    no position, pool into one Other group."""
    return (
        pl.when(position.is_in(list(GROUPS))).then(position).otherwise(pl.lit(OTHER)).alias("group")
    )


def qualifying(ff: pl.DataFrame) -> tuple[pl.DataFrame, int]:
    """PLY-35 rules: a game counts when the player's row has at least one target or carry;
    rows with no player_id are dropped and counted. Returns (rows, rows dropped for no player)."""
    no_player = int(ff["player_id"].null_count()) if ff.height else 0
    opp = pl.col("rec_attempt").fill_null(0.0) + pl.col("rush_attempt").fill_null(0.0)
    rows = ff.filter(pl.col("player_id").is_not_null() & (opp >= 1))
    return rows, no_player


def raw_gaps(rows: pl.DataFrame) -> pl.DataFrame:
    """PLY-35: per player-game raw gap = actual - expected for each stat, with the position
    group. A missing value counts as 0 (ff_opportunity leaves a column null when the player had
    none of that play type)."""

    def total(cols: tuple[str, ...]) -> pl.Expr:
        expr = pl.lit(0.0)
        for c in cols:
            expr = expr + pl.col(c).fill_null(0.0)
        return expr

    return rows.select(
        "game_id",
        "player_id",
        "posteam",
        position_group(pl.col("position")),
        *[(total(act) - total(exp)).alias(stat) for stat, (act, exp) in STATS.items()],
    )


def centring_means(gaps: pl.DataFrame) -> dict[tuple[str, str], tuple[float, int]]:
    """(group, stat) -> (unweighted mean raw gap, player-games), math.fsum (rule 6)."""
    acc: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in gaps.iter_rows(named=True):
        for stat in STATS:
            acc[(r["group"], stat)].append(float(r[stat]))
    return {k: (math.fsum(v) / len(v), len(v)) for k, v in sorted(acc.items())}


def _season_rows(ff: pl.DataFrame, season: int) -> pl.DataFrame:
    return ff.filter(pl.col("game_id").str.starts_with(f"{season}_"))


def ply_35(ctx: MetricContext) -> pl.DataFrame:
    """PLY-35 expected production from opportunity: per (player, team) stint and stat, value =
    centred gap summed over his games, value_w = the G3 recency-weighted mean centred gap
    (efficiency half-life) that G1 shrinks toward 0, n = games; `<stat>_raw` rows carry the
    uncentred gaps, and league rows "league:<group>" the centring mean each group used."""
    from ge.metrics.player import stints

    ff = ctx.snap.collect(FF)
    if ff.is_empty():
        return empty_raw()
    cur = _season_rows(ff, ctx.season)
    rows, no_player = qualifying(cur)
    gaps = raw_gaps(rows).join(
        ctx.games.select(pl.col("team").alias("posteam"), "game_id", "g", "week"),
        on=["posteam", "game_id"],
        how="inner",
    )
    weeks = (
        ctx.games.filter(pl.col("game_id").is_in(cur["game_id"].unique().to_list()))["week"]
        .unique()
        .len()
    )
    min_weeks = param("player.ply_35_centring_min_weeks")
    if weeks < min_weeks:
        prev, _ = qualifying(_season_rows(ff, ctx.season - 1))
        means = centring_means(raw_gaps(prev))
        label = (
            f"centring: season {ctx.season - 1} full-season mean (season {ctx.season} has games "
            f"visible in {weeks} week(s), fewer than {int(min_weeks)})"
        )
    else:
        means = centring_means(gaps)
        label = f"centring: season {ctx.season} games visible at as_of"

    h = cv.half_life("efficiency")
    min_n = param("player.ply_35_min_games")
    ents = pl.concat(
        [
            stints(ctx),
            gaps.select(pl.col("player_id").alias("entity_id"), pl.col("posteam").alias("team")),
        ]
    ).unique()
    parts = []
    for stat in STATS:
        mu = {g: m for (g, s), (m, _) in means.items() if s == stat}
        centred = gaps.with_columns(
            (
                pl.col(stat)
                - pl.col("group").replace_strict(mu, default=None, return_dtype=pl.Float64)
            ).alias("_centred")
        )
        for name, col in ((stat, "_centred"), (f"{stat}_raw", stat)):
            units = centred.select(
                pl.col("player_id").alias("entity_id"),
                pl.col("posteam").alias("team"),
                pl.lit("all").alias("cell"),
                pl.col("g"),
                pl.col(col).alias("x"),
            )
            out = summarise(
                units,
                spec_id=SPEC_ID,
                stat=name,
                entity_type="player",
                entities=ents,
                cells=["all"],
                h=h,
                min_n=min_n,
                league=False,
            )
            parts.append(_with_sums(out, units, label, col == "_centred", centred, stat, mu))
    parts.append(_league_rows(means, label, no_player))
    return pl.concat(parts).sort("entity_type", "entity_id", "team", "stat")


def _with_sums(
    out: pl.DataFrame,
    units: pl.DataFrame,
    label: str,
    is_centred: bool,
    centred: pl.DataFrame,
    stat: str,
    mu: dict[str, float],
) -> pl.DataFrame:
    """value = the gap summed over his games (math.fsum), not the mean summarise gives; rows
    with games carry the centring label; a player whose group had no centring mean says so."""
    sums: dict[tuple[str, str], list[float]] = defaultdict(list)
    for e, t, x in units.drop_nulls("x").select("entity_id", "team", "x").iter_rows():
        sums[(e, t)].append(x)
    total = {k: math.fsum(v) for k, v in sums.items()}
    no_mean = set()
    if is_centred:
        missing = centred.filter(~pl.col("group").is_in(list(mu)))
        no_mean = set(missing.select("player_id", "posteam").iter_rows())
    vals, notes = [], []
    for e, t, n, note in out.select("entity_id", "team", "n", "note").iter_rows():
        vals.append(total.get((e, t)))
        extra = [label] if n else []
        if (e, t) in no_mean:
            extra.append(NO_MEAN)
        notes.append("; ".join(x for x in (note, *extra) if x) or None)
    return finish(
        out.with_columns(
            pl.Series("value", vals, dtype=pl.Float64), pl.Series("note", notes, dtype=pl.Utf8)
        )
    )


def _league_rows(
    means: dict[tuple[str, str], tuple[float, int]], label: str, no_player: int
) -> pl.DataFrame:
    rows = [
        {
            "spec_id": SPEC_ID,
            "entity_type": "league",
            "entity_id": f"league:{g}",
            "cell": "all",
            "stat": f"{stat}_raw",
            "value": m,
            "value_w": m,
            "n": n,
            "n_eff": float(n),
            "note": label,
        }
        for (g, stat), (m, n) in means.items()
    ]
    rows.append(
        {
            "spec_id": SPEC_ID,
            "entity_type": "league",
            "entity_id": "league",
            "cell": "all",
            "stat": NO_PLAYER,
            "value": float(no_player),
            "value_w": float(no_player),
            "n": no_player,
            "n_eff": float(no_player),
            "note": "ff_opportunity rows with no player_id, dropped (PLY-35 rules)",
        }
    )
    return finish(pl.DataFrame(rows))
