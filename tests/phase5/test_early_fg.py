"""PRJ-02 early-down field goals (fix round 1; design approved by Rhys 2026-11-16, rulings Q2-Q10
and F1-F4; plans/phase5-early-down-fg.md). When config/sim.yaml early_fg.enabled is true, a snap
on downs 1-3 is eligible in the 2nd quarter, or in the 4th quarter with the offense's score minus
the defense's from early_fg.q4_score_min to q4_score_max, with at most early_fg.max_seconds left in
the half and the ball at or inside the defense's early_fg.max_yardline; never in overtime. On an
eligible snap, before a spike is considered, the offense attempts a field goal with
P = expit(b0 + b1 s + b2 T + b3 s T), s = seconds left in the half, T = 1 with a timeout left
(M4), fitted per window under the PRJ-02 league weights; BT-02's 200 attempts and 200
non-attempts, else it raises. A missed attempt counts as an attempt, not as a possession alive at
the end of the half. Two diagnostic counters that never draw. Synthetic placeholder data only,
except the realdata replay at the end."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from ge.models.sim import arrays as A
from ge.models.sim.settings import load_sim
from tests.phase5.sim_synth import CLOCK_CATEGORIES, _packed, synthetic_game, synthetic_league

GOLDEN = Path(__file__).parent / "fixtures" / "early_fg_off_hash.json"
KW = {"max_seconds": 30, "max_yardline": 40, "q4_score_min": -3, "q4_score_max": 0,
      "periods": [2, 4]}  # fmt: skip
TRUE = (2.7, -0.43, 3.65, -0.62)  # planted M4 coefficients (synthetic test setting)


# ---------------------------------------------------------------- settings and keys


def test_early_fg_settings_come_from_config() -> None:
    s = load_sim().early_fg
    assert s.enabled.value is True
    assert (s.max_seconds.value, s.max_yardline.value) == (30, 40)
    assert (s.q4_score_min.value, s.q4_score_max.value) == (-3, 0)
    assert s.periods.value == [2, 4]
    for e in (s.enabled, s.max_seconds, s.max_yardline, s.q4_score_min, s.q4_score_max, s.periods):
        assert e.spec_id == "PRJ-02" and e.status == "initial"


def test_early_fg_terms_and_keys() -> None:
    assert A.EARLY_FG_TERMS == ("intercept", "seconds", "timeout", "seconds_x_timeout")
    assert A.early_fg_key("seconds") == "fit:PRJ-02/early_fg/seconds"


# ---------------------------------------------------------------- row set


def test_early_fg_rows() -> None:
    """Eligible snaps only; spikes and kneels are eligible non-kicks (ruling Q4)."""
    from ge.fit.sim_fits import early_fg_rows

    rows = [
        # down, qtr, half_sec, yl, sd, play_type, fga, timeouts
        (1, 2, 5.0, 20.0, 0.0, "field_goal", 1, 0),  # kept: kick
        (2, 2, 25.0, 40.0, -7.0, "pass", 0, 2),  # kept: Q2 any score, the 40
        (3, 2, 30.0, 10.0, 14.0, "qb_spike", 0, 0),  # kept: spike, 30 s
        (1, 4, 3.0, 35.0, -3.0, "run", 0, 1),  # kept: Q4 -3
        (2, 4, 3.0, 35.0, 0.0, "qb_kneel", 0, 1),  # kept: Q4 tied, kneel
        (4, 2, 5.0, 20.0, 0.0, "field_goal", 1, 0),  # 4th down
        (1, 1, 5.0, 20.0, 0.0, "pass", 0, 0),  # Q1
        (1, 3, 5.0, 20.0, 0.0, "pass", 0, 0),  # Q3
        (1, 5, 5.0, 20.0, 0.0, "field_goal", 1, 0),  # overtime
        (1, 2, 31.0, 20.0, 0.0, "pass", 0, 0),  # 31 s
        (1, 2, 5.0, 41.0, 0.0, "field_goal", 1, 0),  # beyond the 40
        (1, 4, 5.0, 20.0, -4.0, "field_goal", 1, 0),  # Q4 -4
        (1, 4, 5.0, 20.0, 1.0, "pass", 0, 0),  # Q4 leading
        (1, 4, 5.0, 20.0, -10.0, "field_goal", 1, 0),  # Q4 -10 (ruling F1)
        (1, 2, 5.0, 20.0, 0.0, "no_play", 0, 0),  # no-play penalty
    ]
    cols = ["down", "qtr", "half_seconds_remaining", "yardline_100", "score_differential",
            "play_type", "field_goal_attempt", "posteam_timeouts_remaining"]  # fmt: skip
    core = pl.DataFrame(rows, schema=cols, orient="row").with_columns(
        pl.lit(0).alias("week_index"), pl.lit("A").alias("posteam")
    )
    r = early_fg_rows(core, **KW)
    assert r["kick"].to_list() == [1.0, 0.0, 0.0, 0.0, 0.0]
    assert r["seconds"].to_list() == [5.0, 25.0, 30.0, 3.0, 3.0]
    assert r["timeout"].to_list() == [0.0, 1.0, 0.0, 1.0, 1.0]
    assert list(r.columns) == ["week_index", "kick", "seconds", "timeout"]


# ---------------------------------------------------------------- the fit


def _planted(n: int, coef: tuple[float, ...], *, week: int = 0, seed: int = 1) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    s = rng.integers(0, 31, n).astype(np.float64)
    t = (rng.random(n) < 0.5).astype(np.float64)
    eta = coef[0] + coef[1] * s + coef[2] * t + coef[3] * s * t
    y = (rng.random(n) < 1.0 / (1.0 + np.exp(-eta))).astype(np.float64)
    return pl.DataFrame({"week_index": np.full(n, week), "kick": y, "seconds": s, "timeout": t})


def _fit(rows: pl.DataFrame, *, target_index: int = 1, h: float = 1e9):  # type: ignore[no-untyped-def]
    from ge.fit.sim_fits import fit_early_fg

    return fit_early_fg(rows, target_index=target_index, h=h)


def test_early_fg_fit_recovers_planted_coefficients() -> None:
    fit = _fit(_planted(60_000, TRUE))
    for got, se, want in zip(fit.coef, fit.se, TRUE, strict=True):
        assert abs(got - want) < 4.0 * se, (got, se, want)
    assert fit.n == 60_000 and 0 < fit.events < fit.n


def test_early_fg_fit_weights_recent_weeks() -> None:
    """Intercept 0 in week 0, 2 in week 99 (synthetic): a short half-life fits near 2."""
    old = _planted(30_000, (0.0, *TRUE[1:]), week=0, seed=2)
    new = _planted(30_000, (2.0, *TRUE[1:]), week=99, seed=3)
    recent = _fit(pl.concat([old, new]), target_index=100, h=2.0)
    pooled = _fit(pl.concat([old, new]), target_index=100, h=1e9)
    assert recent.coef[0] == pytest.approx(2.0, abs=0.25)
    assert 0.5 < pooled.coef[0] < 1.5


def test_early_fg_fit_needs_200_of_each() -> None:
    rows = _planted(5_000, TRUE)
    kicks = rows.filter(pl.col("kick") == 1.0).head(199)
    with pytest.raises(NotImplementedError, match="200"):
        _fit(pl.concat([kicks, rows.filter(pl.col("kick") == 0.0)]))
    misses = rows.filter(pl.col("kick") == 0.0).head(199)
    with pytest.raises(NotImplementedError, match="200"):
        _fit(pl.concat([rows.filter(pl.col("kick") == 1.0), misses]))


def test_early_fg_fit_raises_on_a_one_outcome_term() -> None:
    rows = _planted(20_000, TRUE)
    with_to = rows.filter(pl.col("timeout") == 1.0).with_columns(pl.lit(1.0).alias("kick"))
    one = pl.concat([rows.filter(pl.col("timeout") == 0.0), with_to])
    with pytest.raises(NotImplementedError, match="one outcome"):
        _fit(one)


def test_early_fg_fit_keys_written() -> None:
    from ge.fit.sim_fits import EarlyFgFit
    from ge.fit.sim_job import SimOut, record_early_fg

    fit = EarlyFgFit(coef=(2.6, -0.4, 3.6, -0.6), se=(0.2, 0.03, 0.7, 0.1), n=3000, events=600,
                     n_eff=1500.0)  # fmt: skip
    out = SimOut({}, {}, {}, {})
    record_early_fg(out, fit, [2016, 2017])
    assert sorted(out.values) == sorted(A.early_fg_key(t) for t in A.EARLY_FG_TERMS)
    assert [out.values[A.early_fg_key(t)]["value"] for t in A.EARLY_FG_TERMS] == list(fit.coef)
    assert {v["spec_id"] for v in out.values.values()} == {"PRJ-02"}
    assert out.diagnostics["early_fg"]["events"] == 600


def test_inputs_read_the_early_fg_keys_in_order() -> None:
    from ge.models.sim.inputs import early_fg_model

    vals = {A.early_fg_key(t): float(i) for i, t in enumerate(A.EARLY_FG_TERMS)}
    assert early_fg_model(lambda key, spec_id: vals[key]).tolist() == [0.0, 1.0, 2.0, 3.0]


def test_early_fg_enabled_without_keys_raises() -> None:
    """Ruling Q5: missing keys never switch the path off."""
    from ge.models.sim.inputs import early_fg_inputs

    def missing(key: str, spec_id: str) -> float:
        raise NotImplementedError(f"{spec_id}: {key} has no fitted value")

    with pytest.raises(NotImplementedError, match="early_fg"):
        early_fg_inputs(True, missing)
    on, coef = early_fg_inputs(False, missing)
    assert on is False and coef.tolist() == [0.0, 0.0, 0.0, 0.0]


# ---------------------------------------------------------------- the engine


def test_engine_eligibility_rule() -> None:
    from ge.models.sim.engine import early_fg_eligible

    per = np.array([0.0, 1.0, 0.0, 1.0])  # periods 2 and 4
    # down, qtr, in_ot, half_sec, yl, sd -> eligible (max 30 s, the 40, Q4 -3..0)
    cases = [
        ((1, 2, False, 5.0, 20.0, 7.0), True),
        ((3, 2, False, 30.0, 40.0, -20.0), True),
        ((2, 4, False, 10.0, 30.0, -3.0), True),
        ((2, 4, False, 10.0, 30.0, 0.0), True),
        ((4, 2, False, 5.0, 20.0, 0.0), False),
        ((1, 1, False, 5.0, 20.0, 0.0), False),
        ((1, 3, False, 5.0, 20.0, 0.0), False),
        ((1, 5, True, 5.0, 20.0, 0.0), False),
        ((1, 2, False, 31.0, 20.0, 0.0), False),
        ((1, 2, False, 5.0, 41.0, 0.0), False),
        ((1, 4, False, 5.0, 20.0, -4.0), False),
        ((1, 4, False, 5.0, 20.0, 1.0), False),
        ((1, 4, False, 5.0, 20.0, -10.0), False),
    ]
    for args, want in cases:
        assert early_fg_eligible(*args, per, 30.0, 40.0, -3.0, 0.0) == want, args


def _sim(game, league, n=500, gid="G_EFG"):  # type: ignore[no-untyped-def]
    from ge.models.sim.engine import simulate

    return simulate(game, league, n, game_id=gid, model_version="m1")


def _on(coef: tuple[float, ...]):  # type: ignore[no-untyped-def]
    return replace(synthetic_game(), early_fg_on=True, early_fg=np.array(coef, dtype=np.float64))


def test_engine_kicks_on_eligible_early_down() -> None:
    """P = 1 (test setting): every eligible early-down snap is a field-goal attempt through the
    existing path; 4th-down counters are untouched by it."""
    t = _sim(_on((30.0, 0.0, 0.0, 0.0)), synthetic_league()).team.astype(np.int64)
    elig, att = t[..., A.R_EFG_ELIG], t[..., A.R_EFG_ATT]
    assert elig.sum() > 0 and (att == elig).all()
    fc = A.FOURTH_CELLS
    go = t[..., A.R_4TH_GO0 : A.R_4TH_GO0 + fc].sum(-1)
    n4 = t[..., A.R_4TH_N0 : A.R_4TH_N0 + fc].sum(-1)
    assert (go + t[..., A.R_FG_ATT] - att + t[..., A.R_PUNTS] == n4).all()
    fg_att = t[..., A.R_FG_ATT_D0 : A.R_FG_ATT_D0 + A.FG_DIST_BINS].sum(-1)
    assert (fg_att == t[..., A.R_FG_ATT]).all() and (att <= t[..., A.R_FG_ATT]).all()


def test_engine_never_kicks_early_when_p_is_zero() -> None:
    t = _sim(_on((-1e6, 0.0, 0.0, 0.0)), synthetic_league()).team.astype(np.int64)
    assert t[..., A.R_EFG_ELIG].sum() > 0 and t[..., A.R_EFG_ATT].sum() == 0


@pytest.mark.parametrize("coef", [np.zeros(3), np.zeros(5), np.array([0.0, np.nan, 0.0, 0.0])])
def test_engine_refuses_bad_early_fg_model(coef: np.ndarray) -> None:
    with pytest.raises(ValueError, match="PRJ-02"):
        _sim(replace(synthetic_game(), early_fg_on=True, early_fg=coef), synthetic_league(), 10)


def _digest(game) -> str:  # type: ignore[no-untyped-def]
    r = _sim(game, synthetic_league(), 2000, gid="G_DIAG_HASH")
    h = hashlib.sha256()
    for a in (r.team[:, :, : json.loads(GOLDEN.read_text())["nteam_at_capture"]], r.player,
              r.first_td, r.ot):  # fmt: skip
        h.update(np.ascontiguousarray(a).tobytes())
    return h.hexdigest()


def test_engine_early_fg_off_leaves_outputs_identical() -> None:
    """Ruling F3 (ii): with the path off, the golden full-output hash captured before the change;
    the new counters stay zero. (F3 (i), the diag_counters_hash.json hashes, is
    test_diag_counters.py::test_earlier_outputs_are_byte_identical.)"""
    want = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert synthetic_game().early_fg_on is False
    assert _digest(synthetic_game()) == want["regular"]
    assert _digest(synthetic_game(postseason=True)) == want["postseason"]
    t = _sim(synthetic_game(), synthetic_league()).team
    assert t[..., A.R_EFG_ELIG].sum() == 0 and t[..., A.R_EFG_ATT].sum() == 0


def test_engine_early_fg_counters_do_not_draw() -> None:
    """Ruling Q7: on with P = 0 exactly draws nothing, so every output but the two new counters
    equals the path off."""
    off = _sim(synthetic_game(), synthetic_league())
    on = _sim(_on((-1e6, 0.0, 0.0, 0.0)), synthetic_league())
    keep = [k for k in range(A.NTEAM) if k not in (A.R_EFG_ELIG, A.R_EFG_ATT)]
    assert np.array_equal(off.team[..., keep], on.team[..., keep])
    assert np.array_equal(off.player, on.player) and np.array_equal(off.ot, on.ot)
    assert np.array_equal(off.first_td, on.first_td)
    assert on.team[..., A.R_EFG_ELIG].sum() > 0


def test_missed_early_fg_at_the_gun() -> None:
    """Ruling Q6: every early kick misses and its clock runoff (40 s inside two minutes, test
    setting) ends the period, so a counted end-of-half possession and an early attempt can never
    share a period end: per run, end-of-half possessions + early attempts <= period ends."""
    lg = synthetic_league()
    nc = len(CLOCK_CATEGORIES)
    clock = [[30.0, 40.0]] * nc + [[5.0, 10.0]] * nc
    for name in ("score", "try", "kickoff", "turnover", "punt", "penalty", "incomplete"):
        clock[CLOCK_CATEGORIES.index(name)] = [5.0, 8.0]
        clock[nc + CLOCK_CATEGORIES.index(name)] = [5.0, 8.0]
    clock[nc + CLOCK_CATEGORIES.index("field_goal")] = [40.0]
    lg = replace(lg, clock=_packed(clock), fg_intercept=-30.0)
    game = _on((30.0, 0.0, 0.0, 0.0))
    r = _sim(game, lg, 2000)
    t = r.team.astype(np.int64)
    att = t[..., A.R_EFG_ATT].sum(-1)
    end_half = t[..., A.R_END_HALF].sum(-1)
    assert att.sum() > 0 and t[..., A.R_FG_MADE].sum() == 0
    max_ot = int(game.ot[A.O_MAX_PERIODS])
    assert (end_half + att <= 2 + r.ot.astype(np.int64) * max_ot).all()


# ---------------------------------------------------------------- realdata (section e)


@pytest.mark.realdata
@pytest.mark.parametrize("season", [2024, 2023])
def test_replay_early_down_fg_with_the_window_model(season: int) -> None:
    """Section e: the window's fitted model on the season's actual eligible snaps; predicted
    attempts per team-game within max(0.010, 3 x SE) of actual, SE = sqrt(sum P(1 - P)) /
    team-games. 2024 with S2024, 2023 with S2023. Reads the local nflverse store (DATA-01)."""
    from ge.config import use_season
    from ge.fit.sim_fits import early_fg_rows
    from ge.ingest.raw import DATA_ROOT, read_latest
    from ge.models.sim.inputs import _fit_value, early_fg_model

    try:
        pbp = read_latest(DATA_ROOT, "pbp", season)
    except FileNotFoundError as exc:
        pytest.fail(f"realdata test needs the local store: {exc}")
    s = load_sim().early_fg
    rows = early_fg_rows(
        pbp.with_columns(pl.lit(0).alias("week_index")),
        max_seconds=s.max_seconds.value,
        max_yardline=s.max_yardline.value,
        q4_score_min=s.q4_score_min.value,
        q4_score_max=s.q4_score_max.value,
        periods=s.periods.value,
    )
    with use_season(season):
        b = early_fg_model(_fit_value)
    sec, to = rows["seconds"].to_numpy(), rows["timeout"].to_numpy()
    p = 1.0 / (1.0 + np.exp(-(b[0] + b[1] * sec + b[2] * to + b[3] * sec * to)))
    tg = 2 * pbp["game_id"].n_unique()
    pred, act = float(p.sum()) / tg, float(rows["kick"].sum()) / tg
    se = float(np.sqrt(np.sum(p * (1.0 - p)))) / tg
    tol = max(0.010, 3.0 * se)
    print(
        f"{season}: eligible snaps {rows.height}, team-games {tg}, predicted {pred:.4f}, "
        f"actual {act:.4f}, diff {pred - act:+.4f}, SE {se:.4f}, tolerance {tol:.4f}"
    )
    assert abs(pred - act) <= tol, (season, pred, act, se, tol)
