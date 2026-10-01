"""Phase 2 additions outside src/ge/store: weekly rosters ingest and the `ge store` commands.

CLI shape is checked by introspecting the command tree Typer builds, never by reading
printed --help: Rich adds color codes and wraps to the terminal width, so help text differs
between a laptop and CI."""

import typer

from ge.cli import app
from ge.ingest.nflverse import DATASETS

SNAPSHOT_OPTIONS = {"--game", "--as-of", "--pass", "--closing-line-backtest"}


def _group(*path: str) -> typer.core.TyperGroup:
    cmd = typer.main.get_command(app)
    for name in path:
        assert isinstance(cmd, typer.core.TyperGroup), f"{name}: parent is not a command group"
        assert name in cmd.commands, f"`ge {' '.join(path)}`: {name!r} not registered"
        cmd = cmd.commands[name]
    assert isinstance(cmd, typer.core.TyperGroup)
    return cmd


def option_names(*path: str) -> set[str]:
    """Every option string (e.g. --as-of) of the command at `ge <path>`."""
    *parent, leaf = path
    group = _group(*parent)
    assert leaf in group.commands, f"`ge {' '.join(path)}` not registered"
    return {o for p in group.commands[leaf].params for o in p.opts if o.startswith("-")}


def test_weekly_rosters_are_ingested_as_data_04() -> None:
    assert "rosters_weekly" in DATASETS
    assert DATASETS["rosters_weekly"].spec_id == "DATA-04"


def test_store_commands_listed() -> None:
    assert {"build", "snapshot"} <= set(_group("store").commands)


def test_snapshot_command_options() -> None:
    missing = SNAPSHOT_OPTIONS - option_names("store", "snapshot")
    assert not missing, f"ge store snapshot is missing {sorted(missing)}"
