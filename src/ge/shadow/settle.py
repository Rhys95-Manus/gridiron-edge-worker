"""SHD-13 results from Kalshi's settled market record.

SHD-13: "The result is Kalshi's settled result. A fair-price settlement or a void is not_binary
and is excluded from results." Saved 2026 records show settled markets with status finalized
and result yes (settlement_value_dollars 1.0000), no (0.0000) or scalar (a fair price); a
result counts as binary only when result and settlement value agree on 1 or 0."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ge.ingest.prices import CENTICENTS_PER_DOLLAR, dollars_to_cc

SETTLED_STATUS = "finalized"


def settle_value(market: Mapping[str, Any]) -> tuple[str, int | None] | None:
    """SHD-13: None while the market is not settled; else (yes, 1), (no, 0) or
    (not_binary, None)."""
    if market.get("status") != SETTLED_STATUS:
        return None
    try:
        cc = dollars_to_cc(str(market.get("settlement_value_dollars")))
    except ValueError:
        return ("not_binary", None)
    result = market.get("result")
    if result == "yes" and cc == CENTICENTS_PER_DOLLAR:
        return ("yes", 1)
    if result == "no" and cc == 0:
        return ("no", 0)
    return ("not_binary", None)
