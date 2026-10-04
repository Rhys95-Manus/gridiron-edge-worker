"""DATA-04 nflverse teams table (spec G4, docs synced 2026-10-04): relocated teams keep their
history by franchise. Ingested once for all seasons; snapshots expose team_abbr and team_id."""

from __future__ import annotations

from ge.ingest import nflverse
from ge.store.snapshot import FRANCHISE_COLUMNS
from tests.phase3.conftest import STORE


def test_teams_is_a_seasonless_data_04_dataset() -> None:
    ds = nflverse.DATASETS["teams"]
    assert ds.spec_id == "DATA-04"
    assert ds.seasonless


def test_snapshot_teams_table_is_franchise_ids_only(main_snap) -> None:  # type: ignore[no-untyped-def]
    df = main_snap.collect("teams")
    assert tuple(df.columns) == FRANCHISE_COLUMNS == ("team_abbr", "team_id")
    assert df.height > 0 and df.null_count().sum_horizontal()[0] == 0
    assert df["team_abbr"].n_unique() == df.height
    # every team in the fixture's play-by-play is in the table
    pbp = main_snap.collect("pbp")
    assert set(pbp["posteam"].drop_nulls().unique().to_list()) <= set(df["team_abbr"].to_list())
    assert any("teams: franchise IDs" in lb for lb in main_snap.labels)


def test_fixture_store_has_teams() -> None:
    assert (STORE / "teams" / f"season={nflverse.SEASONLESS}").exists()
