"""The `ge ingest` jobs: glue between the clients, the raw store and the printed reports."""

from __future__ import annotations

import datetime as dt
import json
from collections import defaultdict
from typing import Any
from zoneinfo import ZoneInfo

import polars as pl

from ge.config import IngestConfig, load_fees
from ge.ingest.fees_check import check_fee_schedule, fee_check, parse_effective_date
from ge.ingest.http import PublicClient
from ge.ingest.kalshi import (
    REVIEW_PATH,
    KalshiPublic,
    approved_series,
    nfl_candidates,
    pending_series,
    update_review_file,
)
from ge.ingest.nflverse import current_season
from ge.ingest.prices import book_asks, dollars_to_cc
from ge.ingest.raw import DATA_ROOT, read_latest, seasons_stored, write_raw
from ge.ingest.stadiums import (
    build_stadiums,
    load_overrides,
    load_stadiums,
    missing_for_2026,
    stadium_for_game,
    write_stadiums,
)
from ge.ingest.weather_nws import NwsClient, classify_game, parse_gridpoint
from ge.ingest.wikidata import WikidataClient

EASTERN = ZoneInfo("America/New_York")  # nflverse gametime is Eastern (schedules dictionary)
ATTRIBUTION = "Data: nflverse; charting: FTN Data via nflverse"


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _schedules(seasons: list[int] | None = None) -> pl.DataFrame:
    stored = seasons_stored(DATA_ROOT, "schedules")
    if not stored:
        raise SystemExit("no schedules in data/raw; run `uv run ge ingest nflverse` first")
    wanted = [s for s in stored if seasons is None or s in seasons]
    return pl.concat([read_latest(DATA_ROOT, "schedules", s) for s in wanted], how="diagonal")


# --- stadiums (DATA-13) --------------------------------------------------------------------


def run_stadiums(cfg: IngestConfig, user_agent: str) -> int:
    season = current_season()
    first = cfg.nflverse.first_season.value
    sched = _schedules(list(range(first, season + 1)))
    with PublicClient(cfg.http, user_agent) as http:
        rows = build_stadiums(
            sched, WikidataClient(http, cfg.wikidata), cfg.wikidata, season, load_overrides()
        )
    write_stadiums(rows, season)
    print(
        f"{'stadium_id':<10} {'status':<9} {'lat':>10} {'lon':>11} {'timezone':<28} "
        f"{season!s:<5} name / source"
    )
    for r in rows:
        lat = f"{r['lat']:.5f}" if r["lat"] is not None else "-"
        lon = f"{r['lon']:.5f}" if r["lon"] is not None else "-"
        print(
            f"{r['stadium_id']:<10} {r['match_status']:<9} {lat:>10} {lon:>11} "
            f"{r['timezone'] or '-':<28} {'yes' if r['has_current_season_game'] else '':<5} "
            f"{r['name']}  {r['source_url'] or ''}"
        )
    blanks = [r for r in rows if r["match_status"] not in ("matched", "override")]
    print(f"\n{len(rows)} venues, {len(rows) - len(blanks)} located, {len(blanks)} left blank:")
    for r in blanks:
        print(f"  {r['stadium_id']} {r['name']!r}: {r['match_status']} - {r['match_reason']}")
    problems = missing_for_2026(rows)
    if problems:
        print(f"\nCHECK FAILED: {len(problems)} {season} stadium(s) lack coordinates or source_url")
        return 1
    print(f"\ncheck passed: every {season} stadium has coordinates and a source_url")
    return 0


# --- weather (DATA-06) ---------------------------------------------------------------------


def run_weather(cfg: IngestConfig, user_agent: str, days: int) -> int:
    season = current_season()
    sched = _schedules([season])
    stadiums = load_stadiums()
    today = _now().astimezone(EASTERN).date()
    last = today + dt.timedelta(days=days)
    games = sched.filter(
        pl.col("gameday").str.to_date().is_between(today, last) & pl.col("result").is_null()
    ).sort(["gameday", "gametime"])
    pulled_at = _now()
    status_rows: list[dict[str, Any]] = []
    hourly: list[dict[str, Any]] = []
    grids: dict[str, tuple[str, str | None, list[dict[str, Any]]]] = {}
    with PublicClient(cfg.http, user_agent) as http:
        nws = NwsClient(http, cfg.nws)
        for g in games.iter_rows(named=True):
            st = stadium_for_game(stadiums, g["stadium_id"], g["stadium"]) or {}
            has_xy = st.get("lat") is not None and st.get("lon") is not None
            decision = classify_game(roof=g["roof"], has_coordinates=has_xy)
            detail = ""
            if decision in ("pull", "pull_roof_unknown"):
                key = f"{st['lat']},{st['lon']}"
                if key not in grids:
                    status, url = nws.grid_url(st["lat"], st["lon"])
                    grids[key] = (status, url, parse_gridpoint(nws.gridpoint(url)) if url else [])
                status, url, rows = grids[key]
                if status == "no_weather_source":
                    decision_out = "no_weather_source"
                    detail = (
                        f"NWS has no data for this point ({st.get('timezone')}): "
                        "weather unknown, apply no adjustment"
                    )
                else:
                    decision_out = decision
                    hourly.extend({**r, "game_id": g["game_id"], "grid_url": url} for r in rows)
                    detail = f"{len(rows)} field-hours"
            else:
                decision_out = decision
                detail = {
                    "skip_roof": f"roof {g['roof']}: weather ignored (MTC-05)",
                    "no_coordinates": "stadium has no coordinates: weather unknown",
                }[decision]
            status_rows.append(
                {
                    "game_id": g["game_id"],
                    "gameday": g["gameday"],
                    "stadium_id": g["stadium_id"],
                    "roof": g["roof"],
                    "weather_status": decision_out,
                    "detail": detail,
                }
            )
    if hourly:
        write_raw(
            pl.DataFrame(hourly),
            "nws_hourly",
            season,
            source="NWS api.weather.gov (DATA-06) forecastGridData",
            pulled_at=pulled_at,
        )
    if status_rows:
        write_raw(
            pl.DataFrame(status_rows),
            "nws_game_status",
            season,
            source="ge ingest weather",
            pulled_at=pulled_at,
        )
    print(f"games {today} to {last} (ET): {len(status_rows)}")
    for r in status_rows:
        wind = ""
        rows_g = [h for h in hourly if h["game_id"] == r["game_id"] and h["field"] == "windSpeed"]
        if rows_g:
            vals = [h["value"] for h in rows_g if h["value"] is not None]
            wind = f"wind {min(vals):.1f}-{max(vals):.1f} {rows_g[0]['uom']}" if vals else ""
        print(
            f"  {r['gameday']} {r['game_id']:<16} {r['stadium_id']:<6} {r['roof'] or 'roof?':<9} "
            f"{r['weather_status']:<18} {wind or r['detail']}"
        )
    return 0


# --- Kalshi (DATA-08) ----------------------------------------------------------------------


def _week_window(season: int, week: int) -> tuple[dt.datetime, dt.datetime | None]:
    """Week W runs from its first game date (00:00 ET) to week W+1's first game date."""
    sched = _schedules([season])

    def first_day(w: int) -> dt.date | None:
        days = sched.filter(pl.col("week") == w)["gameday"].str.to_date()
        return days.min() if days.len() else None  # type: ignore[return-value]

    start = first_day(week)
    if start is None:
        raise SystemExit(f"no {season} week {week} games in schedules")
    nxt = first_day(week + 1)

    def to_utc(d: dt.date) -> dt.datetime:
        return dt.datetime.combine(d, dt.time(), EASTERN).astimezone(dt.UTC)

    return to_utc(start), (to_utc(nxt) if nxt else None)


def _occurs(m: dict[str, Any]) -> dt.datetime | None:
    raw = m.get("occurrence_datetime") or m.get("expected_expiration_time")
    return dt.datetime.fromisoformat(raw.replace("Z", "+00:00")) if raw else None


def run_kalshi(cfg: IngestConfig, season: int, week: int, history: bool) -> int:
    pulled_at = _now()
    with PublicClient(cfg.http) as http:
        k = KalshiPublic(http, cfg.kalshi)
        all_series = k.series_list()
        cands = nfl_candidates(all_series)
        new = update_review_file(REVIEW_PATH, cands)
        write_raw(
            pl.DataFrame(
                [
                    {
                        **{
                            kk: json.dumps(v) if isinstance(v, list | dict) else v
                            for kk, v in s.items()
                        }
                    }
                    for s in all_series
                    if s["ticker"] in {c.ticker for c in cands}
                ]
            ),
            "kalshi_series_candidates",
            season,
            source="Kalshi GET /series (DATA-08)",
            pulled_at=pulled_at,
        )
        approved = sorted(approved_series(REVIEW_PATH))
        pending = pending_series(REVIEW_PATH)
        print(
            f"NFL series candidates: {len(cands)} ({new} new); approved: {len(approved)}; "
            f"pending review: {len(pending)} -> {REVIEW_PATH}"
        )
        if not approved:
            print("No approved series yet. Mark series `include` in the review file, then rerun.")
            return 2
        start, end = _week_window(season, week)
        print(
            f"{season} week {week}: markets occurring {start:%Y-%m-%d %H:%M}Z to "
            f"{f'{end:%Y-%m-%d %H:%M}Z' if end else 'open-ended'}"
        )
        markets = []
        for series in approved:
            for m in k.markets(series_ticker=series, min_close_ts=int(start.timestamp())):
                t = _occurs(m)
                if t and t >= start and (end is None or t < end):
                    markets.append({**m, "series_ticker": series})
        book_rows: list[dict[str, Any]] = []
        market_rows: list[dict[str, Any]] = []
        trade_rows: list[dict[str, Any]] = []
        candle_rows: list[dict[str, Any]] = []
        for m in markets:
            book = k.orderbook(m["ticker"])
            yes_ask, no_ask = book_asks(book)
            for side in ("yes", "no"):
                for price, qty in book.get(f"{side}_dollars") or []:
                    book_rows.append(
                        {
                            "ticker": m["ticker"],
                            "side": side,
                            "bid_cc": dollars_to_cc(price),
                            "qty": qty,
                        }
                    )
            market_rows.append(
                {
                    "ticker": m["ticker"],
                    "event_ticker": m.get("event_ticker"),
                    "series_ticker": m["series_ticker"],
                    "status": m.get("status"),
                    "yes_sub_title": m.get("yes_sub_title"),
                    "occurs_at": _occurs(m),
                    "close_time": m.get("close_time"),
                    "yes_ask_cc": yes_ask,
                    "no_ask_cc": no_ask,
                    "volume_fp": m.get("volume_fp"),
                    "rules_primary": m.get("rules_primary"),
                    "rules_secondary": m.get("rules_secondary"),
                    "raw_json": json.dumps(m),
                }
            )
            if history:
                trade_rows.extend({**t, "ticker": m["ticker"]} for t in k.trades(m["ticker"]))
                opened = dt.datetime.fromisoformat(m["open_time"].replace("Z", "+00:00"))
                for c in k.candlesticks(
                    m["series_ticker"],
                    m["ticker"],
                    int(opened.timestamp()),
                    int(pulled_at.timestamp()),
                ):
                    candle_rows.append(
                        {
                            "ticker": m["ticker"],
                            "raw_json": json.dumps(c),
                            "end_period_ts": c.get("end_period_ts"),
                        }
                    )
    for name, rows in (
        ("kalshi_markets", market_rows),
        ("kalshi_orderbook", book_rows),
        ("kalshi_trades", trade_rows),
        ("kalshi_candles", candle_rows),
    ):
        if rows:
            write_raw(
                pl.DataFrame(rows, infer_schema_length=None),
                name,
                season,
                source=f"Kalshi public API (DATA-08) week {week}",
                pulled_at=pulled_at,
            )
    print(f"{len(market_rows)} markets:")
    for r in sorted(market_rows, key=lambda r: (r["occurs_at"], r["ticker"])):
        asks = f"YES {r['yes_ask_cc']} / NO {r['no_ask_cc']} cc"
        print(f"  {r['ticker']:<44} {asks:<24} {(r['rules_primary'] or '')[:110]}")
    missing_rules = [r["ticker"] for r in market_rows if not r["rules_primary"]]
    if missing_rules:
        print(f"WARNING: {len(missing_rules)} markets have no rules text: {missing_rules[:10]}")
        return 1
    return 0


# --- fee schedule (DATA-09) ----------------------------------------------------------------


def run_fees_check(cfg: IngestConfig, pdf_path: str | None) -> int:
    """EDG-02 / DATA-09: API fee check for every included series, plus the PDF date check
    when a hand-saved PDF is given (the PDF URL serves a bot check to scripts)."""
    fees = load_fees()
    ok = True
    if pdf_path:
        with open(pdf_path, "rb") as fh:
            pdf_result = check_fee_schedule(fees, parse_effective_date(fh.read()))
        print(f"PDF {pdf_path}: {pdf_result.message}")
        ok &= pdf_result.ok
    else:
        print("PDF check not run (pass --pdf <saved fee schedule PDF> to run it)")

    included = approved_series(REVIEW_PATH)
    if not included:
        print(f"API check: no series are marked include in {REVIEW_PATH}; nothing to compare")
        return 0 if ok else 1
    with PublicClient(cfg.http) as http:
        listed = {s["ticker"]: s for s in KalshiPublic(http, cfg.kalshi).series_list()}
    gone = sorted(included - set(listed))
    result = fee_check(fees, [listed[t] for t in sorted(included) if t in listed])
    new = result.new + [f"{t}: included series no longer listed by Kalshi" for t in gone]
    print(
        f"API check: {len(included)} included series; {len(result.acknowledged)} acknowledged "
        f"disagreement(s), {len(new)} new or changed, {len(result.stale)} stale acknowledgement(s)"
    )
    for a in new:
        print(f"  ALERT {a}")
    for s in result.stale:
        print(f"  ALERT {s}")
    for a in result.acknowledged:
        print(f"  acknowledged: {a}")
    flagged = [e for e in result.effective if e.alerts]
    if flagged:
        print("  multipliers used (costlier of fees.yaml and API, EDG-02):")
        for e in flagged:
            state = "" if e.known else "  UNTRUSTED"
            print(f"    {e.ticker:<28} row {e.row:<18} taker {e.taker} maker {e.maker}{state}")
    return 0 if ok and not new and not result.stale else 1


# --- report --------------------------------------------------------------------------------


def run_report(cfg: IngestConfig) -> int:
    first = cfg.nflverse.first_season.value
    season = current_season()
    sched = _schedules(list(range(first, season + 1)))
    print(ATTRIBUTION)
    print("\nWeather history: outdoor games (roof outdoors or open) with temp and wind filled")
    print(
        "(nflverse dictionary: temp and wind are 'for outdoors and open only'; played games only)"
    )
    print(f"  {'season':<7}{'outdoor':>8}{'temp':>9}{'wind':>9}{'both':>9}")
    out = sched.filter(pl.col("roof").is_in(["outdoors", "open"]) & pl.col("result").is_not_null())

    def pct(k: int, n: int) -> str:
        return f"{k / n:.1%}" if n else "-"

    for s in sorted(out["season"].unique().to_list()):
        g = out.filter(pl.col("season") == s)
        n = g.height
        temp = int(g["temp"].is_not_null().sum())
        wind = int(g["wind"].is_not_null().sum())
        both = g.filter(pl.col("temp").is_not_null() & pl.col("wind").is_not_null()).height
        print(f"  {s:<7}{n:>8}{pct(temp, n):>9}{pct(wind, n):>9}{pct(both, n):>9}")

    print(f"\nInjuries: latest {season} report in nflverse injuries data")
    if season in seasons_stored(DATA_ROOT, "injuries"):
        inj = read_latest(DATA_ROOT, "injuries", season)
        weeks = sorted(inj["week"].unique().to_list())
        latest = max(weeks) if weeks else None
        pulled = str(inj["pulled_at"].max())
        print(f"  weeks present: {weeks}; latest week: {latest}; pulled {pulled}")
        print("  The file has no report-date column, so the latest week is the best available")
        if latest is not None:
            days = sched.filter((pl.col("season") == season) & (pl.col("week") == latest))
            first_day, last_day = str(days["gameday"].min()), str(days["gameday"].max())
            print(f"  week {latest} games were played {first_day} to {last_day} (from schedules)")
    else:
        print(f"  no {season} injuries file stored")

    print("\nFTN -> pbp join rate by season")
    for s in [x for x in seasons_stored(DATA_ROOT, "ftn_charting") if x >= first]:
        if s not in seasons_stored(DATA_ROOT, "pbp"):
            continue
        ftn = read_latest(DATA_ROOT, "ftn_charting", s).select(
            ["nflverse_game_id", "nflverse_play_id"]
        )
        pbp = read_latest(DATA_ROOT, "pbp", s).select(["game_id", "play_id"])
        pbp = pbp.with_columns(pl.col("play_id").cast(ftn["nflverse_play_id"].dtype))
        j = ftn.join(
            pbp,
            left_on=["nflverse_game_id", "nflverse_play_id"],
            right_on=["game_id", "play_id"],
            how="inner",
        ).height
        print(f"  {s}: {j}/{ftn.height} = {j / ftn.height:.2%}" if ftn.height else f"  {s}: empty")

    counts: dict[str, int] = defaultdict(int)
    for ds in ("nws_game_status",):
        if season in seasons_stored(DATA_ROOT, ds):
            for st in read_latest(DATA_ROOT, ds, season)["weather_status"].to_list():
                counts[st] += 1
    if counts:
        print(f"\nLatest weather pull by status: {dict(counts)}")
    return 0
