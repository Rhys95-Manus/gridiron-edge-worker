"""Phase 3e estimators on synthetic data with planted values: COA-02 p_go (logistic), MTC-03
OL-absence factor (offset logistic), G6 ridge penalty (forward-chaining CV), G3 half-life
(next-game loss), PLY-14 base rates and return factor, PRJ-06 missed-game rates. Tolerances
are test settings stated here; the planted values are test settings, not real-world facts."""

from __future__ import annotations

import math

import numpy as np
import polars as pl
import pytest

from ge.config import load_params
from ge.fit.availability import missed_game_rates, practice_base_rates, return_factor
from ge.fit.halflife import choose_half_life, half_life_losses
from ge.fit.logistic import fit_logistic
from ge.fit.ol_factor import ol_absence_factor
from ge.fit.ridge_cv import choose_penalty, g6_cv_losses, ridge_ratings
from tests.phase3.fit.synth import league_plays, local_level_units, logistic_rows, rng

FIT = load_params().fitting
MIN_EVENTS = int(FIT.bt_02_min_events.value)


# ---- logistic (COA-02 p_go) ----


def test_logistic_recovers_planted_coefficients() -> None:
    coef = np.array([-1.0, -0.25, 0.02, 0.05, -0.0004])
    X, y, _ = logistic_rows(coef=coef, n=60_000, key="logit")
    fit = fit_logistic(X, y)
    z = (fit.coef - coef) / fit.se
    assert np.all(np.abs(z) < 4), (fit.coef, coef, z)


def test_logistic_is_deterministic() -> None:
    coef = np.array([0.5, -0.1, 0.0, 0.0, 0.0])
    X, y, _ = logistic_rows(coef=coef, n=5000, key="det")
    a, b = fit_logistic(X, y), fit_logistic(X, y)
    assert a.coef.tobytes() == b.coef.tobytes()


def test_logistic_offset() -> None:
    coef = np.array([0.3, 0.0, 0.0, 0.0, 0.0])
    X, y, off = logistic_rows(coef=coef, n=40_000, key="off", offset_sd=1.0)
    fit = fit_logistic(X[:, :1], y, offset=off)
    assert abs(fit.coef[0] - 0.3) < 4 * fit.se[0]


# ---- MTC-03 OL-absence factor ----


def _ol_rows(factor: float, key: str) -> pl.DataFrame:
    g = rng(key)
    teams = [f"T{i:02d}" for i in range(32)]
    off_rate = dict(zip(teams, g.uniform(0.04, 0.10, 32), strict=True))
    def_rate = dict(zip(teams, g.uniform(0.04, 0.10, 32), strict=True))
    league = 0.07
    rows = []
    for s in (2001, 2002):
        for w in range(1, 18):
            order = g.permutation(32)
            for a, b in zip(order[::2], order[1::2], strict=True):
                for pos, de in ((teams[a], teams[b]), (teams[b], teams[a])):
                    miss = int(g.choice([0, 0, 0, 1, 1, 2, 3]))
                    o = off_rate[pos] / (1 - off_rate[pos])
                    d = def_rate[de] / (1 - def_rate[de])
                    odds = o * d / (league / (1 - league)) * factor**miss
                    p = odds / (1 + odds)
                    gid = f"{s}_{w:02d}_{teams[a]}_{teams[b]}"
                    for sack in (g.random(36) < p).astype(int):
                        rows.append((s, gid, pos, de, int(sack), miss))
    return pl.DataFrame(
        rows,
        schema={
            "season": pl.Int64,
            "game_id": pl.Utf8,
            "posteam": pl.Utf8,
            "defteam": pl.Utf8,
            "sack": pl.Int64,
            "missing": pl.Int64,
        },
        orient="row",
    )


def test_ol_factor_recovers_planted_factor() -> None:
    fit = ol_absence_factor(_ol_rows(1.25, "ol"), MIN_EVENTS)
    assert fit.value is not None
    lo, hi = math.exp(fit.log_value - 3 * fit.se), math.exp(fit.log_value + 3 * fit.se)
    assert lo < 1.25 < hi, fit
    assert abs(fit.value - 1.25) / 1.25 < 0.1


def test_ol_factor_needs_min_events() -> None:
    rows = _ol_rows(1.25, "ol").head(100)
    fit = ol_absence_factor(rows, MIN_EVENTS)
    assert fit.value is None and fit.reason is not None


# ---- G6 ridge penalty ----


def test_g6_cv_picks_penalty_near_bayes_optimum() -> None:
    tau, sigma = 0.08, 1.4
    seasons = [
        league_plays(
            teams=32, weeks=17, plays_per_game=60, tau=tau, sigma=sigma, home=0.03, key=f"g6/{s}"
        )[0].with_columns(pl.lit(2000 + s).alias("season"))
        for s in range(3)
    ]
    grid = FIT.penalty_grid()
    losses = [g6_cv_losses(s, grid, h=1e9) for s in seasons]
    best = choose_penalty(losses)
    optimum = sigma**2 / tau**2
    # within two grid steps (10^0.5) of the Bayes-optimal penalty
    assert abs(math.log10(best) - math.log10(optimum)) <= 0.5 + 1e-9, (best, optimum)


def test_ridge_ratings_correlate_with_planted() -> None:
    plays, off, de = league_plays(
        teams=32, weeks=17, plays_per_game=60, tau=0.08, sigma=1.4, home=0.03, key="g6r"
    )
    r = ridge_ratings(plays, penalty=300.0, h=1e9)
    names = sorted(off)
    o = np.corrcoef([off[t] for t in names], [r.offense[t] for t in names])[0, 1]
    d = np.corrcoef([de[t] for t in names], [r.defense[t] for t in names])[0, 1]
    assert o > 0.9 and d > 0.9, (o, d)


# ---- G3 half-life ----


def test_half_life_picks_planted_optimum() -> None:
    h_true = 4.0
    alpha = 1 - 0.5 ** (1 / h_true)
    u = local_level_units(alpha=alpha, entities=4000, games=30, plays=10, key="hl")
    grid = FIT.half_life_grid()
    losses = half_life_losses(u, k=1e-9, hs=grid)
    assert choose_half_life([losses]) == h_true, losses


def test_half_life_loss_ratio_below_one_with_signal() -> None:
    u = local_level_units(alpha=0.3, entities=500, games=20, plays=10, key="hl2")
    losses = half_life_losses(u, k=5.0, hs=(2.0, 4.0))
    assert all(v.ratio < 1 for v in losses.values())


# ---- PLY-14 base rates and return factor; PRJ-06 ----


def test_practice_base_rates_recovered() -> None:
    g = rng("prac")
    planted = {"DNP": 0.2, "Limited": 0.75, "Full": 0.97}
    rows = [(s, bool(g.random() < p)) for s, p in planted.items() for _ in range(4000)]
    df = pl.DataFrame(rows, schema={"practice": pl.Utf8, "played": pl.Boolean}, orient="row")
    got = practice_base_rates(df, MIN_EVENTS)
    for s, p in planted.items():
        assert got[s].value is not None and abs(got[s].value - p) < 0.03


def test_practice_base_rate_missing_below_min_events() -> None:
    df = pl.DataFrame({"practice": ["DNP"] * 10, "played": [True] * 10})
    assert practice_base_rates(df, MIN_EVENTS)["DNP"].value is None


def test_return_factor_recovered() -> None:
    g = rng("ret")
    base = g.uniform(0.3, 0.95, 3000)
    ret = np.clip(base * 0.8 + g.normal(0, 0.05, 3000), 0, 1)
    df = pl.DataFrame({"baseline": base, "return_share": ret})
    fit = return_factor(df, MIN_EVENTS)
    assert fit.value is not None and abs(fit.value - 0.8) < 0.02


def test_missed_game_rates_by_position() -> None:
    g = rng("miss")
    planted = {"QB": 0.03, "RB": 0.09, "WR": 0.07, "TE": 0.06}
    rows = [(pos, bool(g.random() < p)) for pos, p in planted.items() for _ in range(6000)]
    df = pl.DataFrame(rows, schema={"position": pl.Utf8, "missed": pl.Boolean}, orient="row")
    got = missed_game_rates(df, MIN_EVENTS)
    for pos, p in planted.items():
        assert got[pos].value is not None and abs(got[pos].value - p) < 0.015


@pytest.mark.parametrize("fn", ["practice", "return", "missed"])
def test_rate_fitters_report_n(fn: str) -> None:
    if fn == "practice":
        got = practice_base_rates(
            pl.DataFrame({"practice": ["Full"] * 300, "played": [True] * 300}), MIN_EVENTS
        )["Full"]
    elif fn == "return":
        got = return_factor(
            pl.DataFrame({"baseline": [0.5] * 300, "return_share": [0.4] * 300}), MIN_EVENTS
        )
    else:
        got = missed_game_rates(
            pl.DataFrame({"position": ["QB"] * 300, "missed": [False] * 300}), MIN_EVENTS
        )["QB"]
    assert got.n == 300
