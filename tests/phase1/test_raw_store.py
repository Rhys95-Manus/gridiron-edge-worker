"""Raw Parquet store: dataset/season/pulled_at partitions, pulled_at (UTC) and source columns,
and an unchanged re-pull writes nothing (idempotent)."""

import datetime as dt
from pathlib import Path

import polars as pl

from ge.ingest.raw import partitions, read_latest, write_raw

T1 = dt.datetime(2026, 9, 1, 12, 0, tzinfo=dt.UTC)
T2 = dt.datetime(2026, 9, 2, 12, 0, tzinfo=dt.UTC)


def _df(n: int) -> pl.DataFrame:
    return pl.DataFrame({"game_id": [f"G{i}" for i in range(n)], "x": list(range(n))})


def test_write_adds_pulled_at_and_source(tmp_path: Path) -> None:
    path = write_raw(_df(3), "demo", 2024, source="unit-test", root=tmp_path, pulled_at=T1)
    assert path is not None
    out = pl.read_parquet(path)
    assert out["source"].unique().to_list() == ["unit-test"]
    assert out["pulled_at"].dtype == pl.Datetime("us", "UTC")
    assert out["pulled_at"].unique().to_list() == [T1]
    assert "season=2024" in str(path) and "demo" in str(path)


def test_unchanged_repull_writes_nothing(tmp_path: Path) -> None:
    assert write_raw(_df(3), "demo", 2024, source="s", root=tmp_path, pulled_at=T1)
    assert write_raw(_df(3), "demo", 2024, source="s", root=tmp_path, pulled_at=T2) is None
    assert len(partitions(tmp_path, "demo", 2024)) == 1
    assert read_latest(tmp_path, "demo", 2024).height == 3


def test_changed_repull_adds_a_new_version(tmp_path: Path) -> None:
    write_raw(_df(3), "demo", 2024, source="s", root=tmp_path, pulled_at=T1)
    write_raw(_df(4), "demo", 2024, source="s", root=tmp_path, pulled_at=T2)
    assert len(partitions(tmp_path, "demo", 2024)) == 2
    latest = read_latest(tmp_path, "demo", 2024)
    assert latest.height == 4
    assert latest["pulled_at"].unique().to_list() == [T2]


def test_naive_pulled_at_is_rejected(tmp_path: Path) -> None:
    try:
        write_raw(
            _df(1),
            "demo",
            2024,
            source="s",
            root=tmp_path,
            pulled_at=dt.datetime(2026, 9, 1, 12, 0),
        )
    except ValueError:
        return
    raise AssertionError("pulled_at must be timezone-aware UTC")
