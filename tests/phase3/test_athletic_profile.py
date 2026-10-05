"""PLY-34 athletic profile (a prior only, not paired) from nflverse combine data (DATA-04,
ruling 2026-10-04). Rulings: percentile within the combine `pos` over every draft year held up
to the target season; timed drills inverted so higher = better; combine rows without a pfr_id
stay in the pool but give no player a profile. Percentile = (below + half of ties) / pool."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import polars as pl
import pytest

from ge.metrics.registry import raw
from ge.store.snapshot import COMBINE_COLUMNS

MEASURES = {
    "height": "ht",
    "weight": "wt",
    "forty": "forty",
    "vertical": "vertical",
    "broad_jump": "broad_jump",
    "cone": "cone",
    "shuttle": "shuttle",
}
LOWER_IS_BETTER = {"forty", "cone", "shuttle"}


def _inches(ht: Any) -> float | None:
    """nflverse combine height is text like "6-2" (feet-inches)."""
    if ht is None:
        return None
    feet, inches = str(ht).split("-")
    return 12 * float(feet) + float(inches)


def test_snapshot_combine_is_pre_season_measurements_only(main_snap) -> None:  # type: ignore[no-untyped-def]
    c = main_snap.collect("combine")
    assert tuple(c.columns) == COMBINE_COLUMNS
    assert c["season"].max() <= main_snap.season
    assert c["season"].min() == 2000
    assert any("combine:" in lb for lb in main_snap.labels)


def test_ply_34_percentiles(ctx, main_snap, xw) -> None:  # type: ignore[no-untyped-def]
    comb = main_snap.collect("combine").to_dicts()
    pool: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in comb:
        for m, col in MEASURES.items():
            x = _inches(r[col]) if m == "height" else r[col]
            if r["pos"] is not None and x is not None:
                pool[(r["pos"], m)].append(float(x))
    gsis_of = {pfr: g for pfr, g in xw.items()}
    latest: dict[str, dict[str, Any]] = {}
    unlinked = 0
    for r in sorted(comb, key=lambda r: (r["season"], r["pfr_id"] or "")):
        g = gsis_of.get(r["pfr_id"]) if r["pfr_id"] else None
        if g is None:
            unlinked += 1
            continue
        latest[g] = r
    frame = raw(ctx, "PLY-34")
    got = {(r["entity_id"], r["stat"]): r for r in frame.iter_rows(named=True)}
    checked = 0
    for g, r in latest.items():
        for m, col in MEASURES.items():
            x = _inches(r[col]) if m == "height" else r[col]
            if r["pos"] is None or x is None:
                assert (g, m) not in got
                continue
            vals = pool[(r["pos"], m)]
            below = sum(v < x for v in vals)
            above = sum(v > x for v in vals)
            ties = sum(v == x for v in vals)
            pct = ((above if m in LOWER_IS_BETTER else below) + 0.5 * ties) / len(vals)
            assert got[(g, m)]["value"] == pytest.approx(float(x)), (g, m)
            p = got[(g, f"{m}_pctl")]
            assert p["value"] == pytest.approx(pct, rel=1e-12), (g, m)
            assert p["n"] == len(vals) and p["cell"] == r["pos"]
            checked += 1
    assert checked > 1000
    assert {r["stat"] for r in frame.iter_rows(named=True)} <= set(MEASURES) | {
        f"{m}_pctl" for m in MEASURES
    }
    print(
        f"\nPLY-34: {len(latest)} players profiled; {unlinked} combine rows without a "
        "linked GSIS ID (kept in the pools)"
    )
    assert frame.filter(pl.col("entity_type") == "player").height > 0
