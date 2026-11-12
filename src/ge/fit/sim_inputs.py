"""Phase 5 fit inputs: rows for the rating-tilt, weather and Questionable/Doubtful fits, built
from nflverse play-by-play with the production play filters (ge.metrics.plays).

Rulings 2026-10-24 (D2-D7):
- D2: surface classes (grass natural; fieldturf, matrixturf, sportturf, astroturf, a_turf
  artificial; whitespace trimmed; empty = unknown).
- D6 and the 2026-10-24 ruling (replacing D3): tilt rows. x = the offense's mean EPA over its
  OFF-01 qualifying pass plays (sacks and scrambles count) or designed runs in that game,
  leaving out the play itself, G7 applied, centred on the season's league mean over the same
  plays. The as-written value (the play included) is kept beside it for the report.
- D5: weather rows. Completion: pass attempts excluding sacks, G7 applied; deep-attempt share:
  the same attempts with air_yards; field-goal make: attempts with kick_distance. Only games
  with an ERA5 game window (outdoor or open roof).
- D7: Questionable/Doubtful rows: offensive positions only; played = at least one offensive
  snap that week."""

from __future__ import annotations

from collections.abc import Mapping

import polars as pl

from ge.config import load_params
from ge.metrics import plays as pf

NATURAL = ("grass",)
ARTIFICIAL = ("fieldturf", "matrixturf", "sportturf", "astroturf", "a_turf")
OFFENSIVE_POSITIONS = ("QB", "RB", "FB", "WR", "TE", "T", "G", "C", "OL", "OT", "OG")
GAME_STATUSES = ("Questionable", "Doubtful")
WEATHER_COLUMNS = {
    "precipitation_mm": "precipitation",
    "snowfall_cm": "snowfall",
    "wind_speed_kmh": "wind_speed",
    "wind_gusts_kmh": "wind_gusts",
    "temperature_c": "temperature",
}


def surface_class(raw: str | None) -> str | None:
    """ENV-01 (ruling D2): natural, artificial, or None when the data has no surface."""
    if raw is None or not raw.strip():
        return None
    v = raw.strip()
    if v in NATURAL:
        return "natural"
    if v in ARTIFICIAL:
        return "artificial"
    raise ValueError(f"ENV-01: surface {raw!r} has no class; rule on it before fitting")


def _is1(col: str) -> pl.Expr:
    return (pl.col(col) == 1).fill_null(False)


def _side_x(plays: pl.DataFrame, keep: pl.Expr, side: str) -> pl.DataFrame:
    """Per play on one side: x_raw (team-game mean EPA), x_loo_raw (without the play) and the
    season league mean over the same plays."""
    d = plays.filter(keep & pl.col("epa").is_not_null()).with_row_index("_row")
    tg = ["game_id", "posteam"]
    return d.with_columns(
        pl.col("epa").sum().over(tg).alias("_sum"),
        pl.len().over(tg).alias("_n"),
        pl.col("epa").mean().over("season").alias("_league"),
        pl.lit(side).alias("side"),
    ).with_columns(
        (pl.col("_sum") / pl.col("_n")).alias("x_raw"),
        pl.when(pl.col("_n") > 1)
        .then((pl.col("_sum") - pl.col("epa")) / (pl.col("_n") - 1))
        .otherwise(None)
        .alias("x_loo_raw"),
    )


def tilt_rows(plays: pl.DataFrame) -> pl.DataFrame:
    """PRJ-02 rating tilt (D6; ruling 2026-10-24): one row per (play, component) with season,
    team_game, y, x (leave-one-out, centred: the fitted predictor), x_written (the play
    included, centred: the report's comparison), x_raw and x_loo_raw. A team-game side with one
    play has no leave-one-out value; its row has x null and is not fitted."""
    passes = _side_x(plays, pf.qualifying() & _is1("pass"), "pass")
    runs = _side_x(plays, pf.designed_run(), "run")
    attempts = passes.filter(_is1("pass_attempt") & ~_is1("sack"))
    parts = [
        attempts.with_columns(pl.lit("completion").alias("component"), _f("complete_pass")),
        attempts.with_columns(pl.lit("interception").alias("component"), _f("interception")),
        attempts.filter(
            _is1("complete_pass") & pl.col("yards_after_catch").is_not_null()
        ).with_columns(pl.lit("yac").alias("component"), _f("yards_after_catch")),
        runs.with_columns(pl.lit("yards_per_carry").alias("component"), _f("yards_gained")),
        runs.with_columns(pl.lit("fumble_lost").alias("component"), _f("fumble_lost")),
    ]
    out = pl.concat(
        [
            p.select(
                "component",
                pl.col("season").cast(pl.Int64),
                (pl.col("game_id") + "|" + pl.col("posteam")).alias("team_game"),
                "y",
                (pl.col("x_loo_raw") - pl.col("_league")).alias("x"),
                (pl.col("x_raw") - pl.col("_league")).alias("x_written"),
                "x_raw",
                "x_loo_raw",
            )
            for p in parts
        ]
    )
    return out.filter(pl.col("y").is_not_null())


def _f(col: str) -> pl.Expr:
    """The outcome as y; a missing outcome stays missing and its row is dropped."""
    return pl.col(col).cast(pl.Float64).alias("y")


def weather_rows(
    plays: pl.DataFrame, windows: pl.DataFrame, elevation_m: Mapping[str, float]
) -> dict[str, pl.DataFrame]:
    """MTC-05 (D5): rows per outcome (completion, deep_attempt, fg_make) with season,
    team_game, y and the five weather factors; fg_make adds distance and altitude (ENV-02)."""
    w = windows.select("game_id", *(pl.col(k).alias(v) for k, v in WEATHER_COLUMNS.items()))
    base = plays.join(w, on="game_id", how="inner").with_columns(
        (pl.col("game_id") + "|" + pl.col("posteam")).alias("team_game"),
        pl.col("season").cast(pl.Int64),
    )
    factors = list(WEATHER_COLUMNS.values())
    attempts = base.filter(_is1("pass_attempt") & ~_is1("sack") & pf.scrimmage() & ~pf.garbage())
    deep_min = float(load_params().offense.off_13_deep_min_air_yards.value)
    completion = attempts.select(
        "season", "team_game", pl.col("complete_pass").cast(pl.Float64).alias("y"), *factors
    )
    deep = attempts.filter(pl.col("air_yards").is_not_null()).select(
        "season",
        "team_game",
        (pl.col("air_yards") >= deep_min).cast(pl.Float64).alias("y"),
        *factors,
    )
    alt = pl.DataFrame(
        {"game_id": list(elevation_m), "altitude": [float(v) for v in elevation_m.values()]},
        schema={"game_id": pl.String, "altitude": pl.Float64},
    )
    fg = (
        base.filter(_is1("field_goal_attempt") & pl.col("kick_distance").is_not_null())
        .join(alt, on="game_id", how="inner")
        .select(
            "season",
            "team_game",
            (pl.col("field_goal_result") == "made").cast(pl.Float64).alias("y"),
            pl.col("kick_distance").cast(pl.Float64).alias("distance"),
            "altitude",
            *factors,
        )
    )
    return {"completion": completion, "deep_attempt": deep, "fg_make": fg}


def game_status_rows(
    injuries: pl.DataFrame, snaps: pl.DataFrame, team_weeks: pl.DataFrame
) -> pl.DataFrame:
    """PLY-14 (D7): one row per offensive player listed Questionable or Doubtful in a week his
    team played; played = at least one offensive snap that week."""
    listed = (
        injuries.filter(
            pl.col("gsis_id").is_not_null()
            & pl.col("report_status").is_in(GAME_STATUSES)
            & pl.col("position").is_in(OFFENSIVE_POSITIONS)
        )
        .select(
            "gsis_id",
            "team",
            pl.col("week").cast(pl.Int64),
            pl.col("report_status").alias("status"),
        )
        .unique()
        .join(
            team_weeks.with_columns(pl.col("week").cast(pl.Int64)), on=["team", "week"], how="semi"
        )
    )
    played = (
        snaps.filter(pl.col("offense_snaps").fill_null(0) > 0)
        .select("gsis_id", "team", pl.col("week").cast(pl.Int64))
        .unique()
        .with_columns(pl.lit(True).alias("played"))
    )
    return (
        listed.join(played, on=["gsis_id", "team", "week"], how="left")
        .with_columns(pl.col("played").fill_null(False))
        .sort("team", "week", "gsis_id")
    )
