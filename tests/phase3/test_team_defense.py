"""Golden tests, spec section 3 (DEF-01 to DEF-08), on the fixture's 2024 week-8 snapshot.
Directions stay in the offense's frame (spec section 3)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import polars as pl
import pytest

from ge.metrics.registry import raw, shrunk
from tests.phase3 import oracle as o
from tests.phase3.golden import check_raw, check_shrunk
from tests.phase3.test_team_offense import RUN_CELLS, SPLITS, _full, _run_stat

H = o.v(o.C.g3_efficiency_half_life_games)
DP = o.P.defense


def _split_units(rows, x):  # type: ignore[no-untyped-def]
    out = []
    for name, keep in SPLITS.items():
        out += o.units(
            rows, "defteam", lambda r, k=keep: o.qualifying(r) and k(r), lambda r, n=name: n, x
        )
    return out


DEF01_K = {
    "all": DP.def_01_k_overall.value,
    "pass": DP.def_01_k_pass.value,
    "run": DP.def_01_k_run.value,
}


def def01(rows):  # type: ignore[no-untyped-def]
    u = _split_units(rows, lambda r: r["epa"])
    return o.aggregate(u, H), o.league(u)


def def02(rows):  # type: ignore[no-untyped-def]
    u = _split_units(rows, lambda r: r["success"])
    return o.aggregate(u, H), o.league(u)


def test_def_01_epa_allowed(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    agg, lg = def01(rows)
    check_raw(
        raw(ctx, "DEF-01"), "epa", agg, lg, teams, SPLITS, lambda c: DP.def_01_min_plays.value
    )
    want, prior = _full(teams, SPLITS, agg, lg, lambda c: DEF01_K[c])
    check_shrunk(shrunk(ctx, "DEF-01", "epa"), want, prior, lambda c: DEF01_K[c])


def test_def_01_opponent_adjustment_waits_for_bt02(ctx) -> None:  # type: ignore[no-untyped-def]
    from ge.metrics import defense

    with pytest.raises(NotImplementedError, match="G6"):
        defense.def_01_adjusted(ctx)


def test_def_02_success_allowed(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    agg, lg = def02(rows)
    k = DP.def_02_k.value
    check_raw(
        raw(ctx, "DEF-02"), "success", agg, lg, teams, SPLITS, lambda c: DP.def_02_min_plays.value
    )
    want, prior = _full(teams, SPLITS, agg, lg, lambda c: k)
    check_shrunk(shrunk(ctx, "DEF-02", "success"), want, prior, lambda c: k)


def test_def_03_directional_run_defense(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    frame = raw(ctx, "DEF-03")
    for stat in ("carries", "ypc", "epa", "success", "explosive"):
        u = o.units(rows, "defteam", o.designed_run, o.run_cell, _run_stat(stat))
        check_raw(
            frame,
            stat,
            o.aggregate(u, H),
            o.league(u),
            teams,
            RUN_CELLS,
            lambda c: DP.def_03_min_carries_per_cell.value,
        )
    car = frame.filter((pl.col("stat") == "carries") & (pl.col("entity_type") == "team"))
    per_team = dict(car.group_by("entity_id").agg(pl.col("n").sum()).iter_rows())
    for t in teams:
        assert per_team[t] == sum(1 for r in rows if o.designed_run(r) and r["defteam"] == t)
    agg1, lg1 = def01(rows)
    agg2, lg2 = def02(rows)
    parents = {
        "epa": (
            {t: o.shrink(agg1.get((t, "run")), lg1["run"], DP.def_01_k_run.value) for t in teams},
            DP.def_03_k_epa_ypc.value,
        ),
        "success": (
            {t: o.shrink(agg2.get((t, "run")), lg2["run"], DP.def_02_k.value) for t in teams},
            DP.def_03_k_success.value,
        ),
    }
    for stat, (par, k) in parents.items():
        u = o.units(rows, "defteam", o.designed_run, o.run_cell, _run_stat(stat))
        agg = o.aggregate(u, H)
        want = {(t, c): o.shrink(agg.get((t, c)), par[t], k) for t in teams for c in RUN_CELLS}
        prior = {(t, c): par[t] for t in teams for c in RUN_CELLS}
        check_shrunk(shrunk(ctx, "DEF-03", stat), want, prior, lambda c, k=k: k)
    for stat in ("ypc", "explosive"):
        with pytest.raises(NotImplementedError, match="DEF-03"):
            shrunk(ctx, "DEF-03", stat)


def _positions(snap) -> dict[str, str]:  # type: ignore[no-untyped-def]
    """Each player's position on his latest visible weekly roster row this season; a tie on
    week goes to the larger position string."""
    rw = snap.collect("rosters_weekly").filter(pl.col("season") == snap.season)
    best: dict[str, tuple[int, str]] = {}
    for r in rw.select("gsis_id", "week", "position").to_dicts():
        if r["gsis_id"] is None:
            continue
        cand = (r["week"], r["position"] or "")
        if r["gsis_id"] not in best or cand > best[r["gsis_id"]]:
            best[r["gsis_id"]] = cand
    return {g: p for g, (_, p) in best.items()}


DEF04_STATS = {
    "targets": lambda r: 1.0,
    "receptions": lambda r: float(r["complete_pass"]),
    "yards": lambda r: float(r["yards_gained"]),
    "tds": lambda r: 1.0 if r["touchdown"] == 1 and r["td_team"] == r["posteam"] else 0.0,
    "epa": lambda r: float(r["epa"]),
}


def test_def_04_defense_vs_position(ctx, rows, teams, main_snap) -> None:  # type: ignore[no-untyped-def]
    """Ratio = sum actual / sum expected over the defense's games, expected = the opponent's
    per-game total to that position in its other games (A9); EPA as a per-target difference
    vs expected (user decision 2026-10-02)."""
    pos = _positions(main_snap)
    ga = o.games_ago(rows)
    opp_of: dict[tuple[str, str], str] = {}
    for r in rows:
        opp_of[(r["game_id"], r["home_team"])] = r["away_team"]
        opp_of[(r["game_id"], r["away_team"])] = r["home_team"]
    tot: dict[tuple[str, str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in rows:
        p = pos.get(r["receiver_player_id"]) if o.target(r) else None
        if p in ("RB", "TE", "WR"):
            for s, f in DEF04_STATS.items():
                tot[(r["posteam"], r["game_id"], p)][s] += f(r)
    k = DP.def_04_k_targets.value
    frame = raw(ctx, "DEF-04")
    got = {(r["entity_id"], r["cell"], r["stat"]): r for r in frame.iter_rows(named=True)}
    sh = {
        s: {(r["entity_id"], r["cell"]): r for r in shrunk(ctx, "DEF-04", s).iter_rows(named=True)}
        for s in ("targets", "receptions", "yards", "tds", "epa_diff")
    }
    checked = 0
    for d in teams:
        for p in ("RB", "TE", "WR"):
            act: dict[str, float] = defaultdict(float)
            exp: dict[str, float] = defaultdict(float)
            actw: dict[str, float] = defaultdict(float)
            expw: dict[str, float] = defaultdict(float)
            wts: list[float] = []
            games = 0
            for gid, g in ga[d].items():
                opp = opp_of[(gid, d)]
                others = [x for x in ga[opp] if opp_of[(x, opp)] != d]
                if not others:
                    continue
                games += 1
                w = 0.5 ** (g / H)
                a = tot.get((opp, gid, p), {})
                for s in DEF04_STATS:
                    e = sum(tot.get((opp, x, p), {}).get(s, 0.0) for x in others) / len(others)
                    act[s] += a.get(s, 0.0)
                    exp[s] += e
                    actw[s] += w * a.get(s, 0.0)
                    expw[s] += w * e
                wts += [w] * int(a.get("targets", 0))
            n = int(act["targets"])
            neff = (sum(wts) ** 2 / sum(x * x for x in wts)) if wts else 0.0
            for s in ("targets", "receptions", "yards", "tds"):
                r = got[(d, p, s)]
                assert r["n"] == n and r["n_eff"] == pytest.approx(neff, rel=1e-12)
                val = act[s] / exp[s] if exp[s] else None
                vw = actw[s] / expw[s] if expw[s] else None
                assert r["value"] == (None if val is None else pytest.approx(val, rel=1e-12))
                assert r["value_w"] == (None if vw is None else pytest.approx(vw, rel=1e-12))
                below = games < DP.def_04_min_games.value or n < DP.def_04_min_targets.value
                assert r["below_min_sample"] == below
                prior = DP.def_04_prior_ratio.value
                want = prior if vw is None or n == 0 else (neff * vw + k * prior) / (neff + k)
                assert sh[s][(d, p)]["shrunk"] == pytest.approx(want, rel=1e-12)
                checked += 1
            r = got[(d, p, "epa_diff")]
            if act["targets"] and exp["targets"]:
                diff = act["epa"] / act["targets"] - exp["epa"] / exp["targets"]
                dw = actw["epa"] / actw["targets"] - expw["epa"] / expw["targets"]
                assert r["value"] == pytest.approx(diff, rel=1e-12, abs=1e-12)
                assert r["value_w"] == pytest.approx(dw, rel=1e-12, abs=1e-12)
                want = (neff * dw) / (neff + k)
                assert sh["epa_diff"][(d, p)]["shrunk"] == pytest.approx(want, rel=1e-12, abs=1e-12)
            else:
                assert r["value"] is None
    assert checked == len(teams) * 3 * 4


def test_paid_defense_metrics_refuse(ctx) -> None:  # type: ignore[no-untyped-def]
    for sid in ("DEF-04b", "DEF-05b"):
        with pytest.raises(NotImplementedError, match="PAID: DATA-11"):
            raw(ctx, sid)


def test_def_05_pass_rush_and_blitz(ctx, rows, ftn, teams) -> None:  # type: ignore[no-untyped-def]
    frame = raw(ctx, "DEF-05")
    k = DP.def_05_k.value
    blitz = DP.def_05_blitz_min_blitzers.value

    def f(field: str, fn: Any):  # type: ignore[no-untyped-def]
        def x(r):  # type: ignore[no-untyped-def]
            row = ftn.get((r["game_id"], int(r["play_id"])))
            return None if row is None or row[field] is None else fn(row[field])

        return x

    stats = {
        "blitz_rate": f("n_blitzers", lambda n: 1.0 if n >= blitz else 0.0),
        "rushers": f("n_pass_rushers", float),
        "box": f("n_defense_box", float),
        "sack_rate": lambda r: r["sack"],
        "hit_rate": lambda r: 1.0 if r["sack"] == 1 or r["qb_hit"] == 1 else 0.0,
    }
    for stat, x in stats.items():
        u = o.units(rows, "defteam", o.dropback, lambda r: "all", x)
        agg, lg = o.aggregate(u, H), o.league(u)
        check_raw(frame, stat, agg, lg, teams, ["all"], lambda c: DP.def_05_min_dropbacks.value)
        want, prior = _full(teams, ["all"], agg, lg, lambda c: k)
        check_shrunk(shrunk(ctx, "DEF-05", stat), want, prior, lambda c: k)


def test_def_06_explosives_allowed(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    frame = raw(ctx, "DEF-06")
    k = DP.def_06_k.value
    run_y, pass_y = (
        DP.def_06_explosive_run_min_yards.value,
        DP.def_06_explosive_pass_min_yards.value,
    )

    def run_x(r):  # type: ignore[no-untyped-def]
        return 1.0 if r["yards_gained"] >= run_y else 0.0

    def pass_x(r):  # type: ignore[no-untyped-def]
        return 1.0 if r["complete_pass"] == 1 and r["yards_gained"] >= pass_y else 0.0

    def any_x(r):  # type: ignore[no-untyped-def]
        return run_x(r) if o.designed_run(r) else pass_x(r)

    for stat, keep, x in (
        ("explosive", o.qualifying, any_x),
        ("explosive_run", o.designed_run, run_x),
        ("explosive_pass", o.dropback, pass_x),
    ):
        u = o.units(rows, "defteam", keep, lambda r: "all", x)
        agg, lg = o.aggregate(u, H), o.league(u)
        check_raw(frame, stat, agg, lg, teams, ["all"], lambda c: DP.def_06_min_plays.value)
        want, prior = _full(teams, ["all"], agg, lg, lambda c: k)
        check_shrunk(shrunk(ctx, "DEF-06", stat), want, prior, lambda c: k)


def test_def_07_red_zone_td_rate_allowed(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    z = DP.def_07_red_zone_yardline_100.value
    u = o.zone_trips(rows, "defteam", z)
    agg, lg = o.aggregate(u, H), o.league(u)
    cell = f"inside_{int(z)}"
    k = DP.def_07_k_trips.value
    check_raw(
        raw(ctx, "DEF-07"),
        "td_per_trip",
        agg,
        lg,
        teams,
        [cell],
        lambda c: DP.def_07_min_trips.value,
    )
    want, prior = _full(teams, [cell], agg, lg, lambda c: k)
    check_shrunk(shrunk(ctx, "DEF-07", "td_per_trip"), want, prior, lambda c: k)


def test_def_08_missing_defenders(ctx, rows, teams, main_snap) -> None:  # type: ignore[no-untyped-def]
    season = main_snap.season
    snaps = main_snap.collect("snap_counts").filter(pl.col("season") == season).to_dicts()
    xw = dict(main_snap.collect("players").select("pfr_id", "gsis_id").iter_rows())
    inj = main_snap.collect("injuries").filter(
        (pl.col("season") == season) & (pl.col("week") == main_snap.week)
    )
    status = {(r["team"], r["gsis_id"]): r["report_status"] for r in inj.to_dicts()}
    look = int(DP.def_08_starter_lookback_games.value)
    min_share = DP.def_08_starter_min_snap_share.value
    frame = raw(ctx, "DEF-08")
    starters = {
        (r["team"], r["entity_id"]): r
        for r in frame.filter(pl.col("stat") == "starter").iter_rows(named=True)
    }
    onoff = {
        (r["team"], r["entity_id"]): r
        for r in frame.filter(pl.col("stat") == "on_off").iter_rows(named=True)
    }
    ga = o.games_ago(rows)
    want_starters = set()
    for t in teams:
        mine = [r for r in snaps if r["team"] == t]
        weeks = sorted({r["week"] for r in mine}, reverse=True)[:look]
        team_snaps = 0.0
        player: dict[str, float] = defaultdict(float)
        for w in weeks:
            wk = [r for r in mine if r["week"] == w]
            team_snaps += max(r["defense_snaps"] / r["defense_pct"] for r in wk if r["defense_pct"])
            for r in wk:
                player[r["pfr_player_id"]] += r["defense_snaps"] or 0
        for pfr, s in player.items():
            if s / team_snaps >= min_share:
                gid = xw.get(pfr, f"pfr:{pfr}")
                want_starters.add((t, gid))
                r = starters[(t, gid)]
                assert r["value"] == pytest.approx(s / team_snaps, rel=1e-12)
                key = (t, gid)
                st = (status[key] or "no game status") if key in status else "not on report"
                assert r["note"] == st
                if st in ("Out", "Doubtful"):
                    played = {
                        x["game_id"]
                        for x in mine
                        if x["pfr_player_id"] == pfr and (x["defense_snaps"] or 0) > 0
                    }
                    with_, without = [], []
                    for p in rows:
                        if o.qualifying(p) and p["defteam"] == t:
                            g = ga[t][p["game_id"]]
                            (with_ if p["game_id"] in played else without).append((g, p["epa"]))
                    a = onoff[key]
                    assert a["n"] == min(len(with_), len(without))
                    if with_ and without:
                        m = lambda xs: sum(x for _, x in xs) / len(xs)  # noqa: E731
                        assert a["value"] == pytest.approx(m(without) - m(with_), rel=1e-12)
                    else:
                        assert a["value"] is None
                    below = min(len(with_), len(without)) < DP.def_08_min_plays_each_way.value
                    assert a["below_min_sample"] == below
                else:
                    assert key not in onoff
    assert set(starters) == want_starters
    eligible = shrunk(ctx, "DEF-08", "on_off")
    for r in eligible.iter_rows(named=True):
        a = onoff[(r["team"], r["entity_id"])]
        assert not a["below_min_sample"]
        k = DP.def_08_k.value
        assert r["shrunk"] == pytest.approx(a["n_eff"] * a["value_w"] / (a["n_eff"] + k))
    assert eligible.height == sum(1 for a in onoff.values() if not a["below_min_sample"])
