"""BUILD_PLAN Phase 4: "on synthetic plays with planted effects, recovered ratings correlate
above 0.9 with the truth and the home term is within 10% of the planted value".

Plus: the other COA-07 coefficients and c within 3 standard errors of the planted values,
and the ratings' approximate standard errors cover the truth at about the nominal rate when
the penalty equals sigma^2 / tau^2 and plays are unweighted (the case where the ridge
posterior is exact). Every size and value is a test setting in tests/phase4/synth.py; the
home term's standard error is well under 3% of its planted value, so the 10% check isn't
marginal."""

from __future__ import annotations

import numpy as np
import pytest

from ge.models.ratings import RATING_TYPES, fit_ratings
from ge.models.ratings_window import fit_c, pooled_coa07
from tests.phase4 import synth

S = synth.Settings()
MATCHED_PENALTY = S.sigma**2 / S.tau**2
H_RECENCY = 8.0
NO_DECAY = 1e12  # half-life so long every weight is 1 to machine precision


@pytest.fixture(scope="module")
def data() -> synth.Synth:
    return synth.make("recovery")


def test_ratings_correlate_with_planted_effects(data: synth.Synth) -> None:
    season = S.first_season + S.seasons - 1
    table = fit_ratings(
        synth.season_frame(data, season),
        data.teams,
        penalty=MATCHED_PENALTY,
        h=H_RECENCY,
        prior=None,
    )
    for k in RATING_TYPES:
        got = [table.values[(t, k)] for t in data.teams]
        want = [data.truth[(season, t, k)] for t in data.teams]
        r = float(np.corrcoef(got, want)[0, 1])
        assert r > 0.9, (k, r)


def test_home_term_within_ten_percent(data: synth.Synth) -> None:
    fit = pooled_coa07(data.plays, MATCHED_PENALTY)
    planted = S.beta["home"]
    assert abs(fit.coefs["home"] - planted) / planted <= 0.10, fit.coefs["home"]
    assert fit.se["home"] / planted < 0.03, fit.se["home"]


@pytest.mark.parametrize("term", ["rest", "travel", "tz"])
def test_other_coa07_terms_within_three_se(data: synth.Synth, term: str) -> None:
    fit = pooled_coa07(data.plays, MATCHED_PENALTY)
    assert abs(fit.coefs[term] - S.beta[term]) <= 3 * fit.se[term], (term, fit.coefs[term])


def test_pooled_fit_recovers_season_intercepts(data: synth.Synth) -> None:
    """The unpenalized intercept also absorbs the season's mean planted team effect (the
    penalized effects are shrunk toward 0), so that mean is added to the planted value."""
    fit = pooled_coa07(data.plays, MATCHED_PENALTY)
    for (season, kind), planted in data.intercepts.items():
        shift = sum(
            float(np.mean([data.truth[(season, t, f"{side}_{kind}")] for t in data.teams]))
            for side in ("off", "def")
        )
        assert fit.intercepts[(season, kind)] == pytest.approx(planted + shift, abs=0.01)


def test_c_within_three_se(data: synth.Synth) -> None:
    got = fit_c(data.team_games)
    tg = data.team_games
    assert got.league_epa == pytest.approx(
        float(tg["epa_sum"].sum() / tg["plays"].sum()), rel=1e-12
    )
    assert got.league_ppd == pytest.approx(
        float(tg["points"].sum() / tg["drives"].sum()), rel=1e-12
    )
    assert got.league_drives == pytest.approx(float(tg["drives"].mean()), rel=1e-12)
    assert got.n_team_games == tg.height
    assert abs(got.c - S.c) <= 3 * got.c_se, (got.c, got.c_se)


def test_standard_errors_cover_the_truth() -> None:
    small = synth.Settings(seasons=1)
    hits = total = 0
    for seed in range(50):
        d = synth.make(f"coverage/{seed}", small)
        season = small.first_season
        table = fit_ratings(
            synth.season_frame(d, season), d.teams, penalty=MATCHED_PENALTY, h=NO_DECAY, prior=None
        )
        for t in d.teams:
            for k in RATING_TYPES:
                total += 1
                hits += (
                    abs(table.values[(t, k)] - d.truth[(season, t, k)]) <= 1.96 * table.se[(t, k)]
                )
    rate = hits / total
    assert 0.90 <= rate <= 0.99, rate
