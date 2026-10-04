"""Rule 5 for metrics: a game's metric values are byte-identical when every game at or after
it is deleted or shuffled in a copy of the store (reuses the Phase 2 leakage harness)."""

from __future__ import annotations

import io
from pathlib import Path

import polars as pl
import pytest

from ge.metrics.context import build_context
from ge.metrics.registry import REGISTRY, raw
from ge.store.snapshot import snapshot
from tests.phase2.leakage import perturbed_store
from tests.phase3.conftest import MAIN_WEEK, STORE, first_game

SPEC_IDS = sorted(sid for sid, e in REGISTRY.items() if not e.paid)


def _bytes(df: pl.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.sort(df.columns, nulls_last=True).write_parquet(
        buf, compression="uncompressed", statistics=False
    )
    return buf.getvalue()


@pytest.mark.parametrize("mode", ["delete", "shuffle"])
def test_metrics_ignore_later_games(tmp_path: Path, mode: str) -> None:
    gid = first_game(MAIN_WEEK)
    base = snapshot(gid, root=STORE)
    dst = tmp_path / "store"
    datasets = sorted(p.name for p in STORE.iterdir() if p.is_dir())
    perturbed_store(STORE, dst, game_id=gid, as_of=base.as_of, mode=mode, datasets=datasets)  # type: ignore[arg-type]
    pert = snapshot(gid, as_of=base.as_of, root=dst)
    a, b = build_context(base), build_context(pert)
    for sid in SPEC_IDS:
        assert _bytes(raw(a, sid)) == _bytes(raw(b, sid)), sid
