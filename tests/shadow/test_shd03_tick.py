"""SHD-03 / SHD-12 / SHD-05 / SHD-13: the tick, close and settle jobs end to end, on a fake
clock, fake Kalshi endpoints (saved 2026 fixture) and a temporary shadow store."""

import copy
import datetime as dt
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import polars as pl
import pytest

from ge.shadow.reader import read_table
from ge.shadow.snapshot import MapResult
from ge.shadow.store import ShadowStore, verify_store
from ge.shadow.tick import TickDeps, run_close, run_settle, run_tick
from ge.store.known_at import kickoff_utc
from tests.shadow.conftest import load_fixture

FIX = load_fixture("kalshi_shadow_game.json")
GAME_ID = "2026_11_ARI_KC"
ROW = next(r for r in FIX["schedules"] if r["game_id"] == GAME_ID)
K = kickoff_utc(ROW["gameday"], ROW["gametime"])
H = dt.timedelta(hours=1)
M = dt.timedelta(minutes=1)
SCHED_PULLED = K - 25 * H
# Two games: the fixture game and a later one on the same day with no markets in the fake.
LATE_ID = "2026_11_LV_DEN"
SCHED = pl.DataFrame([r for r in FIX["schedules"] if r["game_id"] in (GAME_ID, LATE_ID)])


class Clock:
    def __init__(self, t: dt.datetime) -> None:
        self.t = t

    def __call__(self) -> dt.datetime:
        self.t += dt.timedelta(milliseconds=1)
        return self.t


class FakeKalshi:
    def __init__(self, fail: bool = False) -> None:
        self.markets_by_event: dict[str, list[dict[str, Any]]] = {}
        self.requests: Counter[str] = Counter()
        self.fail = fail
        self.trades_by_ticker: dict[str, list[dict[str, Any]]] = {}
        self.final: dict[str, dict[str, Any]] = {}

    def markets(self, **f: Any) -> Iterator[dict[str, Any]]:
        self.requests["markets"] += 1
        if self.fail:
            req = httpx.Request("GET", "https://example.invalid/markets")
            raise httpx.HTTPStatusError(
                "503", request=req, response=httpx.Response(503, request=req)
            )
        if "event_ticker" in f:
            yield from (
                self.final.get(m["ticker"], m)
                for m in FIX["markets"]
                if m["event_ticker"] == f["event_ticker"]
            )
            return
        yield from (m for m in FIX["markets"] if m["series_ticker"] == f["series_ticker"])

    def historical_markets(self, **f: Any) -> Iterator[dict[str, Any]]:
        self.requests["historical_markets"] += 1
        return iter(())

    def orderbook(self, ticker: str) -> dict[str, Any]:
        self.requests["orderbook"] += 1
        return copy.deepcopy(FIX["orderbooks"][ticker])

    def trades(
        self, ticker: str, min_ts: int | None = None, max_ts: int | None = None
    ) -> Iterator[dict[str, Any]]:
        self.requests["trades"] += 1
        assert max_ts is not None and max_ts > int(K.timestamp())
        return iter(self.trades_by_ticker.get(ticker, []))


def _mapper(season: int, as_of: dt.datetime) -> Any:
    def m(name: str, team: str, week: int) -> MapResult:
        return MapResult(False, "no_match", None, None, None, None)

    return m


def _deps(
    tmp_path: Path, k: FakeKalshi, now: dt.datetime, pulls: list[int] | None = None
) -> TickDeps:
    pulls = pulls if pulls is not None else []

    def pull(season: int) -> pl.DataFrame:
        pulls.append(season)
        return SCHED

    clock = Clock(now)
    return TickDeps(
        store=ShadowStore("0", root=tmp_path, base=tmp_path, clock=clock),
        kalshi=k,
        clock=clock,
        season=2026,
        raw_schedules=lambda season: (SCHED, SCHED_PULLED),
        pull_schedules=pull,
        mapper_factory=_mapper,
        code_commit="abc",
    )


def _status(tmp_path: Path) -> pl.DataFrame:
    return read_table(tmp_path / "v0", "snapshot_status")


def test_tick_takes_the_due_snapshot(tmp_path: Path) -> None:
    k = FakeKalshi()
    rep = run_tick(_deps(tmp_path, k, K - 24 * H - M))  # one minute early: ok, not ok_late
    snaps = read_table(tmp_path / "v0", "snapshots")
    assert snaps.height == len(FIX["markets"])
    assert set(snaps["game_id"]) == {GAME_ID} and set(snaps["snapshot_type"]) == {"T-24h"}
    st = _status(tmp_path)
    assert st.select("game_id", "snapshot_type", "status").rows() == [(GAME_ID, "T-24h", "ok")]
    assert k.requests["orderbook"] == len(FIX["markets"])
    assert rep.snapshots_ok == 1
    assert verify_store(tmp_path, "0") == []
    # partitioned by the game's season and week
    assert list((tmp_path / "v0" / "snapshots").glob("season=2026/week=11/written_at=*"))


def test_second_tick_does_not_retake(tmp_path: Path) -> None:
    k = FakeKalshi()
    run_tick(_deps(tmp_path, k, K - 24 * H))
    n = k.requests["orderbook"]
    run_tick(_deps(tmp_path, k, K - 24 * H + 5 * M))
    assert k.requests["orderbook"] == n
    assert read_table(tmp_path / "v0", "snapshots").height == len(FIX["markets"])


def test_no_markets_then_missed_no_markets(tmp_path: Path) -> None:
    late = kickoff_utc(
        *next((r["gameday"], r["gametime"]) for r in FIX["schedules"] if r["game_id"] == LATE_ID)
    )
    k = FakeKalshi()
    run_tick(_deps(tmp_path, k, late - 24 * H))
    att = read_table(tmp_path / "v0", "attempts")
    assert att.filter(pl.col("game_id") == LATE_ID)["outcome"].to_list() == ["no_markets"]
    run_tick(_deps(tmp_path, k, late - 23 * H + M))
    st = _status(tmp_path).filter(pl.col("game_id") == LATE_ID)
    assert st.select("snapshot_type", "status").rows() == [("T-24h", "missed_no_markets")]


def test_api_error_then_missed_api_error(tmp_path: Path) -> None:
    run_tick(_deps(tmp_path, FakeKalshi(fail=True), K - 24 * H))
    att = read_table(tmp_path / "v0", "attempts").filter(pl.col("game_id") == GAME_ID)
    assert att["outcome"].to_list() == ["api_error"]
    run_tick(_deps(tmp_path, FakeKalshi(), K - 23 * H + M))
    st = _status(tmp_path).filter(pl.col("game_id") == GAME_ID)
    assert st.select("snapshot_type", "status").rows() == [("T-24h", "missed_api_error")]


def test_schedules_repulled_into_the_store_when_older_than_6h(tmp_path: Path) -> None:
    pulls: list[int] = []
    run_tick(_deps(tmp_path, FakeKalshi(), K - 24 * H, pulls))  # stored copy 1 h old
    assert pulls == []
    deps = _deps(tmp_path, FakeKalshi(), SCHED_PULLED + 6 * H + M, pulls)
    run_tick(deps)
    assert pulls == [2026]
    stored = read_table(tmp_path / "v0", "schedules")
    assert stored.height == SCHED.height
    run_tick(_deps(tmp_path, FakeKalshi(), SCHED_PULLED + 7 * H, pulls))  # shadow copy is fresh
    assert pulls == [2026]


def test_kickoff_from_newest_stored_schedules(tmp_path: Path) -> None:
    """A newer shadow-store pull that moves the game wins over the older raw copy."""
    moved = SCHED.with_columns(
        pl.when(pl.col("game_id") == GAME_ID)
        .then(pl.lit("16:05"))
        .otherwise(pl.col("gametime"))
        .alias("gametime")
    )
    old_raw = K - 34 * H

    def deps_at(now: dt.datetime, k: FakeKalshi) -> TickDeps:
        d = _deps(tmp_path, k, now)
        d.raw_schedules = lambda season: (SCHED, old_raw)
        d.pull_schedules = lambda season: moved
        return d

    run_tick(deps_at(K - 27 * H, FakeKalshi()))  # raw copy 7 h old: re-pull, kickoff K + 3h05
    assert read_table(tmp_path / "v0", "schedules").height == SCHED.height
    k = FakeKalshi()
    run_tick(deps_at(K - 24 * H, k))  # the old target: nothing due
    assert k.requests["orderbook"] == 0
    run_tick(deps_at(K + 3 * H + 5 * M - 24 * H, k))  # the new target
    assert k.requests["orderbook"] == len(FIX["markets"])


def test_close_after_kickoff_once(tmp_path: Path) -> None:
    k = FakeKalshi()
    run_tick(_deps(tmp_path, k, K - 24 * H))
    t0 = FIX["markets"][0]["ticker"]
    k.trades_by_ticker[t0] = [
        {
            "trade_id": "a",
            "ticker": t0,
            "count_fp": "1.00",
            "yes_price_dollars": "0.4500",
            "no_price_dollars": "0.5500",
            "created_time": (K - M).isoformat().replace("+00:00", "Z"),
        }
    ]
    assert run_close(_deps(tmp_path, k, K - M)) == 0  # before kickoff: nothing
    n = run_close(_deps(tmp_path, k, K + H))
    closes = read_table(tmp_path / "v0", "closes")
    assert n == closes.height == len(FIX["markets"])
    row = closes.filter(pl.col("ticker") == t0).row(0, named=True)
    assert (row["close_status"], row["close_yes_cc"]) == ("ok", 4500)
    assert Counter(closes["close_status"])["no_trade"] == len(FIX["markets"]) - 1
    assert k.requests["trades"] == len(FIX["markets"])
    assert run_close(_deps(tmp_path, k, K + 2 * H)) == 0
    assert verify_store(tmp_path, "0") == []


def test_settle_writes_results_once(tmp_path: Path) -> None:
    k = FakeKalshi()
    run_tick(_deps(tmp_path, k, K - 24 * H))
    run_close(_deps(tmp_path, k, K + H))
    assert run_settle(_deps(tmp_path, k, K + 2 * H)) == 0  # all still active
    yes = next(m for m in FIX["settled"] if m["result"] == "yes")
    scalar = next(m for m in FIX["settled"] if m["result"] == "scalar")
    t0, t1 = FIX["markets"][0]["ticker"], FIX["markets"][1]["ticker"]
    k.final[t0] = {
        **FIX["markets"][0],
        **{f: yes[f] for f in ("status", "result", "settlement_value_dollars")},
    }
    k.final[t1] = {
        **FIX["markets"][1],
        **{f: scalar[f] for f in ("status", "result", "settlement_value_dollars")},
    }
    assert run_settle(_deps(tmp_path, k, K + 5 * H)) == 2
    res = read_table(tmp_path / "v0", "results")
    got = {r["ticker"]: (r["result_status"], r["result_value"]) for r in res.iter_rows(named=True)}
    assert got == {t0: ("yes", 1), t1: ("not_binary", None)}
    assert run_settle(_deps(tmp_path, k, K + 6 * H)) == 0
    assert verify_store(tmp_path, "0") == []


@pytest.mark.parametrize("table", ["snapshots", "closes"])
def test_empty_store_reads_as_empty(tmp_path: Path, table: str) -> None:
    assert read_table(tmp_path / "v0", table).is_empty()
