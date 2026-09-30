"""BT-01 point-in-time snapshot: every input a later phase may use for one game, as it stood
at as_of, with the assumptions it relied on and a byte-level digest.

A snapshot reads the target season and the season before it: last season's values are the
prior in weeks 1-4 (G4). Earlier seasons are for parameter fitting (BT-02), not per-game inputs.

Data: nflverse; charting: FTN Data via nflverse."""

from __future__ import annotations

import datetime as dt
import hashlib
import io
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

from ge.config import Backtest, load_params
from ge.ingest.raw import DATA_ROOT
from ge.store import known_at as ka
from ge.store.vintage import Version, choose_version, observations

GAME_KEYED = {
    "pbp": "game_id",
    "ftn_charting": "nflverse_game_id",
    "snap_counts": "game_id",
    "player_stats": "game_id",
}
NGS = ("nextgen_passing", "nextgen_receiving", "nextgen_rushing")
WEEKLY_REPORTS = {"injuries": "team", "rosters_weekly": "team"}
PRIOR_SEASON_ONLY = ("participation", "rosters")
NWS = ("nws_hourly", "nws_game_status")
KALSHI = ("kalshi_markets", "kalshi_orderbook", "kalshi_candles", "kalshi_trades")
SNAPSHOT_DATASETS = (
    "schedules",
    *GAME_KEYED,
    *NGS,
    *WEEKLY_REPORTS,
    *PRIOR_SEASON_ONLY,
    "depth_charts",
    *NWS,
    *KALSHI,
)
# Output tables, in digest order.
TABLES = (
    "target_game",
    "schedules",
    *GAME_KEYED,
    *NGS,
    "participation",
    "injuries",
    "rosters_weekly",
    "rosters",
    "depth_charts",
    *NWS,
    "kalshi_markets",
    "kalshi_orderbook",
    "kalshi_candles",
    "kalshi_prices",
    "kalshi_trades",
)
ATTRIBUTION = "Data: nflverse; charting: FTN Data via nflverse"

Loader = Callable[[], pl.DataFrame]


@dataclass(frozen=True)
class Snapshot:
    """BT-01: tables are loaded on first use; digest() hashes them in a fixed order."""

    game_id: str
    season: int
    week: int
    kickoff_utc: dt.datetime
    as_of: dt.datetime
    pass_: str
    closing_line_backtest: bool
    labels: tuple[str, ...]
    vintages: tuple[str, ...]
    _loaders: dict[str, Loader] = field(repr=False, compare=False)
    _cache: dict[str, pl.DataFrame] = field(default_factory=dict, repr=False, compare=False)

    @property
    def tables(self) -> tuple[str, ...]:
        return TABLES

    def collect(self, table: str) -> pl.DataFrame:
        if table not in self._loaders:
            raise KeyError(f"no table {table!r}; tables are {TABLES}")
        if table not in self._cache:
            self._cache[table] = self._loaders[table]()
        return self._cache[table]

    def digest(self) -> str:
        """BT-01: sha256 over the header and every table, each sorted by all its columns and
        written canonically, so row order and file layout don't matter."""
        h = hashlib.sha256()
        header = [
            self.game_id,
            self.as_of.isoformat(),
            self.pass_,
            str(self.closing_line_backtest),
            *self.labels,
            *self.vintages,
        ]
        h.update("\n".join(header).encode())
        for t in TABLES:
            h.update(f"\n#{t}\n".encode())
            h.update(_canonical_bytes(self.collect(t)))
        return h.hexdigest()


def _canonical_bytes(df: pl.DataFrame) -> bytes:
    """Uncompressed Parquet without statistics. Not Arrow IPC: IPC copies whatever bytes sit
    under null slots and in string-view buffers, which depend on the file the data came from,
    so equal frames can serialize differently. Parquet stores no values for nulls."""
    sortable = [c for c, d in df.schema.items() if not d.is_nested()]
    out = df.sort(sortable, nulls_last=True, maintain_order=True) if sortable else df
    buf = io.BytesIO()
    out.rechunk().write_parquet(buf, compression="uncompressed", statistics=False)
    return buf.getvalue()


def _read(v: Version | None, columns: list[str] | None = None) -> pl.LazyFrame | None:
    if v is None:
        return None
    lf = pl.scan_parquet(v.path)
    return lf.select(columns) if columns else lf


def _concat(frames: list[pl.LazyFrame | None]) -> pl.DataFrame:
    got = [f for f in frames if f is not None]
    return pl.concat([f.collect() for f in got], how="diagonal_relaxed") if got else pl.DataFrame()


def snapshot(
    game_id: str,
    as_of: dt.datetime | None = None,
    *,
    pass_: ka.Pass = "decision",
    closing_line_backtest: bool = False,
    root: Path = DATA_ROOT,
    bt: Backtest | None = None,
) -> Snapshot:
    """BT-01: the inputs for `game_id` as they stood at `as_of` (default: from `pass_`)."""
    bt = bt or load_params().backtest
    season = int(game_id.split("_", 1)[0])
    seasons = (season - 1, season)

    latest = choose_version(root, "schedules", season, dt.datetime.max.replace(tzinfo=dt.UTC))
    if latest is None:
        raise FileNotFoundError(f"no {season} schedules under {root}")
    first_look = ka.with_kickoff(pl.read_parquet(latest.path)).filter(pl.col("game_id") == game_id)
    if first_look.is_empty():
        raise KeyError(f"{game_id} is not in the {season} schedules")
    if as_of is None:
        as_of = ka.default_as_of(first_look["kickoff_utc"][0], pass_, bt)
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must be timezone-aware")
    as_of = as_of.astimezone(dt.UTC)

    labels: list[str] = []
    versions: dict[tuple[str, int], Version | None] = {
        (ds, s): choose_version(root, ds, s, as_of)
        for ds in (
            "schedules",
            *GAME_KEYED,
            *NGS,
            *WEEKLY_REPORTS,
            *PRIOR_SEASON_ONLY,
            "depth_charts",
        )
        for s in seasons
    }

    # Schedules and the game index.
    sched = ka.with_kickoff(_concat([_read(versions[("schedules", s)]) for s in seasons]))
    target = sched.filter(pl.col("game_id") == game_id)
    if target.is_empty():
        raise KeyError(f"{game_id} missing from the schedules version read at {as_of}")
    kickoff = target["kickoff_utc"][0]
    week = int(target["week"][0])
    started = sched.filter(pl.col("kickoff_utc") < as_of)["game_id"].to_list()
    times = _concat([_read(versions[("pbp", s)], ["game_id", "time_of_day"]) for s in seasons])
    ends = (
        ka.game_ends(times.filter(pl.col("game_id").is_in(started)))
        if times.height
        else pl.DataFrame(schema={"game_id": pl.Utf8, "game_end_utc": pl.Datetime("us", "UTC")})
    )
    games = sched.select("game_id", "season", "week", "home_team", "away_team", "kickoff_utc").join(
        ends, on="game_id", how="left"
    )
    finished = ka.finished_game_ids(games, as_of, game_id)
    labels.append(
        "plays and game stats: only games whose last play (pbp time_of_day) was run by as_of"
    )
    fin_tw = pl.concat(
        [
            games.filter(pl.col("game_id").is_in(finished)).select(
                "season", "week", pl.col(c).alias("team")
            )
            for c in ("home_team", "away_team")
        ]
    )
    tw = ka.team_weeks(sched, bt)
    target_row, target_labels = ka.mask_target_schedule(
        target, as_of, closing_line_backtest=closing_line_backtest
    )
    labels += target_labels

    loaders: dict[str, Loader] = {
        "target_game": lambda: target_row,
        "schedules": lambda: sched.filter(pl.col("game_id").is_in(finished)).drop("kickoff_utc"),
    }

    def game_keyed(ds: str, key: str) -> Loader:
        return lambda: _concat(
            [
                lf.filter(pl.col(key).is_in(finished))
                if (lf := _read(versions[(ds, s)])) is not None
                else None
                for s in seasons
            ]
        )

    for ds, key in GAME_KEYED.items():
        loaders[ds] = game_keyed(ds, key)

    def ngs(ds: str) -> Loader:
        return lambda: ka.ngs_visible(
            _concat([_read(versions[(ds, s)]) for s in seasons]), season, fin_tw
        )

    for ds in NGS:
        loaders[ds] = ngs(ds)
    labels.append("nextgen: week 0 (season totals) and postseason rows only from prior seasons")

    def prior_only(ds: str) -> Loader:
        # Only the prior season's partition is read (participation has no season column).
        return lambda: _concat([_read(versions[(ds, season - 1)])])

    for ds in PRIOR_SEASON_ONLY:
        loaders[ds] = prior_only(ds)
    labels.append(
        "participation (published after the season) and seasonal rosters: prior seasons only"
    )

    assumed = (
        f"assumed known at {int(bt.bt_01_assumed_report_hour_et.value)}:00 ET, "
        f"{int(bt.bt_01_assumed_report_days_before_kickoff.value)} day(s) before the team's "
        "kickoff (stated assumption, BT-01)"
    )

    def weekly(ds: str, team_col: str) -> Loader:
        def load() -> pl.DataFrame:
            parts = []
            for s in seasons:
                v = versions[(ds, s)]
                lf = _read(v)
                if lf is None or v is None:
                    continue
                df = lf.collect()
                parts.append(ka.visible_weekly(df, tw, as_of, team_col) if v.after_as_of else df)
            return pl.concat(parts, how="diagonal_relaxed") if parts else pl.DataFrame()

        return load

    for ds, col in WEEKLY_REPORTS.items():
        loaders[ds] = weekly(ds, col)
        for s in seasons:
            v = versions[(ds, s)]
            if v is not None and v.after_as_of:
                labels.append(f"{ds} {s}: no publish time before our own pulls; {assumed}")
            elif v is not None:
                labels.append(f"{ds} {s}: our own pull at {v.pulled_at.isoformat()} decides")

    dv = versions[("depth_charts", season)]

    def depth() -> pl.DataFrame:
        lf = _read(dv)
        if lf is None or dv is None:
            return pl.DataFrame()
        df = lf.collect()
        if "dt" in df.columns:
            return ka.latest_espn_chart(df, as_of)
        if dv.after_as_of:
            return ka.latest_weekly_chart(df, tw, as_of)
        return df.filter(pl.col("week") == pl.col("week").max().over("club_code"))

    loaders["depth_charts"] = depth
    if dv is not None:
        if dv.after_as_of and dv.path.exists() and "dt" not in pl.read_parquet_schema(dv.path):
            labels.append(f"depth_charts {season}: week-numbered chart, {assumed}")
        else:
            labels.append(f"depth_charts {season}: latest chart dated on or before as_of")

    # NWS forecasts: the latest pull at or before as_of that covers this game.
    def nws(ds: str) -> Loader:
        def load() -> pl.DataFrame:
            for v in reversed(observations(root, ds, season, as_of)):
                df = pl.read_parquet(v.path).filter(pl.col("game_id") == game_id)
                if df.height:
                    return df
            return pl.DataFrame()

        return load

    for ds in NWS:
        loaders[ds] = nws(ds)

    # Kalshi: the markets `ge ingest kalshi` pulled for the target week; prices from rows
    # timed at or before as_of.
    all_mk = observations(root, "kalshi_markets", season, None)

    def markets() -> pl.DataFrame:
        before = [v for v in all_mk if v.pulled_at <= as_of]
        after = [v for v in all_mk if v.pulled_at > as_of]
        order = list(reversed(before)) + after  # prefer the latest pull <= as_of, else earliest
        seen: dict[str, dict[str, object]] = {}
        for v in order:
            raw = pl.read_parquet(v.path)
            in_week = ka.kalshi_ingest_week(raw) == week
            for r in ka.market_metadata_only(raw.filter(in_week)).iter_rows(named=True):
                seen.setdefault(str(r["ticker"]), r)
        if not seen:
            return pl.DataFrame(schema={c: pl.Utf8 for c in ka.STATIC_MARKET_COLUMNS})
        return pl.DataFrame(list(seen.values()), infer_schema_length=None).sort("ticker")

    mk_cache: dict[str, pl.DataFrame] = {}

    def markets_cached() -> pl.DataFrame:
        if "m" not in mk_cache:
            mk_cache["m"] = markets()
        return mk_cache["m"]

    def orderbook() -> pl.DataFrame:
        obs = observations(root, "kalshi_orderbook", season, as_of)
        if not obs:
            return pl.DataFrame()
        ids = markets_cached()["ticker"].to_list()
        return pl.read_parquet(obs[-1].path).filter(pl.col("ticker").is_in(ids))

    def candles() -> pl.DataFrame:
        ids = markets_cached()["ticker"].to_list()
        frames = [
            pl.read_parquet(v.path)
            .filter(pl.col("ticker").is_in(ids))
            .filter(pl.col("end_period_ts") <= int(as_of.timestamp()))
            # a candle counts only if its hour had closed when we pulled it
            .filter(pl.col("end_period_ts") <= int(v.pulled_at.timestamp()))
            for v in observations(root, "kalshi_candles", season, None)
        ]
        if not frames:
            return pl.DataFrame()
        df = pl.concat(frames, how="diagonal_relaxed")
        return df.sort("pulled_at").unique(["ticker", "end_period_ts"], keep="last")

    def trades() -> pl.DataFrame:
        ids = markets_cached()["ticker"].to_list()
        frames = [
            ka.trades_as_of(pl.read_parquet(v.path).filter(pl.col("ticker").is_in(ids)), as_of)
            for v in observations(root, "kalshi_trades", season, None)
        ]
        if not frames:
            return pl.DataFrame()
        df = pl.concat(frames, how="diagonal_relaxed")
        return df.sort("pulled_at").unique(["trade_id"], keep="last")

    def prices() -> pl.DataFrame:
        c = candles()
        return (
            ka.candle_prices_as_of(c, as_of)
            if c.height
            else ka.candle_prices_as_of(
                pl.DataFrame(
                    schema={"ticker": pl.Utf8, "raw_json": pl.Utf8, "end_period_ts": pl.Int64}
                ),
                as_of,
            )
        )

    loaders["kalshi_markets"] = markets_cached
    loaders["kalshi_orderbook"] = orderbook
    loaders["kalshi_candles"] = candles
    loaders["kalshi_prices"] = prices
    loaders["kalshi_trades"] = trades
    labels.append(
        "kalshi: every market pulled for the target week (game mapping is Phase 6); market "
        "rows keep listing fields only; prices = last hourly candle closed by as_of"
    )

    vint = sorted({v.label for v in versions.values() if v is not None})
    for v in sorted(
        {v for v in versions.values() if v is not None and v.after_as_of}, key=lambda v: v.label
    ):
        labels.append(
            f"{v.dataset} {v.season}: read as nflverse published it at {v.pulled_at.isoformat()} "
            "(after as_of; includes later corrections)"
        )
    return Snapshot(
        game_id=game_id,
        season=season,
        week=week,
        kickoff_utc=kickoff,
        as_of=as_of,
        pass_=pass_,
        closing_line_backtest=closing_line_backtest,
        labels=tuple(labels),
        vintages=tuple(vint),
        _loaders=loaders,
    )
