"""Helpers for reading docs/MODEL_SPEC.md and walking the config files."""

from __future__ import annotations

import math
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = REPO_ROOT / "docs" / "MODEL_SPEC.md"
PARAMS_PATH = REPO_ROOT / "config" / "params.yaml"
FEES_PATH = REPO_ROOT / "config" / "fees.yaml"

# ENV- added 2026-09-29 with spec section 6b (ENV-01 to ENV-04).
SPEC_ID_RE = re.compile(r"\b(?:(?:DATA|OFF|DEF|PLY|COA|MTC|ENV|PRJ|EDG|BT)-\d{2}[a-z]?|G[1-7])\b")

# Order matters: m:ss before plain numbers, \tfrac{a}{b} and a/b before plain numbers.
_TOKEN_RE = re.compile(
    r"\\tfrac\{(?P<fn>\d+)\}\{(?P<fd>\d+)\}"
    r"|(?P<min>\d+):(?P<sec>\d{2})\b"
    r"|(?P<num>\d+)/(?P<den>\d+)"
    r"|(?P<plain>\d[\d,]*(?:\.\d+)?)"
    r"|\b(?P<word>one|two|three|four|five|six|seven|eight|nine|ten)\b",
    re.IGNORECASE,
)
_WORD_LIST = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
_WORDS = {w: i + 1 for i, w in enumerate(_WORD_LIST)}


_MD_ESCAPE_RE = re.compile(r"\\([!-/:-@\[-`{-~])")
_SPACES_RE = re.compile(r"[ \t]+")


def normalize_md(text: str) -> str:
    """Undo Markdown export formatting only: drop backslash escapes before ASCII punctuation
    (\\< \\$ \\* \\|, not LaTeX like \\tfrac), drop backticks, collapse runs of spaces and tabs
    (including table-cell padding) to one space. Words, numbers, symbols and line breaks
    are untouched, so they must still match exactly."""
    text = _MD_ESCAPE_RE.sub(r"\1", text)
    text = text.replace("`", "")
    return _SPACES_RE.sub(" ", text)


def spec_text() -> str:
    return SPEC_PATH.read_text(encoding="utf-8")


def spec_ids() -> set[str]:
    return set(SPEC_ID_RE.findall(spec_text()))


def numbers_in(text: str) -> list[float]:
    """Every number written in spec text: 20,000 / 0.25 / 1/3 / 2:00 / \\tfrac{1}{4} / four."""
    out: list[float] = []
    for m in _TOKEN_RE.finditer(text):
        if m.group("fn"):
            out.append(int(m.group("fn")) / int(m.group("fd")))
        elif m.group("min"):
            out.append(int(m.group("min")) * 60 + int(m.group("sec")))
        elif m.group("num"):
            out.append(int(m.group("num")) / int(m.group("den")))
        elif m.group("word"):
            out.append(_WORDS[m.group("word").lower()])
        else:
            out.append(float(m.group("plain").replace(",", "")))
    return out


def value_matches(value: float, number: float) -> bool:
    """Unit rules: as written, percent -> fraction, cents -> centicents, dollars -> centicents."""
    target = abs(value)
    return any(
        math.isclose(target, cand, rel_tol=1e-9, abs_tol=1e-12)
        for cand in (number, number / 100, number * 100, number * 10_000)
    )


def value_in_source(value: float, source: str) -> bool:
    return any(value_matches(value, n) for n in numbers_in(source))


def iter_leaves(params: dict[str, Any]) -> Iterator[tuple[str, str, dict[str, Any]]]:
    """(group, name, entry) for every parameter entry in params.yaml."""
    for group, entries in params.items():
        for name, entry in entries.items():
            yield group, name, entry


def iter_dict_paths(node: Any, prefix: tuple[str, ...] = ()) -> Iterator[tuple[str, ...]]:
    """Every key path in a nested dict (lists are values, not keys)."""
    if isinstance(node, dict):
        for key, child in node.items():
            path = (*prefix, key)
            yield path
            yield from iter_dict_paths(child, path)


def iter_dict_nodes(node: Any, prefix: tuple[str, ...] = ()) -> Iterator[tuple[str, ...]]:
    """Path to every dict in a nested structure, including the root ()."""
    if isinstance(node, dict):
        yield prefix
        for key, child in node.items():
            yield from iter_dict_nodes(child, (*prefix, key))


def get_path(node: Any, path: tuple[str, ...]) -> Any:
    for key in path:
        node = node[key]
    return node


def spec_table_rows(id_prefixes: tuple[str, ...]) -> list[tuple[str, dict[str, str], str]]:
    """(row_id, {header: cell}, raw_line) for every table row whose first cell is a spec ID."""
    rows: list[tuple[str, dict[str, str], str]] = []
    header: list[str] | None = None
    for line in spec_text().splitlines():
        if not line.startswith("|"):
            header = None
            continue
        # Markdown escapes a literal pipe as \| (e.g. |L3 - season| in PLY-13); don't split on it.
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        if header is None:
            header = cells
            continue
        if set(line) <= set("|-: "):
            continue
        row_id = cells[0]
        if row_id.startswith(id_prefixes) and SPEC_ID_RE.fullmatch(row_id):
            rows.append((row_id, dict(zip(header, cells, strict=False)), line))
    return rows
