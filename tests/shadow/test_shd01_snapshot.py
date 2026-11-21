"""SHD-01 / SHD-10 / SHD-16 / SHD-19: one game's snapshot, against the saved 2026 fixture.

Every market in the three series for the game is logged, unpriced with reason
pricer_not_frozen, with its PRV-01 scope result, its PRV-02 map result and its order-book
prices (never the /markets record's)."""

import copy
import datetime as dt
import json
from collections import Counter
from collections.abc import Iterator
from typing import Any

import pytest

from ge.pricer_v0.scope import load_team_codes
from ge.pricer_v0.teams import ScheduleGame, TeamMapError, load_team_map
from ge.shadow.book import book_summary
from ge.shadow.schedule import GameKick, SnapshotType, Window
from ge.shadow.snapshot import MapResult, take_snapshot
from ge.store.known_at import kickoff_utc
from tests.shadow.conftest import load_fixture

FIX = load_fixture("kalshi_shadow_game.json")
GAME_ID = "2026_11_ARI_KC"
ROW = next(r for r in FIX["schedules"] if r["game_id"] == GAME_ID)
K = kickoff_utc(ROW["gameday"], ROW["gametime"])
GAME = GameKick(GAME_ID, ROW["season"], ROW["week"], K)
GAMES = [ScheduleGame.from_row(r) for r in FIX["schedules"]]
W = Window(
    SnapshotType.T24H,
    K - dt.timedelta(hours=24),
    K - dt.timedelta(hours=24, minutes=15),
    K - dt.timedelta(hours=23),
)
TAKEN = W.target + dt.timedelta(minutes=2)


class FakeKalshi:
    """The two public endpoints a snapshot uses, from the fixture; logs every request."""

    def __init__(self, markets: list[dict[str, Any]], books: dict[str, Any]) -> None:
        self._markets = markets
        self._books = books
        self.requests: list[tuple[str, Any]] = []

    def markets(self, **filters: Any) -> Iterator[dict[str, Any]]:
        self.requests.append(("markets", filters))
        yield from (m for m in self._markets if m["series_ticker"] == filters["series_ticker"])

    def orderbook(self, ticker: str) -> dict[str, Any]:
        self.requests.append(("orderbook", ticker))
        return copy.deepcopy(self._books.get(ticker, {"yes_dollars": [], "no_dollars": []}))


class FakeMapper:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int]] = []

    def __call__(self, name: str, team: str, week: int) -> MapResult:
        self.calls.append((name, team, week))
        if name == "Player 01":
            return MapResult(True, None, "00-0000001", "ARI", week, None)
        return MapResult(False, "no_match", None, None, None, None)


def _snap(k: FakeKalshi, mapper: FakeMapper | None = None, **kw: Any) -> Any:
    return take_snapshot(
        k,
        GAME,
        W,
        games=kw.get("games", GAMES),
        team_codes=load_team_codes(),
        team_map=kw.get("team_map", load_team_map()),
        mapper=mapper or FakeMapper(),
        clock=lambda: TAKEN,
        code_commit="abc123",
    )


def _all() -> FakeKalshi:
    return FakeKalshi(FIX["markets"] + FIX["settled"], FIX["orderbooks"])


def test_every_market_of_the_game_is_logged_once() -> None:
    k = _all()
    snap = _snap(k)
    assert snap.outcome == "ok"
    tickers = [r["ticker"] for r in snap.rows]
    assert sorted(tickers) == sorted(m["ticker"] for m in FIX["markets"])
    assert len(tickers) == len(set(tickers)) == snap.n_markets
    assert Counter(r["series"] for r in snap.rows) == Counter(
        m["series_ticker"] for m in FIX["markets"]
    )


def test_requests_are_markets_per_series_and_one_book_per_market() -> None:
    k = _all()
    _snap(k)
    kinds = Counter(kind for kind, _ in k.requests)
    assert kinds == {"markets": 3, "orderbook": len(FIX["markets"])}
    assert {f["series_ticker"] for kind, f in k.requests if kind == "markets"} == {
        "KXNFLRECYDS",
        "KXNFLRSHYDS",
        "KXNFLREC",
    }
    for kind, f in k.requests:
        if kind == "markets":
            assert f["min_close_ts"] == int(K.timestamp())


def test_rows_are_unpriced_pricer_not_frozen_live() -> None:
    snap = _snap(_all())
    for r in snap.rows:
        assert r["priced"] is False and r["p_yes"] is None and r["action"] is None
        assert r["unpriced_reason"] == "pricer_not_frozen"
        assert r["pricing_mode"] == "live"
        assert r["game_id"] == GAME_ID and r["snapshot_type"] == "T-24h"
        assert r["kickoff_utc"] == K and r["target_ts"] == W.target and r["taken_ts"] == TAKEN
        assert r["lateness_s"] == 120.0
        assert r["code_commit"] == "abc123"
        assert r["market_json"]  # the full record, for SHD-19 after-the-fact pricing


def test_prv01_and_prv02_results_on_every_row() -> None:
    mapper = FakeMapper()
    snap = _snap(_all(), mapper)
    in_scope = [r for r in snap.rows if r["prv01_in_scope"]]
    assert in_scope and all(r["prv01_reason"] is None for r in in_scope)
    assert all(r["x"] == int(r["floor_strike"] + 0.5) for r in in_scope)
    p1 = [r for r in snap.rows if r["ticker"].split("-")[2] == "ARIPLAYER01"]
    assert p1 and all(r["prv02_mapped"] and r["gsis_id"] == "00-0000001" for r in p1)
    others = [r for r in in_scope if r not in p1]
    assert all(r["prv02_mapped"] is False and r["prv02_reason"] == "no_match" for r in others)
    # one map call per (player, team), not per strike
    assert len(mapper.calls) == len(set(mapper.calls))
    assert {c[2] for c in mapper.calls} == {GAME.week}


def test_out_of_scope_market_gets_prv01_reason_and_no_map() -> None:
    m = copy.deepcopy(FIX["markets"][0])
    m["strike_type"] = "between"
    k = FakeKalshi([m], FIX["orderbooks"])
    [r] = _snap(k).rows
    assert r["prv01_in_scope"] is False and r["prv01_reason"] == "strike_type_not_greater"
    assert r["prv02_mapped"] is None and r["prv02_reason"] is None


def test_book_prices_come_from_the_order_book_not_the_markets_list() -> None:
    m = copy.deepcopy(FIX["markets"][0])
    book = FIX["orderbooks"][m["ticker"]]
    m["yes_ask_dollars"], m["yes_bid_dollars"] = "0.9900", "0.0100"
    [r] = _snap(FakeKalshi([m], FIX["orderbooks"])).rows
    s = book_summary(book, 200)
    assert (r["yes_bid_cc"], r["yes_ask_cc"]) == (s.yes_bid_cc, s.yes_ask_cc)
    assert r["yes_ask_cc"] != 9900


def test_book_levels_rows() -> None:
    snap = _snap(_all())
    n_levels = sum(len(b["yes_dollars"]) + len(b["no_dollars"]) for b in FIX["orderbooks"].values())
    assert len(snap.book_rows) == n_levels
    r = snap.book_rows[0]
    assert set(r) >= {
        "game_id",
        "kickoff_utc",
        "snapshot_type",
        "taken_ts",
        "ticker",
        "side",
        "bid_cc",
        "qty",
    }
    assert snap.n_books == len(FIX["orderbooks"])


def test_book_summary_best_sizes_depth_spread() -> None:
    """SHD-16 / EDG-01, on the first fixture market's downloaded book."""
    book = FIX["orderbooks"][FIX["markets"][0]["ticker"]]
    s = book_summary(book, 200)
    best_yes = max(book["yes_dollars"], key=lambda lv: float(lv[0]))
    best_no = max(book["no_dollars"], key=lambda lv: float(lv[0]))
    yb, nb = round(float(best_yes[0]) * 10000), round(float(best_no[0]) * 10000)
    assert (s.yes_bid_cc, s.no_bid_cc) == (yb, nb)
    assert (s.yes_ask_cc, s.no_ask_cc) == (10000 - nb, 10000 - yb)
    assert (s.yes_bid_size, s.no_bid_size) == (float(best_yes[1]), float(best_no[1]))
    assert s.yes_ask_size == s.no_bid_size and s.no_ask_size == s.yes_bid_size
    assert s.spread_cc == s.yes_ask_cc - s.yes_bid_cc
    within = lambda side, best: sum(  # noqa: E731
        float(q) for p, q in book[side] if round(float(p) * 10000) >= best - 200
    )
    assert s.yes_bid_depth == pytest.approx(within("yes_dollars", yb))
    assert s.no_bid_depth == pytest.approx(within("no_dollars", nb))
    # the fixture market's /markets record agrees with its book (same pull)
    m = FIX["markets"][0]
    assert s.yes_ask_cc == round(float(m["yes_ask_dollars"]) * 10000)


def test_book_summary_empty_side() -> None:
    s = book_summary({"yes_dollars": [["0.4000", "5.00"]], "no_dollars": []}, 200)
    assert s.yes_bid_cc == 4000 and s.no_ask_cc == 6000
    assert s.no_bid_cc is None and s.yes_ask_cc is None and s.spread_cc is None
    assert s.no_bid_depth == 0.0


def test_no_markets_for_the_game() -> None:
    other = [m for m in FIX["settled"]]
    snap = _snap(FakeKalshi(other, {}))
    assert snap.outcome == "no_markets" and snap.rows == [] and snap.n_markets == 0


def test_event_with_no_schedules_game_is_left_out() -> None:
    games = [g for g in GAMES if g.game_id != GAME_ID]
    snap = _snap(_all(), games=games)
    assert snap.outcome == "no_markets"


def test_team_code_missing_from_config_stops_the_run() -> None:
    """PRV-02: "A configuration error (a Kalshi team code missing from
    config/kalshi_team_codes.yaml) stops the run." """
    tm = {k: v for k, v in load_team_map().items() if k != "ARI"}
    with pytest.raises(TeamMapError):
        _snap(_all(), team_map=tm)


def test_roster_data_gap_leaves_markets_unpriced_and_continues() -> None:
    def gap(name: str, team: str, week: int) -> MapResult:
        return MapResult(False, "no_roster_pull", None, None, None, None)

    snap = take_snapshot(
        _all(),
        GAME,
        W,
        games=GAMES,
        team_codes=load_team_codes(),
        team_map=load_team_map(),
        mapper=gap,
        clock=lambda: TAKEN,
        code_commit=None,
    )
    scoped = [r for r in snap.rows if r["prv01_in_scope"]]
    assert scoped and {r["prv02_reason"] for r in scoped} == {"no_roster_pull"}


class LiveShapeKalshi(FakeKalshi):
    """Live GET /markets records carry no series_ticker key (seen in the first live tick,
    2026-11-21: all 174 stored market records lack it). The request's series_ticker filter is
    the only place the series appears; the event ticker's prefix is used here to answer it."""

    def __init__(self, markets: list[dict[str, Any]], books: dict[str, Any]) -> None:
        live = [{k: v for k, v in m.items() if k != "series_ticker"} for m in markets]
        super().__init__(live, books)

    def markets(self, **filters: Any) -> Iterator[dict[str, Any]]:
        self.requests.append(("markets", filters))
        yield from (
            copy.deepcopy(m)
            for m in self._markets
            if m["event_ticker"].split("-")[0] == filters["series_ticker"]
        )


def test_live_records_without_series_ticker_take_the_requested_series() -> None:
    expected = {r["ticker"]: r for r in _snap(_all()).rows}
    snap = _snap(LiveShapeKalshi(FIX["markets"] + FIX["settled"], FIX["orderbooks"]))
    assert len(snap.rows) == len(expected)
    for r in snap.rows:
        e = expected[r["ticker"]]
        assert r["series"] == e["series"] == r["event_ticker"].split("-")[0]
        assert (r["prv01_in_scope"], r["prv01_reason"]) == (e["prv01_in_scope"], e["prv01_reason"])
        assert (r["prv02_mapped"], r["prv02_reason"]) == (e["prv02_mapped"], e["prv02_reason"])
        # market_json stays the record as received: no series_ticker added
        assert "series_ticker" not in json.loads(r["market_json"])
    assert any(r["prv01_in_scope"] for r in snap.rows)
