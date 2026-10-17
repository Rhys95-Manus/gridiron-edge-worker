"""BT-02 / decision log 2026-10-16: the Phase 3e report shows each PLY-35 stat's 2026 mean raw
gap beside its 2024 mean, to catch any change from the model files re-uploaded in December
2025. Same qualifying rows as the metric (a target or carry, a player); never the holdout."""

from __future__ import annotations

import datetime as dt
import math
from pathlib import Path

import polars as pl
import pytest

from ge.fit import ply35_check as pc
from ge.ingest.raw import write_raw
from ge.metrics import expected as ex
from ge.store.holdout import HoldoutReadError


def _ff(rows: list[tuple[str | None, str | None, float, float, float, float]]) -> pl.DataFrame:
    """(player, position, targets, carries, rec yards, rec yards exp); other stats 0."""
    out = []
    for i, (pid, pos, tg, ca, ry, rye) in enumerate(rows):
        r = {c: 0.0 for c in ex.NUMERIC_COLUMNS}
        r.update(
            game_id=f"2024_01_A_B{i}", player_id=pid, posteam="A", position=pos,
            rec_attempt=tg, rush_attempt=ca, rec_yards_gained=ry, rec_yards_gained_exp=rye,
        )  # fmt: skip
        out.append(r)
    return pl.DataFrame(out)


def test_mean_raw_gap_per_stat_and_group() -> None:
    df = _ff(
        [
            ("p1", "WR", 5, 0, 60, 50),  # +10
            ("p2", "WR", 4, 0, 20, 40),  # -20
            ("p3", "TE", 2, 0, 15, 10),  # +5
            ("p4", "QB", 0, 0, 0, 0),  # no opportunity: left out
            (None, None, 3, 0, 99, 0),  # no player: left out
        ]
    )
    got = pc.mean_raw_gaps(df)
    ry = {
        r["group"]: r for r in got.filter(pl.col("stat") == "receiving_yards").iter_rows(named=True)
    }
    assert ry["all"]["n"] == 3 and math.isclose(ry["all"]["mean"], -5 / 3)
    assert ry["WR"]["n"] == 2 and math.isclose(ry["WR"]["mean"], -5.0)
    assert ry["TE"]["n"] == 1 and math.isclose(ry["TE"]["mean"], 5.0)
    assert set(got["stat"].unique().to_list()) == set(ex.STATS)


def test_comparison_lines_show_both_seasons_and_the_difference() -> None:
    a = pc.mean_raw_gaps(_ff([("p1", "WR", 5, 0, 60, 50)]))
    b = pc.mean_raw_gaps(_ff([("p1", "WR", 5, 0, 40, 50)]))
    lines = pc.comparison_lines(a, b, 2024, 2026)
    text = "\n".join(lines)
    assert "2024" in text and "2026" in text
    row = next(x for x in lines if x.startswith("| receiving_yards | all |"))
    assert "+10" in row and "-10" in row and "-20" in row


def test_reads_latest_pull_of_each_season(tmp_path: Path) -> None:
    t = dt.datetime(2026, 10, 16, tzinfo=dt.UTC)
    for season, ry in ((2024, 60), (2026, 40)):
        write_raw(
            _ff([("p1", "WR", 5, 0, ry, 50)]),
            "ff_opportunity",
            season,
            source="t",
            root=tmp_path,
            pulled_at=t,
        )
    lines = pc.gap_check(tmp_path, 2024, 2026)
    assert any(x.startswith("| receiving_yards | all |") for x in lines)


def test_report_lines_say_when_a_season_is_not_stored(tmp_path: Path) -> None:
    lines = pc.report_lines(tmp_path, 2024, 2026)
    assert lines[0].startswith("## PLY-35 gap check: 2026 mean raw gap beside 2024")
    assert any("not available" in x for x in lines)


def test_refuses_the_holdout(tmp_path: Path) -> None:
    with pytest.raises(HoldoutReadError):
        pc.gap_check(tmp_path, 2024, 2025)
