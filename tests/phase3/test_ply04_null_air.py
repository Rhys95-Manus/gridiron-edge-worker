"""PLY-04 with uncharted air yards (bug found by the Phase 3e real-data run, 2026-10-09; every
season 2016-2024 has 60-108 targets with null air_yards). Ruling 2026-10-09: air share uses
only targets with recorded air_yards, numerator and team denominator alike; target share is
unchanged."""

from __future__ import annotations

import math

import polars as pl

from ge.metrics.context import build_context
from ge.metrics.player import ply_03, ply_04


def test_null_air_target_is_left_out_of_air_share(ctx) -> None:  # type: ignore[no-untyped-def]
    c = build_context(ctx.snap)
    plays = c.plays
    tgt = (pl.col("pass") == 1) & pl.col("receiver_player_id").is_not_null()
    first = plays.filter(tgt & pl.col("air_yards").is_not_null()).sort("game_id", "play_id").row(
        0, named=True
    )
    hit = (pl.col("game_id") == first["game_id"]) & (pl.col("play_id") == first["play_id"])
    c.__dict__["plays"] = plays.with_columns(
        pl.when(hit).then(None).otherwise(pl.col("air_yards")).alias("air_yards")
    )
    out = ply_04(c)  # raised TypeError before the fix
    air = out.filter((pl.col("stat") == "air_share") & (pl.col("entity_type") == "player"))
    assert air["value"].drop_nulls().len() > 0
    # The receiver's air share equals his air yards / team air yards over charted targets only.
    p = c.plays.filter(
        tgt
        & (pl.col("posteam") == first["posteam"])
        & pl.col("air_yards").is_not_null()
        & (pl.col("play_type") != "no_play")
    )
    played = set(
        c.played.filter(
            (pl.col("gsis_id") == first["receiver_player_id"])
            & (pl.col("team") == first["posteam"])
        )["game_id"].to_list()
    )
    p = p.filter(pl.col("game_id").is_in(list(played)))
    mine = p.filter(pl.col("receiver_player_id") == first["receiver_player_id"])
    want = math.fsum(mine["air_yards"].to_list()) / math.fsum(p["air_yards"].to_list())
    got = air.filter(
        (pl.col("entity_id") == first["receiver_player_id"]) & (pl.col("team") == first["posteam"])
    )["value"][0]
    assert math.isclose(got, want, rel_tol=1e-9)
    # Target share still counts the uncharted target.
    ts = ply_03(c).filter(
        (pl.col("entity_id") == first["receiver_player_id"]) & (pl.col("team") == first["posteam"])
    )
    assert ts["n"][0] >= 1
