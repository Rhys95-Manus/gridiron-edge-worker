"""Golden tests, section 6b quarterback skills: PLY-18 to PLY-23 on the 2024 week-8 snapshot,
and the FTN-based ones on the 2021 (no FTN) snapshot."""

from __future__ import annotations

from typing import Any

import polars as pl
import pytest

from ge.metrics.context import build_context
from ge.metrics.registry import raw, shrunk
from ge.store.snapshot import snapshot
from tests.phase3 import oracle as o
from tests.phase3 import oracle_player as op
from tests.phase3 import oracle_skills as osk
from tests.phase3.conftest import STORE, first_game
from tests.phase3.test_player_usage import check

H_EFF = op.v(o.C.g3_efficiency_half_life_games)
H_USE = op.v(o.C.g3_usage_half_life_games)
PL = op.PL
BANDS = ["behind", "short", "intermediate", "deep", "unknown"]
SIDES = ["left", "middle", "right", "unknown"]


def _keys(units: osk.Units) -> set[op.Key]:
    return {u[0] for u in units}


def _passer(r: dict[str, Any]) -> str | None:
    return r["passer_player_id"]


def check_position_prior(ctx, sid, stat, agg, units, pos, k, cell="all", fixed=None) -> None:  # type: ignore[no-untyped-def]
    """Shrunk toward the pooled league value at a position (ruling 2026-10-04): a fixed one
    ('league QB', 'league RB'), or his own roster position ('league at position')."""
    pooled = osk.pooled_by_position(units, pos)
    got = {
        (r["entity_id"], r["team"]): r
        for r in shrunk(ctx, sid, stat).filter(pl.col("cell") == cell).iter_rows(named=True)
    }
    for (key, c), a in agg.items():
        if c != cell:
            continue
        r = got[key]
        p = fixed or pos.get(key[0])
        if p is None or (p, cell) not in pooled:
            assert r["shrunk"] is None and "no roster position" in r["note"], key
            continue
        assert r["prior"] == pytest.approx(pooled[(p, cell)], rel=1e-12), key
        assert r["k"] == k
        assert r["shrunk"] == pytest.approx(op.shrink(a, pooled[(p, cell)], k), rel=1e-12), key


def _raises(ctx, sid: str, stat: str) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(NotImplementedError, match=sid):
        shrunk(ctx, sid, stat)


@pytest.fixture(scope="module")
def pos(main_snap):  # type: ignore[no-untyped-def]
    return osk.positions(main_snap)


def test_ply_18_qb_depth_profile(ctx, rows) -> None:  # type: ignore[no-untyped-def]
    share = osk.cell_share_units(rows, osk.attempt, _passer, osk.band_or_unknown, BANDS)
    epa = op.own_units(rows, osk.attempt, _passer, osk.band_or_unknown, lambda r: r["epa"])
    adot = op.own_units(
        rows,
        lambda r: osk.attempt(r) and r["air_yards"] is not None,
        _passer,
        lambda r: "all",
        lambda r: r["air_yards"],
    )
    frame = raw(ctx, "PLY-18")
    qbs = _keys(share)
    check(frame, "share", op.aggregate(share, H_USE), qbs, BANDS)
    check(frame, "epa", op.aggregate(epa, H_EFF), qbs, BANDS, op.v(PL.ply_18_min_attempts_per_band))
    check(frame, "adot", op.aggregate(adot, H_EFF), qbs, ["all"])
    for s in ("share", "epa", "adot"):
        _raises(ctx, "PLY-18", s)


def _pa_gap(rows, ftn):  # type: ignore[no-untyped-def]
    def who(r):  # type: ignore[no-untyped-def]
        q = op.dropback_qb(r)
        return None if q is None or r["posteam"] is None else (q, r["posteam"])

    def flag(r):  # type: ignore[no-untyped-def]
        f = osk.ftn_field(ftn, r, "is_play_action")
        return None if f is None else bool(f)

    return osk.gap(rows, o.dropback, who, flag, lambda r: float(r["epa"]), H_EFF)


def _check_gap(ctx, sid, stat, want, league, k, min_n, entity="player") -> None:  # type: ignore[no-untyped-def]
    frame = raw(ctx, sid)
    rows = {
        (r["entity_id"], r["team"]): r
        for r in frame.filter(
            (pl.col("stat") == stat) & (pl.col("entity_type") == entity)
        ).iter_rows(named=True)
    }
    lg = frame.filter((pl.col("stat") == stat) & (pl.col("entity_type") == "league"))
    assert lg["value"][0] == pytest.approx(league, rel=1e-12)
    sh = {(r["entity_id"], r["team"]): r for r in shrunk(ctx, sid, stat).iter_rows(named=True)}
    for key, w in want.items():
        r = rows[key]
        assert r["n"] == w["n"], key
        for f in ("value", "value_w"):
            assert r[f] == (None if w[f] is None else pytest.approx(w[f], rel=1e-12, abs=1e-12))
        assert r["below_min_sample"] == (w["n"] < min_n)
        want_s = (
            league
            if w["value_w"] is None or w["n"] == 0
            else ((w["n_eff"] * w["value_w"] + k * league) / (w["n_eff"] + k))
        )
        assert sh[key]["shrunk"] == pytest.approx(want_s, rel=1e-12, abs=1e-12), key


def test_ply_19_play_action_split(ctx, rows, ftn) -> None:  # type: ignore[no-untyped-def]
    want, league = _pa_gap(rows, ftn)
    _check_gap(
        ctx,
        "PLY-19",
        "epa_gap",
        want,
        league,
        op.v(PL.ply_19_k),
        op.v(PL.ply_19_min_play_action_dropbacks),
    )
    rate = op.own_units(
        rows,
        lambda r: o.dropback(r) and osk.ftn_field(ftn, r, "is_play_action") is not None,
        op.dropback_qb,
        lambda r: "all",
        lambda r: float(osk.ftn_field(ftn, r, "is_play_action")),
    )
    qbs = _keys(op.own_units(rows, o.dropback, op.dropback_qb, lambda r: "all", lambda r: 1.0))
    check(raw(ctx, "PLY-19"), "play_action_rate", op.aggregate(rate, H_EFF), qbs, ["all"])
    _raises(ctx, "PLY-19", "play_action_rate")


def test_ply_20_accuracy_and_ball_security(ctx, rows, ftn, pos) -> None:  # type: ignore[no-untyped-def]
    k = op.v(PL.ply_20_k)
    mn = op.v(PL.ply_20_min_attempts)
    frame = raw(ctx, "PLY-20")
    stats: dict[str, osk.Units] = {
        "cpoe": op.own_units(
            rows,
            lambda r: osk.attempt(r) and r["cp"] is not None,
            _passer,
            lambda r: "all",
            lambda r: r["complete_pass"] - r["cp"],
        ),
    }
    for stat, field in (
        ("catchable_rate", "is_catchable_ball"),
        ("interception_worthy_rate", "is_interception_worthy"),
        ("throwaway_rate", "is_throw_away"),
    ):
        stats[stat] = op.own_units(
            rows,
            lambda r, f=field: osk.attempt(r) and osk.ftn_field(ftn, r, f) is not None,
            _passer,
            lambda r: "all",
            lambda r, f=field: float(osk.ftn_field(ftn, r, f)),
        )
    passers = _keys(op.own_units(rows, osk.attempt, _passer, lambda r: "all", lambda r: 1.0))
    for stat, u in stats.items():
        agg = op.aggregate(u, H_EFF)
        check(frame, stat, agg, passers, ["all"], mn)
        check_position_prior(ctx, "PLY-20", stat, agg, u, pos, k, fixed="QB")


def test_ply_21_time_to_throw_and_sacks(ctx, rows, main_snap, pos) -> None:  # type: ignore[no-untyped-def]
    k = op.v(PL.ply_21_k)
    ngs = main_snap.collect("nextgen_passing").filter(pl.col("season") == main_snap.season)
    week_g = {(r["team"], r["week"]): r["g"] for r in ctx.games.iter_rows(named=True)}
    ttt: osk.Units = []
    for r in ngs.to_dicts():
        if r["attempts"] and r["avg_time_to_throw"] is not None:
            a = float(r["attempts"])
            ttt.append(
                (
                    (r["player_gsis_id"], r["team_abbr"]),
                    "all",
                    week_g[(r["team_abbr"], r["week"])],
                    a * r["avg_time_to_throw"],
                    a,
                    a,
                )
            )
    sacks = op.own_units(rows, o.dropback, op.dropback_qb, lambda r: "all", lambda r: r["sack"])
    frame = raw(ctx, "PLY-21")
    for stat, u in (("time_to_throw", ttt), ("sack_rate", sacks)):
        agg = op.aggregate(u, H_EFF)
        check(frame, stat, agg, _keys(u), ["all"], op.v(PL.ply_21_min_dropbacks))
        check_position_prior(ctx, "PLY-21", stat, agg, u, pos, k, fixed="QB")


def test_ply_22_rushing_threat(ctx, rows, pos, games) -> None:  # type: ignore[no-untyped-def]
    def is_rush(r: dict[str, Any]) -> bool:
        return o.designed_run(r) or (o.dropback(r) and r["qb_scramble"] == 1)

    rushes = op.own_units(
        rows, is_rush, lambda r: r["rusher_player_id"], lambda r: "all", lambda r: r["yards_gained"]
    )
    scr = op.own_units(
        rows, o.dropback, op.dropback_qb, lambda r: "all", lambda r: r["qb_scramble"]
    )
    ga = o.games_ago(rows)
    per_game: dict[tuple[op.Key, str], float] = {}
    for r in rows:
        if r["posteam"] is None:
            continue
        for p in {
            op.dropback_qb(r) if o.dropback(r) else None,
            r["rusher_player_id"] if is_rush(r) else None,
        } - {None}:
            per_game.setdefault(((p, r["posteam"]), r["game_id"]), 0.0)
        if o.designed_run(r) and r["rusher_player_id"] is not None:
            key = ((r["rusher_player_id"], r["posteam"]), r["game_id"])
            per_game[key] = per_game.get(key, 0.0) + 1
    rpg = [(key, "all", ga[key[1]][gid], x, 1.0, 1.0) for (key, gid), x in per_game.items()]
    qbs = {k for k in _keys(rushes) | _keys(scr) | {u[0] for u in rpg} if pos.get(k[0]) == "QB"}
    only_qb = lambda u: [x for x in u if x[0] in qbs]  # noqa: E731
    frame = raw(ctx, "PLY-22")
    check(
        frame,
        "yards_per_rush",
        op.aggregate(only_qb(rushes), H_EFF),
        qbs,
        ["all"],
        op.v(PL.ply_22_min_rushes),
    )
    check(frame, "scramble_rate", op.aggregate(only_qb(scr), H_EFF), qbs, ["all"])
    check(frame, "designed_runs_per_game", op.aggregate(only_qb(rpg), H_EFF), qbs, ["all"])
    agg = op.aggregate(only_qb(rushes), H_EFF)
    check_position_prior(
        ctx, "PLY-22", "yards_per_rush", agg, rushes, pos, op.v(PL.ply_22_k), fixed="QB"
    )
    _raises(ctx, "PLY-22", "scramble_rate")
    _raises(ctx, "PLY-22", "designed_runs_per_game")


def test_ply_23_direction(ctx, rows) -> None:  # type: ignore[no-untyped-def]
    share = osk.cell_share_units(rows, osk.attempt, _passer, osk.location, SIDES)
    epa = op.own_units(rows, osk.attempt, _passer, osk.location, lambda r: r["epa"])
    frame = raw(ctx, "PLY-23")
    check(frame, "share", op.aggregate(share, H_USE), _keys(share), SIDES)
    check(
        frame,
        "epa",
        op.aggregate(epa, H_EFF),
        _keys(share),
        SIDES,
        op.v(PL.ply_23_min_attempts_per_side),
    )
    _raises(ctx, "PLY-23", "share")
    _raises(ctx, "PLY-23", "epa")


@pytest.fixture(scope="module")
def ctx_2021():  # type: ignore[no-untyped-def]
    return build_context(snapshot(first_game(6, season=2021), root=STORE))


@pytest.mark.parametrize(
    ("sid", "stat"),
    [
        ("PLY-19", "epa_gap"),
        ("PLY-20", "catchable_rate"),
        ("PLY-20", "interception_worthy_rate"),
        ("PLY-20", "throwaway_rate"),
    ],
)
def test_ftn_skills_missing_before_2022(ctx_2021, sid: str, stat: str) -> None:  # type: ignore[no-untyped-def]
    s = shrunk(ctx_2021, sid, stat)
    assert s.height > 0 and s["shrunk"].null_count() == s.height
    assert set(s["note"].to_list()) == {"no FTN: missing"}
