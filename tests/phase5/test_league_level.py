"""PRJ-02 league level: h_L is chosen per window from the params grid by predicting each
training week's league points per team-game with the 0.5^(w / h_L)-weighted mean of the earlier
weeks, and taking the h_L with the smallest mean squared error. Weeks here all have the same
number of team-games, so the test does not depend on whether weeks are weighted by team-games;
and a common factor on every weight cancels in a weighted mean, so it does not depend on
whether the latest earlier week has w = 0 or w = 1. Values are synthetic test settings."""

from __future__ import annotations

import numpy as np
import pytest

from ge.fit.league_level import H_L_GRID, choose_league_half_life

SPEC_GRID = (1.5, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0, 24.0, 32.0, 48.0)


def _oracle_mse(points: np.ndarray, h: float) -> float:
    errs = []
    for t in range(1, len(points)):
        w = 0.5 ** (np.arange(t, 0, -1) / h)  # oldest earlier week first
        errs.append(points[t] - float(np.dot(w, points[:t]) / w.sum()))
    return float(np.mean(np.square(errs)))


def test_grid_is_the_spec_grid() -> None:
    assert tuple(H_L_GRID) == SPEC_GRID


@pytest.mark.parametrize("seed", [1, 2])
def test_choice_matches_independent_oracle(seed: int) -> None:
    rng = np.random.default_rng(seed)
    weeks = 120
    drift = np.cumsum(rng.normal(0, 0.15, weeks))  # a slowly moving league level
    points = 22.0 + drift + rng.normal(0, 1.0, weeks)
    team_games = np.full(weeks, 32)
    h, losses = choose_league_half_life(points, team_games)
    oracle = {g: _oracle_mse(points, g) for g in SPEC_GRID}
    assert losses == pytest.approx(oracle, rel=1e-9)
    assert h == min(oracle, key=lambda g: oracle[g])


def test_level_shift_picks_short_and_stationary_picks_long() -> None:
    rng = np.random.default_rng(3)
    shifted = np.r_[np.full(60, 20.0), np.full(60, 26.0), np.full(60, 18.0)]
    shifted = shifted + rng.normal(0, 0.2, shifted.size)
    h_shift, _ = choose_league_half_life(shifted, np.full(shifted.size, 32))
    flat = 22.0 + rng.normal(0, 2.0, 180)
    h_flat, _ = choose_league_half_life(flat, np.full(flat.size, 32))
    assert h_shift < h_flat
