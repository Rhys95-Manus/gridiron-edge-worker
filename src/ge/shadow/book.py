"""SHD-10 / SHD-16 order-book summary from GET /markets/{ticker}/orderbook.

SHD-10: "Book prices come from the order-book endpoint, never from the markets list."
SHD-16: "Liquidity is the contracts at or within 2¢ of the best price on each side (EDG-04)."
The book lists bids only (EDG-01): YES ask = $1 - best NO bid, NO ask = $1 - best YES bid, and
the size behind an ask is the size of the opposite best bid. Depth is reported per bid side;
the YES-ask depth is the NO-bid depth and vice versa."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from ge.ingest.prices import CENTICENTS_PER_DOLLAR, dollars_to_cc


@dataclass(frozen=True)
class BookSummary:
    """SHD-16: best bids and asks (centicents), their sizes and the depth within the window."""

    yes_bid_cc: int | None
    yes_bid_size: float | None
    no_bid_cc: int | None
    no_bid_size: float | None
    yes_ask_cc: int | None
    yes_ask_size: float | None
    no_ask_cc: int | None
    no_ask_size: float | None
    spread_cc: int | None
    yes_bid_depth: float
    no_bid_depth: float


def _side(
    levels: Sequence[Sequence[str]], window_cc: int
) -> tuple[int | None, float | None, float]:
    qty: dict[int, Decimal] = {}
    for price, q in levels:
        cc = dollars_to_cc(price)
        qty[cc] = qty.get(cc, Decimal(0)) + Decimal(q)
    if not qty:
        return None, None, 0.0
    best = max(qty)
    depth = sum((q for cc, q in qty.items() if cc >= best - window_cc), Decimal(0))
    return best, float(qty[best]), float(depth)


def book_summary(
    orderbook_fp: Mapping[str, Sequence[Sequence[str]]], window_cc: int
) -> BookSummary:
    """SHD-16 / EDG-01: summarise one order book. window_cc is EDG-04's 2¢ depth window."""
    yb, ybs, yd = _side(orderbook_fp.get("yes_dollars") or [], window_cc)
    nb, nbs, nd = _side(orderbook_fp.get("no_dollars") or [], window_cc)
    yes_ask = None if nb is None else CENTICENTS_PER_DOLLAR - nb
    no_ask = None if yb is None else CENTICENTS_PER_DOLLAR - yb
    spread = None if yes_ask is None or yb is None else yes_ask - yb
    return BookSummary(yb, ybs, nb, nbs, yes_ask, nbs, no_ask, ybs, spread, yd, nd)
