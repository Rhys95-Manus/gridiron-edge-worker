"""PRJ-02 play loop on a synthetic game (tests/phase5/sim_synth.py): determinism (E12),
internal consistency of every run, planted pace / PROE / shares recovered, the red-zone share
switch, the per-run availability draw with redistribution (PLY-14 / PLY-15, E6), and overtime
(ties in the regular season only). Tolerances are Monte Carlo errors, stated per test."""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from ge.models.sim import arrays as A
from ge.models.sim.engine import SimResult, band_probs, simulate
from tests.phase5.sim_synth import synthetic_game, synthetic_league

N = 4000


@pytest.fixture(scope="module")
def league():  # type: ignore[no-untyped-def]
    return synthetic_league()


@pytest.fixture(scope="module")
def base(league) -> SimResult:  # type: ignore[no-untyped-def]
    return simulate(synthetic_game(), league, N, game_id="G_TEST", model_version="m1")


def test_same_inputs_give_identical_bytes(league, base: SimResult) -> None:  # type: ignore[no-untyped-def]
    again = simulate(synthetic_game(), league, N, game_id="G_TEST", model_version="m1")
    assert again.team.tobytes() == base.team.tobytes()
    assert again.player.tobytes() == base.player.tobytes()
    assert again.first_td.tobytes() == base.first_td.tobytes()


def test_serial_and_parallel_give_identical_bytes(league, base: SimResult) -> None:  # type: ignore[no-untyped-def]
    serial = simulate(synthetic_game(), league, N, game_id="G_TEST", model_version="m1",
                      parallel=False)  # fmt: skip
    assert serial.team.tobytes() == base.team.tobytes()
    assert serial.player.tobytes() == base.player.tobytes()


def test_different_seed_gives_different_output(league, base: SimResult) -> None:  # type: ignore[no-untyped-def]
    other = simulate(synthetic_game(), league, N, game_id="G_TEST", model_version="m2")
    assert other.team.tobytes() != base.team.tobytes()


def test_every_run_is_internally_consistent(base: SimResult) -> None:
    rec_yds = base.player[:, :, :, A.S_REC_YDS].sum(axis=2)
    pass_yds = base.player[:, :, :, A.S_PASS_YDS].sum(axis=2)
    np.testing.assert_array_equal(rec_yds, base.team[:, :, A.R_PASS_YDS])
    np.testing.assert_array_equal(pass_yds, base.team[:, :, A.R_PASS_YDS])
    tds = (base.player[:, :, :, A.S_RUSH_TD] + base.player[:, :, :, A.S_REC_TD]).sum(axis=2)
    np.testing.assert_array_equal(tds, base.team[:, :, A.R_OFF_TD])
    rush = base.player[:, :, :, A.S_RUSH_YDS].sum(axis=2)
    np.testing.assert_array_equal(rush, base.team[:, :, A.R_RUSH_YDS])
    assert np.all(base.team[:, :, A.R_POINTS] >= 6 * base.team[:, :, A.R_OFF_TD])
    rec = base.player[:, :, :, A.S_REC].sum(axis=2)
    cmp_ = base.player[:, :, :, A.S_PASS_CMP].sum(axis=2)
    np.testing.assert_array_equal(rec, cmp_)


def test_first_td_scorer_is_recorded_when_any_td(base: SimResult) -> None:
    any_td = base.team[:, :, A.R_OFF_TD].sum(axis=1) > 0
    assert np.all(base.first_td[any_td, 0] >= 0)


def test_faster_pace_gives_more_plays(league) -> None:  # type: ignore[no-untyped-def]
    """Planted pace: 20 vs 36 seconds per running-clock snap (test settings)."""
    fast = simulate(synthetic_game(pace=20.0), league, N, game_id="G_TEST", model_version="m1")
    slow = simulate(synthetic_game(pace=36.0), league, N, game_id="G_TEST", model_version="m1")
    f = fast.team[:, :, A.R_PLAYS].mean()
    s = slow.team[:, :, A.R_PLAYS].mean()
    assert f > 1.2 * s, (f, s)


def test_planted_proe_moves_pass_rate(league) -> None:  # type: ignore[no-untyped-def]
    """PROE adds to xpass (here a constant), so the dropback rate rises by 0.10 (OFF-05). With
    about 260,000 plays per arm, 4 SE of a difference of proportions is under 0.01."""
    a = simulate(synthetic_game(proe=0.0), league, N, game_id="G_TEST", model_version="m1")
    b = simulate(synthetic_game(proe=0.10), league, N, game_id="G_TEST", model_version="m1")

    def rate(r: SimResult) -> float:
        return float(r.team[:, :, A.R_PASS_PLAYS].sum() / r.team[:, :, A.R_PLAYS].sum())

    assert rate(b) - rate(a) == pytest.approx(0.10, abs=0.01)


def test_target_shares_recovered(base: SimResult) -> None:
    """Zone shares equal overall shares in the synthetic game, so simulated target shares match
    PLY-03 (pooled over runs; about 130,000 targets per side, Monte Carlo SE < 0.002)."""
    from tests.phase5.sim_synth import TARGETS

    t = base.player[:, 0, :, A.S_TARGETS].sum(axis=0)
    share = t / t.sum()
    zone_aware = np.array(TARGETS) / np.sum(TARGETS)
    np.testing.assert_allclose(share, zone_aware, atol=0.01)


def test_red_zone_switch(league) -> None:  # type: ignore[no-untyped-def]
    """WR3 has a 0.1% overall target share but all the PLY-06 opportunity share inside the 20
    (a zone share is split into targets and carries by each player's own overall mix, and a
    draw with no positive zone weight falls back to the overall shares). So nearly every target
    he gets is inside the 20: his share of all targets is far above 0.1% and below half."""
    g = synthetic_game()
    p = g.player.copy()
    p[:, 6, A.P_TARGET] = 0.001
    p[:, :, [A.P_Z20, A.P_Z10, A.P_Z5]] = 0.0
    p[:, 6, [A.P_Z20, A.P_Z10, A.P_Z5]] = 1.0
    r = simulate(dataclasses.replace(g, player=p), league, N, game_id="G_TEST",
                 model_version="m1")  # fmt: skip
    wr3 = r.player[:, 0, 6, A.S_TARGETS].sum()
    total = r.player[:, 0, :, A.S_TARGETS].sum()
    assert 0.02 * total < wr3 < 0.5 * total


def test_questionable_player_plays_at_his_rate_and_sits_cleanly(league) -> None:  # type: ignore[no-untyped-def]
    """WR1 plays with probability 0.6. Over 4,000 runs the SE is 0.008; 4 SE = 0.031. In runs
    he sits he has no stats, and his team's targets are unchanged on average (redistributed)."""
    g = synthetic_game()
    p = g.player.copy()
    p[:, 4, A.P_AVAIL] = 0.6
    r = simulate(dataclasses.replace(g, player=p), league, N, game_id="G_TEST",
                 model_version="m1")  # fmt: skip
    played = r.player[:, 0, 4, A.S_PLAYED]
    assert played.mean() == pytest.approx(0.6, abs=0.031)
    sat = played == 0
    assert r.player[sat, 0, 4, A.S_TARGETS].sum() == 0
    t_sat = r.player[sat, 0, :, A.S_TARGETS].sum(axis=1).mean()
    t_played = r.player[~sat, 0, :, A.S_TARGETS].sum(axis=1).mean()
    assert t_sat == pytest.approx(t_played, rel=0.05)


def test_small_yard_shifts_are_not_rounded_away(league) -> None:  # type: ignore[no-untyped-def]
    """A +0.2 yards-per-carry shift must raise mean rush yards per carry by about 0.2 (stochastic
    rounding), not by 0 (deterministic rounding swallows shifts below half a yard). About
    100,000 carries per arm: 4 SE of the difference is under 0.06 yards."""
    g = synthetic_game()
    t = g.team.copy()
    t[:, A.T_YPC_SHIFT] = 0.2
    a = simulate(g, league, N, game_id="G_TEST", model_version="m1")
    b = simulate(dataclasses.replace(g, team=t), league, N, game_id="G_TEST", model_version="m1")

    def ypc(r: SimResult) -> float:
        qb_scr = r.player[:, :, :, A.S_RUSH_ATT].sum()
        return float(r.player[:, :, :, A.S_RUSH_YDS].sum() / qb_scr)

    assert ypc(b) - ypc(a) == pytest.approx(0.2, abs=0.06)


def test_compiled_logit_matches_predict_with_interactions() -> None:
    """The play loop's compiled model (CompiledLogit + _eta) gives the same value as
    ge.fit.distill.predict, including the per-down distance terms (ruling 2026-10-25)."""
    import polars as pl

    from ge.fit.distill import predict
    from ge.models.sim.arrays import compile_logit
    from ge.models.sim.engine import _eta, _logit_arrays

    coef = {
        "intercept": 0.3,
        "down=2.0": 0.2,
        "down=3.0": 0.5,
        "down=4.0": 0.7,
        "ydstogo|down=1.0": -0.1,
        "ydstogo^2|down=1.0": 0.002,
        "ydstogo|down=3.0": 0.15,
        "ydstogo^2|down=3.0": -0.004,
        "yardline_100": -0.01,
        "yardline_100^2": 0.0001,
        "wp": 0.4,
    }
    m = _logit_arrays(compile_logit(coef))
    rng = np.random.default_rng(5)
    rows = pl.DataFrame(
        {
            "down": rng.integers(1, 5, 50).astype(float),
            "ydstogo": rng.integers(1, 20, 50).astype(float),
            "yardline_100": rng.integers(1, 99, 50).astype(float),
            "wp": rng.uniform(0, 1, 50),
        }
    )
    want = predict(coef, rows)
    for i, r in enumerate(rows.iter_rows(named=True)):
        x = np.zeros(A.NF)
        x[A.F_DOWN], x[A.F_YDSTOGO], x[A.F_YL], x[A.F_WP] = (
            r["down"], r["ydstogo"], r["yardline_100"], r["wp"]
        )  # fmt: skip
        got = 1 / (1 + np.exp(-_eta(x, m)))
        assert got == pytest.approx(want[i], rel=1e-12)


def test_band_rule_is_log5() -> None:
    """Ruling 2026-10-25 (replacing C5): band probability proportional to passer share x target
    share / league share, renormalized. League-average passer and target give league shares.
    Hand example: passer (0.2, 0.5, 0.2, 0.1), target (0.1, 0.5, 0.2, 0.2), league (0.2, 0.5,
    0.2, 0.1): products / league = (0.1, 0.5, 0.2, 0.2), sum 1.0 -> (0.1, 0.5, 0.2, 0.2)."""
    league_share = np.array([0.2, 0.5, 0.2, 0.1])
    out = np.zeros(4)
    band_probs(league_share.copy(), league_share.copy(), league_share, out)
    np.testing.assert_allclose(out, league_share)
    band_probs(np.array([0.2, 0.5, 0.2, 0.1]), np.array([0.1, 0.5, 0.2, 0.2]), league_share, out)
    np.testing.assert_allclose(out, [0.1, 0.5, 0.2, 0.2])
    band_probs(np.full(4, np.nan), np.array([0.1, 0.5, 0.2, 0.2]), league_share, out)
    np.testing.assert_allclose(out, league_share)  # no usable shares: league


def test_regular_season_can_tie_postseason_cannot(league) -> None:  # type: ignore[no-untyped-def]
    reg = simulate(synthetic_game(), league, N, game_id="G_TEST", model_version="m1")
    post = simulate(synthetic_game(postseason=True), league, N, game_id="G_TEST",
                    model_version="m1")  # fmt: skip
    diff_post = post.team[:, 0, A.R_POINTS] - post.team[:, 1, A.R_POINTS]
    assert np.all(diff_post != 0)
    assert post.ot.sum() > 0
    assert reg.ot.sum() > 0
