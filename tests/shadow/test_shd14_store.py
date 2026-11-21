"""SHD-14 / SHD-15 / SHD-19: the append-only shadow store.

SHD-14: "Write-once partitions plus a hash-chained manifest; the writer has no update or delete.
Files and manifest lines are hashed with SHA-256. No snapshot row for a game can be written after
its kickoff." Rows here are synthetic (no real-world facts)."""

import ast
import datetime as dt
import hashlib
import json
import os
import stat
from pathlib import Path

import polars as pl
import pytest

from ge.config import REPO_ROOT
from ge.shadow.store import (
    MANIFEST,
    TABLES,
    KickoffPassed,
    ShadowStore,
    StoreError,
    verify_store,
)

T0 = dt.datetime(2026, 11, 22, 12, 0, tzinfo=dt.UTC)
KICK = dt.datetime(2026, 11, 23, 18, 0, tzinfo=dt.UTC)


class Clock:
    def __init__(self, t: dt.datetime) -> None:
        self.t = t

    def __call__(self) -> dt.datetime:
        self.t += dt.timedelta(microseconds=1)  # distinct written_at per write
        return self.t


def _store(tmp_path: Path, t: dt.datetime = T0) -> ShadowStore:
    return ShadowStore("0", root=tmp_path, base=tmp_path, clock=Clock(t))


def _snap_rows(n: int = 2, kickoff: dt.datetime = KICK) -> list[dict[str, object]]:
    return [
        {
            "game_id": "G1",
            "kickoff_utc": kickoff,
            "ticker": f"T{i}",
            "pricing_mode": "live",
            "unpriced_reason": "pricer_not_frozen",
        }
        for i in range(n)
    ]


def _status_rows() -> list[dict[str, object]]:
    return [{"game_id": "G1", "snapshot_type": "T-24h", "status": "ok", "pricing_mode": "live"}]


def test_layout_and_read_only(tmp_path: Path) -> None:
    path = _store(tmp_path).append("snapshots", _snap_rows(), season=2026, week=12)
    rel = path.relative_to(tmp_path).parts
    assert rel[:5] == ("v0", "snapshots", "season=2026", "week=12", rel[4])
    assert rel[4].startswith("written_at=") and rel[5] == "part.parquet"
    for f in (path, path.parent / "content.sha256"):
        assert not os.stat(f).st_mode & stat.S_IWRITE, f"{f.name} must be read-only"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert (path.parent / "content.sha256").read_text(encoding="ascii").strip() == digest


def test_every_row_has_shadow_version_written_at_and_pricing_mode(tmp_path: Path) -> None:
    path = _store(tmp_path).append("snapshots", _snap_rows(3), season=2026, week=12)
    df = pl.read_parquet(path)
    assert df["shadow_version"].to_list() == ["0"] * 3
    assert df["pricing_mode"].to_list() == ["live"] * 3
    assert df["written_at"].null_count() == 0


@pytest.mark.parametrize("table", sorted(TABLES))
def test_pricing_mode_required_on_every_table(tmp_path: Path, table: str) -> None:
    rows = [{"game_id": "G1", "kickoff_utc": KICK}]
    with pytest.raises(StoreError, match="pricing_mode"):
        _store(tmp_path).append(table, rows, season=2026, week=12)


def test_pricing_mode_values(tmp_path: Path) -> None:
    rows = _snap_rows()
    rows[0]["pricing_mode"] = "guess"
    with pytest.raises(StoreError, match="pricing_mode"):
        _store(tmp_path).append("snapshots", rows, season=2026, week=12)


def test_row_shadow_version_must_match_store(tmp_path: Path) -> None:
    rows = [{**r, "shadow_version": "1"} for r in _snap_rows()]
    with pytest.raises(StoreError, match="shadow_version"):
        _store(tmp_path).append("snapshots", rows, season=2026, week=12)


def test_unknown_table_and_empty_rows_refused(tmp_path: Path) -> None:
    s = _store(tmp_path)
    with pytest.raises(StoreError, match="table"):
        s.append("whatever", _status_rows(), season=2026, week=12)
    with pytest.raises(StoreError, match="no rows"):
        s.append("snapshot_status", [], season=2026, week=12)


def test_partitions_are_write_once(tmp_path: Path) -> None:
    fixed = lambda: T0  # noqa: E731 - same written_at twice
    s = ShadowStore("0", root=tmp_path, base=tmp_path, clock=fixed)
    s.append("snapshot_status", _status_rows(), season=2026, week=12)
    with pytest.raises(FileExistsError):
        s.append("snapshot_status", _status_rows(), season=2026, week=12)


def test_writer_has_no_update_or_delete(tmp_path: Path) -> None:
    public = {n for n in dir(_store(tmp_path)) if not n.startswith("_")}
    assert public == {"append", "root", "version", "version_dir"}


@pytest.mark.parametrize("table", ["snapshots", "book_levels"])
def test_no_snapshot_row_after_kickoff(tmp_path: Path, table: str) -> None:
    s = _store(tmp_path, KICK - dt.timedelta(microseconds=1))  # first write lands at KICK
    with pytest.raises(KickoffPassed):
        s.append(table, _snap_rows(), season=2026, week=12)
    assert not list(tmp_path.rglob("part.parquet"))


def test_snapshot_rows_need_kickoff(tmp_path: Path) -> None:
    rows = [{k: v for k, v in r.items() if k != "kickoff_utc"} for r in _snap_rows()]
    with pytest.raises(StoreError, match="kickoff_utc"):
        _store(tmp_path).append("snapshots", rows, season=2026, week=12)


def test_status_rows_may_be_written_after_kickoff(tmp_path: Path) -> None:
    s = _store(tmp_path, KICK + dt.timedelta(hours=1))
    s.append("snapshot_status", _status_rows(), season=2026, week=12)


def test_store_root_guard_applies(tmp_path: Path) -> None:
    from ge.shadow.store import StorePathError

    with pytest.raises(StorePathError, match="data/raw"):
        ShadowStore("0", root=REPO_ROOT / "data" / "raw" / "shadow")
    with pytest.raises(StorePathError, match="outside"):
        ShadowStore("0", root=tmp_path)  # default base is data/shadow


def _three_writes(tmp_path: Path) -> list[Path]:
    s = _store(tmp_path)
    return [
        s.append("snapshots", _snap_rows(), season=2026, week=12),
        s.append("snapshot_status", _status_rows(), season=2026, week=12),
        s.append("snapshot_status", _status_rows(), season=2026, week=13),
    ]


def test_manifest_is_a_sha256_hash_chain(tmp_path: Path) -> None:
    paths = _three_writes(tmp_path)
    lines = (tmp_path / "v0" / MANIFEST).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    prev = "0" * 64
    for i, (line, path) in enumerate(zip(lines, paths, strict=True)):
        entry = json.loads(line)
        assert entry["seq"] == i
        assert entry["prev_sha256"] == prev
        assert entry["file_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert entry["path"] == path.relative_to(tmp_path / "v0").as_posix()
        prev = hashlib.sha256(line.encode("utf-8")).hexdigest()
    assert verify_store(tmp_path, "0") == []


def _make_writable(p: Path) -> None:
    os.chmod(p, stat.S_IREAD | stat.S_IWRITE)


def test_verify_fails_when_an_earlier_file_changes(tmp_path: Path) -> None:
    first = _three_writes(tmp_path)[0]
    _make_writable(first)
    data = bytearray(first.read_bytes())
    data[len(data) // 2] ^= 0x01
    first.write_bytes(bytes(data))
    problems = verify_store(tmp_path, "0")
    assert any("sha256" in p and first.name in p for p in problems), problems


@pytest.mark.parametrize("drop", [0, 1, 2])
def test_verify_fails_when_a_manifest_line_is_removed(tmp_path: Path, drop: int) -> None:
    _three_writes(tmp_path)
    m = tmp_path / "v0" / MANIFEST
    lines = m.read_text(encoding="utf-8").splitlines(keepends=True)
    del lines[drop]
    m.write_text("".join(lines), encoding="utf-8", newline="")
    assert verify_store(tmp_path, "0") != []


def test_verify_fails_when_a_manifest_line_is_edited(tmp_path: Path) -> None:
    _three_writes(tmp_path)
    m = tmp_path / "v0" / MANIFEST
    text = m.read_text(encoding="utf-8").replace('"rows": 2', '"rows": 3', 1)
    m.write_text(text, encoding="utf-8", newline="")
    assert verify_store(tmp_path, "0") != []


def test_verify_fails_on_an_unlisted_partition(tmp_path: Path) -> None:
    _three_writes(tmp_path)
    extra = tmp_path / "v0" / "snapshots" / "season=2026" / "week=12" / "written_at=x"
    extra.mkdir()
    pl.DataFrame({"a": [1]}).write_parquet(extra / "part.parquet")
    assert any("not in the manifest" in p for p in verify_store(tmp_path, "0"))


def test_verify_of_an_empty_store_is_clean(tmp_path: Path) -> None:
    assert verify_store(tmp_path, "0") == []


# SHD-15: "No fit, threshold, filter or market-type choice reads shadow data, enforced by a test."
_NO_SHADOW_PACKAGES = ("fit", "pricer_v0", "models", "metrics", "edge", "backtest", "store")


def _imports(path: Path) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
            out |= {f"{node.module}.{a.name}" for a in node.names}
    return out


def test_no_fit_or_pricer_module_imports_the_shadow_reader() -> None:
    src = REPO_ROOT / "src" / "ge"
    files = [f for pkg in _NO_SHADOW_PACKAGES for f in (src / pkg).rglob("*.py")]
    assert any("pricer_v0" in f.parts for f in files) and any("fit" in f.parts for f in files)
    offenders = {
        f.relative_to(src).as_posix(): sorted(i for i in _imports(f) if i.startswith("ge.shadow"))
        for f in files
    }
    assert {k: v for k, v in offenders.items() if v} == {}
