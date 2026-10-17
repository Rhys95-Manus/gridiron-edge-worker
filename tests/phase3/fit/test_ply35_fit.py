"""PLY-35 k (rulings 2026-10-16): split-half on per-game centred gaps (unit player-game, entity
player-team stint in a season, prior 0) on PLY-35's own m grid in games, because no stint-season
reaches BT-02's 25 games a half; r reported separately for seasons inside ffopportunity's stated
training data (<= 2020) and after; PLY-35 stays out of the G3 half-life fit. Units here are
synthetic with a planted k; the grid is passed in (its params follow the spec sync)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
import pytest

from ge.config import load_params
from ge.fit.job import FitConfig, Fitter, Out, Work
from ge.fit.season import unit_file
from ge.fit.splithalf import SplitHalfConfig
from ge.metrics.engine import fit_k_key
from ge.store.holdout import Window
from tests.phase3.fit.synth import rng

LEVEL = float(load_params().fitting.bt_02_no_signal_confidence.value)
SPLIT = SplitHalfConfig(
    m_grid=(25, 50, 100, 200, 400), splits=20, min_entities=30, confidence=LEVEL
)
GRID = (4, 6, 8)  # a test grid in games; the fitted grid comes from params after the sync
REL_TOL = 0.15  # recovered k within 15% of the planted k (as in test_splithalf)
SEASONS = (2019, 2020, 2021, 2022)
WINDOW = Window("S2023", 2023, SEASONS)
STAT = "receiving_yards"
KEY = fit_k_key("PLY-35", STAT, None)


def _cfg(grid: tuple[int, ...] | None) -> FitConfig:
    return FitConfig(SPLIT, (100.0,), (6.0,), 30, 200, grid)


def _work(tmp: Path, k: float, games: int) -> Work:
    """Per season: 400 stints, `games` games each; gap = stint effect + game noise with
    var(noise) / var(effect) = k (so k is in games)."""
    tau = 10.0
    sigma = tau * k**0.5
    for s in SEASONS:
        g = rng(f"ply35/{s}/{k}/{games}")
        eff = g.normal(0.0, tau, 400)
        rows = []
        for i, e in enumerate(eff):
            x = e + g.normal(0.0, sigma, games)
            rows += [(f"p{i}", "T", "all", float(j), float(x[j])) for j in range(games)]
        schema = {"entity_id": pl.Utf8, "team": pl.Utf8, "cell": pl.Utf8, "g": pl.Float64}
        u = pl.DataFrame(rows, schema={**schema, "x": pl.Float64}, orient="row").with_columns(
            pl.lit(1.0).alias("d"), pl.lit(1.0).alias("c"), pl.lit(s).alias("season")
        )
        d = tmp / f"season={s}" / "units"
        d.mkdir(parents=True, exist_ok=True)
        u.write_parquet(d / unit_file("PLY-35", STAT, "units"))
    return Work(tmp)


@pytest.fixture(scope="module")
def fitted(tmp_path_factory: pytest.TempPathFactory) -> tuple[Out, float]:
    k = 6.0
    work = _work(tmp_path_factory.mktemp("ply35"), k, 17)
    out = Out()
    Fitter(work, _cfg(GRID), "t").fit_k(WINDOW, out)
    return out, k


def test_recovers_a_planted_k_in_games(fitted: tuple[Out, float]) -> None:
    out, k = fitted
    v = out.values[KEY]
    assert abs(v["value"] - k) / k < REL_TOL, v
    assert v["seasons"] == list(SEASONS)
    assert "player-games" in v["method"]


def test_r_reported_inside_and_after_the_model_training_data(fitted: tuple[Out, float]) -> None:
    out, _ = fitted
    note = out.notes[KEY]
    assert "r 2019-2020 (inside model training data): m:r = 4:" in note
    assert "r 2021-2022 (after model training data): m:r = 4:" in note


def test_without_a_grid_k_is_missing(tmp_path: Path) -> None:
    out = Out()
    Fitter(_work(tmp_path, 6.0, 17), _cfg(None), "t").fit_k(WINDOW, out)
    assert KEY not in out.values
    assert "no PLY-35 game m grid" in out.missing[KEY]


def test_params_grid_is_the_spec_grid() -> None:
    f = load_params().fitting
    assert f.ply35_m_grid() == (4, 6, 8)
    assert FitConfig.from_params(f).ply35_m_grid == (4, 6, 8)


def test_short_stints_leave_k_missing(tmp_path: Path) -> None:
    out = Out()
    Fitter(_work(tmp_path, 6.0, 7), _cfg(GRID), "t").fit_k(WINDOW, out)  # 7 < 2 x 4 games
    assert KEY not in out.values
    assert "reach 2m games" in out.missing[KEY]


def test_ply35_stays_out_of_the_half_life_fit(fitted: tuple[Out, float], tmp_path: Path) -> None:
    out, _ = fitted
    ks = {KEY: float(out.values[KEY]["value"])}
    work = _work(tmp_path, 6.0, 17)
    o2 = Out()
    hs = Fitter(work, _cfg(GRID), "t").fit_half_lives(WINDOW, ks, o2)
    assert hs == {}
    assert o2.missing["conventions.g3_efficiency_half_life_games"] == (
        "no stat with a fitted k in this class"
    )
    assert np.isfinite(ks[KEY])
