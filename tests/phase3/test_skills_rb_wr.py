"""Golden tests, section 6b running back and receiver skills: PLY-24 to PLY-33 on the 2024
week-8 snapshot, and the FTN-based ones on the 2021 (no FTN) snapshot."""

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
from tests.phase3.test_skills_qb import BANDS, SIDES, _keys, _raises, check_position_prior

H_EFF = op.v(o.C.g3_efficiency_half_life_games)
H_USE = op.v(o.C.g3_usage_half_life_games)
PL = op.PL


def _rusher(r: dict[str, Any]) -> str | None:
    return r["rusher_player_id"]


def _receiver(r: dict[str, Any]) -> str | None:
    return r["receiver_player_id"]


@pytest.fixture(scope="module")
def pos(main_snap):  # type: ignore[no-untyped-def]
    return osk.positions(main_snap)


def box_band(box: Any) -> str | None:
    """PLY-24: light (<= 6 in box), standard (7), stacked (>= 8)."""
    if box is None:
        return None
    if box <= op.v(PL.ply_24_light_box_max):
        return "light"
    if box >= op.v(PL.ply_24_stacked_box_min):
        return "stacked"
    return "standard" if box == op.v(PL.ply_24_standard_box) else None


def test_ply_24_box_count_splits(ctx, rows, ftn) -> None:  # type: ignore[no-untyped-def]
    cell = lambda r: box_band(osk.ftn_field(ftn, r, "n_defense_box"))  # noqa: E731
    frame = raw(ctx, "PLY-24")
    backs = _keys(op.own_units(rows, o.designed_run, _rusher, lambda r: "all", lambda r: 1.0))
    for stat, x in (("success", lambda r: r["success"]), ("ypc", lambda r: r["yards_gained"])):
        u = op.own_units(rows, o.designed_run, _rusher, cell, x)
        check(
            frame,
            stat,
            op.aggregate(u, H_EFF),
            backs,
            ["light", "standard", "stacked"],
            op.v(PL.ply_24_min_carries_per_band),
        )
        _raises(ctx, "PLY-24", stat)


def test_ply_25_formation_split(ctx, rows) -> None:  # type: ignore[no-untyped-def]
    cell = lambda r: "shotgun" if r["shotgun"] == 1 else "under_center"  # noqa: E731
    frame = raw(ctx, "PLY-25")
    backs = _keys(op.own_units(rows, o.designed_run, _rusher, lambda r: "all", lambda r: 1.0))
    for stat, x in (("success", lambda r: r["success"]), ("ypc", lambda r: r["yards_gained"])):
        u = op.own_units(rows, o.designed_run, _rusher, cell, x)
        check(
            frame,
            stat,
            op.aggregate(u, H_EFF),
            backs,
            ["shotgun", "under_center"],
            op.v(PL.ply_25_min_carries_each),
        )
        _raises(ctx, "PLY-25", stat)


def test_ply_26_explosiveness_and_stuffs(ctx, rows, pos) -> None:  # type: ignore[no-untyped-def]
    frame = raw(ctx, "PLY-26")
    for stat, x, k in (
        (
            "explosive",
            lambda r: 1.0 if r["yards_gained"] >= op.v(PL.ply_26_explosive_min_yards) else 0.0,
            op.v(PL.ply_26_k_explosive),
        ),
        (
            "stuff",
            lambda r: 1.0 if r["yards_gained"] <= op.v(PL.ply_26_stuff_max_yards) else 0.0,
            op.v(PL.ply_26_k_stuff),
        ),
    ):
        u = op.own_units(rows, o.designed_run, _rusher, lambda r: "all", x)
        agg = op.aggregate(u, H_EFF)
        check(frame, stat, agg, _keys(u), ["all"], op.v(PL.ply_26_min_carries))
        check_position_prior(ctx, "PLY-26", stat, agg, u, pos, k, fixed="RB")
    # RYOE is PLY-11's value, shown alongside
    a = raw(ctx, "PLY-11").filter(pl.col("entity_type") == "player")
    b = frame.filter(pl.col("stat") == "ryoe_per_carry")
    cols = ["entity_id", "team", "value", "n"]
    assert a.select(cols).sort(cols).equals(b.select(cols).sort(cols))


def test_ply_27_receiving_role(ctx, rows, ftn, games) -> None:  # type: ignore[no-untyped-def]
    frame = raw(ctx, "PLY-27")
    screen = op.share_units(
        rows,
        games,
        lambda r: op.usage_target(r) and osk.ftn_field(ftn, r, "is_screen_pass") is True,
        lambda r: "all",
        _receiver,
    )
    check(frame, "screen_share", op.aggregate(screen, H_USE), set(games), ["all"])
    tgt = op.share_units(rows, games, op.usage_target, lambda r: "all", _receiver)
    check(frame, "target_share", op.aggregate(tgt, H_USE), set(games), ["all"])
    for s in ("screen_share", "target_share", "yacoe"):
        _raises(ctx, "PLY-27", s)


def test_ply_28_receiver_depth_profile(ctx, rows) -> None:  # type: ignore[no-untyped-def]
    share = osk.cell_share_units(rows, o.target, _receiver, osk.band_or_unknown, BANDS)
    epa = op.own_units(rows, o.target, _receiver, osk.band_or_unknown, lambda r: r["epa"])
    adot = op.own_units(
        rows,
        lambda r: o.target(r) and r["air_yards"] is not None,
        _receiver,
        lambda r: "all",
        lambda r: r["air_yards"],
    )
    frame = raw(ctx, "PLY-28")
    keys = _keys(share)
    check(frame, "share", op.aggregate(share, H_USE), keys, BANDS)
    check(frame, "epa", op.aggregate(epa, H_EFF), keys, BANDS, op.v(PL.ply_28_min_targets_per_band))
    check(frame, "adot", op.aggregate(adot, H_EFF), keys, ["all"])
    for s in ("share", "epa", "adot"):
        _raises(ctx, "PLY-28", s)


def test_ply_29_field_location(ctx, rows) -> None:  # type: ignore[no-untyped-def]
    share = osk.cell_share_units(rows, o.target, _receiver, osk.location, SIDES)
    epa = op.own_units(rows, o.target, _receiver, osk.location, lambda r: r["epa"])
    frame = raw(ctx, "PLY-29")
    check(frame, "share", op.aggregate(share, H_USE), _keys(share), SIDES)
    check(
        frame,
        "epa",
        op.aggregate(epa, H_EFF),
        _keys(share),
        SIDES,
        op.v(PL.ply_29_min_targets_per_side),
    )
    mid = frame.filter((pl.col("cell") == "middle") & (pl.col("stat") == "share"))
    assert (mid["proxy"]).all() and mid["note"].str.contains("slot").all()
    for s in ("share", "epa"):
        _raises(ctx, "PLY-29", s)


def test_ply_30_hands(ctx, rows, ftn, pos) -> None:  # type: ignore[no-untyped-def]
    f = lambda r, k: osk.ftn_field(ftn, r, k)  # noqa: E731
    frame = raw(ctx, "PLY-30")
    cases = {
        "drop_rate": (
            lambda r: (
                o.target(r) and f(r, "is_catchable_ball") is True and f(r, "is_drop") is not None
            ),
            lambda r: float(f(r, "is_drop")),
            op.v(PL.ply_30_min_catchable),
            op.v(PL.ply_30_k_catchable),
        ),
        "contested_catch_rate": (
            lambda r: o.target(r) and f(r, "is_contested_ball") is True,
            lambda r: float(r["complete_pass"]),
            op.v(PL.ply_30_min_contested),
            op.v(PL.ply_30_k_contested),
        ),
    }
    receivers = _keys(op.own_units(rows, o.target, _receiver, lambda r: "all", lambda r: 1.0))
    for stat, (keep, x, mn, k) in cases.items():
        u = op.own_units(rows, keep, _receiver, lambda r: "all", x)
        agg = op.aggregate(u, H_EFF)
        check(frame, stat, agg, receivers, ["all"], mn)
        check_position_prior(ctx, "PLY-30", stat, agg, u, pos, k)
    cr = op.own_units(
        rows,
        lambda r: (
            o.target(r) and r["complete_pass"] == 1 and f(r, "is_created_reception") is not None
        ),
        _receiver,
        lambda r: "all",
        lambda r: float(f(r, "is_created_reception")),
    )
    check(frame, "created_reception_rate", op.aggregate(cr, H_EFF), receivers, ["all"])
    _raises(ctx, "PLY-30", "created_reception_rate")


def test_ply_31_separation(ctx, main_snap, pos) -> None:  # type: ignore[no-untyped-def]
    ngs = main_snap.collect("nextgen_receiving").filter(pl.col("season") == main_snap.season)
    week_g = {(r["team"], r["week"]): r["g"] for r in ctx.games.iter_rows(named=True)}
    frame = raw(ctx, "PLY-31")
    for stat, col in (("separation", "avg_separation"), ("cushion", "avg_cushion")):
        u: osk.Units = []
        for r in ngs.to_dicts():
            if r["targets"] and r[col] is not None:
                t = float(r["targets"])
                u.append(
                    (
                        (r["player_gsis_id"], r["team_abbr"]),
                        "all",
                        week_g[(r["team_abbr"], r["week"])],
                        t * r[col],
                        t,
                        t,
                    )
                )
        agg = op.aggregate(u, H_EFF)
        check(frame, stat, agg, _keys(u), ["all"], op.v(PL.ply_31_min_targets))
        check_position_prior(ctx, "PLY-31", stat, agg, u, pos, op.v(PL.ply_31_k))
    a = raw(ctx, "PLY-09").filter(pl.col("entity_type") == "player")
    b = frame.filter(pl.col("stat") == "yacoe")
    cols = ["entity_id", "team", "value", "n"]
    assert a.select(cols).sort(cols).equals(b.select(cols).sort(cols))


def test_ply_32_end_zone_targets(ctx, rows, games) -> None:  # type: ignore[no-untyped-def]
    def ez(r: dict[str, Any]) -> bool:
        return bool(
            op.usage_target(r)
            and r["air_yards"] is not None
            and (r["air_yards"] >= r["yardline_100"])
        )

    u = op.share_units(rows, games, ez, lambda r: "all", _receiver)
    check(
        raw(ctx, "PLY-32"),
        "end_zone_share",
        op.aggregate(u, H_USE),
        set(games),
        ["all"],
        op.v(PL.ply_32_min_team_end_zone_targets),
    )
    _raises(ctx, "PLY-32", "end_zone_share")


def test_ply_33_play_action_and_motion_usage(ctx, rows, ftn, games) -> None:  # type: ignore[no-untyped-def]
    u = []
    for cell, field in (("play_action", "is_play_action"), ("motion", "is_motion")):
        u += op.share_units(
            rows,
            games,
            lambda r, f=field: op.usage_target(r) and osk.ftn_field(ftn, r, f) is True,
            lambda r, c=cell: c,
            _receiver,
        )
    check(
        raw(ctx, "PLY-33"),
        "target_share",
        op.aggregate(u, H_USE),
        set(games),
        ["play_action", "motion"],
        op.v(PL.ply_33_min_targets_each),
    )
    _raises(ctx, "PLY-33", "target_share")


@pytest.fixture(scope="module")
def ctx_2021():  # type: ignore[no-untyped-def]
    return build_context(snapshot(first_game(6, season=2021), root=STORE))


@pytest.mark.parametrize(
    ("sid", "stat"),
    [("PLY-30", "drop_rate"), ("PLY-30", "contested_catch_rate")],
)
def test_ftn_skills_missing_before_2022(ctx_2021, sid: str, stat: str) -> None:  # type: ignore[no-untyped-def]
    s = shrunk(ctx_2021, sid, stat)
    assert s.height > 0 and s["shrunk"].null_count() == s.height
    assert set(s["note"].to_list()) == {"no FTN: missing"}
    assert raw(ctx_2021, "PLY-24").filter(pl.col("entity_type") == "player")["n"].sum() == 0
