"""`ge metrics --season S --through-week W`: one snapshot anchored on the first week W+1 game
(as_of = its decision time, so every week-W game is visible), every metric's raw rows, the
shrunk rows that can be computed, and a list of what can't with the reason. Deterministic."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import polars as pl
import typer

from ge.cli import app
from ge.metrics.context import build_context
from ge.metrics.job import anchor_game, run_metrics
from ge.metrics.registry import REGISTRY, raw, shrunk
from ge.store.snapshot import snapshot
from tests.phase3.conftest import STORE, store_table

SEASON, THROUGH = 2024, 7


def test_anchor_is_the_first_game_of_the_next_week() -> None:
    s = store_table("schedules", SEASON).filter(pl.col("week") == THROUGH + 1)
    first = s.sort("gameday", "gametime", "game_id")["game_id"][0]
    assert anchor_game(SEASON, THROUGH, root=STORE) == first


def test_job_writes_raw_shrunk_and_not_computed(tmp_path: Path) -> None:
    out = run_metrics(SEASON, THROUGH, root=STORE, out_dir=tmp_path)
    folder = tmp_path / f"season={SEASON}" / f"through_week={THROUGH}"
    raw_df = pl.read_parquet(folder / "raw.parquet")
    sh = pl.read_parquet(folder / "shrunk.parquet")
    nc = pl.read_parquet(folder / "not_computed.parquet")
    assert out.anchor_game == anchor_game(SEASON, THROUGH, root=STORE)
    snap = snapshot(out.anchor_game, root=STORE)
    assert out.as_of == snap.as_of
    ctx = build_context(snap)
    for sid, e in REGISTRY.items():
        if e.paid:
            assert nc.filter((pl.col("spec_id") == sid) & (pl.col("stat") == "*")).height == 1
            continue
        mine = raw_df.filter(pl.col("spec_id") == sid)
        want = raw(ctx, sid)
        cols = list(want.columns)
        assert (
            mine.select(cols).sort(cols, nulls_last=True).equals(want.sort(cols, nulls_last=True))
        ), sid
        for stat, sd in e.stats.items():
            if sd.k is None:  # counts are never shrunk
                continue
            got = sh.filter((pl.col("spec_id") == sid) & (pl.col("stat") == stat)).height
            in_nc = nc.filter((pl.col("spec_id") == sid) & (pl.col("stat") == stat)).height > 0
            try:
                want_rows = shrunk(ctx, sid, stat).height
            except NotImplementedError:
                assert in_nc and got == 0, (sid, stat)
            else:  # computed (possibly no eligible rows, e.g. DEF-08 on/off)
                assert not in_nc and got == want_rows, (sid, stat)
    reasons = dict(
        nc.select(pl.concat_str(["spec_id", "stat"], separator=" "), "reason").iter_rows()
    )
    assert "role prior" in reasons["PLY-03 target_share"]
    assert "OFF-12" in reasons["OFF-12 ypc"]
    assert sh.filter(pl.col("spec_id") == "OFF-01").height == 3 * 32
    assert "Data: nflverse; charting: FTN Data via nflverse" in out.summary


def test_job_is_deterministic(tmp_path: Path) -> None:
    a = run_metrics(SEASON, THROUGH, root=STORE, out_dir=tmp_path / "a")
    b = run_metrics(SEASON, THROUGH, root=STORE, out_dir=tmp_path / "b")
    for name in ("raw.parquet", "shrunk.parquet", "not_computed.parquet"):
        pa = tmp_path / "a" / f"season={SEASON}" / f"through_week={THROUGH}" / name
        pb = tmp_path / "b" / f"season={SEASON}" / f"through_week={THROUGH}" / name
        assert pa.read_bytes() == pb.read_bytes(), name
    assert a.summary == b.summary


def test_explicit_as_of_is_used(tmp_path: Path) -> None:
    anchor = anchor_game(SEASON, THROUGH, root=STORE)
    default = snapshot(anchor, root=STORE).as_of
    later = default + dt.timedelta(hours=12)
    out = run_metrics(SEASON, THROUGH, as_of=later, root=STORE, out_dir=tmp_path)
    assert out.as_of == later


def test_cli_options() -> None:
    cmd = typer.main.get_command(app)
    assert isinstance(cmd, typer.core.TyperGroup)
    opts = {o for p in cmd.commands["metrics"].params for o in p.opts}
    assert {"--season", "--through-week", "--week", "--as-of"} <= opts
