"""SHD-01 to SHD-04 and SHD-12: which snapshots are due, as a pure function of the clock.

SHD-01: "Snapshots are taken at kickoff − 24 h (the primary snapshot) and kickoff − 90 min,
using BT-01's offsets and kickoff from the newest stored nflverse schedules."
SHD-02: "A T−24h snapshot is valid from 15 min early to 60 min late. A T−90m snapshot is valid
from 10 min early to 25 min late."
SHD-04: "An order-book capture is taken at kickoff − 5 min, valid within ±4 min."
SHD-12: "Every planned snapshot gets a status row: ok, ok_late, missed_not_run,
missed_api_error, missed_no_markets or invalid_kickoff_moved."

Session-4 choices (open questions in session4-report.md): a snapshot is planned when its window
closes at or after the shadow version's capture start; ok means taken at or before the target,
ok_late after it; a window that closes without an ok row takes its miss reason from the last
attempt inside it; a snapshot whose taken_ts falls outside the window of the newest kickoff is
invalid_kickoff_moved and the snapshot is planned again for the new window."""  # noqa: RUF002

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ge.config import Params

# SHD-19 names live and after_the_fact only; capture rows logged at the snapshot use live
# (open question Q1 in session4-report.md).
PRICING_MODE_CAPTURE = "live"


class SnapshotType(StrEnum):
    T24H = "T-24h"
    T90M = "T-90m"
    CLOSE_BOOK = "T-close-book"


@dataclass(frozen=True)
class ShadowWindows:
    """SHD-01 to SHD-04: offsets and tolerances from params.yaml (BT-01 and shadow groups)."""

    offsets: tuple[tuple[SnapshotType, dt.timedelta, dt.timedelta, dt.timedelta], ...]
    tick: dt.timedelta
    schedule_max_age: dt.timedelta

    @classmethod
    def from_params(cls, params: Params) -> ShadowWindows:
        bt, sh = params.backtest, params.shadow

        def mins(v: float) -> dt.timedelta:
            return dt.timedelta(minutes=float(v))

        cb = mins(sh.shd_04_close_capture_tolerance_minutes.value)
        return cls(
            offsets=(
                (
                    SnapshotType.T24H,
                    dt.timedelta(hours=float(bt.bt_01_decision_hours_before_kickoff.value)),
                    mins(sh.shd_02_t24h_early_minutes.value),
                    mins(sh.shd_02_t24h_late_minutes.value),
                ),
                (
                    SnapshotType.T90M,
                    mins(bt.bt_01_second_pass_minutes_before_kickoff.value),
                    mins(sh.shd_02_t90m_early_minutes.value),
                    mins(sh.shd_02_t90m_late_minutes.value),
                ),
                (
                    SnapshotType.CLOSE_BOOK,
                    mins(sh.shd_04_close_capture_minutes_before_kickoff.value),
                    cb,
                    cb,
                ),
            ),
            tick=mins(sh.shd_03_tick_minutes.value),
            schedule_max_age=dt.timedelta(hours=float(sh.shd_03_schedule_max_age_hours.value)),
        )


@dataclass(frozen=True)
class Window:
    snapshot_type: SnapshotType
    target: dt.datetime
    open: dt.datetime
    close: dt.datetime


@dataclass(frozen=True)
class GameKick:
    """One schedules game and its kickoff (UTC) from the newest stored schedules."""

    game_id: str
    season: int
    week: int
    kickoff_utc: dt.datetime


@dataclass(frozen=True)
class StatusRec:
    """The latest snapshot_status row for a (game, snapshot type)."""

    status: str
    taken_ts: dt.datetime | None
    target_ts: dt.datetime
    written_at: dt.datetime


@dataclass(frozen=True)
class Attempt:
    """One snapshot try: outcome ok, api_error or no_markets."""

    ts: dt.datetime
    outcome: str
    detail: str


@dataclass(frozen=True)
class Due:
    game: GameKick
    window: Window


@dataclass(frozen=True)
class TickPlan:
    due: list[Due]
    status_rows: list[dict[str, Any]]


def windows(kickoff: dt.datetime, cfg: ShadowWindows) -> list[Window]:
    """SHD-01 / SHD-02 / SHD-04: each snapshot's target and validity window for a kickoff."""
    return [
        Window(t, kickoff - before, kickoff - before - early, kickoff - before + late)
        for t, before, early, late in cfg.offsets
    ]


def judge(taken: dt.datetime, w: Window) -> str | None:
    """SHD-02 / SHD-12: ok (at or before target), ok_late (after it, inside the window) or None
    (outside the window)."""
    if not w.open <= taken <= w.close:
        return None
    return "ok" if taken <= w.target else "ok_late"


_TAKEN = frozenset({"ok", "ok_late"})
_MISS = {"api_error": "missed_api_error", "no_markets": "missed_no_markets"}


def plan_tick(
    now: dt.datetime,
    games: Sequence[GameKick],
    latest_status: Mapping[tuple[str, str], StatusRec],
    attempts: Mapping[tuple[str, str], Sequence[Attempt]],
    start: dt.datetime,
    cfg: ShadowWindows,
) -> TickPlan:
    """SHD-03 / SHD-12: the snapshots due now and the status rows to write (misses and
    invalid_kickoff_moved). Pure: reads nothing but its arguments."""
    if now.tzinfo is None or start.tzinfo is None:
        raise ValueError("now and start must be timezone-aware")
    due: list[Due] = []
    rows: list[dict[str, Any]] = []
    for g in sorted(games, key=lambda x: (x.kickoff_utc, x.game_id)):
        for w in windows(g.kickoff_utc, cfg):
            if w.close < start:
                continue
            key = (g.game_id, str(w.snapshot_type))
            rec = latest_status.get(key)
            if rec is not None and rec.status in _TAKEN:
                if rec.taken_ts is not None and judge(rec.taken_ts, w) is not None:
                    continue
                rows.append(
                    status_row(g, w, "invalid_kickoff_moved", rec.taken_ts, "kickoff moved")
                )
            elif rec is not None and rec.status != "invalid_kickoff_moved":
                continue  # a miss row is final
            if w.open <= now <= w.close:
                due.append(Due(g, w))
            elif now > w.close:
                tries = [a for a in attempts.get(key, ()) if w.open <= a.ts <= w.close]
                last = max(tries, key=lambda a: a.ts) if tries else None
                status = _MISS.get(last.outcome, "missed_not_run") if last else "missed_not_run"
                rows.append(status_row(g, w, status, None, last.detail if last else ""))
    return TickPlan(due, rows)


def status_row(
    g: GameKick,
    w: Window,
    status: str,
    taken: dt.datetime | None,
    detail: str,
    n_markets: int | None = None,
    n_books: int | None = None,
) -> dict[str, Any]:
    """SHD-12: one snapshot_status row."""
    return {
        "game_id": g.game_id,
        "season": g.season,
        "week": g.week,
        "kickoff_utc": g.kickoff_utc,
        "snapshot_type": str(w.snapshot_type),
        "status": status,
        "target_ts": w.target,
        "taken_ts": taken,
        "lateness_s": None if taken is None else (taken - w.target).total_seconds(),
        "n_markets": n_markets,
        "n_books": n_books,
        "detail": detail,
        "pricing_mode": PRICING_MODE_CAPTURE,
    }
