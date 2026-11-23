"""SHD-14 / SHD-15 shadow store: write-once partitions under data/shadow, hash-chained manifest.

SHD-14: "Write-once partitions plus a hash-chained manifest; the writer has no update or delete.
Files and manifest lines are hashed with SHA-256. No snapshot row for a game can be written after
its kickoff. The writer refuses any path under data/raw."

Layout (planning report 4.6):
data/shadow/v<shadow_version>/<table>/season=<YYYY>/week=<WW>/written_at=<UTC>/part.parquet
plus content.sha256 beside it, and data/shadow/v<shadow_version>/MANIFEST.jsonl with one line
per written file: its SHA-256 and the SHA-256 of the previous manifest line."""

from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import io
import json
import os
import stat
import sys
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import polars as pl

from ge.config import REPO_ROOT

SHADOW_BASE = REPO_ROOT / "data" / "shadow"
RAW_ROOT = REPO_ROOT / "data" / "raw"
MANIFEST = "MANIFEST.jsonl"
_LOCK = "write.lock"
_HASH_FILE = "content.sha256"
_PART = "part.parquet"
_TS_FORMAT = "%Y%m%dT%H%M%S%fZ"
_GENESIS = "0" * 64
# SHD-19: "These rows carry pricing_mode after_the_fact; rows priced at the snapshot carry
# pricing_mode live."
PRICING_MODES = frozenset({"live", "after_the_fact"})
# Planning report 4.6 tables, plus attempts (each snapshot try, for SHD-12 miss reasons),
# schedules (SHD-03 re-pulls into the shadow store) and job_runs (SHD-03 close and settle
# checks, and ticks that failed with an unexpected error, for SHD-12 missed_error).
TABLES = frozenset(
    {
        "snapshots",
        "book_levels",
        "snapshot_status",
        "attempts",
        "closes",
        "results",
        "schedules",
        "job_runs",
    }
)
# SHD-14: "No snapshot row for a game can be written after its kickoff."
KICKOFF_TABLES = frozenset({"snapshots", "book_levels"})


class StorePathError(ValueError):
    """SHD-14: the writer refuses any path under data/raw, and anything outside data/shadow."""


class StoreError(ValueError):
    """SHD-14 / SHD-15: rows the store will not write."""


class KickoffPassed(StoreError):
    """SHD-14: no snapshot row for a game can be written after its kickoff."""


def _norm(p: Path) -> str:
    return os.path.normcase(str(p.resolve()))


def _under(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def check_store_path(path: Path, base: Path = SHADOW_BASE) -> Path:
    """SHD-14: the writer refuses any path under data/raw (as written, and its resolved
    junction target), and anything outside the shadow base (data/shadow; tests pass a
    temporary base). Returns the resolved path."""
    p = _norm(path)
    for raw in {os.path.normcase(str(RAW_ROOT.absolute())), _norm(RAW_ROOT)}:
        if _under(p, raw):
            raise StorePathError(f"SHD-14: refusing a path under data/raw: {path}")
    if not _under(p, _norm(base)):
        raise StorePathError(f"SHD-14: refusing a path outside {base}: {path}")
    return path.resolve()


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@contextlib.contextmanager
def _locked(path: Path, timeout_s: float = 120.0) -> Iterator[None]:
    """One writer at a time per shadow version (OS file lock; released if the process dies)."""
    fh = path.open("a+b")
    try:
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                if sys.platform == "win32":
                    import msvcrt

                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() > deadline:
                    raise StoreError(f"SHD-14: store locked by another writer: {path}") from None
                time.sleep(0.2)
        yield
    finally:
        if sys.platform == "win32":
            import msvcrt

            with contextlib.suppress(OSError):
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        fh.close()


def _manifest_lines(vdir: Path) -> list[str]:
    m = vdir / MANIFEST
    if not m.exists():
        return []
    return m.read_bytes().decode("utf-8").split("\n")[:-1]


def _as_frame(rows: pl.DataFrame | Sequence[Mapping[str, Any]]) -> pl.DataFrame:
    if isinstance(rows, pl.DataFrame):
        return rows
    return pl.DataFrame(list(rows), infer_schema_length=None)


def _utc(value: Any) -> dt.datetime:
    if not isinstance(value, dt.datetime) or value.tzinfo is None:
        raise StoreError(f"kickoff_utc must be a timezone-aware datetime, got {value!r}")
    return value.astimezone(dt.UTC)


class ShadowStore:
    """SHD-14: the append-only writer. Its only write is append(); there is no update or
    delete. Each append is a new write-once partition, made read-only, and one manifest line."""

    def __init__(
        self,
        version: str,
        root: Path = SHADOW_BASE,
        *,
        base: Path = SHADOW_BASE,
        clock: Callable[[], dt.datetime] = _utc_now,
    ) -> None:
        if not version or not version.replace(".", "").isalnum():
            raise StoreError(f"bad shadow_version {version!r}")
        self.root = check_store_path(root, base)
        self.version = version
        self.version_dir = check_store_path(self.root / f"v{version}", base)
        self._base = base
        self._clock = clock

    def _check(self, table: str, df: pl.DataFrame, written_at: dt.datetime) -> None:
        if table not in TABLES:
            raise StoreError(f"SHD-14: unknown table {table!r}; tables are {sorted(TABLES)}")
        if df.is_empty():
            raise StoreError(f"SHD-14: no rows to write to {table}")
        if "pricing_mode" not in df.columns:
            raise StoreError("SHD-19: every row needs pricing_mode")
        bad = set(df["pricing_mode"].to_list()) - PRICING_MODES
        if bad:
            raise StoreError(f"SHD-19: pricing_mode must be one of {sorted(PRICING_MODES)}: {bad}")
        if "shadow_version" in df.columns and set(df["shadow_version"].to_list()) != {self.version}:
            raise StoreError(f"SHD-15: rows carry another shadow_version than {self.version}")
        if table in KICKOFF_TABLES:
            if "kickoff_utc" not in df.columns or df["kickoff_utc"].null_count():
                raise StoreError(f"SHD-14: every {table} row needs kickoff_utc")
            first = min(_utc(k) for k in df["kickoff_utc"].to_list())
            if written_at >= first:
                raise KickoffPassed(
                    f"SHD-14: {table} row written at {written_at.isoformat()} is at or after "
                    f"kickoff {first.isoformat()}"
                )

    def append(
        self,
        table: str,
        rows: pl.DataFrame | Sequence[Mapping[str, Any]],
        *,
        season: int,
        week: int,
    ) -> Path:
        """SHD-14: write rows as a new partition of `table`. Every row gets shadow_version and
        written_at (UTC). Returns the written part.parquet."""
        df = _as_frame(rows)
        self.version_dir.mkdir(parents=True, exist_ok=True)
        with _locked(self.version_dir / _LOCK):
            written_at = self._clock().astimezone(dt.UTC)
            self._check(table, df, written_at)
            out = (
                self.version_dir
                / table
                / f"season={season}"
                / f"week={week:02d}"
                / f"written_at={written_at.strftime(_TS_FORMAT)}"
            )
            check_store_path(out, self._base)
            out.mkdir(parents=True, exist_ok=False)
            stamped = df.with_columns(
                pl.lit(self.version).alias("shadow_version"),
                pl.lit(written_at).cast(pl.Datetime("us", "UTC")).alias("written_at"),
            )
            buf = io.BytesIO()
            stamped.write_parquet(buf)
            data = buf.getvalue()
            digest = _sha256(data)
            path = out / _PART
            path.write_bytes(data)
            (out / _HASH_FILE).write_text(digest + "\n", encoding="ascii", newline="\n")
            for f in (path, out / _HASH_FILE):
                os.chmod(f, stat.S_IREAD)
            lines = _manifest_lines(self.version_dir)
            entry = {
                "seq": len(lines),
                "path": path.relative_to(self.version_dir).as_posix(),
                "table": table,
                "rows": stamped.height,
                "file_sha256": digest,
                "written_at": written_at.isoformat(),
                "prev_sha256": _sha256(lines[-1].encode("utf-8")) if lines else _GENESIS,
            }
            line = json.dumps(entry, sort_keys=True)
            with (self.version_dir / MANIFEST).open("a", encoding="utf-8", newline="\n") as fh:
                fh.write(line + "\n")
            return path


def verify_store(root: Path, version: str) -> list[str]:
    """SHD-14: recompute every hash. Returns the problems found (empty = verified): a broken
    chain, a missing, changed or unlisted file, a wrong content.sha256, or a row whose
    shadow_version is not this version."""
    vdir = root / f"v{version}"
    problems: list[str] = []
    listed: set[str] = set()
    prev = _GENESIS
    for i, line in enumerate(_manifest_lines(vdir)):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            problems.append(f"manifest line {i}: not JSON")
            prev = _sha256(line.encode("utf-8"))
            continue
        if entry.get("seq") != i:
            problems.append(f"manifest line {i}: seq {entry.get('seq')} (a line was removed?)")
        if entry.get("prev_sha256") != prev:
            problems.append(f"manifest line {i}: prev_sha256 breaks the chain")
        prev = _sha256(line.encode("utf-8"))
        rel = str(entry.get("path"))
        listed.add(rel)
        f = vdir / rel
        if not f.exists():
            problems.append(f"{rel}: listed in the manifest but missing")
            continue
        digest = _sha256(f.read_bytes())
        if digest != entry.get("file_sha256"):
            problems.append(f"{rel}: sha256 differs from the manifest")
        side = f.parent / _HASH_FILE
        if not side.exists() or side.read_text(encoding="ascii").strip() != digest:
            problems.append(f"{rel}: content.sha256 differs from the file")
        try:
            df = pl.read_parquet(f, columns=["shadow_version"])
        except Exception as exc:  # a changed file may not even parse
            problems.append(f"{rel}: unreadable ({type(exc).__name__})")
            continue
        if df.height != entry.get("rows"):
            problems.append(f"{rel}: {df.height} rows, manifest says {entry.get('rows')}")
        if set(df["shadow_version"].to_list()) != {version}:
            problems.append(f"{rel}: rows of another shadow_version")
    if vdir.exists():
        for f in sorted(vdir.rglob(_PART)):
            rel = f.relative_to(vdir).as_posix()
            if rel not in listed:
                problems.append(f"{rel}: not in the manifest")
    return problems
