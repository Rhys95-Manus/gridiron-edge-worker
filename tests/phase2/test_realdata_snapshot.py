"""BUILD_PLAN Phase 2 acceptance tests on the real downloaded store (data/raw).

Marked realdata: run locally with `uv run pytest -m phase2`; CI has no data. Games are chosen
by rule (hash rank, weekday, format), never typed by hand.

Nothing here reads data at import or collection time: the leakage tests are parametrized by
fixed indices and resolve each index to a game inside the test, so a missing store makes every
case FAIL with a clear message instead of collecting zero cases."""

from __future__ import annotations

import datetime as dt
import functools
import hashlib
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl
import pytest

from ge.config import load_params
from ge.ingest.raw import DATA_ROOT, partitions, read_latest
from ge.store.known_at import default_as_of, report_known_at, with_kickoff
from ge.store.snapshot import SNAPSHOT_DATASETS, snapshot
from tests.phase2.leakage import perturbed_store

pytestmark = pytest.mark.realdata

ET = ZoneInfo("America/New_York")
BT = load_params().backtest
N_LEAKAGE_GAMES = 20  # BUILD_PLAN Phase 2: "20 randomly chosen 2022-2025 games"
PLAY_TABLES = {"pbp": "game_id", "ftn_charting": "nflverse_game_id", "snap_counts": "game_id",
               "player_stats": "game_id"}  # fmt: skip


def _sched(season: int) -> pl.DataFrame:
    try:
        return with_kickoff(read_latest(DATA_ROOT, "schedules", season))
    except FileNotFoundError as exc:
        pytest.fail(f"realdata test needs the local store: {exc}. Run `uv run ge ingest nflverse`.")


def _hash_rank(ids: list[str]) -> list[str]:
    return sorted(ids, key=lambda g: hashlib.sha256(g.encode()).hexdigest())


@functools.cache
def _leakage_games() -> tuple[str, ...]:
    ids = [
        g
        for s in (2022, 2023, 2024, 2025)
        for g in _sched(s).filter(pl.col("result").is_not_null())["game_id"].to_list()
    ]
    return tuple(_hash_rank(ids)[:N_LEAKAGE_GAMES])


def _game(i: int) -> str:
    games = _leakage_games()
    if len(games) < N_LEAKAGE_GAMES:
        pytest.fail(
            f"only {len(games)} completed 2022-2025 games in the store; need {N_LEAKAGE_GAMES}"
        )
    return games[i]


@functools.cache
def _baseline(game_id: str, pass_: str) -> str:
    return snapshot(game_id, pass_=pass_).digest()  # type: ignore[arg-type]


@pytest.mark.parametrize("i", range(N_LEAKAGE_GAMES))
@pytest.mark.parametrize("pass_", ["decision", "inactives"])
@pytest.mark.parametrize("mode", ["delete", "shuffle"])
def test_leakage_future_games_changed_snapshot_identical(
    i: int, pass_: str, mode: str, tmp_path: Path
) -> None:
    game_id = _game(i)
    snap = snapshot(game_id, pass_=pass_)  # type: ignore[arg-type]
    perturbed_store(
        DATA_ROOT,
        tmp_path,
        game_id=game_id,
        as_of=snap.as_of,
        mode=mode,  # type: ignore[arg-type]
        datasets=list(SNAPSHOT_DATASETS),
    )
    other = snapshot(game_id, pass_=pass_, root=tmp_path)  # type: ignore[arg-type]
    assert other.digest() == _baseline(game_id, pass_)


@pytest.mark.parametrize("i", range(N_LEAKAGE_GAMES))
@pytest.mark.parametrize("pass_", ["decision", "inactives"])
def test_no_play_from_the_target_game_or_any_later_game(i: int, pass_: str) -> None:
    game_id = _game(i)
    snap = snapshot(game_id, pass_=pass_)  # type: ignore[arg-type]
    season = int(game_id[:4])
    kick = pl.concat([_sched(s) for s in (season - 1, season)]).select("game_id", "kickoff_utc")
    k0 = kick.filter(pl.col("game_id") == game_id)["kickoff_utc"][0]
    later = set(kick.filter(pl.col("kickoff_utc") >= k0)["game_id"].to_list())
    for table, key in PLAY_TABLES.items():
        ids = set(snap.collect(table)[key].unique().to_list())
        assert game_id not in ids, table
        assert not ids & later, f"{table}: {sorted(ids & later)[:5]}"


def test_same_day_early_games_excluded_at_kickoff_minus_90() -> None:
    s = _sched(2024).with_columns(
        pl.col("kickoff_utc").dt.convert_time_zone("America/New_York").alias("k")
    )
    # A 4 pm ET Sunday game: at kickoff - 90 min the 1 pm games are still being played.
    late = s.filter((pl.col("weekday") == "Sunday") & (pl.col("k").dt.hour() == 16))
    target = late.filter(pl.col("game_id") == _hash_rank(late["game_id"].to_list())[0]).row(
        0, named=True
    )
    snap = snapshot(target["game_id"], pass_="inactives")
    ends = (
        read_latest(DATA_ROOT, "pbp", 2024)
        .select("game_id", pl.col("time_of_day").str.to_datetime(time_zone="UTC", time_unit="us"))
        .group_by("game_id")
        .agg(pl.col("time_of_day").max().alias("end"))
    )
    early = s.filter(
        (pl.col("gameday") == target["gameday"]) & (pl.col("kickoff_utc") < target["kickoff_utc"])
    ).join(ends, on="game_id")
    running = set(early.filter(pl.col("end") > snap.as_of)["game_id"].to_list())
    done = set(early.filter(pl.col("end") <= snap.as_of)["game_id"].to_list())
    assert running, "expected same-day games still in progress at kickoff - 90 min"
    ids = set(snap.collect("pbp")["game_id"].unique().to_list())
    assert not ids & running
    assert done <= ids
    # Once they have finished (kickoff + 12 h), the same game's snapshot does see them.
    after = snapshot(target["game_id"], as_of=target["kickoff_utc"] + dt.timedelta(hours=12))
    assert running <= set(after.collect("pbp")["game_id"].unique().to_list())


@pytest.mark.parametrize("i", range(3))
def test_same_snapshot_twice_is_identical(i: int) -> None:
    game_id = _game(i)
    a, b = snapshot(game_id), snapshot(game_id)
    assert a.digest() == b.digest()
    for t in a.tables:
        assert a.collect(t).equals(b.collect(t)), t
    assert a.labels == b.labels and a.vintages == b.vintages


def test_target_game_never_shows_scores_and_hides_closing_lines() -> None:
    g = _game(0)
    tgt = snapshot(g).collect("target_game")
    assert tgt.height == 1
    assert not {"home_score", "away_score", "result", "total"} & set(tgt.columns)
    assert "spread_line" not in tgt.columns
    flagged = snapshot(g, closing_line_backtest=True).collect("target_game")
    assert "spread_line" in flagged.columns
    assert any("observed_as_forecast_proxy" in lb for lb in snapshot(g).labels)


def _depth_game(season: int) -> dict:
    s = _sched(season).filter(pl.col("result").is_not_null())
    return s.filter(pl.col("game_id") == _hash_rank(s["game_id"].to_list())[0]).row(0, named=True)


def test_depth_chart_2023_week_format() -> None:
    g = _depth_game(2023)
    snap = snapshot(g["game_id"])
    got = snap.collect("depth_charts")
    raw = read_latest(DATA_ROOT, "depth_charts", 2023)
    s = _sched(2023)
    for team in (g["home_team"], g["away_team"]):
        games = pl.concat(
            [s.filter(pl.col("home_team") == team), s.filter(pl.col("away_team") == team)]
        )
        visible = [
            r["week"]
            for r in games.iter_rows(named=True)
            if report_known_at(r["kickoff_utc"], BT) <= snap.as_of
        ]
        have = set(raw.filter(pl.col("club_code") == team)["week"].to_list())
        want = max(w for w in visible if w in have)
        mine = got.filter(pl.col("club_code") == team)
        assert set(mine["week"].to_list()) == {want}, team
        assert (
            mine.height
            == raw.filter((pl.col("club_code") == team) & (pl.col("week") == want)).height
        )
    assert any("12 noon ET" in lb or "assumed" in lb for lb in snap.labels)


def test_depth_chart_2026_espn_format() -> None:
    g = _depth_game(2026)
    snap = snapshot(g["game_id"])
    got = snap.collect("depth_charts")
    raw = read_latest(DATA_ROOT, "depth_charts", 2026).with_columns(
        pl.col("dt").str.to_datetime(time_zone="UTC", time_unit="us").alias("_t")
    )
    for team in (g["home_team"], g["away_team"]):
        mine = raw.filter((pl.col("team") == team) & (pl.col("_t") <= snap.as_of))
        want = mine.sort("_t")["dt"][-1]
        g_rows = got.filter(pl.col("team") == team)
        assert set(g_rows["dt"].to_list()) == {want}, team
        assert g_rows.height == mine.filter(pl.col("dt") == want).height


def _own_injury_pulls() -> tuple[dt.datetime, dt.datetime, int]:
    """Two of our own 2026 injury pulls: one on a Tuesday (ET) and one on the Friday or
    Saturday after it. Returns (tuesday_pull, weekend_pull, week)."""
    pulls = [
        dt.datetime.strptime(p.name.split("=", 1)[1], "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.UTC)
        for p in partitions(DATA_ROOT, "injuries", 2026)
    ]
    for tue in pulls:
        if tue.astimezone(ET).strftime("%A") != "Tuesday":
            continue
        for later in pulls:
            gap = (later.astimezone(ET).date() - tue.astimezone(ET).date()).days
            if later.astimezone(ET).strftime("%A") in ("Friday", "Saturday") and 0 < gap <= 4:
                inj = pl.read_parquet(
                    next(
                        p
                        for p in partitions(DATA_ROOT, "injuries", 2026)
                        if p.name.endswith(later.strftime("%Y%m%dT%H%M%SZ"))
                    )
                    / "part.parquet"
                )
                week = int(inj["week"].max())
                return tue, later, week
    pytest.fail(
        "needs two of our own 2026 injury pulls: a Tuesday pull and a Friday/Saturday pull after "
        f"it. Have: {[p.isoformat() for p in pulls]}. After Friday's report, run "
        "`uv run ge ingest nflverse --seasons 2026 --datasets injuries`."
    )


def test_friday_out_seen_saturday_not_tuesday() -> None:
    tue, weekend, week = _own_injury_pulls()
    s = _sched(2026)
    inj = pl.read_parquet(
        next(
            p
            for p in partitions(DATA_ROOT, "injuries", 2026)
            if p.name.endswith(weekend.strftime("%Y%m%dT%H%M%SZ"))
        )
        / "part.parquet"
    )
    day = weekend.astimezone(ET).date()
    saturday = day if day.strftime("%A") == "Saturday" else day + dt.timedelta(days=1)
    sat = max(weekend, dt.datetime.combine(saturday, dt.time(0), ET).astimezone(dt.UTC))
    games = s.filter((pl.col("week") == week) & (pl.col("kickoff_utc") > sat))
    outs = inj.filter((pl.col("week") == week) & (pl.col("report_status") == "Out"))
    outs = outs.join(
        pl.concat(
            [games.select("game_id", pl.col(c).alias("team")) for c in ("home_team", "away_team")]
        ),
        on="team",
    )
    assert outs.height, f"no Out players in week {week} for games after {sat.isoformat()}"
    p = outs.sort("gsis_id").row(0, named=True)
    key = (pl.col("gsis_id") == p["gsis_id"]) & (pl.col("week") == week)
    on_sat = snapshot(p["game_id"], as_of=sat).collect("injuries").filter(key)
    assert on_sat["report_status"].to_list() == ["Out"]
    on_tue = snapshot(p["game_id"], as_of=tue).collect("injuries").filter(key)
    assert on_tue.is_empty()


def test_kalshi_prices_as_of_from_real_2025_candles() -> None:
    assert partitions(DATA_ROOT, "kalshi_candles", 2025), (
        "run `uv run ge ingest kalshi --season 2025 --week 10 --history` first"
    )
    s = _sched(2025).filter(pl.col("week") == 10)
    g = s.sort(["gameday", "gametime"]).row(-1, named=True)
    snap = snapshot(g["game_id"])
    prices = snap.collect("kalshi_prices")
    assert prices.height, "no Kalshi prices as of kickoff - 24 h"
    assert prices["yes_bid_cc"].dtype == pl.Int64
    assert (prices["candle_end_utc"] <= snap.as_of).all()
    assert default_as_of(g["kickoff_utc"], "decision", BT) == snap.as_of
    candles = snap.collect("kalshi_candles")
    assert (candles["end_period_ts"] <= int(snap.as_of.timestamp())).all()
    mk = snap.collect("kalshi_markets")
    assert "raw_json" not in mk.columns and "status" not in mk.columns
