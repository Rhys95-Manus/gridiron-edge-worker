"""PRJ-01b market anchoring: two offensive offsets solved so the interpolated median margin and
total are within 0.25 points of half-point targets, with common random numbers (the game's
fixed seed in every iteration). Synthetic game; slopes and targets are test settings."""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from ge.models.sim import arrays as A
from ge.models.sim.anchor import AnchorFailed, anchor
from ge.models.sim.arrays import GameArrays
from ge.models.sim.median import interpolated_median
from tests.phase5.sim_synth import synthetic_game, synthetic_league

N = 20_000  # PRJ-02's runs per game: the interpolated median's MC error is about 0.13 points
BASE = synthetic_game()


def make(d_home: float, d_away: float) -> GameArrays:
    """Offsets move each offense's tilt shifts with test slopes (logit / yards per EPA)."""
    t = BASE.team.copy()
    for s, d in ((0, d_home), (1, d_away)):
        t[s, A.T_CMP_SHIFT] += 1.0 * d
        t[s, A.T_YAC_SHIFT] += 3.0 * d
        t[s, A.T_YPC_SHIFT] += 4.0 * d
    return dataclasses.replace(BASE, team=t)


# half-point lines near the synthetic game's baseline (margin about 0, total about 91)
@pytest.mark.parametrize(("margin", "total"), [(3.5, 90.5), (-6.5, 94.5)])
def test_reaches_half_point_lines_within_quarter_point(margin: float, total: float) -> None:
    league = synthetic_league()
    res = anchor(make, league, target_margin=margin, target_total=total, n_runs=N,
                 game_id="G_ANCHOR", model_version="m1")  # fmt: skip
    pts = res.result.team[:, :, A.R_POINTS].astype(np.int64)
    m = interpolated_median(pts[:, 0] - pts[:, 1])
    t = interpolated_median(pts.sum(axis=1))
    assert abs(m - margin) <= 0.25 and abs(t - total) <= 0.25, (m, t, res.iterations)
    assert res.median_margin == pytest.approx(m) and res.median_total == pytest.approx(t)


def test_unreachable_target_raises() -> None:
    def stuck(d_home: float, d_away: float) -> GameArrays:
        return BASE  # offsets change nothing

    with pytest.raises(AnchorFailed, match="PRJ-01b"):
        anchor(stuck, synthetic_league(), target_margin=10.5, target_total=60.5, n_runs=500,
               game_id="G_ANCHOR", model_version="m1")  # fmt: skip
