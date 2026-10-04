"""Golden tests for PLY-14 (injury and practice status) and PLY-15 (opportunity
redistribution), on the fixture's 2024 week-8 snapshot.

PLY-14 (spec synced 2026-10-04): no game designation means expected to play once the team's
final report is in the feed; a team's final report is in when its week rows include an Out,
Doubtful or Questionable (ruling 2026-10-04); while it's missing, its listed players are
"status unknown". Practice base rates come from Phase 3e, so availability raises.

PLY-15 (ruling 2026-10-04): trigger = listed Out; redistributes target and carry shares;
QB = most dropbacks in the game; play-caller from COA-01, else the G4 head-coach stand-in;
career snaps counted within the snapshot window and labelled."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

import polars as pl
import pytest

from ge.metrics import player
from ge.metrics.registry import raw, shrunk
from tests.phase3 import oracle as o
from tests.phase3 import oracle_player as op

PL = op.PL
DESIGNATIONS = ("Out", "Doubtful", "Questionable")


@pytest.fixture(scope="module")
def report(main_snap) -> list[dict[str, Any]]:  # type: ignore[no-untyped-def]
    inj = main_snap.collect("injuries")
    return inj.filter(
        (pl.col("season") == main_snap.season) & (pl.col("week") == main_snap.week)
    ).to_dicts()


def test_ply_14_status_and_final_report(ctx, report) -> None:  # type: ignore[no-untyped-def]
    final = defaultdict(bool)
    for r in report:
        final[r["team"]] |= r["report_status"] in DESIGNATIONS
    frame = raw(ctx, "PLY-14")
    teams = {
        r["entity_id"]: r
        for r in frame.filter(pl.col("stat") == "final_report_in").iter_rows(named=True)
    }
    for t, is_in in final.items():
        assert teams[t]["value"] == (1.0 if is_in else 0.0), t
    status = {
        (r["entity_id"], r["team"]): r
        for r in frame.filter(pl.col("stat") == "game_status").iter_rows(named=True)
    }
    unknown = {
        (r["entity_id"], r["team"]): r["value"]
        for r in frame.filter(pl.col("stat") == "status_unknown").iter_rows(named=True)
    }
    assert len(status) == len({(r["gsis_id"], r["team"]) for r in report})
    n_unknown = 0
    for r in report:
        key = (r["gsis_id"], r["team"])
        if r["report_status"] in DESIGNATIONS:
            want = r["report_status"]
        else:
            want = "expected to play" if final[r["team"]] else "status unknown"
        assert status[key]["note"].startswith(want), (key, status[key]["note"])
        assert unknown[key] == (1.0 if want == "status unknown" else 0.0), key
        n_unknown += want == "status unknown"
    print(
        f"\nPLY-14 week {ctx.week}: {sum(final.values())} teams with a final report, "
        f"{len(final) - sum(final.values())} without; {n_unknown} players status unknown"
    )


def test_ply_14_missing_final_report_flags_listed_players(main_snap, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Historically a week's report counts as known all at once (BT-01), so the fixture never
    has a team without its final report. Recreate the live case from the decisions log: in a
    store copy, blank one team's game statuses for the target week (practice rows stay). Only
    that team's listed players become "status unknown"; everyone else is unchanged."""
    import shutil

    from ge.metrics.context import build_context
    from ge.store.snapshot import snapshot
    from tests.phase3.conftest import STORE

    dst = tmp_path / "store"
    shutil.copytree(STORE, dst)
    (part,) = (dst / "injuries" / f"season={main_snap.season}").glob("*/part.parquet")
    inj = pl.read_parquet(part)
    wk = (pl.col("week") == main_snap.week) & pl.col("report_status").is_in(list(DESIGNATIONS))
    team = sorted(inj.filter(wk)["team"].unique().to_list())[0]  # first team by rule
    blank = (pl.col("week") == main_snap.week) & (pl.col("team") == team)
    inj.with_columns(
        pl.when(blank).then(None).otherwise(pl.col("report_status")).alias("report_status")
    ).write_parquet(part)
    base = build_context(main_snap)
    moved = build_context(snapshot(main_snap.game_id, as_of=main_snap.as_of, root=dst))
    a, b = raw(base, "PLY-14"), raw(moved, "PLY-14")
    fin = {
        r["entity_id"]: r["value"]
        for r in b.filter(pl.col("stat") == "final_report_in").iter_rows(named=True)
    }
    assert fin[team] == 0.0
    unk = b.filter((pl.col("stat") == "status_unknown") & (pl.col("value") == 1.0))
    assert set(unk["team"].to_list()) == {team}
    listed = moved.injuries_now().filter(pl.col("team") == team)
    assert unk.height == listed.select("gsis_id").n_unique() > 0
    notes = b.filter((pl.col("stat") == "game_status") & (pl.col("team") == team))["note"]
    assert all(n.startswith("status unknown") for n in notes.to_list())
    others = [
        df.filter((pl.col("team") != team) & (pl.col("stat") != "return_factor")).sort(
            "team", "entity_id", "stat"
        )
        for df in (a, b)
    ]
    assert others[0].equals(others[1])
    print(f"\nPLY-14 with {team}'s game statuses blanked: {unk.height} players status unknown")


def test_ply_14_availability_waits_for_phase_3e(ctx) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(NotImplementedError, match="PLY-14"):
        player.ply_14_availability(ctx)


def test_ply_14_return_from_injury(ctx, snaps, xw, rows, report, main_snap) -> None:  # type: ignore[no-untyped-def]
    """First game back after missing 2+ games: the return factor (initial 0.85) is attached.
    Missed = the team's visible games after his last game with a snap; only for his latest
    team, and not when he's listed Out or Doubtful. User rule 2026-10-04: only if he appeared
    on that team's injury report (any status) or its weekly roster as reserve (status RES,
    which is where IR shows: the injury feed has no IR status) in a missed week, so released
    players aren't flagged."""
    season = main_snap.season
    inj_weeks = {
        (r["gsis_id"], r["team"], r["week"])
        for r in main_snap.collect("injuries").filter(pl.col("season") == season).to_dicts()
    }
    res_weeks = {
        (r["gsis_id"], r["team"], r["week"])
        for r in main_snap.collect("rosters_weekly")
        .filter((pl.col("season") == season) & (pl.col("status") == "RES"))
        .to_dicts()
    }
    week_of = {(r["posteam"], r["game_id"]): r["week"] for r in rows if r["posteam"]}
    ga = o.games_ago(rows)
    last: dict[str, tuple[int, str]] = {}
    played_g: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in sorted(snaps, key=lambda r: (r["week"], r["team"])):
        tot = (r["offense_snaps"] or 0) + (r["defense_snaps"] or 0) + (r["st_snaps"] or 0)
        if tot > 0:
            pid = xw.get(r["pfr_player_id"], f"pfr:{r['pfr_player_id']}")
            last[pid] = (r["week"], r["team"])
            played_g[(pid, r["team"])].append(ga[r["team"]][r["game_id"]])
    out = {(r["gsis_id"], r["team"]) for r in report if r["report_status"] in ("Out", "Doubtful")}
    need = op.v(PL.ply_14_return_min_missed_games)
    want = {}
    dropped = 0
    for pid, (_, team) in last.items():
        missed = int(min(played_g[(pid, team)]))  # games since his last one = its games-ago
        if missed < need or (pid, team) in out:
            continue
        weeks = {week_of[(team, g)] for g, i in ga[team].items() if i < missed}
        listed = any((pid, team, w) in inj_weeks or (pid, team, w) in res_weeks for w in weeks)
        if listed:
            want[(pid, team)] = missed
        else:
            dropped += 1
    print(f"\nPLY-14 return flag: {len(want)} players, {dropped} not listed while out (dropped)")
    assert dropped > 0, "fixture should contain an unlisted absence (e.g. a released player)"
    frame = raw(ctx, "PLY-14").filter(pl.col("stat") == "return_factor")
    got = {(r["entity_id"], r["team"]): r for r in frame.iter_rows(named=True)}
    assert set(got) == set(want)
    for key, missed in want.items():
        assert got[key]["value"] == op.v(PL.ply_14_return_factor)
        assert got[key]["n"] == missed
    assert want, "fixture should contain a player returning after 2+ missed games"


def _qb_by_game(rows: list[dict[str, Any]]) -> dict[tuple[str, str], str]:
    c: Counter[tuple[str, str, str]] = Counter()
    for r in rows:
        if r["qb_dropback"] == 1 and o.scrimmage(r) and (q := op.dropback_qb(r)) is not None:
            c[(r["posteam"], r["game_id"], q)] += 1
    best: dict[tuple[str, str], tuple[int, str]] = {}
    for (t, g, q), n in c.items():
        if (t, g) not in best or (n, q) > best[(t, g)]:
            best[(t, g)] = (n, q)
    return {k: q for k, (_, q) in best.items()}


def _coach_by_game(main_snap) -> dict[tuple[str, str], str]:  # type: ignore[no-untyped-def]
    s = main_snap.collect("schedules").filter(pl.col("season") == main_snap.season)
    out = {}
    for r in s.to_dicts():
        out[(r["home_team"], r["game_id"])] = r["home_coach"]
        out[(r["away_team"], r["game_id"])] = r["away_coach"]
    return out


def _positions(main_snap) -> dict[str, str]:  # type: ignore[no-untyped-def]
    rw = main_snap.collect("rosters_weekly").filter(pl.col("season") == main_snap.season)
    best: dict[str, tuple[int, str]] = {}
    for r in rw.select("gsis_id", "week", "position").to_dicts():
        if r["gsis_id"] is not None:
            cand = (r["week"], r["position"] or "")
            if r["gsis_id"] not in best or cand > best[r["gsis_id"]]:
                best[r["gsis_id"]] = cand
    return {g: p for g, (_, p) in best.items()}


def test_ply_15_redistribution(ctx, rows, games, report, main_snap, snaps, xw) -> None:  # type: ignore[no-untyped-def]
    ga = o.games_ago(rows)
    qb = _qb_by_game(rows)
    hc = _coach_by_game(main_snap)
    pos = _positions(main_snap)
    k = op.v(PL.ply_15_k_games)
    same_w = op.v(PL.ply_15_same_position_weight)
    low = op.v(PL.ply_15_low_confidence_max_career_snaps)
    min_games = op.v(PL.ply_15_min_games_without)
    career: dict[str, float] = defaultdict(float)
    for r in main_snap.collect("snap_counts").to_dicts():
        career[xw.get(r["pfr_player_id"], f"pfr:{r['pfr_player_id']}")] += r["offense_snaps"] or 0
    shares = {
        "target_share": (op.usage_target, lambda r: r["receiver_player_id"]),
        "carry_share": (op.usage_carry, lambda r: r["rusher_player_id"]),
    }
    frame = raw(ctx, "PLY-15")
    got = {
        (r["entity_id"], r["team"], r["cell"], r["stat"]): r for r in frame.iter_rows(named=True)
    }
    sh = {
        s: {
            (r["entity_id"], r["team"], r["cell"]): r
            for r in shrunk(ctx, "PLY-15", s).iter_rows(named=True)
        }
        for s in shares
    }
    outs = sorted({(r["gsis_id"], r["team"]) for r in report if r["report_status"] == "Out"})
    checked = 0
    for x, team in outs:
        team_games = {g for g, i in ga.get(team, {}).items()}
        now_game = min(team_games, key=lambda g: ga[team][g]) if team_games else None
        cur_qb, cur_hc = qb.get((team, now_game)), hc.get((team, now_game))
        without = sorted(
            g
            for g in team_games
            if g not in games.get((x, team), set())
            and qb.get((team, g)) == cur_qb
            and hc.get((team, g)) == cur_hc
        )
        for stat, (keep, whose) in shares.items():
            u = op.share_units(rows, games, keep, lambda r: "all", whose)
            season = op.aggregate(u, op.v(o.C.g3_usage_half_life_games))
            cur = {
                key: a.value
                for (key, _), a in season.items()
                if key[1] == team and a.value is not None
            }
            s_x = cur.get((x, team)) or 0.0
            if s_x == 0:
                assert not any(kk[2] == f"without:{x}" and kk[3] == stat for kk in got), x
                continue
            rest = {key: s for key, s in cur.items() if key[0] != x and s > 0}
            wts = {
                key: s * (same_w if pos.get(key[0]) == pos.get(x) else 1.0)
                for key, s in rest.items()
            }
            tw = sum(wts.values())
            cell = f"without:{x}"
            for key, s in rest.items():
                default = s + s_x * wts[key] / tw
                # observed, per game, in the games without X he played
                num: dict[str, float] = defaultdict(float)
                den: dict[str, float] = defaultdict(float)
                for r in rows:
                    mine = r["game_id"] in games.get(key, set())
                    if r["posteam"] == team and r["game_id"] in without and keep(r) and mine:
                        den[r["game_id"]] += 1
                        num[r["game_id"]] += whose(r) == key[0]
                gs = sorted(den)
                r = got[(key[0], team, cell, stat)]
                assert r["n"] == len(gs), (key, stat)
                assert r["below_min_sample"] == (len(without) < min_games)
                h = op.v(o.C.g3_usage_half_life_games)
                ws = {g: 0.5 ** (ga[team][g] / h) for g in gs}
                if gs:
                    assert r["value"] == pytest.approx(sum(num.values()) / sum(den.values()))
                    vw = sum(ws[g] * num[g] for g in gs) / sum(ws[g] * den[g] for g in gs)
                    neff = sum(ws.values()) ** 2 / sum(w * w for w in ws.values())
                    assert r["value_w"] == pytest.approx(vw, rel=1e-12)
                else:
                    assert r["value"] is None
                srow = sh[stat][(key[0], team, cell)]
                assert srow["prior"] == pytest.approx(default, rel=1e-12), (key, stat)
                if len(without) >= min_games and gs:
                    want = (neff * vw + k * default) / (neff + k)
                else:
                    want = default
                assert srow["shrunk"] == pytest.approx(want, rel=1e-12), (key, stat)
                is_low = career[key[0]] < low and default > s
                assert ("low confidence" in (r["note"] or "")) == is_low, (key, r["note"])
                checked += 1
    assert checked > 0, "fixture has no Out player with a target or carry share"
    print(f"\nPLY-15: {checked} teammate rows checked for {len(outs)} Out players")
