"""Download the real responses the phase1 tests use. Run once, by hand:

    uv run python tests/phase1/fixtures/capture_fixtures.py

Uses plain httpx on purpose (not ge.ingest) so fixtures don't depend on the code under test.
Every file records its source URL and pull time, per CLAUDE.md rule 2.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import nflreadpy
import polars as pl
from dotenv import dotenv_values

HERE = Path(__file__).parent
REPO = HERE.parents[2]
UA = dotenv_values(REPO / ".env").get("NWS_USER_AGENT") or os.environ["NWS_USER_AGENT"]

KALSHI = "https://external-api.kalshi.com/trade-api/v2"  # docs.kalshi.com quick start
NWS = "https://api.weather.gov"  # weather.gov/documentation/services-web-api
# Wikidata:Data_access documents https://wikidata.org/w/api.php, which 301-redirects here.
WIKIDATA = "https://www.wikidata.org/w/api.php"


def now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


def save(name: str, source: str, response: Any, **extra: Any) -> None:
    body = {"source": source, "pulled_at": now(), **extra, "response": response}
    (HERE / name).write_text(json.dumps(body, indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", name)


def get(client: httpx.Client, url: str, **params: Any) -> httpx.Response:
    r = client.get(url, params=params or None)
    time.sleep(0.5)  # be polite; capture only
    return r


def kalshi(client: httpx.Client) -> None:
    # Series list, trimmed to Football/combos plus two known name-rule false positives.
    r = get(client, f"{KALSHI}/series")
    r.raise_for_status()
    series = r.json()["series"]
    keep = [
        s
        for s in series
        if "Football" in (s.get("tags") or [])
        or s["ticker"].startswith("KXMVE")
        or "NFL" in (s["ticker"] + (s.get("title") or "")).upper()
    ]
    save("kalshi_series_subset.json", f"{KALSHI}/series", {"series": keep}, note="trimmed")

    # One open KXNFLGAME market with both sides of the book populated, captured with its
    # market record in the same second so Kalshi's own yes_ask/no_ask are the expected values.
    r = get(client, f"{KALSHI}/markets", series_ticker="KXNFLGAME", status="open", limit=200)
    r.raise_for_status()
    for m in r.json()["markets"]:
        for _ in range(5):
            book = get(client, f"{KALSHI}/markets/{m['ticker']}/orderbook").json()
            market = get(client, f"{KALSHI}/markets/{m['ticker']}").json()["market"]
            book2 = get(client, f"{KALSHI}/markets/{m['ticker']}/orderbook").json()
            fp = book.get("orderbook_fp") or {}
            if book == book2 and fp.get("yes_dollars") and fp.get("no_dollars"):
                save(
                    "kalshi_orderbook.json",
                    f"{KALSHI}/markets/{m['ticker']}/orderbook",
                    book,
                    market_source=f"{KALSHI}/markets/{m['ticker']}",
                    market=market,
                )
                return
    raise SystemExit("no stable two-sided KXNFLGAME book found; rerun later")


def wikidata_and_nws(client: httpx.Client) -> None:
    sched = nflreadpy.load_schedules(True)
    names = sorted(sched.filter(pl.col("season") == 2026)["stadium"].unique().to_list())

    searches: dict[str, Any] = {}
    for name in [*names[:3], "Zzqx Nonexistent Stadium Name"]:
        r = get(
            client,
            WIKIDATA,
            action="wbsearchentities",
            search=name,
            language="en",
            type="item",
            limit=10,
            format="json",
        )
        r.raise_for_status()
        searches[name] = r.json()
    save("wikidata_search.json", WIKIDATA + "?action=wbsearchentities", searches)

    ids = sorted({hit["id"] for resp in searches.values() for hit in resp.get("search", [])})
    r = get(
        client,
        WIKIDATA,
        action="wbgetentities",
        ids="|".join(ids[:50]),
        props="labels|aliases|claims",
        languages="en",
        format="json",
    )
    r.raise_for_status()
    save("wikidata_entities.json", WIKIDATA + "?action=wbgetentities", r.json())

    # Confirm the coordinate property's ID and label rather than trusting memory.
    r = get(
        client,
        WIKIDATA,
        action="wbsearchentities",
        search="coordinate location",
        language="en",
        type="property",
        limit=5,
        format="json",
    )
    r.raise_for_status()
    save("wikidata_coordinate_property.json", WIKIDATA + "?type=property", r.json())

    # NWS: a real US point (first matched stadium) and a point outside NWS coverage.
    coord_prop = r.json()["search"][0]["id"]
    ents = json.loads((HERE / "wikidata_entities.json").read_text(encoding="utf-8"))["response"]
    point = None
    for ent in ents["entities"].values():
        for claim in ent.get("claims", {}).get(coord_prop, []):
            v = claim["mainsnak"].get("datavalue", {}).get("value")
            if v:
                point = (
                    round(Decimal(str(v["latitude"])), 4),
                    round(Decimal(str(v["longitude"])), 4),
                )
                break
        if point:
            break
    assert point, "no coordinates in captured entities"
    pts = get(client, f"{NWS}/points/{point[0]},{point[1]}")
    pts.raise_for_status()
    save("nws_points.json", f"{NWS}/points/{point[0]},{point[1]}", pts.json())
    grid_url = pts.json()["properties"]["forecastGridData"]
    grid = get(client, grid_url)
    grid.raise_for_status()
    save("nws_gridpoint.json", grid_url, grid.json())

    # 0,0 is in the Atlantic, outside every NWS office: record the real error response.
    bad = get(client, f"{NWS}/points/0,0")
    save("nws_points_outside.json", f"{NWS}/points/0,0", bad.json(), status_code=bad.status_code)


def fee_pdf(client: httpx.Client) -> None:
    import yaml

    url = yaml.safe_load((REPO / "config" / "fees.yaml").read_text(encoding="utf-8"))["source_url"]
    r = client.get(url, follow_redirects=True)
    r.raise_for_status()
    (HERE / "kalshi_fee_schedule.pdf").write_bytes(r.content)
    save(
        "kalshi_fee_schedule.meta.json",
        url,
        None,
        bytes=len(r.content),
        content_type=r.headers.get("content-type"),
    )


def wikidata_elevation_property(client: httpx.Client) -> None:
    """ENV-02: confirm the elevation property's ID and label rather than trusting memory."""
    r = get(
        client,
        WIKIDATA,
        action="wbsearchentities",
        search="elevation above sea level",
        language="en",
        type="property",
        limit=5,
        format="json",
    )
    r.raise_for_status()
    save("wikidata_elevation_property.json", WIKIDATA + "?type=property", r.json())
    # Items approved 2026-09-29 (DEN00, CHI98, PHI00), captured to test elevation parsing.
    ids = "Q1046135|Q1132413|Q1052370"
    r = get(
        client,
        WIKIDATA,
        action="wbgetentities",
        ids=ids,
        props="labels|claims",
        languages="en",
        format="json",
    )
    r.raise_for_status()
    save(
        "wikidata_elevation_entities.json", WIKIDATA + f"?action=wbgetentities&ids={ids}", r.json()
    )
    # Items the Denver stadium item links to, captured only because they carry real P2044
    # claims to test the elevation parser on (no venue item has one as of 2026-09-29).
    linked = "Q1261|Q16554"
    r = get(
        client,
        WIKIDATA,
        action="wbgetentities",
        ids=linked,
        props="labels|claims",
        languages="en",
        format="json",
    )
    r.raise_for_status()
    save(
        "wikidata_elevation_parser_entities.json",
        WIKIDATA + f"?action=wbgetentities&ids={linked}",
        r.json(),
    )


def nflverse_teams(client: httpx.Client) -> None:
    teams = nflreadpy.load_teams().select(["team_abbr", "team_name", "team_nick"])
    save("nflverse_teams.json", f"nflreadpy {nflreadpy.__version__} load_teams()", teams.to_dicts())


if __name__ == "__main__":
    import sys

    steps = {
        "kalshi": kalshi,
        "wikidata_nws": wikidata_and_nws,
        "fee_pdf": fee_pdf,
        "nflverse_teams": nflverse_teams,
        "wikidata_elevation_property": wikidata_elevation_property,
    }
    headers = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
    with httpx.Client(headers=headers, timeout=60) as c:
        for step in sys.argv[1:] or list(steps):
            steps[step](c)
