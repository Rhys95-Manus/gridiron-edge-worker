"""BT-01 availability for ff_opportunity (DATA-04; spec synced 2026-10-16): one file per
season, rebuilt whole by ffverse, no per-game publish time. Before our own pulls, a game's rows
count as known at 12 noon ET on the day after its last play (ET date), labelled; from our own
pulls on, pulled_at decides. Either way only games whose last play was run by as_of are shown.

Runs on the Phase 3 fixture store, whose ff_opportunity slice was pulled after its games (so the
history rule applies), and on copies of it with an earlier pull planted (our own pull)."""

from __future__ import annotations

import datetime as dt
import shutil
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl

from ge.config import load_params
from ge.store import known_at as ka
from ge.store.snapshot import FF_OPPORTUNITY_COLUMNS, TABLES, snapshot
from tests.phase3.conftest import MAIN_WEEK, SEASON, STORE, store_table

ET = ZoneInfo("America/New_York")
BT = load_params().backtest
FF = "ff_opportunity"
SPEC_COLUMNS = (
    "game_id", "player_id", "posteam", "position", "rec_attempt", "rush_attempt", "receptions",
    "receptions_exp", "rec_yards_gained", "rec_yards_gained_exp", "rush_yards_gained",
    "rush_yards_gained_exp", "rec_touchdown", "rec_touchdown_exp", "rush_touchdown",
    "rush_touchdown_exp",
)  # fmt: skip


def _et(y: int, mo: int, d: int, h: int, mi: int = 0) -> dt.datetime:
    return dt.datetime(y, mo, d, h, mi, tzinfo=ET).astimezone(dt.UTC)


# ---- the rule itself ----


def test_known_at_is_noon_et_the_day_after_the_last_play() -> None:
    assert BT.bt_01_ff_opportunity_known_hour_et.value == 12
    end = _et(2024, 10, 27, 23, 30)  # Sunday night
    assert ka.ff_opportunity_known_at(end, BT) == _et(2024, 10, 28, 12)


def test_known_at_uses_the_et_date_of_the_last_play() -> None:
    # A game ending after midnight ET belongs to that later ET date.
    end = _et(2024, 10, 29, 0, 20)
    assert ka.ff_opportunity_known_at(end, BT) == _et(2024, 10, 30, 12)


def test_known_at_across_the_dst_change() -> None:
    # 2024-11-03 is the end of US daylight time: noon EST on Nov 4 is 17:00 UTC.
    end = _et(2024, 11, 3, 16, 30)
    got = ka.ff_opportunity_known_at(end, BT)
    assert got == dt.datetime(2024, 11, 4, 17, 0, tzinfo=dt.UTC)


# ---- snapshots on the fixture store (history before our own pulls) ----


def _games() -> pl.DataFrame:
    """Schedules of the fixture season with kickoff and last-play time (from pbp)."""
    sched = ka.with_kickoff(store_table("schedules", SEASON))
    ends = ka.game_ends(store_table("pbp", SEASON).select("game_id", "time_of_day"))
    return sched.join(ends, on="game_id", how="left")


def _late_target() -> tuple[str, dt.datetime, list[str]]:
    """By rule: the latest-kicking-off week-MAIN_WEEK game, and the games whose last play fell
    on the ET date before its kickoff date."""
    g = _games()
    tgt = g.filter(pl.col("week") == MAIN_WEEK).sort("kickoff_utc", "game_id").row(-1, named=True)
    k_date = tgt["kickoff_utc"].astimezone(ET).date()
    prev = g.filter(
        pl.col("game_end_utc").is_not_null()
        & (pl.col("game_end_utc").dt.convert_time_zone("America/New_York").dt.date()
           == k_date - dt.timedelta(days=1))
    )["game_id"].to_list()  # fmt: skip
    assert prev, "fixture has no game ending the day before the target's kickoff"
    return tgt["game_id"], tgt["kickoff_utc"], sorted(prev)


def test_fixture_slice_was_pulled_after_its_games() -> None:
    _, kickoff, _ = _late_target()
    snap = snapshot(_late_target()[0], root=STORE)
    v = [x for x in snap.vintages if x.startswith(f"{FF}/{SEASON}@")]
    assert v and "vintage_after_as_of" in v[0], snap.vintages
    assert kickoff > snap.as_of


def test_history_rule_hides_games_until_noon_the_next_day() -> None:
    gid, kickoff, prev = _late_target()
    noon = dt.datetime.combine(kickoff.astimezone(ET).date(), dt.time(12), ET).astimezone(dt.UTC)
    assert noon < kickoff
    before = snapshot(gid, as_of=noon - dt.timedelta(minutes=1), root=STORE).collect(FF)
    at = snapshot(gid, as_of=noon, root=STORE).collect(FF)
    assert not set(prev) & set(before["game_id"].to_list())
    assert set(prev) <= set(at["game_id"].to_list())
    # Games that ended two or more days earlier are visible either way.
    older = set(at["game_id"].to_list()) - set(prev)
    assert older and older <= set(before["game_id"].to_list())


def test_history_rule_is_labelled() -> None:
    gid, _, _ = _late_target()
    labels = " | ".join(snapshot(gid, root=STORE).labels)
    assert f"{FF} {SEASON}: no per-game publish time before our own pulls" in labels
    assert "12 noon ET on the day after the game's last play" in labels


def test_only_spec_columns_are_exposed() -> None:
    assert FF in TABLES
    assert tuple(FF_OPPORTUNITY_COLUMNS) == SPEC_COLUMNS
    gid, _, _ = _late_target()
    df = snapshot(gid, root=STORE).collect(FF)
    assert tuple(df.columns) == SPEC_COLUMNS
    assert df.height > 0


def test_no_row_from_the_target_game_or_later() -> None:
    gid, kickoff, _ = _late_target()
    snap = snapshot(gid, root=STORE)
    shown = set(snap.collect(FF)["game_id"].to_list())
    g = _games()
    late = set(g.filter(pl.col("kickoff_utc") >= kickoff)["game_id"].to_list())
    unfinished = set(
        g.filter(pl.col("game_end_utc").is_null() | (pl.col("game_end_utc") > snap.as_of))[
            "game_id"
        ].to_list()
    )
    assert gid in late
    assert not shown & (late | unfinished)


def test_prior_season_rows_are_all_visible() -> None:
    gid, _, _ = _late_target()
    shown = snapshot(gid, root=STORE).collect(FF)
    prior = store_table(FF, SEASON - 1)
    prior = prior.filter(pl.col("game_id").str.starts_with(f"{SEASON - 1}_"))
    assert set(prior["game_id"].to_list()) <= set(shown["game_id"].to_list())


def test_same_snapshot_twice_is_identical() -> None:
    gid, _, _ = _late_target()
    assert snapshot(gid, root=STORE).digest() == snapshot(gid, root=STORE).digest()


# ---- our own pulls: pulled_at decides ----


def _with_own_pull(tmp: Path, pulled: dt.datetime, drop_game: str | None) -> Path:
    """A copy of the fixture store with an extra ff_opportunity pull at `pulled`, optionally
    missing one game (as if ffverse had not rebuilt it yet)."""
    dst = tmp / "store"
    shutil.copytree(STORE, dst)
    df = store_table(FF, SEASON)
    if drop_game is not None:
        df = df.filter(pl.col("game_id") != drop_game)
    part = dst / FF / f"season={SEASON}" / f"pulled_at={pulled.strftime('%Y%m%dT%H%M%SZ')}"
    part.mkdir(parents=True)
    df.write_parquet(part / "part.parquet")
    return dst


def test_own_pull_shows_finished_games_without_the_noon_rule(tmp_path: Path) -> None:
    gid, kickoff, prev = _late_target()
    noon = dt.datetime.combine(kickoff.astimezone(ET).date(), dt.time(12), ET).astimezone(dt.UTC)
    as_of = noon - dt.timedelta(hours=2)
    root = _with_own_pull(tmp_path, as_of - dt.timedelta(hours=1), None)
    snap = snapshot(gid, as_of=as_of, root=root)
    shown = set(snap.collect(FF)["game_id"].to_list())
    assert set(prev) <= shown  # before noon, but our pull holds them
    labels = " | ".join(snap.labels)
    assert f"{FF} {SEASON}: our own pull at" in labels


def test_own_pull_without_a_game_does_not_show_it(tmp_path: Path) -> None:
    gid, kickoff, prev = _late_target()
    as_of = kickoff - dt.timedelta(hours=2)
    root = _with_own_pull(tmp_path, as_of - dt.timedelta(hours=1), prev[0])
    shown = set(snapshot(gid, as_of=as_of, root=root).collect(FF)["game_id"].to_list())
    assert prev[0] not in shown
    assert set(prev[1:]) <= shown


def test_own_pull_still_hides_unfinished_games(tmp_path: Path) -> None:
    gid, kickoff, _ = _late_target()
    as_of = kickoff - dt.timedelta(hours=2)
    root = _with_own_pull(tmp_path, as_of - dt.timedelta(hours=1), None)
    snap = snapshot(gid, as_of=as_of, root=root)
    g = _games()
    not_done = set(
        g.filter(pl.col("game_end_utc").is_null() | (pl.col("game_end_utc") > as_of))[
            "game_id"
        ].to_list()
    )
    assert not set(snap.collect(FF)["game_id"].to_list()) & not_done
