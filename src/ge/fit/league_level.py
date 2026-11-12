"""PRJ-02 league level: choosing h_L, the recency half-life (in league weeks) of every league
distribution the simulation draws from.

For each training week, that week's league points per team-game is predicted by the weighted
mean of the earlier weeks, each earlier team-game weighted 0.5^(w / h_L) with w its league
weeks before the predicted week (ruling B6, 2026-10-23: a week counts in proportion to its
team-games). The h_L with the smallest mean squared error over the window's training weeks is
chosen. The first week has nothing earlier and is not scored."""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from ge.config import load_params

H_L_GRID: tuple[float, ...] = load_params().projection.h_l_grid()


def league_week_weights(n_earlier: int, h: float) -> npt.NDArray[np.float64]:
    """PRJ-02: 0.5^(w / h) for the n earlier weeks, oldest first (w = n .. 1)."""
    return np.asarray(0.5 ** (np.arange(n_earlier, 0, -1) / h), dtype=np.float64)


def choose_league_half_life(
    points_per_team_game: npt.ArrayLike,
    team_games: npt.ArrayLike,
    grid: tuple[float, ...] = H_L_GRID,
) -> tuple[float, dict[float, float]]:
    """PRJ-02: (chosen h_L, {h: mean squared error}) over league weeks in order."""
    y = np.asarray(points_per_team_game, dtype=np.float64)
    m = np.asarray(team_games, dtype=np.float64)
    if y.ndim != 1 or y.shape != m.shape or y.size < 2:
        raise ValueError("PRJ-02: need weekly points and team-games for at least two weeks")
    if np.any(m <= 0):
        raise ValueError("PRJ-02: every league week needs at least one team-game")
    losses: dict[float, float] = {}
    for h in grid:
        errs = np.empty(y.size - 1)
        for t in range(1, y.size):
            w = league_week_weights(t, h) * m[:t]
            errs[t - 1] = y[t] - float(np.dot(w, y[:t]) / w.sum())
        losses[h] = float(np.mean(np.square(errs)))
    best = min(grid, key=lambda h: (losses[h], h))
    return best, losses
