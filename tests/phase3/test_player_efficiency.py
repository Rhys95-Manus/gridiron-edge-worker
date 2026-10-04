"""Golden tests, spec section 4 efficiency: PLY-09, 10, 11, 16, 17 on the fixture's 2024
week-8 snapshot, and PLY-17 on the 2021 (no FTN) snapshot."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import polars as pl
import pytest

from ge.metrics.context import build_context
from ge.metrics.registry import raw, shrunk
from ge.store.snapshot import snapshot
from tests.phase3 import oracle as o
from tests.phase3 import oracle_player as op
from tests.phase3.conftest import STORE, first_game
from tests.phase3.test_player_usage import check
from tests.phase3.test_team_offense import RUN_CELLS, _run_stat, off01, off02

H = op.v(o.C.g3_efficiency_half_life_games)
PL = op.PL


def _keys(units) -> set[op.Key]:  # type: ignore[no-untyped-def]
    return {u[0] for u in units}


def _check_shrunk_fixed(ctx, sid, stat, agg, prior, k) -> None:  # type: ignore[no-untyped-def]
    got = {
        ((r["entity_id"], r["team"]), r["cell"]): r
        for r in shrunk(ctx, sid, stat).iter_rows(named=True)
    }
    for key, a in agg.items():
        assert got[key]["prior"] == prior and got[key]["k"] == k
        assert got[key]["shrunk"] == pytest.approx(op.shrink(a, prior, k), rel=1e-12, abs=1e-12)


def test_ply_09_yac_over_expected(ctx, rows) -> None:  # type: ignore[no-untyped-def]
    def keep(r: dict[str, Any]) -> bool:
        return (
            o.target(r)
            and r["complete_pass"] == 1
            and r["xyac_mean_yardage"] is not None
            and r["yards_after_catch"] is not None
        )

    u = op.own_units(
        rows,
        keep,
        lambda r: r["receiver_player_id"],
        lambda r: "all",
        lambda r: r["yards_after_catch"] - r["xyac_mean_yardage"],
    )
    agg = op.aggregate(u, H)
    check(raw(ctx, "PLY-09"), "yacoe", agg, _keys(u), ["all"], op.v(PL.ply_09_min_receptions))
    _check_shrunk_fixed(ctx, "PLY-09", "yacoe", agg, 0.0, op.v(PL.ply_09_k_receptions))


def test_ply_10_catch_rate_over_expected(ctx, rows) -> None:  # type: ignore[no-untyped-def]
    u = op.own_units(
        rows,
        lambda r: o.target(r) and r["cp"] is not None,
        lambda r: r["receiver_player_id"],
        lambda r: "all",
        lambda r: r["complete_pass"] - r["cp"],
    )
    agg = op.aggregate(u, H)
    check(raw(ctx, "PLY-10"), "croe", agg, _keys(u), ["all"], op.v(PL.ply_10_min_targets))
    _check_shrunk_fixed(ctx, "PLY-10", "croe", agg, 0.0, op.v(PL.ply_10_k_targets))


def test_ply_11_rushing_yards_over_expected(ctx, main_snap) -> None:  # type: ignore[no-untyped-def]
    """NGS weekly value, carry-weighted."""
    ngs = main_snap.collect("nextgen_rushing").filter(pl.col("season") == main_snap.season)
    week_g: dict[tuple[str, int], float] = {
        (r["team"], r["week"]): r["g"] for r in ctx.games.iter_rows(named=True)
    }
    u = []
    for r in ngs.to_dicts():
        att, per = r["rush_attempts"], r["rush_yards_over_expected_per_att"]
        if not att or per is None:
            continue
        g = week_g[(r["team_abbr"], r["week"])]
        u.append(
            ((r["player_gsis_id"], r["team_abbr"]), "all", g, att * per, float(att), float(att))
        )
    agg = op.aggregate(u, H)
    check(raw(ctx, "PLY-11"), "ryoe_per_carry", agg, _keys(u), ["all"], op.v(PL.ply_11_min_carries))
    _check_shrunk_fixed(ctx, "PLY-11", "ryoe_per_carry", agg, 0.0, op.v(PL.ply_11_k_carries))


def test_ply_16_back_directional_profile(ctx, rows) -> None:  # type: ignore[no-untyped-def]
    """Per back: share of his designed carries per lane (usage), success and EPA per lane
    (efficiency) shrunk toward his team's shrunk OFF-12 cell value."""
    whose = lambda r: r["rusher_player_id"]  # noqa: E731
    share_u = []
    ga = op.games_ago(rows)
    for r in rows:
        if op.usage_carry(r) and r["rusher_player_id"] is not None:
            for c in RUN_CELLS:
                share_u.append(
                    (
                        (r["rusher_player_id"], r["posteam"]),
                        c,
                        ga[r["posteam"]][r["game_id"]],
                        1.0 if o.run_cell(r) == c else 0.0,
                        1.0,
                        1.0,
                    )
                )
    frame = raw(ctx, "PLY-16")
    backs = _keys(share_u)
    h_use = op.v(o.C.g3_usage_half_life_games)
    check(frame, "share", op.aggregate(share_u, h_use), backs, RUN_CELLS)
    sums = (
        frame.filter(pl.col("stat") == "share")
        .group_by("entity_id", "team")
        .agg(pl.col("value").sum())
    )
    assert sums["value"].to_list() == pytest.approx([1.0] * sums.height)
    # per-back cells sum to his designed carries
    eff = {
        s: op.own_units(rows, o.designed_run, whose, o.run_cell, _run_stat(s))
        for s in ("success", "epa")
    }
    car = (
        frame.filter(pl.col("stat") == "success")
        .group_by("entity_id", "team")
        .agg(pl.col("n").sum())
    )
    for pid, team, n in car.iter_rows():
        assert n == sum(
            1
            for r in rows
            if o.designed_run(r) and r["rusher_player_id"] == pid and r["posteam"] == team
        )
    with pytest.raises(NotImplementedError, match="PLY-16"):
        shrunk(ctx, "PLY-16", "share")
    # team priors: OFF-12's shrunk cells (themselves shrunk toward OFF-01 / OFF-02 run)
    teams = sorted({t for _, t in backs})
    agg1, lg1 = off01(rows)
    agg2, lg2 = off02(rows)
    run_par = {
        "epa": {
            t: o.shrink(agg1.get((t, "run")), lg1["run"], o.P.offense.off_01_k_run.value)
            for t in teams
        },
        "success": {
            t: o.shrink(agg2.get((t, "run")), lg2["run"], o.P.offense.off_02_k.value) for t in teams
        },
    }
    k_team = {
        "epa": o.P.offense.off_12_k_epa_ypc.value,
        "success": o.P.offense.off_12_k_success.value,
    }
    k = op.v(PL.ply_16_k_carries)
    for stat, units in eff.items():
        agg = op.aggregate(units, H)
        check(frame, stat, agg, backs, RUN_CELLS, op.v(PL.ply_16_min_carries_per_cell))
        team_u = o.units(rows, "posteam", o.designed_run, o.run_cell, _run_stat(stat))
        tagg = o.aggregate(team_u, H)
        got = {
            ((r["entity_id"], r["team"]), r["cell"]): r
            for r in shrunk(ctx, "PLY-16", stat).iter_rows(named=True)
        }
        for key in backs:
            for c in RUN_CELLS:
                tprior = o.shrink(tagg.get((key[1], c)), run_par[stat][key[1]], k_team[stat])
                r = got[(key, c)]
                assert r["prior"] == pytest.approx(tprior, rel=1e-12), (key, c)
                assert r["shrunk"] == pytest.approx(
                    op.shrink(agg.get((key, c)), tprior, k), rel=1e-12, abs=1e-12
                )


def _blitz_arms(rows, ftn):  # type: ignore[no-untyped-def]
    ga = op.games_ago(rows)
    arms: dict[tuple[op.Key, bool], list[tuple[float, float, float]]] = defaultdict(list)
    lg: dict[bool, list[tuple[float, float]]] = defaultdict(list)
    for r in rows:
        if not o.dropback(r):
            continue
        f = ftn.get((r["game_id"], int(r["play_id"])))
        qb = op.dropback_qb(r)
        if f is None or f["n_blitzers"] is None or qb is None:
            continue
        b = f["n_blitzers"] >= op.v(PL.ply_17_blitz_min_blitzers)
        if not b and f["n_blitzers"] != op.v(PL.ply_17_no_blitz_blitzers):
            continue
        w = 0.5 ** (ga[r["posteam"]][r["game_id"]] / H)
        arms[((qb, r["posteam"]), b)].append((w, float(r["epa"]), float(r["sack"])))
        lg[b].append((float(r["epa"]), float(r["sack"])))
    return arms, lg


def test_ply_17_qb_vs_blitz(ctx, rows, ftn) -> None:  # type: ignore[no-untyped-def]
    arms, lg = _blitz_arms(rows, ftn)
    frame = raw(ctx, "PLY-17")
    got = {
        ((r["entity_id"], r["team"]), r["stat"]): r
        for r in frame.filter(pl.col("entity_type") == "player").iter_rows(named=True)
    }
    league = {
        r["stat"]: r["value"]
        for r in frame.filter(pl.col("entity_type") == "league").iter_rows(named=True)
    }
    k = op.v(PL.ply_17_k_blitzed_dropbacks)
    qbs = {key for key, _ in arms}
    sh = {
        s: {(r["entity_id"], r["team"]): r for r in shrunk(ctx, "PLY-17", s).iter_rows(named=True)}
        for s in ("epa_gap", "sack_gap")
    }
    for i, stat in ((1, "epa_gap"), (2, "sack_gap")):
        lgap = sum(x[i - 1] for x in lg[True]) / len(lg[True]) - sum(
            x[i - 1] for x in lg[False]
        ) / len(lg[False])
        assert league[stat] == pytest.approx(lgap, rel=1e-12)
        for key in qbs:
            on, off = arms.get((key, True), []), arms.get((key, False), [])
            r = got[(key, stat)]
            assert r["n"] == len(on)
            if on and off:
                m = lambda xs, i=i: sum(x[i] for x in xs) / len(xs)  # noqa: E731
                wm = lambda xs, i=i: sum(x[0] * x[i] for x in xs) / sum(x[0] for x in xs)  # noqa: E731
                assert r["value"] == pytest.approx(m(on) - m(off), rel=1e-12, abs=1e-12)
                vw = wm(on) - wm(off)
                assert r["value_w"] == pytest.approx(vw, rel=1e-12, abs=1e-12)
                ws = [x[0] for x in on]
                neff = sum(ws) ** 2 / sum(w * w for w in ws)
                assert r["n_eff"] == pytest.approx(neff, rel=1e-12)
                want = (neff * vw + k * lgap) / (neff + k)
                assert sh[stat][key]["shrunk"] == pytest.approx(want, rel=1e-12, abs=1e-12)
            else:
                assert r["value"] is None
                assert sh[stat][key]["shrunk"] == pytest.approx(lgap, rel=1e-12)
            assert r["below_min_sample"] == (len(on) < op.v(PL.ply_17_min_blitzed_dropbacks))


def test_ply_17_without_ftn_is_missing() -> None:
    """2021 has no FTN (ruling 2026-10-04): PLY-17 is missing, shrunk rows are null with a
    note, so matchup terms using it contribute zero (Phase 5)."""
    ctx = build_context(snapshot(first_game(6, season=2021), root=STORE))
    frame = raw(ctx, "PLY-17").filter(pl.col("entity_type") == "player")
    assert frame.height > 0 and frame["value"].null_count() == frame.height
    for stat in ("epa_gap", "sack_gap"):
        s = shrunk(ctx, "PLY-17", stat)
        assert s.height > 0
        assert s["shrunk"].null_count() == s.height
        assert set(s["note"].to_list()) == {"no FTN: missing"}
