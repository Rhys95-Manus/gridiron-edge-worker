"""BT-01 leakage harness: a copy of the raw store with everything at or after a target game
deleted or shuffled. What counts as "after" is decided here from kickoff order and row
timestamps only, independently of ge.store's known-at rules, so the test can't agree with a
bug by construction.

The copy holds the target season and the season before it (what a snapshot reads, G4); later
seasons are left out, which deletes them in both modes."""

from __future__ import annotations

import datetime as dt
import hashlib
import os
import shutil
from pathlib import Path
from typing import Literal

import numpy as np
import polars as pl

from ge.ingest.nflverse import SEASONLESS
from ge.ingest.raw import partitions
from ge.store.known_at import CLOSING_LINES, TARGET_NEVER, with_kickoff

Mode = Literal["delete", "shuffle"]

GAME_KEY = {
    "pbp": "game_id",
    "ftn_charting": "nflverse_game_id",
    "participation": "nflverse_game_id",
    "snap_counts": "game_id",
    "player_stats": "game_id",
}
TEAM_WEEK_KEY = {
    "injuries": "team",
    "rosters_weekly": "team",
    "depth_charts": "club_code",  # week-numbered format; the ESPN format is cut by dt
    "nextgen_passing": "team_abbr",
    "nextgen_receiving": "team_abbr",
    "nextgen_rushing": "team_abbr",
}
PULL_TIMED = ("nws_hourly", "nws_game_status", "kalshi_orderbook")
MARKET_PRICE_FIELDS = ("status", "close_time", "yes_ask_cc", "no_ask_cc", "volume_fp", "raw_json")
_TS = "%Y%m%dT%H%M%SZ"


def _link(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def _rng(key: str) -> np.random.Generator:
    return np.random.default_rng(int(hashlib.sha256(key.encode()).hexdigest()[:16], 16))


def _permute_columns(df: pl.DataFrame, cols: list[str], rng: np.random.Generator) -> pl.DataFrame:
    if df.height < 2:
        return df
    return df.with_columns(df[c].gather(rng.permutation(df.height).tolist()) for c in cols)


# Identity and time columns stay put when shuffling, so a future row stays in the future;
# every other value moves to a different future row.
KEEP = {
    "game_id", "nflverse_game_id", "season", "week", "season_type", "game_type", "team",
    "club_code", "team_abbr", "gameday", "gametime", "weekday", "home_team", "away_team",
    "time_of_day", "dt", "ticker", "end_period_ts", "created_time", "trade_id", "pulled_at",
    "source",
}  # fmt: skip


def _scramble(
    df: pl.DataFrame, mask: pl.Series, mode: Mode, rng: np.random.Generator
) -> pl.DataFrame:
    """delete: drop the masked rows. shuffle: permute each value column independently among
    the masked rows (values land on the wrong games and players), then shuffle row order."""
    if not mask.any():
        return df
    if mode == "delete":
        return df.filter(~mask)
    hit = _permute_columns(df.filter(mask), [c for c in df.columns if c not in KEEP], rng)
    out = pl.concat([df.filter(~mask), hit], how="vertical")
    return out[rng.permutation(out.height).tolist()]


def perturbed_store(
    src: Path, dst: Path, *, game_id: str, as_of: dt.datetime, mode: Mode, datasets: list[str]
) -> None:
    rng = _rng(f"{game_id}/{as_of.isoformat()}/{mode}")
    season = int(game_id[:4])
    sched = with_kickoff(pl.read_parquet(partitions(src, "schedules", season)[-1] / "part.parquet"))
    tgt = sched.filter(pl.col("game_id") == game_id).row(0, named=True)
    k0, week0 = tgt["kickoff_utc"], tgt["week"]
    late_ids = set(sched.filter(pl.col("kickoff_utc") >= k0)["game_id"].to_list())
    # Games that kicked off earlier but were still being played at as_of.
    if "pbp" in datasets:
        pbp_path = partitions(src, "pbp", season)[-1] / "part.parquet"
        ends = (
            pl.read_parquet(pbp_path, columns=["game_id", "time_of_day"])
            .with_columns(pl.col("time_of_day").str.to_datetime(time_zone="UTC", time_unit="us"))
            .group_by("game_id")
            .agg(pl.col("time_of_day").max())
        )
        late_ids |= set(ends.filter(pl.col("time_of_day") > as_of)["game_id"].to_list())
    for ds in datasets:
        # Seasonless datasets (the DATA-04 player ID crosswalk) hold no game information;
        # they are copied unchanged.
        for part in partitions(src, ds, SEASONLESS):
            _link(
                part / "part.parquet",
                dst / ds / f"season={SEASONLESS}" / part.name / "part.parquet",
            )
        for s in (season - 1, season):
            for part in partitions(src, ds, s):
                src_file = part / "part.parquet"
                out = dst / ds / f"season={s}" / part.name / "part.parquet"
                pulled = dt.datetime.strptime(part.name.split("=", 1)[1], _TS).replace(
                    tzinfo=dt.UTC
                )
                df = pl.read_parquet(src_file)
                new = _perturb(
                    ds,
                    df,
                    s == season,
                    pulled,
                    as_of,
                    rng,
                    mode,
                    game_id,
                    late_ids,
                    week0,
                )
                if new is None:
                    continue
                if new is df:
                    _link(src_file, out)
                else:
                    out.parent.mkdir(parents=True, exist_ok=True)
                    new.write_parquet(out)


def _perturb(
    ds: str,
    df: pl.DataFrame,
    target_season: bool,
    pulled: dt.datetime,
    as_of: dt.datetime,
    rng: np.random.Generator,
    mode: Mode,
    game_id: str,
    late_ids: set[str],
    week0: int,
) -> pl.DataFrame | None:
    everything = pl.Series([True] * df.height)
    if ds in PULL_TIMED:
        if pulled <= as_of:
            return df
        return None if mode == "delete" else _scramble(df, everything, mode, rng)
    if ds == "kalshi_markets":
        if pulled <= as_of:
            return df
        cols = [c for c in MARKET_PRICE_FIELDS if c in df.columns]
        if mode == "delete":
            return df.with_columns(pl.lit(None, dtype=df[c].dtype).alias(c) for c in cols)
        return _permute_columns(df, cols, rng)
    if ds == "kalshi_candles":
        return _scramble(df, df["end_period_ts"] > int(as_of.timestamp()), mode, rng)
    if ds == "kalshi_trades":
        t = df["created_time"].str.to_datetime(time_zone="UTC", time_unit="us")
        return _scramble(df, t > as_of, mode, rng)
    if not target_season:
        return df
    if ds == "schedules":
        # A later game's existence and kickoff are published in advance, so its identity and
        # time columns stay; everything else (scores, lines, weather, QBs...) is deleted
        # (nulled) or shuffled among later games.
        late = df["game_id"].is_in(list(late_ids - {game_id}))
        if mode == "delete":
            vals = [c for c in df.columns if c not in KEEP]
            df = df.with_columns(
                pl.when(late).then(pl.lit(None, dtype=df[c].dtype)).otherwise(pl.col(c)).alias(c)
                for c in vals
            )
        else:
            df = _scramble(df, late, mode, rng)
        is_t = df["game_id"] == game_id
        fake = [c for c in (*TARGET_NEVER, *CLOSING_LINES) if c in df.columns]
        other = df.filter(~is_t)
        donor = other[int(rng.integers(other.height))]  # another game's values
        return df.with_columns(
            pl.when(is_t)
            .then(
                pl.lit(None, dtype=df[c].dtype)
                if mode == "delete"
                else pl.lit(donor[c][0], dtype=df[c].dtype)
            )
            .otherwise(pl.col(c))
            .alias(c)
            for c in fake
        )
    if ds in GAME_KEY:
        return _scramble(df, df[GAME_KEY[ds]].is_in(list(late_ids)), mode, rng)
    if ds == "depth_charts" and "dt" in df.columns:
        t = df["dt"].str.to_datetime(time_zone="UTC", time_unit="us")
        return _scramble(df, t > as_of, mode, rng)
    if ds in TEAM_WEEK_KEY:
        # Only later weeks: a same-week report for a team kicking off after the target is
        # published before the target's as_of (e.g. Friday's report for a late Sunday game).
        # Week 0 (NGS season totals) is end-of-season data.
        mask = ((df["week"] > week0) | (df["week"] == 0)).fill_null(False)
        return _scramble(df, mask, mode, rng)
    return df
