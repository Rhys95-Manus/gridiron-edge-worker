"""Phase 4 fixtures: test-only fitted files and window constants, and a synthetic COA-01
registry, for ratings built from the phase3 real-data fixture store (tests/phase3/fixtures;
2023 in full, 2024 weeks 1-8).

Every number written here is a test setting chosen for the test, not a fitted value and not a
football fact. The repo's own config/params_fitted and config/ratings_fitted are never read by
these fixtures."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from pathlib import Path

import pytest
import yaml

from ge.config import ATTRIBUTION, use_fitted_root
from ge.metrics.coaching import CoachingRegistry, load_registry
from ge.metrics.conventions import G6_PENALTY_KEY
from ge.models.ratings import C_KEY, COA07_KEYS, LEAGUE_KEYS, SE_SUFFIX
from tests.phase3.conftest import STORE, store_table
from tests.phase3.registry_rows import staff, write

_HERE = Path(__file__).parent
FIRST_TRAINING_SEASON = 2016

# Test settings for the Phase 3e values the ratings read, per window.
FIT_SETTINGS: dict[str, dict[str, float]] = {
    "S2023": {"penalty": 200.0, "h_eff": 6.0, "h_usage": 4.0},
    "S2024": {"penalty": 300.0, "h_eff": 8.0, "h_usage": 6.0},
}
# Test settings for the Phase 4 window constants. Travel and time zone are zero so the golden
# test's oracle needs only the schedules (coa07_features is checked against coa_07 apart).
CONST_SETTINGS: dict[str, float] = {
    "home": 0.02,
    "rest": 0.003,
    "travel": 0.0,
    "tz": 0.0,
    "c": 6.0,
    "league_epa": 0.01,
    "league_ppd": 2.0,
    "league_drives": 11.0,
}
CONST_SE = 0.001


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if _HERE in Path(item.fspath).parents:
            item.add_marker(pytest.mark.phase4)


def _window(window: str) -> tuple[int, list[int]]:
    test_season = int(window[1:])
    return test_season, list(range(FIRST_TRAINING_SEASON, test_season))


def _value(spec_id: str, value: float, seasons: list[int]) -> dict[str, object]:
    return {
        "spec_id": spec_id,
        "status": "fitted",
        "value": float(value),
        "method": "test setting (tests/phase4/conftest.py)",
        "seasons": seasons,
        "n": 1,
        "initial_value": None,
    }


def _file(window: str, version: str, values: Mapping[str, object]) -> dict[str, object]:
    test_season, seasons = _window(window)
    return {
        "fit_version": version,
        "window": window,
        "test_season": test_season,
        "seasons": seasons,
        "data_as_of": "2026-10-12T00:00:00+00:00",
        "data_digest": "test",
        "code_commit": "test",
        "attribution": ATTRIBUTION,
        "values": dict(values),
        "missing": {},
    }


def _dump(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8", newline="\n")


def write_fitted_root(root: Path, settings: Mapping[str, Mapping[str, float]]) -> Path:
    """A Phase 3e fitted root (active.yaml + one file per window) with test settings."""
    version = "t1"
    for window, s in settings.items():
        _, seasons = _window(window)
        values = {
            "conventions.g3_efficiency_half_life_games": _value("G3", s["h_eff"], seasons),
            "conventions.g3_usage_half_life_games": _value("G3", s["h_usage"], seasons),
            G6_PENALTY_KEY: _value("G6", s["penalty"], seasons),
        }
        _dump(root / version / f"{window}.yaml", _file(window, version, values))
    _dump(root / "active.yaml", {"fit_version": version})
    return root


def write_ratings_root(root: Path, windows: list[str], consts: Mapping[str, float]) -> Path:
    """A Phase 4 ratings root (active.yaml + one file per window) with test settings."""
    version = "rt1"
    for window in windows:
        _, seasons = _window(window)
        values: dict[str, object] = {}
        for term, key in COA07_KEYS.items():
            values[key] = _value("COA-07", consts[term], seasons)
            values[key + SE_SUFFIX] = _value("COA-07", CONST_SE, seasons)
        values[C_KEY] = _value("PRJ-01", consts["c"], seasons)
        values[C_KEY + SE_SUFFIX] = _value("PRJ-01", CONST_SE, seasons)
        for name, key in LEAGUE_KEYS.items():
            values[key] = _value("PRJ-01", consts[name], seasons)
        _dump(root / version / f"{window}.yaml", _file(window, version, values))
    _dump(root / "active.yaml", {"fit_version": version})
    return root


@pytest.fixture(scope="session")
def fitted_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return write_fitted_root(tmp_path_factory.mktemp("fitted"), FIT_SETTINGS)


@pytest.fixture(scope="session")
def ratings_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return write_ratings_root(
        tmp_path_factory.mktemp("ratings"), list(FIT_SETTINGS), CONST_SETTINGS
    )


@pytest.fixture
def fit_env(fitted_root: Path) -> Iterator[Path]:
    """Ratings read the test fitted root, never config/params_fitted."""
    with use_fitted_root(fitted_root):
        yield fitted_root


@pytest.fixture(scope="session")
def registry(tmp_path_factory: pytest.TempPathFactory) -> CoachingRegistry:
    """Placeholder COA-01 rows, not real coaches: every fixture team keeps one play-caller
    from before 2023, so G4 decides changes from the QB rule alone."""
    sched = store_table("schedules", 2024)
    teams = sorted(set(sched["home_team"].to_list()) | set(sched["away_team"].to_list()))
    path = tmp_path_factory.mktemp("registry") / "coaching_registry.csv"
    return load_registry(write(path, [r for t in teams for r in staff(t, "2022-01-01")]))


__all__ = ["STORE"]
