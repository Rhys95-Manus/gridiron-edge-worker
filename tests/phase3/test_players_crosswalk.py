"""DATA-04 player ID crosswalk (user decision 2026-10-02): nflverse's players table, ingested
once for all seasons, and exposed by snapshots as ID columns only."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from ge.ingest import nflverse
from ge.ingest.raw import partitions
from tests.phase3.conftest import STORE, store_table


def test_players_is_a_seasonless_data_04_dataset() -> None:
    ds = nflverse.DATASETS["players"]
    assert ds.spec_id == "DATA-04"
    assert ds.seasonless


def test_players_ingest_stores_one_partition_and_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = store_table("players", nflverse.SEASONLESS).drop("pulled_at", "source")
    calls: list[int] = []

    def loader(season: int) -> pl.DataFrame:
        calls.append(season)
        return real

    monkeypatch.setitem(
        nflverse.DATASETS, "players", nflverse.Dataset("DATA-04", loader, seasonless=True)
    )
    first = nflverse.ingest_nflverse([2023, 2024], ["players"], root=tmp_path)
    again = nflverse.ingest_nflverse([2023, 2024], ["players"], root=tmp_path)
    assert [r.status for r in first] == ["written"]
    assert [r.status for r in again] == ["unchanged"]
    assert calls == [nflverse.SEASONLESS, nflverse.SEASONLESS]
    assert len(partitions(tmp_path, "players", nflverse.SEASONLESS)) == 1
    assert not (tmp_path / "players" / "season=2023").exists()


def test_snapshot_players_table_is_id_crosswalk_only(main_snap) -> None:  # type: ignore[no-untyped-def]
    df = main_snap.collect("players")
    assert df.columns == ["gsis_id", "pfr_id"]
    assert df.height > 0
    assert df.null_count().sum_horizontal()[0] == 0
    assert df.n_unique() == df.height
    assert any("players: ID crosswalk" in lb for lb in main_snap.labels)


def test_crosswalk_maps_nearly_every_snap_count_row(main_snap) -> None:  # type: ignore[no-untyped-def]
    snaps = main_snap.collect("snap_counts")
    ids = set(main_snap.collect("players")["pfr_id"].to_list())
    unmatched = snaps.filter(~pl.col("pfr_player_id").is_in(list(ids)))
    print(f"snap rows without a gsis_id: {unmatched.height} of {snaps.height}")
    assert unmatched.height <= 0.01 * snaps.height, unmatched.select("player", "team").head(20)


def test_fixture_store_has_players() -> None:
    assert (STORE / "players" / f"season={nflverse.SEASONLESS}").exists()
