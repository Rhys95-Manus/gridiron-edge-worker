"""PRJ-01b: the interpolated (mid-distribution) median s, where P(X < s) + 1/2 P(X = s) = 0.5,
interpolated linearly between whole numbers. Values are hand-computed in each docstring."""

from __future__ import annotations

import numpy as np
import pytest

from ge.models.sim.median import interpolated_median


def test_hand_computed_three_point_distribution() -> None:
    """P(0) = 0.2, P(1) = 0.3, P(2) = 0.5.
    mid(0) = 0.1, mid(1) = 0.2 + 0.15 = 0.35, mid(2) = 0.5 + 0.25 = 0.75.
    0.5 lies between mid(1) and mid(2): s = 1 + (0.5 - 0.35) / (0.75 - 0.35) = 1.375."""
    x = np.array([0] * 2 + [1] * 3 + [2] * 5)
    assert interpolated_median(x) == pytest.approx(1.375)


def test_exact_hit_returns_that_integer() -> None:
    """P(-1) = 0.25, P(0) = 0.5, P(1) = 0.25: mid(0) = 0.25 + 0.25 = 0.5, so s = 0."""
    x = np.array([-1, 0, 0, 1])
    assert interpolated_median(x) == pytest.approx(0.0)


def test_half_point_line_is_reachable() -> None:
    """P(3) = 0.4, P(4) = 0.6: mid(3) = 0.2, mid(4) = 0.4 + 0.3 = 0.7.
    s = 3 + (0.5 - 0.2) / (0.7 - 0.2) = 3.6; a plain median (4) could not be within 0.25 of 3.5
    or 3.75, the interpolated one moves continuously."""
    x = np.array([3] * 4 + [4] * 6)
    assert interpolated_median(x) == pytest.approx(3.6)


def test_gap_between_values_interpolates_across_missing_integers() -> None:
    """P(-7) = 0.3, P(3) = 0.7 (nothing in between): mid(-7) = 0.15; mid(k) = 0.3 for -6..2;
    mid(3) = 0.3 + 0.35 = 0.65. 0.5 lies between mid(2) = 0.3 and mid(3) = 0.65:
    s = 2 + (0.5 - 0.3) / (0.65 - 0.3) = 2 + 0.2 / 0.35 = 2.571428..."""
    x = np.array([-7] * 3 + [3] * 7)
    assert interpolated_median(x) == pytest.approx(2 + 0.2 / 0.35)


def test_plateau_at_one_half_takes_its_midpoint() -> None:
    """Ruling B5: P(-3) = P(5) = 0.5. mid(-3) = 0.25; mid(k) = 0.5 for k = -2..4; mid(5) = 0.75.
    The run -2..4 has midpoint 1."""
    x = np.array([-3] * 5 + [5] * 5)
    assert interpolated_median(x) == pytest.approx(1.0)


def test_rejects_non_integer_values() -> None:
    with pytest.raises(ValueError, match="PRJ-01b"):
        interpolated_median(np.array([0.5, 1.0]))
