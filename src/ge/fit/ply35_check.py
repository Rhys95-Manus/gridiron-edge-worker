"""BT-02 report check for PLY-35 (spec synced 2026-10-16): each stat's mean raw gap in one
season beside another (2026 beside 2024), to catch any change from ffopportunity's model files
re-uploaded in December 2025. Same qualifying rows as the metric; the holdout is refused.

Data: nflverse; charting: FTN Data via nflverse; expected points: ffopportunity (ffverse) via
nflverse; data license not stated by the source."""

from __future__ import annotations

import math
from pathlib import Path

import polars as pl

from ge.ingest.raw import partitions, read_latest
from ge.metrics import expected as ex
from ge.store.holdout import refuse_holdout

ALL = "all"


def mean_raw_gaps(ff: pl.DataFrame) -> pl.DataFrame:
    """(stat, group, n, mean) over qualifying player-games: every group and `all`."""
    rows, _ = ex.qualifying(ff)
    gaps = ex.raw_gaps(rows)
    out = []
    for stat in ex.STATS:
        by: dict[str, list[float]] = {ALL: []}
        for g, x in gaps.select("group", stat).iter_rows():
            by.setdefault(g, []).append(float(x))
            by[ALL].append(float(x))
        for g, xs in sorted(by.items()):
            if xs:
                out.append((stat, g, len(xs), math.fsum(xs) / len(xs)))
    return pl.DataFrame(
        out,
        schema={"stat": pl.Utf8, "group": pl.Utf8, "n": pl.Int64, "mean": pl.Float64},
        orient="row",
    )


def comparison_lines(a: pl.DataFrame, b: pl.DataFrame, sa: int, sb: int) -> list[str]:
    """Markdown rows: each stat and group's mean raw gap (n) in both seasons and b - a."""
    lines = [
        f"| stat | group | {sa} mean gap (n) | {sb} mean gap (n) | {sb} - {sa} |",
        "|---|---|---|---|---|",
    ]
    j = a.join(b, on=["stat", "group"], how="full", coalesce=True, suffix="_b")
    order = {s: i for i, s in enumerate(ex.STATS)}
    for r in sorted(
        j.iter_rows(named=True), key=lambda r: (order[r["stat"]], r["group"] != ALL, r["group"])
    ):
        ma, mb = r["mean"], r["mean_b"]
        fa = "—" if ma is None else f"{ma:+.3f} ({r['n']})"
        fb = "—" if mb is None else f"{mb:+.3f} ({r['n_b']})"
        d = "—" if ma is None or mb is None else f"{mb - ma:+.3f}"
        lines.append(f"| {r['stat']} | {r['group']} | {fa} | {fb} | {d} |")
    return lines


def report_lines(root: Path, sa: int, sb: int) -> list[str]:
    """The report section: the comparison, or why it is not available."""
    head = [
        f"## PLY-35 gap check: {sb} mean raw gap beside {sa}",
        "",
        "Per qualifying player-game (a target or carry, a player), actual - expected, from each "
        "season's latest stored pull; to catch any change from the model files re-uploaded in "
        "December 2025.",
        "",
    ]
    missing = [s for s in (sa, sb) if not partitions(root, "ff_opportunity", s)]
    if missing:
        return [*head, f"not available: no stored ff_opportunity for season(s) {missing}"]
    return head + gap_check(root, sa, sb)


def gap_check(root: Path, sa: int, sb: int) -> list[str]:
    """The comparison from each season's latest stored pull. The holdout is refused (BT-07b)."""
    refuse_holdout(sa, "PLY-35 gap check")
    refuse_holdout(sb, "PLY-35 gap check")
    a = mean_raw_gaps(read_latest(root, "ff_opportunity", sa))
    b = mean_raw_gaps(read_latest(root, "ff_opportunity", sb))
    return comparison_lines(a, b, sa, sb)
