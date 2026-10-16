"""PRJ-01a / COA-07 per-window fit on the fixture store, and provenance of the committed
window files.

- coa07_features reproduces Phase 3's coa_07() for the target game (same origin rules).
- team_games: points are the schedules' final scores, drives the distinct fixed_drive values in
  possession, plays and EPA the OFF-01 qualifying plays (oracle: tests/phase3/oracle.py).
- fit_window reads only the window's training seasons, gives identical output when later
  seasons are deleted, and round-trips through its versioned file."""

from __future__ import annotations

import datetime as dt
import math
import shutil
from collections import defaultdict
from pathlib import Path

import polars as pl
import pytest
import yaml

from ge.config import FittedFile, _check_fitted, _read_yaml, load_params
from ge.fit import history
from ge.metrics.coaching import coa_07
from ge.metrics.context import build_context
from ge.models.ratings import (
    C_KEY,
    CALIB_KEYS,
    COA07_KEYS,
    LEAGUE_KEYS,
    RATINGS_FITTED_ROOT,
    SE_SUFFIX,
    coa07_features,
    load_window_consts,
)
from ge.models.ratings_window import fit_window, team_games, write_window_file
from ge.store.holdout import Window
from ge.store.snapshot import snapshot
from tests.phase3 import oracle as o
from tests.phase3.conftest import STORE, first_game, store_table

AS_OF = dt.datetime(2026, 10, 12, tzinfo=dt.UTC)
# A window over the one full training season the fixture store holds (2023), test season 2024.
FIXTURE_WINDOW = Window("S2024", 2024, (2023,))


@pytest.mark.parametrize("week", [3, 5, 8])
def test_coa07_features_match_coa_07(week: int) -> None:
    gid = first_game(week)
    snap = snapshot(gid, root=STORE)
    want = {(r["entity_id"], r["stat"]): r["value"] for r in coa_07(build_context(snap)).to_dicts()}
    tgt = snap.collect("target_game")
    sched = pl.concat([snap.collect("schedules"), tgt], how="diagonal_relaxed")
    got = coa07_features(sched, [gid])
    t = tgt.row(0, named=True)
    assert sorted(got["team"].to_list()) == sorted([t["home_team"], t["away_team"]])
    for r in got.to_dicts():
        assert r["game_id"] == gid
        assert r["rest_days"] == want[(r["team"], "rest_days")]
        assert r["travel_km"] == pytest.approx(want[(r["team"], "travel_km")], abs=1e-9)
        assert r["tz_change_hours"] == want[(r["team"], "tz_change_hours")]
        side = 1.0 if r["team"] == t["home_team"] else -1.0
        assert r["home"] == (0.0 if t["location"] == "Neutral" else side)


def test_team_games_match_oracle() -> None:
    pbp = store_table("pbp", 2023)
    sched = store_table("schedules", 2023)
    got = {(r["game_id"], r["team"]): r for r in team_games(pbp, sched).to_dicts()}
    plays: dict[tuple[str, str], list[float]] = defaultdict(list)
    drives: dict[tuple[str, str], set[float]] = defaultdict(set)
    for r in pbp.to_dicts():
        key = (r["game_id"], r["posteam"])
        if r["posteam"] is not None and r["fixed_drive"] is not None:
            drives[key].add(r["fixed_drive"])
        if o.qualifying(r) and r["epa"] is not None:
            plays[key].append(float(r["epa"]))
    scores = {}
    for s in sched.to_dicts():
        if s["home_score"] is not None:
            scores[(s["game_id"], s["home_team"])] = s["home_score"]
            scores[(s["game_id"], s["away_team"])] = s["away_score"]
    assert set(got) == set(scores)
    for key, r in got.items():
        assert r["season"] == 2023
        assert r["points"] == scores[key]
        assert r["drives"] == len(drives[key])
        assert r["plays"] == len(plays[key])
        assert r["epa_sum"] == pytest.approx(math.fsum(plays[key]), abs=1e-9)


@pytest.mark.usefixtures("fit_env")
def test_fit_window_reads_only_training_seasons(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[int] = []
    orig = history.Reader.version

    def spy(self: history.Reader, dataset: str, season: int):  # type: ignore[no-untyped-def]
        seen.append(season)
        return orig(self, dataset, season)

    monkeypatch.setattr(history.Reader, "version", spy)
    fit = fit_window(FIXTURE_WINDOW, AS_OF, root=STORE)
    assert seen and all(s < 2024 for s in seen if s >= 1900), sorted(set(seen))
    assert fit.seasons == (2023,)
    assert fit.c.n_team_games > 0 and math.isfinite(fit.c.c) and fit.c.c_se > 0
    assert set(fit.coa07.coefs) == {"home", "rest", "travel", "tz"}


@pytest.mark.usefixtures("fit_env")
def test_fit_window_ignores_later_seasons(tmp_path: Path) -> None:
    copy = tmp_path / "store"
    shutil.copytree(STORE, copy)
    for ds in copy.iterdir():
        for later in ds.glob("season=2024"):
            shutil.rmtree(later)
    a = fit_window(FIXTURE_WINDOW, AS_OF, root=STORE)
    b = fit_window(FIXTURE_WINDOW, AS_OF, root=copy)
    assert repr(a) == repr(b)


@pytest.mark.usefixtures("fit_env")
def test_window_file_round_trip(tmp_path: Path) -> None:
    fit = fit_window(FIXTURE_WINDOW, AS_OF, root=STORE)
    path = write_window_file(fit, "rtest", tmp_path)
    (tmp_path / "active.yaml").write_text("fit_version: rtest\n", encoding="utf-8", newline="\n")
    assert path == tmp_path / "rtest" / "S2024.yaml"
    assert b"\r\n" not in path.read_bytes()
    f = FittedFile.model_validate(_read_yaml(path))
    _check_fitted(f, path, load_params())
    assert "Data: nflverse" in f.attribution
    got = load_window_consts(2024, tmp_path)
    assert dict(got.coa07) == dict(fit.coa07.coefs)
    assert dict(got.coa07_se) == dict(fit.coa07.se)
    assert (got.c, got.c_se) == (fit.c.c, fit.c.c_se)
    assert (got.league_epa, got.league_ppd, got.league_drives) == (
        fit.c.league_epa,
        fit.c.league_ppd,
        fit.c.league_drives,
    )
    for v in f.values.values():
        assert v.seasons == [2023]


def test_committed_window_files() -> None:
    """The ratings constants the walk-forward and live ratings read: one file per window in
    every committed version, each with every constant, its standard error and full
    provenance. r1 (Phase 4) holds the base keys; r2 on (Phase 4b) also holds the calibration
    keys (change approved 2026-10-14)."""
    active = RATINGS_FITTED_ROOT / "active.yaml"
    assert active.exists(), "run `ge ratings-fit` and commit config/ratings_fitted"
    version = yaml.safe_load(active.read_text(encoding="utf-8"))["fit_version"]
    versions = sorted(p.name for p in RATINGS_FITTED_ROOT.iterdir() if p.is_dir())
    assert version in versions
    bt = load_params().backtest
    first, last = int(bt.bt_01_first_test_season.value), int(bt.bt_01_last_test_season.value)
    holdout = int(bt.bt_01_holdout_season.value)
    base = {*COA07_KEYS.values(), C_KEY, *LEAGUE_KEYS.values()}
    base |= {k + SE_SUFFIX for k in (*COA07_KEYS.values(), C_KEY)}
    for ver in versions:
        keys = base if ver == "r1" else base | set(CALIB_KEYS.values())
        for window in [f"S{s}" for s in range(first, last + 1)] + ["live"]:
            path = RATINGS_FITTED_ROOT / ver / f"{window}.yaml"
            f = FittedFile.model_validate(_read_yaml(path))
            _check_fitted(f, path, load_params())
            assert holdout not in f.seasons
            assert set(f.values) == keys, (ver, window)
            for key, v in f.values.items():
                assert v.method.strip() and v.n > 0 and set(v.seasons) <= set(f.seasons), key
