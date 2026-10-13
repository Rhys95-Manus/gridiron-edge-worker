"""BUILD_PLAN Phase 4: "ratings for a game change by zero when any later game is altered"
(reuses the Phase 2 leakage harness). Every game at or after the target is deleted or
shuffled in a copy of the fixture store; ratings, standard errors, pass rates and lines must
be byte-identical. Checked after G4's window (week 8) and inside it (week 3)."""

from __future__ import annotations

import io
from pathlib import Path

import polars as pl
import pytest

from ge.metrics.coaching import CoachingRegistry
from ge.models.ratings import GameRatings, ratings_for_game
from ge.store.snapshot import snapshot
from tests.phase2.leakage import perturbed_store
from tests.phase3.conftest import G4_WEEK, MAIN_WEEK, STORE, first_game


def _bytes(df: pl.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.sort(df.columns).write_parquet(buf, compression="uncompressed", statistics=False)
    return buf.getvalue()


def _fingerprint(g: GameRatings) -> tuple[object, ...]:
    t = g.table
    return (
        _bytes(t.frame()),
        repr((t.int_pass, t.int_run, t.sigma2, t.n_plays)),
        t.cov.tobytes(),
        repr(sorted(g.pass_rate.items())),
        repr(g.lines),
        g.notes,
    )


@pytest.mark.usefixtures("fit_env")
@pytest.mark.parametrize("week", [MAIN_WEEK, G4_WEEK])
@pytest.mark.parametrize("mode", ["delete", "shuffle"])
def test_ratings_ignore_later_games(
    tmp_path: Path, week: int, mode: str, ratings_root: Path, registry: CoachingRegistry
) -> None:
    gid = first_game(week)
    as_of = snapshot(gid, root=STORE).as_of
    base = ratings_for_game(gid, as_of, root=STORE, ratings_root=ratings_root, registry=registry)
    dst = tmp_path / "store"
    datasets = sorted(p.name for p in STORE.iterdir() if p.is_dir())
    perturbed_store(STORE, dst, game_id=gid, as_of=as_of, mode=mode, datasets=datasets)  # type: ignore[arg-type]
    pert = ratings_for_game(gid, as_of, root=dst, ratings_root=ratings_root, registry=registry)
    assert _fingerprint(base) == _fingerprint(pert)
