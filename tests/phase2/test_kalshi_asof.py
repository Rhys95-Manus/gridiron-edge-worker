"""BT-01 Kalshi prices as of a past moment, from real 2025 hourly candles (fixture)."""

import datetime as dt
import json
from decimal import Decimal

import polars as pl

from ge.config import load_params
from ge.store.known_at import (
    STATIC_MARKET_COLUMNS,
    candle_prices_as_of,
    default_as_of,
    kalshi_ingest_week,
    market_metadata_only,
    trades_as_of,
    with_kickoff,
)
from tests.phase2.conftest import load_json_fixture, load_parquet_fixture

BT = load_params().backtest


def _candles() -> tuple[pl.DataFrame, dict]:
    fx = load_json_fixture("kalshi_candles_2025w10.json")
    rows = [
        {
            "ticker": m["market"]["ticker"],
            "raw_json": json.dumps(c),
            "end_period_ts": c["end_period_ts"],
        }
        for m in fx["markets"]
        for c in m["response"]["candlesticks"]
    ]
    return pl.DataFrame(rows), fx


def _cc(v: str | None) -> int | None:
    return None if v is None else int(Decimal(v) * 10_000)


def test_prices_as_of_kickoff_minus_24h_come_from_last_closed_candle() -> None:
    candles, fx = _candles()
    sched = with_kickoff(load_parquet_fixture("schedules_2023_2026"))
    k = sched.filter(pl.col("game_id") == fx["game_id"])["kickoff_utc"][0]
    as_of = default_as_of(k, "decision", BT)
    got = candle_prices_as_of(candles, as_of)
    assert got.height == len(fx["markets"])
    assert got["yes_bid_cc"].dtype == pl.Int64 and got["yes_ask_cc"].dtype == pl.Int64
    for m in fx["markets"]:
        cs = [c for c in m["response"]["candlesticks"] if c["end_period_ts"] <= as_of.timestamp()]
        last = max(cs, key=lambda c: c["end_period_ts"])
        row = got.filter(pl.col("ticker") == m["market"]["ticker"]).row(0, named=True)
        assert row["candle_end_utc"] == dt.datetime.fromtimestamp(last["end_period_ts"], dt.UTC)
        assert row["yes_bid_cc"] == _cc(last["yes_bid"]["close"])
        assert row["yes_ask_cc"] == _cc(last["yes_ask"]["close"])
        assert row["candle_end_utc"] <= as_of


def test_no_price_before_first_candle() -> None:
    candles, _ = _candles()
    first = dt.datetime.fromtimestamp(candles["end_period_ts"].min(), dt.UTC)
    assert candle_prices_as_of(candles, first - dt.timedelta(seconds=1)).is_empty()


def test_trades_as_of_keeps_only_earlier_trades() -> None:
    trades = pl.DataFrame(
        {
            "ticker": ["T", "T", "T"],
            "trade_id": ["a", "b", "c"],
            "created_time": [
                "2025-11-09T00:00:00Z",
                "2025-11-09T01:00:00.5Z",
                "2025-11-09T02:00:00Z",
            ],
        }
    )
    got = trades_as_of(trades, dt.datetime(2025, 11, 9, 1, 0, 0, 500000, tzinfo=dt.UTC))
    assert got["trade_id"].to_list() == ["a", "b"]


def test_ingest_week_from_column_or_older_source_text() -> None:
    new = pl.DataFrame({"ticker": ["A"], "nfl_week": [10], "source": ["anything"]})
    assert kalshi_ingest_week(new).to_list() == [10]
    # Rows written before nfl_week existed carry the week in their source (Phase 1 ingest).
    old = pl.DataFrame(
        {
            "ticker": ["A", "B"],
            "source": ["Kalshi public API (DATA-08) week 4", "Kalshi public API (DATA-08) week 12"],
        }
    )
    assert kalshi_ingest_week(old).to_list() == [4, 12]


def test_market_rows_pulled_after_as_of_keep_static_fields_only() -> None:
    _, fx = _candles()
    m = fx["markets"][0]["market"]
    stored = pl.DataFrame(
        [
            {
                "ticker": m["ticker"],
                "event_ticker": m["event_ticker"],
                "series_ticker": "KXNFLGAME",
                "status": m["status"],
                "yes_sub_title": m.get("yes_sub_title"),
                "occurs_at": None,
                "close_time": m["close_time"],
                "yes_ask_cc": None,
                "no_ask_cc": None,
                "volume_fp": m.get("volume_fp"),
                "rules_primary": m["rules_primary"],
                "rules_secondary": m.get("rules_secondary"),
                "raw_json": json.dumps(m),
            }
        ]
    )
    out = market_metadata_only(stored)
    assert list(out.columns) == [c for c in stored.columns if c in STATIC_MARKET_COLUMNS]
    assert "raw_json" not in out.columns and "status" not in out.columns
    assert out["rules_primary"][0] == m["rules_primary"]
