"""Phase 3e versioned params: fitted files sit beside config/params.yaml, never replace it, and
the metric engine reads the fit for the season it computes (S2021..S2024 walk-forward, `live`
for seasons after the holdout, the initial file alone before the first test season)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
import yaml

from ge.config import (
    ATTRIBUTION,
    PARAMS_PATH,
    FitVersionMissing,
    group_proxy,
    load_params,
    params_for,
    use_fitted_root,
    use_season,
)
from ge.store.holdout import HoldoutReadError

BT = load_params().backtest
HOLDOUT = int(BT.bt_01_holdout_season.value)
FIRST_TRAIN = int(BT.bt_01_first_training_season.value)
INITIAL_USAGE_H = float(load_params().conventions.g3_usage_half_life_games.value)


def _entry(value: float, seasons: list[int], spec_id: str = "G3") -> dict[str, Any]:
    return {
        "spec_id": spec_id,
        "status": "fitted",
        "value": value,
        "method": "planted by test",
        "seasons": seasons,
        "n": 100,
        "initial_value": None,
    }


def _file(
    window: str, test_season: int | None, last: int, values: dict[str, Any]
) -> dict[str, Any]:
    seasons = list(range(FIRST_TRAIN, last + 1))
    return {
        "fit_version": "tv1",
        "window": window,
        "test_season": test_season,
        "seasons": seasons,
        "data_as_of": "2026-10-07T00:00:00+00:00",
        "data_digest": "0" * 64,
        "code_commit": "test",
        "attribution": ATTRIBUTION,
        "values": values,
        "missing": {"fit:COA-02/p_go_intercept": "planted: no data"},
    }


def _write(root: Path, version: str, name: str, body: dict[str, Any]) -> None:
    d = root / version
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.yaml").write_text(yaml.safe_dump(body, sort_keys=True), encoding="utf-8")


@pytest.fixture
def root(tmp_path: Path) -> Path:
    r = tmp_path / "params_fitted"
    s23 = list(range(FIRST_TRAIN, 2023))
    _write(
        r,
        "tv1",
        "S2023",
        _file(
            "S2023",
            2023,
            2022,
            {
                "conventions.g3_usage_half_life_games": _entry(4.5, s23),
                "fit:OFF-12/team_ypc_k": _entry(321.0, s23, "OFF-12"),
            },
        ),
    )
    live = list(range(FIRST_TRAIN, HOLDOUT))
    _write(
        r,
        "tv1",
        "live",
        _file(
            "live", None, HOLDOUT - 1, {"conventions.g3_usage_half_life_games": _entry(2.0, live)}
        ),
    )
    (r / "active.yaml").write_text("fit_version: tv1\n", encoding="utf-8")
    return r


def test_overlay_for_walk_forward_season(root: Path) -> None:
    a = params_for(2023, root)
    e = a.params.conventions.g3_usage_half_life_games
    assert e.value == 4.5 and e.status == "fitted"
    assert a.window == "S2023"
    assert a.extra("fit:OFF-12/team_ypc_k", "OFF-12") == 321.0
    # Untouched keys keep the initial entry.
    assert a.params.offense.off_02_k == load_params().offense.off_02_k


def test_live_fit_for_seasons_after_holdout(root: Path) -> None:
    a = params_for(HOLDOUT + 1, root)
    assert a.window == "live"
    assert a.params.conventions.g3_usage_half_life_games.value == 2.0


def test_initial_only_before_first_test_season(root: Path) -> None:
    a = params_for(FIRST_TRAIN + 1, root)
    assert a.window is None
    assert a.params == load_params()


def test_missing_window_file_means_initial_and_fit_keys_raise(root: Path) -> None:
    a = params_for(2024, root)  # tv1 has no S2024 file
    assert a.window is None
    with pytest.raises(NotImplementedError, match="OFF-12"):
        a.extra("fit:OFF-12/team_ypc_k", "OFF-12")


def test_fit_key_listed_missing_raises_with_reason(root: Path) -> None:
    with pytest.raises(NotImplementedError, match="planted: no data"):
        params_for(2023, root).extra("fit:COA-02/p_go_intercept", "COA-02")


def test_holdout_season_refused(root: Path) -> None:
    with pytest.raises(HoldoutReadError, match="BT-07b"):
        params_for(HOLDOUT, root)


def test_no_active_version_means_initial(tmp_path: Path) -> None:
    a = params_for(2023, tmp_path / "nothing_here")
    assert a.window is None and a.params == load_params()


def test_active_version_without_folder_fails(tmp_path: Path) -> None:
    r = tmp_path / "pf"
    r.mkdir()
    (r / "active.yaml").write_text("fit_version: nope\n", encoding="utf-8")
    with pytest.raises(FitVersionMissing, match="nope"):
        params_for(2023, r)


@pytest.mark.parametrize(
    ("change", "match"),
    [
        (lambda b: b["seasons"].append(2023), "test season"),
        (lambda b: b["seasons"].append(HOLDOUT), "BT-07b"),
        (lambda b: b.update(attribution="nflverse"), "attribution"),
        (
            lambda b: b["values"]["conventions.g3_usage_half_life_games"].update(status="initial"),
            "status",
        ),
        (lambda b: b["values"].update({"offense.no_such_key": _entry(1.0, [2016])}), "no_such_key"),
        (
            lambda b: b["values"]["conventions.g3_usage_half_life_games"].update(seasons=[2023]),
            "outside",
        ),
    ],
)
def test_bad_fitted_file_rejected(root: Path, change: Any, match: str) -> None:
    p = root / "tv1" / "S2023.yaml"
    body = yaml.safe_load(p.read_text(encoding="utf-8"))
    change(body)
    p.write_text(yaml.safe_dump(body), encoding="utf-8")
    with pytest.raises((ValueError, HoldoutReadError), match=match):
        params_for(2023, root)


def test_use_season_drives_module_proxies(root: Path) -> None:
    from ge.metrics import conventions as cv

    conv = group_proxy("conventions")
    with use_fitted_root(root):
        with use_season(2023):
            assert conv.g3_usage_half_life_games.value == 4.5
            assert cv.half_life("usage") == 4.5
            with use_season(HOLDOUT + 1):
                assert cv.half_life("usage") == 2.0
            assert cv.half_life("usage") == 4.5
        with use_season(FIRST_TRAIN + 1):
            assert cv.half_life("usage") == INITIAL_USAGE_H
    assert cv.half_life("usage") == INITIAL_USAGE_H


def test_initial_file_never_written(root: Path) -> None:
    before = hashlib.sha256(PARAMS_PATH.read_bytes()).hexdigest()
    params_for(2023, root)
    params_for(HOLDOUT + 1, root)
    assert hashlib.sha256(PARAMS_PATH.read_bytes()).hexdigest() == before
