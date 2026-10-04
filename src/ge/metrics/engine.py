"""The metric output contract and the two steps every rate metric shares.

1. summarise: per entity x cell, the raw mean (`value`), the G3 recency-weighted mean
   (`value_w`), the play count `n`, G3's `n_eff`, and G2's min-sample flag; plus one `league`
   row per cell (unweighted league mean, plan A2). Every entity gets a row for every cell, with
   n = 0 and a null value where it has no plays.
2. shrink (G1): shrunk = (n_eff * value_w + k * prior) / (n_eff + k); = prior at n = 0.

Data: nflverse; charting: FTN Data via nflverse."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

import polars as pl

from ge.config import load_params
from ge.metrics import conventions as cv

if TYPE_CHECKING:
    from ge.metrics.context import MetricContext

RAW_SCHEMA: dict[str, pl.DataType | type[pl.DataType]] = {
    "spec_id": pl.Utf8,
    "entity_type": pl.Utf8,  # team | player | league
    "entity_id": pl.Utf8,
    "team": pl.Utf8,
    "cell": pl.Utf8,
    "stat": pl.Utf8,
    "value": pl.Float64,  # unweighted observed value
    "value_w": pl.Float64,  # G3 recency-weighted observed value (what G1 shrinks)
    "n": pl.Int64,
    "n_eff": pl.Float64,
    "min_n": pl.Float64,
    "below_min_sample": pl.Boolean,
    "proxy": pl.Boolean,
    "note": pl.Utf8,
}
SHRUNK_SCHEMA: dict[str, pl.DataType | type[pl.DataType]] = {
    **RAW_SCHEMA,
    "k": pl.Float64,
    "prior": pl.Float64,
    "shrunk": pl.Float64,
}
UNITS_SCHEMA: dict[str, pl.DataType | type[pl.DataType]] = {
    "entity_id": pl.Utf8,
    "team": pl.Utf8,
    "cell": pl.Utf8,
    "g": pl.Float64,
    "x": pl.Float64,
}
Side = Literal["offense", "defense"]


def param(key: str) -> float:
    """A params.yaml value by "group.name" key (registry entries name keys, not numbers)."""
    group, name = key.split(".")
    return float(getattr(getattr(load_params(), group), name).value)


def empty_raw() -> pl.DataFrame:
    return pl.DataFrame(schema=RAW_SCHEMA)


def finish(df: pl.DataFrame) -> pl.DataFrame:
    """Cast to the raw schema, filling optional columns."""
    for c, t in RAW_SCHEMA.items():
        if c not in df.columns:
            default: object = False if t == pl.Boolean else None
            df = df.with_columns(pl.lit(default, dtype=t).alias(c))
    return df.select([pl.col(c).cast(t) for c, t in RAW_SCHEMA.items()])


def summarise(
    units: pl.DataFrame,
    *,
    spec_id: str,
    stat: str,
    entity_type: str,
    entities: pl.DataFrame,
    cells: Sequence[str],
    h: float,
    min_n: Mapping[str, float] | float | None = None,
    league: bool = True,
) -> pl.DataFrame:
    """Step 1. `units` has entity_id, team, cell, g (games ago) and x; rows with a null x are
    dropped. `entities` (entity_id, team) sets the grid."""
    # Rule 6: a canonical row order, so float sums don't depend on how the store's rows
    # happen to be ordered.
    u = (
        units.filter(pl.col("x").is_not_null())
        .sort("entity_id", "cell", "g", "x")
        .with_columns((pl.lit(0.5) ** (pl.col("g") / h)).alias("w"))
    )
    agg = u.group_by("entity_id", "cell").agg(
        pl.len().cast(pl.Int64).alias("n"),
        pl.col("x").mean().alias("value"),
        ((pl.col("w") * pl.col("x")).sum() / pl.col("w").sum()).alias("value_w"),
        (pl.col("w").sum() ** 2 / (pl.col("w") ** 2).sum()).alias("n_eff"),
    )
    grid = (
        entities.select("entity_id", "team")
        .unique()
        .join(pl.DataFrame({"cell": list(cells)}, schema={"cell": pl.Utf8}), how="cross")
    )
    out = grid.join(agg, on=["entity_id", "cell"], how="left").with_columns(
        pl.col("n").fill_null(0), pl.col("n_eff").fill_null(0.0)
    )
    parts = [out.with_columns(pl.lit(entity_type).alias("entity_type"))]
    if league:
        lg = u.group_by("cell").agg(
            pl.len().cast(pl.Int64).alias("n"), pl.col("x").mean().alias("value")
        )
        lg = pl.DataFrame({"cell": list(cells)}, schema={"cell": pl.Utf8}).join(
            lg, on="cell", how="left"
        )
        parts.append(
            lg.with_columns(
                pl.lit("league").alias("entity_type"),
                pl.lit("league").alias("entity_id"),
                pl.lit(None, dtype=pl.Utf8).alias("team"),
                pl.col("value").alias("value_w"),
                pl.col("n").fill_null(0),
                pl.col("n").fill_null(0).cast(pl.Float64).alias("n_eff"),
            )
        )
    df = pl.concat([finish(p) for p in parts])
    mins = _min_expr(min_n)
    df = df.with_columns(
        pl.lit(spec_id).alias("spec_id"),
        pl.lit(stat).alias("stat"),
        mins.alias("min_n"),
    ).with_columns(
        pl.when(pl.col("entity_type") == "league")
        .then(pl.lit(False))
        .otherwise((pl.col("n") < pl.col("min_n")).fill_null(False))
        .alias("below_min_sample")
    )
    return finish(df).sort("entity_type", "entity_id", "cell")


def _min_expr(min_n: Mapping[str, float] | float | None) -> pl.Expr:
    if min_n is None:
        return pl.lit(None, dtype=pl.Float64)
    if isinstance(min_n, Mapping):
        return pl.col("cell").replace_strict(dict(min_n), default=None, return_dtype=pl.Float64)
    return pl.lit(float(min_n))


# ---- step 2: priors and shrinkage ----


@dataclass(frozen=True)
class League:
    """Prior = league mean for the cell; in weeks 1-4, G4 carryover instead."""


@dataclass(frozen=True)
class Fixed:
    """Prior = a stated value (e.g. "prior 0"), or a params key."""

    value: float | None = None
    key: str | None = None

    def get(self) -> float:
        return param(self.key) if self.key is not None else float(self.value or 0.0)


@dataclass(frozen=True)
class Parent:
    """Prior = the entity's shrunk value of another metric's cell (e.g. OFF-12 cells shrink to
    the team's shrunk OFF-01 run EPA)."""

    spec_id: str
    stat: str
    cell: str


Prior = League | Fixed | Parent


@dataclass(frozen=True)
class StatDef:
    """How one stat of a metric is shrunk. `k` is a params key, or one per cell. `missing`
    names what the spec lacks; shrinking such a stat raises NotImplementedError."""

    stat: str
    half_life: cv.HalfLife
    k: str | Mapping[str, str] | None = None
    prior: Prior = field(default_factory=League)
    missing: str | None = None
    eligible: Callable[[pl.DataFrame], pl.DataFrame] | None = None

    def k_keys(self) -> list[str]:
        if self.k is None:
            return []
        return [self.k] if isinstance(self.k, str) else list(self.k.values())

    def k_expr(self) -> pl.Expr:
        if isinstance(self.k, str):
            return pl.lit(param(self.k))
        assert self.k is not None
        return pl.col("cell").replace_strict(
            {c: param(key) for c, key in self.k.items()}, return_dtype=pl.Float64
        )


def apply_shrink(rows: pl.DataFrame, k: pl.Expr) -> pl.DataFrame:
    """G1 on rows that already carry a `prior` column. No observation (n = 0, or no defined
    value, e.g. a ratio whose expected total is 0) leaves the prior."""
    return rows.with_columns(k.alias("k")).with_columns(
        pl.when((pl.col("n") == 0) | pl.col("value_w").is_null())
        .then(pl.col("prior"))
        .otherwise(
            (pl.col("n_eff") * pl.col("value_w") + pl.col("k") * pl.col("prior"))
            / (pl.col("n_eff") + pl.col("k"))
        )
        .alias("shrunk")
    )


def shrink_stat(
    ctx: MetricContext,
    spec_id: str,
    sd: StatDef,
    raw: pl.DataFrame,
    side: Side | None,
    parent: Callable[[str, str], pl.DataFrame],
) -> pl.DataFrame:
    """Step 2 for one stat of one metric. `parent(spec_id, stat)` returns another metric's
    shrunk rows (from the same context)."""
    if sd.missing:
        raise NotImplementedError(sd.missing)
    if sd.k is None:
        raise ValueError(f"{spec_id} {sd.stat}: a count, not shrunk")
    rows = raw.filter((pl.col("stat") == sd.stat) & (pl.col("entity_type") != "league"))
    if sd.eligible is not None:
        rows = sd.eligible(rows)
    pr = sd.prior
    if isinstance(pr, Fixed):
        rows = rows.with_columns(pl.lit(pr.get()).alias("prior"))
    elif isinstance(pr, Parent):
        p = parent(pr.spec_id, pr.stat).filter(pl.col("cell") == pr.cell)
        rows = rows.join(
            p.select("entity_id", pl.col("shrunk").alias("prior")), on="entity_id", how="left"
        )
    elif ctx.week is not None and cv.in_carryover_window(ctx.week):
        rows = _carryover(ctx, spec_id, sd, rows, side)
    else:
        lg = raw.filter((pl.col("stat") == sd.stat) & (pl.col("entity_type") == "league"))
        rows = rows.join(lg.select("cell", pl.col("value").alias("prior")), on="cell", how="left")
    if rows["prior"].null_count():
        bad = rows.filter(pl.col("prior").is_null())
        if "no FTN" in set(bad["note"].drop_nulls().to_list()):
            raise NotImplementedError(
                f"{spec_id} {sd.stat}: no FTN charting this season (before 2022), so there is no "
                "league value to shrink toward; BT-07a's 'FTN inputs set to their priors' needs "
                "a prior defined without later seasons (Phase 3e)"
            )
        raise ValueError(
            f"{spec_id} {sd.stat}: no prior for {bad.select('entity_id', 'cell').rows()[:5]}"
        )
    out = apply_shrink(rows, sd.k_expr())
    return out.select(list(SHRUNK_SCHEMA))


def _carryover(
    ctx: MetricContext, spec_id: str, sd: StatDef, rows: pl.DataFrame, side: Side | None
) -> pl.DataFrame:
    """G4: last season's shrunk value (league average where the team has none), regressed a
    further 1/3 toward last season's league average on a new play-caller or QB. Last season's
    rows are matched by franchise, so a relocated team keeps its history."""
    from ge.metrics.registry import raw as raw_of
    from ge.metrics.registry import shrunk as shrunk_of

    if side is None:
        raise NotImplementedError(f"G4: {spec_id} has no team side for carryover")
    prev = ctx.prior_context()
    fr = pl.col("entity_id").map_elements(ctx.franchise, return_dtype=pl.Utf8).alias("_fr")
    last = shrunk_of(prev, spec_id, sd.stat).select(fr, "cell", pl.col("shrunk").alias("_last"))
    lg = raw_of(prev, spec_id).filter(
        (pl.col("stat") == sd.stat) & (pl.col("entity_type") == "league")
    )
    lg_map = dict(lg.select("cell", "value").iter_rows())
    rows = rows.with_columns(fr).join(last, on=["_fr", "cell"], how="left").drop("_fr")
    priors, notes = [], []
    for r in rows.iter_rows(named=True):
        league = lg_map.get(r["cell"])
        if league is None:
            raise ValueError(f"G4: {spec_id} {sd.stat}: no prior-season league value")
        base = r["_last"] if r["_last"] is not None else league
        changed, why = ctx.g4_changed(r["entity_id"], side)
        priors.append(cv.carryover_prior(base, league, changed=changed))
        notes.append("; ".join(x for x in (r["note"], f"G4 carryover{why}") if x))
    return rows.drop("_last").with_columns(
        pl.Series("prior", priors, dtype=pl.Float64), pl.Series("note", notes, dtype=pl.Utf8)
    )
