"""Phase 5 per-window fits that need no new design choice: the PRJ-02 league week series behind
h_L, and C8's field-goal-attempt-vs-punt logistic model (ruling 2026-10-23), weighted by the
PRJ-02 league level. Schedules and plays are synthetic placeholders, not real games."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from ge.fit.sim_fits import fit_fg_vs_punt, league_week_series, league_weights


def test_league_week_series_hand_computed() -> None:
    """Two seasons, regular-season and postseason weeks in order. Week (2016, 1): games 20-10 and
    30-14 -> 74 points / 4 team-games = 18.5. (2016, 18 postseason): 24-21 -> 22.5.
    (2017, 1): 17-3 -> 10. An unplayed game (no score) is left out."""
    sched = pl.DataFrame(
        {
            "season": [2016, 2016, 2016, 2017, 2017],
            "week": [1, 1, 18, 1, 2],
            "game_type": ["REG", "REG", "WC", "REG", "REG"],
            "home_score": [20, 30, 24, 17, None],
            "away_score": [10, 14, 21, 3, None],
        }
    )
    s = league_week_series(sched)
    assert s.select("season", "week").rows() == [(2016, 1), (2016, 18), (2017, 1)]
    assert s["points_per_team_game"].to_list() == pytest.approx([18.5, 22.5, 10.0])
    assert s["team_games"].to_list() == [4, 2, 2]
    assert s["week_index"].to_list() == [0, 1, 2]


def test_league_weights_count_weeks_before_the_target() -> None:
    """w = league weeks before the target week: the latest training week has w = 1."""
    w = league_weights(np.array([0, 1, 2]), target_index=3, h=2.0)
    assert w == pytest.approx([0.5 ** (3 / 2), 0.5 ** (2 / 2), 0.5 ** (1 / 2)])


def test_fg_vs_punt_recovers_planted_model_within_3_se() -> None:
    rng = np.random.default_rng(21)
    n = 30_000
    yardline = rng.integers(1, 100, n)
    b0, b1 = 4.0, -0.11  # synthetic: field goals near the goal line, punts far away
    p = 1 / (1 + np.exp(-(b0 + b1 * yardline)))
    plays = pl.DataFrame(
        {
            "week_index": rng.integers(0, 50, n),
            "game_id": rng.integers(0, 4_000, n),
            "yardline_100": yardline.astype(float),
            "fg_attempt": (rng.random(n) < p).astype(float),
        }
    )
    fit = fit_fg_vs_punt(plays, target_index=50, h=1e9)  # h huge: weights all ~1
    assert abs(fit.intercept - b0) < 3 * fit.intercept_se
    assert abs(fit.slope - b1) < 3 * fit.slope_se
    assert fit.events >= 200


def test_fg_vs_punt_needs_200_events() -> None:
    plays = pl.DataFrame(
        {
            "week_index": [0] * 100,
            "game_id": list(range(100)),
            "yardline_100": [30.0] * 50 + [70.0] * 50,
            "fg_attempt": [1.0] * 50 + [0.0] * 50,
        }
    )
    with pytest.raises(NotImplementedError, match="PRJ-02"):
        fit_fg_vs_punt(plays, target_index=1, h=4.0)
