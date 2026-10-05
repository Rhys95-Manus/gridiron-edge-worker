"""Golden tests, section 6b defensive counterparts: DEF-09 to DEF-17 on the 2024 week-8
snapshot. Team-level, on plays against, directions in the offense's frame."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import polars as pl
import pytest

from ge.metrics.registry import raw, shrunk
from tests.phase3 import oracle as o
from tests.phase3 import oracle_player as op
from tests.phase3 import oracle_skills as osk
from tests.phase3.golden import check_raw, check_shrunk
from tests.phase3.test_skills_qb import _check_gap
from tests.phase3.test_skills_rb_wr import box_band
from tests.phase3.test_team_defense import def01, def02
from tests.phase3.test_team_offense import PASS_CELLS, _full

H = o.v(o.C.g3_efficiency_half_life_games)
DP = o.P.defense


def _defteam(r: dict[str, Any]) -> tuple[str, str] | None:
    return None if r["defteam"] is None else (r["defteam"], r["defteam"])


def test_def_09_pass_map_allowed(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    frame = raw(ctx, "DEF-09")
    assert set(frame["stat"].unique().to_list()) == {"epa", "cpoe"}
    k = DP.def_09_k.value
    mn = DP.def_09_min_targets_per_cell.value
    ue = o.units(rows, "defteam", o.target, o.pass_cell, lambda r: r["epa"])
    agg = o.aggregate(ue, H)
    check_raw(frame, "epa", agg, o.league(ue), teams, PASS_CELLS, lambda c: mn)
    agg1, lg1 = def01(rows)
    par = {t: o.shrink(agg1.get((t, "pass")), lg1["pass"], DP.def_01_k_pass.value) for t in teams}
    want = {(t, c): o.shrink(agg.get((t, c)), par[t], k) for t in teams for c in PASS_CELLS}
    check_shrunk(
        shrunk(ctx, "DEF-09", "epa"),
        want,
        {(t, c): par[t] for t in teams for c in PASS_CELLS},
        lambda c: k,
    )
    uc = o.units(
        rows,
        "defteam",
        lambda r: o.target(r) and r["cp"] is not None,
        o.pass_cell,
        lambda r: r["complete_pass"] - r["cp"],
    )
    check_raw(frame, "cpoe", o.aggregate(uc, H), o.league(uc), teams, PASS_CELLS)
    with pytest.raises(NotImplementedError, match="DEF-09"):
        shrunk(ctx, "DEF-09", "cpoe")


def test_def_10_play_action_defense(ctx, rows, ftn) -> None:  # type: ignore[no-untyped-def]
    def flag(r):  # type: ignore[no-untyped-def]
        f = osk.ftn_field(ftn, r, "is_play_action")
        return None if f is None else bool(f)

    want, league = osk.gap(rows, o.dropback, _defteam, flag, lambda r: float(r["epa"]), H)
    _check_gap(
        ctx,
        "DEF-10",
        "epa_gap",
        want,
        league,
        DP.def_10_k.value,
        DP.def_10_min_play_action_dropbacks.value,
        entity="team",
    )


def test_def_11_tackling_after_catch(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    def keep(r: dict[str, Any]) -> bool:
        return (
            o.target(r)
            and r["complete_pass"] == 1
            and r["xyac_mean_yardage"] is not None
            and r["yards_after_catch"] is not None
        )

    u = o.units(
        rows,
        "defteam",
        keep,
        lambda r: "all",
        lambda r: r["yards_after_catch"] - r["xyac_mean_yardage"],
    )
    agg = o.aggregate(u, H)
    k = DP.def_11_k.value
    check_raw(
        raw(ctx, "DEF-11"),
        "yacoe",
        agg,
        o.league(u),
        teams,
        ["all"],
        lambda c: DP.def_11_min_receptions.value,
    )
    want = {(t, "all"): o.shrink(agg.get((t, "all")), 0.0, k) for t in teams}
    check_shrunk(shrunk(ctx, "DEF-11", "yacoe"), want, dict.fromkeys(want, 0.0), lambda c: k)


def test_def_12_box_tendency_and_split(ctx, rows, ftn, teams) -> None:  # type: ignore[no-untyped-def]
    frame = raw(ctx, "DEF-12")
    box = lambda r: osk.ftn_field(ftn, r, "n_defense_box")  # noqa: E731
    stacked = op.v(o.P.player.ply_24_stacked_box_min)
    us = o.units(
        rows,
        "defteam",
        lambda r: o.qualifying(r) and box(r) is not None,
        lambda r: "all",
        lambda r: 1.0 if box(r) >= stacked else 0.0,
    )
    check_raw(frame, "stacked_box_share", o.aggregate(us, H), o.league(us), teams, ["all"])
    with pytest.raises(NotImplementedError, match="DEF-12"):
        shrunk(ctx, "DEF-12", "stacked_box_share")
    bands = ["light", "standard", "stacked"]
    k = DP.def_12_k.value
    mn = DP.def_12_min_carries_per_band.value
    agg2, lg2 = def02(rows)
    par = {t: o.shrink(agg2.get((t, "run")), lg2["run"], DP.def_02_k.value) for t in teams}
    for stat, x in (("success", lambda r: r["success"]), ("ypc", lambda r: r["yards_gained"])):
        u = o.units(rows, "defteam", o.designed_run, lambda r: box_band(box(r)), x)
        agg = o.aggregate(u, H)
        check_raw(frame, stat, agg, o.league(u), teams, bands, lambda c: mn)
        if stat == "success":
            want = {(t, c): o.shrink(agg.get((t, c)), par[t], k) for t in teams for c in bands}
            check_shrunk(
                shrunk(ctx, "DEF-12", stat),
                want,
                {(t, c): par[t] for t in teams for c in bands},
                lambda c: k,
            )
        else:
            with pytest.raises(NotImplementedError, match="DEF-12"):
                shrunk(ctx, "DEF-12", stat)


def test_def_13_blitz_results(ctx, rows, ftn) -> None:  # type: ignore[no-untyped-def]
    pl_ = o.P.player

    def flag(r):  # type: ignore[no-untyped-def]
        n = osk.ftn_field(ftn, r, "n_blitzers")
        if n is None:
            return None
        if n >= op.v(pl_.ply_17_blitz_min_blitzers):
            return True
        return False if n == op.v(pl_.ply_17_no_blitz_blitzers) else None

    want, league = osk.gap(rows, o.dropback, _defteam, flag, lambda r: float(r["epa"]), H)
    _check_gap(
        ctx,
        "DEF-13",
        "epa_gap",
        want,
        league,
        DP.def_13_k.value,
        DP.def_13_min_blitzed_dropbacks.value,
        entity="team",
    )


def test_def_14_qb_runs_allowed(ctx, rows, teams, main_snap) -> None:  # type: ignore[no-untyped-def]
    pos = osk.positions(main_snap)
    frame = raw(ctx, "DEF-14")
    k = DP.def_14_k.value
    mn = DP.def_14_min_dropbacks.value
    scr = o.units(rows, "defteam", o.dropback, lambda r: "all", lambda r: r["qb_scramble"])
    agg = o.aggregate(scr, H)
    check_raw(frame, "scramble_rate", agg, o.league(scr), teams, ["all"], lambda c: mn)
    want, prior = _full(teams, ["all"], agg, o.league(scr), lambda c: k)
    check_shrunk(shrunk(ctx, "DEF-14", "scramble_rate"), want, prior, lambda c: k)
    # QB rushing yards per opponent dropback: x = yards on a QB rush, d = 1 per dropback
    ga = o.games_ago(rows)
    sx: dict[str, list[tuple[float, float, float]]] = defaultdict(list)
    for r in rows:
        if r["defteam"] is None:
            continue
        qb_rush = (o.dropback(r) and r["qb_scramble"] == 1) or (
            o.designed_run(r) and pos.get(r["rusher_player_id"]) == "QB"
        )
        db = o.dropback(r)
        if not (qb_rush or db):
            continue
        w = 0.5 ** (ga[r["defteam"]][r["game_id"]] / H)
        sx[r["defteam"]].append(
            (w, float(r["yards_gained"]) if qb_rush else 0.0, 1.0 if db else 0.0)
        )
    rows_ = {
        r["entity_id"]: r
        for r in frame.filter(
            (pl.col("stat") == "qb_rush_yards") & (pl.col("entity_type") == "team")
        ).iter_rows(named=True)
    }
    all_x = [x for v in sx.values() for x in v]
    league = sum(x for _, x, _ in all_x) / sum(d for _, _, d in all_x)
    sh = {r["entity_id"]: r for r in shrunk(ctx, "DEF-14", "qb_rush_yards").iter_rows(named=True)}
    for t, v in sx.items():
        n = sum(d for _, _, d in v)
        r = rows_[t]
        assert r["n"] == n
        assert r["value"] == pytest.approx(sum(x for _, x, _ in v) / n, rel=1e-12)
        vw = sum(w * x for w, x, _ in v) / sum(w * d for w, _, d in v)
        assert r["value_w"] == pytest.approx(vw, rel=1e-12)
        ne = sum(w * d for w, _, d in v) ** 2 / sum(w * w * d for w, _, d in v)
        assert sh[t]["shrunk"] == pytest.approx((ne * vw + k * league) / (ne + k), rel=1e-12)


def test_def_15_formation_run_defense(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    frame = raw(ctx, "DEF-15")
    cells = ["shotgun", "under_center"]
    cell = lambda r: "shotgun" if r["shotgun"] == 1 else "under_center"  # noqa: E731
    k = DP.def_15_k.value
    agg2, lg2 = def02(rows)
    par = {t: o.shrink(agg2.get((t, "run")), lg2["run"], DP.def_02_k.value) for t in teams}
    for stat, x in (("success", lambda r: r["success"]), ("ypc", lambda r: r["yards_gained"])):
        u = o.units(rows, "defteam", o.designed_run, cell, x)
        agg = o.aggregate(u, H)
        check_raw(
            frame, stat, agg, o.league(u), teams, cells, lambda c: DP.def_15_min_carries_each.value
        )
        if stat == "success":
            want = {(t, c): o.shrink(agg.get((t, c)), par[t], k) for t in teams for c in cells}
            check_shrunk(
                shrunk(ctx, "DEF-15", stat),
                want,
                {(t, c): par[t] for t in teams for c in cells},
                lambda c: k,
            )
        else:
            with pytest.raises(NotImplementedError, match="DEF-15"):
                shrunk(ctx, "DEF-15", stat)


def test_def_16_end_zone_pass_defense(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    def ez(r: dict[str, Any]) -> bool:
        return o.target(r) and r["air_yards"] is not None and r["air_yards"] >= r["yardline_100"]

    u = o.units(
        rows,
        "defteam",
        ez,
        lambda r: "all",
        lambda r: 1.0 if r["touchdown"] == 1 and r["td_team"] == r["posteam"] else 0.0,
    )
    agg, lg = o.aggregate(u, H), o.league(u)
    k = DP.def_16_k.value
    check_raw(
        raw(ctx, "DEF-16"),
        "td_rate",
        agg,
        lg,
        teams,
        ["all"],
        lambda c: DP.def_16_min_end_zone_targets.value,
    )
    want, prior = _full(teams, ["all"], agg, lg, lambda c: k)
    check_shrunk(shrunk(ctx, "DEF-16", "td_rate"), want, prior, lambda c: k)


CREDITS = {
    "sacks": [
        ("sack_player_id", 1.0),
        ("half_sack_1_player_id", 0.5),
        ("half_sack_2_player_id", 0.5),
    ],
    "qb_hits": [("qb_hit_1_player_id", 1.0), ("qb_hit_2_player_id", 1.0)],
    "passes_defensed": [("pass_defense_1_player_id", 1.0), ("pass_defense_2_player_id", 1.0)],
    "interceptions": [("interception_player_id", 1.0)],
    "tackles_for_loss": [
        ("tackle_for_loss_1_player_id", 1.0),
        ("tackle_for_loss_2_player_id", 1.0),
    ],
}


def test_def_17_defender_contribution_shares(ctx, rows, snaps, xw) -> None:  # type: ignore[no-untyped-def]
    """Each defender's share of team sacks (halves 0.5), QB hits, passes defensed, INTs and
    TFL, in games he played (defensive snap > 0); prior = his defensive snap share in those
    games; k = 20 events; garbage time kept (usage). Min 200 team defensive snaps."""
    ga = o.games_ago(rows)
    hu = op.v(o.C.g3_usage_half_life_games)
    played: dict[tuple[str, str], set[str]] = defaultdict(set)
    snap_num: dict[tuple[str, str], float] = defaultdict(float)
    team_def: dict[tuple[str, str], float] = {}
    for r in snaps:
        if r["defense_pct"]:
            key = (r["team"], r["game_id"])
            team_def[key] = max(team_def.get(key, 0.0), r["defense_snaps"] / r["defense_pct"])
    for r in snaps:
        if (r["defense_snaps"] or 0) > 0:
            pid = xw.get(r["pfr_player_id"], f"pfr:{r['pfr_player_id']}")
            played[(pid, r["team"])].add(r["game_id"])
            snap_num[(pid, r["team"])] += r["defense_snaps"]
    credits: dict[tuple[str, str, str], float] = defaultdict(float)  # (team, game, stat)
    mine: dict[tuple[str, str, str, str], float] = defaultdict(float)  # (pid, team, game, stat)
    for r in rows:
        if r["defteam"] is None or not o.scrimmage(r):
            continue
        for stat, cols in CREDITS.items():
            for col, wt in cols:
                if r[col] is not None:
                    credits[(r["defteam"], r["game_id"], stat)] += wt
                    mine[(r[col], r["defteam"], r["game_id"], stat)] += wt
    frame = raw(ctx, "DEF-17")
    got = {(r["entity_id"], r["team"], r["stat"]): r for r in frame.iter_rows(named=True)}
    k = DP.def_17_k_events_per_share.value
    checked = 0
    for (pid, team), gs in played.items():
        tsnaps = sum(team_def[(team, g)] for g in gs)
        for stat in CREDITS:
            num = sum(mine.get((pid, team, g, stat), 0.0) for g in gs)
            den = sum(credits.get((team, g, stat), 0.0) for g in gs)
            r = got[(pid, team, stat)]
            assert r["value"] == (pytest.approx(num / den, rel=1e-12) if den else None), (pid, stat)
            assert r["n"] == round(den)
            assert r["below_min_sample"] == (tsnaps < DP.def_17_min_team_defensive_snaps.value)
            ws = {g: 0.5 ** (ga[team][g] / hu) for g in gs}
            wd = sum(ws[g] * credits.get((team, g, stat), 0.0) for g in gs)
            if den:
                vw = sum(ws[g] * mine.get((pid, team, g, stat), 0.0) for g in gs) / wd
                assert r["value_w"] == pytest.approx(vw, rel=1e-12)
            checked += 1
    sh = {
        (r["entity_id"], r["team"]): r for r in shrunk(ctx, "DEF-17", "sacks").iter_rows(named=True)
    }
    for (pid, team), gs in list(played.items())[:200]:
        tsnaps = sum(team_def[(team, g)] for g in gs)
        assert sh[(pid, team)]["prior"] == pytest.approx(snap_num[(pid, team)] / tsnaps, rel=1e-12)
        assert sh[(pid, team)]["k"] == k
    assert checked > 1000
