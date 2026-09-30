"""BT-01 known-at rules: which rows of each dataset could have been known at as_of.

nflverse publishes no timestamps for most of this, so each rule is stated here once, and every
snapshot carries a label naming the assumptions it relied on (docs/MODEL_SPEC.md BT-01,
"Availability rules"). All times are timezone-aware UTC; schedule times are US Eastern."""

from __future__ import annotations

import datetime as dt
import json
from typing import Literal
from zoneinfo import ZoneInfo

import polars as pl

from ge.config import Backtest
from ge.ingest.prices import dollars_to_cc

EASTERN = ZoneInfo("America/New_York")  # nflverse schedules: gameday and gametime are Eastern
Pass = Literal["decision", "inactives"]

# Target game's schedule fields that only exist after the game. Starting QBs count: who
# actually started is post-game knowledge.
TARGET_NEVER = (
    "away_score",
    "home_score",
    "result",
    "total",
    "overtime",
    "away_qb_id",
    "home_qb_id",
    "away_qb_name",
    "home_qb_name",
)
# nflverse schedules carry closing lines only (BT-04).
CLOSING_LINES = (
    "spread_line",
    "total_line",
    "away_moneyline",
    "home_moneyline",
    "away_spread_odds",
    "home_spread_odds",
    "under_odds",
    "over_odds",
)
OBSERVED_WEATHER = ("temp", "wind")
OBSERVED_AS_FORECAST_PROXY = "observed_as_forecast_proxy"
# Kalshi market fields that don't change with time; everything else in a market row pulled
# after as_of (status, close time, asks, volume, raw record with its result) is dropped.
STATIC_MARKET_COLUMNS = (
    "ticker",
    "event_ticker",
    "series_ticker",
    "yes_sub_title",
    "occurs_at",
    "rules_primary",
    "rules_secondary",
)
_UTC_US = pl.Datetime("us", "UTC")


class GameEndUnknown(RuntimeError):
    """A game has play-by-play but no play has a wall-clock time, so we can't tell when it
    finished. Raised instead of guessing (user decision 2026-09-30)."""


def kickoff_utc(gameday: str, gametime: str) -> dt.datetime:
    """BT-01: kickoff from schedules' Eastern gameday and gametime, as UTC."""
    local = dt.datetime.combine(
        dt.date.fromisoformat(gameday), dt.time.fromisoformat(gametime), EASTERN
    )
    return local.astimezone(dt.UTC)


def with_kickoff(sched: pl.DataFrame) -> pl.DataFrame:
    """BT-01: add kickoff_utc to a schedules frame."""
    return sched.with_columns(
        (pl.col("gameday") + " " + pl.col("gametime"))
        .str.to_datetime("%Y-%m-%d %H:%M", time_zone="America/New_York", time_unit="us")
        .dt.convert_time_zone("UTC")
        .alias("kickoff_utc")
    )


def week_window(sched: pl.DataFrame, week: int) -> tuple[dt.datetime, dt.datetime | None]:
    """DATA-08 / BT-01: a week runs from its first game date (00:00 ET) to the next week's
    first game date; the last week is open-ended."""

    def first_day(w: int) -> dt.date | None:
        days = sched.filter(pl.col("week") == w)["gameday"].str.to_date()
        return days.min() if days.len() else None  # type: ignore[return-value]

    start = first_day(week)
    if start is None:
        raise KeyError(f"no week {week} games in schedules")
    nxt = first_day(week + 1)

    def to_utc(d: dt.date) -> dt.datetime:
        return dt.datetime.combine(d, dt.time(), EASTERN).astimezone(dt.UTC)

    return to_utc(start), (to_utc(nxt) if nxt else None)


def report_known_at(kickoff: dt.datetime, bt: Backtest) -> dt.datetime:
    """BT-01: an undated weekly report (injuries, weekly roster, week-numbered depth chart)
    counts as known at the assumed hour ET, the assumed days before the kickoff's ET date."""
    day = kickoff.astimezone(EASTERN).date() - dt.timedelta(
        days=bt.bt_01_assumed_report_days_before_kickoff.value
    )
    hour = bt.bt_01_assumed_report_hour_et.value
    return dt.datetime.combine(day, dt.time(int(hour)), EASTERN).astimezone(dt.UTC)


def default_as_of(kickoff: dt.datetime, pass_: Pass, bt: Backtest) -> dt.datetime:
    """BT-01: decision time is kickoff minus 24 h; the second pass is kickoff minus 90 min."""
    if pass_ == "decision":
        return kickoff - dt.timedelta(hours=bt.bt_01_decision_hours_before_kickoff.value)
    if pass_ == "inactives":
        return kickoff - dt.timedelta(minutes=bt.bt_01_second_pass_minutes_before_kickoff.value)
    raise ValueError(f"pass must be 'decision' or 'inactives', not {pass_!r}")


def team_weeks(sched: pl.DataFrame, bt: Backtest) -> pl.DataFrame:
    """BT-01: one row per team per game with its kickoff and assumed report time."""
    s = sched if "kickoff_utc" in sched.columns else with_kickoff(sched)
    both = pl.concat(
        [
            s.select("season", "week", pl.col(side).alias("team"), "game_id", "kickoff_utc")
            for side in ("home_team", "away_team")
        ]
    )
    known = [report_known_at(k, bt) for k in both["kickoff_utc"].to_list()]
    return both.with_columns(pl.Series("known_at", known, dtype=_UTC_US)).sort(
        "season", "week", "team"
    )


def game_ends(pbp: pl.DataFrame) -> pl.DataFrame:
    """BT-01: each game's last play wall-clock time (pbp time_of_day, UTC)."""
    ends = (
        pbp.select("game_id", "time_of_day")
        .with_columns(pl.col("time_of_day").str.to_datetime(time_zone="UTC", time_unit="us"))
        .group_by("game_id")
        .agg(pl.col("time_of_day").max().alias("game_end_utc"))
        .sort("game_id")
    )
    unknown = ends.filter(pl.col("game_end_utc").is_null())["game_id"].to_list()
    if unknown:
        raise GameEndUnknown(f"no play has a time_of_day in games {unknown}")
    return ends


def finished_game_ids(games: pl.DataFrame, as_of: dt.datetime, target_game_id: str) -> list[str]:
    """BT-01: games that kicked off before the target game and whose last play was run by
    as_of. `games` has game_id, kickoff_utc and game_end_utc (null for unplayed games)."""
    tgt = games.filter(pl.col("game_id") == target_game_id)
    if tgt.is_empty():
        raise KeyError(f"{target_game_id} not in games")
    k0 = tgt["kickoff_utc"][0]
    return sorted(
        games.filter(
            (pl.col("game_id") != target_game_id)
            & (pl.col("kickoff_utc") < k0)
            & pl.col("game_end_utc").is_not_null()
            & (pl.col("game_end_utc") <= as_of)
        )["game_id"].to_list()
    )


def mask_target_schedule(
    row: pl.DataFrame, as_of: dt.datetime, *, closing_line_backtest: bool
) -> tuple[pl.DataFrame, list[str]]:
    """BT-01: the target game's schedule row with post-game fields removed. Closing lines are
    shown only at or after kickoff, or when the caller asks for a closing-line backtest."""
    df = row if "kickoff_utc" in row.columns else with_kickoff(row)
    kickoff = df["kickoff_utc"][0]
    labels = [f"target_game: {', '.join(TARGET_NEVER)} never shown (post-game)"]
    drop = [c for c in TARGET_NEVER if c in df.columns]
    if as_of >= kickoff:
        labels.append("target_game: closing lines shown (as_of at or after kickoff)")
    elif closing_line_backtest:
        labels.append("target_game: closing lines shown (closing_line_backtest flag)")
    else:
        labels.append("target_game: closing lines hidden (as_of before kickoff)")
        drop += [c for c in CLOSING_LINES if c in df.columns]
    labels.append(f"target_game: temp, wind are {OBSERVED_AS_FORECAST_PROXY}")
    return df.drop(drop), labels


def visible_weekly(
    df: pl.DataFrame, tw: pl.DataFrame, as_of: dt.datetime, team_col: str
) -> pl.DataFrame:
    """BT-01: rows of an undated weekly report whose team-week report time is <= as_of.
    Weeks with no game for that team (byes) have no report time and are left out."""
    keys = tw.select(
        "season", "week", pl.col("team").alias(team_col), pl.col("known_at").alias("_known_at")
    )
    j = df.join(keys, on=["season", "week", team_col], how="inner", maintain_order="left")
    return j.filter(pl.col("_known_at") <= as_of).select(df.columns)


def latest_weekly_chart(
    depth: pl.DataFrame, tw: pl.DataFrame, as_of: dt.datetime, team_col: str = "club_code"
) -> pl.DataFrame:
    """BT-01: week-numbered depth charts (before 2025): each team's latest visible week."""
    vis = visible_weekly(depth, tw, as_of, team_col)
    return vis.filter(pl.col("week") == pl.col("week").max().over(team_col))


def latest_espn_chart(depth: pl.DataFrame, as_of: dt.datetime) -> pl.DataFrame:
    """BT-01: ESPN daily depth charts (2025 on): each team's latest chart dated <= as_of."""
    t = pl.col("dt").str.to_datetime(time_zone="UTC", time_unit="us")
    vis = depth.filter(t <= as_of)
    return vis.filter(t == t.max().over("team"))


def prior_seasons_only(df: pl.DataFrame, target_season: int) -> pl.DataFrame:
    """BT-01: datasets published only after a season ends (participation, DATA-03) or
    describing a whole season (seasonal rosters)."""
    return df.filter(pl.col("season") < target_season)


def ngs_visible(
    ngs: pl.DataFrame, target_season: int, finished_team_weeks: pl.DataFrame
) -> pl.DataFrame:
    """BT-01: Next Gen Stats weekly rows for finished team games. Week 0 (season totals) and
    postseason rows, whose week numbers don't match schedules, only for prior seasons."""
    fin = finished_team_weeks.select(
        "season", "week", pl.col("team").alias("team_abbr"), pl.lit(True).alias("_done")
    ).unique()
    j = ngs.join(fin, on=["season", "week", "team_abbr"], how="left", maintain_order="left")
    this = (
        (pl.col("season") == target_season)
        & (pl.col("week") > 0)
        & (pl.col("season_type") == "REG")
        & pl.col("_done").fill_null(False)
    )
    return j.filter((pl.col("season") < target_season) | this).select(ngs.columns)


def _candle_cc(side: dict[str, str | None] | None) -> int | None:
    close = (side or {}).get("close")
    return None if close is None else dollars_to_cc(close)


def candle_prices_as_of(candles: pl.DataFrame, as_of: dt.datetime) -> pl.DataFrame:
    """BT-01 / BT-04: each market's price as of as_of = its last hourly candle that closed by
    as_of (yes bid, yes ask and last trade at the candle close, in integer centicents)."""
    cut = candles.filter(pl.col("end_period_ts") <= int(as_of.timestamp()))
    last = cut.filter(pl.col("end_period_ts") == pl.col("end_period_ts").max().over("ticker"))
    rows = []
    for r in last.sort("ticker").iter_rows(named=True):
        c = json.loads(r["raw_json"])
        rows.append(
            {
                "ticker": r["ticker"],
                "candle_end_utc": dt.datetime.fromtimestamp(r["end_period_ts"], dt.UTC),
                "yes_bid_cc": _candle_cc(c.get("yes_bid")),
                "yes_ask_cc": _candle_cc(c.get("yes_ask")),
                "last_price_cc": _candle_cc(c.get("price")),
                "volume_fp": c.get("volume"),
                "open_interest_fp": c.get("open_interest"),
            }
        )
    schema: dict[str, pl.DataType | type[pl.DataType]] = {
        "ticker": pl.Utf8,
        "candle_end_utc": _UTC_US,
        "yes_bid_cc": pl.Int64,
        "yes_ask_cc": pl.Int64,
        "last_price_cc": pl.Int64,
        "volume_fp": pl.Utf8,
        "open_interest_fp": pl.Utf8,
    }
    return pl.DataFrame(rows, schema=schema)


def trades_as_of(trades: pl.DataFrame, as_of: dt.datetime) -> pl.DataFrame:
    """BT-01: Kalshi trades created at or before as_of."""
    t = pl.col("created_time").str.to_datetime(time_zone="UTC", time_unit="us")
    return trades.filter(t <= as_of)


def kalshi_ingest_week(markets: pl.DataFrame) -> pl.Series:
    """DATA-08: the NFL week `ge ingest kalshi` pulled a market row for: the nfl_week column,
    or for rows written before it existed, the "week N" at the end of their source."""
    if "nfl_week" in markets.columns:
        return markets["nfl_week"].cast(pl.Int64)
    return markets["source"].str.extract(r"week (\d+)$", 1).cast(pl.Int64).alias("nfl_week")


def market_metadata_only(markets: pl.DataFrame) -> pl.DataFrame:
    """BT-01: a Kalshi market row pulled after as_of, reduced to fields fixed at listing."""
    return markets.select([c for c in markets.columns if c in STATIC_MARKET_COLUMNS])
