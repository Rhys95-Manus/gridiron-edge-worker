"""DATA-08 (approved 2026-10-17): the tracked config/kalshi_nfl_series.yaml holds only the
user's decisions (decision, decided_by, decided_on, decision_basis); discovery metadata and
proposals live in an untracked file under data/, so the scheduled collector never leaves the
tracked file modified."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from ge.config import REPO_ROOT
from ge.ingest import kalshi as k
from tests.phase1.test_kalshi_proposals import _series, _teams

DECISION_KEYS = {"decision", "decided_by", "decided_on", "decision_basis"}


def _paths(tmp: Path) -> tuple[Path, Path]:
    return tmp / "decisions.yaml", tmp / "review.yaml"


def _decide(decisions: Path, review: Path, n: int = 2) -> list[str]:
    tickers = sorted(yaml.safe_load(review.read_text(encoding="utf-8"))["series"])[:n]
    k.apply_decisions(
        decisions,
        review,
        {tickers[0]: "test include"},
        {t: "test exclude" for t in tickers[1:]},
        decided_by="user",
        decided_on="2026-10-17",
    )
    return tickers


def test_paths() -> None:
    assert k.DECISIONS_PATH == REPO_ROOT / "config" / "kalshi_nfl_series.yaml"
    assert k.REVIEW_PATH == REPO_ROOT / "data" / "kalshi" / "series_review.yaml"


def test_discovery_writes_only_the_review_file(tmp_path: Path) -> None:
    decisions, review = _paths(tmp_path)
    cands, new = k.refresh_review(review, decisions, _series(), _teams())
    assert new == len(cands) > 0
    assert review.exists() and not decisions.exists()
    rows = yaml.safe_load(review.read_text(encoding="utf-8"))["series"]
    assert all("decision" not in r for r in rows.values())
    assert k.pending_series(review, decisions) == {c.ticker for c in cands}


def test_rediscovery_with_changed_metadata_leaves_decisions_byte_identical(
    tmp_path: Path,
) -> None:
    decisions, review = _paths(tmp_path)
    k.refresh_review(review, decisions, _series(), _teams())
    _decide(decisions, review)
    before = decisions.read_bytes()
    changed = copy.deepcopy(_series())
    for s in changed:
        s["title"] = (s.get("title") or "") + " (renamed)"
        s["fee_multiplier"] = 2
    k.refresh_review(review, decisions, changed, _teams())
    assert decisions.read_bytes() == before
    rows = yaml.safe_load(review.read_text(encoding="utf-8"))["series"]
    assert all(r["title"].endswith("(renamed)") for r in rows.values())


def test_new_ticker_arrives_pending_without_touching_decisions(tmp_path: Path) -> None:
    decisions, review = _paths(tmp_path)
    series = _series()
    k.refresh_review(review, decisions, series[:5], _teams())
    _decide(decisions, review)
    before = decisions.read_bytes()
    cands, new = k.refresh_review(review, decisions, series, _teams())
    assert new > 0
    assert decisions.read_bytes() == before
    decided = set(k.read_decisions(decisions))
    assert k.pending_series(review, decisions) == {c.ticker for c in cands} - decided
    rows = yaml.safe_load(review.read_text(encoding="utf-8"))["series"]
    for t in k.pending_series(review, decisions):
        assert rows[t]["proposed"] in {"include", "exclude", "undecided"}, t
        assert k.FEE_RULE_SKIPPED in rows[t]["proposed_rules"], t


def test_decided_ticker_that_disappears_keeps_its_decision(tmp_path: Path) -> None:
    decisions, review = _paths(tmp_path)
    k.refresh_review(review, decisions, _series(), _teams())
    first, *_ = _decide(decisions, review)
    k.refresh_review(review, decisions, [s for s in _series() if s["ticker"] != first], _teams())
    assert k.approved_series(decisions) == {first}
    assert first not in k.pending_series(review, decisions)


def test_decisions_file_holds_only_decision_fields(tmp_path: Path) -> None:
    decisions, review = _paths(tmp_path)
    k.refresh_review(review, decisions, _series(), _teams())
    inc, *exc = _decide(decisions, review, 3)
    rows = yaml.safe_load(decisions.read_text(encoding="utf-8"))["series"]
    assert set(rows) == {inc, *exc}
    for r in rows.values():
        assert set(r) == DECISION_KEYS
    assert rows[inc] == {
        "decision": "include",
        "decided_by": "user",
        "decided_on": "2026-10-17",
        "decision_basis": "test include",
    }
    assert b"\r\n" not in decisions.read_bytes()


def test_apply_decisions_rejects_unknown_or_double_listed(tmp_path: Path) -> None:
    decisions, review = _paths(tmp_path)
    k.refresh_review(review, decisions, _series(), _teams())
    first = sorted(yaml.safe_load(review.read_text(encoding="utf-8"))["series"])[0]
    for inc, exc in (({"KXNOTASERIES": "x"}, {}), ({first: "x"}, {first: "y"})):
        with pytest.raises(ValueError):
            k.apply_decisions(
                decisions, review, inc, exc, decided_by="user", decided_on="2026-10-17"
            )


@pytest.mark.parametrize(
    "row",
    [
        {"decision": "pending", "decided_by": "u", "decided_on": "d", "decision_basis": "b"},
        {"decision": "yes", "decided_by": "u", "decided_on": "d", "decision_basis": "b"},
        {"decision": "include", "decided_by": "u", "decided_on": "d"},
        {"decision": "include", "decided_by": "u", "decided_on": "d", "decision_basis": "b",
         "title": "metadata does not belong here"},
    ],
)  # fmt: skip
def test_bad_decision_rows_are_rejected(tmp_path: Path, row: dict[str, Any]) -> None:
    decisions = tmp_path / "decisions.yaml"
    decisions.write_text(yaml.safe_dump({"series": {"KXNFLX": row}}), encoding="utf-8")
    with pytest.raises(ValueError):
        k.approved_series(decisions)


def test_split_combined_file(tmp_path: Path) -> None:
    """The one-time migration: decided rows go to the decisions file (four fields), every row's
    metadata and proposal go to the review file; pending rows have no decision."""
    combined = tmp_path / "combined.yaml"
    decisions, review = _paths(tmp_path)
    meta = {"first_seen": "2026-09-29", "title": "T", "category": "Sports", "tags": ["Football"],
            "reasons": ["tag:Football"], "fee_type": "quadratic", "fee_multiplier": 1,
            "proposed": "include", "proposed_rules": ["nfl_prefix"]}  # fmt: skip
    combined.write_text(
        yaml.safe_dump(
            {
                "generated_by": "ge ingest kalshi",
                "series": {
                    "KXA": {"decision": "include", **meta, "decided_by": "user",
                            "decided_on": "2026-09-29", "decision_basis": "b"},
                    "KXB": {"decision": "pending", **meta},
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )  # fmt: skip
    k.split_combined(combined, decisions, review)
    d = yaml.safe_load(decisions.read_text(encoding="utf-8"))["series"]
    r = yaml.safe_load(review.read_text(encoding="utf-8"))["series"]
    assert d == {
        "KXA": {"decision": "include", "decided_by": "user", "decided_on": "2026-09-29",
                "decision_basis": "b"}
    }  # fmt: skip
    assert set(r) == {"KXA", "KXB"}
    assert r["KXB"] == meta and "decision" not in r["KXA"]
    assert k.pending_series(review, decisions) == {"KXB"}


def test_repo_decisions_file() -> None:
    """The tracked file after the split: decisions only, every row complete, and the user's
    2026-10-17 decision on KXNFLSEEDOU."""
    rows = k.read_decisions(k.DECISIONS_PATH)
    assert rows
    assert all(set(r) == DECISION_KEYS for r in rows.values())
    assert rows["KXNFLSEEDOU"] == {
        "decision": "include",
        "decided_by": "user",
        "decided_on": "2026-10-17",
        "decision_basis": "tracked futures, not modelled in v1",
    }
    assert b"\r\n" not in k.DECISIONS_PATH.read_bytes()
