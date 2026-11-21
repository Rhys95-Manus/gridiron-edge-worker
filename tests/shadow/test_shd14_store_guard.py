"""SHD-14: "The writer refuses any path under data/raw." Tested before any other store code."""

from pathlib import Path

import pytest

from ge.config import REPO_ROOT
from ge.shadow.store import SHADOW_BASE, StorePathError, check_store_path

RAW = REPO_ROOT / "data" / "raw"


@pytest.mark.parametrize(
    "path",
    [
        RAW,
        RAW / "schedules",
        RAW / "kalshi_markets" / "season=2026" / "x" / "part.parquet",
        SHADOW_BASE / ".." / "raw" / "x",  # traversal back into data/raw
    ],
)
def test_refuses_data_raw(path: Path) -> None:
    with pytest.raises(StorePathError, match="data/raw"):
        check_store_path(path)


def test_refuses_data_raw_even_with_a_base_that_contains_it() -> None:
    with pytest.raises(StorePathError, match="data/raw"):
        check_store_path(RAW / "x", base=REPO_ROOT / "data")


def test_refuses_data_raw_resolved_target() -> None:
    """data/raw may be a junction to another checkout: its resolved target is refused too."""
    with pytest.raises(StorePathError, match="data/raw"):
        check_store_path(RAW.resolve() / "x", base=RAW.resolve().parent)


@pytest.mark.parametrize(
    "path",
    [REPO_ROOT / "data" / "other", REPO_ROOT / "src", SHADOW_BASE.parent, SHADOW_BASE / ".."],
)
def test_refuses_outside_data_shadow(path: Path) -> None:
    with pytest.raises(StorePathError, match="outside"):
        check_store_path(path)


def test_accepts_inside_data_shadow() -> None:
    p = SHADOW_BASE / "v0" / "snapshots"
    assert check_store_path(p) == p.resolve()


def test_accepts_inside_a_test_base(tmp_path: Path) -> None:
    p = tmp_path / "v0" / "snapshots"
    assert check_store_path(p, base=tmp_path) == p.resolve()
