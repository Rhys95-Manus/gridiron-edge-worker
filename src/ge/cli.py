"""`ge` command line: one command per job. Every job is a placeholder until its phase is built."""

from __future__ import annotations

from typing import Annotated

import typer

app = typer.Typer(
    help="Gridiron Edge worker. Data: nflverse; charting: FTN Data via nflverse.",
    no_args_is_help=True,
    add_completion=False,
)

Season = Annotated[int | None, typer.Option(help="Season year, e.g. 2024.")]
Week = Annotated[int | None, typer.Option(help="Week number.")]
AsOf = Annotated[
    str | None,
    typer.Option("--as-of", help="ISO timestamp; only data pulled at or before it is read."),
]


def _not_built(job: str, phase: str) -> None:
    raise NotImplementedError(f"ge {job}: not built yet ({phase} in docs/BUILD_PLAN.md)")


@app.command()
def ingest(season: Season = None, week: Week = None, as_of: AsOf = None) -> None:
    """Pull nflverse, NWS and Kalshi public data (DATA-01 to DATA-09)."""
    _not_built("ingest", "Phase 1")


@app.command()
def metrics(season: Season = None, week: Week = None, as_of: AsOf = None) -> None:
    """Compute team, player and coaching metrics (OFF-, DEF-, PLY-, COA-)."""
    _not_built("metrics", "Phase 3")


@app.command()
def simulate(season: Season = None, week: Week = None, as_of: AsOf = None) -> None:
    """Run the game simulation (PRJ-02)."""
    _not_built("simulate", "Phase 5")


@app.command()
def price(season: Season = None, week: Week = None, as_of: AsOf = None) -> None:
    """Price Kalshi markets (PRJ-03 to PRJ-06)."""
    _not_built("price", "Phase 6")


@app.command()
def sync(season: Season = None, week: Week = None, as_of: AsOf = None) -> None:
    """Write projections and recommendations to Base44."""
    _not_built("sync", "Phase 9")


@app.command()
def backtest(season: Season = None, week: Week = None, as_of: AsOf = None) -> None:
    """Walk-forward backtest and Historical Performance Report (BT-01 to BT-07)."""
    _not_built("backtest", "Phase 8")


if __name__ == "__main__":
    app()
