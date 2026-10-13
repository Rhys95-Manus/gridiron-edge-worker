"""PRJ-01a / G6 / G4 mechanics on small synthetic inputs, against an independent play-level
closed form written here (not the production grouping).

The ridge: minimise sum_i w_i (y_i - offset_i - x_i b)^2 + sum_j lambda_j (b_j - b0_j)^2,
w_i = 0.5^(g_i / h), lambda_j = 0 for the pass and run intercepts, lambda for team columns,
lambda x run_penalty_scale for run columns. Standard errors: sigma^2 (X'WX + Lambda)^-1 with
sigma^2 = sum w r^2 / sum w (decision log 2026-10-12)."""

from __future__ import annotations

import datetime as dt
import io
import math

import numpy as np
import polars as pl
import pytest

from ge.models.ratings import (
    RATING_TYPES,
    Prior,
    WindowConsts,
    expected_epa,
    expected_points,
    fit_ratings,
    game_lines,
    offense_terms,
    pass_rates,
    term_offset,
)
from tests.phase4 import synth

SMALL = synth.Settings(teams=6, seasons=1, weeks=5, plays_per_offense=30)


def _bytes(df: pl.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.write_parquet(buf, compression="uncompressed", statistics=False)
    return buf.getvalue()


def _frame(key: str) -> tuple[synth.Synth, pl.DataFrame]:
    s = synth.make(key, SMALL)
    return s, synth.season_frame(s, SMALL.first_season)


def _oracle(
    plays: pl.DataFrame,
    teams: list[str],
    penalty: float,
    h: float,
    b0: dict[tuple[str, str], float] | None,
    run_scale: float = 1.0,
) -> tuple[dict[object, float], dict[object, float], float]:
    """Play-level closed form. Returns (coef by name, se by name, sigma^2)."""
    names: list[object] = ["int_pass", "int_run"] + [(t, k) for t in teams for k in RATING_TYPES]
    col = {n: i for i, n in enumerate(names)}
    rows = plays.to_dicts()
    X = np.zeros((len(rows), len(names)))
    y = np.zeros(len(rows))
    w = np.zeros(len(rows))
    for i, r in enumerate(rows):
        kind = "pass" if r["is_pass"] else "run"
        X[i, col[f"int_{kind}"]] = 1.0
        X[i, col[(r["posteam"], f"off_{kind}")]] = 1.0
        X[i, col[(r["defteam"], f"def_{kind}")]] = 1.0
        y[i] = r["epa"] - r["offset"]
        w[i] = 0.5 ** (r["g_off"] / h)
    lam = np.zeros(len(names))
    prior = np.zeros(len(names))
    for n, i in col.items():
        if isinstance(n, tuple):
            lam[i] = penalty * (run_scale if n[1].endswith("run") else 1.0)
            prior[i] = (b0 or {}).get(n, 0.0)
    A = (X.T * w) @ X + np.diag(lam)
    b = np.linalg.solve(A, (X.T * w) @ y + lam * prior)
    r = y - X @ b
    sigma2 = math.fsum(w * r * r) / math.fsum(w)
    se = np.sqrt(np.diag(sigma2 * np.linalg.inv(A)))
    return (
        {n: float(b[i]) for n, i in col.items()},
        {n: float(se[i]) for n, i in col.items()},
        sigma2,
    )


@pytest.mark.parametrize("run_scale", [1.0, 0.5, 2.0])
@pytest.mark.parametrize("with_prior", [False, True])
def test_fit_matches_play_level_closed_form(run_scale: float, with_prior: bool) -> None:
    s, plays = _frame(f"math/{run_scale}/{with_prior}")
    g = synth.rng("math/prior")
    b0 = (
        {(t, k): float(g.normal(0.0, 0.05)) for t in s.teams for k in RATING_TYPES}
        if with_prior
        else None
    )
    prior = Prior(b0, 0.0, 0.0, 1.0) if b0 is not None else None
    got = fit_ratings(plays, s.teams, penalty=40.0, h=3.0, prior=prior, run_penalty_scale=run_scale)
    coef, se, sigma2 = _oracle(plays, s.teams, 40.0, 3.0, b0, run_scale)
    assert got.int_pass == pytest.approx(coef["int_pass"], abs=1e-10)
    assert got.int_run == pytest.approx(coef["int_run"], abs=1e-10)
    assert got.sigma2 == pytest.approx(sigma2, rel=1e-10)
    assert got.n_plays == plays.height
    for t in s.teams:
        for k in RATING_TYPES:
            assert got.values[(t, k)] == pytest.approx(coef[(t, k)], abs=1e-10), (t, k)
            assert got.se[(t, k)] == pytest.approx(se[(t, k)], rel=1e-8), (t, k)


def test_vanishing_penalty_gives_weighted_least_squares_fit() -> None:
    """As lambda -> 0 the fitted values (identified, unlike the collinear coefficients) match
    weighted least squares."""
    s, plays = _frame("math/wls")
    got = fit_ratings(plays, s.teams, penalty=1e-9, h=3.0, prior=None)
    coef, _, _ = _oracle(plays, s.teams, 0.0 + 1e-9, 3.0, None)
    for r in plays.to_dicts():
        kind = "pass" if r["is_pass"] else "run"
        mine = (
            (got.int_pass if kind == "pass" else got.int_run)
            + got.values[(r["posteam"], f"off_{kind}")]
            + got.values[(r["defteam"], f"def_{kind}")]
        )
        ref = (
            coef[f"int_{kind}"]
            + coef[(r["posteam"], f"off_{kind}")]
            + coef[(r["defteam"], f"def_{kind}")]
        )
        assert mine == pytest.approx(ref, abs=1e-6)


def test_no_plays_gives_the_prior() -> None:
    """Before a team's first game of the season: ratings are b0, intercepts last season's
    final values, standard errors sqrt(sigma^2 / lambda) from the prior's residual variance."""
    teams = ["A", "B"]
    b0 = {
        (t, k): 0.01 * (i + 1)
        for i, (t, k) in enumerate((t, k) for t in teams for k in RATING_TYPES)
    }
    prior = Prior(b0, 0.07, -0.05, 0.16)
    empty = pl.DataFrame(
        schema={
            "game_id": pl.Utf8,
            "posteam": pl.Utf8,
            "defteam": pl.Utf8,
            "is_pass": pl.Boolean,
            "epa": pl.Float64,
            "g_off": pl.Float64,
            "offset": pl.Float64,
        }
    )
    got = fit_ratings(empty, teams, penalty=100.0, h=8.0, prior=prior)
    assert (got.int_pass, got.int_run, got.n_plays) == (0.07, -0.05, 0)
    for key, v in b0.items():
        assert got.values[key] == v
        assert got.se[key] == pytest.approx(math.sqrt(0.16 / 100.0))


def test_byte_identical_and_order_free() -> None:
    """Rule 6, and the leakage harness's shuffle mode reorders rows: same plays in any order
    give byte-identical ratings."""
    s, plays = _frame("math/bytes")
    a = fit_ratings(plays, s.teams, penalty=40.0, h=3.0, prior=None)
    b = fit_ratings(plays, s.teams, penalty=40.0, h=3.0, prior=None)
    shuffled = plays[synth.rng("math/shuffle").permutation(plays.height).tolist()]
    c = fit_ratings(shuffled, s.teams, penalty=40.0, h=3.0, prior=None)
    assert _bytes(a.frame()) == _bytes(b.frame()) == _bytes(c.frame())
    assert (a.int_pass, a.int_run, a.sigma2) == (c.int_pass, c.int_run, c.sigma2)
    assert a.cov.tobytes() == c.cov.tobytes()


def test_offense_terms_and_offset() -> None:
    """COA-07 in PRJ-01a: home +1 / -1, 0 at a neutral site; rest and travel offense minus
    defense; time zone |offense change| - |defense change|."""
    features = pl.DataFrame(
        {
            "game_id": ["g1", "g1", "g2", "g2"],
            "team": ["H", "A", "N1", "N2"],
            "home": [1.0, -1.0, 0.0, 0.0],
            "rest_days": [7.0, 4.0, 10.0, 6.0],
            "travel_km": [0.0, 2500.0, 900.0, 4000.0],
            "tz_change_hours": [0.0, -3.0, 1.0, -2.0],
        }
    )
    t = offense_terms(features).sort("game_id", "posteam")
    got = {r["posteam"]: r for r in t.to_dicts()}
    assert got["H"] == {
        "game_id": "g1", "posteam": "H", "defteam": "A",
        "home": 1.0, "d_rest": 3.0, "d_travel": -2500.0, "d_tz": -3.0,
    }  # fmt: skip
    assert got["A"]["home"] == -1.0 and got["A"]["d_tz"] == 3.0
    assert got["N1"]["home"] == 0.0 and got["N2"]["home"] == 0.0
    assert got["N1"]["d_tz"] == -1.0 and got["N2"]["d_travel"] == 3100.0
    coefs = {"home": 0.02, "rest": 0.003, "travel": -1e-5, "tz": -0.01}
    off = term_offset(t, coefs).to_list()
    want = [
        coefs["home"] * r["home"]
        + coefs["rest"] * r["d_rest"]
        + coefs["travel"] * r["d_travel"]
        + coefs["tz"] * r["d_tz"]
        for r in t.to_dicts()
    ]
    assert off == pytest.approx(want, abs=1e-15)


def test_pass_rate_spans_the_season_boundary() -> None:
    """p_A (decision log 2026-10-12): last season's games keep their games-ago weight."""
    t0 = dt.datetime(3001, 12, 1, tzinfo=dt.UTC)
    games = [  # oldest first: two last-season games, one this season
        ("old1", t0, [True, True, False, False]),
        ("old2", t0 + dt.timedelta(days=7), [True, False, False, False]),
        ("new1", t0 + dt.timedelta(days=280), [True, True, True, False]),
    ]
    rows = [
        {"posteam": "A", "game_id": gid, "kickoff_utc": kt, "is_pass": p}
        for gid, kt, ps in games
        for p in ps
    ]
    h = 6.0
    w = {"new1": 1.0, "old2": 0.5 ** (1 / h), "old1": 0.5 ** (2 / h)}
    num = math.fsum(w[r["game_id"]] * r["is_pass"] for r in rows)
    den = math.fsum(w[r["game_id"]] for r in rows)
    frame = pl.DataFrame(rows)
    assert pass_rates(frame, h)["A"] == pytest.approx(num / den, rel=1e-12)
    shuffled = frame[[3, 7, 0, 11, 5, 1, 9, 2, 10, 4, 8, 6]]
    assert pass_rates(shuffled, h) == pass_rates(frame, h)


def test_points_and_lines_arithmetic() -> None:
    s, plays = _frame("math/lines")
    table = fit_ratings(plays, s.teams, penalty=40.0, h=3.0, prior=None)
    home, away = s.teams[0], s.teams[1]
    p = {home: 0.6, away: 0.55}
    terms = pl.DataFrame(
        {
            "game_id": ["g", "g"],
            "posteam": [home, away],
            "defteam": [away, home],
            "home": [1.0, -1.0],
            "d_rest": [3.0, -3.0],
            "d_travel": [-500.0, 500.0],
            "d_tz": [0.0, 0.0],
        }
    )
    coefs = {"home": 0.02, "rest": 0.003, "travel": -1e-5, "tz": -0.01}
    consts = WindowConsts(
        "S3001", "rt", coefs, dict.fromkeys(coefs, 0.0), c=6.0, c_se=0.1,
        league_epa=0.01, league_ppd=2.0, league_drives=11.0,
    )  # fmt: skip
    off = {t: term_offset(terms.filter(pl.col("posteam") == t), coefs)[0] for t in (home, away)}

    def e(o: str, d: str) -> float:
        v = table.values
        return (
            p[o] * (table.int_pass + v[(o, "off_pass")] + v[(d, "def_pass")])
            + (1 - p[o]) * (table.int_run + v[(o, "off_run")] + v[(d, "def_run")])
            + off[o]
        )

    eh, ea = e(home, away), e(away, home)
    got_e, grad = expected_epa(table, home, away, p[home], off[home])
    assert got_e == pytest.approx(eh, abs=1e-12)
    assert expected_points(eh, consts) == pytest.approx(11.0 * (2.0 + 6.0 * (eh - 0.01)), abs=1e-12)
    lines = game_lines(table, "g", home, away, p, terms, consts)
    ph, pa = 11.0 * (2.0 + 6.0 * (eh - 0.01)), 11.0 * (2.0 + 6.0 * (ea - 0.01))
    assert (lines.home_points, lines.away_points) == pytest.approx((ph, pa), abs=1e-12)
    assert lines.spread == pytest.approx(ph - pa, abs=1e-12)
    assert lines.total == pytest.approx(ph + pa, abs=1e-12)
    # Delta method over the ratings' covariance.
    _, ga = expected_epa(table, away, home, p[away], off[away])
    k = 11.0 * 6.0
    gs, gt = k * (grad - ga), k * (grad + ga)
    assert lines.spread_se == pytest.approx(math.sqrt(gs @ table.cov @ gs), rel=1e-10)
    assert lines.total_se == pytest.approx(math.sqrt(gt @ table.cov @ gt), rel=1e-10)
