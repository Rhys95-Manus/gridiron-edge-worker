"""`ge ingest collect`: the scheduled pull. Not part of any BUILD_PLAN phase (user request
2026-10-02); it lives with the ingest tests because it only chains existing ingest jobs."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import polars as pl
import pytest
import typer
from typer.testing import CliRunner

from ge.cli import app
from ge.ingest import collect
from ge.ingest.collect import Step, current_week, default_steps, run_collect
from ge.ingest.nflverse import PullResult
from ge.store.known_at import week_window
from tests.phase2.conftest import load_parquet_fixture

SEASON = 2025  # a completed season in the real schedules fixture


def _season(season: int) -> pl.DataFrame:
    s = load_parquet_fixture("schedules_2023_2026")
    return s.filter(pl.col("season") == season)


# --- current week, from schedules -----------------------------------------------------------


def test_current_week_is_the_week_whose_window_holds_now() -> None:
    sched = _season(SEASON)
    weeks = sorted(sched["week"].unique().to_list())
    for w in weeks:
        start, end = week_window(sched, w)
        assert current_week(sched, start) == w
        if end is not None:
            assert current_week(sched, end - dt.timedelta(microseconds=1)) == w
            assert current_week(sched, end) == w + 1


def test_last_week_is_open_ended() -> None:
    sched = _season(SEASON)
    last = max(sched["week"].to_list())
    start, end = week_window(sched, last)
    assert end is None
    assert current_week(sched, start + dt.timedelta(days=60)) == last


def test_before_week_one_is_an_error_not_a_guess() -> None:
    sched = _season(SEASON)
    start, _ = week_window(sched, min(sched["week"].to_list()))
    with pytest.raises(LookupError):
        current_week(sched, start - dt.timedelta(microseconds=1))


def test_naive_now_is_rejected() -> None:
    with pytest.raises(ValueError):
        current_week(_season(SEASON), dt.datetime(2025, 10, 1))


# --- the runner -----------------------------------------------------------------------------


def _log_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def test_steps_run_in_order_and_a_failure_does_not_stop_the_rest(tmp_path: Path) -> None:
    ran: list[str] = []

    def ok(name: str) -> Step:
        def run() -> tuple[bool, str]:
            ran.append(name)
            return True, f"{name} fine"

        return Step(name, run)

    def boom() -> tuple[bool, str]:
        ran.append("b")
        raise RuntimeError("network down")

    log = tmp_path / "logs" / "collect.log"
    code = run_collect([ok("a"), Step("b", boom), ok("c")], log)

    assert ran == ["a", "b", "c"]
    assert code == 1
    lines = _log_lines(log)
    events = [(ln.split()[1], ln.split()[2]) for ln in lines if ln.split()[1] in ("START", "END")]
    assert events == [
        ("START", "a"),
        ("END", "a"),
        ("START", "b"),
        ("END", "b"),
        ("START", "c"),
        ("END", "c"),
    ]
    end_b = next(ln for ln in lines if ln.split()[1:3] == ["END", "b"])
    assert "FAILED" in end_b and "network down" in end_b
    end_a = next(ln for ln in lines if ln.split()[1:3] == ["END", "a"])
    assert " ok " in end_a and "a fine" in end_a
    assert "1 failed" in lines[-1]


def test_a_step_reporting_failure_counts_as_failed(tmp_path: Path) -> None:
    log = tmp_path / "collect.log"
    code = run_collect([Step("a", lambda: (False, "exit 2")), Step("b", lambda: (True, ""))], log)
    assert code == 1
    assert "FAILED" in next(ln for ln in _log_lines(log) if ln.split()[1:3] == ["END", "a"])


def test_all_ok_exits_zero_and_log_appends(tmp_path: Path) -> None:
    log = tmp_path / "collect.log"
    assert run_collect([Step("a", lambda: (True, "x"))], log) == 0
    first = len(_log_lines(log))
    assert run_collect([Step("a", lambda: (True, "x"))], log) == 0
    assert len(_log_lines(log)) == 2 * first


def test_log_timestamps_are_utc_iso(tmp_path: Path) -> None:
    log = tmp_path / "collect.log"
    run_collect([Step("a", lambda: (True, ""))], log)
    for ln in _log_lines(log):
        stamp = dt.datetime.fromisoformat(ln.split()[0])
        assert stamp.utcoffset() == dt.timedelta(0)


# --- the three real steps, with their network calls replaced --------------------------------


def test_default_steps_are_kalshi_then_nflverse_then_weather() -> None:
    assert [s.name for s in default_steps()] == ["kalshi", "nflverse", "weather"]


def test_kalshi_step_pulls_the_week_worked_out_from_schedules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sched = _season(SEASON)
    w = 5
    start, _ = week_window(sched, w)
    calls: list[tuple[int, int, bool]] = []

    def fake_run_kalshi(cfg: Any, season: int, week: int, history: bool) -> int:
        calls.append((season, week, history))
        return 0

    monkeypatch.setattr(collect, "current_season", lambda: SEASON)
    monkeypatch.setattr(collect, "_schedules", lambda seasons: sched)
    monkeypatch.setattr(collect, "_now", lambda: start + dt.timedelta(hours=30))
    monkeypatch.setattr(collect, "run_kalshi", fake_run_kalshi)
    ok, detail = default_steps()[0].run()
    assert ok
    assert calls == [(SEASON, w, False)]
    assert f"week {w}" in detail


def test_kalshi_step_fails_on_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    sched = _season(SEASON)
    start, _ = week_window(sched, 3)
    monkeypatch.setattr(collect, "current_season", lambda: SEASON)
    monkeypatch.setattr(collect, "_schedules", lambda seasons: sched)
    monkeypatch.setattr(collect, "_now", lambda: start)
    monkeypatch.setattr(collect, "run_kalshi", lambda *a: 2)
    ok, detail = default_steps()[0].run()
    assert not ok and "exit 2" in detail


def test_nflverse_step_pulls_injuries_depth_charts_and_schedules_for_current_season(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[int], list[str] | None]] = []

    def fake(seasons: list[int], datasets: list[str] | None = None) -> list[PullResult]:
        calls.append((seasons, datasets))
        return [PullResult(d, seasons[0], "written", 10) for d in datasets or []]

    monkeypatch.setattr(collect, "current_season", lambda: SEASON)
    monkeypatch.setattr(collect, "ingest_nflverse", fake)
    ok, _ = default_steps()[1].run()
    assert ok
    # schedules: flexed kickoff times change gametime after the season's first pull
    assert calls == [([SEASON], ["injuries", "depth_charts", "schedules"])]


def test_nflverse_step_fails_when_a_pull_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(seasons: list[int], datasets: list[str] | None = None) -> list[PullResult]:
        return [
            PullResult("injuries", SEASON, "written", 10),
            PullResult("depth_charts", SEASON, "error", detail="HTTPError: 503"),
        ]

    monkeypatch.setattr(collect, "current_season", lambda: SEASON)
    monkeypatch.setattr(collect, "ingest_nflverse", fake)
    ok, detail = default_steps()[1].run()
    assert not ok and "HTTPError: 503" in detail


def test_weather_step_uses_configured_window(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def fake(cfg: Any, user_agent: str, days: int) -> int:
        calls.append(days)
        return 0

    monkeypatch.setattr(collect, "run_weather", fake)
    monkeypatch.setattr(collect, "_user_agent", lambda: "ua")
    ok, _ = default_steps()[2].run()
    assert ok
    assert calls == [collect.load_ingest().nws.forecast_window_days.value]


# --- the command ----------------------------------------------------------------------------


def test_collect_is_an_ingest_subcommand() -> None:
    root = typer.main.get_command(app)
    assert isinstance(root, typer.core.TyperGroup)
    group = root.commands["ingest"]
    assert isinstance(group, typer.core.TyperGroup)
    assert "collect" in group.commands


def test_command_exits_nonzero_when_any_step_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    log = tmp_path / "collect.log"
    monkeypatch.setattr(collect, "LOG_PATH", log)
    monkeypatch.setattr(
        collect,
        "default_steps",
        lambda: [Step("a", lambda: (True, "")), Step("b", lambda: (False, "bad"))],
    )
    result = CliRunner().invoke(app, ["ingest", "collect"])
    assert result.exit_code == 1, result.output
    assert log.exists()

    monkeypatch.setattr(collect, "default_steps", lambda: [Step("a", lambda: (True, ""))])
    result = CliRunner().invoke(app, ["ingest", "collect"])
    assert result.exit_code == 0, result.output
