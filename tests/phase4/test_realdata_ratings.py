"""Phase 4 on the local real store (data/, from `ge ingest`) with the repo's active fits
(config/params_fitted and config/ratings_fitted). Run locally, not in CI.

- The closing-line sign convention holds in every walk-forward season before any comparison:
  spread_line rises with the home team's margin and total_line with the combined score.
- A full real week rates all 32 teams with finite standard errors.
- The leakage harness on the real store: a 2023 week-10 game's ratings are byte-identical
  when every later game is deleted or shuffled."""

from __future__ import annotations

import math
from pathlib import Path

import polars as pl
import pytest

from ge.ingest.raw import DATA_ROOT, read_latest
from ge.metrics.job import anchor_game
from ge.models.ratings import RATING_TYPES, ratings_for_game
from ge.models.ratings_report import check_line_signs
from ge.store.snapshot import snapshot
from tests.phase2.leakage import perturbed_store
from tests.phase4.test_leakage import _fingerprint

pytestmark = pytest.mark.realdata

SEASONS = (2021, 2022, 2023, 2024)


def test_closing_line_signs() -> None:
    sched = pl.concat(
        [read_latest(DATA_ROOT, "schedules", s) for s in SEASONS], how="diagonal_relaxed"
    )
    got = check_line_signs(sched)
    assert got["season"].to_list() == list(SEASONS)
    print(got)


def test_a_real_week_rates_every_team() -> None:
    got = ratings_for_game(anchor_game(2023, 9))
    assert len(got.table.teams) == 32
    for t in got.table.teams:
        for k in RATING_TYPES:
            assert math.isfinite(got.table.values[(t, k)]) and got.table.se[(t, k)] > 0
    assert math.isfinite(got.lines.spread) and got.lines.spread_se > 0


@pytest.mark.parametrize("mode", ["delete", "shuffle"])
def test_real_store_leakage(tmp_path: Path, mode: str) -> None:
    gid = anchor_game(2023, 9)
    as_of = snapshot(gid).as_of
    base = ratings_for_game(gid, as_of)
    dst = tmp_path / "store"
    datasets = sorted(p.name for p in DATA_ROOT.iterdir() if p.is_dir())
    perturbed_store(DATA_ROOT, dst, game_id=gid, as_of=as_of, mode=mode, datasets=datasets)  # type: ignore[arg-type]
    assert _fingerprint(ratings_for_game(gid, as_of, root=dst)) == _fingerprint(base)
