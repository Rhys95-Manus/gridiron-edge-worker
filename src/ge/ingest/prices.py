"""Kalshi dollar strings to integer centicents, and asks from a bids-only order book."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation

CENTICENTS_PER_DOLLAR = 10_000  # CLAUDE.md rule 7: 1 centicent = 1/10,000 of a dollar


def dollars_to_cc(value: str) -> int:
    """DATA-08: parse a Kalshi *_dollars string ("0.1500") into integer centicents.

    Raises ValueError for anything that isn't an exact price in [0, 1] dollars."""
    try:
        d = Decimal(value)
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(f"not a dollar amount: {value!r}") from exc
    cc = d * CENTICENTS_PER_DOLLAR
    if cc != cc.to_integral_value():
        raise ValueError(f"finer than a centicent: {value!r}")
    if not 0 <= cc <= CENTICENTS_PER_DOLLAR:
        raise ValueError(f"price outside $0-$1: {value!r}")
    return int(cc)


def _best_bid_cc(levels: Sequence[Sequence[str]]) -> int | None:
    return max((dollars_to_cc(price) for price, _qty in levels), default=None)


def book_asks(orderbook_fp: Mapping[str, Sequence[Sequence[str]]]) -> tuple[int | None, int | None]:
    """EDG-01: YES ask = $1 - best NO bid; NO ask = $1 - best YES bid, in centicents.

    The book lists bids only; a side with no bids means nothing to buy the other side from."""
    best_yes = _best_bid_cc(orderbook_fp.get("yes_dollars") or [])
    best_no = _best_bid_cc(orderbook_fp.get("no_dollars") or [])
    yes_ask = None if best_no is None else CENTICENTS_PER_DOLLAR - best_no
    no_ask = None if best_yes is None else CENTICENTS_PER_DOLLAR - best_yes
    return yes_ask, no_ask
