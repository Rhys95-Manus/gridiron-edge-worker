"""BT-01 version choice: which stored pull of a dataset-season a snapshot reads."""

import datetime as dt
from pathlib import Path

import polars as pl

from ge.ingest.raw import write_raw
from ge.store.vintage import choose_version, observations
from tests.phase2.conftest import load_parquet_fixture

T1 = dt.datetime(2026, 9, 29, 18, 59, tzinfo=dt.UTC)
T2 = dt.datetime(2026, 10, 3, 12, 0, tzinfo=dt.UTC)
T3 = dt.datetime(2026, 10, 10, 12, 0, tzinfo=dt.UTC)


def _slice() -> pl.DataFrame:
    s = load_parquet_fixture("schedules_2023_2026").filter(pl.col("season") == 2026)
    return s.drop("pulled_at", "source")


def _store(root: Path, pulls: list[dt.datetime]) -> None:
    df = _slice()
    for i, t in enumerate(pulls):
        changed = df.with_columns(pl.lit(i).alias("pull_no"))  # each pull differs
        assert write_raw(changed, "schedules", 2026, source="fixture", root=root, pulled_at=t)


def test_latest_on_or_before_as_of(tmp_path: Path) -> None:
    _store(tmp_path, [T1, T2])
    v = choose_version(tmp_path, "schedules", 2026, T2 - dt.timedelta(seconds=1))
    assert v is not None and v.pulled_at == T1 and not v.after_as_of
    v = choose_version(tmp_path, "schedules", 2026, T2)
    assert v is not None and v.pulled_at == T2 and not v.after_as_of


def test_before_first_pull_uses_earliest_and_labels_it(tmp_path: Path) -> None:
    _store(tmp_path, [T1, T2])
    v = choose_version(tmp_path, "schedules", 2026, T1 - dt.timedelta(days=400))
    assert v is not None and v.pulled_at == T1 and v.after_as_of


def test_a_later_pull_never_changes_a_past_choice(tmp_path: Path) -> None:
    _store(tmp_path, [T1, T2])
    past = [T1 - dt.timedelta(days=30), T1, T2 - dt.timedelta(hours=1), T2]
    before = [choose_version(tmp_path, "schedules", 2026, t) for t in past]
    df = _slice().with_columns(pl.lit(99).alias("pull_no"))
    write_raw(df, "schedules", 2026, source="fixture", root=tmp_path, pulled_at=T3)
    after = [choose_version(tmp_path, "schedules", 2026, t) for t in past]
    assert before == after


def test_missing_dataset_season_is_none(tmp_path: Path) -> None:
    assert choose_version(tmp_path, "schedules", 2026, T1) is None


def test_observations_are_every_pull_on_or_before_as_of(tmp_path: Path) -> None:
    _store(tmp_path, [T1, T2, T3])
    got = [v.pulled_at for v in observations(tmp_path, "schedules", 2026, T2)]
    assert got == [T1, T2]
    assert [v.pulled_at for v in observations(tmp_path, "schedules", 2026, None)] == [T1, T2, T3]
