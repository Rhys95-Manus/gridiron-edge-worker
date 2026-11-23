"""SHD-03 close and settle cadence (spec sync 5, decision 2026-11-23).

SHD-03: "Close checks run hourly, for games that kicked off in the last 48 h. Settle checks run
once a day, at 09:00 ET." Hourly means once per UTC clock hour; a settle check missed at 09:00 ET
runs at the next tick (catch-up). Pure functions on a fake clock."""

import datetime as dt

import pytest

from ge.config import load_params
from ge.shadow.cadence import Cadence, close_due, settle_due, settle_slot
from ge.store.known_at import EASTERN

H = dt.timedelta(hours=1)
M = dt.timedelta(minutes=1)


@pytest.fixture
def cad() -> Cadence:
    return Cadence.from_params(load_params())


def et(y: int, mo: int, d: int, h: int, mi: int = 0) -> dt.datetime:
    return dt.datetime(y, mo, d, h, mi, tzinfo=EASTERN).astimezone(dt.UTC)


def test_cadence_params(cad: Cadence) -> None:
    assert cad.close_lookback == 48 * H
    assert cad.settle_et_time == dt.time(9, 0)


def test_close_due_once_per_clock_hour() -> None:
    t = dt.datetime(2026, 11, 23, 10, 5, tzinfo=dt.UTC)
    assert close_due(t, None)
    assert not close_due(t + 50 * M, t)  # 10:55, same hour
    assert close_due(t + 55 * M, t)  # 11:00, next hour
    assert close_due(t + 3 * H, t)  # missed hours: one check, not three


@pytest.mark.parametrize(
    ("now", "last", "due"),
    [
        (et(2026, 11, 23, 8, 59), et(2026, 11, 22, 9, 1), False),  # before today's 09:00
        (et(2026, 11, 23, 9, 0), et(2026, 11, 22, 9, 1), True),  # 09:00 inclusive
        (et(2026, 11, 23, 15, 0), et(2026, 11, 23, 9, 0), False),  # already ran today
        (et(2026, 11, 23, 14, 0), et(2026, 11, 22, 9, 0), True),  # catch-up after a miss
        (et(2026, 11, 23, 8, 0), et(2026, 11, 21, 9, 0), True),  # missed all of yesterday
        (et(2026, 11, 23, 8, 0), None, True),  # never ran
    ],
)
def test_settle_due_daily_at_0900_et_with_catch_up(
    cad: Cadence, now: dt.datetime, last: dt.datetime | None, due: bool
) -> None:
    assert settle_due(now, last, cad) is due


def test_settle_slot_follows_eastern_time_across_dst(cad: Cadence) -> None:
    # EDT (UTC-4) in October, EST (UTC-5) in December.
    assert settle_slot(dt.datetime(2026, 10, 15, 14, 0, tzinfo=dt.UTC), cad) == dt.datetime(
        2026, 10, 15, 13, 0, tzinfo=dt.UTC
    )
    assert settle_slot(dt.datetime(2026, 12, 15, 14, 0, tzinfo=dt.UTC), cad) == dt.datetime(
        2026, 12, 15, 14, 0, tzinfo=dt.UTC
    )
    # 13:59 UTC in December is 08:59 EST: the slot is the previous day's 09:00 EST.
    assert settle_slot(dt.datetime(2026, 12, 15, 13, 59, tzinfo=dt.UTC), cad) == dt.datetime(
        2026, 12, 14, 14, 0, tzinfo=dt.UTC
    )


def test_naive_times_are_refused(cad: Cadence) -> None:
    with pytest.raises(ValueError):
        close_due(dt.datetime(2026, 11, 23, 10, 0), None)
    with pytest.raises(ValueError):
        settle_due(dt.datetime(2026, 11, 23, 10, 0), None, cad)
