"""DATA-08 Kalshi public market data. GET-only, no auth, no order/portfolio/account endpoints
(CLAUDE.md rule 8). Endpoint paths are from docs.kalshi.com (see config/ingest.yaml sources).

NFL series discovery proposes candidates with reasons into config/kalshi_nfl_series.yaml;
only series you mark `include` are ingested (approved 2026-09-29)."""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ge.config import REPO_ROOT, KalshiSettings
from ge.ingest.http import PublicClient

REVIEW_PATH = REPO_ROOT / "config" / "kalshi_nfl_series.yaml"
DECISIONS = ("pending", "include", "exclude")

_NFL_IN_TICKER = re.compile(r"NFL(?!X)")  # KXNFL... but not ...NFLX (Netflix)
_NFL_IN_TITLE = re.compile(r"\bNFL\b")


@dataclass(frozen=True)
class Candidate:
    ticker: str
    title: str
    category: str | None
    tags: tuple[str, ...]
    fee_type: str | None
    fee_multiplier: Any
    reasons: tuple[str, ...] = field(default_factory=tuple)


def nfl_candidates(series: list[dict[str, Any]]) -> list[Candidate]:
    """DATA-08: every series that might be NFL, with the rule(s) that flagged it."""
    out = []
    for s in series:
        ticker = s["ticker"]
        title = s.get("title") or ""
        tags = tuple(s.get("tags") or ())
        reasons = []
        if "Football" in tags:
            reasons.append("tag:Football")
        if ticker.upper().startswith("KXMVENFL"):
            reasons.append("combo:KXMVENFL")
        if _NFL_IN_TICKER.search(ticker.upper()):
            reasons.append("ticker:NFL")
        if _NFL_IN_TITLE.search(title.upper()):
            reasons.append("title:NFL")
        if "PRO FOOTBALL" in title.upper():
            reasons.append("title:Pro Football")
        if reasons:
            out.append(
                Candidate(
                    ticker,
                    title,
                    s.get("category"),
                    tags,
                    s.get("fee_type"),
                    s.get("fee_multiplier"),
                    tuple(reasons),
                )
            )
    return sorted(out, key=lambda c: c.ticker)


def _read_review(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"series": {}}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rows = data.get("series") or {}
    for ticker, row in rows.items():
        if row.get("decision") not in DECISIONS:
            raise ValueError(f"{path}: {ticker} decision must be one of {DECISIONS}")
    return {"series": rows}


def update_review_file(path: Path, candidates: list[Candidate]) -> int:
    """Add new candidates as `pending`, refresh metadata, keep every existing decision.
    Returns how many candidates were new."""
    data = _read_review(path)
    rows = data["series"]
    today = dt.datetime.now(dt.UTC).date().isoformat()
    new = 0
    for c in candidates:
        row = rows.get(c.ticker)
        if row is None:
            new += 1
            row = {"decision": "pending", "first_seen": today}
        row.update(
            title=c.title,
            category=c.category,
            tags=list(c.tags),
            reasons=list(c.reasons),
            fee_type=c.fee_type,
            fee_multiplier=c.fee_multiplier,
        )
        rows[c.ticker] = row
    body = {
        "generated_by": "ge ingest kalshi",
        "how_to_review": "Set each decision to include or exclude. Only include is ingested; "
        "new candidates arrive as pending and are reported, never auto-included.",
        "series": dict(sorted(rows.items())),
    }
    path.write_text(
        yaml.safe_dump(body, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n"
    )
    return new


_PDF_TICKER = re.compile(r"\bKX[A-Z0-9]+\b")
_PDF_NFL_TEXT = re.compile(
    r"Pro\s+Football|Professional\s+Football|Football\s+Conference|Super\s+Bowl"
)
# Other pro leagues added 2026-10-02: Kalshi sometimes tags their series Football.
_OTHER_LEAGUE_TICKER = ("NCAA", "CFB", "CFL", "UFL", "XFL", "NBA", "WNBA", "NHL", "MLB", "MLS")
_OTHER_LEAGUE_TITLE = re.compile(r"\b(COLLEGE|NCAA\w*|CFB|CFL|UFL|XFL|NBA|WNBA|NHL|MLB|MLS)\b")
_SPORTS_CATEGORIES = {"Sports", "Exotics"}  # Kalshi puts NFL combos (KXMVENFL*) in Exotics
INCLUDE_RULES = ("nfl_prefix", "fee_schedule_nfl", "nfl_team_in_title")
EXCLUDE_RULES = ("other_league", "non_sports")


def fee_schedule_nfl_tickers(pdf: bytes) -> set[str]:
    """DATA-09: series tickers the fee schedule PDF describes as pro football or Super Bowl."""
    from io import BytesIO

    from pypdf import PdfReader

    text = " ".join(p.extract_text() or "" for p in PdfReader(BytesIO(pdf)).pages)
    marks = list(_PDF_TICKER.finditer(text))
    out = set()
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        row = text[m.end() : end]
        if _PDF_NFL_TEXT.search(row) and "College" not in row:
            out.add(m.group())
    return out


def propose(
    candidates: list[Candidate], team_names: list[str], fee_nfl: set[str]
) -> dict[str, tuple[str, list[str]]]:
    """DATA-08: rule-based include/exclude proposal per candidate. Both kinds of rule firing,
    or neither, leaves it undecided for the user."""
    teams = [t.casefold() for t in team_names if t]
    out: dict[str, tuple[str, list[str]]] = {}
    for c in candidates:
        t, title = c.ticker.upper(), c.title or ""
        rules = []
        if t.startswith(("KXNFL", "KXMVENFL")):
            rules.append("nfl_prefix")
        if t in fee_nfl:
            rules.append("fee_schedule_nfl")
        if any(name in title.casefold() for name in teams):
            rules.append("nfl_team_in_title")
        if any(x in t for x in _OTHER_LEAGUE_TICKER) or _OTHER_LEAGUE_TITLE.search(title.upper()):
            rules.append("other_league")
        if c.category not in _SPORTS_CATEGORIES:
            rules.append("non_sports")
        inc = any(r in INCLUDE_RULES for r in rules)
        exc = any(r in EXCLUDE_RULES for r in rules)
        if inc and not exc:
            out[c.ticker] = ("include", rules)
        elif exc and not inc:
            out[c.ticker] = ("exclude", rules)
        else:
            out[c.ticker] = ("undecided", rules or ["no_rule_matched"])
    return out


def write_proposals(path: Path, proposals: dict[str, tuple[str, list[str]]]) -> None:
    """Record proposals next to each decision. Decisions are never changed here."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for ticker, (proposal, rules) in proposals.items():
        row = data["series"].get(ticker)
        if row is not None:
            row["proposed"] = proposal
            row["proposed_rules"] = rules
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n"
    )


FEE_RULE_SKIPPED = "fee_schedule_nfl not run (no saved PDF)"


def refresh_review(
    path: Path, all_series: list[dict[str, Any]], team_names: list[str]
) -> tuple[list[Candidate], int]:
    """DATA-08: add new NFL candidates as pending and propose include/exclude for every
    pending row that has no proposal yet (user request 2026-10-04). Live runs have no
    fee-schedule PDF (it sits behind a bot check), so that rule is skipped and the skip is
    recorded in proposed_rules (user decision 2026-10-04). Decisions are never changed."""
    cands = nfl_candidates(all_series)
    new = update_review_file(path, cands)
    rows = _read_review(path)["series"]
    todo = [
        c
        for c in cands
        if rows[c.ticker]["decision"] == "pending" and "proposed" not in rows[c.ticker]
    ]
    if todo:
        props = {
            t: (p, [*rules, FEE_RULE_SKIPPED])
            for t, (p, rules) in propose(todo, team_names, set()).items()
        }
        write_proposals(path, props)
    return cands, new


def apply_decisions(
    path: Path,
    include: dict[str, str],
    exclude: dict[str, str],
    *,
    decided_by: str,
    decided_on: str,
) -> None:
    """Record the user's decisions ({ticker: basis}) with who decided and when."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    rows = data["series"]
    both = sorted(set(include) & set(exclude))
    unknown = sorted((set(include) | set(exclude)) - set(rows))
    if both or unknown:
        raise ValueError(f"listed as both include and exclude: {both}; not in file: {unknown}")
    for decision, picks in (("include", include), ("exclude", exclude)):
        for ticker, basis in picks.items():
            rows[ticker].update(
                decision=decision,
                decided_by=decided_by,
                decided_on=decided_on,
                decision_basis=basis,
            )
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n"
    )


def approved_series(path: Path = REVIEW_PATH) -> set[str]:
    return {t for t, row in _read_review(path)["series"].items() if row["decision"] == "include"}


def pending_series(path: Path = REVIEW_PATH) -> set[str]:
    return {t for t, row in _read_review(path)["series"].items() if row["decision"] == "pending"}


_EVENT_DATE = re.compile(r"-(\d{2}[A-Z]{3}\d{2})")


def event_ticker_date(event_ticker: str) -> dt.date | None:
    """DATA-08: the game date in an event ticker (KXNFLGAME-25NOV09PITLAC -> 2025-11-09), or
    None when the ticker carries no date (season-long markets)."""
    m = _EVENT_DATE.search(event_ticker)
    if not m:
        return None
    try:
        return dt.datetime.strptime(m.group(1).title(), "%y%b%d").date()
    except ValueError:
        return None


def events_on_dates(events: list[dict[str, Any]], dates: set[dt.date]) -> list[dict[str, Any]]:
    """DATA-08: events whose ticker date is one of `dates`, sorted by ticker."""
    return sorted(
        (e for e in events if event_ticker_date(e["event_ticker"]) in dates),
        key=lambda e: e["event_ticker"],
    )


def markets_for_event(k: KalshiPublic, event_ticker: str) -> list[tuple[dict[str, Any], bool]]:
    """DATA-08: an event's markets from GET /markets and GET /historical/markets (both take
    one event_ticker, per docs.kalshi.com). Returns (market, historical); live wins a tie."""
    live = list(k.markets(event_ticker=event_ticker))
    seen = {m["ticker"] for m in live}
    hist = [m for m in k.historical_markets(event_ticker=event_ticker) if m["ticker"] not in seen]
    return [(m, False) for m in live] + [(m, True) for m in hist]


class KalshiPublic:
    """DATA-08 read-only client for the documented public market-data endpoints."""

    def __init__(self, client: PublicClient, cfg: KalshiSettings) -> None:
        self._c = client
        self._base = cfg.base_url.value.rstrip("/")
        self._cfg = cfg

    def _get(self, path: str, **params: Any) -> Any:
        clean = {k: v for k, v in params.items() if v is not None}
        return self._c.get_json(self._base + path, clean or None)

    def _paged(self, path: str, key: str, limit: int, **params: Any) -> Iterator[dict[str, Any]]:
        cursor: str | None = None
        while True:
            page = self._get(path, limit=limit, cursor=cursor, **params)
            yield from page.get(key) or []
            cursor = page.get("cursor") or None
            if not cursor:
                return

    def series_list(self, **filters: Any) -> list[dict[str, Any]]:
        return list(self._get("/series", **filters).get("series") or [])

    def events(self, **filters: Any) -> Iterator[dict[str, Any]]:
        return self._paged("/events", "events", self._cfg.events_page_limit.value, **filters)

    def markets(self, **filters: Any) -> Iterator[dict[str, Any]]:
        return self._paged("/markets", "markets", self._cfg.markets_page_limit.value, **filters)

    def orderbook(self, ticker: str) -> dict[str, Any]:
        return dict(self._get(f"/markets/{ticker}/orderbook").get("orderbook_fp") or {})

    def trades(
        self, ticker: str, min_ts: int | None = None, max_ts: int | None = None
    ) -> Iterator[dict[str, Any]]:
        return self._paged(
            "/markets/trades",
            "trades",
            self._cfg.trades_page_limit.value,
            ticker=ticker,
            min_ts=min_ts,
            max_ts=max_ts,
        )

    def candlesticks(
        self, series_ticker: str, ticker: str, start_ts: int, end_ts: int
    ) -> list[dict[str, Any]]:
        body = self._get(
            f"/series/{series_ticker}/markets/{ticker}/candlesticks",
            start_ts=start_ts,
            end_ts=end_ts,
            period_interval=self._cfg.candle_period_minutes.value,
        )
        return list(body.get("candlesticks") or [])

    def historical_cutoff(self) -> dict[str, Any]:
        return dict(self._get("/historical/cutoff"))

    def historical_markets(self, **filters: Any) -> Iterator[dict[str, Any]]:
        return self._paged(
            "/historical/markets", "markets", self._cfg.markets_page_limit.value, **filters
        )

    def historical_trades(
        self, ticker: str, min_ts: int | None = None, max_ts: int | None = None
    ) -> Iterator[dict[str, Any]]:
        return self._paged(
            "/historical/trades",
            "trades",
            self._cfg.trades_page_limit.value,
            ticker=ticker,
            min_ts=min_ts,
            max_ts=max_ts,
        )

    def historical_candlesticks(
        self, ticker: str, start_ts: int, end_ts: int
    ) -> list[dict[str, Any]]:
        body = self._get(
            f"/historical/markets/{ticker}/candlesticks",
            start_ts=start_ts,
            end_ts=end_ts,
            period_interval=self._cfg.candle_period_minutes.value,
        )
        return list(body.get("candlesticks") or [])
