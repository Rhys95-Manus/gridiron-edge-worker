"""DATA-04 nflverse combine data (ruling 2026-10-04: combine is under DATA-04; ingested from
2000, the first season nflverse publishes). Feeds PLY-34 as a prior only."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from ge.config import load_ingest
from ge.ingest import nflverse
from ge.ingest.raw import partitions


def test_combine_is_a_data_04_dataset_from_2000() -> None:
    ds = nflverse.DATASETS["combine"]
    cfg = load_ingest().nflverse.combine_first_season
    assert ds.spec_id == "DATA-04"
    assert cfg.value == 2000
    assert "nflreadr.nflverse.com/reference/load_combine" in cfg.source
    assert ds.first_season == cfg.value


def test_combine_ingest_skips_seasons_before_2000(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []

    def loader(season: int) -> pl.DataFrame:
        calls.append(season)
        return pl.DataFrame({"season": [season], "pfr_id": ["X"], "pos": ["QB"]})

    ds = nflverse.DATASETS["combine"]
    monkeypatch.setitem(
        nflverse.DATASETS,
        "combine",
        nflverse.Dataset("DATA-04", loader, first_season=ds.first_season),
    )
    res = nflverse.ingest_nflverse([1999, 2000, 2001], ["combine"], root=tmp_path)
    assert calls == [2000, 2001]
    assert [r.status for r in res] == ["written", "written"]
    assert not partitions(tmp_path, "combine", 1999)
