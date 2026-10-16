"""G4 week-1 quarterback (decision log 2026-10-13, Phase 4b).

Before a team's first game of a season, when it has no dropbacks yet, its quarterback is QB1
on the latest depth chart available at decision time (BT-01): last season's most-dropback
passer = no change; anyone else = new quarterback (G4's 1/3 regression); no depth chart =
unknown, game unrated.

The cases edit a copy of the phase3 fixture store's 2024 depth chart (real data, cut by
tests/phase3/fixtures/capture_fixtures.py); player IDs placed in a chart are real passer IDs
taken from the fixture's own 2023 play-by-play, never typed in."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path

import polars as pl
import pytest

from ge.config import load_params, use_season
from ge.metrics.coaching import CoachingRegistry
from ge.metrics.context import MetricContext, build_context, qb1_from_chart
from ge.models.ratings import (
    build_prior,
    load_window_consts,
    ratings_for_game,
    ratings_params,
)
from ge.store.snapshot import snapshot
from tests.phase3.conftest import STORE, first_game, store_table
from tests.phase3.test_g4_carryover import _qb

EXTRA = float(load_params().conventions.g4_new_caller_or_qb_extra_regression.value)
WEEK1 = first_game(1)


def _fixture_facts() -> tuple[str, str, str]:
    """(the week-1 game's home team, yet to play at its decision time and in its rating table
    (ruling 2026-10-14); its 2023 top passer; another team's 2023 top passer)."""
    snap = snapshot(WEEK1, root=STORE)
    played = set(
        snap.collect("pbp").filter(pl.col("season") == snap.season)["posteam"].drop_nulls()
    )
    team = str(snap.collect("target_game")["home_team"][0])
    assert team not in played
    last = _qb(store_table("pbp", 2023).to_dicts())
    other = sorted(p for t, p in last.items() if p != last[team])[0]
    return team, last[team], other


TEAM, SAME_QB, OTHER_QB = _fixture_facts()


def _store(tmp: Path, edit: Callable[[pl.DataFrame], pl.DataFrame]) -> Path:
    """A copy of the fixture store with the 2024 depth chart edited (meta file kept)."""
    dst = tmp / "store"
    shutil.copytree(STORE, dst)
    (part,) = sorted((dst / "depth_charts" / "season=2024").glob("pulled_at=*/part.parquet"))
    df = pl.read_parquet(part)
    edit(df).write_parquet(part)
    meta = json.loads((part.parent / "part.meta.json").read_text(encoding="utf-8"))
    assert meta["source"] and meta["pulled_at"]
    return dst


def _qb1(df: pl.DataFrame, team: str) -> pl.Expr:
    return (
        (pl.col("club_code") == team)
        & (pl.col("depth_position") == "QB")
        & (pl.col("formation") == "Offense")
        & (pl.col("depth_team").cast(pl.Int64) == 1)
    )


def _set_qb1(
    team: str, gsis: str, week: int | None = None
) -> Callable[[pl.DataFrame], pl.DataFrame]:
    def edit(df: pl.DataFrame) -> pl.DataFrame:
        hit = _qb1(df, team) & (pl.col("week") == week if week is not None else pl.lit(True))
        assert df.filter(hit).height > 0
        return df.with_columns(
            pl.when(hit).then(pl.lit(gsis)).otherwise(pl.col("gsis_id")).alias("gsis_id")
        )

    return edit


def _ctx(root: Path, registry: CoachingRegistry) -> MetricContext:
    return build_context(snapshot(WEEK1, root=root), registry)


def test_same_quarterback_is_no_change(tmp_path: Path, registry: CoachingRegistry) -> None:
    ctx = _ctx(_store(tmp_path, _set_qb1(TEAM, SAME_QB)), registry)
    changed, _ = ctx.g4_changed(TEAM, "offense")
    assert changed is False


def test_other_quarterback_is_a_new_quarterback(tmp_path: Path, registry: CoachingRegistry) -> None:
    ctx = _ctx(_store(tmp_path, _set_qb1(TEAM, OTHER_QB)), registry)
    changed, note = ctx.g4_changed(TEAM, "offense")
    assert changed is True and "new QB" in note


def test_no_depth_chart_leaves_the_change_unknown(
    tmp_path: Path, registry: CoachingRegistry
) -> None:
    root = _store(tmp_path, lambda df: df.filter(pl.col("club_code") != TEAM))
    ctx = _ctx(root, registry)
    changed, note = ctx.g4_changed(TEAM, "offense")
    assert changed is None and "depth chart" in note


def test_chart_published_after_decision_time_is_not_used(
    tmp_path: Path, registry: CoachingRegistry
) -> None:
    """A later week's chart (known only after the week-1 game's decision time) naming another
    QB1 must not change the week-1 answer."""

    def edit(df: pl.DataFrame) -> pl.DataFrame:
        df = _set_qb1(TEAM, SAME_QB, week=1)(df)
        return _set_qb1(TEAM, OTHER_QB, week=2)(df)

    ctx = _ctx(_store(tmp_path, edit), registry)
    changed, _ = ctx.g4_changed(TEAM, "offense")
    assert changed is False


@pytest.mark.usefixtures("fit_env")
def test_week1_prior_regresses_only_for_a_new_quarterback(
    tmp_path: Path, registry: CoachingRegistry, ratings_root: Path
) -> None:
    same = _ctx(_store(tmp_path / "a", _set_qb1(TEAM, SAME_QB)), registry)
    new = _ctx(_store(tmp_path / "b", _set_qb1(TEAM, OTHER_QB)), registry)
    with use_season(same.season):
        params = ratings_params(same.season)
    consts = load_window_consts(same.season, ratings_root)
    p_same = build_prior(same, params, consts)
    p_new = build_prior(new, params, consts)
    assert p_same is not None and p_new is not None
    for k in ("off_pass", "off_run"):
        assert p_new.ratings[(TEAM, k)] == pytest.approx(
            p_same.ratings[(TEAM, k)] * (1 - EXTRA), abs=1e-15
        )
    for k in ("def_pass", "def_run"):
        assert p_new.ratings[(TEAM, k)] == p_same.ratings[(TEAM, k)]


@pytest.mark.usefixtures("fit_env")
def test_week1_game_is_rated_with_a_chart_and_unrated_without(
    tmp_path: Path, registry: CoachingRegistry, ratings_root: Path
) -> None:
    got = ratings_for_game(WEEK1, root=STORE, ratings_root=ratings_root, registry=registry)
    assert any("G4" in n for n in got.notes)
    tgt = snapshot(WEEK1, root=STORE).collect("target_game").row(0, named=True)
    root = _store(tmp_path, lambda df: df.filter(pl.col("club_code") != tgt["home_team"]))
    with pytest.raises(NotImplementedError, match=r"G4.*depth chart"):
        ratings_for_game(WEEK1, root=root, ratings_root=ratings_root, registry=registry)


def test_qb1_from_both_chart_formats() -> None:
    """Synthetic charts (IDs are made-up strings): week-numbered (before 2025) and ESPN daily
    (2025 on); two different QB1s on one team is ambiguous (None)."""
    weekly = pl.DataFrame(
        {
            "club_code": ["AAA", "AAA", "BBB", "BBB", "CCC"],
            "week": [1, 1, 1, 1, 1],
            "formation": ["Offense"] * 5,
            "depth_position": ["QB", "QB", "QB", "QB", "WR"],
            "depth_team": ["1", "2", "1", "1", "1"],
            "gsis_id": ["P1", "P2", "P3", "P4", "P5"],
        }
    )
    assert qb1_from_chart(weekly) == {"AAA": "P1", "BBB": None}
    espn = pl.DataFrame(
        {
            "dt": ["2026-09-01T12:00:00Z"] * 3,
            "team": ["AAA", "AAA", "BBB"],
            "pos_abb": ["QB", "QB", "QB"],
            "pos_rank": [1, 2, 1],
            "gsis_id": ["P1", "P2", "P3"],
        }
    )
    assert qb1_from_chart(espn) == {"AAA": "P1", "BBB": "P3"}
    assert qb1_from_chart(pl.DataFrame()) == {}
