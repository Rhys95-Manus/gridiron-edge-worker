"""PRJ-01a reads the G6 penalty and the efficiency and usage half-lives from the active
Phase 3e fit for the season's window, never from params.yaml (prj_01_model_half_life_games
was retired 2026-10-12), and never refits the penalty (BUILD_PLAN Phase 4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ge.config import load_params
from ge.metrics.coaching import CoachingRegistry
from ge.models.ratings import load_window_consts, ratings_for_game, ratings_params
from ge.store.holdout import HoldoutReadError
from tests.phase3.conftest import MAIN_WEEK, STORE, first_game
from tests.phase4.conftest import CONST_SETTINGS, FIT_SETTINGS


@pytest.mark.usefixtures("fit_env")
@pytest.mark.parametrize("window", sorted(FIT_SETTINGS))
def test_each_season_reads_its_own_window(window: str) -> None:
    got = ratings_params(int(window[1:]))
    s = FIT_SETTINGS[window]
    assert (got.window, got.fit_version) == (window, "t1")
    assert (got.penalty, got.h_efficiency, got.h_usage) == (s["penalty"], s["h_eff"], s["h_usage"])


@pytest.mark.usefixtures("fit_env")
@pytest.mark.parametrize("season", [2019, 2022])
def test_no_fit_raises(season: int) -> None:
    """2019 is before the first test season; S2022 has no file in the test root."""
    with pytest.raises(NotImplementedError, match="PRJ-01a"):
        ratings_params(season)


@pytest.mark.usefixtures("fit_env")
def test_holdout_raises() -> None:
    with pytest.raises(HoldoutReadError):
        ratings_params(int(load_params().backtest.bt_01_holdout_season.value))


def test_no_half_life_setting_in_params_yaml() -> None:
    fields = set(type(load_params().projection).model_fields)
    assert not {f for f in fields if "half_life" in f}, fields


def test_window_consts_read_per_season(ratings_root: Path) -> None:
    got = load_window_consts(2024, ratings_root)
    assert got.window == "S2024"
    assert dict(got.coa07) == {t: CONST_SETTINGS[t] for t in ("home", "rest", "travel", "tz")}
    assert (got.c, got.league_epa, got.league_ppd, got.league_drives) == (
        CONST_SETTINGS["c"],
        CONST_SETTINGS["league_epa"],
        CONST_SETTINGS["league_ppd"],
        CONST_SETTINGS["league_drives"],
    )
    with pytest.raises(NotImplementedError, match="PRJ-01a"):
        load_window_consts(2022, ratings_root)
    with pytest.raises(HoldoutReadError):
        load_window_consts(int(load_params().backtest.bt_01_holdout_season.value), ratings_root)


@pytest.mark.usefixtures("fit_env")
def test_penalty_is_never_refit(
    monkeypatch: pytest.MonkeyPatch, ratings_root: Path, registry: CoachingRegistry
) -> None:
    import ge.fit.ridge_cv as cv

    def refit(*args: object, **kwargs: object) -> None:
        raise AssertionError("PRJ-01a must not cross-validate the G6 penalty")

    monkeypatch.setattr(cv, "g6_cv_losses", refit)
    monkeypatch.setattr(cv, "choose_penalty", refit)
    got = ratings_for_game(
        first_game(MAIN_WEEK), root=STORE, ratings_root=ratings_root, registry=registry
    )
    assert got.params.penalty == FIT_SETTINGS["S2024"]["penalty"]
