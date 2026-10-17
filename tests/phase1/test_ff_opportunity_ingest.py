"""DATA-04 nflverse ff_opportunity (Phase 3f; spec synced 2026-10-16): load_ff_opportunity,
weekly, model v1.0.0, seasons 2016 on, kept current by the collector so our own pulls set
pulled_at. The real-data checks confirm the columns PLY-35 reads from the stored files."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from ge.config import ATTRIBUTION, load_ingest
from ge.ingest import collect, nflverse
from ge.ingest.raw import DATA_ROOT, partitions, read_latest

# MODEL_SPEC PLY-35 "Data fields" (confirmed from real data 2026-10-16).
PLY35_COLUMNS = (
    "game_id",
    "player_id",
    "posteam",
    "position",
    "rec_attempt",
    "rush_attempt",
    "receptions",
    "receptions_exp",
    "rec_yards_gained",
    "rec_yards_gained_exp",
    "rush_yards_gained",
    "rush_yards_gained_exp",
    "rec_touchdown",
    "rec_touchdown_exp",
    "rush_touchdown",
    "rush_touchdown_exp",
)
STRINGS = ("game_id", "player_id", "posteam", "position")
SPEC_ATTRIBUTION = (
    "Data: nflverse; charting: FTN Data via nflverse; expected points: ffopportunity (ffverse) "
    "via nflverse; data license not stated by the source"
)
CHECK_SEASON = 2024  # never 2025 (BT-07b holdout; decision log 2026-10-16)


def test_ff_opportunity_is_a_data_04_dataset() -> None:
    ds = nflverse.DATASETS["ff_opportunity"]
    assert ds.spec_id == "DATA-04"
    assert ds.first_season is None  # nflverse.first_season: 2016 (MODEL_SPEC DATA-04)
    assert load_ingest().nflverse.first_season.value == 2016
    mv = load_ingest().nflverse.ff_opportunity_model_version
    assert mv.value == "v1.0.0"
    assert "model v1.0.0" in mv.source


def test_loader_pins_weekly_and_the_model_version(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, ...]] = []

    def fake(seasons: object, stat_type: str, model_version: str) -> pl.DataFrame:
        calls.append((seasons, stat_type, model_version))
        return pl.DataFrame({"game_id": ["x"]})

    monkeypatch.setattr(nflverse.nfl, "load_ff_opportunity", fake)
    nflverse.DATASETS["ff_opportunity"].loader(2024)
    assert calls == [(2024, "weekly", "v1.0.0")]


def test_ingest_skips_seasons_before_2016(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[int] = []

    def fake(seasons: int, stat_type: str, model_version: str) -> pl.DataFrame:
        seen.append(seasons)
        return pl.DataFrame({"season": [str(seasons)], "game_id": ["x"]})

    monkeypatch.setattr(nflverse.nfl, "load_ff_opportunity", fake)
    res = nflverse.ingest_nflverse([2015, 2016], ["ff_opportunity"], root=tmp_path)
    assert seen == [2016]
    assert [(r.season, r.status) for r in res] == [(2016, "written")]
    assert not partitions(tmp_path, "ff_opportunity", 2015)


def test_collector_pulls_ff_opportunity() -> None:
    """BT-01 (spec synced 2026-10-16): from our own pulls on, pulled_at decides."""
    assert "ff_opportunity" in collect.NFLVERSE_DATASETS


def test_attribution_line_is_the_spec_line() -> None:
    assert ATTRIBUTION == SPEC_ATTRIBUTION
    from ge.ingest import jobs

    assert jobs.ATTRIBUTION == SPEC_ATTRIBUTION


def test_no_module_hard_codes_an_attribution_line() -> None:
    """Every printed or written attribution comes from ge.config.ATTRIBUTION; the previous line
    appears only as the validator's legacy line (decision log 2026-10-16)."""
    src = Path(__file__).parents[2] / "src" / "ge"
    hits = [
        str(p.relative_to(src))
        for p in src.rglob("*.py")
        if p.name != "config.py"
        and any(
            q + "Data: nflverse; charting: FTN Data via nflverse" + e in p.read_text("utf-8")
            for q in ('"', "'")
            for e in ('"', "'", '."', ".'")
        )
    ]
    assert not hits, hits


@pytest.mark.realdata
def test_stored_columns_and_types() -> None:
    df = read_latest(DATA_ROOT, "ff_opportunity", CHECK_SEASON)
    missing = [c for c in PLY35_COLUMNS if c not in df.columns]
    assert not missing, missing
    for c in PLY35_COLUMNS:
        want = pl.Utf8 if c in STRINGS else pl.Float64
        assert df.schema[c] == want, (c, df.schema[c])
    assert df.height > 0


@pytest.mark.realdata
def test_stored_diff_is_actual_minus_expected() -> None:
    df = read_latest(DATA_ROOT, "ff_opportunity", CHECK_SEASON)
    for s in ("receptions", "rec_yards_gained", "rush_yards_gained", "rec_touchdown"):
        d = (df[s] - df[f"{s}_exp"] - df[f"{s}_diff"]).abs().max()
        assert d == 0.0, (s, d)
