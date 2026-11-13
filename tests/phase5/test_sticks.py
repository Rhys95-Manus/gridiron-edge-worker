"""PRJ-02 sticks spot-short (ruling 2026-11-12, S-1). Real gains bunch one yard short of the line
to gain and dip at it; tables pooled over a distance bin cannot show that. On downs 1-3, short of
goal to go, with ydstogo between config/sim.yaml sticks.togo_min and togo_max, a designed run or a
completion that gains exactly the distance is spotted one yard short with probability q[kind].

q[kind] = 1 - O / E, clamped to [0, 1]: O = weighted count of training plays of that kind at
distance t (in range) that gained exactly t; E = sum over t of W_t x ref_t, W_t = weighted count
of plays at t, ref_t = mean over reference distances t' (in range, same distance bin as t, edges
sticks.distance_upper, |t - t'| >= sticks.min_gap) of the weighted share of plays at t' gaining
exactly t. Weights: the PRJ-02 league weights rescaled to the kind's effective sample size. E
must reach sticks.min_expected, or the fit raises. Synthetic placeholder data only."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import polars as pl
import pytest

from ge.models.sim import arrays as A
from ge.models.sim.settings import load_sim
from tests.phase5.sim_synth import (
    _air_packed,
    _logit,
    _packed,
    _run_packed,
    synthetic_game,
    synthetic_league,
)

KW = {"togo_min": 3, "togo_max": 10, "distance_upper": [2, 6, 10], "min_gap": 2,
      "min_expected": 200}  # fmt: skip


def _rows(kind: int, q: float, *, per_gain: int = 100, week: int = 0) -> pl.DataFrame:
    """Every distance 3-10 has per_gain plays at each gain 0-20 (synthetic); at distance t a
    share q of the plays gaining t is moved to t - 1."""
    out = []
    for t in range(3, 11):
        for g in range(21):
            n = per_gain
            if g == t:
                n = round(per_gain * (1 - q))
            elif g == t - 1:
                n = per_gain + round(per_gain * q)
            out += [(week, kind, float(t), float(g))] * n
    return pl.DataFrame(out, schema=["week_index", "kind", "ydstogo", "yards_gained"], orient="row")


def _both(q_run: float, q_comp: float, **kw) -> pl.DataFrame:  # type: ignore[no-untyped-def]
    return pl.concat([_rows(0, q_run, **kw), _rows(1, q_comp, **kw)])


def _fit(rows: pl.DataFrame, *, target_index: int = 1, h: float = 1e9, **over):  # type: ignore[no-untyped-def]
    from ge.fit.sim_fits import fit_sticks

    return fit_sticks(rows, target_index=target_index, h=h, **(KW | over))


# ---------------------------------------------------------------- settings and keys


def test_sticks_settings_come_from_config() -> None:
    s = load_sim().sticks
    assert (s.togo_min.value, s.togo_max.value) == (3, 10)
    assert s.distance_upper.value == [2, 6, 10]
    assert s.min_gap.value == 2
    assert s.min_expected.value == 200
    for e in (s.togo_min, s.togo_max, s.distance_upper, s.min_gap, s.min_expected):
        assert e.spec_id == "PRJ-02" and e.status == "initial"


def test_sticks_kinds_and_keys() -> None:
    assert A.STICKS_KINDS == ("run", "completion")
    assert A.sticks_key("run") == "fit:PRJ-02/sticks/run"
    assert A.sticks_key("completion") == "fit:PRJ-02/sticks/completion"


# ---------------------------------------------------------------- row set


def test_sticks_rows_keep_live_runs_and_completions_on_downs_1_to_3() -> None:
    """Designed runs (kind 0) and completions (kind 1) on downs 1-3, not goal to go
    (ydstogo < yardline_100), no penalty flag, scrimmage, not G7 garbage time."""
    from ge.config import ActiveParams, load_params, use_params
    from ge.fit.sim_fits import sticks_rows

    rows = [
        # down, togo, yl, play_type, rush, scramble, pass_att, complete, penalty, qtr, wp
        (1, 10.0, 50.0, "run", 1, 0, 0, 0, 0, 1, 0.5),  # kept: run
        (2, 5.0, 60.0, "pass", 0, 0, 1, 1, 0, 2, 0.5),  # kept: completion
        (2, 5.0, 60.0, "pass", 0, 0, 1, 0, 0, 2, 0.5),  # incomplete
        (1, 10.0, 50.0, "run", 1, 1, 0, 0, 0, 1, 0.5),  # scramble
        (4, 2.0, 50.0, "run", 1, 0, 0, 0, 0, 1, 0.5),  # 4th down
        (1, 8.0, 8.0, "run", 1, 0, 0, 0, 0, 1, 0.5),  # goal to go
        (1, 10.0, 50.0, "run", 1, 0, 0, 0, 1, 1, 0.5),  # penalty flag
        (1, 10.0, 50.0, "run", 1, 0, 0, 0, 0, 4, 0.99),  # G7 garbage time
        (1, 10.0, 50.0, "no_play", 1, 0, 0, 0, 1, 1, 0.5),  # no play
    ]
    cols = ["down", "ydstogo", "yardline_100", "play_type", "rush", "qb_scramble", "pass_attempt",
            "complete_pass", "penalty", "qtr", "wp"]  # fmt: skip
    core = pl.DataFrame(rows, schema=cols, orient="row").with_columns(
        pl.lit(0).alias("week_index"),
        pl.lit(0).alias("qb_kneel"),
        pl.lit(0).alias("qb_spike"),
        pl.lit(0).alias("two_point_attempt"),
        pl.lit(4.0).alias("yards_gained"),
    )
    with use_params(ActiveParams(load_params(), None)):
        r = sticks_rows(core)
    assert r["kind"].to_list() == [0, 1]
    assert set(r.columns) >= {"week_index", "kind", "ydstogo", "yards_gained"}


# ---------------------------------------------------------------- the fit


def test_sticks_fit_recovers_a_planted_q() -> None:
    """Uniform gains at every distance; at the line a share 0.4 (runs) and 0.25 (completions) is
    moved one yard short: E = 100 per distance, O = 60 and 75."""
    fit = _fit(_both(0.4, 0.25))
    assert fit.q == pytest.approx((0.4, 0.25), abs=1e-12)
    assert fit.observed == pytest.approx((8 * 60.0, 8 * 75.0))
    assert fit.expected == pytest.approx((8 * 100.0, 8 * 100.0))


def test_sticks_fit_ignores_distances_out_of_range() -> None:
    """Plays at 1-2 or 11+ yards to go never enter O, E or a reference."""
    extra = pl.DataFrame(
        [(0, k, float(t), float(t)) for k in (0, 1) for t in (1, 2, 11, 12) for _ in range(500)],
        schema=["week_index", "kind", "ydstogo", "yards_gained"], orient="row",
    )  # fmt: skip
    base = _both(0.4, 0.25)
    assert _fit(pl.concat([base, extra])).q == pytest.approx(_fit(base).q, abs=1e-12)


def test_sticks_reference_uses_the_same_bin_and_the_gap() -> None:
    """ref_t averages the share of gain t over distances t' in t's bin with |t - t'| >= 2: a
    large share of gain 9 at distance 8 (gap 1) or 5 (another bin) does not enter ref_9; the
    share at distance 7 (same bin, gap 2) is the only one that does."""
    from ge.fit.sim_fits import sticks_reference

    shares = {t: {g: 100 / 2100 for g in range(21)} for t in range(3, 11)}
    shares[8][9] = 0.9
    shares[5][9] = 0.9
    shares[7][9] = 0.5
    ref = sticks_reference(shares, togo_min=3, togo_max=10, distance_upper=[2, 6, 10], min_gap=2)
    assert ref[9] == pytest.approx(0.5)  # only t' = 7 qualifies for t = 9
    assert ref[3] == pytest.approx(100 / 2100)  # t' = 5, 6
    assert sorted(ref) == list(range(3, 11))


def test_sticks_fit_weights_recent_weeks() -> None:
    """No heap in week 0, q = 0.8 in week 99 (synthetic): a short half-life fits near 0.8, a
    huge one near the pooled 0.4."""
    rows = pl.concat([_both(0.0, 0.0, week=0), _both(0.8, 0.8, week=99)])
    recent = _fit(rows, target_index=100, h=2.0)
    pooled = _fit(rows, target_index=100, h=1e9)
    assert recent.q[0] == pytest.approx(0.8, abs=0.01)
    assert pooled.q[0] == pytest.approx(0.4, abs=1e-6)


def test_sticks_fit_clamps_q_to_0_and_1() -> None:
    """A heap at the line (O > E) gives q = 0, none at the line gives q = 1; the raw value is
    kept for the report."""
    fit = _fit(_both(-0.5, 1.0))
    assert fit.raw[0] == pytest.approx(-0.5) and fit.q[0] == 0.0
    assert fit.raw[1] == pytest.approx(1.0) and fit.q[1] == 1.0


def test_sticks_fit_needs_the_minimum_expected_count() -> None:
    """E = 8 per kind with one play per gain: below sticks.min_expected (200) the fit raises."""
    with pytest.raises(NotImplementedError, match=r"S-1.*200"):
        _fit(_both(0.0, 0.0, per_gain=1))


def test_sticks_fit_raises_when_a_distance_has_no_reference() -> None:
    """With the gap so wide that some distance has no reference distance in its bin."""
    with pytest.raises(NotImplementedError, match="no reference distance"):
        _fit(_both(0.4, 0.25), min_gap=4)


def test_sticks_fit_keys_written() -> None:
    from ge.fit.sim_fits import SticksFit
    from ge.fit.sim_job import SimOut, record_sticks

    fit = SticksFit(q=(0.45, 0.3), raw=(0.45, 0.3), observed=(55.0, 70.0),
                    expected=(100.0, 100.0), n=[1000, 2000], n_eff=[900.0, 1800.0])  # fmt: skip
    out = SimOut({}, {}, {}, {})
    record_sticks(out, fit, [2016, 2017])
    assert sorted(out.values) == sorted(A.sticks_key(k) for k in A.STICKS_KINDS)
    assert out.values[A.sticks_key("run")]["value"] == 0.45
    assert out.values[A.sticks_key("completion")]["value"] == 0.3
    assert {v["spec_id"] for v in out.values.values()} == {"PRJ-02"}
    assert out.diagnostics["sticks"]["expected"] == [100.0, 100.0]


def test_inputs_read_the_sticks_keys_in_order() -> None:
    from ge.models.sim.inputs import sticks_model

    vals = {A.sticks_key("run"): 0.5, A.sticks_key("completion"): 0.25}
    assert sticks_model(lambda key, spec_id: vals[key]).tolist() == [0.5, 0.25]


# ---------------------------------------------------------------- the engine


def test_engine_spot_short_rule() -> None:
    from ge.models.sim.engine import spot_short

    rng = np.random.default_rng(0)
    # gain, togo, yardline_100, down, q -> spotted gain (togo range 3-10)
    cases = [
        ((10.0, 10.0, 50.0, 1, 1.0), 9.0),
        ((10.0, 10.0, 50.0, 1, 0.0), 10.0),
        ((3.0, 3.0, 50.0, 3, 1.0), 2.0),
        ((11.0, 10.0, 50.0, 1, 1.0), 11.0),
        ((9.0, 10.0, 50.0, 2, 1.0), 9.0),
        ((10.0, 10.0, 50.0, 4, 1.0), 10.0),  # 4th down
        ((10.0, 10.0, 10.0, 1, 1.0), 10.0),  # goal to go
        ((2.0, 2.0, 50.0, 2, 1.0), 2.0),  # below togo_min
        ((11.0, 11.0, 50.0, 2, 1.0), 11.0),  # above togo_max
    ]
    for args, want in cases:
        assert spot_short(*args, 3.0, 10.0, rng) == want, args


def _sim(game, league, n=400):  # type: ignore[no-untyped-def]
    from ge.models.sim.engine import simulate

    return simulate(game, league, n, game_id="G_STICKS", model_version="m1")


def _second_and_1(game, league) -> tuple[int, int]:  # type: ignore[no-untyped-def]
    t = _sim(game, league).team.astype(np.int64)
    sec = t[..., A.R_SECOND_ATT0 : A.R_SECOND_ATT0 + A.THIRD_BINS]
    return int(sec[..., 0].sum()), int(sec.sum())


def _quiet(league):  # type: ignore[no-untyped-def]
    return replace(league, penalty_offense_rate=0.0, penalty_defense_rate=0.0,
                   fumble_run_rate=0.0, fumble_completion_rate=0.0, spike_rate=0.0)  # fmt: skip


def test_engine_spots_runs_one_short_by_kind() -> None:
    """Every designed run gains 10 (test setting): with q_run = 1 each 1st & 10 becomes 2nd & 1;
    with q_run = 0, or only q_completion = 1, no 2nd & 1 ever happens."""
    lg = replace(_quiet(synthetic_league()), run_yards=_run_packed([[10.0]] * 11))
    runs = replace(synthetic_game(), xpass=_logit(-30.0))
    on, _ = _second_and_1(replace(runs, sticks_q=np.array([1.0, 0.0])), lg)
    off, _ = _second_and_1(replace(runs, sticks_q=np.array([0.0, 0.0])), lg)
    other, _ = _second_and_1(replace(runs, sticks_q=np.array([0.0, 1.0])), lg)
    assert on > 0 and off == 0 and other == 0


def test_engine_spots_completions_one_short_by_kind() -> None:
    """Every pass is a 10-yard completion with no YAC, no sacks, scrambles or interceptions
    (test settings): q_completion = 1 makes 2nd & 1s, q_run = 1 alone does not."""
    lg = replace(_quiet(synthetic_league()), air_yards=_air_packed([[10.0]] * 4),
                 yac=_packed([[0.0]] * 5), int_rate_band=np.zeros(4),
                 scramble_rate=0.0)  # fmt: skip
    passes = replace(synthetic_game(), xpass=_logit(30.0), cp=_logit(30.0))
    team = passes.team.copy()
    team[:, A.T_SACK_LOGIT] = -30.0
    player = passes.player.copy()
    player[:, :, A.P_SCRAMBLE] = 0.0
    passes = replace(passes, team=team, player=player)
    on, _ = _second_and_1(replace(passes, sticks_q=np.array([0.0, 1.0])), lg)
    off, _ = _second_and_1(replace(passes, sticks_q=np.array([1.0, 0.0])), lg)
    assert on > 0 and off == 0


@pytest.mark.parametrize("q", [np.array([0.5]), np.array([0.5, 0.5, 0.5]), np.array([-0.1, 0.5]),
                               np.array([0.5, 1.1])])  # fmt: skip
def test_engine_refuses_bad_sticks_q(q: np.ndarray) -> None:
    with pytest.raises(ValueError, match="PRJ-02"):
        _sim(replace(synthetic_game(), sticks_q=q), synthetic_league(), 10)
