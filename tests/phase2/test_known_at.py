"""BT-01 known-at rules on real schedule, pbp and depth-chart slices (tests/phase2/fixtures)."""

import datetime as dt
from zoneinfo import ZoneInfo

import polars as pl
import pytest

from ge.config import load_params
from ge.store.known_at import (
    GameEndUnknown,
    default_as_of,
    finished_game_ids,
    game_ends,
    kickoff_utc,
    latest_espn_chart,
    latest_weekly_chart,
    report_known_at,
    team_weeks,
    visible_weekly,
    with_kickoff,
)
from tests.phase2.conftest import load_parquet_fixture

ET = ZoneInfo("America/New_York")
BT = load_params().backtest
HOUR = BT.bt_01_assumed_report_hour_et.value
DAYS = BT.bt_01_assumed_report_days_before_kickoff.value


def _sched() -> pl.DataFrame:
    return with_kickoff(load_parquet_fixture("schedules_2023_2026"))


def test_kickoff_is_eastern_and_matches_first_play() -> None:
    """Independent check on the Eastern reading of schedules: the median gap between each
    game's first timestamped pbp row (time_of_day, UTC) and the kickoff we compute is under
    30 minutes. A time zone mistake would move every game by whole hours. Single games can
    be far off (a delayed start; a pregame row stamped minutes early), so they're printed."""
    s = _sched().filter(pl.col("season") == 2024)
    ends = load_parquet_fixture("pbp_time_of_day_2024")
    first = (
        ends.drop_nulls("time_of_day")
        .with_columns(pl.col("time_of_day").str.to_datetime(time_zone="UTC", time_unit="us"))
        .group_by("game_id")
        .agg(pl.col("time_of_day").min().alias("first_play"))
    )
    j = s.join(first, on="game_id", how="inner")
    assert j.height == s.filter(pl.col("result").is_not_null()).height
    gap = (pl.col("first_play") - pl.col("kickoff_utc")).dt.total_minutes()
    median = j.select(gap.median()).item()
    assert abs(median) < 30, median
    print(f"median first play - kickoff: {median} min; outliers (30+ min):")
    print(j.filter(gap.abs() >= 30).select("game_id", "kickoff_utc", "first_play"))
    one = j.row(0, named=True)
    expect = dt.datetime.combine(
        dt.date.fromisoformat(one["gameday"]), dt.time.fromisoformat(one["gametime"]), ET
    ).astimezone(dt.UTC)
    assert kickoff_utc(one["gameday"], one["gametime"]) == expect


def test_report_known_at_is_noon_et_the_day_before_for_every_game() -> None:
    s = _sched()
    for g in s.iter_rows(named=True):
        k = g["kickoff_utc"]
        got = report_known_at(k, BT)
        local_day = k.astimezone(ET).date() - dt.timedelta(days=DAYS)
        assert got == dt.datetime.combine(local_day, dt.time(HOUR), ET).astimezone(dt.UTC)
        assert got.astimezone(ET).hour == HOUR
        assert got < k, g["game_id"]


def test_report_known_at_across_the_dst_change() -> None:
    """Games whose kickoff and report day sit on opposite sides of a DST change."""
    s = _sched()
    flips = [
        g
        for g in s.iter_rows(named=True)
        if report_known_at(g["kickoff_utc"], BT).astimezone(ET).utcoffset()
        != g["kickoff_utc"].astimezone(ET).utcoffset()
    ]
    assert flips, "expected at least one game on a DST-change weekend in 2023-2026"
    for g in flips:
        got = report_known_at(g["kickoff_utc"], BT).astimezone(ET)
        assert (got.hour, got.minute) == (HOUR, 0)


def test_thursday_saturday_monday_and_morning_kickoffs() -> None:
    s = _sched()
    by_day = {d: s.filter(pl.col("weekday") == d) for d in ("Thursday", "Saturday", "Monday")}
    for day, games in by_day.items():
        assert games.height, f"no {day} games in fixture"
        for g in games.iter_rows(named=True):
            wd = report_known_at(g["kickoff_utc"], BT).astimezone(ET).strftime("%A")
            expect = (g["kickoff_utc"].astimezone(ET) - dt.timedelta(days=DAYS)).strftime("%A")
            assert wd == expect
    # Morning (international) kickoffs: kickoff - 24 h comes BEFORE the assumed report time,
    # so the decision-time snapshot must not see that week's report.
    morning = s.filter(pl.col("gametime") < f"{HOUR:02d}:00")
    assert morning.height, "no pre-noon ET kickoffs in fixture"
    for g in morning.iter_rows(named=True):
        k = g["kickoff_utc"]
        assert default_as_of(k, "decision", BT) < report_known_at(k, BT)


def test_default_as_of_comes_from_params() -> None:
    k = _sched().row(0, named=True)["kickoff_utc"]
    assert default_as_of(k, "decision", BT) == k - dt.timedelta(
        hours=BT.bt_01_decision_hours_before_kickoff.value
    )
    assert default_as_of(k, "inactives", BT) == k - dt.timedelta(
        minutes=BT.bt_01_second_pass_minutes_before_kickoff.value
    )
    with pytest.raises(ValueError):
        default_as_of(k, "whenever", BT)  # type: ignore[arg-type]


def test_team_weeks_one_row_per_team_game() -> None:
    s = _sched()
    tw = team_weeks(s, BT)
    assert tw.height == 2 * s.height
    assert tw.select("season", "week", "team").n_unique() == tw.height
    assert set(tw.columns) >= {"season", "week", "team", "game_id", "kickoff_utc", "known_at"}


def test_game_ends_and_unknown_end_fails_loudly() -> None:
    pbp = load_parquet_fixture("pbp_time_of_day_2024")
    ends = game_ends(pbp)
    s = _sched().filter(pl.col("season") == 2024)
    j = s.join(ends, on="game_id")
    assert j.height == ends.height == pbp["game_id"].n_unique()
    assert (j["game_end_utc"] > j["kickoff_utc"]).all()
    gid = pbp["game_id"][0]
    broken = pbp.with_columns(
        pl.when(pl.col("game_id") == gid)
        .then(None)
        .otherwise(pl.col("time_of_day"))
        .alias("time_of_day")
    )
    with pytest.raises(GameEndUnknown, match=gid):
        game_ends(broken)


def test_finished_games_exclude_same_day_games_still_being_played() -> None:
    s = _sched().filter(pl.col("season") == 2024)
    games = s.join(game_ends(load_parquet_fixture("pbp_time_of_day_2024")), on="game_id")
    et = games.with_columns(
        pl.col("kickoff_utc").dt.convert_time_zone("America/New_York").alias("k")
    )
    late = et.filter((pl.col("weekday") == "Sunday") & (pl.col("k").dt.hour() >= 16)).sort("k")
    target = late.row(0, named=True)
    early = et.filter(
        (pl.col("gameday") == target["gameday"]) & (pl.col("kickoff_utc") < target["kickoff_utc"])
    )
    assert early.height, "expected earlier games on the same day"
    as_of = default_as_of(target["kickoff_utc"], "inactives", BT)
    done = set(finished_game_ids(games, as_of, target["game_id"]))
    running = early.filter(pl.col("game_end_utc") > as_of)["game_id"].to_list()
    assert running, "expected an early game still in progress at kickoff - 90 min"
    assert not done & set(running)
    assert target["game_id"] not in done
    before = games.filter(pl.col("game_end_utc") <= as_of)["game_id"].to_list()
    assert set(before) == done
    # Even at or after kickoff, the target game and games kicked off with it stay out.
    at_k = set(
        finished_game_ids(games, target["kickoff_utc"] + dt.timedelta(hours=6), target["game_id"])
    )
    assert target["game_id"] not in at_k
    same_slot = games.filter(pl.col("kickoff_utc") >= target["kickoff_utc"])["game_id"].to_list()
    assert not at_k & set(same_slot)


def test_weekly_reports_become_visible_at_noon_the_day_before() -> None:
    depth = load_parquet_fixture("depth_weekly_2023")
    tw = team_weeks(_sched(), BT).filter(pl.col("season") == 2023)
    team = sorted(depth["club_code"].unique().to_list())[0]
    row = tw.filter((pl.col("team") == team) & (pl.col("week") == 2)).row(0, named=True)
    t = row["known_at"]
    weeks_before = set(
        visible_weekly(depth, tw, t - dt.timedelta(seconds=1), "club_code")
        .filter(pl.col("club_code") == team)["week"]
        .to_list()
    )
    weeks_at = set(
        visible_weekly(depth, tw, t, "club_code")
        .filter(pl.col("club_code") == team)["week"]
        .to_list()
    )
    assert 2 not in weeks_before and 2 in weeks_at
    assert max(weeks_before) == 1


def test_latest_weekly_chart_per_team() -> None:
    depth = load_parquet_fixture("depth_weekly_2023")
    tw = team_weeks(_sched(), BT).filter(pl.col("season") == 2023)
    for team in depth["club_code"].unique().to_list():
        games = tw.filter(pl.col("team") == team).sort("week")
        for g in games.iter_rows(named=True):
            as_of = default_as_of(g["kickoff_utc"], "decision", BT)
            got = latest_weekly_chart(depth, tw, as_of).filter(pl.col("club_code") == team)
            visible = games.filter(pl.col("known_at") <= as_of)["week"].to_list()
            have = set(depth.filter(pl.col("club_code") == team)["week"].to_list())
            expect = max([w for w in visible if w in have], default=None)
            assert set(got["week"].to_list()) == ({expect} if expect is not None else set())


def test_latest_espn_chart_is_latest_dt_on_or_before_as_of() -> None:
    depth = load_parquet_fixture("depth_espn_2025")
    stamps = sorted(
        {dt.datetime.fromisoformat(d.replace("Z", "+00:00")) for d in depth["dt"].to_list()}
    )
    for t in [*stamps[:: max(1, len(stamps) // 12)], stamps[-1]]:
        for as_of in (t, t - dt.timedelta(seconds=1)):
            got = latest_espn_chart(depth, as_of)
            for team in depth["team"].unique().to_list():
                mine = depth.filter(pl.col("team") == team)
                ok = [
                    d
                    for d in mine["dt"].unique().to_list()
                    if dt.datetime.fromisoformat(d.replace("Z", "+00:00")) <= as_of
                ]
                want = max(
                    ok,
                    key=lambda d: dt.datetime.fromisoformat(d.replace("Z", "+00:00")),
                    default=None,
                )
                g = got.filter(pl.col("team") == team)
                if want is None:
                    assert g.is_empty()
                else:
                    assert set(g["dt"].to_list()) == {want}
                    assert g.height == mine.filter(pl.col("dt") == want).height
