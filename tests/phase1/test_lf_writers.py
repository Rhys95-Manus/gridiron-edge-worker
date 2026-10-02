"""Every text file the worker writes uses LF line endings on every OS. Path.write_text
translates "\\n" to the platform separator, so on Windows it wrote CRLF into config files
that git stores as LF (.gitattributes eol=lf), leaving every regenerated file "modified"."""

import ast
import datetime as dt
import functools
from pathlib import Path
from typing import Any

import polars as pl

from ge.ingest.kalshi import apply_decisions, nfl_candidates, update_review_file, write_proposals
from ge.ingest.raw import partitions, write_raw
from ge.ingest.stadiums import load_stadiums, write_stadiums
from tests.phase1.conftest import load_fixture


@functools.cache
def _series() -> Any:
    return load_fixture("kalshi_series_subset.json")["response"]["series"]


def _assert_lf(path: Path) -> None:
    data = path.read_bytes()
    assert b"\n" in data, f"{path.name}: expected multi-line text"
    assert b"\r\n" not in data, f"{path.name}: {data.count(b'\r\n')} CRLF line endings"


def test_kalshi_review_file_writers_use_lf(tmp_path: Path) -> None:
    path = tmp_path / "kalshi_nfl_series.yaml"
    cands = nfl_candidates(_series())
    assert cands
    update_review_file(path, cands)
    _assert_lf(path)
    write_proposals(path, {c.ticker: ("include", ["nfl_prefix"]) for c in cands[:2]})
    _assert_lf(path)
    apply_decisions(
        path,
        {cands[0].ticker: "test"},
        {},
        decided_by="test",
        decided_on="2026-10-02",
    )
    _assert_lf(path)


def test_stadiums_writer_uses_lf(tmp_path: Path) -> None:
    path = tmp_path / "stadiums.yaml"
    write_stadiums(load_stadiums(), 2026, path)
    _assert_lf(path)


def test_every_write_text_under_src_forces_lf() -> None:
    """Guard for writers added later: each Path.write_text call under src/ passes newline."""
    src = Path(__file__).resolve().parents[2] / "src"
    calls, bad = 0, []
    for p in sorted(src.rglob("*.py")):
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "write_text"
            ):
                calls += 1
                kw = {k.arg: k.value for k in node.keywords}
                nl = kw.get("newline")
                if not (isinstance(nl, ast.Constant) and nl.value == "\n"):
                    bad.append(f"{p.relative_to(src)}:{node.lineno}")
    assert calls >= 5, f"found only {calls} write_text calls; the scan is broken"
    assert not bad, f'write_text without newline="\\n": {bad}'


def test_raw_store_hash_file_uses_lf(tmp_path: Path) -> None:
    t = dt.datetime(2026, 10, 2, tzinfo=dt.UTC)
    write_raw(pl.DataFrame({"a": [1]}), "x", 2026, source="t", root=tmp_path, pulled_at=t)
    (part,) = partitions(tmp_path, "x", 2026)
    data = (part / "content.sha256").read_bytes()
    assert data.endswith(b"\n") and b"\r" not in data
