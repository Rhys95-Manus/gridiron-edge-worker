"""`ge metrics --season S --through-week W`: every metric for every team and player as they
stood after week W.

One snapshot, anchored on the first game of week W + 1 (by kickoff), at that game's decision
time unless --as-of is given, so every week-W game is visible and nothing later is. It writes
data/metrics/season=S/through_week=W/ with raw.parquet (every metric's raw rows),
shrunk.parquet (every stat that can be shrunk now) and not_computed.parquet (every metric or
stat that raises, with the reason: PAID metrics, priors that wait for Phase 3e, ...).

Data: nflverse; charting: FTN Data via nflverse."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from ge.ingest.raw import DATA_ROOT, read_latest
from ge.metrics.coaching import CoachingRegistry
from ge.metrics.context import build_context
from ge.metrics.engine import RAW_SCHEMA, SHRUNK_SCHEMA
from ge.metrics.registry import REGISTRY, raw, shrunk
from ge.store.snapshot import ATTRIBUTION, snapshot

OUT_ROOT = DATA_ROOT.parent / "metrics"
NC_SCHEMA = {"spec_id": pl.Utf8, "stat": pl.Utf8, "reason": pl.Utf8}
_ORDER = ["spec_id", "entity_type", "entity_id", "team", "cell", "stat"]


@dataclass(frozen=True)
class MetricsRun:
    anchor_game: str
    as_of: dt.datetime
    folder: Path
    summary: str


def anchor_game(season: int, through_week: int, root: Path = DATA_ROOT) -> str:
    """The first game of week `through_week + 1` by kickoff (game_id breaks ties)."""
    s = read_latest(root, "schedules", season).filter(pl.col("week") == through_week + 1)
    if s.is_empty():
        raise ValueError(f"no week {through_week + 1} games in the {season} schedules")
    return str(s.sort("gameday", "gametime", "game_id")["game_id"][0])


def run_metrics(
    season: int,
    through_week: int,
    *,
    as_of: dt.datetime | None = None,
    root: Path = DATA_ROOT,
    out_dir: Path = OUT_ROOT,
    registry: CoachingRegistry | None = None,
) -> MetricsRun:
    game = anchor_game(season, through_week, root)
    snap = snapshot(game, as_of, root=root)
    ctx = build_context(snap, registry)
    raws, shrunks, missing = [], [], []
    for sid in sorted(REGISTRY):
        e = REGISTRY[sid]
        try:
            raws.append(raw(ctx, sid))
        except NotImplementedError as exc:
            missing.append((sid, "*", str(exc)))
            continue
        for stat in sorted(e.stats):
            if e.stats[stat].k is None:  # a count (e.g. OFF-12 carries): never shrunk
                continue
            try:
                shrunks.append(shrunk(ctx, sid, stat))
            except NotImplementedError as exc:
                missing.append((sid, stat, str(exc)))
    raw_df = pl.concat(raws).select(list(RAW_SCHEMA)).sort(_ORDER, nulls_last=True)
    sh_df = pl.concat(shrunks).select(list(SHRUNK_SCHEMA)).sort(_ORDER, nulls_last=True)
    nc_df = pl.DataFrame(missing, schema=NC_SCHEMA, orient="row").sort("spec_id", "stat")
    folder = out_dir / f"season={season}" / f"through_week={through_week}"
    folder.mkdir(parents=True, exist_ok=True)
    for name, df in (("raw", raw_df), ("shrunk", sh_df), ("not_computed", nc_df)):
        df.write_parquet(folder / f"{name}.parquet", statistics=False)
    summary = _summary(season, through_week, game, snap.as_of, raw_df, sh_df, nc_df)
    return MetricsRun(game, snap.as_of, folder, summary)


def team_table(raw_df: pl.DataFrame, sh_df: pl.DataFrame) -> pl.DataFrame:
    """Per team: OFF-01 / OFF-02 / DEF-01 / DEF-02 overall (cell `all`), raw season-to-date
    values with their play counts, and the shrunk values."""
    cols = []
    for sid, stat, name in (
        ("OFF-01", "epa", "off_epa"),
        ("OFF-02", "success", "off_success"),
        ("DEF-01", "epa", "def_epa"),
        ("DEF-02", "success", "def_success"),
    ):
        keep = (
            (pl.col("spec_id") == sid)
            & (pl.col("stat") == stat)
            & (pl.col("cell") == "all")
            & (pl.col("entity_type") == "team")
        )
        r = raw_df.filter(keep).select(
            pl.col("entity_id").alias("team"),
            pl.col("value").alias(name),
            pl.col("n").alias(f"{name}_n"),
        )
        s = sh_df.filter(keep).select(
            pl.col("entity_id").alias("team"), pl.col("shrunk").alias(f"{name}_shrunk")
        )
        cols.append(r.join(s, on="team", how="left"))
    out = cols[0]
    for c in cols[1:]:
        out = out.join(c, on="team", how="full", coalesce=True)
    return out.sort("team")


def _summary(
    season: int,
    week: int,
    game: str,
    as_of: dt.datetime,
    raw_df: pl.DataFrame,
    sh_df: pl.DataFrame,
    nc_df: pl.DataFrame,
) -> str:
    table = team_table(raw_df, sh_df)
    with pl.Config(tbl_rows=-1, tbl_cols=-1, tbl_width_chars=200, float_precision=3):
        body = str(table)
    return "\n".join(
        [
            f"ge metrics: season {season} through week {week}",
            f"snapshot anchored on {game}, as_of {as_of.isoformat()}",
            f"{raw_df['spec_id'].n_unique()} metrics, {raw_df.height} raw rows, "
            f"{sh_df.height} shrunk rows; {nc_df.height} metric/stat pairs not computed",
            "",
            body,
            "",
            ATTRIBUTION,
        ]
    )
