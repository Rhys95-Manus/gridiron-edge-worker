"""SHD-05 closing price and SHD-13 results.

SHD-05: "The YES price of the last trade created after the snapshot was taken and before
kickoff. No such trade before kickoff: no_trade. Last pre-kickoff trade at or before the
snapshot: stale." Trades are synthetic, shaped as docs.kalshi.com GET /markets/trades
documents them (trade_id, ticker, count_fp, yes_price_dollars, no_price_dollars,
created_time); no live trades response is saved yet (open question in session4-report.md).
SHD-13: "The result is Kalshi's settled result. A fair-price settlement or a void is
not_binary." Settled markets come from the saved 2026 fixture."""

import datetime as dt
from typing import Any

import pytest

from ge.shadow.close import closing_price
from ge.shadow.settle import settle_value
from tests.shadow.conftest import load_fixture

K = dt.datetime(2026, 11, 22, 18, 0, tzinfo=dt.UTC)
TAKEN = K - dt.timedelta(hours=24)
S = dt.timedelta(seconds=1)


def trade(ts: dt.datetime, yes: str, tid: str = "t") -> dict[str, Any]:
    no = f"{1 - float(yes):.4f}"
    return {
        "trade_id": tid,
        "ticker": "X",
        "count_fp": "1.00",
        "yes_price_dollars": yes,
        "no_price_dollars": no,
        "created_time": ts.isoformat().replace("+00:00", "Z"),
    }


def test_last_trade_after_snapshot_before_kickoff() -> None:
    c = closing_price(
        [
            trade(TAKEN + S, "0.4000", "a"),
            trade(K - S, "0.4500", "b"),
            trade(K - 2 * S, "0.4400", "c"),
        ],
        K,
        TAKEN,
    )
    assert (c.status, c.close_yes_cc, c.last_trade_id) == ("ok", 4500, "b")
    assert c.last_trade_ts == K - S and c.n_pre_kickoff == 3


def test_trades_at_or_after_kickoff_are_ignored() -> None:
    c = closing_price(
        [trade(TAKEN + S, "0.4000"), trade(K, "0.9000"), trade(K + S, "0.9500")], K, TAKEN
    )
    assert (c.status, c.close_yes_cc) == ("ok", 4000)


def test_no_trade() -> None:
    assert closing_price([], K, TAKEN).status == "no_trade"
    c = closing_price([trade(K + S, "0.5000")], K, TAKEN)
    assert (c.status, c.close_yes_cc) == ("no_trade", None)


@pytest.mark.parametrize("at", [TAKEN, TAKEN - S])
def test_stale_when_last_pre_kickoff_trade_is_at_or_before_snapshot(at: dt.datetime) -> None:
    c = closing_price([trade(at, "0.4000")], K, TAKEN)
    assert (c.status, c.close_yes_cc) == ("stale", None)
    assert c.last_trade_ts == at


def test_tied_last_trades_with_different_prices_are_ambiguous() -> None:
    c = closing_price([trade(K - S, "0.4000", "a"), trade(K - S, "0.4100", "b")], K, TAKEN)
    assert (c.status, c.close_yes_cc) == ("ambiguous_last_trade", None)
    same = closing_price([trade(K - S, "0.4000", "a"), trade(K - S, "0.4000", "b")], K, TAKEN)
    assert (same.status, same.close_yes_cc) == ("ok", 4000)


def test_sub_centicent_price_raises() -> None:
    with pytest.raises(ValueError):
        closing_price([trade(K - S, "0.400001")], K, TAKEN)


SETTLED = {
    (m["status"], m["result"]): m for m in load_fixture("kalshi_shadow_game.json")["settled"]
}


def test_settled_yes_and_no() -> None:
    assert settle_value(SETTLED[("finalized", "yes")]) == ("yes", 1)
    assert settle_value(SETTLED[("finalized", "no")]) == ("no", 0)


def test_fair_price_settlement_is_not_binary() -> None:
    m = SETTLED[("finalized", "scalar")]
    assert m["settlement_value_dollars"] not in ("0.0000", "1.0000")
    assert settle_value(m) == ("not_binary", None)


def test_unsettled_market_has_no_result_yet() -> None:
    assert settle_value(SETTLED[("active", "")]) is None


def test_result_and_value_must_agree() -> None:
    m = {**SETTLED[("finalized", "yes")], "settlement_value_dollars": "0.0000"}
    assert settle_value(m) == ("not_binary", None)
