"""G4 prior-season carryover on week-1 and week-3 snapshots.

Spec G4 (docs synced 2026-10-04): a new play-caller comes from COA-01, and until COA-01 has
rows a head-coach change in the schedules data stands in; a new QB means the team's
most-dropback passer differs from last season's; relocated teams keep their history, matched
by franchise with the nflverse teams table. An unknown change still raises (user decision
2026-10-02). Raw values always compute."""

from __future__ import annotations

import csv
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

import polars as pl
import pytest

from ge.metrics.coaching import REGISTRY_COLUMNS, load_registry
from ge.metrics.context import build_context
from ge.metrics.registry import raw, shrunk
from ge.store.snapshot import snapshot
from tests.phase3 import oracle as o
from tests.phase3.conftest import G4_WEEK, SEASON, STORE, first_game, store_table

H = o.v(o.C.g3_efficiency_half_life_games)
EXTRA = o.v(o.C.g4_new_caller_or_qb_extra_regression)
K = o.P.offense.off_01_k_overall.value


def _synthetic_registry(path: Path, teams: list[str]) -> Path:
    """Placeholder rows, not real coaches: every team keeps one caller from before 2023."""
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(REGISTRY_COLUMNS))
        w.writeheader()
        for t in teams:
            w.writerow(
                {
                    "team": t,
                    "head_coach": f"TEST-HC-{t}",
                    "offensive_coordinator": f"TEST-OC-{t}",
                    "defensive_coordinator": f"TEST-DC-{t}",
                    "offensive_play_caller": f"TEST-OPC-{t}",
                    "defensive_play_caller": f"TEST-DPC-{t}",
                    "effective_date": "2022-01-01",
                    "source_url": "https://example.invalid/synthetic-test-row",
                }
            )
    return path


def _qb(rows: list[dict[str, Any]]) -> dict[str, str]:
    c: Counter[tuple[str, str]] = Counter()
    for r in rows:
        if r["qb_dropback"] == 1 and o.scrimmage(r) and r["passer_player_id"] is not None:
            c[(r["posteam"], r["passer_player_id"])] += 1
    best: dict[str, tuple[int, str]] = {}
    for (t, p), n in c.items():
        if t not in best or (n, p) > best[t]:
            best[t] = (n, p)
    return {t: p for t, (_, p) in best.items()}


def _head_coach(sched: list[dict[str, Any]]) -> dict[str, str]:
    """Each team's head coach in its latest game in these schedule rows."""
    last: dict[str, tuple[str, str]] = {}
    for r in sched:
        for side in ("home", "away"):
            t, coach = r[f"{side}_team"], r[f"{side}_coach"]
            if t not in last or r["gameday"] > last[t][0]:
                last[t] = (r["gameday"], coach)
    return {t: c for t, (_, c) in last.items()}


def _expected(snap: Any, *, use_hc: bool) -> dict[str, tuple[float, bool]]:
    """Oracle: per team, (G4 prior for OFF-01 all, changed?)."""
    pbp = snap.collect("pbp")
    cur = pbp.filter(pl.col("season") == snap.season).to_dicts()
    last = pbp.filter(pl.col("season") == snap.season - 1).to_dicts()
    sched = snap.collect("schedules")
    hc_now = _head_coach(sched.filter(pl.col("season") == snap.season).to_dicts())
    hc_then = _head_coach(sched.filter(pl.col("season") == snap.season - 1).to_dicts())
    u_last = o.units(last, "posteam", o.qualifying, lambda r: "all", lambda r: r["epa"])
    agg_last, lg_last = o.aggregate(u_last, H), o.league(u_last)["all"]
    qb_now, qb_then = _qb(cur), _qb(last)
    out = {}
    for t in sorted(qb_now):
        base = o.shrink(agg_last.get((t, "all")), lg_last, K)
        changed = qb_now[t] != qb_then[t] or (use_hc and hc_now[t] != hc_then[t])
        out[t] = (base + EXTRA * (lg_last - base) if changed else base, changed)
    return out


def _check(ctx: Any, snap: Any, want: dict[str, tuple[float, bool]]) -> None:
    cur = snap.collect("pbp").filter(pl.col("season") == snap.season).to_dicts()
    agg_cur = o.aggregate(
        o.units(cur, "posteam", o.qualifying, lambda r: "all", lambda r: r["epa"]), H
    )
    got = {
        r["entity_id"]: r
        for r in shrunk(ctx, "OFF-01", "epa").filter(pl.col("cell") == "all").iter_rows(named=True)
    }
    for t, (prior, _) in want.items():
        assert got[t]["prior"] == pytest.approx(prior, rel=1e-12), t
        assert got[t]["shrunk"] == pytest.approx(o.shrink(agg_cur.get((t, "all")), prior, K)), t


def test_head_coach_stands_in_without_registry(g4_snap) -> None:  # type: ignore[no-untyped-def]
    """The repo registry has no rows: a head-coach change in schedules is the caller change."""
    ctx = build_context(g4_snap)
    assert g4_snap.week <= o.v(o.C.g4_prior_carryover_last_week)
    want = _expected(g4_snap, use_hc=True)
    _check(ctx, g4_snap, want)
    notes = {
        r["entity_id"]: r["note"] or ""
        for r in shrunk(ctx, "OFF-01", "epa").filter(pl.col("cell") == "all").iter_rows(named=True)
    }
    assert any(changed for _, changed in want.values())
    for t, (_, changed) in want.items():
        assert ("new " in notes[t]) == changed, (t, notes[t])
    assert any("head coach" in n for n in notes.values()), "no head-coach change in the fixture"
    # defense: a head-coach change only (no QB term)
    assert shrunk(ctx, "DEF-02", "success").height > 0
    assert raw(ctx, "OFF-01").height > 0


def test_registry_callers_replace_head_coach(g4_snap, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    """With COA-01 rows covering both dates, the registry decides; head coaches are ignored."""
    pbp = g4_snap.collect("pbp").filter(pl.col("season") == g4_snap.season)
    teams = sorted(set(pbp["home_team"].to_list()) | set(pbp["away_team"].to_list()))
    reg = load_registry(_synthetic_registry(tmp_path / "reg.csv", teams))
    ctx = build_context(g4_snap, registry=reg)
    want = _expected(g4_snap, use_hc=False)
    _check(ctx, g4_snap, want)
    assert any(changed for _, changed in want.values()), "fixture should contain a QB change"


def test_week_1_qb_unknown_raises() -> None:
    """Week 1: a team that hasn't played has no current-season dropbacks, so unless its head
    coach changed its QB change is unknown and the carryover raises. Every team still gets
    raw rows; teams yet to play have n = 0."""
    snap = snapshot(first_game(1), root=STORE)
    ctx = build_context(snap)
    with pytest.raises(NotImplementedError, match="G4"):
        shrunk(ctx, "OFF-01", "epa")
    rows = raw(ctx, "OFF-01").filter((pl.col("entity_type") == "team") & (pl.col("cell") == "all"))
    assert rows.height == 32
    played = set(
        snap.collect("pbp").filter(pl.col("season") == snap.season)["posteam"].drop_nulls()
    )
    assert played and len(played) < 32
    for r in rows.iter_rows(named=True):
        assert (r["n"] > 0) == (r["entity_id"] in played), r["entity_id"]


def _relocation_pair(present: set[str]) -> tuple[str, str]:
    """From the nflverse teams table: a franchise (team_id) with more than one abbreviation,
    one of them playing in the fixture's season. Returns (current, former)."""
    t = store_table("teams", 0).select("team_abbr", "team_id")
    for _tid, abbrs in sorted(t.group_by("team_id").agg(pl.col("team_abbr")).iter_rows()):
        cur = sorted(a for a in abbrs if a in present)
        old = sorted(a for a in abbrs if a not in present)
        if cur and old:
            return cur[0], old[0]
    raise AssertionError("teams table has no relocated franchise")


_TEAM_COLS = ("posteam", "defteam", "home_team", "away_team", "td_team", "timeout_team",
              "penalty_team", "team")  # fmt: skip


def test_relocated_team_keeps_its_history(g4_snap, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    """Rename one franchise to its former abbreviation in every prior-season table of a store
    copy: the carryover prior must not change."""
    present = set(
        g4_snap.collect("schedules").filter(pl.col("season") == SEASON)["home_team"].to_list()
    )
    cur, old = _relocation_pair(present)
    dst = tmp_path / "store"
    shutil.copytree(STORE, dst)
    for part in dst.glob(f"*/season={SEASON - 1}/*/part.parquet"):
        df = pl.read_parquet(part)
        cols = [c for c in _TEAM_COLS if c in df.columns]
        if cols:
            df.with_columns(pl.col(c).replace(cur, old) for c in cols).write_parquet(part)
    base = build_context(g4_snap)
    moved = build_context(snapshot(first_game(G4_WEEK), as_of=g4_snap.as_of, root=dst))
    assert old in set(moved.prior_context().teams["team"].to_list())
    a = shrunk(base, "OFF-01", "epa").filter(pl.col("entity_id") == cur)
    b = shrunk(moved, "OFF-01", "epa").filter(pl.col("entity_id") == cur)
    assert b["prior"].to_list() == pytest.approx(a["prior"].to_list(), rel=1e-12)
    assert b["note"].to_list() == a["note"].to_list()


def test_franchise_map_comes_from_teams_table(g4_snap) -> None:  # type: ignore[no-untyped-def]
    ctx = build_context(g4_snap)
    t = store_table("teams", 0)
    for abbr, tid in t.select("team_abbr", "team_id").iter_rows():
        assert ctx.franchise(abbr) == tid
    with pytest.raises(KeyError):
        ctx.franchise("NOT-A-TEAM")


def test_registry_columns() -> None:
    assert REGISTRY_COLUMNS == (
        "team",
        "head_coach",
        "offensive_coordinator",
        "defensive_coordinator",
        "offensive_play_caller",
        "defensive_play_caller",
        "effective_date",
        "source_url",
    )
