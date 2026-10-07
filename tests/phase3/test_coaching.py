"""Golden tests, spec section 5 (COA-01 to COA-07), on the fixture's 2024 week-8 snapshot.

3d rulings (2026-10-05): a mid-season play-caller change drops the pre-change plays from
OFF-04 to OFF-10 and shrinks toward the new caller's prior (league average, or his last
team's end-of-season shrunk value when COA-01 shows his history); until COA-01 has rows a
head-coach change in the schedules data stands in. COA-03 drops garbage-time TDs and their
tries. COA-07's time-zone change is UTC-offset hours from the previous game's stadium (home
stadium after a bye). Registry rows here are synthetic placeholders, not real coaches."""

from __future__ import annotations

import datetime as dt
import math
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import polars as pl
import pytest
import yaml

from ge.config import REPO_ROOT, load_ingest
from ge.metrics.coaching import load_registry
from ge.metrics.context import build_context
from ge.metrics.registry import raw, shrunk
from ge.store.snapshot import snapshot
from tests.phase3 import oracle as o
from tests.phase3.conftest import MAIN_WEEK, STORE, first_game
from tests.phase3.golden import check_raw, check_shrunk
from tests.phase3.registry_rows import staff, write

H = o.v(o.C.g3_efficiency_half_life_games)
CP = o.P.coaching
OP = o.P.offense


def _registry(path: Path, rows: list[dict[str, str]]) -> Path:
    return write(path, rows)


def _row(team: str, caller: str, since: str) -> list[dict[str, str]]:
    """Synthetic placeholder rows (one per role) for a team from `since`."""
    return staff(team, since, caller=caller)


def _rows(*groups: list[dict[str, str]]) -> list[dict[str, str]]:
    return [r for g in groups for r in g]


def _off04_units(rows: list[dict[str, Any]]) -> list[tuple[str, str, int, float]]:
    return o.units(
        rows,
        "posteam",
        lambda r: o.qualifying(r) and o.neutral(r) and r["down"] in (1, 2),
        lambda r: "all",
        lambda r: r["pass"],
    )


# ---- COA-01 ----


def test_coa_01_registry_rows_and_head_coach_check(main_snap, teams, tmp_path) -> None:  # type: ignore[no-untyped-def]
    reg = load_registry(
        _registry(
            tmp_path / "r.csv", _rows(*(_row(t, f"TEST-OPC-{t}", "2022-01-01") for t in teams))
        )
    )
    frame = raw(build_context(main_snap, registry=reg), "COA-01")
    got = {(r["entity_id"], r["stat"]): r for r in frame.iter_rows(named=True)}
    for t in teams:
        assert f"TEST-OPC-{t}" in got[(t, "registry")]["note"]
        # synthetic head coaches never match the schedules data's real ones
        assert got[(t, "hc_matches_schedules")]["value"] == 0.0
        assert got[(t, "play_caller_reset")]["value"] == 0.0
    empty = raw(build_context(main_snap), "COA-01")  # the repo registry: no rows yet
    notes = empty.filter(pl.col("stat") == "registry")["note"].to_list()
    assert len(notes) == len(teams) and set(notes) == {"no COA-01 row covering as_of"}


# ---- mid-season play-caller reset (OFF-04 to OFF-10) ----


def _reset_team(main_snap) -> str:  # type: ignore[no-untyped-def]
    """First team alphabetically that isn't in the target game: a rule, not a pick."""
    tg = main_snap.collect("target_game").row(0, named=True)
    s = main_snap.collect("schedules").filter(pl.col("season") == main_snap.season)
    teams = sorted(set(s["home_team"].to_list()) - {tg["home_team"], tg["away_team"]})
    return teams[0]


def test_head_coach_change_resets_off_04_to_10(main_snap, rows, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Until COA-01 has rows, a mid-season head-coach change in the schedules data stands in.
    In a store copy, give one team a new (placeholder) head coach for its last two games."""
    team = _reset_team(main_snap)
    ga = o.games_ago(rows)
    new_games = {g for g, i in ga[team].items() if i < 2}
    dst = tmp_path / "store"
    shutil.copytree(STORE, dst)
    (part,) = (dst / "schedules" / f"season={main_snap.season}").glob("*/part.parquet")
    s = pl.read_parquet(part)
    s.with_columns(
        pl.when(pl.col("game_id").is_in(list(new_games)) & (pl.col("home_team") == team))
        .then(pl.lit("TEST-NEW-HC"))
        .otherwise(pl.col("home_coach"))
        .alias("home_coach"),
        pl.when(pl.col("game_id").is_in(list(new_games)) & (pl.col("away_team") == team))
        .then(pl.lit("TEST-NEW-HC"))
        .otherwise(pl.col("away_coach"))
        .alias("away_coach"),
    ).write_parquet(part)
    base = build_context(main_snap)
    moved = build_context(snapshot(main_snap.game_id, as_of=main_snap.as_of, root=dst))
    u = [x for x in _off04_units(rows) if x[0] != team or x[2] < 2]
    agg = o.aggregate(u, H)
    lg = o.league(_off04_units(rows))["all"]  # the league average keeps every play
    a = raw(base, "OFF-04")
    b = raw(moved, "OFF-04")
    r = b.filter(pl.col("entity_id") == team).row(0, named=True)
    assert r["n"] == agg[(team, "all")].n
    assert r["value_w"] == pytest.approx(agg[(team, "all")].value_w, rel=1e-12)
    assert "play-caller reset" in r["note"] and "head coach" in r["note"]
    others = [df.filter(pl.col("entity_id") != team).sort("entity_id", "cell") for df in (a, b)]
    assert others[0].equals(others[1])  # other teams and the league row unchanged
    s_ = shrunk(moved, "OFF-04", "pass_rate").filter(pl.col("entity_id") == team).row(0, named=True)
    k = OP.off_04_k.value
    assert s_["prior"] == pytest.approx(lg, rel=1e-12)
    assert s_["shrunk"] == pytest.approx(o.shrink(agg[(team, "all")], lg, k), rel=1e-12)
    # OFF-11 is outside OFF-04..OFF-10: untouched
    assert raw(base, "OFF-11").equals(raw(moved, "OFF-11"))


def test_registry_change_resets_with_caller_history(main_snap, rows, teams, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """With COA-01 rows: team T's caller changes after its 5th game to one who called plays
    for team U at the end of last season, so T's prior is U's end-of-last-season shrunk
    OFF-04."""
    team = _reset_team(main_snap)
    other = next(t for t in teams if t != team)
    sched = main_snap.collect("schedules").filter(pl.col("season") == main_snap.season)
    mine = sched.filter((pl.col("home_team") == team) | (pl.col("away_team") == team)).sort(
        "gameday"
    )
    days = mine["gameday"].to_list()
    change = (dt.date.fromisoformat(days[4]) + dt.timedelta(days=1)).isoformat()
    rows_ = _rows(
        *(_row(t, f"TEST-OPC-{t}", "2022-01-01") for t in teams if t not in (team, other)),
        _row(team, f"TEST-OPC-{team}", "2022-01-01"),
        _row(team, "TEST-OPC-MOVER", change),
        _row(other, "TEST-OPC-MOVER", "2022-01-01"),
        _row(other, f"TEST-OPC-{other}", f"{main_snap.season}-02-01"),
    )
    ctx = build_context(main_snap, registry=load_registry(_registry(tmp_path / "r.csv", rows_)))
    ga = o.games_ago(rows)
    # the oldest game under the new caller: the largest games-ago among games after the change
    first_new = max(
        ga[team][g]
        for g in mine.filter(pl.col("gameday") > change)["game_id"].to_list()
        if g in ga[team]
    )
    u = [x for x in _off04_units(rows) if x[0] != team or x[2] <= first_new]
    agg = o.aggregate(u, H)
    last = main_snap.collect("pbp").filter(pl.col("season") == main_snap.season - 1).to_dicts()
    ul = _off04_units(last)
    hist = o.shrink(o.aggregate(ul, H).get((other, "all")), o.league(ul)["all"], OP.off_04_k.value)
    r = raw(ctx, "OFF-04").filter(pl.col("entity_id") == team).row(0, named=True)
    assert r["n"] == agg[(team, "all")].n and "registry" in r["note"]
    s_ = shrunk(ctx, "OFF-04", "pass_rate").filter(pl.col("entity_id") == team).row(0, named=True)
    assert s_["prior"] == pytest.approx(hist, rel=1e-12)
    assert "his last team" in s_["note"]
    k = OP.off_04_k.value
    assert s_["shrunk"] == pytest.approx(o.shrink(agg[(team, "all")], hist, k), rel=1e-12)


# ---- COA-02 to COA-05 ----


def test_coa_02_fourth_down_go_rate(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    def keep(r: dict[str, Any]) -> bool:
        return (
            r["down"] == 4
            and r["play_type"] in ("pass", "run", "punt", "field_goal")
            and not o.garbage(r)
            and r["posteam"] is not None
        )

    u = o.units(
        rows,
        "posteam",
        keep,
        lambda r: "all",
        lambda r: 1.0 if r["play_type"] in ("pass", "run") else 0.0,
    )
    check_raw(
        raw(ctx, "COA-02"),
        "go_rate",
        o.aggregate(u, H),
        o.league(u),
        teams,
        ["all"],
        lambda c: CP.coa_02_min_fourth_downs.value,
    )
    with pytest.raises(NotImplementedError, match="COA-02"):
        shrunk(ctx, "COA-02", "go_over_expected")


def test_coa_03_two_point_rate(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    ga = o.games_ago(rows)
    seq = sorted(rows, key=lambda r: (r["game_id"], r["play_id"]))
    tds: dict[tuple[str, str], float] = defaultdict(float)
    tries: dict[tuple[str, str], float] = defaultdict(float)
    last_td: dict[str, dict[str, Any]] = {}
    for r in seq:
        if r["touchdown"] == 1 and r["td_team"] is not None:
            last_td[r["game_id"]] = r
            if not o.garbage(r):
                tds[(r["td_team"], r["game_id"])] += 1
        if r["two_point_attempt"] == 1 and r["posteam"] is not None:
            td = last_td.get(r["game_id"])
            if td is not None and not o.garbage(td):
                tries[(r["posteam"], r["game_id"])] += 1
    got = {
        x["entity_id"]: x
        for x in raw(ctx, "COA-03")
        .filter((pl.col("stat") == "two_point_rate") & (pl.col("entity_type") == "team"))
        .iter_rows(named=True)
    }
    keys = set(tds) | set(tries)
    for t in teams:
        gs = [g for (tm, g) in keys if tm == t]
        d = sum(tds.get((t, g), 0.0) for g in gs)
        assert got[t]["n"] == round(d), t
        if d:
            assert got[t]["value"] == pytest.approx(sum(tries.get((t, g), 0.0) for g in gs) / d)
            ws = {g: 0.5 ** (ga[t][g] / H) for g in gs}
            vw = sum(ws[g] * tries.get((t, g), 0.0) for g in gs) / sum(
                ws[g] * tds.get((t, g), 0.0) for g in gs
            )
            assert got[t]["value_w"] == pytest.approx(vw, rel=1e-12)
        assert got[t]["below_min_sample"] == (d < CP.coa_03_min_tds.value)
    s = shrunk(ctx, "COA-03", "two_point_rate")
    assert s.height == len(teams) and s["k"].unique().to_list() == [CP.coa_03_k.value]


def _bucket(r: dict[str, Any]) -> str | None:
    wp = r["wp"]
    if wp is None or o.garbage(r):
        return None
    if wp > CP.coa_04_leading_min_wp.value:
        return "leading"
    if wp < CP.coa_04_trailing_max_wp.value:
        return "trailing"
    return None


def test_coa_04_script_response(ctx, rows, teams) -> None:  # type: ignore[no-untyped-def]
    frame = raw(ctx, "COA-04")
    k = CP.coa_04_k.value
    mn = CP.coa_04_min_plays_per_bucket.value
    cells = ["leading", "trailing"]
    up = o.units(
        rows,
        "posteam",
        lambda r: o.qualifying(r) and r["xpass"] is not None and _bucket(r) is not None,
        _bucket,
        lambda r: r["pass"] - r["xpass"],
    )
    ut = o.pace_pairs(
        rows, prior_ok=lambda r: _bucket(r) is not None, cell=lambda r: _bucket(r) or "none"
    )
    for stat, u in (("proe", up), ("seconds_per_play", ut)):
        agg, lg = o.aggregate(u, H), o.league(u)
        check_raw(frame, stat, agg, lg, teams, cells, lambda c: mn)
        want = {(t, c): o.shrink(agg.get((t, c)), lg[c], k) for t in teams for c in cells}
        check_shrunk(
            shrunk(ctx, "COA-04", stat),
            want,
            {(t, c): lg[c] for t in teams for c in cells},
            lambda c: k,
        )


def test_coa_05_scheme_tendency_percentiles(ctx, teams) -> None:  # type: ignore[no-untyped-def]
    """Outside-run share (end + tackle cells of OFF-12, raw: OFF-12 has no shrunk share),
    under-center rate (1 - shrunk OFF-09), play-action and motion rates (shrunk OFF-06/07),
    each as a percentile among the teams: (below + half the ties) / teams."""
    car = raw(ctx, "OFF-12").filter(
        (pl.col("stat") == "carries") & (pl.col("entity_type") == "team")
    )
    out_cells = ["left_end", "left_tackle", "right_tackle", "right_end"]
    vals: dict[str, dict[str, float]] = defaultdict(dict)
    for t in teams:
        mine = car.filter(pl.col("entity_id") == t)
        tot = mine["n"].sum()
        vals["outside_run_share"][t] = mine.filter(pl.col("cell").is_in(out_cells))["n"].sum() / tot
    for stat, sid, s, flip in (
        ("under_center_rate", "OFF-09", "shotgun_rate", True),
        ("play_action_rate", "OFF-06", "play_action_rate", False),
        ("motion_rate", "OFF-07", "motion_rate", False),
    ):
        for r in shrunk(ctx, sid, s).iter_rows(named=True):
            vals[stat][r["entity_id"]] = 1 - r["shrunk"] if flip else r["shrunk"]
    frame = raw(ctx, "COA-05")
    got = {(r["entity_id"], r["stat"]): r["value"] for r in frame.iter_rows(named=True)}
    for stat, by in vals.items():
        xs = list(by.values())
        for t, x in by.items():
            assert got[(t, stat)] == pytest.approx(x, rel=1e-12)
            pct = (sum(v < x for v in xs) + 0.5 * sum(v == x for v in xs)) / len(xs)
            assert got[(t, f"{stat}_pctl")] == pytest.approx(pct, rel=1e-12)


def test_coa_05b_is_paid(ctx) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(NotImplementedError, match="PAID: DATA-11"):
        raw(ctx, "COA-05b")


# ---- COA-06, COA-07 ----


def test_coa_06_coordinator_history(main_snap, teams, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Display only: past meetings in the snapshot window between this team's offensive
    play-caller and the opponent's defensive play-caller (and the reverse), EPA per qualifying
    play in those games. Synthetic rows: every caller stayed put since 2022, so the meetings
    are the past games between the two teams."""
    reg = load_registry(
        _registry(
            tmp_path / "r.csv", _rows(*(_row(t, f"TEST-OPC-{t}", "2022-01-01") for t in teams))
        )
    )
    ctx = build_context(main_snap, registry=reg)
    tg = main_snap.collect("target_game").row(0, named=True)
    pbp = main_snap.collect("pbp").to_dicts()
    frame = raw(ctx, "COA-06")
    for off, dfn in ((tg["away_team"], tg["home_team"]), (tg["home_team"], tg["away_team"])):
        plays = [r for r in pbp if r["posteam"] == off and r["defteam"] == dfn and o.qualifying(r)]
        gs = sorted({r["game_id"] for r in plays})
        r = frame.filter((pl.col("entity_id") == off) & (pl.col("stat") == "epa_vs_coordinator"))
        assert r["n"][0] == len(gs)
        if gs:
            assert r["value"][0] == pytest.approx(sum(x["epa"] for x in plays) / len(plays))
        else:
            assert r["value"][0] is None
        assert r["below_min_sample"][0] == (len(gs) < CP.coa_06_min_games.value)
    no_reg = raw(build_context(main_snap), "COA-06")
    assert no_reg["value"].null_count() == no_reg.height
    assert all("COA-01" in n for n in no_reg["note"].to_list())


def _stadiums() -> dict[str, dict[str, Any]]:
    data = yaml.safe_load((REPO_ROOT / "config" / "stadiums.yaml").read_text(encoding="utf-8"))
    return {s["stadium_id"]: s for s in data["stadiums"]}


def test_coa_07_situational_features(ctx, main_snap) -> None:  # type: ignore[no-untyped-def]
    radius = load_ingest().geo.earth_mean_radius_km.value
    st = _stadiums()
    tg = main_snap.collect("target_game").row(0, named=True)
    sched = main_snap.collect("schedules").sort("gameday", "game_id").to_dicts()
    dest = st[tg["stadium_id"]]
    kickoff = dt.datetime.combine(
        dt.date.fromisoformat(tg["gameday"]),
        dt.time.fromisoformat(tg["gametime"]),
        ZoneInfo("America/New_York"),
    )
    got = {(r["entity_id"], r["stat"]): r for r in raw(ctx, "COA-07").iter_rows(named=True)}
    for side in ("home", "away"):
        t = tg[f"{side}_team"]
        mine = [g for g in sched if t in (g["home_team"], g["away_team"])]
        cur = [g for g in mine if g["season"] == main_snap.season]
        bye = not cur or cur[-1]["week"] < tg["week"] - 1
        if bye:
            origin = st[[g for g in mine if g["home_team"] == t][-1]["stadium_id"]]
        else:
            origin = st[cur[-1]["stadium_id"]]
        p1, p2 = math.radians(origin["lat"]), math.radians(dest["lat"])
        dl = math.radians(dest["lon"] - origin["lon"])
        km = radius * math.acos(
            min(1.0, math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl))
        )

        def off(s: dict[str, Any]) -> float:
            return kickoff.astimezone(ZoneInfo(s["timezone"])).utcoffset().total_seconds() / 3600  # type: ignore[union-attr]

        assert got[(t, "rest_days")]["value"] == tg[f"{side}_rest"]
        assert got[(t, "travel_km")]["value"] == pytest.approx(km, rel=1e-9, abs=1e-6)
        assert got[(t, "tz_change_hours")]["value"] == pytest.approx(off(dest) - off(origin))
        assert ("home stadium after a bye" in got[(t, "travel_km")]["note"]) == bye


def test_earth_radius_is_cited() -> None:
    e = load_ingest().geo.earth_mean_radius_km
    assert e.value == 6371.0087714
    assert "wikipedia.org/wiki/Earth_radius" in e.source and "IUGG" in e.source


def test_week_index_is_the_main_snapshot() -> None:
    assert first_game(MAIN_WEEK).startswith("2024_08")
