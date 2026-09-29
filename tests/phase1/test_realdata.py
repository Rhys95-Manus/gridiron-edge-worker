"""BUILD_PLAN Phase 1 acceptance tests on the real downloaded store (data/raw).

Run `uv run ge ingest nflverse` first. Marked realdata: they run locally with
`uv run pytest -m phase1`, and CI deselects them because it has no data."""

from pathlib import Path

import polars as pl
import pytest

from ge.config import load_ingest
from ge.ingest.nflverse import completed_seasons, ingest_nflverse
from ge.ingest.raw import DATA_ROOT, partitions, read_latest

pytestmark = pytest.mark.realdata

CFG = load_ingest()


def _schedules() -> pl.DataFrame:
    return pl.concat([read_latest(DATA_ROOT, "schedules", s) for s in completed_seasons(DATA_ROOT)])


def test_store_has_every_completed_season() -> None:
    first = CFG.nflverse.first_season.value
    seasons = completed_seasons(DATA_ROOT)
    assert seasons, "no schedules in data/raw; run `uv run ge ingest nflverse`"
    assert seasons[0] <= first
    assert set(range(first, seasons[-1] + 1)) <= set(seasons)


def test_pbp_games_equal_completed_schedule_games() -> None:
    sched = _schedules()
    first = CFG.nflverse.first_season.value
    bad = []
    for season in [s for s in completed_seasons(DATA_ROOT) if s >= first]:
        done = set(
            sched.filter((pl.col("season") == season) & pl.col("result").is_not_null())["game_id"]
        )
        pbp = set(read_latest(DATA_ROOT, "pbp", season)["game_id"].unique())
        if pbp != done:
            bad.append(
                f"{season}: only in pbp {sorted(pbp - done)[:5]}, "
                f"only in schedules {sorted(done - pbp)[:5]}"
            )
    assert not bad, "\n".join(bad)


def test_ftn_joins_pbp_on_unique_keys() -> None:
    first_ftn = CFG.nflverse.ftn_first_season.value
    rates = []
    for season in [s for s in completed_seasons(DATA_ROOT) if s >= first_ftn]:
        ftn = read_latest(DATA_ROOT, "ftn_charting", season)
        pbp = read_latest(DATA_ROOT, "pbp", season)
        fkeys = ftn.select(["nflverse_game_id", "nflverse_play_id"])
        pkeys = pbp.select(["game_id", "play_id"])
        assert fkeys.is_duplicated().sum() == 0, f"{season}: duplicate FTN keys"
        assert pkeys.is_duplicated().sum() == 0, f"{season}: duplicate pbp keys"
        joined = fkeys.join(
            pkeys.with_columns(pl.col("play_id").cast(fkeys["nflverse_play_id"].dtype)),
            left_on=["nflverse_game_id", "nflverse_play_id"],
            right_on=["game_id", "play_id"],
            how="inner",
        )
        rates.append((season, ftn.height, joined.height))
    assert rates, "no FTN seasons in the store"
    print("\nFTN -> pbp join rate by season:")
    for season, n, j in rates:
        print(f"  {season}: {j}/{n} = {j / n:.4%}")


def test_running_ingest_twice_adds_no_rows(tmp_path: Path) -> None:
    season = completed_seasons(DATA_ROOT)[-1]
    for _ in range(2):
        ingest_nflverse(seasons=[season], datasets=["schedules", "injuries"], root=tmp_path)
    for ds in ("schedules", "injuries"):
        assert len(partitions(tmp_path, ds, season)) == 1, ds
        latest = read_latest(tmp_path, ds, season)
        assert latest.height == latest.unique().height, f"{ds}: duplicate rows"
