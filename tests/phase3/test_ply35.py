"""PLY-35 expected production from opportunity (spec synced 2026-10-16): golden test against an
independent oracle on the fixture store, the centring rule and its fallback, the minimum sample,
the shrink toward 0 with a fitted k, and the exclusions the spec lists."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import polars as pl
import pytest
import yaml

from ge.config import ATTRIBUTION, load_params, use_fitted_root
from ge.metrics import conventions as cv
from ge.metrics import expected as ex
from ge.metrics.context import build_context
from ge.metrics.engine import NO_SIGNAL, fit_k_key
from ge.metrics.registry import REGISTRY, raw, shrunk
from ge.store.known_at import with_kickoff
from ge.store.snapshot import Snapshot, snapshot
from tests.phase3.conftest import G4_WEEK, SEASON, STORE, store_table
from tests.phase3.oracle_ply35 import STATS, null_player_rows, oracle

P = load_params().player
MIN_GAMES = P.ply_35_min_games.value
MIN_WEEKS = P.ply_35_centring_min_weeks.value
FIRST = int(load_params().backtest.bt_01_first_training_season.value)


@pytest.fixture(scope="module")
def early_snap() -> Snapshot:
    """By rule: the earliest-kickoff game of week G4_WEEK, so only weeks before it are visible
    (fewer than 3): the previous season's centring mean stands in."""
    s = with_kickoff(store_table("schedules", SEASON)).filter(pl.col("week") == G4_WEEK)
    return snapshot(str(s.sort("kickoff_utc", "game_id")["game_id"][0]), root=STORE)


def _player_rows(df: pl.DataFrame, stat: str) -> pl.DataFrame:
    return df.filter((pl.col("stat") == stat) & (pl.col("entity_type") == "player"))


def test_params_quote_the_spec() -> None:
    assert MIN_GAMES == 3
    assert MIN_WEEKS == 3


def test_registered_with_four_shrunk_stats_and_raw_gaps() -> None:
    e = REGISTRY["PLY-35"]
    assert set(STATS) == set(ex.STATS)
    for s in STATS:
        assert e.stats[s].half_life == "efficiency"
        assert e.stats[f"{s}_raw"].k is None  # reported alongside, not shrunk
    assert (ex.ply_35.__doc__ or "").startswith("PLY-35")


@pytest.mark.parametrize("which", ["main", "early"])
def test_golden_against_the_oracle(which: str, main_snap: Snapshot, early_snap: Snapshot) -> None:
    snap = main_snap if which == "main" else early_snap
    ctx = build_context(snap)
    got = raw(ctx, "PLY-35")
    want, _, fallback = oracle(
        snap.season, snap.game_id, snap.as_of, cv.half_life("efficiency"), int(MIN_WEEKS)
    )
    assert fallback is (which == "early")  # games in fewer than 3 weeks are visible
    assert want, "oracle found no player-games"
    for stat in STATS:
        rows = _player_rows(got, stat).filter(pl.col("n") > 0)
        mine = {(r["entity_id"], r["team"]): r for r in rows.iter_rows(named=True)}
        theirs = {(p, t): v for (p, t, s), v in want.items() if s == stat}
        assert set(mine) == set(theirs), stat
        for key, v in theirs.items():
            r = mine[key]
            assert r["n"] == v["n"], (stat, key)
            assert math.isclose(r["value"], v["value"], rel_tol=0, abs_tol=1e-9), (stat, key)
            assert math.isclose(r["value_w"], v["value_w"], rel_tol=0, abs_tol=1e-9), (stat, key)
            assert math.isclose(r["n_eff"], v["n_eff"], rel_tol=1e-12), (stat, key)
            assert r["below_min_sample"] is (v["n"] < MIN_GAMES)


@pytest.mark.parametrize("which", ["main", "early"])
def test_centring_means_are_reported(which: str, main_snap: Snapshot, early_snap: Snapshot) -> None:
    snap = main_snap if which == "main" else early_snap
    got = raw(build_context(snap), "PLY-35")
    _, means, fallback = oracle(
        snap.season, snap.game_id, snap.as_of, cv.half_life("efficiency"), int(MIN_WEEKS)
    )
    lg = got.filter(pl.col("entity_id").str.starts_with("league:"))
    for (grp, stat), mu in means.items():
        r = lg.filter((pl.col("entity_id") == f"league:{grp}") & (pl.col("stat") == f"{stat}_raw"))
        assert r.height == 1, (grp, stat)
        assert math.isclose(r["value"][0], mu, rel_tol=0, abs_tol=1e-12)
        note = r["note"][0] or ""
        if fallback:
            assert f"season {snap.season - 1} full-season mean" in note
        else:
            assert f"season {snap.season} games visible at as_of" in note


def test_fallback_is_labelled_on_player_rows(early_snap: Snapshot) -> None:
    rows = _player_rows(raw(build_context(early_snap), "PLY-35"), "receiving_yards")
    played = rows.filter(pl.col("n") > 0)
    assert played.height
    assert all(
        f"centring: season {early_snap.season - 1} full-season mean" in (n or "")
        for n in played["note"].to_list()
    )


def test_raw_gaps_are_kept_alongside(main_snap: Snapshot) -> None:
    got = raw(build_context(main_snap), "PLY-35")
    for stat in STATS:
        a = _player_rows(got, stat).filter(pl.col("n") > 0)
        b = _player_rows(got, f"{stat}_raw").filter(pl.col("n") > 0)
        assert a.height == b.height
        j = a.join(b, on=["entity_id", "team"], suffix="_raw")
        # centred sum = raw sum - n x the group's mean, so the two differ unless the mean is 0
        assert (j["n"] == j["n_raw"]).all()


def test_rows_without_a_player_are_dropped_and_counted(main_snap: Snapshot) -> None:
    got = raw(build_context(main_snap), "PLY-35")
    c = got.filter(pl.col("stat") == "rows_no_player_id")
    assert c.height == 1
    assert c["value"][0] == null_player_rows(main_snap.season, main_snap.game_id, main_snap.as_of)
    assert c["value"][0] > 0  # the fixture has such rows
    players = _player_rows(got, "receptions")
    assert players["entity_id"].null_count() == 0


def test_without_a_fit_shrinking_raises(main_snap: Snapshot) -> None:
    with pytest.raises(NotImplementedError, match="PLY-35"):
        shrunk(build_context(main_snap), "PLY-35", "receiving_yards")


# ---- the shrink with a planted fitted k ----


def _v(value: float) -> dict[str, Any]:
    return {
        "spec_id": "PLY-35",
        "status": "fitted",
        "value": value,
        "method": "planted by test",
        "seasons": list(range(FIRST, 2024)),
        "n": 100,
        "initial_value": None,
    }


@pytest.fixture(scope="module")
def planted(tmp_path_factory: pytest.TempPathFactory) -> Path:
    r = tmp_path_factory.mktemp("ply35fit")
    body = {
        "fit_version": "tv",
        "window": "S2024",
        "test_season": 2024,
        "seasons": list(range(FIRST, 2024)),
        "data_as_of": "2026-10-09T00:00:00+00:00",
        "data_digest": "0" * 64,
        "code_commit": "test",
        "attribution": ATTRIBUTION,
        "values": {fit_k_key("PLY-35", "receiving_yards", None): _v(7.0)},
        "missing": {},
        "no_signal": {fit_k_key("PLY-35", "tds", None): NO_SIGNAL},
    }
    (r / "tv").mkdir()
    (r / "tv" / "S2024.yaml").write_text(yaml.safe_dump(body), encoding="utf-8")
    (r / "active.yaml").write_text("fit_version: tv\n", encoding="utf-8")
    return r


def test_shrinks_toward_zero_with_the_fitted_k(main_snap: Snapshot, planted: Path) -> None:
    with use_fitted_root(planted):
        s = shrunk(build_context(main_snap), "PLY-35", "receiving_yards")
    assert (s["prior"] == 0.0).all()
    assert set(s["k"].to_list()) == {7.0}
    played = s.filter(pl.col("n") > 0)
    want = played["n_eff"] * played["value_w"] / (played["n_eff"] + 7.0)
    assert ((played["shrunk"] - want).abs() < 1e-12).all()
    assert (s.filter(pl.col("n") == 0)["shrunk"] == 0.0).all()


def test_no_detectable_signal_leaves_zero(main_snap: Snapshot, planted: Path) -> None:
    with use_fitted_root(planted):
        s = shrunk(build_context(main_snap), "PLY-35", "tds")
    assert (s["shrunk"] == 0.0).all()
    assert all(NO_SIGNAL in (n or "") for n in s["note"].to_list())


# ---- pure-function cases the fixture may not hold ----


def _ff(
    rows: list[tuple[str, str | None, str, str | None, float, float, float, float]],
) -> pl.DataFrame:
    """(game_id, player_id, team, position, targets, carries, rec yards, rec yards exp)."""
    base = {c: 0.0 for c in ex.NUMERIC_COLUMNS}
    out = []
    for gid, pid, team, pos, tg, ca, ry, rye in rows:
        r = dict(base)
        r.update(
            game_id=gid, player_id=pid, posteam=team, position=pos, rec_attempt=tg,
            rush_attempt=ca, rec_yards_gained=ry, rec_yards_gained_exp=rye,
        )  # fmt: skip
        out.append(r)
    return pl.DataFrame(out)


def test_qualifying_rows_need_a_target_or_carry_and_a_player() -> None:
    df = _ff(
        [
            ("g1", "p1", "A", "WR", 1, 0, 10, 8),
            ("g1", "p2", "A", "QB", 0, 0, 0, 0),  # no opportunity
            ("g1", None, "A", None, 2, 0, 5, 5),  # no player
            ("g1", "p3", "A", "QB", 0, 3, 0, 0),  # QB rushing counts
        ]
    )
    rows, dropped = ex.qualifying(df)
    assert sorted(rows["player_id"].to_list()) == ["p1", "p3"]
    assert dropped == 1


def test_position_groups() -> None:
    df = pl.DataFrame({"position": ["QB", "RB", "WR", "TE", "FB", "P", None]})
    got = df.select(ex.position_group(pl.col("position")))["group"].to_list()
    assert got == ["QB", "RB", "WR", "TE", "Other", "Other", "Other"]


def test_traded_player_has_one_row_per_team() -> None:
    df = _ff(
        [
            ("g1", "p1", "A", "WR", 3, 0, 30, 20),
            ("g2", "p1", "B", "WR", 3, 0, 10, 20),
        ]
    )
    rows, _ = ex.qualifying(df)
    gaps = ex.raw_gaps(rows)
    keys = sorted(set(gaps.select("player_id", "posteam").iter_rows()))
    assert keys == [("p1", "A"), ("p1", "B")]
