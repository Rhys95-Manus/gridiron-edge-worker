"""Golden tests, spec section 2 (OFF-01 to OFF-17), on the fixture's 2024 week-8 snapshot.

Each expected value is computed by tests/phase3/oracle.py from the snapshot's raw rows."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import polars as pl
import pytest

from ge.metrics.registry import raw, shrunk
from tests.phase3 import oracle as o
from tests.phase3.golden import check_raw, check_shrunk

H = o.v(o.C.g3_efficiency_half_life_games)
OP = o.P.offense
SPLITS = {"all": lambda r: True, "pass": lambda r: r["pass"] == 1, "run": lambda r: r["rush"] == 1}
RUN_CELLS = [
    "left_end",
    "left_tackle",
    "left_guard",
    "middle",
    "right_guard",
    "right_tackle",
    "right_end",
    "unknown",
]
PASS_CELLS = [
    f"{loc}_{b}"
    for loc in ("left", "middle", "right")
    for b in ("behind", "short", "intermediate", "deep")
] + ["unknown"]
DZ_CELLS = [
    f"{d}_{z}" for d in ("d1", "d2", "d34") for z in ("own", "open", "red_zone", "goal_to_go")
]


def _split_units(rows, x):  # type: ignore[no-untyped-def]
    out = []
    for name, keep in SPLITS.items():
        out += o.units(
            rows, "posteam", lambda r, k=keep: o.qualifying(r) and k(r), lambda r, n=name: n, x
        )
    return out


def _shrunk_league(agg, lg, k_of):  # type: ignore[no-untyped-def]
    want, prior = {}, {}
    for (e, c), a in agg.items():
        want[(e, c)] = o.shrink(a, lg[c], k_of(c))
        prior[(e, c)] = lg[c]
    return want, prior


def _full(teams, cells, agg, lg, k_of):  # type: ignore[no-untyped-def]
    """Shrunk for every team x cell, including cells with no plays (shrunk = prior)."""
    want, prior = {}, {}
    for t in teams:
        for c in cells:
            want[(t, c)] = o.shrink(agg.get((t, c)), lg[c], k_of(c))
            prior[(t, c)] = lg[c]
    return want, prior


OFF01_K = {
    "all": OP.off_01_k_overall.value,
    "pass": OP.off_01_k_pass.value,
    "run": OP.off_01_k_run.value,
}
OFF01_MIN = {
    "all": OP.off_01_min_plays.value,
    "pass": OP.off_01_min_pass_plays.value,
    "run": OP.off_01_min_run_plays.value,
}


def off01(rows: list[dict[str, Any]]):  # type: ignore[no-untyped-def]
    u = _split_units(rows, lambda r: r["epa"])
    return o.aggregate(u, H), o.league(u)


def off02(rows: list[dict[str, Any]]):  # type: ignore[no-untyped-def]
    u = _split_units(rows, lambda r: r["success"])
    return o.aggregate(u, H), o.league(u)


def test_off_01_epa_per_play(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    agg, lg = off01(rows)
    check_raw(raw(ctx, "OFF-01"), "epa", agg, lg, teams, SPLITS, lambda c: OFF01_MIN[c])
    want, prior = _full(teams, SPLITS, agg, lg, lambda c: OFF01_K[c])
    check_shrunk(shrunk(ctx, "OFF-01", "epa"), want, prior, lambda c: OFF01_K[c])


def test_off_01_opponent_adjustment_waits_for_bt02(ctx) -> None:  # type: ignore[no-untyped-def]
    from ge.metrics import offense

    with pytest.raises(NotImplementedError, match="G6"):
        offense.off_01_adjusted(ctx)


def test_off_02_success_rate(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    agg, lg = off02(rows)
    k = OP.off_02_k.value
    check_raw(
        raw(ctx, "OFF-02"), "success", agg, lg, teams, SPLITS, lambda c: OP.off_02_min_plays.value
    )
    want, prior = _full(teams, SPLITS, agg, lg, lambda c: k)
    check_shrunk(shrunk(ctx, "OFF-02", "success"), want, prior, lambda c: k)


def test_off_03_down_and_zone(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    agg1, lg1 = off01(rows)
    agg2, lg2 = off02(rows)
    k01, k02 = OP.off_01_k_overall.value, OP.off_02_k.value
    parent = {
        "epa": {t: o.shrink(agg1.get((t, "all")), lg1["all"], k01) for t in teams},
        "success": {t: o.shrink(agg2.get((t, "all")), lg2["all"], k02) for t in teams},
    }
    frame = raw(ctx, "OFF-03")
    k = OP.off_03_k.value
    for stat in ("epa", "success"):
        u = o.units(rows, "posteam", o.qualifying, o.down_zone_cell, lambda r, s=stat: r[s])
        agg = o.aggregate(u, H)
        check_raw(
            frame,
            stat,
            agg,
            o.league(u),
            teams,
            DZ_CELLS,
            lambda c: OP.off_03_min_plays_per_cell.value,
        )
        want = {
            (t, c): o.shrink(agg.get((t, c)), parent[stat][t], k) for t in teams for c in DZ_CELLS
        }
        prior = {(t, c): parent[stat][t] for t in teams for c in DZ_CELLS}
        check_shrunk(shrunk(ctx, "OFF-03", stat), want, prior, lambda c: k)
    # cells partition the qualifying plays
    q = sum(1 for r in rows if o.qualifying(r))
    ent = frame.filter((pl.col("stat") == "epa") & (pl.col("entity_type") == "team"))
    assert ent["n"].sum() == q


def _neutral_q(r):  # type: ignore[no-untyped-def]
    return o.qualifying(r) and o.neutral(r)


def test_off_04_early_down_pass_rate(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    u = o.units(
        rows,
        "posteam",
        lambda r: _neutral_q(r) and r["down"] in (1, 2),
        lambda r: "all",
        lambda r: r["pass"],
    )
    agg, lg = o.aggregate(u, H), o.league(u)
    k = OP.off_04_k.value
    check_raw(
        raw(ctx, "OFF-04"),
        "pass_rate",
        agg,
        lg,
        teams,
        ["all"],
        lambda c: OP.off_04_min_plays.value,
    )
    want, prior = _full(teams, ["all"], agg, lg, lambda c: k)
    check_shrunk(shrunk(ctx, "OFF-04", "pass_rate"), want, prior, lambda c: k)


def test_off_05_proe(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    u = o.units(
        rows,
        "posteam",
        lambda r: _neutral_q(r) and r["xpass"] is not None,
        lambda r: "all",
        lambda r: r["pass"] - r["xpass"],
    )
    agg, lg = o.aggregate(u, H), o.league(u)
    k = OP.off_05_k.value
    check_raw(
        raw(ctx, "OFF-05"), "proe", agg, lg, teams, ["all"], lambda c: OP.off_05_min_plays.value
    )
    want = {(t, "all"): o.shrink(agg.get((t, "all")), 0.0, k) for t in teams}
    check_shrunk(shrunk(ctx, "OFF-05", "proe"), want, dict.fromkeys(want, 0.0), lambda c: k)


@pytest.mark.parametrize(
    ("spec_id", "stat", "field", "keep", "min_key", "k_key"),
    [
        (
            "OFF-06",
            "play_action_rate",
            "is_play_action",
            "dropback",
            "off_06_min_dropbacks",
            "off_06_k",
        ),
        ("OFF-07", "motion_rate", "is_motion", "qualifying", "off_07_min_plays", "off_07_k"),
        ("OFF-08", "rpo_rate", "is_rpo", "qualifying", "off_08_min_plays", "off_08_k"),
    ],
)
def test_off_06_to_08_ftn_rates(  # type: ignore[no-untyped-def]
    ctx, rows, ftn, teams, spec_id, stat, field, keep, min_key, k_key
) -> None:
    keep_fn = getattr(o, keep)

    def x(r):  # type: ignore[no-untyped-def]
        f = ftn.get((r["game_id"], int(r["play_id"])))
        return None if f is None or f[field] is None else float(f[field])

    u = o.units(rows, "posteam", keep_fn, lambda r: "all", x)
    agg, lg = o.aggregate(u, H), o.league(u)
    k = getattr(OP, k_key).value
    check_raw(
        raw(ctx, spec_id), stat, agg, lg, teams, ["all"], lambda c: getattr(OP, min_key).value
    )
    want, prior = _full(teams, ["all"], agg, lg, lambda c: k)
    check_shrunk(shrunk(ctx, spec_id, stat), want, prior, lambda c: k)


def test_off_09_shotgun_rate(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    u = o.units(rows, "posteam", o.qualifying, lambda r: "all", lambda r: r["shotgun"])
    agg, lg = o.aggregate(u, H), o.league(u)
    k = OP.off_09_k.value
    check_raw(
        raw(ctx, "OFF-09"),
        "shotgun_rate",
        agg,
        lg,
        teams,
        ["all"],
        lambda c: OP.off_09_min_plays.value,
    )
    want, prior = _full(teams, ["all"], agg, lg, lambda c: k)
    check_shrunk(shrunk(ctx, "OFF-09", "shotgun_rate"), want, prior, lambda c: k)


def test_off_10_neutral_pace(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    u = o.pace_pairs(rows)
    agg, lg = o.aggregate(u, H), o.league(u)
    k = OP.off_10_k_pairs.value
    check_raw(
        raw(ctx, "OFF-10"),
        "seconds_per_play",
        agg,
        lg,
        teams,
        ["all"],
        lambda c: OP.off_10_min_pairs.value,
    )
    want, prior = _full(teams, ["all"], agg, lg, lambda c: k)
    check_shrunk(shrunk(ctx, "OFF-10", "seconds_per_play"), want, prior, lambda c: k)
    assert max(x for *_, x in u) <= OP.off_10_max_snap_gap_seconds.value


def test_off_11_plays_per_game(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    ga = o.games_ago(rows)
    count: dict[tuple[str, str], int] = defaultdict(int)
    for r in rows:
        if o.qualifying(r):
            count[(r["posteam"], r["game_id"])] += 1
    u = [(t, "all", ga[t][g], float(n)) for (t, g), n in count.items()]
    agg, lg = o.aggregate(u, H), o.league(u)
    k = OP.off_11_k_games.value
    check_raw(
        raw(ctx, "OFF-11"),
        "plays_per_game",
        agg,
        lg,
        teams,
        ["all"],
        lambda c: OP.off_11_min_games.value,
    )
    want, prior = _full(teams, ["all"], agg, lg, lambda c: k)
    check_shrunk(shrunk(ctx, "OFF-11", "plays_per_game"), want, prior, lambda c: k)


def _run_stat(stat: str):  # type: ignore[no-untyped-def]
    exp = OP.off_12_explosive_run_min_yards.value
    return {
        "carries": lambda r: 1.0,
        "ypc": lambda r: r["yards_gained"],
        "epa": lambda r: r["epa"],
        "success": lambda r: r["success"],
        "explosive": lambda r: 1.0 if r["yards_gained"] >= exp else 0.0,
    }[stat]


def test_off_12_directional_run_grid(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    frame = raw(ctx, "OFF-12")
    for stat in ("carries", "ypc", "epa", "success", "explosive"):
        u = o.units(rows, "posteam", o.designed_run, o.run_cell, _run_stat(stat))
        check_raw(
            frame,
            stat,
            o.aggregate(u, H),
            o.league(u),
            teams,
            RUN_CELLS,
            lambda c: OP.off_12_min_carries_per_cell.value,
        )
    # BUILD_PLAN: cell carries sum to the team's designed carries
    car = frame.filter((pl.col("stat") == "carries") & (pl.col("entity_type") == "team"))
    per_team = dict(car.group_by("entity_id").agg(pl.col("n").sum()).iter_rows())
    for t in teams:
        assert per_team[t] == sum(1 for r in rows if o.designed_run(r) and r["posteam"] == t)
    # shrunk: EPA toward OFF-01 run, success toward OFF-02 run; YPC and explosive raise
    agg1, lg1 = off01(rows)
    agg2, lg2 = off02(rows)
    parents = {
        "epa": (
            {t: o.shrink(agg1.get((t, "run")), lg1["run"], OP.off_01_k_run.value) for t in teams},
            OP.off_12_k_epa_ypc.value,
        ),
        "success": (
            {t: o.shrink(agg2.get((t, "run")), lg2["run"], OP.off_02_k.value) for t in teams},
            OP.off_12_k_success.value,
        ),
    }
    for stat, (par, k) in parents.items():
        u = o.units(rows, "posteam", o.designed_run, o.run_cell, _run_stat(stat))
        agg = o.aggregate(u, H)
        want = {(t, c): o.shrink(agg.get((t, c)), par[t], k) for t in teams for c in RUN_CELLS}
        prior = {(t, c): par[t] for t in teams for c in RUN_CELLS}
        check_shrunk(shrunk(ctx, "OFF-12", stat), want, prior, lambda c, k=k: k)
    for stat in ("ypc", "explosive"):
        with pytest.raises(NotImplementedError, match="OFF-12"):
            shrunk(ctx, "OFF-12", stat)


def test_off_13_pass_map(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    frame = raw(ctx, "OFF-13")
    k = OP.off_13_k_targets.value
    # share: unit = team target, x = 1 if in the cell
    u = []
    ga = o.games_ago(rows)
    for r in rows:
        if o.target(r):
            for c in PASS_CELLS:
                u.append(
                    (
                        r["posteam"],
                        c,
                        ga[r["posteam"]][r["game_id"]],
                        1.0 if o.pass_cell(r) == c else 0.0,
                    )
                )
    agg, lg = o.aggregate(u, H), o.league(u)
    check_raw(frame, "share", agg, lg, teams, PASS_CELLS)
    want, prior = _full(teams, PASS_CELLS, agg, lg, lambda c: k)
    check_shrunk(shrunk(ctx, "OFF-13", "share"), want, prior, lambda c: k)
    tot = frame.filter((pl.col("stat") == "share") & (pl.col("entity_type") == "team"))
    sums = tot.group_by("entity_id").agg(pl.col("value").sum())
    assert sums["value"].to_list() == pytest.approx([1.0] * sums.height)
    # epa per target toward the team's shrunk pass EPA
    agg1, lg1 = off01(rows)
    par = {t: o.shrink(agg1.get((t, "pass")), lg1["pass"], OP.off_01_k_pass.value) for t in teams}
    ue = o.units(rows, "posteam", o.target, o.pass_cell, lambda r: r["epa"])
    agge = o.aggregate(ue, H)
    min_n = OP.off_13_min_targets_per_cell.value
    check_raw(frame, "epa", agge, o.league(ue), teams, PASS_CELLS, lambda c: min_n)
    want = {(t, c): o.shrink(agge.get((t, c)), par[t], k) for t in teams for c in PASS_CELLS}
    prior = {(t, c): par[t] for t in teams for c in PASS_CELLS}
    check_shrunk(shrunk(ctx, "OFF-13", "epa"), want, prior, lambda c: k)
    # completion over expected: raw only
    uc = o.units(
        rows,
        "posteam",
        lambda r: o.target(r) and r["cp"] is not None,
        o.pass_cell,
        lambda r: r["complete_pass"] - r["cp"],
    )
    check_raw(frame, "cpoe", o.aggregate(uc, H), o.league(uc), teams, PASS_CELLS)
    with pytest.raises(NotImplementedError, match="OFF-13"):
        shrunk(ctx, "OFF-13", "cpoe")
    # share rows are greyed by the cell's own target count
    share = {(r["entity_id"], r["cell"]): r for r in tot.iter_rows(named=True)}
    for (t, c), a in agge.items():
        assert share[(t, c)]["below_min_sample"] == (a.n < min_n)


def test_off_14_red_zone(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    frame = raw(ctx, "OFF-14")
    zones = [
        OP.off_14_zone_20_yardline_100.value,
        OP.off_14_zone_10_yardline_100.value,
        OP.off_14_zone_5_yardline_100.value,
    ]
    cells = [f"inside_{int(z)}" for z in zones]
    up, ut = [], []
    for z in zones:
        up += o.units(
            rows,
            "posteam",
            lambda r, z=z: o.qualifying(r) and r["yardline_100"] <= z,
            lambda r, z=z: f"inside_{int(z)}",
            lambda r: r["pass"],
        )
        ut += o.zone_trips(rows, "posteam", z)
    for stat, u, kk, mm in (
        ("pass_share", up, OP.off_14_k_plays.value, OP.off_14_min_plays.value),
        ("td_per_trip", ut, OP.off_14_k_trips.value, OP.off_14_min_trips.value),
    ):
        agg, lg = o.aggregate(u, H), o.league(u)
        check_raw(frame, stat, agg, lg, teams, cells, lambda c, mm=mm: mm)
        want, prior = _full(teams, cells, agg, lg, lambda c, kk=kk: kk)
        check_shrunk(shrunk(ctx, "OFF-14", stat), want, prior, lambda c, kk=kk: kk)


def test_off_15_pass_protection(ctx, rows, teams, main_snap) -> None:  # type: ignore[no-untyped-def]
    frame = raw(ctx, "OFF-15")
    k = OP.off_15_k.value
    for stat, x in (
        ("sack_rate", lambda r: r["sack"]),
        ("hit_rate", lambda r: 1.0 if r["sack"] == 1 or r["qb_hit"] == 1 else 0.0),
    ):
        u = o.units(rows, "posteam", o.dropback, lambda r: "all", x)
        agg, lg = o.aggregate(u, H), o.league(u)
        check_raw(frame, stat, agg, lg, teams, ["all"], lambda c: OP.off_15_min_dropbacks.value)
        want, prior = _full(teams, ["all"], agg, lg, lambda c: k)
        check_shrunk(shrunk(ctx, "OFF-15", stat), want, prior, lambda c: k)
    # time to throw: NGS weekly, attempts-weighted (A24), display only
    ngs = main_snap.collect("nextgen_passing").filter(pl.col("season") == main_snap.season)
    tw: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for r in ngs.to_dicts():
        if r["avg_time_to_throw"] is not None and r["attempts"]:
            tw[r["team_abbr"]].append((r["attempts"], r["avg_time_to_throw"]))
    got = {
        r["entity_id"]: r
        for r in frame.filter(pl.col("stat") == "time_to_throw")
        .filter(pl.col("entity_type") == "team")
        .iter_rows(named=True)
    }
    for t, xs in tw.items():
        assert got[t]["value"] == pytest.approx(sum(a * x for a, x in xs) / sum(a for a, _ in xs))
        assert got[t]["n"] == sum(a for a, _ in xs)


def test_off_16_run_blocking_by_side(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    frame = raw(ctx, "OFF-16")
    k = OP.off_16_k.value
    stuff = OP.off_16_stuff_max_yards.value

    def side(r):  # type: ignore[no-untyped-def]
        return r["run_location"] if r["run_location"] in ("left", "right") else None

    us = o.units(rows, "posteam", o.designed_run, side, lambda r: r["success"])
    ux = o.units(
        rows, "posteam", o.designed_run, side, lambda r: 1.0 if r["yards_gained"] <= stuff else 0.0
    )
    mn = OP.off_16_min_carries_per_side.value
    check_raw(
        frame, "success", o.aggregate(us, H), o.league(us), teams, ["left", "right"], lambda c: mn
    )
    check_raw(
        frame, "stuff", o.aggregate(ux, H), o.league(ux), teams, ["left", "right"], lambda c: mn
    )
    agg2, lg2 = off02(rows)
    par = {t: o.shrink(agg2.get((t, "run")), lg2["run"], OP.off_02_k.value) for t in teams}
    agg = o.aggregate(us, H)
    want = {(t, c): o.shrink(agg.get((t, c)), par[t], k) for t in teams for c in ("left", "right")}
    prior = {(t, c): par[t] for t in teams for c in ("left", "right")}
    check_shrunk(shrunk(ctx, "OFF-16", "success"), want, prior, lambda c: k)
    with pytest.raises(NotImplementedError, match="OFF-16"):
        shrunk(ctx, "OFF-16", "stuff")


def test_off_17_ol_continuity(ctx, main_snap, teams) -> None:  # type: ignore[no-untyped-def]
    """Starters = 5 OL with most offensive snaps in the team's last 3 games; continuity = share
    of the team's games in which all 5 played >= 50% (plan A8)."""
    season = main_snap.season
    snaps = main_snap.collect("snap_counts").filter(pl.col("season") == season).to_dicts()
    xw = dict(main_snap.collect("players").select("pfr_id", "gsis_id").iter_rows())
    n_ol = int(OP.off_17_starting_ol_count.value)
    look = int(OP.off_17_starter_lookback_games.value)
    min_pct = OP.off_17_continuity_min_snap_share.value
    frame = raw(ctx, "OFF-17")
    cont = {
        r["entity_id"]: r
        for r in frame.filter(pl.col("stat") == "continuity").iter_rows(named=True)
    }
    starters = frame.filter(pl.col("stat") == "starter")
    inj = main_snap.collect("injuries").filter(
        (pl.col("season") == season) & (pl.col("week") == main_snap.week)
    )
    status = {(r["team"], r["gsis_id"]): r["report_status"] for r in inj.to_dicts()}
    for t in teams:
        mine = [r for r in snaps if r["team"] == t]
        weeks = sorted({r["week"] for r in mine}, reverse=True)
        last = set(weeks[:look])
        tot: dict[str, float] = defaultdict(float)
        for r in mine:
            if r["week"] in last and r["position"] in ("T", "G", "C"):
                tot[r["pfr_player_id"]] += r["offense_snaps"] or 0
        top = sorted(tot, key=lambda p: (-tot[p], p))[:n_ol]
        full = 0
        for w in weeks:
            pct = {r["pfr_player_id"]: r["offense_pct"] or 0 for r in mine if r["week"] == w}
            full += all(pct.get(p, 0) >= min_pct for p in top)
        assert cont[t]["value"] == pytest.approx(full / len(weeks)), t
        assert cont[t]["n"] == len(weeks)
        got = starters.filter(pl.col("team") == t).sort("entity_id")
        want_ids = sorted(xw.get(p, f"pfr:{p}") for p in top)
        assert got["entity_id"].to_list() == want_ids, t
        for r in got.iter_rows(named=True):
            key = (t, r["entity_id"])
            want = (status[key] or "no game status") if key in status else "not on report"
            assert r["note"] == want, (t, r)
