"""PRJ-02 rating tilt (Phase 5 checklist): with every slope at zero, team ratings change
nothing; with a planted slope on synthetic plays, the fitter recovers it within 3 SE.

Each slope: play outcome on the offense's realized same-side EPA/play in that game, with season
intercepts (logistic for completion, interception, fumble lost; least squares for YAC and yards
per carry), standard errors clustered by team-game (ruling B8, 2026-10-23). Every number below
is a synthetic test setting, not a football fact."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from ge.fit.sim_job import SimOut, record_tilt
from ge.fit.tilt import TILT_COMPONENTS, TiltFit, fit_tilt_slope
from ge.models.sim.tilt import TiltSlopes, tilt_shifts

SEASON_LEVELS = {2016: -0.2, 2017: 0.0, 2018: 0.3}  # season intercepts (logit or yards)


def _plays(beta: float, kind: str, seed: int) -> pl.DataFrame:
    """Synthetic plays: 300 team-games per season, 40 plays each, x = game EPA/play."""
    rng = np.random.default_rng(seed)
    rows: dict[str, list[float | int]] = {"season": [], "team_game": [], "x": [], "y": []}
    for season, level in SEASON_LEVELS.items():
        x_game = rng.normal(0.0, 0.15, size=300) + 0.05 * (season - 2017)
        x = np.repeat(x_game, 40)
        # a shared game-level shock, so plays in one team-game are correlated (ruling B8)
        eta = level + beta * x + np.repeat(rng.normal(0.0, 0.2, size=300), 40)
        if kind == "logistic":
            y = (rng.random(x.size) < 1.0 / (1.0 + np.exp(-eta))).astype(float)
        else:
            y = eta + rng.normal(0.0, 5.0, size=x.size)
        rows["season"].extend([season] * x.size)
        rows["team_game"].extend((season * 1000 + np.repeat(np.arange(300), 40)).tolist())
        rows["x"].extend(x.tolist())
        rows["y"].extend(y.tolist())
    return pl.DataFrame(rows)


def test_components_are_the_five_in_the_spec() -> None:
    assert dict(TILT_COMPONENTS) == {
        "completion": "logistic",
        "yac": "least_squares",
        "interception": "logistic",
        "yards_per_carry": "least_squares",
        "fumble_lost": "logistic",
    }


@pytest.mark.parametrize(
    ("component", "beta", "seed"),
    [
        ("completion", 1.2, 1),
        ("interception", -2.0, 2),
        ("fumble_lost", -1.5, 3),
        ("yac", 6.0, 4),
        ("yards_per_carry", 4.0, 5),
    ],
)
def test_fitter_recovers_planted_slope_within_3_se(component: str, beta: float, seed: int) -> None:
    kind = dict(TILT_COMPONENTS)[component]
    fit = fit_tilt_slope(_plays(beta, kind, seed), component)
    assert fit.se > 0
    assert abs(fit.slope - beta) < 3 * fit.se, (fit.slope, fit.se)


def test_standard_errors_are_clustered_by_team_game() -> None:
    """Ruling B8: x is shared by every play in a team-game, so the clustered SE must exceed the
    classical one on data with a game-level shock."""
    rng = np.random.default_rng(8)
    games, per = 900, 40
    x = np.repeat(rng.normal(0.0, 0.15, games), per)
    shock = np.repeat(rng.normal(0.0, 3.0, games), per)  # material game-level shock
    plays = pl.DataFrame(
        {
            "season": np.repeat([2016, 2017, 2018], games // 3 * per),
            "team_game": np.repeat(np.arange(games), per),
            "x": x,
            "y": 6.0 * x + shock + rng.normal(0.0, 5.0, games * per),
        }
    )
    fit = fit_tilt_slope(plays, "yac")
    assert fit.clusters == 900
    assert fit.se > fit.se_classical


@pytest.mark.parametrize(
    ("slope", "se", "listed"),
    [(-0.24, 0.168, True), (0.18, 0.019, False), (0.30, 0.15, False), (0.29, 0.15, True)],
)
def test_no_signal_tilt_slope_is_listed_and_contributes_zero(
    slope: float, se: float, listed: bool
) -> None:
    """Ruling 2026-10-24: BT-02's no-signal rule applies to tilt slopes. With a 95% interval
    (z = 1.95996...): 0.30 / 0.15 = 2.0 is signal; 0.29 / 0.15 = 1.93 is not."""
    out = SimOut({}, {}, {}, {})
    fit = TiltFit("fumble_lost", slope, se, se, 10_000, 500, 300)
    record_tilt(out, fit, "logistic", [2016, 2017], confidence=0.95)
    key = "fit:PRJ-02/tilt/fumble_lost"
    assert (key in out.no_signal) is listed
    assert (key in out.values) is not listed
    assert out.values[key + "/se"]["value"] == se  # the SE is always stored


def test_season_intercepts_absorb_season_level_shifts() -> None:
    """Shifting every x in one season by a constant leaves the slope unchanged."""
    plays = _plays(1.0, "logistic", 7)
    shifted = plays.with_columns(
        pl.when(pl.col("season") == 2018).then(pl.col("x") + 0.4).otherwise(pl.col("x"))
    )
    a = fit_tilt_slope(plays, "completion")
    b = fit_tilt_slope(shifted, "completion")
    assert b.slope == pytest.approx(a.slope, rel=1e-6)


@pytest.mark.parametrize(("net_pass", "net_run"), [(0.0, 0.0), (0.12, -0.08), (-0.3, 0.25)])
def test_zero_slopes_mean_ratings_change_nothing(net_pass: float, net_run: float) -> None:
    zero = TiltSlopes(completion=0.0, yac=0.0, interception=0.0, yards_per_carry=0.0, fumble=0.0)
    s = tilt_shifts(zero, net_pass=net_pass, net_run=net_run)
    assert (s.completion_logit, s.yac_yards, s.interception_logit) == (0.0, 0.0, 0.0)
    assert (s.ypc_yards, s.fumble_logit) == (0.0, 0.0)


def test_shift_is_slope_times_net_rating_of_its_own_side() -> None:
    slopes = TiltSlopes(
        completion=1.0, yac=2.0, interception=-3.0, yards_per_carry=4.0, fumble=-5.0
    )
    s = tilt_shifts(slopes, net_pass=0.1, net_run=-0.2)
    assert s.completion_logit == pytest.approx(0.1)
    assert s.yac_yards == pytest.approx(0.2)
    assert s.interception_logit == pytest.approx(-0.3)
    assert s.ypc_yards == pytest.approx(-0.8)
    assert s.fumble_logit == pytest.approx(1.0)
