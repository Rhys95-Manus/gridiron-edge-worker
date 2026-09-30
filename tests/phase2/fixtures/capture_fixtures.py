"""Cut the real-data fixtures the phase2 unit tests use. Run once, by hand:

    uv run python tests/phase2/fixtures/capture_fixtures.py

nflverse slices come from the local raw store (data/raw, downloaded in Phase 1); the Kalshi
candles come straight from Kalshi's public historical endpoint with plain httpx, so fixtures
don't depend on the code under test. Every fixture has a <name>.meta.json recording its source
and pull time, per CLAUDE.md rule 2. Games are picked by rule, never typed by hand.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

import httpx
import polars as pl

HERE = Path(__file__).parent
REPO = HERE.parents[2]
RAW = REPO / "data" / "raw"
KALSHI = "https://external-api.kalshi.com/trade-api/v2"  # docs.kalshi.com quick start


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


def _latest(dataset: str, season: int) -> Path:
    parts = sorted((RAW / dataset / f"season={season}").glob("pulled_at=*/part.parquet"))
    if not parts:
        raise SystemExit(f"no {dataset} {season} in data/raw; run `uv run ge ingest nflverse`")
    return parts[-1]


def _save_parquet(name: str, df: pl.DataFrame, sources: list[Path], note: str) -> None:
    df.write_parquet(HERE / f"{name}.parquet")
    meta = {
        "source": [str(p.relative_to(REPO)).replace("\\", "/") for p in sources],
        "source_column": sorted(set(df["source"].to_list())) if "source" in df.columns else None,
        "pulled_at": sorted({str(v) for v in df["pulled_at"].to_list()})
        if "pulled_at" in df.columns
        else None,
        "cut_at": _now(),
        "rows": df.height,
        "note": note,
    }
    (HERE / f"{name}.meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print("wrote", name, df.shape)


def schedules() -> None:
    paths = [_latest("schedules", s) for s in (2023, 2024, 2025, 2026)]
    df = pl.concat([pl.read_parquet(p) for p in paths], how="diagonal")
    _save_parquet("schedules_2023_2026", df, paths, "full schedules, 2023-2026")


def _first_game(season: int) -> dict[str, Any]:
    s = pl.read_parquet(_latest("schedules", season)).sort(["gameday", "gametime", "game_id"])
    return s.row(0, named=True)


def depth_weekly() -> None:
    g = _first_game(2023)
    p = _latest("depth_charts", 2023)
    df = pl.read_parquet(p).filter(pl.col("club_code").is_in([g["away_team"], g["home_team"]]))
    _save_parquet(
        "depth_weekly_2023", df, [p], f"both teams of the first 2023 game ({g['game_id']})"
    )


def depth_espn() -> None:
    g = _first_game(2025)
    p = _latest("depth_charts", 2025)
    df = pl.read_parquet(p).filter(pl.col("team").is_in([g["away_team"], g["home_team"]]))
    _save_parquet("depth_espn_2025", df, [p], f"both teams of the first 2025 game ({g['game_id']})")


def pbp_times() -> None:
    p = _latest("pbp", 2024)
    df = pl.read_parquet(p, columns=["game_id", "play_id", "time_of_day", "pulled_at", "source"])
    _save_parquet(
        "pbp_time_of_day_2024", df, [p], "game_id, play_id, time_of_day for every 2024 play"
    )


def ngs() -> None:
    p = _latest("nextgen_passing", 2024)
    df = pl.read_parquet(p)
    # First team alphabetically that has both season-total (week 0) and postseason rows.
    has0 = set(df.filter(pl.col("week") == 0)["team_abbr"].to_list())
    post = set(df.filter(pl.col("season_type") == "POST")["team_abbr"].to_list())
    team = sorted(has0 & post)[0]
    df = df.filter(pl.col("team_abbr") == team)
    _save_parquet("nextgen_passing_2024_one_team", df, [p], f"every 2024 row for {team}")


def kalshi_candles() -> None:
    """Hourly candles for the last-kicking-off 2025 week-10 game's KXNFLGAME markets."""
    sched = pl.read_parquet(_latest("schedules", 2025)).filter(pl.col("week") == 10)
    last = sched.sort(["gameday", "gametime"]).row(-1, named=True)
    date = dt.date.fromisoformat(last["gameday"]).strftime("%y%b%d").upper()
    with httpx.Client(timeout=60) as c:
        markets: list[dict[str, Any]] = []
        cursor = None
        while True:
            params: dict[str, Any] = {"series_ticker": "KXNFLGAME", "limit": 1000}
            if cursor:
                params["cursor"] = cursor
            page = c.get(f"{KALSHI}/historical/markets", params=params).json()
            markets += [m for m in page.get("markets", []) if f"-{date}" in m["event_ticker"]]
            cursor = page.get("cursor")
            if not cursor:
                break
        teams = (last["away_team"], last["home_team"])
        mine = [m for m in markets if all(t in m["event_ticker"] for t in teams)]
        if not mine:
            raise SystemExit(f"no KXNFLGAME market found for {last['game_id']} on {date}")
        out = []
        for m in mine:
            o = dt.datetime.fromisoformat(m["open_time"].replace("Z", "+00:00"))
            e = dt.datetime.fromisoformat(m["close_time"].replace("Z", "+00:00"))
            url = f"{KALSHI}/historical/markets/{m['ticker']}/candlesticks"
            r = c.get(
                url,
                params={
                    "start_ts": int(o.timestamp()),
                    "end_ts": int(e.timestamp()),
                    "period_interval": 60,
                },
            )
            r.raise_for_status()
            out.append({"source": url, "market": m, "response": r.json()})
    body = {
        "source": f"{KALSHI}/historical/markets/<ticker>/candlesticks?period_interval=60",
        "pulled_at": _now(),
        "game_id": last["game_id"],
        "markets": out,
    }
    (HERE / "kalshi_candles_2025w10.json").write_text(json.dumps(body, indent=1), encoding="utf-8")
    print("wrote kalshi_candles_2025w10.json", [m["market"]["ticker"] for m in out])


def _pages(c: httpx.Client, path: str, key: str, **params: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    cursor = None
    while True:
        p = {**params, **({"cursor": cursor} if cursor else {})}
        r = c.get(f"{KALSHI}{path}", params=p)
        r.raise_for_status()
        out += r.json().get(key) or []
        cursor = r.json().get("cursor")
        if not cursor:
            return out


def kalshi_events() -> None:
    """GET /events for KXNFLGAME (docs: "All events are accessible through this endpoint, even
    if their associated markets are older than the historical cutoff"), plus live and
    historical GET markets?event_ticker= for one archived 2025 event and one live 2026 one."""
    with httpx.Client(timeout=60) as c:
        events = _pages(c, "/events", "events", series_ticker="KXNFLGAME", limit=200)
        body = {
            "source": f"{KALSHI}/events?series_ticker=KXNFLGAME&limit=200 (all pages)",
            "pulled_at": _now(),
            "response": {"events": events},
        }
        (HERE / "kalshi_events_kxnflgame.json").write_text(
            json.dumps(body, indent=1), encoding="utf-8"
        )
        sched = pl.read_parquet(_latest("schedules", 2025)).filter(pl.col("week") == 10)
        last = sched.sort(["gameday", "gametime"]).row(-1, named=True)
        date = dt.date.fromisoformat(last["gameday"]).strftime("%y%b%d").upper()
        old = next(e["event_ticker"] for e in events if f"-{date}" in e["event_ticker"]
                   and last["home_team"] in e["event_ticker"])  # fmt: skip
        today = dt.datetime.now(dt.UTC).date()
        live = next(
            e["event_ticker"]
            for e in sorted(events, key=lambda e: e["event_ticker"])
            if (d := _ticker_date(e["event_ticker"])) is not None and d >= today
        )
        out = {}
        for ev in (old, live):
            out[ev] = {
                "live": _pages(c, "/markets", "markets", event_ticker=ev, limit=1000),
                "historical": _pages(
                    c, "/historical/markets", "markets", event_ticker=ev, limit=1000
                ),
            }
        body = {
            "source": f"{KALSHI}/markets?event_ticker= and /historical/markets?event_ticker=",
            "pulled_at": _now(),
            "archived_event": old,
            "live_event": live,
            "response": out,
        }
        (HERE / "kalshi_event_markets.json").write_text(
            json.dumps(body, indent=1), encoding="utf-8"
        )
        print(
            "wrote kalshi_events_kxnflgame.json",
            len(events),
            "and kalshi_event_markets.json",
            old,
            live,
        )


def _ticker_date(ticker: str) -> dt.date | None:
    import re

    m = re.search(r"-(\d{2}[A-Z]{3}\d{2})", ticker)
    if not m:
        return None
    try:
        return dt.datetime.strptime(m.group(1).title(), "%y%b%d").date()
    except ValueError:
        return None


if __name__ == "__main__":
    steps = {
        "kalshi_events": kalshi_events,
        "schedules": schedules,
        "depth_weekly": depth_weekly,
        "depth_espn": depth_espn,
        "pbp_times": pbp_times,
        "ngs": ngs,
        "kalshi_candles": kalshi_candles,
    }
    for step in sys.argv[1:] or list(steps):
        steps[step]()
