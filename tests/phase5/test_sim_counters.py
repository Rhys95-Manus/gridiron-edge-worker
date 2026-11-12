"""PRJ-02 diagnostic counters (approved 2026-10-27, no model change): air yards and YAC by
depth band, goal-line clips, air-yard redraws, and 3rd downs by distance and play type. Each
must agree with the counters it splits, run by run, on the synthetic game."""

from __future__ import annotations

import numpy as np
import pytest

from ge.models.sim import arrays as A
from ge.models.sim import backtest
from ge.models.sim.engine import SimResult, simulate, togo_bin
from tests.phase5.sim_synth import synthetic_game, synthetic_league

N = 4000


@pytest.fixture(scope="module")
def base() -> SimResult:
    return simulate(synthetic_game(), synthetic_league(), N, game_id="G_TEST", model_version="m1")


def _t(r: SimResult, idx: int, n: int = 1) -> np.ndarray:
    return r.team[:, :, idx : idx + n].astype(np.int64)


@pytest.mark.parametrize(
    ("togo", "b"),
    [(1.0, 0), (0.5, 0), (2.0, 1), (3.0, 2), (4.0, 3), (6.0, 3), (7.0, 4), (10.0, 4),
     (11.0, 5), (25.0, 5)],
)  # fmt: skip
def test_togo_bins(togo: float, b: int) -> None:
    """Bins 1, 2, 3, 4-6, 7-10, 11+ (as in the xpass and 3rd-down tables)."""
    assert togo_bin(togo) == b


def test_third_down_splits_add_up(base: SimResult) -> None:
    nb = A.THIRD_BINS
    att = _t(base, A.R_THIRD_ATT_RUN0, nb) + _t(base, A.R_THIRD_ATT_PASS0, nb)
    conv = _t(base, A.R_THIRD_CONV_RUN0, nb) + _t(base, A.R_THIRD_CONV_PASS0, nb)
    np.testing.assert_array_equal(att.sum(axis=2), _t(base, A.R_THIRD_ATT)[:, :, 0])
    np.testing.assert_array_equal(conv.sum(axis=2), _t(base, A.R_THIRD_CONV)[:, :, 0])
    assert np.all(_t(base, A.R_THIRD_CONV_RUN0, nb) <= _t(base, A.R_THIRD_ATT_RUN0, nb))
    assert np.all(_t(base, A.R_THIRD_CONV_PASS0, nb) <= _t(base, A.R_THIRD_ATT_PASS0, nb))
    a, c = att.sum(axis=(0, 1)), conv.sum(axis=(0, 1))
    assert a.min() > 0
    assert c[0] / a[0] > c[4] / a[4]  # 3rd-and-1 converts more often than 3rd-and-7-10


def test_band_air_yards_within_band(base: SimResult) -> None:
    """Behind the line: air <= -1 on every attempt; short: 0-9 (never capped: the cap is the
    end-zone back line, at least 11 yards away). Tenths of a yard."""
    att = _t(base, A.R_ATT_B0, 4)
    air = _t(base, A.R_AIR_ATT_B0, 4)
    assert np.all(air[:, :, 0] <= -10 * att[:, :, 0])
    assert np.all((air[:, :, 1] >= 0) & (air[:, :, 1] <= 90 * att[:, :, 1]))
    m = air.sum(axis=(0, 1)) / att.sum(axis=(0, 1)) / 10.0
    assert 10.0 <= m[2] < 20.0 and m[3] >= 18.0, m


def test_completion_air_and_yac_reproduce_band_yards(base: SimResult) -> None:
    """Per completion: yards = round(air + YAC) (stochastic, unbiased), less any yards past
    the goal line (clips). Per run within one yard per completion; over all runs within 0.5%."""
    cmp_ = _t(base, A.R_CMP_B0, 4).sum(axis=2)
    yds = _t(base, A.R_YDS_B0, 4).sum(axis=2)
    raw = (_t(base, A.R_AIR_CMP_B0, 4) + _t(base, A.R_YAC_CMP_B0, 4)).sum(axis=2) / 10.0
    clip = _t(base, A.R_GL_CLIP_YDS)[:, :, 0]
    gap = raw - clip - yds
    assert np.all(np.abs(gap) <= 1.1 * cmp_ + 1e-9)
    assert abs(gap.sum()) <= 0.005 * yds.sum()


def test_clips_and_redraws_are_bounded(base: SimResult) -> None:
    clips, clip_yds = _t(base, A.R_GL_CLIPS)[:, :, 0], _t(base, A.R_GL_CLIP_YDS)[:, :, 0]
    assert np.all(clips <= _t(base, A.R_COMP)[:, :, 0])
    assert np.all(clip_yds >= clips)  # a clip removes at least one whole yard
    assert np.all((clip_yds > 0) == (clips > 0))
    assert clips.sum() > 0  # the synthetic game reaches the red zone
    redraws, caps = _t(base, A.R_AIR_REDRAWS)[:, :, 0], _t(base, A.R_AIR_CAPS)[:, :, 0]
    assert np.all(caps <= redraws)
    assert np.all(redraws <= _t(base, A.R_PASS_ATT)[:, :, 0])


def test_summary_has_the_diagnostic_columns() -> None:
    cols = backtest.SUMMARY_COLUMNS
    for side in ("home", "away"):
        for b in range(4):
            for k in ("air_att", "air_cmp", "yac_cmp"):
                assert f"{side}_{k}_b{b}_x10" in cols
        for k in ("gl_clips", "gl_clip_yds", "air_redraws", "air_caps"):
            assert f"{side}_{k}" in cols
        for t in range(A.THIRD_BINS):
            for k in ("third_att_run", "third_conv_run", "third_att_pass", "third_conv_pass"):
                assert f"{side}_{k}{t}" in cols
