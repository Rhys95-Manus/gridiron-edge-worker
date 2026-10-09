"""BT-07b in Phase 3e: 2025 is never computed during development. The metric engine refuses a
2025 target season, the fitters refuse any training window that reaches 2025 (or the test
season), and the fitted-params loader refuses season 2025 (user ruling 2026-10-07: the guard
sits in the metric engine and the fitters, not in snapshot())."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from ge.config import load_params
from ge.store.holdout import HoldoutReadError, Window, holdout_season, refuse_holdout
from ge.store.snapshot import Snapshot

BT = load_params().backtest
HOLDOUT = int(BT.bt_01_holdout_season.value)
FIRST_TRAIN = int(BT.bt_01_first_training_season.value)
FIRST_TEST = int(BT.bt_01_first_test_season.value)
LAST_TEST = int(BT.bt_01_last_test_season.value)


def test_holdout_season_comes_from_params() -> None:
    assert holdout_season() == HOLDOUT


def test_refuse_holdout_only_the_holdout() -> None:
    with pytest.raises(HoldoutReadError, match="BT-07b"):
        refuse_holdout(HOLDOUT, "test")
    refuse_holdout(HOLDOUT - 1, "test")
    refuse_holdout(HOLDOUT + 1, "test")


def test_walk_forward_windows() -> None:
    ws = Window.walk_forward()
    assert [w.name for w in ws] == [f"S{s}" for s in range(FIRST_TEST, LAST_TEST + 1)] + ["live"]
    for w in ws[:-1]:
        assert w.test_season is not None
        assert w.seasons == tuple(range(FIRST_TRAIN, w.test_season))
    live = ws[-1]
    assert live.test_season is None
    assert live.seasons == tuple(range(FIRST_TRAIN, LAST_TEST + 1))
    assert all(HOLDOUT not in w.seasons for w in ws)


def test_window_refuses_test_season_and_later() -> None:
    with pytest.raises(HoldoutReadError, match="season 2023"):
        Window("bad", 2023, (2021, 2022, 2023))
    with pytest.raises(HoldoutReadError, match="BT-07b"):
        Window("bad", None, (2024, HOLDOUT))


def test_window_check_read() -> None:
    w = Window("S2023", 2023, (2021, 2022))
    w.check_read(2022)
    for s in (2023, 2024, HOLDOUT):
        with pytest.raises(HoldoutReadError):
            w.check_read(s)


def _fake_snapshot(season: int) -> Snapshot:
    t = dt.datetime(season, 9, 10, tzinfo=dt.UTC)
    return Snapshot(
        game_id=f"{season}_01_AAA_BBB",
        season=season,
        week=1,
        kickoff_utc=t,
        as_of=t,
        pass_="decision",
        closing_line_backtest=False,
        labels=(),
        vintages=(),
        _loaders={},
    )


def test_build_context_refuses_holdout_target() -> None:
    from ge.metrics.context import build_context

    with pytest.raises(HoldoutReadError, match="BT-07b"):
        build_context(_fake_snapshot(HOLDOUT))


def test_run_metrics_refuses_holdout_before_reading(tmp_path: Path) -> None:
    from ge.metrics.job import run_metrics

    # An empty store: anything that read data first would fail differently.
    with pytest.raises(HoldoutReadError, match="BT-07b"):
        run_metrics(HOLDOUT, 1, root=tmp_path, out_dir=tmp_path / "out")
