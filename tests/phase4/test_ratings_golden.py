"""PRJ-01a golden test on real data: ratings_for_game for the fixture store's week-8 game
equals an independent oracle built here from the snapshot's raw rows.

The oracle uses the Phase 3 row filters (tests/phase3/oracle.py), G3 games ago within the
season, the home and rest terms straight from the schedules (travel and time-zone
coefficients are 0 in the test window constants; coa07_features is checked against coa_07 in
test_window_fit.py), a play-level closed-form ridge, p_A over both seasons by kickoff order,
and the points formula. Penalty, half-lives and window constants are test settings
(tests/phase4/conftest.py)."""

from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest

from ge.metrics.coaching import CoachingRegistry
from ge.models.ratings import RATING_TYPES, ratings_for_game
from ge.store.snapshot import snapshot
from tests.phase3 import oracle as o
from tests.phase3.conftest import MAIN_WEEK, STORE, first_game
from tests.phase4.conftest import CONST_SETTINGS, FIT_SETTINGS
from tests.phase4.test_ratings_math import _oracle

SET = FIT_SETTINGS["S2024"]


def _home_rest(sched: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {r["game_id"]: r for r in sched}


def _offense_terms(g: dict[str, Any], off: str) -> tuple[float, float]:
    """(home, d_rest) for the offense, from one schedules row."""
    is_home = off == g["home_team"]
    home = 0.0 if g["location"] == "Neutral" else (1.0 if is_home else -1.0)
    mine, theirs = (g["home_rest"], g["away_rest"]) if is_home else (g["away_rest"], g["home_rest"])
    return home, float(mine) - float(theirs)


@pytest.mark.usefixtures("fit_env")
def test_week8_ratings_and_lines_match_oracle(
    ratings_root: Path, registry: CoachingRegistry
) -> None:
    import polars as pl

    gid = first_game(MAIN_WEEK)
    got = ratings_for_game(gid, root=STORE, ratings_root=ratings_root, registry=registry)
    snap = snapshot(gid, root=STORE)
    season = snap.season
    pbp = snap.collect("pbp")
    cur = pbp.filter(pl.col("season") == season).to_dicts()
    sched = _home_rest(snap.collect("schedules").to_dicts())
    ga = o.games_ago(cur)
    c = CONST_SETTINGS
    rows = []
    for r in cur:
        if not o.qualifying(r) or r["epa"] is None:
            continue
        home, d_rest = _offense_terms(sched[r["game_id"]], r["posteam"])
        rows.append(
            {
                "posteam": r["posteam"],
                "defteam": r["defteam"],
                "is_pass": r["pass"] == 1,
                "epa": float(r["epa"]),
                "g_off": float(ga[r["posteam"]][r["game_id"]]),
                "offset": c["home"] * home + c["rest"] * d_rest,
            }
        )
    done = snap.collect("schedules").filter(pl.col("season") == season)
    teams = sorted(set(done["home_team"]) | set(done["away_team"]))
    assert len(teams) == 32  # every team has played by week 8 in the fixture
    coef, se, sigma2 = _oracle(pl.DataFrame(rows), teams, SET["penalty"], SET["h_eff"], None)

    assert got.table.teams == tuple(teams)
    assert got.table.int_pass == pytest.approx(coef["int_pass"], abs=1e-9)
    assert got.table.int_run == pytest.approx(coef["int_run"], abs=1e-9)
    assert got.table.sigma2 == pytest.approx(sigma2, rel=1e-9)
    for t in teams:
        for k in RATING_TYPES:
            assert got.table.values[(t, k)] == pytest.approx(coef[(t, k)], abs=1e-9), (t, k)
            assert got.table.se[(t, k)] == pytest.approx(se[(t, k)], rel=1e-7), (t, k)

    # p_A over both seasons in the snapshot, games ago by (season, week) across the boundary.
    both = [r for r in pbp.to_dicts() if o.qualifying(r) and r["epa"] is not None]
    order: dict[str, set[tuple[int, int, str]]] = defaultdict(set)
    for r in both:
        order[r["posteam"]].add((r["season"], r["week"], r["game_id"]))
    g_all = {
        t: {gid_: i for i, (_, _, gid_) in enumerate(sorted(gs, reverse=True))}
        for t, gs in order.items()
    }
    num: dict[str, list[float]] = defaultdict(list)
    den: dict[str, list[float]] = defaultdict(list)
    for r in both:
        w = 0.5 ** (g_all[r["posteam"]][r["game_id"]] / SET["h_usage"])
        num[r["posteam"]].append(w * (r["pass"] == 1))
        den[r["posteam"]].append(w)
    p = {t: math.fsum(num[t]) / math.fsum(den[t]) for t in num}
    for t in teams:
        assert got.pass_rate[t] == pytest.approx(p[t], rel=1e-12), t

    tgt = snap.collect("target_game").row(0, named=True)
    home_t, away_t = tgt["home_team"], tgt["away_team"]

    def e(off: str, de: str) -> float:
        h, d = _offense_terms(tgt, off)
        return (
            p[off] * (coef["int_pass"] + coef[(off, "off_pass")] + coef[(de, "def_pass")])
            + (1 - p[off]) * (coef["int_run"] + coef[(off, "off_run")] + coef[(de, "def_run")])
            + c["home"] * h
            + c["rest"] * d
        )

    def pts(x: float) -> float:
        return c["league_drives"] * (c["league_ppd"] + c["c"] * (x - c["league_epa"]))

    ph, pa = pts(e(home_t, away_t)), pts(e(away_t, home_t))
    assert (got.lines.home_team, got.lines.away_team) == (home_t, away_t)
    assert got.lines.spread == pytest.approx(ph - pa, abs=1e-9)
    assert got.lines.total == pytest.approx(ph + pa, abs=1e-9)
    assert got.params.window == "S2024" and got.consts.window == "S2024"
