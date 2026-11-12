"""MTC-05 / ENV v5 weather fit (Phase 5 checklist): planted effects on synthetic plays are
recovered within 3 SE; a planted zero effect comes out no-signal (95% interval includes 0).
Every number is a synthetic test setting, not a weather or football fact."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from ge.fit.weather import (
    OUTCOME_FACTORS,
    WEATHER_FACTORS,
    WindGustsMasked,
    factor_correlations,
    fit_weather_effects,
)

SEASONS = (2016, 2017, 2018)


def _plays(
    effects: dict[str, float], seed: int, games: int = 1_000, per_game: int = 40
) -> pl.DataFrame:
    """Synthetic pass plays; the five weather values are drawn once per team-game (they are
    game-window values), independently of each other."""
    rng = np.random.default_rng(seed)
    parts = []
    for i, season in enumerate(SEASONS):
        game_cols = {
            "precipitation": rng.exponential(1.0, games) * (rng.random(games) < 0.2),
            "snowfall": rng.exponential(1.0, games) * (rng.random(games) < 0.1),
            "wind_speed": rng.gamma(4.0, 4.0, games),
            "wind_gusts": rng.gamma(5.0, 6.0, games),
            "temperature": rng.normal(10.0, 10.0, games),
        }
        cols = {f: np.repeat(v, per_game) for f, v in game_cols.items()}
        eta = 0.5 + 0.1 * i + sum(effects.get(f, 0.0) * cols[f] for f in cols)
        y = (rng.random(eta.size) < 1 / (1 + np.exp(-eta))).astype(float)
        team_game = season * 10_000 + np.repeat(np.arange(games), per_game)
        parts.append(
            pl.DataFrame({"season": [season] * eta.size, "team_game": team_game, **cols, "y": y})
        )
    return pl.concat(parts)


def test_factors_are_the_five_game_window_values() -> None:
    assert set(WEATHER_FACTORS) == {
        "precipitation",
        "snowfall",
        "wind_speed",
        "wind_gusts",
        "temperature",
    }


def test_outcome_factor_lists() -> None:
    """MTC-05 as ruled 2026-10-24 (after the B4 stop): completion and field-goal make keep gusts
    and drop wind speed; deep-attempt share keeps all five; precipitation does not act on
    field goals (spec)."""
    assert set(OUTCOME_FACTORS["completion"]) == {
        "precipitation",
        "snowfall",
        "wind_gusts",
        "temperature",
    }
    assert set(OUTCOME_FACTORS["deep_attempt"]) == set(WEATHER_FACTORS)
    assert set(OUTCOME_FACTORS["fg_make"]) == {"snowfall", "wind_gusts", "temperature"}


def test_planted_effect_recovered_within_3_se() -> None:
    planted = {"wind_gusts": -0.015, "precipitation": -0.15}
    fits = fit_weather_effects(_plays(planted, seed=11), outcome="completion")
    for factor, beta in planted.items():
        f = fits[factor]
        assert abs(f.coef - beta) < 3 * f.se, (factor, f.coef, f.se)
        assert not f.no_signal


def test_pairwise_factor_correlations_are_reported() -> None:
    """Ruling B4: the report shows the correlation between every pair of factors."""
    plays = _plays({}, seed=13)
    corr = factor_correlations(plays)
    assert len(corr) == 10  # 5 factors, every pair once
    w = plays["wind_speed"].to_numpy()
    g = plays["wind_gusts"].to_numpy()
    assert corr[("wind_speed", "wind_gusts")] == pytest.approx(float(np.corrcoef(w, g)[0, 1]))


def test_wind_and_gusts_hidden_by_joint_fit_stops() -> None:
    """Ruling B4: wind and gusts both no-signal jointly while either is significant alone means
    stop and ask. Here gusts = wind + small noise and wind has a real effect, so the joint fit
    splits it between two near-collinear terms. Deep-attempt share is the outcome that still
    carries both terms (ruling 2026-10-24)."""
    rng = np.random.default_rng(14)
    plays = _plays({}, seed=14)
    gusts = plays["wind_speed"].to_numpy() * 1.5 + rng.normal(0, 0.05, plays.height)
    eta = 0.5 - 0.01 * plays["wind_speed"].to_numpy()
    y = (rng.random(plays.height) < 1 / (1 + np.exp(-eta))).astype(float)
    plays = plays.with_columns(pl.Series("wind_gusts", gusts), pl.Series("y", y))
    with pytest.raises(WindGustsMasked):
        fit_weather_effects(plays, outcome="deep_attempt")


def test_planted_zero_effect_is_no_signal() -> None:
    fits = fit_weather_effects(_plays({"wind_gusts": -0.015}, seed=12), outcome="completion")
    f = fits["temperature"]
    assert f.no_signal
    assert f.applied == 0.0  # BT-02: a no-signal effect contributes zero
    assert fits["wind_gusts"].applied == pytest.approx(fits["wind_gusts"].coef)
