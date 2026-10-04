"""The three planned 3a tests added 2026-10-04: OFF-10's hand-traced drive, OFF-04's
neutral-filter edge rows, and OFF-06/07/08's FTN join-rate report plus the pre-2022 case."""

from __future__ import annotations

import json
from itertools import pairwise
from typing import Any

import polars as pl
import pytest

from ge.metrics import offense
from ge.metrics import plays as pf
from ge.metrics.context import build_context
from ge.metrics.registry import raw, shrunk
from ge.store.snapshot import snapshot
from tests.phase3 import oracle as o
from tests.phase3.conftest import FIXTURES, STORE, first_game

C = o.C


# ---- OFF-10: one drive traced by hand ----


def test_off_10_hand_traced_drive(ctx, rows) -> None:  # type: ignore[no-untyped-def]
    trace = json.loads((FIXTURES / "off10_trace.json").read_text(encoding="utf-8"))
    assert trace["source"] and trace["pulled_at"]
    # the drive is the one the stated rule picks
    wk1 = [r for r in rows if r["week"] == 1 and (r["play_type"] is not None or r["timeout"] == 1)]
    drives: dict[tuple[str, float], list[dict[str, Any]]] = {}
    for r in wk1:
        drives.setdefault((r["game_id"], r["fixed_drive"]), []).append(r)
    picked = next(
        key
        for key in sorted(drives, key=lambda k: (k[0], k[1] if k[1] is not None else -1))
        if key[1] is not None
        and len(drives[key]) >= 8
        and all(
            any(r[f] == 1 for r in drives[key]) for f in ("incomplete_pass", "timeout", "penalty")
        )
    )
    assert picked == (trace["game_id"], trace["fixed_drive"])
    # every consecutive row pair of the drive is in the trace
    ids = sorted(int(r["play_id"]) for r in drives[picked])
    assert [(p["a"], p["b"]) for p in trace["pairs"]] == list(pairwise(ids))
    got = offense.pace_pairs(ctx).filter(
        (pl.col("game_id") == trace["game_id"]) & (pl.col("fixed_drive") == trace["fixed_drive"])
    )
    want = {p["a"]: p["delta"] for p in trace["pairs"] if p["keep"]}
    assert (
        dict(zip(got["play_id"].cast(pl.Int64).to_list(), got["x"].to_list(), strict=True)) == want
    )


# ---- OFF-04: G5 / G7 boundary rows ----


def _edge_rows(rows: list[dict[str, Any]]) -> pl.DataFrame:
    """One real 1st-down qualifying neutral row, copied with boundary values swapped in."""
    base = next(
        r for r in rows if o.qualifying(r) and o.neutral(r) and r["down"] == 1 and r["qtr"] == 1
    )
    lo, hi = o.v(C.g5_neutral_wp_min), o.v(C.g5_neutral_wp_max)
    end = o.v(C.g5_end_of_half_excluded_seconds)
    g_lo, g_hi = o.v(C.g7_garbage_wp_low), o.v(C.g7_garbage_wp_high)
    cases = [
        ("wp at lower bound", {"wp": lo}),
        ("wp just below", {"wp": lo - 1e-9}),
        ("wp at upper bound", {"wp": hi}),
        ("wp just above", {"wp": hi + 1e-9}),
        ("2:00 left in half", {"half_seconds_remaining": end}),
        ("2:01 left in half", {"half_seconds_remaining": end + 1}),
        ("wp missing", {"wp": None}),
        ("4th qtr at garbage low bound", {"qtr": 4, "wp": g_lo}),
        ("4th qtr below garbage low", {"qtr": 4, "wp": g_lo - 1e-9}),
        ("4th qtr above garbage high", {"qtr": 4, "wp": g_hi + 1e-9}),
        ("overtime below garbage low", {"qtr": 5, "wp": g_lo - 1e-9}),
        ("3rd qtr below garbage low", {"qtr": 3, "wp": g_lo - 1e-9}),
        ("3rd down", {"down": 3}),
        ("two-point try", {"two_point_attempt": 1}),
    ]
    return pl.DataFrame(
        [{**base, **change, "_case": name} for name, change in cases], infer_schema_length=None
    )


def test_neutral_and_garbage_boundaries(rows) -> None:  # type: ignore[no-untyped-def]
    df = _edge_rows(rows)
    got = df.with_columns(
        pf.neutral().alias("neutral"),
        pf.garbage().alias("garbage"),
        (pf.qualifying() & pf.neutral() & pl.col("down").is_in([1, 2])).alias("off_04"),
    )
    expected = {
        "wp at lower bound": (True, False, True),
        "wp just below": (False, False, False),
        "wp at upper bound": (True, False, True),
        "wp just above": (False, False, False),
        "2:00 left in half": (False, False, False),
        "2:01 left in half": (True, False, True),
        "wp missing": (False, False, False),
        "4th qtr at garbage low bound": (False, False, False),
        "4th qtr below garbage low": (False, True, False),
        "4th qtr above garbage high": (False, True, False),
        "overtime below garbage low": (False, True, False),
        "3rd qtr below garbage low": (False, False, False),
        "3rd down": (True, False, False),
        "two-point try": (True, False, False),
    }
    for r in got.iter_rows(named=True):
        assert (r["neutral"], r["garbage"], r["off_04"]) == expected[r["_case"]], r["_case"]
        # the oracle agrees row by row
        assert o.neutral(r) == r["neutral"] and o.garbage(r) == r["garbage"], r["_case"]


# ---- OFF-06/07/08: FTN join rate; pre-2022 has no FTN ----


def test_ftn_join_rate_report(ctx, rows, ftn, teams) -> None:  # type: ignore[no-untyped-def]
    rep = offense.ftn_join_rate(ctx)
    got = {(r["team"], r["plays"]): r for r in rep.iter_rows(named=True)}
    for name, keep in (("dropbacks", o.dropback), ("qualifying", o.qualifying)):
        for t in teams:
            mine = [r for r in rows if keep(r) and r["posteam"] == t]
            joined = sum(1 for r in mine if (r["game_id"], int(r["play_id"])) in ftn)
            r = got[(t, name)]
            assert (r["n"], r["joined"]) == (len(mine), joined), (t, name)
            assert r["rate"] == pytest.approx(joined / len(mine))
    print("\nFTN join rate by play set (min / mean / max over teams):")
    print(
        rep.group_by("plays")
        .agg(
            pl.col("rate").min(),
            pl.col("rate").mean().alias("mean"),
            pl.col("rate").max().alias("max"),
        )
        .sort("plays")
    )


@pytest.fixture(scope="module")
def ctx_2021():  # type: ignore[no-untyped-def]
    snap = snapshot(first_game(6, season=2021), root=STORE)
    assert snap.season == 2021 and snap.week == 6
    return build_context(snap)


@pytest.mark.parametrize(
    ("spec_id", "stat"),
    [
        ("OFF-06", "play_action_rate"),
        ("OFF-07", "motion_rate"),
        ("OFF-08", "rpo_rate"),
        ("DEF-05", "blitz_rate"),
        ("DEF-05", "rushers"),
        ("DEF-05", "box"),
    ],
)
def test_pre_2022_ftn_metrics_are_missing(ctx_2021, spec_id: str, stat: str) -> None:  # type: ignore[no-untyped-def]
    """FTN starts in 2022. A 2021 snapshot has plays but no charting: every team row has n = 0,
    no value and the note "no FTN". Ruling 2026-10-04: FTN metrics are treated as missing, so
    the shrunk rows exist with a null shrunk value (matchup terms using them contribute 0)."""
    frame = raw(ctx_2021, spec_id).filter(pl.col("stat") == stat)
    teams = frame.filter(pl.col("entity_type") == "team")
    assert teams.height == 32
    assert teams["n"].to_list() == [0] * 32
    assert teams["value"].null_count() == 32
    assert set(frame["note"].to_list()) == {"no FTN"}
    assert ctx_2021.plays.filter(pf.qualifying()).height > 0  # plays exist, charting doesn't
    s = shrunk(ctx_2021, spec_id, stat)
    assert s.height == 32
    assert s["shrunk"].null_count() == 32 and s["prior"].null_count() == 32
    assert set(s["note"].to_list()) == {"no FTN: missing"}
