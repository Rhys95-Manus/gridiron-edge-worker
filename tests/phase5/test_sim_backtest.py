"""PRJ-02 season runner: 2025 raises HoldoutReadError before any read; a game whose inputs
cannot be built is listed with its reason, not guessed; summary columns are per side."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from ge.models.sim import backtest
from ge.store.holdout import HoldoutReadError


def test_holdout_season_raises_before_any_read(monkeypatch: pytest.MonkeyPatch,
                                               tmp_path: Path) -> None:  # fmt: skip
    def boom(*a: Any, **k: Any) -> Any:
        raise AssertionError("read attempted")

    monkeypatch.setattr(backtest, "season_games", boom)
    monkeypatch.setattr(backtest, "build_game", boom)
    with pytest.raises(HoldoutReadError):
        backtest.run_season(2025, n_runs=10, model_version="t", out_root=tmp_path)
    assert not any(tmp_path.iterdir())


def test_unbuildable_game_is_listed_with_reason(monkeypatch: pytest.MonkeyPatch,
                                                tmp_path: Path) -> None:  # fmt: skip
    monkeypatch.setattr(backtest, "season_games", lambda season: ["2024_01_AAA_BBB"])
    monkeypatch.setattr(backtest, "load_window_league", lambda season: object())

    def no_inputs(*a: Any, **k: Any) -> Any:
        raise NotImplementedError("PRJ-01: no off_pass rating for AAA")

    monkeypatch.setattr(backtest, "build_game", no_inputs)
    path = backtest.run_season(2024, n_runs=10, model_version="t", out_root=tmp_path)
    import polars as pl

    df = pl.read_parquet(path)
    assert df["game_id"].to_list() == ["2024_01_AAA_BBB"]
    assert df["skip_reason"][0].startswith("PRJ-01")


def test_summary_columns() -> None:
    cols = backtest.SUMMARY_COLUMNS
    for c in ("home_points", "away_points", "margin_mean", "margin_median", "total_mean",
              "total_median", "margin_sd", "home_plays", "away_pass_att", "ot_rate",
              "prj01a_spread", "prj01a_total"):  # fmt: skip
        assert c in cols
