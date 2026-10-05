"""The metric output contract and the two steps every rate metric shares.

1. summarise: per entity x cell, the raw mean (`value`), the G3 recency-weighted mean
   (`value_w`), the play count `n`, G3's `n_eff`, and G2's min-sample flag; plus one `league`
   row per cell (unweighted league mean, plan A2). Every entity gets a row for every cell, with
   n = 0 and a null value where it has no plays.
2. shrink (G1): shrunk = (n_eff * value_w + k * prior) / (n_eff + k); = prior at n = 0.

Data: nflverse; charting: FTN Data via nflverse."""

from __future__ import annotations

import math
from collections import defaultdict
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
    dropped. Optional columns: d (denominator, default 1) and c (how many plays the unit
    stands for, default 1), so value = sum x / sum d, value_w = sum w x / sum w d,
    n = sum c and n_eff = (sum w c)^2 / sum w^2 c. With d = c = 1 that is the plain mean.
    `entities` (entity_id, team) sets the grid; rows are keyed by both, so a player traded
    mid-season has one row per team (ruling 2026-10-04)."""
    # Rule 6: a canonical row order, so float sums don't depend on how the store's rows
    # happen to be ordered.
    for col in ("d", "c"):
        if col not in units.columns:
            units = units.with_columns(pl.lit(1.0).alias(col))
    u = units.filter(pl.col("x").is_not_null()).with_columns(
        (pl.lit(0.5) ** (pl.col("g") / h)).alias("w")
    )
    agg = _fsum_groups(u, ["entity_id", "team", "cell"])
    grid = (
        entities.select("entity_id", "team")
        .unique()
        .join(pl.DataFrame({"cell": list(cells)}, schema={"cell": pl.Utf8}), how="cross")
    )
    out = grid.join(agg, on=["entity_id", "team", "cell"], how="left").with_columns(
        pl.col("n").fill_null(0), pl.col("n_eff").fill_null(0.0)
    )
    parts = [out.with_columns(pl.lit(entity_type).alias("entity_type"))]
    if league:
        lg = _fsum_groups(u.with_columns(pl.lit(1.0).alias("w")), ["cell"]).select(
            "cell", "n", "value"
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
    return finish(df).sort("entity_type", "entity_id", "team", "cell")


def _fsum_groups(u: pl.DataFrame, keys: list[str]) -> pl.DataFrame:
    """Per group: n = sum c, value = sum x / sum d, value_w = sum w x / sum w d,
    n_eff = (sum w c)^2 / sum w^2 c. Sums use math.fsum, which is exact, so the result doesn't
    depend on row order or memory layout (rule 6: byte-identical outputs)."""
    acc: dict[tuple[object, ...], list[list[float]]] = defaultdict(lambda: [[] for _ in range(7)])
    for row in u.select(*keys, "w", "x", "d", "c").iter_rows():
        k, (w, x, d, c) = row[: len(keys)], row[len(keys) :]
        for lst, val in zip(acc[k], (c, x, d, w * x, w * d, w * c, w * w * c), strict=True):
            lst.append(val)
    rows = []
    for k, (cs, xs, ds, wxs, wds, wcs, w2cs) in acc.items():
        sd, swd = math.fsum(ds), math.fsum(wds)
        swc, sw2c = math.fsum(wcs), math.fsum(w2cs)
        rows.append(
            (
                *k,
                round(math.fsum(cs)),
                math.fsum(xs) / sd if sd else None,
                math.fsum(wxs) / swd if swd else None,
                swc * swc / sw2c if sw2c else 0.0,
            )
        )
    schema = {
        **{key: pl.Utf8 for key in keys},
        "n": pl.Int64,
        "value": pl.Float64,
        "value_w": pl.Float64,
        "n_eff": pl.Float64,
    }
    return pl.DataFrame(rows, schema=schema, orient="row")


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
    the team's shrunk OFF-01 run EPA). `cell=None` means the same cell as the row; `by="team"`
    matches the row's team to the parent's team rows (PLY-16 lanes shrink toward the team's
    OFF-12 cell)."""

    spec_id: str
    stat: str
    cell: str | None
    by: Literal["entity", "team"] = "entity"


@dataclass(frozen=True)
class Computed:
    """Prior computed per row by the metric itself: a function of the context returning
    entity_id, team, cell, prior (e.g. PLY-15's default redistribution rule)."""

    fn: Callable[[MetricContext], pl.DataFrame]


@dataclass(frozen=True)
class AtPosition:
    """Prior = the league value pooled over players at a position (ruling 2026-10-04): a fixed
    one ("league QB", "league RB") or the player's own weekly-roster position ("league at
    position"). The raw frame carries the pooled values as league rows "league:<POS>"; a
    player with no roster position gets no prior and no shrunk value (noted)."""

    fixed: str | None = None


Prior = League | Fixed | Parent | Computed | AtPosition
NO_POSITION = "no roster position: no position prior"


def position_league_rows(
    ctx: MetricContext, units: pl.DataFrame, spec_id: str, stat: str
) -> pl.DataFrame:
    """League rows "league:<POS>" per cell: sum x / sum d over every unit of players at that
    weekly-roster position (math.fsum, rule 6)."""
    for col in ("d", "c"):
        if col not in units.columns:
            units = units.with_columns(pl.lit(1.0).alias(col))
    pos = ctx.positions
    u = (
        units.filter(pl.col("x").is_not_null())
        .with_columns(
            pl.col("entity_id")
            .replace_strict(pos, default=None, return_dtype=pl.Utf8)
            .alias("pos"),
            pl.lit(1.0).alias("w"),
        )
        .filter(pl.col("pos").is_not_null() & (pl.col("pos") != ""))
    )
    g = _fsum_groups(u, ["pos", "cell"])
    return finish(
        g.select(
            pl.lit(spec_id).alias("spec_id"),
            pl.lit("league").alias("entity_type"),
            pl.concat_str([pl.lit("league:"), pl.col("pos")]).alias("entity_id"),
            "cell",
            pl.lit(stat).alias("stat"),
            "value",
            pl.col("value").alias("value_w"),
            "n",
            pl.col("n").cast(pl.Float64).alias("n_eff"),
        )
    )


NO_FTN = "no FTN"
MISSING_FTN = "no FTN: missing"


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
    # PLY-15: below the minimum sample the observation isn't used at all (shrunk = prior).
    prior_only_below_min: bool = False

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


def apply_shrink(rows: pl.DataFrame, k: pl.Expr, prior_only: pl.Expr | None = None) -> pl.DataFrame:
    """G1 on rows that already carry a `prior` column. No observation (n = 0, or no defined
    value, e.g. a ratio whose expected total is 0), or a row `prior_only` marks, leaves the
    prior."""
    no_obs = (pl.col("n") == 0) | pl.col("value_w").is_null()
    if prior_only is not None:
        no_obs = no_obs | prior_only
    return rows.with_columns(k.alias("k")).with_columns(
        pl.when(no_obs)
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
    if rows.height and (rows["note"].fill_null("") == NO_FTN).all():  # .all() skips nulls
        # Ruling 2026-10-04: no FTN charting (before 2022) means the metric is missing; the
        # rows stay, with no prior and no shrunk value, and matchup terms using it add zero.
        return rows.with_columns(
            pl.lit(None, dtype=pl.Float64).alias("k"),
            pl.lit(None, dtype=pl.Float64).alias("prior"),
            pl.lit(None, dtype=pl.Float64).alias("shrunk"),
            pl.lit(MISSING_FTN).alias("note"),
        ).select(list(SHRUNK_SCHEMA))
    pr = sd.prior
    if isinstance(pr, Fixed):
        rows = rows.with_columns(pl.lit(pr.get()).alias("prior"))
    elif isinstance(pr, Parent):
        p = parent(pr.spec_id, pr.stat)
        if pr.cell is not None:
            p = p.filter(pl.col("cell") == pr.cell)
        key = "entity_id" if pr.by == "entity" else "team"
        on = [key] if pr.cell is not None else [key, "cell"]
        p = p.select(
            pl.col("entity_id").alias(key),
            *([] if pr.cell else ["cell"]),
            pl.col("shrunk").alias("prior"),
        )
        rows = rows.join(p, on=on, how="left")
    elif isinstance(pr, Computed):
        rows = rows.join(pr.fn(ctx), on=["entity_id", "team", "cell"], how="left")
    elif isinstance(pr, AtPosition):
        pos = ctx.positions
        lg = raw.filter(
            (pl.col("stat") == sd.stat) & pl.col("entity_id").str.starts_with("league:")
        ).select(pl.col("entity_id").alias("_key"), "cell", pl.col("value").alias("prior"))
        pos_key = (
            pl.lit(f"league:{pr.fixed}")
            if pr.fixed
            else pl.concat_str(
                [
                    pl.lit("league:"),
                    pl.col("entity_id").replace_strict(pos, default=None, return_dtype=pl.Utf8),
                ]
            )
        )
        rows = (
            rows.with_columns(pos_key.alias("_key"))
            .join(lg, on=["_key", "cell"], how="left")
            .drop("_key")
        )
        unknown = pl.col("prior").is_null()
        rows = rows.with_columns(
            pl.when(unknown).then(pl.lit(NO_POSITION)).otherwise(pl.col("note")).alias("note")
        )
        out = apply_shrink(rows.filter(~unknown), sd.k_expr())
        missing = rows.filter(unknown).with_columns(
            sd.k_expr().alias("k"), pl.lit(None, dtype=pl.Float64).alias("shrunk")
        )
        return pl.concat([out.select(list(SHRUNK_SCHEMA)), missing.select(list(SHRUNK_SCHEMA))])
    elif side is not None and ctx.week is not None and cv.in_carryover_window(ctx.week):
        # G4 is a team rule (new play-caller or QB); player metrics have section 4 priors.
        rows = _carryover(ctx, spec_id, sd, rows, side)
    else:
        lg = raw.filter((pl.col("stat") == sd.stat) & (pl.col("entity_type") == "league"))
        rows = rows.join(lg.select("cell", pl.col("value").alias("prior")), on="cell", how="left")
    if rows["prior"].null_count():
        bad = rows.filter(pl.col("prior").is_null())
        raise ValueError(
            f"{spec_id} {sd.stat}: no prior for {bad.select('entity_id', 'cell').rows()[:5]}"
        )
    skip = pl.col("below_min_sample") if sd.prior_only_below_min else None
    return apply_shrink(rows, sd.k_expr(), prior_only=skip).select(list(SHRUNK_SCHEMA))


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
