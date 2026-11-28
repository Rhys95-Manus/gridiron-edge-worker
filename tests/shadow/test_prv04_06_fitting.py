"""PRV-04 to PRV-06 maximum-likelihood fits (PRV-10) and the pv0 params_fitted files, on
synthetic data only (made-up IDs; no real players or games). Random draws here are test data,
from fixed seeds."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np
import polars as pl
import pytest
from scipy import special as spf
from scipy import stats as sps

from ge.config import FittedFile, _check_fitted, _read_yaml, load_params
from ge.pricer_v0.distributions import EmpiricalRatio
from ge.pricer_v0.fitting import (
    FIT_VERSION,
    NotFitted,
    empirical_ratio_fit,
    fit_window,
    hurdle_gamma_mle,
    nb_size_mle,
    read_fit_file,
    shifted_gamma_mle,
    write_fit_file,
)
from ge.pricer_v0.training import YardsPools, pricer_window

MIN_N = int(load_params().pricer_v0.prv_min_player_games_per_position_group.value)


def _nb_ll(y: np.ndarray, mu: np.ndarray, r: float) -> float:
    return float(
        np.sum(
            spf.gammaln(y + r)
            - spf.gammaln(r)
            - spf.gammaln(y + 1)
            + r * np.log(r / (r + mu))
            + y * np.log(mu / (r + mu))
        )
    )


# ---- negative binomial size (PRV-04, and PRV-06's carries) ----


def test_nb_size_recovers_the_size_and_is_a_maximum() -> None:
    rng = np.random.default_rng(7)
    mu = rng.uniform(1.0, 8.0, 20000)
    r_true = 4.0
    y = rng.negative_binomial(r_true, r_true / (r_true + mu)).astype(float)
    r = nb_size_mle(y, mu)
    assert isinstance(r, float)
    assert r == pytest.approx(r_true, rel=0.1)
    best = _nb_ll(y, mu, r)
    assert best >= _nb_ll(y, mu, r * 1.01) and best >= _nb_ll(y, mu, r / 1.01)


def test_nb_size_with_no_over_dispersion_is_not_fitted() -> None:
    mu = np.array([2.0, 3.0, 4.0, 5.0] * 50)
    y = mu.copy()  # variance 0 around the mean: no finite size maximises the likelihood
    got = nb_size_mle(y, mu)
    assert isinstance(got, NotFitted)
    assert "over-dispersed" in got.reason


# ---- hurdle gamma (PRV-05), interval likelihood ----


def _hurdle_ll(y: np.ndarray, mu: np.ndarray, alpha: float, pi: float) -> float:
    pos = y > 0
    theta = mu[pos] / ((1 - pi) * alpha)
    lo = np.maximum(y[pos] - 0.5, 0.0)
    hi = y[pos] + 0.5
    mass = sps.gamma.cdf(hi, alpha, scale=theta) - sps.gamma.cdf(lo, alpha, scale=theta)
    return float(np.sum(np.log(mass)))


def _hurdle_data(seed: int, n: int, alpha: float, pi: float) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    mu = rng.uniform(10.0, 80.0, n)
    zero = rng.uniform(size=n) < pi
    g = rng.gamma(alpha, mu / ((1 - pi) * alpha))
    y = np.where(zero, -rng.integers(0, 3, n), np.maximum(np.floor(g + 0.5), 1.0))
    return y.astype(float), mu


def test_hurdle_zero_mass_is_the_share_at_or_below_zero() -> None:
    y, mu = _hurdle_data(3, 4000, 2.0, 0.2)
    _alpha, pi = hurdle_gamma_mle(y, mu)
    assert pi == float(np.mean(y <= 0))


def test_hurdle_alpha_maximises_the_interval_likelihood() -> None:
    y, mu = _hurdle_data(5, 6000, 2.0, 0.25)
    alpha, pi = hurdle_gamma_mle(y, mu)
    assert alpha == pytest.approx(2.0, rel=0.15)
    best = _hurdle_ll(y, mu, alpha, pi)
    grid = np.linspace(alpha * 0.8, alpha * 1.2, 81)
    assert best >= max(_hurdle_ll(y, mu, a, pi) for a in grid) - 1e-6


def test_hurdle_with_no_positive_yards_is_not_fitted() -> None:
    got = hurdle_gamma_mle(np.zeros(600), np.full(600, 5.0))
    assert isinstance(got, NotFitted)


# ---- shifted gamma (PRV-06), interval likelihood ----


def _shift_ll(y: np.ndarray, mu: np.ndarray, alpha: float, s: float) -> float:
    theta = (mu + s) / alpha
    lo = np.maximum(y - 0.5 + s, 0.0)
    hi = y + 0.5 + s
    mass = sps.gamma.cdf(hi, alpha, scale=theta) - sps.gamma.cdf(lo, alpha, scale=theta)
    return float(np.sum(np.log(mass)))


def test_shifted_gamma_is_a_maximum_with_the_shift_covering_every_loss() -> None:
    rng = np.random.default_rng(11)
    mu = rng.uniform(5.0, 90.0, 6000)
    a_true, s_true = 1.5, 8.0
    g = rng.gamma(a_true, (mu + s_true) / a_true)
    y = np.floor(g - s_true + 0.5)
    alpha, s = shifted_gamma_mle(y, mu)
    assert s >= 0 and s > -y.min() - 0.5
    assert alpha == pytest.approx(a_true, rel=0.15)
    assert s == pytest.approx(s_true, rel=0.25)
    best = _shift_ll(y, mu, alpha, s)
    for da, ds in ((1.01, 1.0), (1 / 1.01, 1.0), (1.0, 1.01), (1.0, 1 / 1.01)):
        assert best >= _shift_ll(y, mu, alpha * da, s * ds) - 1e-6


# ---- empirical ratio (PRV-05/06) ----


def test_empirical_ratio_bins_are_linear_deciles_and_interior_edges_go_up() -> None:
    mu = np.arange(1.0, 101.0)  # 1..100
    actual = 2.0 * mu
    actual[0] = 0.0
    er = empirical_ratio_fit(mu, actual)
    assert isinstance(er, EmpiricalRatio)
    assert er.edges == tuple(float(x) for x in np.quantile(mu, np.linspace(0.0, 1.0, 11)))
    assert len(er.ratios) == 10
    flat = sorted(r for b in er.ratios for r in b)
    assert flat == sorted((actual / mu).tolist())
    # every training mu sits in the bin bin_of gives it
    for m, a in zip(mu, actual, strict=True):
        assert a / m in er.ratios[er.bin_of(float(m))]


def test_empirical_ratio_leaves_out_mu_at_or_below_zero() -> None:
    mu = np.concatenate([np.arange(1.0, 21.0), [0.0, -1.0]])
    actual = np.ones(mu.size)
    er = empirical_ratio_fit(mu, actual)
    assert sum(len(b) for b in er.ratios) == 20


def test_empirical_ratio_with_tied_edges_stops() -> None:
    mu = np.array([1.0] * 50 + [2.0] * 50)
    with pytest.raises(ValueError, match="PRV-0"):
        empirical_ratio_fit(mu, mu)


# ---- one window ----

GROUPS = ("RB", "TE", "WR")


def _rows(stat: str, n_by_group: dict[str, int], seed: int) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    out = []
    for g, n in n_by_group.items():
        mu = rng.uniform(1.0, 6.0, n) if stat == "receptions" else rng.uniform(10.0, 70.0, n)
        if stat == "receptions":
            y = rng.negative_binomial(5.0, 5.0 / (5.0 + mu)).astype(float)
        elif stat == "receiving_yards":
            y = np.where(rng.uniform(size=n) < 0.2, 0.0, np.ceil(rng.gamma(2.0, mu / 1.6)))
        else:
            y = np.floor(rng.gamma(1.5, (mu + 6.0) / 1.5) - 6.0 + 0.5)
        carries = rng.uniform(1.0, 15.0, n)
        out.append(
            pl.DataFrame(
                {
                    "game_id": [f"2021_{i % 18 + 1:02d}_TMA_TMB" for i in range(n)],
                    "team": ["TMA"] * n,
                    "gsis_id": [f"{g}{i:05d}" for i in range(n)],
                    "group": [g] * n,
                    "mu": mu,
                    "carries_mean": carries,
                    "actual": y,
                    "carries": rng.negative_binomial(3.0, 3.0 / (3.0 + carries)).astype(float),
                }
            )
        )
    return pl.concat(out)


def _pools() -> YardsPools:
    vals = tuple(float(v) for v in range(-3, 30))
    return YardsPools(
        window="S2022",
        seasons=(2021,),
        per_reception={g: vals for g in GROUPS},
        per_carry={g: vals for g in GROUPS},
        dropped_receptions=0,
        dropped_carries=0,
    )


def _window_fit(n_te: int):  # type: ignore[no-untyped-def]
    sizes = {"RB": MIN_N, "TE": n_te, "WR": MIN_N + 200}
    rows = {
        s: _rows(s, sizes, i)
        for i, s in enumerate(("receptions", "receiving_yards", "rushing_yards"))
    }
    return fit_window(pricer_window("S2022"), rows, _pools())


def test_fit_window_applies_the_500_player_game_rule_per_family_and_group() -> None:
    f = _window_fit(MIN_N - 1)
    assert set(f.nb_size) == {"RB", "WR"}
    assert set(f.hurdle) == {"RB", "WR"} and set(f.shifted) == {"RB", "WR"}
    assert set(f.carries_size) == {"RB", "WR"}
    assert {g for (_, g) in f.empirical} == {"RB", "WR"}
    assert set(f.compound_receiving) == {"RB", "WR"}
    te = [k for k in f.missing if k.endswith("/TE")]
    assert te and all(f"n = {MIN_N - 1}" in f.missing[k] for k in te)
    assert f.n["fit:pv0/PRV-04/negative_binomial/size/receptions/WR"] == MIN_N + 200


def test_fit_window_fits_every_family_at_exactly_the_minimum() -> None:
    f = _window_fit(MIN_N)
    assert set(f.nb_size) == set(GROUPS) and not f.missing


def test_fit_file_round_trips_and_passes_the_provenance_checks(tmp_path: Path) -> None:
    f = _window_fit(MIN_N - 1)
    folder = tmp_path / FIT_VERSION
    write_fit_file(
        f,
        folder,
        data_as_of="2026-09-29T18:59:09+00:00",
        data_digest="d" * 64,
        code_commit="abc+uncommitted",
    )
    path = folder / "S2022.yaml"
    assert "&id" not in path.read_text(encoding="utf-8")  # plain lists, as in v4, no anchors
    ff = FittedFile.model_validate(_read_yaml(path))
    _check_fitted(ff, path, load_params())
    assert ff.fit_version == FIT_VERSION and ff.seasons == [2021] and ff.test_season == 2022
    assert all(v.status == "fitted" and v.seasons == [2021] for v in ff.values.values())
    side = folder / "S2022_empirical_ratio.parquet"
    digest = hashlib.sha256(side.read_bytes()).hexdigest()
    edge_keys = [k for k in ff.values if "/empirical_ratio/" in k]
    assert edge_keys and all(digest in ff.values[k].method for k in edge_keys)
    back = read_fit_file("S2022", folder)
    assert back.nb_size == f.nb_size and back.carries_size == f.carries_size
    assert back.hurdle == f.hurdle and back.shifted == f.shifted
    assert back.empirical == f.empirical
    assert back.compound_receiving == f.compound_receiving
    assert back.missing == f.missing


def test_read_fit_file_refuses_a_changed_sidecar(tmp_path: Path) -> None:
    f = _window_fit(MIN_N)
    folder = tmp_path / FIT_VERSION
    write_fit_file(f, folder, data_as_of="x", data_digest="d" * 64, code_commit="c")
    side = folder / "S2022_empirical_ratio.parquet"
    pl.read_parquet(side).with_columns(pl.col("ratio") * 2).write_parquet(side)
    with pytest.raises(ValueError, match="sha256"):
        read_fit_file("S2022", folder)


def test_nb_log_likelihood_helper_matches_scipy() -> None:
    # guards the test helper itself
    y = np.array([0.0, 1.0, 5.0])
    mu = np.array([1.0, 2.0, 3.0])
    r = 2.5
    ref = float(np.sum(sps.nbinom.logpmf(y, r, r / (r + mu))))
    assert _nb_ll(y, mu, r) == pytest.approx(ref, abs=1e-10)
    assert math.isfinite(ref)
