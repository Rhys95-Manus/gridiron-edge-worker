"""Phase 2 additions outside src/ge/store: weekly rosters ingest and the `ge store` commands."""

from typer.testing import CliRunner

from ge.cli import app
from ge.ingest.nflverse import DATASETS


def test_weekly_rosters_are_ingested_as_data_04() -> None:
    assert "rosters_weekly" in DATASETS
    assert DATASETS["rosters_weekly"].spec_id == "DATA-04"


def test_store_commands_listed() -> None:
    r = CliRunner().invoke(app, ["store", "--help"])
    assert r.exit_code == 0, r.output
    assert "build" in r.output and "snapshot" in r.output


def test_snapshot_command_options() -> None:
    r = CliRunner().invoke(app, ["store", "snapshot", "--help"])
    assert r.exit_code == 0, r.output
    for opt in ("--game", "--as-of", "--pass", "--closing-line-backtest"):
        assert opt in r.output
