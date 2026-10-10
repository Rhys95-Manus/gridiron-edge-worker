"""BT-02 split-half for stats that are not a single mean of units (user ruling 2026-10-08):
the stat is computed whole within each half.

- Gaps (DEF-10, DEF-13, PLY-17, PLY-19's gap; DEF-08's on/off): each half takes m units on
  each side (`arm`), so m counts the smaller side; value = mean(x | side 1) - mean(x | side 0).
- Ratios (DEF-04; PLY-04 WOPR): each half takes m counted units (targets); the value is the
  stat's own formula on the half (value functions below).

Rows: entity, game, c (how many counted units the row is), an optional arm column, and the
columns the value function reads. As in ge.fit.splithalf: each entity's games go to half A or B
at random per split, rows are taken in random order until m are in (per arm), entities short of
m anywhere are left out; k_from_halves then applies the same r, k_m and no-signal rule. Seeded
from the caller's key (rule 6); sums are sequential over sorted rows."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import polars as pl

from ge.fit.splithalf import KFit, SplitHalfConfig, k_from_halves, seeded

ValueFn = Callable[[pl.DataFrame], pl.DataFrame]  # rows of one half -> entity, value
_HV = {
    "split": pl.Int64,
    "m": pl.Int64,
    "entity": pl.Utf8,
    "v_a": pl.Float64,
    "v_b": pl.Float64,
    "n_a": pl.Float64,
    "n_b": pl.Float64,
    "group": pl.Utf8,
}


def _fsum_by(df: pl.DataFrame, col: str) -> dict[str, float]:
    """Per-entity sums, sequential over rows sorted by entity (np.add.reduceat), so the result
    doesn't depend on row order or threads (rule 6)."""
    if df.is_empty():
        return {}
    s = df.select("entity", pl.col(col).cast(pl.Float64)).sort("entity", col)
    ents = s["entity"].to_numpy()
    vals = s[col].to_numpy()
    starts = np.flatnonzero(np.r_[True, ents[1:] != ents[:-1]])
    sums = np.add.reduceat(vals, starts)
    return dict(zip(ents[starts].tolist(), sums.tolist(), strict=True))


def gap_value(rows: pl.DataFrame) -> pl.DataFrame:
    """mean(x | arm 1) - mean(x | arm 0) per entity."""
    out = []
    on, off = rows.filter(pl.col("arm") == 1), rows.filter(pl.col("arm") == 0)
    s1, s0 = _fsum_by(on, "x"), _fsum_by(off, "x")
    n1 = dict(on.group_by("entity").len().iter_rows())
    n0 = dict(off.group_by("entity").len().iter_rows())
    for e in sorted(set(s1) & set(s0)):
        out.append((e, s1[e] / n1[e] - s0[e] / n0[e]))
    return pl.DataFrame(out, schema={"entity": pl.Utf8, "value": pl.Float64}, orient="row")


def ratio_value(rows: pl.DataFrame) -> pl.DataFrame:
    """sum(num) / sum(den) per entity (DEF-04's actual / expected)."""
    num, den = _fsum_by(rows, "num"), _fsum_by(rows, "den")
    out = [(e, num[e] / den[e]) for e in sorted(num) if den.get(e)]
    return pl.DataFrame(out, schema={"entity": pl.Utf8, "value": pl.Float64}, orient="row")


def diff_of_ratios_value(rows: pl.DataFrame) -> pl.DataFrame:
    """DEF-04 epa_diff: sum(a_epa) / sum(a_tg) - sum(e_epa) / sum(e_tg) per entity."""
    ae, at = _fsum_by(rows, "a_epa"), _fsum_by(rows, "a_tg")
    ee, et = _fsum_by(rows, "e_epa"), _fsum_by(rows, "e_tg")
    out = [(e, ae[e] / at[e] - ee[e] / et[e]) for e in sorted(ae) if at.get(e) and et.get(e)]
    return pl.DataFrame(out, schema={"entity": pl.Utf8, "value": pl.Float64}, orient="row")


def wopr_value(target_weight: float, air_weight: float) -> ValueFn:
    """PLY-04 WOPR = target weight x target share + air weight x air share, per entity."""

    def fn(rows: pl.DataFrame) -> pl.DataFrame:
        t, tt = _fsum_by(rows, "his_target"), _fsum_by(rows, "c")
        a, at = _fsum_by(rows, "his_air"), _fsum_by(rows, "team_air")
        out = [
            (e, target_weight * t[e] / tt[e] + air_weight * (a[e] / at[e] if at[e] else 0.0))
            for e in sorted(t)
            if tt.get(e)
        ]
        return pl.DataFrame(out, schema={"entity": pl.Utf8, "value": pl.Float64}, orient="row")

    return fn


def wopr_residual_value(target_weight: float, air_weight: float) -> ValueFn:
    """PLY-04 WOPR's residual from its slot prior (v2 ruling 1): the half's WOPR minus the mean
    slot-prior WOPR over the half's player-games, weighted by team targets (column `p` = his
    slot's prior WOPR in that target's game; one row per team target)."""
    wopr = wopr_value(target_weight, air_weight)

    def fn(rows: pl.DataFrame) -> pl.DataFrame:
        w = wopr(rows)
        cp = _fsum_by(rows.with_columns((pl.col("c") * pl.col("p")).alias("_cp")), "_cp")
        cc = _fsum_by(rows, "c")
        prior = pl.DataFrame(
            [(e, cp[e] / cc[e]) for e in sorted(cp) if cc.get(e)],
            schema={"entity": pl.Utf8, "_p": pl.Float64},
            orient="row",
        )
        return w.join(prior, on="entity").select(
            "entity", (pl.col("value") - pl.col("_p")).alias("value")
        )

    return fn


def whole_half_values(
    rows: pl.DataFrame,
    cfg: SplitHalfConfig,
    seed_key: str,
    value: ValueFn,
    arm: str | None = None,
    center: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """`center` (entity, mu): subtracted from both halves' values (v2 ruling 2: a multi-cell
    stat minus its cell's league mean in the same season). Optional rows column `group`: the
    entity each entity-cell belongs to (ruling 3: N counts distinct entities)."""
    groups = (
        rows.select(pl.col("entity").cast(pl.Utf8), pl.col("group").cast(pl.Utf8)).unique()
        if "group" in rows.columns
        else None
    )
    if groups is not None:
        rows = rows.drop("group")
    r = rows.with_columns(
        pl.col("entity").cast(pl.Utf8),
        pl.col("game").cast(pl.Utf8),
        (pl.col(arm).cast(pl.Int64) if arm else pl.lit(0, dtype=pl.Int64)).alias("arm"),
        pl.col("c").cast(pl.Float64),
    )
    r = r.sort(r.columns)  # canonical order (rule 6)
    if r.is_empty():
        return pl.DataFrame(schema=_HV)
    games = r.select("entity", "game").unique().sort("entity", "game")
    arms = sorted(set(r["arm"].to_list()))
    frames = []
    for b in range(cfg.splits):
        g = seeded(f"{seed_key}/split{b}")
        side = g.integers(0, 2, games.height)
        key = g.random(r.height)
        rb = (
            r.with_columns(pl.Series("_key", key))
            .join(games.with_columns(pl.Series("_h", side)), on=["entity", "game"], how="left")
            .sort("entity", "_h", "arm", "_key")
            .with_columns(
                (pl.col("c").cum_sum().over("entity", "_h", "arm") - pl.col("c")).alias("_before")
            )
        )
        for m in cfg.m_grid:
            kept = rb.filter(pl.col("_before") < m)
            size = kept.group_by("entity", "_h", "arm").agg(pl.col("c").sum().alias("_n"))
            full = (
                size.filter(pl.col("_n") >= m)
                .group_by("entity")
                .agg(pl.len().alias("_k"), pl.col("_n").mean().alias("_mean_n"))
                .filter(pl.col("_k") == 2 * len(arms))
            )
            if full.is_empty():
                continue
            kept = kept.join(full.select("entity"), on="entity", how="semi")
            va = value(kept.filter(pl.col("_h") == 0)).rename({"value": "v_a"})
            vb = value(kept.filter(pl.col("_h") == 1)).rename({"value": "v_b"})
            hv = (
                va.join(vb, on="entity")
                .join(full.select("entity", "_mean_n"), on="entity")
                .select(
                    pl.lit(b, dtype=pl.Int64).alias("split"),
                    pl.lit(m, dtype=pl.Int64).alias("m"),
                    "entity",
                    "v_a",
                    "v_b",
                    pl.col("_mean_n").alias("n_a"),
                    pl.col("_mean_n").alias("n_b"),
                )
                .filter(pl.col("v_a").is_finite() & pl.col("v_b").is_finite())
            )
            if center is not None:
                hv = (
                    hv.join(center, on="entity", how="inner")
                    .with_columns(pl.col("v_a") - pl.col("mu"), pl.col("v_b") - pl.col("mu"))
                    .drop("mu")
                )
            frames.append(hv)
    if not frames:
        return pl.DataFrame(schema=_HV)
    out = pl.concat(frames)
    if groups is not None:
        out = out.join(groups, on="entity", how="left")
    else:
        out = out.with_columns(pl.col("entity").alias("group"))
    return out.sort("split", "m", "entity")


def whole_split_half_k(
    rows: pl.DataFrame,
    cfg: SplitHalfConfig,
    seed_key: str,
    value: ValueFn,
    arm: str | None = None,
) -> KFit:
    return k_from_halves(whole_half_values(rows, cfg, seed_key, value, arm), cfg)
