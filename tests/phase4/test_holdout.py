"""BT-07b in Phase 4: the ratings, the window fit, the walk-forward report and the CLI never
read the holdout season. Each refuses before any read; the game ID below is a made-up string
in the nflverse format, not a real game."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ge.cli import app
from ge.config import load_params
from ge.models.ratings import ratings_for_game
from ge.models.ratings_report import ReportSettings, walk_forward, write_report
from ge.models.ratings_window import fit_window
from ge.store.holdout import HoldoutReadError, Window

HOLDOUT = int(load_params().backtest.bt_01_holdout_season.value)
FAKE_GAME = f"{HOLDOUT}_01_AAA_BBB"


def test_ratings_for_game_refuses(tmp_path: Path) -> None:
    with pytest.raises(HoldoutReadError):
        ratings_for_game(FAKE_GAME, root=tmp_path / "empty")


def test_walk_forward_and_report_refuse(tmp_path: Path) -> None:
    with pytest.raises(HoldoutReadError):
        walk_forward([HOLDOUT - 1, HOLDOUT], root=tmp_path / "empty")
    settings = ReportSettings((HOLDOUT,), (1.0,), 2)
    with pytest.raises(HoldoutReadError):
        write_report([HOLDOUT - 1], settings, root=tmp_path / "empty", out_dir=tmp_path)


def test_window_fit_cannot_include_the_holdout(tmp_path: Path) -> None:
    with pytest.raises(HoldoutReadError):
        Window("bad", None, (HOLDOUT - 1, HOLDOUT))
    with pytest.raises(HoldoutReadError):
        fit_window(
            Window.for_test_season(HOLDOUT), dt.datetime(2026, 10, 12, tzinfo=dt.UTC), root=tmp_path
        )


@pytest.mark.parametrize(
    "args",
    [
        ["ratings", "--season", str(HOLDOUT), "--through-week", "5"],
        ["ratings-report", "--seasons", f"{HOLDOUT - 1}-{HOLDOUT}"],
    ],
)
def test_cli_refuses(args: list[str], tmp_path: Path) -> None:
    result = CliRunner().invoke(app, [*args, "--data-root", str(tmp_path / "empty")])
    assert isinstance(result.exception, HoldoutReadError), result.output
