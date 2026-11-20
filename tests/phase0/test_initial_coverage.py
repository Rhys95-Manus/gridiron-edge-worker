"""BUILD_PLAN Phase 0: every value the spec labels "initial" appears in params.yaml.

Read straight from docs/MODEL_SPEC.md, not from a hand-typed list:
- every k in the Shrink column and every number in the Min n column of the
  OFF / DEF / PLY / COA tables (section 2 says these k are all initial until BT-02);
- every "initial <number>" and "initial <symbol> = <number>" phrase outside the Decisions
  log, each covered by an entry whose source holds the phrase itself, and the G3 half-lives.
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

# Seasons are not sample sizes: years, and walk-forward bounds like "S minus 1", written
# with a minus sign or a hyphen (COA-07, user approval 2026-10-08).
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b|\bS\s*[\N{MINUS SIGN}-]\s*1\b")


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


# "initial 0.5", "(initial 4)", and the symbol form "initial h = 3" (approved 2026-11-19).
_INITIAL_RE = re.compile(
    r"initial\W{0,3}(\d+(?:\.\d+)?)|initial\s+[^\W\d]\w*\s*=\s*(\d+(?:\.\d+)?)"
)
_DECISIONS_LOG = "## Decisions log"


def _rules_text() -> str:
    """The spec without its Decisions log section (ruling 2026-11-19)."""
    text = spec_text()
    start = text.index(f"\n{_DECISIONS_LOG}\n")
    end = text.index("\n## ", start + 1)
    return text[:start] + text[end:]


def _initial_matches(line: str) -> list[tuple[str, float]]:
    return [(m.group(0), float(m.group(1) or m.group(2))) for m in _INITIAL_RE.finditer(line)]


def _initial_missing(text: str, entries: list[dict[str, Any]]) -> list[str]:
    """Initial phrases with no entry whose source holds the phrase and whose value matches.
    Requiring the phrase in the source stops another number on the same line (e.g. PRV-03's
    minimum of 3 prior games) from covering it."""
    missing = []
    for line in text.splitlines():
        for phrase, number in _initial_matches(line):
            if not any(
                phrase in e["source"] and e["source"] in line and value_matches(e["value"], number)
                for e in entries
            ):
                missing.append(f"{phrase} in: {line[:90]}...")
    return missing


def test_every_initial_phrase_is_in_params() -> None:
    text = _rules_text()
    found = [m for line in text.splitlines() for m in _initial_matches(line)]
    assert len(found) >= 5, f"only {len(found)} 'initial N' phrases parsed"
    missing = _initial_missing(text, _entries())
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


# The PRV-03 sentence that sync #2 (2026-11-19) replaced; it slipped past the old regex.
_OLD_PRV03 = "The usage half-life is initial h = 3 games."
_NEW_PRV03 = (
    "The usage half-life is G3's fitted usage half-life from the same params_fitted window file"
    " as k."
)


def test_initial_phrase_regex_reads_symbol_form() -> None:
    """Approved 2026-11-19: "initial <symbol> = N" counts as an initial phrase."""
    assert [(t, n) for t, n in _initial_matches(_OLD_PRV03)] == [("initial h = 3", 3.0)]
    assert [(t, n) for t, n in _initial_matches("λ (initial 0.5)")] == [("initial 0.5", 0.5)]


def test_old_prv03_line_would_have_failed() -> None:
    """The pre-sync PRV-03 line, rebuilt from today's spec, is reported missing even though
    the same line holds another 3 (PRV-03's minimum prior games)."""
    line = next(ln for ln in _rules_text().splitlines() if ln.startswith("**PRV-03 "))
    assert line.count(_NEW_PRV03) == 1
    old_line = line.replace(_NEW_PRV03, _OLD_PRV03)
    assert _initial_missing(old_line, _entries()) == [f"initial h = 3 in: {old_line[:90]}..."]


def test_rules_text_skips_only_the_decisions_log() -> None:
    """Ruling 2026-11-19: the Decisions log records history (it quotes replaced wording), so
    the initial-phrase scan reads every other section."""
    text = _rules_text()
    assert "## Decisions log" not in text
    assert "## Open questions" in text and "## Sources" in text
    assert "**PRV-03 " in text
