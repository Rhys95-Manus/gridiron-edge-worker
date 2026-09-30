"""BT-01 DuckDB database over the raw Parquet store, for SQL over every stored version.

`ge store build` writes data/store.duckdb with one view per dataset (every version, with its
season and pulled_at partition as columns) and a `games` table (kickoff and last-play time per
game, from the latest versions). Snapshots don't read this file: they read the Parquet
partitions directly so a test can point them at a copy of the store."""

from __future__ import annotations

from pathlib import Path

import duckdb
import polars as pl

from ge.ingest.raw import DATA_ROOT, read_latest, seasons_stored
from ge.store.known_at import game_ends, with_kickoff

DB_PATH = DATA_ROOT.parent / "store.duckdb"


def _datasets(root: Path) -> list[str]:
    return sorted(
        p.name
        for p in root.iterdir()
        if p.is_dir() and any(p.glob("season=*/pulled_at=*/part.parquet"))
    )


def games_table(root: Path = DATA_ROOT) -> pl.DataFrame:
    """BT-01: one row per scheduled game: kickoff (UTC) and last play time (null if unplayed)."""
    frames = []
    pbp_seasons = set(seasons_stored(root, "pbp"))
    for s in seasons_stored(root, "schedules"):
        sched = with_kickoff(read_latest(root, "schedules", s)).select(
            "game_id", "season", "week", "game_type", "home_team", "away_team", "kickoff_utc"
        )
        if s in pbp_seasons:
            ends = game_ends(read_latest(root, "pbp", s).select("game_id", "time_of_day"))
            sched = sched.join(ends, on="game_id", how="left")
        else:
            sched = sched.with_columns(
                pl.lit(None, dtype=pl.Datetime("us", "UTC")).alias("game_end_utc")
            )
        frames.append(sched)
    return pl.concat(frames).sort("kickoff_utc", "game_id")


def build(root: Path = DATA_ROOT, db_path: Path = DB_PATH) -> dict[str, int]:
    """BT-01: (re)create the views and the games table. Returns row counts per object."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    with duckdb.connect(str(db_path)) as con:
        for ds in _datasets(root):
            glob = (root / ds / "season=*" / "pulled_at=*" / "part.parquet").as_posix()
            con.execute(
                f'CREATE OR REPLACE VIEW "{ds}" AS SELECT *, '
                "CAST(regexp_extract(filename, 'season=(\\d+)', 1) AS INTEGER) "
                "AS partition_season, "
                "strptime(regexp_extract(filename, 'pulled_at=([0-9TZ]+)', 1), '%Y%m%dT%H%M%SZ') "
                "AS partition_pulled_at "
                f"FROM read_parquet('{glob}', union_by_name = true, filename = true)"
            )
            counts[ds] = int(con.execute(f'SELECT count(*) FROM "{ds}"').fetchone()[0])  # type: ignore[index]
        con.register("games_df", games_table(root))
        con.execute("CREATE OR REPLACE TABLE games AS SELECT * FROM games_df")
        con.unregister("games_df")
        counts["games"] = int(con.execute("SELECT count(*) FROM games").fetchone()[0])  # type: ignore[index]
    return counts
