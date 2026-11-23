"""SHD-05 closing price and SHD-13 results.

SHD-05: "The YES price of the last trade created after the snapshot was taken and before
kickoff. No such trade before kickoff: no_trade. Last pre-kickoff trade at or before the
snapshot: stale. ... Last pre-kickoff trades with the same time but different prices:
ambiguous_last_trade". Edge-case trades are synthetic, shaped as docs.kalshi.com GET
/markets/trades documents them (trade_id, ticker, count_fp, yes_price_dollars,
no_price_dollars, created_time). shadow_real_closes.json holds closes rows written live by
`ge shadow close` (anonymised); the store keeps no raw trades, so those tests check the live
rows against SHD-05 and rebuild trades at their real timestamps.
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


REAL = load_fixture("shadow_real_closes.json")["closes"]


def _ts(v: str | None) -> dt.datetime | None:
    return None if v is None else dt.datetime.fromisoformat(v)


def test_real_fixture_covers_every_close_status() -> None:
    assert {r["close_status"] for r in REAL} == {"ok", "stale", "no_trade", "ambiguous_last_trade"}


@pytest.mark.parametrize("row", REAL, ids=lambda r: f"{r['close_status']}-{r['ticker']}")
def test_live_closes_obey_shd05(row: dict[str, Any]) -> None:
    """The rows `ge shadow close` wrote on the live store follow SHD-05's definitions."""
    taken, kick, last = _ts(row["taken_ts"]), _ts(row["kickoff_utc"]), _ts(row["last_trade_ts"])
    assert taken is not None and kick is not None and taken < kick
    status, price, n = row["close_status"], row["close_yes_cc"], row["n_pre_kickoff_trades"]
    if status == "no_trade":
        assert (price, last, n) == (None, None, 0)
        return
    assert last is not None and last < kick and n >= 1
    if status == "ok":
        assert taken < last and isinstance(price, int) and 0 < price < 10000
    elif status == "stale":
        assert last <= taken and price is None
    else:  # ambiguous_last_trade: two last trades, so at least two pre-kickoff trades
        assert taken < last and price is None and n >= 2


@pytest.mark.parametrize("row", REAL, ids=lambda r: f"{r['close_status']}-{r['ticker']}")
def test_closing_price_reproduces_live_rows_at_real_timestamps(row: dict[str, Any]) -> None:
    """Trades rebuilt from each live row (the store keeps no raw trades) at the row's real
    microsecond timestamps give back the stored status, price and last-trade time."""
    taken, kick, last = _ts(row["taken_ts"]), _ts(row["kickoff_utc"]), _ts(row["last_trade_ts"])
    assert taken is not None and kick is not None
    status, n = row["close_status"], row["n_pre_kickoff_trades"]
    us = dt.timedelta(microseconds=1)
    after_kick = [trade(kick, "0.9900", "after"), trade(kick + us, "0.0100", "after2")]
    if status == "no_trade":
        c = closing_price(after_kick, kick, taken)
        assert (c.status, c.close_yes_cc, c.last_trade_ts, c.n_pre_kickoff) == (
            "no_trade",
            None,
            None,
            0,
        )
        return
    assert last is not None
    if status == "ambiguous_last_trade":
        lasts = [trade(last, "0.4000", "l1"), trade(last, "0.4100", "l2")]
    else:
        price = row["close_yes_cc"] if status == "ok" else 5000
        lasts = [trade(last, f"{price / 10000:.4f}", "l1")]
    earlier = [trade(last - (i + 1) * us, "0.5000", f"e{i}") for i in range(n - len(lasts))]
    c = closing_price([*earlier, *lasts, *after_kick], kick, taken)
    assert (c.status, c.close_yes_cc, c.last_trade_ts, c.n_pre_kickoff) == (
        status,
        row["close_yes_cc"],
        last,
        n,
    )


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
