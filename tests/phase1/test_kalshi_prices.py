"""DATA-08 / EDG-01: YES ask = $1 - best NO bid, NO ask = $1 - best YES bid, in integer centicents.

Expected values are Kalshi's own yes_ask_dollars / no_ask_dollars from the market record
captured in the same second as the book, not recomputed here.
"""

import pytest

from ge.ingest.prices import book_asks, dollars_to_cc
from tests.phase1.conftest import load_fixture


def test_dollar_strings_convert_exactly() -> None:
    assert dollars_to_cc("0.1500") == 1500
    assert dollars_to_cc("1.0000") == 10000
    assert dollars_to_cc("0.0001") == 1
    assert dollars_to_cc("0") == 0


@pytest.mark.parametrize("bad", ["0.00005", "abc", "", "-0.0100", "1.0001"])
def test_bad_dollar_strings_raise(bad: str) -> None:
    with pytest.raises(ValueError):
        dollars_to_cc(bad)


def test_real_book_gives_kalshis_own_asks() -> None:
    fx = load_fixture("kalshi_orderbook.json")
    yes_ask, no_ask = book_asks(fx["response"]["orderbook_fp"])
    assert yes_ask == dollars_to_cc(fx["market"]["yes_ask_dollars"])
    assert no_ask == dollars_to_cc(fx["market"]["no_ask_dollars"])
    assert isinstance(yes_ask, int)
    assert isinstance(no_ask, int)


def test_empty_side_has_no_ask() -> None:
    fx = load_fixture("kalshi_orderbook.json")
    book = dict(fx["response"]["orderbook_fp"])
    book["no_dollars"] = []
    yes_ask, no_ask = book_asks(book)
    assert yes_ask is None  # no NO bids -> nothing to buy YES from
    assert no_ask == dollars_to_cc(fx["market"]["no_ask_dollars"])
