"""Raw Parquet store: data/raw/<dataset>/season=<YYYY>/pulled_at=<UTC>/part.parquet.

Every row gets pulled_at (UTC) and source. A re-pull whose content matches the latest stored
version writes nothing, so completed seasons never duplicate; a changed pull adds a new
version, which is the history the point-in-time store (Phase 2) reads."""

from __future__ import annotations

import datetime as dt
import hashlib
import io
from pathlib import Path

import polars as pl

from ge.config import REPO_ROOT

DATA_ROOT = REPO_ROOT / "data" / "raw"
_HASH_FILE = "content.sha256"
_TS_FORMAT = "%Y%m%dT%H%M%SZ"


def _content_hash(df: pl.DataFrame) -> str:
    buf = io.BytesIO()
    df.write_ipc(buf, compression="uncompressed")
    return hashlib.sha256(buf.getvalue()).hexdigest()


def _season_dir(root: Path, dataset: str, season: int) -> Path:
    return root / dataset / f"season={season}"


def partitions(root: Path, dataset: str, season: int) -> list[Path]:
    """Stored versions for one dataset and season, oldest first."""
    d = _season_dir(root, dataset, season)
    return sorted(p for p in d.glob("pulled_at=*") if (p / "part.parquet").exists())


def seasons_stored(root: Path, dataset: str) -> list[int]:
    return sorted(
        int(p.name.split("=", 1)[1])
        for p in (root / dataset).glob("season=*")
        if partitions(root, dataset, int(p.name.split("=", 1)[1]))
    )


def write_raw(
    df: pl.DataFrame,
    dataset: str,
    season: int,
    *,
    source: str,
    root: Path = DATA_ROOT,
    pulled_at: dt.datetime,
) -> Path | None:
    """Store one pull. Returns the new file, or None when content matches the latest version."""
    if pulled_at.tzinfo is None or pulled_at.utcoffset() != dt.timedelta(0):
        raise ValueError("pulled_at must be timezone-aware UTC")
    digest = _content_hash(df)
    existing = partitions(root, dataset, season)
    if existing and (existing[-1] / _HASH_FILE).read_text(encoding="ascii").strip() == digest:
        return None
    out_dir = _season_dir(root, dataset, season) / f"pulled_at={pulled_at.strftime(_TS_FORMAT)}"
    out_dir.mkdir(parents=True, exist_ok=False)
    stamped = df.with_columns(
        pl.lit(pulled_at).cast(pl.Datetime("us", "UTC")).alias("pulled_at"),
        pl.lit(source).alias("source"),
    )
    path = out_dir / "part.parquet"
    stamped.write_parquet(path)
    (out_dir / _HASH_FILE).write_text(digest + "\n", encoding="ascii", newline="\n")
    return path


def read_latest(root: Path, dataset: str, season: int) -> pl.DataFrame:
    parts = partitions(root, dataset, season)
    if not parts:
        raise FileNotFoundError(f"no stored {dataset} for season {season} under {root}")
    return pl.read_parquet(parts[-1] / "part.parquet")
