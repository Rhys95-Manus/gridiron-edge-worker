"""SHD-05 closing price from GET /markets/trades (retrospective, after kickoff).

SHD-05: "The YES price of the last trade created after the snapshot was taken and before
kickoff. No such trade before kickoff: no_trade. Last pre-kickoff trade at or before the
snapshot: stale. Both are excluded from CLV and counted in the report. Last pre-kickoff trades
with the same time but different prices: ambiguous_last_trade, also excluded from CLV and
counted."

Trade fields as documented at docs.kalshi.com GET /markets/trades (read 2026-11-21):
trade_id, yes_price_dollars, created_time. The page does not say whether min_ts/max_ts are
inclusive, so callers ask past kickoff and this function filters created_time < kickoff
itself. An ambiguous_last_trade close carries no price."""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from ge.ingest.prices import dollars_to_cc


@dataclass(frozen=True)
class Close:
    status: str  # ok | no_trade | stale | ambiguous_last_trade
    close_yes_cc: int | None
    last_trade_id: str | None
    last_trade_ts: dt.datetime | None
    n_pre_kickoff: int


def _ts(value: str) -> dt.datetime:
    t = dt.datetime.fromisoformat(value)
    if t.tzinfo is None:
        raise ValueError(f"trade created_time without a time zone: {value!r}")
    return t.astimezone(dt.UTC)


def closing_price(
    trades: Iterable[Mapping[str, Any]], kickoff: dt.datetime, taken: dt.datetime
) -> Close:
    """SHD-05: the closing YES price (centicents) for a snapshot taken at `taken`."""
    pre = [
        (
            _ts(str(t["created_time"])),
            dollars_to_cc(str(t["yes_price_dollars"])),
            str(t["trade_id"]),
        )
        for t in trades
    ]
    pre = [p for p in pre if p[0] < kickoff]
    if not pre:
        return Close("no_trade", None, None, None, 0)
    last_ts = max(p[0] for p in pre)
    last = sorted((p for p in pre if p[0] == last_ts), key=lambda p: p[2])
    if last_ts <= taken:
        return Close("stale", None, last[-1][2], last_ts, len(pre))
    prices = {p[1] for p in last}
    if len(prices) > 1:
        return Close("ambiguous_last_trade", None, None, last_ts, len(pre))
    return Close("ok", prices.pop(), last[-1][2], last_ts, len(pre))
