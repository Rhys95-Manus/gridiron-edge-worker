"""SHD-03 tick, SHD-05 close and SHD-13 settle jobs.

SHD-03: "A tick runs every 5 minutes. The tick re-pulls schedules into the shadow store when the
newest stored copy is more than 6 h old." Kickoffs come from the newest stored schedules: the
collector's copy in data/raw (read only) or the tick's own copy in data/shadow, whichever was
pulled later (SHD-01). The tick writes SHD-12 status rows, takes the snapshots that are due,
and records every attempt so a window that closes without a snapshot gets its miss reason.
Close (SHD-05) and settle (SHD-13) are retrospective and run after the tick's snapshots.
Public GET endpoints only (CLAUDE.md rule 8)."""

from __future__ import annotations

import datetime as dt
import json
import logging
import subprocess
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import polars as pl

from ge.config import REPO_ROOT, load_params
from ge.ingest.http import RetryableStatus
from ge.ingest.kalshi import markets_for_event
from ge.pricer_v0.scope import load_team_codes
from ge.pricer_v0.teams import ScheduleGame, load_team_map
from ge.shadow.close import closing_price
from ge.shadow.reader import read_table
from ge.shadow.schedule import (
    PRICING_MODE_CAPTURE,
    Attempt,
    GameKick,
    ShadowWindows,
    SnapshotType,
    StatusRec,
    judge,
    plan_tick,
    status_row,
)
from ge.shadow.settle import settle_value
from ge.shadow.snapshot import Mapper, MapResult, take_snapshot
from ge.shadow.store import MANIFEST, ShadowStore, StoreError
from ge.store.known_at import kickoff_utc

log = logging.getLogger(__name__)
# Season-level tables (schedules) are stored under week=00.
SEASON_WEEK = 0
_API_ERRORS = (httpx.HTTPError, RetryableStatus)
_PRICED_TYPES = (str(SnapshotType.T24H), str(SnapshotType.T90M))
_STORE_COLS = ("shadow_version", "written_at", "pricing_mode", "pull_ts")


@dataclass
class TickDeps:
    """Everything a job touches, injectable for tests."""

    store: ShadowStore
    kalshi: Any  # KalshiPublic: markets, orderbook, trades, historical_markets
    clock: Callable[[], dt.datetime]
    season: int
    raw_schedules: Callable[[int], tuple[pl.DataFrame, dt.datetime]]
    pull_schedules: Callable[[int], pl.DataFrame]
    mapper_factory: Callable[[int, dt.datetime], Mapper]
    code_commit: str | None


@dataclass
class TickReport:
    schedules_source: str = ""
    due: int = 0
    snapshots_ok: int = 0
    no_markets: int = 0
    api_errors: int = 0
    errors: list[str] = field(default_factory=list)
    status_rows: int = 0
    rows_written: dict[str, int] = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"schedules {self.schedules_source}; due {self.due}: ok {self.snapshots_ok}, "
            f"no_markets {self.no_markets}, api_error {self.api_errors}, "
            f"errors {len(self.errors)}; status rows {self.status_rows}; rows {self.rows_written}"
        )


def _vdir(deps: TickDeps) -> Path:
    return deps.store.version_dir


def _append(
    deps: TickDeps, table: str, rows: list[dict[str, Any]], report: TickReport | None
) -> None:
    """Write rows grouped by their (season, week) partition."""
    groups: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        groups[(int(r["season"]), int(r["week"]))].append(r)
    for (season, week), grp in sorted(groups.items()):
        deps.store.append(table, grp, season=season, week=week)
        if report is not None:
            report.rows_written[table] = report.rows_written.get(table, 0) + len(grp)


def newest_schedules(
    deps: TickDeps, now: dt.datetime, *, allow_pull: bool, report: TickReport | None = None
) -> pl.DataFrame:
    """SHD-01 / SHD-03: the newest stored schedules for the season; when the newest copy is
    more than the max age old and allow_pull, re-pull into the shadow store first."""
    cfg = ShadowWindows.from_params(load_params())
    best: tuple[dt.datetime, pl.DataFrame, str] | None = None
    try:
        raw, raw_at = deps.raw_schedules(deps.season)
        best = (raw_at, raw, f"data/raw pulled {raw_at.isoformat()}")
    except FileNotFoundError:
        pass
    stored = read_table(_vdir(deps), "schedules")
    if not stored.is_empty():
        stored = stored.filter(pl.col("season") == deps.season)
    if not stored.is_empty():
        at = stored["pull_ts"].max()
        assert isinstance(at, dt.datetime)
        if best is None or at > best[0]:
            df = stored.filter(pl.col("pull_ts") == at).drop(_STORE_COLS, strict=False)
            best = (at, df, f"data/shadow pulled {at.isoformat()}")
    if allow_pull and (best is None or now - best[0] > cfg.schedule_max_age):
        df = deps.pull_schedules(deps.season)
        pull_ts = deps.clock()
        deps.store.append(
            "schedules",
            df.with_columns(
                pl.lit(pull_ts).cast(pl.Datetime("us", "UTC")).alias("pull_ts"),
                pl.lit(PRICING_MODE_CAPTURE).alias("pricing_mode"),
            ),
            season=deps.season,
            week=SEASON_WEEK,
        )
        best = (pull_ts, df, f"re-pulled into data/shadow at {pull_ts.isoformat()}")
    if best is None:
        raise FileNotFoundError(f"no {deps.season} schedules stored")
    if report is not None:
        report.schedules_source = best[2]
    return best[1]


def _games(sched: pl.DataFrame) -> tuple[list[GameKick], list[ScheduleGame]]:
    kicks, games = [], []
    for r in sched.iter_rows(named=True):
        if not r.get("gameday") or not r.get("gametime"):
            continue  # no kickoff time yet (e.g. undecided playoff slots)
        kicks.append(
            GameKick(
                str(r["game_id"]),
                int(r["season"]),
                int(r["week"]),
                kickoff_utc(str(r["gameday"]), str(r["gametime"])),
            )
        )
        games.append(ScheduleGame.from_row(r))
    return kicks, games


def _latest_status(vdir: Path) -> dict[tuple[str, str], StatusRec]:
    st = read_table(vdir, "snapshot_status")
    out: dict[tuple[str, str], StatusRec] = {}
    for r in st.sort("written_at").iter_rows(named=True) if not st.is_empty() else []:
        out[(r["game_id"], r["snapshot_type"])] = StatusRec(
            r["status"], r["taken_ts"], r["target_ts"], r["written_at"]
        )
    return out


def _attempts(vdir: Path) -> dict[tuple[str, str], list[Attempt]]:
    at = read_table(vdir, "attempts")
    out: dict[tuple[str, str], list[Attempt]] = defaultdict(list)
    for r in at.iter_rows(named=True) if not at.is_empty() else []:
        out[(r["game_id"], r["snapshot_type"])].append(
            Attempt(r["attempt_ts"], r["outcome"], r["detail"] or "")
        )
    return dict(out)


def capture_start(vdir: Path, now: dt.datetime) -> dt.datetime:
    """The shadow version's capture start: its first manifest line's written_at (or now,
    before anything is written). Windows that closed earlier are not planned."""
    m = vdir / MANIFEST
    if m.exists():
        first = m.read_text(encoding="utf-8").split("\n", 1)[0]
        if first:
            return dt.datetime.fromisoformat(json.loads(first)["written_at"])
    return now


def run_tick(deps: TickDeps, only_games: set[str] | None = None) -> TickReport:
    """SHD-03: one tick. Raises on a configuration error (PRV-02 team code missing).
    only_games limits planning to those games (for a supervised manual tick)."""
    report = TickReport()
    now = deps.clock()
    vdir = _vdir(deps)
    start = capture_start(vdir, now)
    sched = newest_schedules(deps, now, allow_pull=True, report=report)
    kicks, games = _games(sched)
    if only_games is not None:
        kicks = [g for g in kicks if g.game_id in only_games]
    cfg = ShadowWindows.from_params(load_params())
    plan = plan_tick(now, kicks, _latest_status(vdir), _attempts(vdir), start, cfg)
    if plan.status_rows:
        _append(deps, "snapshot_status", plan.status_rows, report)
        report.status_rows += len(plan.status_rows)
    report.due = len(plan.due)
    team_codes, team_map = load_team_codes(), load_team_map()
    for d in sorted(plan.due, key=lambda x: (x.window.target, x.game.game_id)):
        g, w = d.game, d.window
        base = {
            "game_id": g.game_id,
            "season": g.season,
            "week": g.week,
            "snapshot_type": str(w.snapshot_type),
            "pricing_mode": PRICING_MODE_CAPTURE,
        }
        t_try = deps.clock()
        try:
            snap = take_snapshot(
                deps.kalshi,
                g,
                w,
                games=games,
                team_codes=team_codes,
                team_map=team_map,
                mapper=deps.mapper_factory(g.season, t_try),
                clock=deps.clock,
                code_commit=deps.code_commit,
            )
        except _API_ERRORS as exc:
            report.api_errors += 1
            _append(
                deps,
                "attempts",
                [
                    {
                        **base,
                        "attempt_ts": t_try,
                        "outcome": "api_error",
                        "detail": f"{type(exc).__name__}: {exc}"[:500],
                    }
                ],
                report,
            )
            continue
        if snap.outcome == "no_markets":
            report.no_markets += 1
            _append(
                deps,
                "attempts",
                [{**base, "attempt_ts": t_try, "outcome": "no_markets", "detail": ""}],
                report,
            )
            continue
        taken = snap.rows[0]["taken_ts"]
        verdict = judge(taken, w)
        try:
            if verdict is None:
                raise StoreError(f"taken {taken.isoformat()} outside the window")
            _append(deps, "snapshots", snap.rows, report)
            if snap.book_rows:
                _append(deps, "book_levels", snap.book_rows, report)
        except StoreError as exc:  # incl. KickoffPassed
            report.errors.append(f"{g.game_id} {w.snapshot_type}: {exc}")
            _append(
                deps,
                "attempts",
                [{**base, "attempt_ts": t_try, "outcome": "error", "detail": str(exc)[:500]}],
                report,
            )
            continue
        _append(
            deps,
            "snapshot_status",
            [status_row(g, w, verdict, taken, "", snap.n_markets, snap.n_books)],
            report,
        )
        _append(
            deps, "attempts", [{**base, "attempt_ts": t_try, "outcome": "ok", "detail": ""}], report
        )
        report.snapshots_ok += 1
    return report


def run_close(deps: TickDeps) -> int:
    """SHD-05: for every ok/ok_late T-24h and T-90m snapshot whose game has kicked off (newest
    stored kickoff) and has no closes rows yet, fetch each market's trades and write one closes
    row per market. Returns rows written."""
    now = deps.clock()
    vdir = _vdir(deps)
    kicks = {g.game_id: g for g in _games(newest_schedules(deps, now, allow_pull=False))[0]}
    done: set[tuple[str, str, dt.datetime]] = set()
    closes = read_table(vdir, "closes")
    if not closes.is_empty():
        done = set(closes.select("game_id", "snapshot_type", "taken_ts").iter_rows())
    snaps = read_table(vdir, "snapshots")
    trades: dict[tuple[str, dt.datetime], list[dict[str, Any]]] = {}
    written = 0
    for (gid, stype), rec in sorted(_latest_status(vdir).items()):
        g = kicks.get(gid)
        if (
            stype not in _PRICED_TYPES
            or rec.status not in ("ok", "ok_late")
            or g is None
            or now < g.kickoff_utc
            or (gid, stype, rec.taken_ts) in done
        ):
            continue
        mine = snaps.filter(
            (pl.col("game_id") == gid)
            & (pl.col("snapshot_type") == stype)
            & (pl.col("taken_ts") == rec.taken_ts)
        )
        rows = []
        try:
            for ticker in sorted(set(mine["ticker"].to_list())):
                key = (ticker, g.kickoff_utc)
                if key not in trades:
                    trades[key] = list(
                        deps.kalshi.trades(ticker, max_ts=int(g.kickoff_utc.timestamp()) + 1)
                    )
                assert rec.taken_ts is not None
                c = closing_price(trades[key], g.kickoff_utc, rec.taken_ts)
                rows.append(
                    {
                        "game_id": gid,
                        "season": g.season,
                        "week": g.week,
                        "snapshot_type": stype,
                        "taken_ts": rec.taken_ts,
                        "ticker": ticker,
                        "kickoff_utc": g.kickoff_utc,
                        "close_status": c.status,
                        "close_yes_cc": c.close_yes_cc,
                        "last_trade_id": c.last_trade_id,
                        "last_trade_ts": c.last_trade_ts,
                        "n_pre_kickoff_trades": c.n_pre_kickoff,
                        "closed_at": deps.clock(),
                        "pricing_mode": PRICING_MODE_CAPTURE,
                    }
                )
        except _API_ERRORS as exc:
            log.warning("close %s %s: %s; retried next run", gid, stype, exc)
            continue
        if rows:
            _append(deps, "closes", rows, None)
            written += len(rows)
    return written


def run_settle(deps: TickDeps) -> int:
    """SHD-13: for every closed market without a result, read its event's markets (live, then
    historical) and write a results row once Kalshi has settled it. Returns rows written."""
    vdir = _vdir(deps)
    closes = read_table(vdir, "closes")
    if closes.is_empty():
        return 0
    results = read_table(vdir, "results")
    have = set() if results.is_empty() else set(results["ticker"].to_list())
    pending = set(closes["ticker"].to_list()) - have
    if not pending:
        return 0
    snaps = read_table(vdir, "snapshots").filter(pl.col("ticker").is_in(sorted(pending)))
    meta = {
        r["ticker"]: r
        for r in snaps.select("ticker", "event_ticker", "game_id", "season", "week")
        .unique("ticker", keep="first")
        .iter_rows(named=True)
    }
    events: dict[str, list[str]] = defaultdict(list)
    for t in sorted(pending):
        events[meta[t]["event_ticker"]].append(t)
    rows = []
    for ev, tickers in sorted(events.items()):
        try:
            found = {m["ticker"]: m for m, _hist in markets_for_event(deps.kalshi, ev)}
        except _API_ERRORS as exc:
            log.warning("settle %s: %s; retried next run", ev, exc)
            continue
        for t in tickers:
            m = found.get(t)
            v = None if m is None else settle_value(m)
            if m is None or v is None:
                continue
            rows.append(
                {
                    **meta[t],
                    "market_status": m.get("status"),
                    "result": m.get("result"),
                    "settlement_value_dollars": m.get("settlement_value_dollars"),
                    "result_status": v[0],
                    "result_value": v[1],
                    "settled_seen_at": deps.clock(),
                    "market_json": json.dumps(m, sort_keys=True, ensure_ascii=False),
                    "pricing_mode": PRICING_MODE_CAPTURE,
                }
            )
    if rows:
        _append(deps, "results", rows, None)
    return len(rows)


# --- live wiring ---------------------------------------------------------------------------


def _code_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


def _raw_schedules(season: int) -> tuple[pl.DataFrame, dt.datetime]:
    from ge.ingest.raw import DATA_ROOT, partitions

    parts = partitions(DATA_ROOT, "schedules", season)
    if not parts:
        raise FileNotFoundError(f"no {season} schedules in data/raw")
    at = dt.datetime.strptime(parts[-1].name.split("=", 1)[1], "%Y%m%dT%H%M%SZ").replace(
        tzinfo=dt.UTC
    )
    return pl.read_parquet(parts[-1] / "part.parquet").drop(
        ["pulled_at", "source"], strict=False
    ), at


def _pull_schedules(season: int) -> pl.DataFrame:
    from ge.ingest.nflverse import DATASETS

    return DATASETS["schedules"].loader(season)


def roster_mapper(season: int, as_of: dt.datetime) -> Mapper:
    """PRV-02 at as_of. No rosters_weekly pull for the season is a data gap: those markets
    are unpriced as no_roster_pull and the run continues (PRV-02, sync 2026-11-21)."""
    from ge.pricer_v0.player_map import map_player, roster_as_of

    team_map = load_team_map()
    try:
        roster = roster_as_of(season, as_of)
    except FileNotFoundError:
        return lambda name, team, week: MapResult(False, "no_roster_pull", None, None, None, None)

    def m(name: str, team: str, week: int) -> MapResult:
        pm = map_player(name, team, week, roster, team_map)
        return MapResult(
            pm.mapped,
            None if pm.reason is None else str(pm.reason),
            pm.gsis_id,
            pm.nflverse_team,
            pm.roster_week,
            pm.roster_pulled_at,
        )

    return m


def live_deps(version: str, http: Any) -> TickDeps:
    """Real dependencies: KalshiPublic over the shared adaptive-rate PublicClient."""
    from ge.config import load_ingest
    from ge.ingest.kalshi import KalshiPublic
    from ge.ingest.nflverse import current_season

    def now() -> dt.datetime:
        return dt.datetime.now(dt.UTC)

    return TickDeps(
        store=ShadowStore(version, clock=now),
        kalshi=KalshiPublic(http, load_ingest().kalshi),
        clock=now,
        season=current_season(),
        raw_schedules=_raw_schedules,
        pull_schedules=_pull_schedules,
        mapper_factory=roster_mapper,
        code_commit=_code_commit(),
    )


def tables_summary(vdir: Path, tables: Iterable[str]) -> dict[str, int]:
    return {t: read_table(vdir, t).height for t in tables}
