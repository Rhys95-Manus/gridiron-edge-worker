"""Phase 3f leakage on the real store: for 20 hash-ranked completed 2022-2024 games (never 2025,
the BT-07b holdout; decision log 2026-10-16), deleting or shuffling every game at or after the
target in a copy of the store leaves the snapshot's ff_opportunity table byte-identical, and the
table holds no row of the target game or a later one. Marked realdata: run locally."""

from __future__ import annotations

import functools
import hashlib
import io
from pathlib import Path

import polars as pl
import pytest

from ge.ingest.raw import DATA_ROOT, read_latest
from ge.store.known_at import with_kickoff
from ge.store.snapshot import SNAPSHOT_DATASETS, snapshot
from tests.phase2.leakage import perturbed_store

pytestmark = pytest.mark.realdata

N_GAMES = 20  # BUILD_PLAN Phase 2's 20 randomly chosen games, on 2022-2024 here
SEASONS = (2022, 2023, 2024)
FF = "ff_opportunity"


def _sched(season: int) -> pl.DataFrame:
    try:
        return with_kickoff(read_latest(DATA_ROOT, "schedules", season))
    except FileNotFoundError as exc:
        pytest.fail(f"realdata test needs the local store: {exc}")


@functools.cache
def _games() -> tuple[str, ...]:
    ids = [
        g
        for s in SEASONS
        for g in _sched(s).filter(pl.col("result").is_not_null())["game_id"].to_list()
    ]
    return tuple(sorted(ids, key=lambda g: hashlib.sha256(g.encode()).hexdigest())[:N_GAMES])


def _bytes(df: pl.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.sort(df.columns, nulls_last=True).write_parquet(
        buf, compression="uncompressed", statistics=False
    )
    return buf.getvalue()


@pytest.mark.parametrize("i", range(N_GAMES))
@pytest.mark.parametrize("mode", ["delete", "shuffle"])
def test_ff_table_ignores_later_games(i: int, mode: str, tmp_path: Path) -> None:
    gid = _games()[i]
    assert int(gid[:4]) in SEASONS
    base = snapshot(gid)
    ff = base.collect(FF)
    assert ff.height > 0, f"{gid}: no ff_opportunity rows; run `uv run ge ingest nflverse`"
    sched = _sched(int(gid[:4]))
    k0 = sched.filter(pl.col("game_id") == gid)["kickoff_utc"][0]
    late = set(sched.filter(pl.col("kickoff_utc") >= k0)["game_id"].to_list())
    assert not set(ff["game_id"].to_list()) & late
    perturbed_store(
        DATA_ROOT,
        tmp_path,
        game_id=gid,
        as_of=base.as_of,
        mode=mode,  # type: ignore[arg-type]
        datasets=list(SNAPSHOT_DATASETS),
    )
    other = snapshot(gid, as_of=base.as_of, root=tmp_path).collect(FF)
    assert _bytes(other) == _bytes(ff)
