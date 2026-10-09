"""`ge fit` end to end on the Phase 3 real-data store slice (tests/phase3/fixtures/store):

- leakage (BUILD_PLAN 3e): a season-S fit is byte-identical when every season >= S is deleted
  or altered in a copy of the store
- 2025: a planted holdout partition changes nothing, and a fit can't be asked to read it
- determinism (rule 6): two fresh runs write byte-identical files

The slice holds 2023 in full and 2024 weeks 1-8, so the window used here is S2024 trained on
2023 alone: many values come out missing (too few entities), which these tests don't mind."""

from __future__ import annotations

import datetime as dt
import shutil
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from ge.fit.history import Reader
from ge.fit.job import run_fit
from ge.store.holdout import HoldoutReadError, Window
from tests.phase3.conftest import STORE

AS_OF = dt.datetime(2026, 10, 8, tzinfo=dt.UTC)
WINDOW = Window("S2024", 2024, (2023,))


def _fit(store: Path, tmp: Path, tag: str) -> bytes:
    run_fit(
        [WINDOW],
        "t",
        AS_OF,
        root=store,
        work_root=tmp / f"work_{tag}",
        out_root=tmp / f"out_{tag}",
        commit="test",
    )
    return (tmp / f"out_{tag}" / "t" / "S2024.yaml").read_bytes()


def _copy(tmp: Path, name: str) -> Path:
    dst = tmp / name
    shutil.copytree(STORE, dst)
    return dst


@pytest.fixture(scope="module")
def base(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, bytes]:
    tmp = tmp_path_factory.mktemp("fit")
    return tmp, _fit(STORE, tmp, "base")


def test_fit_writes_a_loadable_file(base: tuple[Path, bytes]) -> None:
    from ge.config import FittedFile, _check_fitted, _read_yaml, load_params

    tmp, _ = base
    p = tmp / "out_base" / "t" / "S2024.yaml"
    f = FittedFile.model_validate(_read_yaml(p))
    _check_fitted(f, p, load_params())
    assert f.seasons == [2023] and f.test_season == 2024
    assert f.values, "no value fitted at all"
    assert all(set(v.seasons) <= {2023} for v in f.values.values())


def test_deterministic(base: tuple[Path, bytes]) -> None:
    tmp, first = base
    assert _fit(STORE, tmp, "again") == first


def test_seasons_at_or_after_s_deleted(base: tuple[Path, bytes]) -> None:
    tmp, first = base
    store = _copy(tmp, "store_deleted")
    for ds in store.iterdir():
        for part in ds.glob("season=*"):
            if part.name.split("=")[1].isdigit() and int(part.name.split("=")[1]) >= 2024:
                shutil.rmtree(part)
    assert _fit(store, tmp, "deleted") == first


def test_seasons_at_or_after_s_altered_and_holdout_planted(base: tuple[Path, bytes]) -> None:
    tmp, first = base
    store = _copy(tmp, "store_altered")
    g = np.random.default_rng(7)
    for part in (store / "pbp" / "season=2024").glob("pulled_at=*/part.parquet"):
        df = pl.read_parquet(part)
        df = df.with_columns(pl.Series("epa", g.normal(0, 5, df.height)))
        df.write_parquet(part)
    # A planted 2025 partition (the holdout): a fit must never read it.
    src = next((store / "pbp" / "season=2023").glob("pulled_at=*"))
    shutil.copytree(src, store / "pbp" / "season=2025" / src.name)
    assert _fit(store, tmp, "altered") == first


def test_reader_refuses_holdout_and_test_season() -> None:
    r = Reader(STORE, WINDOW, AS_OF)
    for s in (2024, 2025):
        with pytest.raises(HoldoutReadError):
            r.version("pbp", s)
    with pytest.raises(HoldoutReadError, match="BT-07b"):
        Reader(STORE, Window.live(), AS_OF).version("pbp", 2025)
