"""BUILD_PLAN Phase 0: every value the spec labels "initial" appears in params.yaml.

Read straight from docs/MODEL_SPEC.md, not from a hand-typed list:
- every k in the Shrink column and every number in the Min n column of the
  OFF / DEF / PLY / COA tables (section 2 says these k are all initial until BT-02);
- every "initial <number>" phrase, and the G3 half-lives.
"""

import re
from typing import Any

import yaml

from tests.phase0.helpers import (
    PARAMS_PATH,
    iter_leaves,
    numbers_in,
    spec_table_rows,
    spec_text,
    value_matches,
)

_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")


def _entries() -> list[dict[str, Any]]:
    data = yaml.safe_load(PARAMS_PATH.read_text(encoding="utf-8"))
    return [e for _, _, e in iter_leaves(data)]


def _ids(entry: dict[str, Any]) -> set[str]:
    sid = entry["spec_id"]
    return {sid} if isinstance(sid, str) else set(sid)


def _covered(spec_id: str | None, number: float, line: str, entries: list[dict[str, Any]]) -> bool:
    return any(
        (spec_id is None or spec_id in _ids(e))
        and e["source"] in line
        and value_matches(e["value"], number)
        for e in entries
    )


def _k_numbers(cell: str) -> list[float]:
    """Numbers following each 'k =' up to the next ';'."""
    out: list[float] = []
    for seg in re.findall(r"k = ([^;]*)", cell):
        out.extend(numbers_in(seg))
    return out


def test_every_table_k_and_min_n_is_in_params() -> None:
    entries = _entries()
    rows = spec_table_rows(("OFF-", "DEF-", "PLY-", "COA-"))
    assert len(rows) >= 40, f"only {len(rows)} metric rows parsed"
    missing = []
    for row_id, cells, line in rows:
        shrink = cells.get("Shrink (k, prior)", "")
        min_n = _YEAR_RE.sub("", cells.get("Min n", ""))
        for label, numbers in (("k", _k_numbers(shrink)), ("min n", numbers_in(min_n))):
            for number in numbers:
                if not _covered(row_id, number, line, entries):
                    missing.append(f"{row_id} {label} = {number:g}")
    assert not missing, "not in params.yaml:\n" + "\n".join(missing)


def test_every_initial_phrase_is_in_params() -> None:
    entries = _entries()
    found = []
    missing = []
    for line in spec_text().splitlines():
        for m in re.finditer(r"initial\W{0,3}(\d+(?:\.\d+)?)", line):
            number = float(m.group(1))
            found.append(number)
            if not _covered(None, number, line, entries):
                missing.append(f"initial {m.group(1)} in: {line[:90]}...")
    assert len(found) >= 5, f"only {len(found)} 'initial N' phrases parsed"
    assert not missing, "\n".join(missing)


def test_g3_half_lives_are_in_params() -> None:
    entries = _entries()
    line = next(ln for ln in spec_text().splitlines() if ln.startswith("**G3."))
    halves = [float(h) for h in re.findall(r"h = (\d+(?:\.\d+)?)", line)]
    assert halves == [3.0, 6.0], halves
    for h in halves:
        assert _covered("G3", h, line, entries), f"G3 h = {h:g} missing"


def test_one_lambda_per_matchup_adjustment() -> None:
    """Your decision: separate lambda for MTC-01, MTC-02 and MTC-03."""
    lambdas = [e for e in _entries() if "λ (initial 0.5)" in e["source"]]
    assert sorted(i for e in lambdas for i in _ids(e)) == ["MTC-01", "MTC-02", "MTC-03"]
    assert all(e["value"] == 0.5 for e in lambdas)
