"""Shadow store reader, for the shadow jobs and reports only.

SHD-15: "No fit, threshold, filter or market-type choice reads shadow data, enforced by a test"
(tests/shadow/test_shd14_store.py: no fit or pricer module imports ge.shadow)."""

from __future__ import annotations

from pathlib import Path

import polars as pl


def read_table(version_dir: Path, table: str) -> pl.DataFrame:
    """Every partition of a table, in written_at order; empty when nothing is stored."""
    parts = sorted(
        (version_dir / table).glob("season=*/week=*/written_at=*/part.parquet"),
        key=lambda p: p.parent.name,
    )
    if not parts:
        return pl.DataFrame()
    return pl.concat([pl.read_parquet(p) for p in parts], how="diagonal_relaxed")
