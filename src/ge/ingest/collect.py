"""`ge ingest collect`: the scheduled pull. Runs the week's Kalshi pull, the current season's
injuries and depth charts, and the weather pull, in that order. Each step's start, end and
result go to logs/collect.log; a failing step never stops the others."""

from __future__ import annotations

import datetime as dt
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from ge.config import REPO_ROOT, load_ingest
from ge.ingest.jobs import _now, _schedules, run_kalshi, run_weather
from ge.ingest.nflverse import current_season, ingest_nflverse
from ge.store.known_at import week_window

LOG_PATH = REPO_ROOT / "logs" / "collect.log"
NFLVERSE_DATASETS = ["injuries", "depth_charts"]

StepFn = Callable[[], tuple[bool, str]]


@dataclass(frozen=True)
class Step:
    name: str
    run: StepFn  # returns (ok, one-line detail); may raise


def current_week(sched: pl.DataFrame, now: dt.datetime) -> int:
    """DATA-08: the week whose window holds `now`, using the same window as the Kalshi pull
    (week W runs from its first game date, 00:00 ET, to week W+1's first game date). `sched`
    is one season's schedules. Before week 1 there is no current week, so it raises."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    for w in sorted(sched["week"].unique().to_list(), reverse=True):
        start, end = week_window(sched, w)
        if start <= now and (end is None or now < end):
            return int(w)
    raise LookupError(f"{now.isoformat()} is before the first week in schedules")


def _user_agent() -> str:
    from ge.settings import Settings

    return Settings().nws_user_agent.get_secret_value()


def _kalshi() -> tuple[bool, str]:
    season = current_season()
    week = current_week(_schedules([season]), _now())
    code = run_kalshi(load_ingest(), season, week, False)
    return code == 0, f"season {season} week {week}: exit {code}"


def _nflverse() -> tuple[bool, str]:
    season = current_season()
    results = ingest_nflverse([season], NFLVERSE_DATASETS)
    detail = "; ".join(
        f"{r.dataset} {r.season} {r.status} {r.rows} rows" + (f" ({r.detail})" if r.detail else "")
        for r in results
    )
    return not any(r.status == "error" for r in results), detail


def _weather() -> tuple[bool, str]:
    cfg = load_ingest()
    days = cfg.nws.forecast_window_days.value
    code = run_weather(cfg, _user_agent(), days)
    return code == 0, f"next {days} days: exit {code}"


def default_steps() -> list[Step]:
    return [Step("kalshi", _kalshi), Step("nflverse", _nflverse), Step("weather", _weather)]


def _write(path: Path, msg: str) -> None:
    stamp = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        for line in msg.splitlines() or [""]:
            fh.write(f"{stamp} {line}\n")


def run_collect(steps: list[Step], log_path: Path) -> int:
    """Run every step in order, logging each one's start, end and result. Returns 1 if any
    step raised or reported failure, else 0."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    _write(log_path, f"COLLECT start: {', '.join(s.name for s in steps)}")
    failed: list[str] = []
    for step in steps:
        _write(log_path, f"START {step.name}")
        t0 = time.monotonic()
        try:
            ok, detail = step.run()
        except (Exception, SystemExit) as exc:  # SystemExit: jobs exit on missing schedules
            ok, detail = False, f"{type(exc).__name__}: {exc}"
            for line in traceback.format_exc().splitlines():
                _write(log_path, f"TRACE {step.name} {line}")
        secs = time.monotonic() - t0
        _write(log_path, f"END {step.name} {'ok' if ok else 'FAILED'} ({secs:.1f} s): {detail}")
        if not ok:
            failed.append(step.name)
    code = 1 if failed else 0
    _write(
        log_path,
        f"COLLECT end: {len(steps) - len(failed)} ok, {len(failed)} failed"
        + (f" ({', '.join(failed)})" if failed else "")
        + f", exit {code}",
    )
    return code
