"""PRJ-01a rated teams (ruling 2026-10-14): G4's unknown-change rule applies only to the
target game's two teams plus every team with plays this season; other teams are left out of
that game's rating table. From week 2 on nothing may change: the table holds all 32 teams
and is byte-identical to the Phase 4 (r1) behaviour, which rated every team in the context.

Fixture store (2023 in full, 2024 weeks 1-8); test window constants and fitted values from
tests/phase4/conftest.py."""

from __future__ import annotations

import io
from pathlib import Path

import polars as pl
import pytest

from ge.config import use_season
from ge.metrics.coaching import CoachingRegistry
from ge.metrics.context import build_context
from ge.models.ratings import (
    build_prior,
    coa07_features,
    fit_ratings,
    game_lines,
    load_window_consts,
    offense_terms,
    pass_rates,
    rate_context,
    ratings_params,
    season_plays,
    team_names,
)
from ge.store.snapshot import snapshot
from tests.phase3.conftest import STORE, first_game


def _bytes(df: pl.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.write_parquet(buf, compression="uncompressed", statistics=False)
    return buf.getvalue()


@pytest.mark.usefixtures("fit_env")
@pytest.mark.parametrize("week", [2, 3, 4, 5, 8])
def test_week2_on_matches_phase4_behaviour(
    week: int, ratings_root: Path, registry: CoachingRegistry
) -> None:
    ctx = build_context(snapshot(first_game(week), root=STORE), registry)
    got = rate_context(ctx, ratings_root=ratings_root)
    assert len(got.table.teams) == 32

    # Phase 4 (r1) behaviour, written out: every team in the context plus every team with
    # plays, a G4 prior over all of them, the same fit and lines.
    season = ctx.season
    params = ratings_params(season)
    consts = load_window_consts(season, ratings_root)
    cur = season_plays(ctx, season, consts)
    name = team_names(ctx)
    r1_teams = sorted(
        {name(t) for t in ctx.teams["team"].to_list()}
        | set(cur["posteam"].to_list())
        | set(cur["defteam"].to_list())
    )
    with use_season(season):
        prior = build_prior(ctx, params, consts, r1_teams)
    table = fit_ratings(cur, r1_teams, penalty=params.penalty, h=params.h_efficiency, prior=prior)
    last = season_plays(ctx.prior_context(), season - 1, consts)
    rates = pass_rates(
        pl.concat([last, cur]).select("posteam", "game_id", "kickoff_utc", "is_pass"),
        params.h_usage,
    )
    tg = ctx.snap.collect("target_game")
    sched = pl.concat([ctx.snap.collect("schedules"), tg], how="diagonal_relaxed")
    gid = str(tg["game_id"][0])
    terms = offense_terms(coa07_features(sched, [gid]))
    lines = game_lines(
        table, gid, str(tg["home_team"][0]), str(tg["away_team"][0]), rates, terms, consts
    )

    assert got.table.teams == tuple(r1_teams)
    assert _bytes(got.table.frame()) == _bytes(table.frame())
    assert got.table.cov.tobytes() == table.cov.tobytes()
    assert (got.table.int_pass, got.table.int_run) == (table.int_pass, table.int_run)
    assert got.lines == lines


@pytest.mark.usefixtures("fit_env")
def test_week1_table_holds_only_the_teams_that_touch_the_game(
    ratings_root: Path, registry: CoachingRegistry
) -> None:
    ctx = build_context(snapshot(first_game(1), root=STORE), registry)
    got = rate_context(ctx, ratings_root=ratings_root)
    tg = ctx.snap.collect("target_game").row(0, named=True)
    played = set(
        ctx.snap.collect("pbp").filter(pl.col("season") == ctx.season)["posteam"].drop_nulls()
    )
    assert set(got.table.teams) == {tg["home_team"], tg["away_team"]} | played
    assert len(got.table.teams) < 32
