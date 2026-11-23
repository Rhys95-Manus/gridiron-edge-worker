"""SHD-03 close and settle cadence, as pure functions of the clock.

SHD-03: "Close checks run hourly, for games that kicked off in the last 48 h. Settle checks run
once a day, at 09:00 ET." Hourly is read as once per UTC clock hour: a close check is due when
the last one ran in an earlier clock hour. A settle check is due when none has run since the
most recent 09:00 ET at or before now, so a check missed at 09:00 (laptop off) runs at the next
tick. The last run of each job is read from the store's job_runs table."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from ge.config import Params
from ge.store.known_at import EASTERN


@dataclass(frozen=True)
class Cadence:
    """SHD-03 close look-back and settle time (params.yaml shadow group)."""

    close_lookback: dt.timedelta
    settle_et_time: dt.time

    @classmethod
    def from_params(cls, params: Params) -> Cadence:
        sh = params.shadow
        minute = int(sh.shd_03_settle_et_minute_of_day.value)
        return cls(
            close_lookback=dt.timedelta(hours=float(sh.shd_03_close_lookback_hours.value)),
            settle_et_time=dt.time(minute // 60, minute % 60),
        )


def _aware(t: dt.datetime) -> dt.datetime:
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("times must be timezone-aware")
    return t.astimezone(dt.UTC)


def close_due(now: dt.datetime, last: dt.datetime | None) -> bool:
    """SHD-03: a close check runs once per UTC clock hour."""
    now = _aware(now)
    if last is None:
        return True
    hour = now.replace(minute=0, second=0, microsecond=0)
    return _aware(last) < hour


def settle_slot(now: dt.datetime, cad: Cadence) -> dt.datetime:
    """SHD-03: the most recent 09:00 ET at or before now (UTC)."""
    local = _aware(now).astimezone(EASTERN)
    slot = dt.datetime.combine(local.date(), cad.settle_et_time, tzinfo=EASTERN)
    if slot > local:
        slot = dt.datetime.combine(
            local.date() - dt.timedelta(days=1), cad.settle_et_time, tzinfo=EASTERN
        )
    return slot.astimezone(dt.UTC)


def settle_due(now: dt.datetime, last: dt.datetime | None, cad: Cadence) -> bool:
    """SHD-03: a settle check runs once a day at 09:00 ET; a missed one runs at the next tick."""
    slot = settle_slot(now, cad)
    return last is None or _aware(last) < slot
