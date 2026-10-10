"""BT-02 method, Phase 3e v2 (spec synced 2026-10-10): what a stat's split-half is measured around.

- residual(): a stat with a slot or role prior is tested on each player's residual from that
  prior: unit x becomes x - p * d (p = the prior of the unit's cell and its game's slot, fitted
  in the same window), so a half's value is his value minus the d-weighted prior.
- center_season_cell(): a multi-cell stat is centred on each cell's league mean in the same
  season: x becomes x - mu * d, mu = sum x / sum d over every unit of that season and cell, so
  differences between cells and league drift between seasons never count as entity signal.

Sums are sequential over sorted rows (np.add.reduceat), so results don't depend on row order
(rule 6)."""

from __future__ import annotations

import numpy as np
import polars as pl


def residual(units: pl.DataFrame) -> pl.DataFrame:
    """x - p * d; the prior column `p` is dropped. Rows without a prior must be removed first."""
    return units.with_columns((pl.col("x") - pl.col("p") * pl.col("d")).alias("x")).drop("p")


def cell_means(units: pl.DataFrame) -> pl.DataFrame:
    """Per (season, cell): mu = sum x / sum d over every unit."""
    s = units.select("season", "cell", pl.col("x").cast(pl.Float64), pl.col("d").cast(pl.Float64))
    s = s.sort("season", "cell", "x", "d")
    key = (s["season"].cast(pl.Utf8) + "|" + s["cell"]).to_numpy()
    starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    sx = np.add.reduceat(s["x"].to_numpy(), starts)
    sd = np.add.reduceat(s["d"].to_numpy(), starts)
    return pl.DataFrame(
        {
            "season": s["season"].gather(starts.tolist()),
            "cell": s["cell"].gather(starts.tolist()),
            "mu": np.divide(sx, sd, out=np.zeros_like(sx), where=sd != 0),
        }
    )


def center_season_cell(units: pl.DataFrame) -> pl.DataFrame:
    """x - mu * d with mu the unit's (season, cell) league mean."""
    if units.is_empty():
        return units
    mu = cell_means(units)
    return (
        units.join(mu, on=["season", "cell"], how="left")
        .with_columns((pl.col("x") - pl.col("mu") * pl.col("d")).alias("x"))
        .drop("mu")
    )
