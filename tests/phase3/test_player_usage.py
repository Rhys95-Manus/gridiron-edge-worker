"""Golden tests, spec section 4 usage: PLY-01 to PLY-08, PLY-12 and PLY-13, on the fixture's
2024 week-8 snapshot. 3b rulings (2026-10-04): shares over the games he played, one row per
(player, team) stint, role-prior shrinkage raises until Phase 3e."""

from __future__ import annotations

import math
from typing import Any

import polars as pl
import pytest

from ge.metrics.registry import REGISTRY, raw, shrunk
from tests.phase3 import oracle_player as op
from tests.phase3.oracle import P

H_USE = op.v(P.conventions.g3_usage_half_life_games)
H_EFF = op.v(P.conventions.g3_efficiency_half_life_games)
PL = op.PL
REL = 1e-12
ZONES = {
    z: op.v(getattr(PL, z))
    for z in (
        "ply_06_zone_20_yardline_100",
        "ply_06_zone_10_yardline_100",
        "ply_06_zone_5_yardline_100",
    )
}


def _ap(x: float | None) -> Any:
    return None if x is None else pytest.approx(x, rel=REL, abs=1e-12)


def check(
    frame: pl.DataFrame,
    stat: str,
    want: dict[tuple[op.Key, str], op.Agg],
    keys: set[op.Key],
    cells: list[str],
    min_n: float | None = None,
) -> None:
    rows = frame.filter((pl.col("stat") == stat) & (pl.col("entity_type") == "player"))
    got = {((r["entity_id"], r["team"]), r["cell"]): r for r in rows.iter_rows(named=True)}
    assert {k for k, _ in got} == keys, (stat, sorted({k for k, _ in got} ^ keys)[:5])
    for key in keys:
        for c in cells:
            r, a = got[(key, c)], want.get((key, c))
            if a is None:
                assert r["n"] == 0 and r["value"] is None, (stat, key, c)
                continue
            assert r["n"] == a.n, (stat, key, c)
            assert r["value"] == _ap(a.value), (stat, key, c)
            assert r["value_w"] == _ap(a.value_w), (stat, key, c)
            assert r["n_eff"] == _ap(a.n_eff), (stat, key, c)
            if min_n is not None:
                assert r["below_min_sample"] == (a.n < min_n), (stat, key, c)


def _role_prior_raises(ctx, sid: str, stat: str) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(NotImplementedError, match="role prior"):
        shrunk(ctx, sid, stat)


def _games_played(games, key) -> int:  # type: ignore[no-untyped-def]
    return len(games.get(key, ()))


def test_ply_01_snap_share(ctx, games, snaps, xw) -> None:  # type: ignore[no-untyped-def]
    """Player offense snaps / team offense snaps (A12: team snaps from snap counts), over the
    games he played; n = games (k in games)."""
    rows_ = ctx.table("pbp").to_dicts()
    ga = op.games_ago(rows_)
    ts = op.team_snaps(snaps)
    u = []
    for r in snaps:
        if (r["offense_snaps"] or 0) > 0:
            pid = xw.get(r["pfr_player_id"], f"pfr:{r['pfr_player_id']}")
            t = (r["team"], r["game_id"])
            u.append(
                (
                    (pid, r["team"]),
                    "all",
                    ga[r["team"]][r["game_id"]],
                    float(r["offense_snaps"]),
                    ts[t],
                    1.0,
                )
            )
    frame = raw(ctx, "PLY-01")
    check(frame, "snap_share", op.aggregate(u, H_USE), set(games), ["all"])
    for r in frame.filter(pl.col("entity_type") == "player").iter_rows(named=True):
        n_games = sum(1 for x in u if x[0] == (r["entity_id"], r["team"]))
        assert r["below_min_sample"] == (n_games < op.v(PL.ply_01_min_games))
    _role_prior_raises(ctx, "PLY-01", "snap_share")


def test_unmatched_snap_players_are_reported(ctx, snaps, xw) -> None:  # type: ignore[no-untyped-def]
    """A12: snap-count players with no GSIS ID keep a visible pfr: key and are listed."""
    frame = raw(ctx, "PLY-01").filter(pl.col("entity_id").str.starts_with("pfr:"))
    want = {
        f"pfr:{r['pfr_player_id']}"
        for r in snaps
        if (r["offense_snaps"] or 0) > 0 and r["pfr_player_id"] not in xw
    }
    assert set(frame["entity_id"].to_list()) == want
    print(f"\nsnap-count players without a GSIS ID: {len(want)}")


def test_ply_02_route_participation_proxy(ctx) -> None:  # type: ignore[no-untyped-def]
    a = raw(ctx, "PLY-02")
    b = raw(ctx, "PLY-01")
    assert a["proxy"].all()
    cols = ["entity_id", "team", "cell", "value", "value_w", "n", "n_eff"]
    assert (
        a.filter(pl.col("entity_type") == "player")
        .select(cols)
        .sort(cols)
        .equals(b.filter(pl.col("entity_type") == "player").select(cols).sort(cols))
    )
    with pytest.raises(NotImplementedError, match="PAID: DATA-11"):
        REGISTRY["PLY-02"].full(ctx)  # type: ignore[misc]


def test_ply_03_target_share(ctx, rows, games) -> None:  # type: ignore[no-untyped-def]
    u = op.share_units(
        rows, games, op.usage_target, lambda r: "all", lambda r: r["receiver_player_id"]
    )
    check(raw(ctx, "PLY-03"), "target_share", op.aggregate(u, H_USE), set(games), ["all"])
    _role_prior_raises(ctx, "PLY-03", "target_share")


def test_ply_04_air_share_and_wopr(ctx, rows, games) -> None:  # type: ignore[no-untyped-def]
    whose = lambda r: r["receiver_player_id"]  # noqa: E731
    ua = op.share_units(
        rows,
        games,
        op.usage_target,
        lambda r: "all",
        whose,
        x=lambda r: r["air_yards"],
        d=lambda r: r["air_yards"],
    )
    ut = op.share_units(rows, games, op.usage_target, lambda r: "all", whose)
    air, tgt = op.aggregate(ua, H_USE), op.aggregate(ut, H_USE)
    frame = raw(ctx, "PLY-04")
    check(frame, "air_share", air, set(games), ["all"])
    wt, wa = op.v(PL.ply_04_wopr_target_weight), op.v(PL.ply_04_wopr_air_weight)
    wop = {
        (r["entity_id"], r["team"]): r
        for r in frame.filter(pl.col("stat") == "wopr").iter_rows(named=True)
    }
    for key, a in tgt.items():
        b = air[key]
        k = key[0]
        if a.value is None or b.value is None:
            continue
        assert wop[k]["value"] == _ap(wt * a.value + wa * b.value), k
        assert wop[k]["value_w"] == _ap(wt * a.value_w + wa * b.value_w), k  # type: ignore[operator]
    _role_prior_raises(ctx, "PLY-04", "air_share")


def test_ply_05_carry_share(ctx, rows, games) -> None:  # type: ignore[no-untyped-def]
    u = op.share_units(
        rows, games, op.usage_carry, lambda r: "all", lambda r: r["rusher_player_id"]
    )
    check(raw(ctx, "PLY-05"), "carry_share", op.aggregate(u, H_USE), set(games), ["all"])
    _role_prior_raises(ctx, "PLY-05", "carry_share")


def _opp(r: dict[str, Any]) -> bool:
    return op.usage_target(r) or op.usage_carry(r)


def test_ply_06_red_zone_share(ctx, rows, games) -> None:  # type: ignore[no-untyped-def]
    zones = [
        PL.ply_06_zone_20_yardline_100,
        PL.ply_06_zone_10_yardline_100,
        PL.ply_06_zone_5_yardline_100,
    ]
    u = []
    for z in zones:
        zv = op.v(z)
        u += op.share_units(
            rows,
            games,
            lambda r, zv=zv: _opp(r) and r["yardline_100"] <= zv,
            lambda r, zv=zv: f"inside_{int(zv)}",
            op.owner,
        )
    cells = [f"inside_{int(op.v(z))}" for z in zones]
    check(raw(ctx, "PLY-06"), "opportunity_share", op.aggregate(u, H_USE), set(games), cells)
    _role_prior_raises(ctx, "PLY-06", "opportunity_share")


def test_ply_07_third_down_and_two_minute(ctx, rows, games) -> None:  # type: ignore[no-untyped-def]
    two = op.v(PL.ply_07_two_minute_seconds)
    u = op.share_units(
        rows, games, lambda r: _opp(r) and r["down"] == 3, lambda r: "third_down", op.owner
    )
    u += op.share_units(
        rows,
        games,
        lambda r: _opp(r) and r["half_seconds_remaining"] <= two,
        lambda r: "two_minute",
        op.owner,
    )
    check(
        raw(ctx, "PLY-07"),
        "opportunity_share",
        op.aggregate(u, H_USE),
        set(games),
        ["third_down", "two_minute"],
    )
    _role_prior_raises(ctx, "PLY-07", "opportunity_share")


def test_ply_08_yards_per_team_dropback_proxy(ctx, rows, games) -> None:  # type: ignore[no-untyped-def]
    """v1 proxy: receiving yards / team dropbacks in games he played (efficiency: G7 out)."""

    def yards(r: dict[str, Any]) -> float:
        return float(r["yards_gained"]) if r["complete_pass"] == 1 else 0.0

    u = op.share_units(
        rows, games, op.dropback, lambda r: "all", lambda r: r["receiver_player_id"], x=yards
    )
    frame = raw(ctx, "PLY-08")
    assert frame["proxy"].all()
    check(frame, "yards_per_team_dropback", op.aggregate(u, H_EFF), set(games), ["all"])
    _role_prior_raises(ctx, "PLY-08", "yards_per_team_dropback")
    with pytest.raises(NotImplementedError, match="PAID: DATA-11"):
        REGISTRY["PLY-08"].full(ctx)  # type: ignore[misc]


def test_ply_12_alignment_is_paid(ctx) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(NotImplementedError, match="PAID: DATA-11"):
        raw(ctx, "PLY-12")


def test_ply_13_trend_and_role_change(ctx, rows, games, snaps, xw) -> None:  # type: ignore[no-untyped-def]
    """L3 and L5 = the team's last 3 / 5 games, counting the ones he played; flag when
    |L3 - season| > 2 sqrt(p(1 - p) / n), p = season share, n = team opportunities in the L3
    games he played."""
    ga = op.games_ago(rows)
    ts = op.team_snaps(snaps)
    snap_u = []
    for r in snaps:
        if (r["offense_snaps"] or 0) > 0:
            pid = xw.get(r["pfr_player_id"], f"pfr:{r['pfr_player_id']}")
            snap_u.append(
                (
                    (pid, r["team"]),
                    "all",
                    ga[r["team"]][r["game_id"]],
                    float(r["offense_snaps"]),
                    ts[(r["team"], r["game_id"])],
                    1.0,
                )
            )
    metrics = {
        "PLY-01": snap_u,
        "PLY-03": op.share_units(
            rows, games, op.usage_target, lambda r: "all", lambda r: r["receiver_player_id"]
        ),
        "PLY-05": op.share_units(
            rows, games, op.usage_carry, lambda r: "all", lambda r: r["rusher_player_id"]
        ),
        "PLY-06": [
            x
            for z in ZONES
            for x in op.share_units(
                rows,
                games,
                lambda r, zv=ZONES[z]: _opp(r) and r["yardline_100"] <= zv,
                lambda r, zv=ZONES[z]: f"inside_{int(zv)}",
                op.owner,
            )
        ],
    }
    s_win, l_win = int(op.v(PL.ply_13_short_window_games)), int(op.v(PL.ply_13_long_window_games))
    sig = op.v(PL.ply_13_role_change_sigmas)
    frame = raw(ctx, "PLY-13")
    got = {
        (r["entity_id"], r["team"], r["cell"], r["stat"]): r for r in frame.iter_rows(named=True)
    }
    flagged = 0
    for sid, units in metrics.items():
        by: dict[tuple[op.Key, str], list[tuple[int, float, float]]] = {}
        for key, cell, g, x, d, _ in units:
            by.setdefault((key, cell), []).append((g, x, d))
        for (key, cell), items in by.items():
            sd = sum(d for _, _, d in items)
            if not sd:
                continue
            p = sum(x for _, x, _ in items) / sd
            row_cell = f"{sid}:{cell}"
            for name, w in (("L3", s_win), ("L5", l_win)):
                win = [(x, d) for g, x, d in items if g < w]
                dd = sum(d for _, d in win)
                r = got[(key[0], key[1], row_cell, name)]
                assert r["value"] == (_ap(sum(x for x, _ in win) / dd) if dd else None), (key, name)
                assert r["n"] == round(dd), (key, row_cell, name)
            win3 = [(x, d) for g, x, d in items if g < s_win]
            n3 = sum(d for _, d in win3)
            flag = got[(key[0], key[1], row_cell, "role_change")]
            if n3:
                l3 = sum(x for x, _ in win3) / n3
                want = abs(l3 - p) > sig * math.sqrt(p * (1 - p) / n3)
                assert flag["value"] == (1.0 if want else 0.0), (key, row_cell)
                flagged += want
            else:
                assert flag["value"] is None
    assert flagged > 0, "fixture has no role change at all"
